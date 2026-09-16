import ctypes
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
import customtkinter as ctk

from mitia import App, size


@unittest.skipUnless(sys.platform == "win32", "Windows input regression")
class WindowsInputTests(unittest.TestCase):
    def setUp(self):
        self.settings_dir = tempfile.TemporaryDirectory()
        self.settings_patch = patch.object(
            App,
            "_settings_path",
            return_value=Path(self.settings_dir.name) / "settings.json",
        )
        self.font_patch = patch("mitia.load_persian_font", return_value=None)
        self.settings_patch.start()
        self.font_patch.start()

        self.app = App()
        self.app.geometry("980x820+20+20")
        self.app.attributes("-topmost", True)
        self.app.pick("image")
        self.app.focus_force()
        self.callback_errors = []
        self.app.report_callback_exception = (
            lambda *args: self.callback_errors.append(args)
        )
        self.pump(180)

    def tearDown(self):
        try:
            for callback in self.app.tk.splitlist(
                self.app.tk.call("after", "info")
            ):
                try:
                    self.app.after_cancel(callback)
                except Exception:
                    pass
            self.app.destroy()
        finally:
            self.font_patch.stop()
            self.settings_patch.stop()
            self.settings_dir.cleanup()

    def pump(self, milliseconds=180):
        self.app.after(milliseconds, self.app.quit)
        self.app.mainloop()

    def wait_until(self, predicate, attempts=20):
        for _ in range(attempts):
            if predicate():
                return True
            self.pump(80)
        return False

    def click(self, widget, relx=0.5, rely=0.5):
        self.app.update_idletasks()
        x = widget.winfo_rootx() + int(widget.winfo_width() * relx)
        y = widget.winfo_rooty() + int(widget.winfo_height() * rely)
        ctypes.windll.user32.SetCursorPos(x, y)
        ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
        ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
        self.pump()

    def click_list_row(self, index):
        self.app.update_idletasks()
        bbox = self.app.list.bbox(index)
        self.assertIsNotNone(bbox)
        x0, y0, width, height = bbox
        x = self.app.list.winfo_rootx() + x0 + max(4, width // 2)
        y = self.app.list.winfo_rooty() + y0 + height // 2
        ctypes.windll.user32.SetCursorPos(x, y)
        ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
        ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
        self.pump()

    def key(self, vk):
        widget = self.app.focus_get()

        self.assertIsNotNone(
            widget,
            "No widget has keyboard focus",
        )

        if vk == 8:
            # Backspace
            try:
                if widget.selection_present():
                    widget.delete("sel.first", "sel.last")
                else:
                    position = widget.index("insert")
                    if position > 0:
                        widget.delete(position - 1)
            except Exception:
                pass

        elif 48 <= vk <= 57:
            # Numbers 0-9
            character = chr(vk)

            try:
                if widget.selection_present():
                    widget.delete("sel.first", "sel.last")
            except Exception:
                pass

            widget.insert("insert", character)

        elif 65 <= vk <= 90:
            # Letters A-Z
            character = chr(vk)

            try:
                if widget.selection_present():
                    widget.delete("sel.first", "sel.last")
            except Exception:
                pass

            widget.insert("insert", character)

        self.pump()

    def test_click_custom_then_type_and_process_in_both_languages(self):
        app = self.app
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "photo.jpg"
            Image.new("RGB", (400, 300), "red").save(source)
            app.add_paths([str(source)])

            for run_number, language in enumerate(("fa", "en"), start=1):
                if app.lang != language:
                    app.change_lang()
                    self.pump()

                app.dim.set("Original")
                app.custom_toggle("Original")
                app.custom.set("")
                self.pump()

                self.click(app.dimension_menu._text_label)
                self.assertIsNotNone(app.menu_popup)
                buttons = app.menu_popup.winfo_children()[0].winfo_children()
                custom_button = next(
                    widget
                    for widget in buttons
                    if isinstance(widget, ctk.CTkButton)
                    and widget.cget("text") == app.tr("custom_option")
                )
                self.click(custom_button)

                self.assertEqual(app.dim.get(), "Custom")
                self.assertTrue(app.custombox.winfo_ismapped())

                app.custom_entry.focus_force()
                self.pump()

                self.assertEqual(
                        app.focus_get(),
                        app.custom_entry._entry,
                        "Custom dimension entry did not receive keyboard focus",
                )

                for character in "1280":
                    self.key(ord(character))

                self.assertEqual(app.custom.get(), "1280")

                self.key(8)
                self.assertEqual(app.custom.get(), "128")

                app.custom_entry.select_range(0, "end")
                self.key(ord("2"))
                self.assertEqual(app.custom.get(), "2")

                self.key(ord("0"))
                self.key(ord("0"))
                self.assertEqual(app.custom.get(), "200")

                self.click(app.start_button)
                self.assertTrue(
                    self.wait_until(lambda: not app.busy, attempts=40),
                    "Compression did not finish in time",
                )

                outputs = sorted(Path(folder).glob("photo_compressed*.jpg"))
                self.assertEqual(len(outputs), run_number)
                with Image.open(outputs[-1]) as result:
                    self.assertEqual(result.size, (200, 150))

                self.assertFalse(self.callback_errors)

    def test_single_click_on_file_shows_estimate_without_preview_button(self):
        app = self.app
        self.assertFalse(hasattr(app, "preview_button"))

        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "estimate.jpg"
            Image.new("RGB", (800, 600), "blue").save(source, quality=95)
            app.add_paths([str(source)])
            expected_new = 12345

            with patch("mitia.estimate_image_size", return_value=expected_new):
                self.click_list_row(0)
                expected = app.msg(
                    "estimate_result",
                    old=size(source.stat().st_size),
                    new=size(expected_new),
                )
                self.assertTrue(
                    self.wait_until(lambda: app.status.get() == expected),
                    app.status.get(),
                )

            self.assertEqual(list(Path(folder).iterdir()), [source])
            self.assertFalse(self.callback_errors)

    def test_cancel_button_resets_progress_bar(self):
        app = self.app
        app.busy = True
        app.cancel_event.clear()
        app.cancel_button.configure(state="normal")
        app.bar.set(0.82)
        self.pump(50)

        self.click(app.cancel_button)

        self.assertTrue(app.cancel_event.is_set())
        self.assertAlmostEqual(app.bar.get(), 0.0, places=6)
        self.assertEqual(app.cancel_button.cget("state"), "disabled")
        self.assertFalse(self.callback_errors)

        app.busy = False

    def test_ctrl_a_selects_custom_entry_with_persian_keyboard_layout(self):
        app = self.app

        # برو به حالت تصویر و Custom را فعال کن
        app.dim.set("Custom")
        app.custom_toggle("Custom")
        app.update_idletasks()

        entry = app.custom_entry._entry

        # مقدار آزمایشی
        app.custom.set("1280")
        entry.focus_force()
        self.pump()

        # شبیه‌سازی حالتی که کلید فیزیکی A زده شده
        # ولی Layout ویندوز فارسی است و keysym دیگر "a" نیست.
        event = type(
            "FakeEvent",
            (),
            {
                "widget": entry,
                "keysym": "Arabic_sheen",
                "keycode": 65,
            },
        )()

        result = app._custom_ctrl_shortcut(event)

        self.assertEqual(result, "break")
        self.assertTrue(
            entry.selection_present(),
            "Ctrl+A with Persian keyboard layout did not select the text",
        )

        self.assertEqual(
            entry.get()[entry.index("sel.first"):entry.index("sel.last")],
            "1280",
        )

        # بعد از انتخاب، تایپ عدد باید مقدار قبلی را جایگزین کند
        entry.delete("sel.first", "sel.last")
        entry.insert("insert", "2")

        self.assertEqual(app.custom.get(), "2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
