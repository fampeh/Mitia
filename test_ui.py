import unittest

import customtkinter as ctk

from mitia import App


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
                    self.assertLess(abs(menu.winfo_rooty() - box.winfo_rooty()), 3)
                    self.assertGreaterEqual(box.winfo_rootx(), app.winfo_rootx())
                    self.assertLessEqual(box.winfo_rootx() + box.winfo_width(), app.winfo_rootx() + app.winfo_width())
                    menu._open_dropdown_menu()
                    app.update()
                    popup = app.menu_popup
                    self.assertIsNotNone(popup)
                    self.assertLess(abs(popup.winfo_rootx() - menu.winfo_rootx()), 3)
                    self.assertLess(abs(popup.winfo_width() - menu.winfo_width()), 3)
                    self.assertTrue(popup.winfo_rooty() >= menu.winfo_rooty() + menu.winfo_height()
                                    or popup.winfo_rooty() + popup.winfo_height() <= menu.winfo_rooty())
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


if __name__ == "__main__":
    unittest.main()
