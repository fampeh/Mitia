import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
import customtkinter as ctk

import mitia
from mitia import App, CompactMenu, size


GUI_AVAILABLE = sys.platform in ("win32", "darwin") or bool(os.environ.get("DISPLAY"))


@unittest.skipUnless(GUI_AVAILABLE, "GUI display required")
class SettingsAndUITests(unittest.TestCase):
    def setUp(self):
        self.settings_dir = tempfile.TemporaryDirectory()
        self.settings_file = Path(self.settings_dir.name) / "settings.json"
        self.settings_patch = patch.object(
            App, "_settings_path", return_value=self.settings_file
        )
        self.font_patch = patch("mitia.load_persian_font", return_value=None)
        self.settings_patch.start()
        self.font_patch.start()

        self.app = App()
        self.app.geometry("980x820+20+20")
        self.app.pick("image")
        self.pump(80)

    def tearDown(self):
        self.destroy_app()
        self.font_patch.stop()
        self.settings_patch.stop()
        ctk.set_widget_scaling(1.0)
        self.settings_dir.cleanup()

    def destroy_app(self):
        app = getattr(self, "app", None)
        if app is None:
            return
        try:
            for callback in app.tk.splitlist(app.tk.call("after", "info")):
                try:
                    app.after_cancel(callback)
                except Exception:
                    pass
            app.destroy()
        except Exception:
            pass
        self.app = None

    def pump(self, milliseconds=80):
        app = self.app
        if app is None:
            return
        deadline = time.monotonic() + milliseconds / 1000
        while time.monotonic() < deadline:
            try:
                app.update()
            except Exception:
                break
            time.sleep(0.005)

    def wait_until(self, predicate, timeout=2.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.pump(20)
            if predicate():
                return True
        return False

    def test_no_preview_button_exists_anymore(self):
        self.assertFalse(hasattr(self.app, "preview_button"))
        self.assertTrue(hasattr(self.app, "start_button"))
        self.assertTrue(hasattr(self.app, "cancel_button"))

    def test_click_selection_pipeline_shows_quick_estimate_in_footer(self):
        app = self.app
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "photo.jpg"
            Image.new("RGB", (400, 300), "red").save(source, quality=90)
            app.add_paths([str(source)])
            app.list.selection_clear(0, "end")
            app.list.selection_set(0)

            with patch("mitia.estimate_image_size", return_value=12345):
                app.estimate_selected()
                expected = app.msg(
                    "estimate_result",
                    old=size(source.stat().st_size),
                    new=size(12345),
                )
                self.assertTrue(
                    self.wait_until(lambda: app.status.get() == expected),
                    app.status.get(),
                )

            self.assertFalse(app.busy)
            self.assertFalse(hasattr(app, "preview_button"))
            self.assertEqual(list(Path(folder).iterdir()), [source])

    def test_stale_estimate_result_is_ignored(self):
        app = self.app
        app.status.set("KEEP")
        app.estimate_request = 10
        app.events.put(("est", 9, 1000, 500))
        self.pump(120)
        self.assertEqual(app.status.get(), "KEEP")

    def test_cancel_resets_progress_immediately_and_on_cancel_event(self):
        app = self.app
        app.busy = True
        app.cancel_event.clear()
        app.cancel_button.configure(state="normal")
        app.bar.set(0.73)

        app.cancel()

        self.assertTrue(app.cancel_event.is_set())
        self.assertAlmostEqual(app.bar.get(), 0.0, places=6)
        self.assertEqual(app.cancel_button.cget("state"), "disabled")
        self.assertEqual(app.status.get(), app.tr("cancelled"))

        app.bar.set(0.61)
        app.events.put(("c",))
        self.assertTrue(self.wait_until(lambda: not app.busy))
        self.assertAlmostEqual(app.bar.get(), 0.0, places=6)
        self.assertEqual(app.start_button.cget("state"), "normal")

    def test_auto_routes_video_from_images_without_wrong_media_warning(self):
        app = self.app
        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / "clip.mp4"
            video.write_bytes(b"fake")

            with patch("mitia.messagebox.showwarning") as warning:
                app.add_paths([str(video)])

            self.assertEqual(app.mode, "video")
            self.assertEqual(app.files["video"], [str(video.resolve())])
            self.assertEqual(app.files["image"], [])
            warning.assert_not_called()

    def test_auto_routes_image_from_videos_without_wrong_media_warning(self):
        app = self.app
        app.pick("video")
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "photo.jpg"
            Image.new("RGB", (20, 20), "red").save(image)

            with patch("mitia.messagebox.showwarning") as warning:
                app.add_paths([str(image)])

            self.assertEqual(app.mode, "image")
            self.assertEqual(app.files["image"], [str(image.resolve())])
            warning.assert_not_called()

    def test_mixed_media_are_sorted_into_both_lists_and_current_mode_stays(self):
        app = self.app
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "photo.jpg"
            video = Path(folder) / "clip.mp4"
            Image.new("RGB", (20, 20), "red").save(image)
            video.write_bytes(b"fake")

            app.add_paths([str(image), str(video)])

            self.assertEqual(app.mode, "image")
            self.assertEqual(app.files["image"], [str(image.resolve())])
            self.assertEqual(app.files["video"], [str(video.resolve())])

    def test_duplicates_are_ignored_and_unsupported_files_warn_once(self):
        app = self.app
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "photo.jpg"
            unknown = Path(folder) / "notes.xyz"
            Image.new("RGB", (20, 20), "red").save(image)
            unknown.write_text("hello", encoding="utf-8")

            with patch("mitia.messagebox.showwarning") as warning:
                app.add_paths([str(image), str(image), str(unknown)])

            self.assertEqual(app.files["image"], [str(image.resolve())])
            warning.assert_called_once()
            self.assertIn("1", warning.call_args.args[1])

    def test_folder_import_sorts_images_and_videos(self):
        app = self.app
        with tempfile.TemporaryDirectory() as folder:
            folder_path = Path(folder)
            image = folder_path / "photo.png"
            video = folder_path / "movie.mkv"
            other = folder_path / "readme.txt"
            Image.new("RGB", (20, 20), "blue").save(image)
            video.write_bytes(b"fake")
            other.write_text("x", encoding="utf-8")

            with patch("mitia.messagebox.showwarning") as warning:
                app.add_paths([folder])

            self.assertIn(str(image.resolve()), app.files["image"])
            self.assertIn(str(video.resolve()), app.files["video"])
            warning.assert_called_once()

    def test_settings_survive_language_and_mode_rebuilds(self):
        app = self.app
        app.out.set("C:/Users/Test/My Photos")
        app.output_entry.delete(0, "end")
        app.output_entry.insert(0, "C:/Users/Test/My Photos")
        app.q.set(72)
        app.dim.set("Custom")
        app.custom.set("640")
        app.axis.set(app.tr("height"))
        app.gray.set(True)

        app.change_lang()
        self.pump(50)

        self.assertEqual(app.out.get(), "C:/Users/Test/My Photos")
        self.assertEqual(app.output_entry.cget("justify"), "left")
        self.assertEqual(app.axis.get(), "Height")
        self.assertTrue(app.custombox.winfo_ismapped())

        app.pick("video")
        app.q.set(28)
        app.res.set("720p")
        app.save_settings()
        app.pick("image")

        self.assertEqual(app.q.get(), 72)
        self.assertEqual(app.custom.get(), "640")
        self.assertEqual(app.axis.get(), app.tr("height"))
        self.assertTrue(app.gray.get())

        app.pick("video")
        self.assertEqual(app.q.get(), 28)
        self.assertEqual(app.res.get(), "720p")

    def test_settings_persist_across_app_restart(self):
        app = self.app
        app.q.set(67)
        app.dim.set("Custom")
        app.custom.set("555")
        app.axis.set(app.tr("width"))
        app.gray.set(True)
        app.save_settings()
        app.lang = "en"
        app._save_persistent()

        self.destroy_app()
        self.app = App()
        self.app.geometry("980x820+20+20")
        self.assertEqual(self.app.lang, "en")
        self.app.pick("image")
        self.pump(50)

        self.assertEqual(self.app.q.get(), 67)
        self.assertEqual(self.app.dim.get(), "Custom")
        self.assertEqual(self.app.custom.get(), "555")
        self.assertEqual(self.app.axis.get(), self.app.tr("width"))
        self.assertTrue(self.app.gray.get())

    def test_numeric_input_rejects_letters_accepts_persian_digits(self):
        app = self.app
        app.dim.set("Custom")
        app.custom_toggle("Custom")
        self.pump(30)

        entry = app.custom_entry
        entry.delete(0, "end")
        entry.insert(0, "abc")
        self.assertEqual(app.custom.get(), "")

        entry.insert(0, "۱۲۸۰")
        self.assertEqual(app.custom.get(), "۱۲۸۰")
        app.axis.set(app.tr("width"))

        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "photo.jpg"
            Image.new("RGB", (400, 300), "red").save(source)
            app.files["image"] = [str(source)]
            q, fmt, width, height, gray = app.opts()
            self.assertEqual((width, height), (1280, None))

    def test_custom_menu_callback_shows_and_hides_custom_controls(self):
        app = self.app
        app.dimension_menu.choose(app.tr("custom_option"))
        self.pump(30)
        self.assertEqual(app.dim.get(), "Custom")
        self.assertTrue(app.custombox.winfo_ismapped())

        app.dimension_menu.choose(app.tr("original"))
        self.pump(30)
        self.assertEqual(app.dim.get(), "Original")
        self.assertFalse(app.custombox.winfo_ismapped())

    def test_compact_menu_popup_tracks_widget_and_closes_after_choice(self):
        app = self.app

        for scaling in (1.0, 1.25):
            ctk.set_widget_scaling(scaling)
            app.geometry(f"{int(980 * scaling)}x{int(820 * scaling)}")

            # Let geometry/scaling changes settle before opening the popup.
            self.pump(80)
            app.dismiss_menu()
            app.update_idletasks()

            menu = app.dimension_menu
            menu._open_dropdown_menu()

            # Do not call app.update()/self.pump() here: the app intentionally
            # dismisses an open menu on a root <Configure> event, so processing
            # another full event cycle can close the popup before we inspect it.
            popup = app.menu_popup
            self.assertIsNotNone(popup)
            self.assertIs(app.menu_owner, menu)

            popup.update_idletasks()

            self.assertLess(abs(popup.winfo_rootx() - menu.winfo_rootx()), 4)
            self.assertLess(abs(popup.winfo_width() - menu.winfo_width()), 4)
            self.assertGreaterEqual(
                popup.winfo_rooty(), menu.winfo_rooty() + menu.winfo_height()
            )

            menu.choose(menu.cget("values")[0])

            self.assertIsNone(app.menu_popup)
            self.assertIsNone(app.menu_owner)

    def test_default_output_is_beside_each_input(self):
        app = self.app
        with tempfile.TemporaryDirectory() as folder:
            sources = []
            for name in ("one", "two"):
                parent = Path(folder) / name
                parent.mkdir()
                source = parent / "photo.jpg"
                Image.new("RGB", (200, 150), "red").save(source, quality=95)
                sources.append(str(source))

            app.files["image"] = sources
            app.out.set("")
            app.q.set(50)
            app.work("image", sources, "", app.opts())

            for source in sources:
                self.assertTrue(
                    Path(source).with_name("photo_compressed.jpg").is_file()
                )
                self.assertTrue(Path(source).is_file())

    def test_busy_guards_block_navigation_and_file_mutation(self):
        app = self.app
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "photo.jpg"
            Image.new("RGB", (20, 20), "red").save(source)
            app.add_paths([str(source)])
            app.busy = True

            with patch("mitia.threading.Thread") as worker:
                app.start()
                app.clear_files()
                app.pick("video")
                app.add_paths([str(source)])
                worker.assert_not_called()

            self.assertEqual(app.files["image"], [str(source.resolve())])
            self.assertEqual(app.mode, "image")
            app.busy = False

    def test_output_trace_does_not_leak_across_rebuilds(self):
        app = self.app
        initial = len(app.out.trace_info())
        for _ in range(4):
            app.output_entry.delete(0, "end")
            app.output_entry.insert(0, "C:/Users/Test/My output")
            app.change_lang()
            self.pump(20)
            self.assertEqual(app.output_entry.get(), "C:/Users/Test/My output")
            self.assertEqual(len(app.out.trace_info()), initial)


if __name__ == "__main__":
    unittest.main(verbosity=2)
