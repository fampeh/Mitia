import unittest
import tempfile
from pathlib import Path
from PIL import Image

import customtkinter as ctk

from mitia import App, CompactMenu


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.app = App()
        self.app.pick("image")
        self.app.update()

    def tearDown(self):
        for callback in self.app.tk.splitlist(self.app.tk.call("after", "info")):
            self.app.after_cancel(callback)
        self.app.destroy()

    def test_settings_survive_language_and_mode_changes(self):
        app = self.app
        app.out.set("C:/Users/Test/My Photos")
        app.q.set(72)
        app.dim.set("Custom")
        app.custom.set("640")
        app.axis.set(app.tr("height"))
        app.gray.set(True)
        app.change_lang()
        app.update()
        self.assertEqual(app.out.get(), "C:/Users/Test/My Photos")
        self.assertEqual(app.output_entry.cget("justify"), "left")
        self.assertEqual(app.axis.get(), "Height")
        self.assertTrue(app.custombox.winfo_ismapped())
        app.pick("video")
        app.q.set(28)
        app.res.set("720p")
        app.change_lang()
        app.pick("image")
        app.update()
        self.assertEqual(app.q.get(), 72)
        self.assertEqual(app.custom.get(), "640")
        self.assertEqual(app.axis.get(), app.tr("height"))
        self.assertTrue(app.gray.get())
        self.assertEqual(app.output_entry.cget("justify"), "left")
        app.pick("video")
        self.assertEqual(app.q.get(), 28)
        self.assertEqual(app.res.get(), "720p")

    def test_compact_layout_and_popup(self):
        app = self.app
        for scaling in (1.0, 1.25, 1.5):
            ctk.set_widget_scaling(scaling)
            for language in ("fa", "en"):
                if app.lang != language:
                    app.change_lang()
                for width in (800, 980):
                    app.geometry(f"{int(width * scaling)}x{int(820 * scaling)}")
                    app.dim.set("Custom")
                    app.custom_toggle("Custom")
                    app.update()
                    app.after(250, app.quit)
                    app.mainloop()
                    menu = app.dimension_menu
                    box = app.custombox
                    panel = menu.master.master.master
                    for group in panel.winfo_children():
                        if group.grid_info().get("row") == 0:
                            self.assertGreaterEqual(group.winfo_rootx(), panel.winfo_rootx())
                            self.assertLessEqual(group.winfo_rootx() + group.winfo_width(), panel.winfo_rootx() + panel.winfo_width())
                    checkbox = app.gray_checkbox
                    self.assertLess(abs(checkbox.winfo_rooty() + checkbox.winfo_height() / 2 - menu.winfo_rooty() - menu.winfo_height() / 2), 3)
                    self.assertLess(abs(menu.winfo_rooty() - box.winfo_rooty()), 3)
                    self.assertGreaterEqual(box.winfo_rootx(), app.winfo_rootx())
                    self.assertLessEqual(box.winfo_rootx() + box.winfo_width(), app.winfo_rootx() + app.winfo_width())
                    menu._open_dropdown_menu()
                    app.update()
                    popup = app.menu_popup
                    self.assertIsNotNone(popup)
                    self.assertLess(abs(popup.winfo_rootx() - menu.winfo_rootx()), 3)
                    self.assertLess(abs(popup.winfo_width() - menu.winfo_width()), 3)
                    self.assertGreaterEqual(popup.winfo_rooty(), menu.winfo_rooty() + menu.winfo_height())
                    menu.choose(app.tr("original"))
                    app.update()
                    self.assertIsNone(app.menu_popup)
                    self.assertFalse(box.winfo_ismapped())
        ctk.set_widget_scaling(1.0)

    def test_numeric_input_and_footer(self):
        app = self.app
        app.geometry("800x720")
        app.dim.set("Custom")
        app.custom_toggle("Custom")
        app.update()
        entry = next(w for w in app.custombox.winfo_children() if isinstance(w, ctk.CTkEntry))
        entry.insert(0, "abc")
        self.assertEqual(app.custom.get(), "")
        entry.insert(0, "1280")
        entry.insert("end", "px")
        self.assertEqual(app.custom.get(), "1280")
        for language in ("fa", "en"):
            if app.lang != language:
                app.change_lang()
            app.update()
            button = app.start_button
            self.assertTrue(button.winfo_ismapped())
            self.assertLessEqual(button.winfo_rooty() + button.winfo_height(), app.winfo_rooty() + app.winfo_height())

    def test_default_output_beside_each_input(self):
        app = self.app
        with tempfile.TemporaryDirectory() as folder:
            sources = []
            for name in ("one", "two"):
                parent = Path(folder) / name
                parent.mkdir()
                source = parent / "photo.jpg"
                Image.new("RGB", (20, 20), "red").save(source)
                sources.append(str(source))
            app.files["image"] = sources
            app.out.set("")
            app.work("image", sources, "", app.opts())
            for source in sources:
                self.assertTrue(Path(source).with_name("photo_compressed.jpg").is_file())
                self.assertTrue(Path(source).is_file())

    def test_menus_remain_open_after_click(self):
        app = self.app
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        for mode in ("image", "video"):
            app.pick(mode)
            for language in ("fa", "en"):
                if app.lang != language:
                    app.change_lang()
                app.update()
                app.after(300, app.quit)
                app.mainloop()
                menus = [w for w in descendants(app) if isinstance(w, CompactMenu)]
                for menu in menus:
                    if not menu.winfo_ismapped():
                        continue
                    menu._canvas.event_generate("<Button-1>", x=menu.winfo_width()-10, y=10)
                    app.after(300, app.quit)
                    app.mainloop()
                    self.assertIs(app.menu_owner, menu)
                    self.assertIsNotNone(app.menu_popup)
                    self.assertTrue(app.menu_popup.winfo_ismapped())
                    menu.choose(menu.cget("values")[0])
                    self.assertIsNone(app.menu_popup)

    def test_custom_selection_keeps_controls_fixed(self):
        app = self.app
        for language in ("fa", "en"):
            if app.lang != language:
                app.change_lang()
            for scaling in (1.0, 1.25, 1.5):
                ctk.set_widget_scaling(scaling)
                app.geometry(f"{int(980 * scaling)}x{int(820 * scaling)}")
                app.dim.set("Original")
                app.custom_toggle("Original")
                app.update()
                panel = app.dimension_menu.master.master.master
                def positions():
                    return [(w.winfo_rootx(), w.winfo_width()) for w in panel.winfo_children() if w.grid_info().get("row") == 0]
                before = positions()
                app.dim.set("Custom")
                app.custom_toggle("Custom")
                app.update()
                self.assertEqual(before, positions())
                checkbox = app.gray_checkbox
                browse = app.output_browse_button
                if language == "fa":
                    self.assertLess(abs(checkbox.winfo_rootx() - browse.winfo_rootx()), 3)
                else:
                    self.assertLess(abs(checkbox.winfo_rootx() + checkbox.winfo_width() - browse.winfo_rootx() - browse.winfo_width()), 3)
        ctk.set_widget_scaling(1.0)

    def test_dimensions_apply_from_menu_and_persian_numbers(self):
        app = self.app
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "original.jpg"
            Image.new("RGB", (400, 300), "red").save(source)
            app.files["image"] = [str(source)]
            for language in ("fa", "en"):
                if app.lang != language:
                    app.change_lang()
                for preset, expected in (("800 × 600", (800, 600)), (app.tr("custom_option"), (160, 120))):
                    app.dimension_menu.choose(preset)
                    app.update()
                    if app.dim.get() == "Custom":
                        app.custom_entry.delete(0, "end")
                        app.custom_entry.insert(0, "۱۶۰")
                        self.assertEqual(app.custom.get(), "۱۶۰")
                        app.axis.set(app.tr("width"))
                    app.work("image", [str(source)], "", app.opts())
                    candidates = list(Path(folder).glob("original_compressed*.jpg"))
                    target = max(candidates, key=lambda p: p.stat().st_mtime_ns)
                    with Image.open(target) as result:
                        self.assertEqual(result.size, expected)


if __name__ == "__main__":
    unittest.main()
