import ctypes
import sys
import unittest
import tempfile
from pathlib import Path
from PIL import Image

import customtkinter as ctk

from mitia import App


@unittest.skipUnless(sys.platform == "win32", "Windows input regression")
class WindowsInputTests(unittest.TestCase):
    def setUp(self):
        self.app = App()
        self.app.geometry("980x820+20+20")
        self.app.attributes("-topmost", True)
        self.app.pick("image")
        self.app.focus_force()
        self.callback_errors = []
        self.app.report_callback_exception = lambda *args: self.callback_errors.append(args)
        self.pump()

    def tearDown(self):
        for callback in self.app.tk.splitlist(self.app.tk.call("after", "info")):
            self.app.after_cancel(callback)
        self.app.destroy()

    def pump(self):
        self.app.after(200, self.app.quit)
        self.app.mainloop()

    def click(self, widget):
        self.app.update_idletasks()
        x = widget.winfo_rootx() + widget.winfo_width() // 2
        y = widget.winfo_rooty() + widget.winfo_height() // 2
        ctypes.windll.user32.SetCursorPos(x, y)
        ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
        ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
        self.pump()

    def key(self, vk):
        scan = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
        ctypes.windll.user32.keybd_event(vk, scan, 0, 0)
        ctypes.windll.user32.keybd_event(vk, scan, 2, 0)
        self.pump()

    def test_click_custom_then_type(self):
        app = self.app
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "photo.jpg"
            Image.new("RGB", (400, 300), "red").save(source)
            app.add_paths([str(source)])
            for language in ("fa", "en"):
                if app.lang != language:
                    app.change_lang()
                app.dim.set("Original")
                app.custom_toggle("Original")
                app.custom.set("")
                self.pump()
                self.click(app.dimension_menu._text_label)
                self.assertIsNotNone(app.menu_popup)
                buttons = app.menu_popup.winfo_children()[0].winfo_children()
                custom_button = next(w for w in buttons if isinstance(w, ctk.CTkButton) and w.cget("text") == app.tr("custom_option"))
                self.click(custom_button)
                self.assertEqual(app.dim.get(), "Custom")
                self.click(app.custom_entry)
                for character in "1280":
                    self.key(ord(character))
                self.assertEqual(app.custom.get(), "1280")
                self.key(8)
                self.assertEqual(app.custom.get(), "128")
                app.custom_entry.select_range(0, "end")
                self.key(ord("2"))
                self.assertEqual(app.custom.get(), "2")
                self.key(ord("A"))
                self.assertEqual(app.custom.get(), "2")
                self.key(ord("0"))
                self.key(ord("0"))
                self.click(app.start_button)
                for _ in range(30):
                    if not app.busy:
                        break
                    self.pump()
                self.assertFalse(app.busy)
                outputs = list(Path(folder).glob("photo_compressed*.jpg"))
                self.assertEqual(len(outputs), 1 if language == "fa" else 2)
                with Image.open(outputs[-1]) as result:
                    self.assertEqual(result.size, (200, 150))
                self.assertFalse(self.callback_errors)


if __name__ == "__main__":
    unittest.main()
