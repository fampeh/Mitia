import io
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, features

import mitia
from mitia import (
    ProcessingCancelled,
    estimate_image_size,
    estimate_video_size,
    ffmpeg,
    pack_image,
    pack_video,
    size,
)


class ImageProcessingTests(unittest.TestCase):
    def test_size_handles_none_and_units(self):
        self.assertEqual(size(None), "—")
        self.assertEqual(size(1024), "1 KB")
        self.assertEqual(size(1024 * 1024), "1.00 MB")

    def test_cmyk_to_png(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "cmyk.jpg"
            Image.new("CMYK", (20, 20), (0, 100, 100, 0)).save(source)

            old_size, new_size, status = pack_image(
                source, folder, 80, "PNG", None, None, False
            )

            self.assertEqual(status, "compressed")
            self.assertGreater(old_size, 0)
            self.assertGreater(new_size, 0)
            with Image.open(Path(folder) / "cmyk_compressed.png") as output:
                self.assertEqual(output.format, "PNG")
                self.assertNotEqual(output.mode, "CMYK")

    @unittest.skipUnless(features.check("webp"), "Pillow WebP support required")
    def test_cmyk_to_webp(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "cmyk.jpg"
            Image.new("CMYK", (30, 20), (0, 100, 100, 0)).save(source)

            pack_image(source, folder, 75, "WEBP", None, None, False)

            with Image.open(Path(folder) / "cmyk_compressed.webp") as output:
                self.assertEqual(output.format, "WEBP")

    def test_sixteen_bit_png_to_jpeg(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "depth.png"
            Image.new("I;16", (20, 20), 200).save(source)

            pack_image(source, folder, 80, "JPEG", None, None, False)

            with Image.open(Path(folder) / "depth_compressed.jpg") as output:
                self.assertEqual(output.format, "JPEG")
                self.assertIn(output.mode, ("L", "RGB"))

    def test_transparent_rgba_survives_grayscale_png(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "alpha.png"
            image = Image.new("RGBA", (4, 4), (255, 0, 0, 0))
            image.putpixel((1, 1), (0, 255, 0, 255))
            image.save(source)

            pack_image(source, folder, 80, "PNG", None, None, True)

            with Image.open(Path(folder) / "alpha_compressed.png") as output:
                rgba = output.convert("RGBA")
                self.assertEqual(rgba.getpixel((0, 0))[3], 0)
                self.assertEqual(rgba.getpixel((1, 1))[3], 255)

    def test_palette_transparency_survives_grayscale_png(self):
        """
        Palette-mode PNG transparency is preserved during grayscale conversion.
        """
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "palette.png"
            image = Image.new("P", (4, 4), 0)
            image.putpalette([255, 0, 0, 0, 255, 0] + [0] * 762)
            image.putpixel((1, 1), 1)
            image.save(source, transparency=0)

            pack_image(source, folder, 80, "PNG", None, None, True)

            with Image.open(Path(folder) / "palette_compressed.png") as output:
                rgba = output.convert("RGBA")
                self.assertEqual(rgba.getpixel((0, 0))[3], 0)
                self.assertEqual(rgba.getpixel((1, 1))[3], 255)

    def test_exif_rotation_resize_and_unique_names(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "rotated.jpg"
            exif = Image.Exif()
            exif[274] = 6
            Image.new("RGB", (40, 20), "red").save(source, exif=exif)
            original_bytes = source.read_bytes()

            pack_image(source, folder, 80, "JPEG", 10, None, False)
            pack_image(source, folder, 80, "JPEG", None, 10, False)

            first = Path(folder) / "rotated_compressed.jpg"
            second = Path(folder) / "rotated_compressed_2.jpg"
            self.assertTrue(first.is_file())
            self.assertTrue(second.is_file())

            with Image.open(first) as output:
                self.assertEqual(output.size, (10, 20))
            with Image.open(second) as output:
                self.assertEqual(output.size, (5, 10))

            self.assertEqual(source.read_bytes(), original_bytes)

    def test_failed_save_leaves_no_partial_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "photo.png"
            Image.new("RGB", (20, 20), "red").save(source)

            with patch.object(Image.Image, "save", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    pack_image(source, folder, 80, "JPEG", None, None, False)

            self.assertEqual(list(Path(folder).iterdir()), [source])

    def test_cancel_after_image_save_removes_partial_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "photo.jpg"
            Image.new("RGB", (50, 50), "red").save(source)
            cancel = threading.Event()

            def fake_save(_image, handle, _fmt=None, **_kwargs):
                handle.write(b"partial output")
                cancel.set()

            with patch.object(Image.Image, "save", new=fake_save):
                with self.assertRaises(ProcessingCancelled):
                    pack_image(source, folder, 80, "JPEG", None, None, False, cancel)

            self.assertEqual(list(Path(folder).iterdir()), [source])

    def test_explicit_same_format_larger_output_is_discarded(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "photo.jpg"
            Image.new("RGB", (20, 20), "red").save(source, quality=50)
            old_size = source.stat().st_size

            def fake_save(_image, handle, _fmt=None, **_kwargs):
                handle.write(b"x" * (old_size + 500))

            with patch.object(Image.Image, "save", new=fake_save):
                returned_old, returned_new, status = pack_image(
                    source, folder, 100, "JPEG", None, None, False
                )

            self.assertEqual(returned_old, old_size)
            self.assertIsNone(returned_new)
            self.assertEqual(status, "already_optimized")
            self.assertFalse((Path(folder) / "photo_compressed.jpg").exists())

    def test_real_transformation_is_kept_even_if_larger(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "photo.jpg"
            Image.new("RGB", (20, 20), "red").save(source)
            old_size = source.stat().st_size

            def fake_save(_image, handle, _fmt=None, **_kwargs):
                handle.write(b"x" * (old_size + 500))

            with patch.object(Image.Image, "save", new=fake_save):
                returned_old, returned_new, status = pack_image(
                    source, folder, 80, "PNG", None, None, False
                )

            self.assertEqual(returned_old, old_size)
            self.assertGreater(returned_new, old_size)
            self.assertEqual(status, "compressed")
            self.assertTrue((Path(folder) / "photo_compressed.png").exists())

    def test_png_slider_controls_compress_level_without_optimize(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "photo.png"
            Image.new("RGB", (100, 100), "red").save(source)
            original_save = Image.Image.save
            captured = {}

            def spy_save(image, handle, fmt=None, **kwargs):
                captured.update(kwargs)
                return original_save(image, handle, fmt, **kwargs)

            with patch.object(Image.Image, "save", new=spy_save):
                pack_image(source, folder, 20, "PNG", None, None, False)

            self.assertNotIn("optimize", captured)
            self.assertEqual(captured.get("compress_level"), 7)


class EstimateTests(unittest.TestCase):
    def test_image_estimate_is_fast_formula_and_responds_to_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "photo.jpg"
            Image.new("RGB", (1600, 1200), "red").save(source, quality=95)

            original = estimate_image_size(source, 80, None, None, None, False)
            lower_quality = estimate_image_size(source, 40, None, None, None, False)
            resized = estimate_image_size(source, 80, None, 800, None, False)
            webp = estimate_image_size(source, 80, "WEBP", None, None, False)

            self.assertGreater(original, 0)
            self.assertLess(lower_quality, original)
            self.assertLess(resized, original)
            self.assertLess(webp, original)
            self.assertEqual(list(Path(folder).iterdir()), [source])

    def test_video_estimate_does_not_encode_and_responds_to_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "video.mp4"
            source.write_bytes(b"x" * (5 * 1024 * 1024))

            with patch("mitia._quick_video_info", return_value=(1080, "h264")), \
                 patch("mitia.subprocess.Popen") as popen:
                h264 = estimate_video_size(source, 23, "libx264", None)
                h265 = estimate_video_size(source, 23, "libx265", None)
                downscaled = estimate_video_size(source, 23, "libx264", 720)
                high_crf = estimate_video_size(source, 30, "libx264", None)

            popen.assert_not_called()
            self.assertGreater(h264, 0)
            self.assertLess(h265, h264)
            self.assertLess(downscaled, h264)
            self.assertLess(high_crf, h264)


class _FakePopen:
    last_command = None

    def __init__(self, command, stdout=None, stderr=None, encoding=None, errors=None, creationflags=0):
        type(self).last_command = list(command)
        self.command = list(command)
        self.stdout = io.StringIO("")
        self.stderr = io.StringIO("")
        self.returncode = 0
        Path(command[-1]).write_bytes(b"v" * (2 * 1024 * 1024 + 100))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def poll(self):
        return 0

    def wait(self, timeout=None):
        return 0

    def terminate(self):
        self.returncode = 0

    def kill(self):
        self.returncode = 0


class _CancelDuringCopy:
    def __init__(self, trigger_on=3):
        self.calls = 0
        self.trigger_on = trigger_on

    def is_set(self):
        self.calls += 1
        return self.calls >= self.trigger_on


class VideoUnitTests(unittest.TestCase):
    def test_video_command_omits_attachments(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "input.mkv"
            source.write_bytes(b"fake source")

            with patch("mitia.subprocess.Popen", _FakePopen):
                pack_video("fake-ffmpeg", source, folder, 23, "libx264", None)

            self.assertNotIn("0:t?", _FakePopen.last_command)
            self.assertIn("0:s?", _FakePopen.last_command)
            self.assertTrue((Path(folder) / "input_compressed.mp4").is_file())

    def test_cancel_during_final_video_copy_removes_partial_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "input.mkv"
            source.write_bytes(b"fake source")
            cancel = _CancelDuringCopy(trigger_on=3)

            with patch("mitia.subprocess.Popen", _FakePopen):
                with self.assertRaises(ProcessingCancelled):
                    pack_video(
                        "fake-ffmpeg", source, folder, 23, "libx264", None,
                        cancel=cancel,
                    )

            self.assertEqual(list(Path(folder).glob("*.mp4")), [])


@unittest.skipUnless(ffmpeg(), "FFmpeg required for integration tests")
class VideoIntegrationTests(unittest.TestCase):
    def _make_video(self, source):
        subprocess = __import__("subprocess")
        subprocess.run(
            [
                ffmpeg(), "-nostdin", "-loglevel", "error",
                "-f", "lavfi", "-i", "testsrc=size=321x241:rate=8",
                "-t", "1.0", "-c:v", "ffv1", str(source),
            ],
            check=True,
            capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def _frame_size(self, video, frame):
        subprocess = __import__("subprocess")
        subprocess.run(
            [
                ffmpeg(), "-nostdin", "-loglevel", "error", "-y",
                "-i", str(video), "-frames:v", "1", str(frame),
            ],
            check=True,
            capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        with Image.open(frame) as output:
            return output.size

    def test_unicode_path_odd_dimensions_codecs_and_no_upscale(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "ویدئو نمونه.mkv"
            self._make_video(source)

            for index, (codec, height) in enumerate(
                (("libx264", None), ("libx265", 480)), start=1
            ):
                pack_video(ffmpeg(), source, folder, 28, codec, height)
                videos = sorted(Path(folder).glob("ویدئو نمونه_compressed*.mp4"))
                target = videos[-1]
                frame = Path(folder) / f"frame_{index}.png"
                self.assertEqual(self._frame_size(target, frame), (320, 240))

    def test_progress_callback_reaches_near_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "progress.mkv"
            self._make_video(source)
            values = []

            pack_video(
                ffmpeg(), source, folder, 28, "libx264", None,
                progress_callback=values.append,
            )

            self.assertTrue(values)
            self.assertGreater(max(values), 0.5)
            self.assertTrue((Path(folder) / "progress_compressed.mp4").exists())

    def test_bad_video_leaves_no_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "broken.mp4"
            source.write_bytes(b"not a video")

            with self.assertRaises(RuntimeError):
                pack_video(ffmpeg(), source, folder, 23, "libx264", None)

            self.assertEqual(list(Path(folder).iterdir()), [source])

    def test_cancelled_valid_video_leaves_no_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "cancel.mkv"
            self._make_video(source)
            cancel = threading.Event()
            cancel.set()

            with self.assertRaises(ProcessingCancelled):
                pack_video(ffmpeg(), source, folder, 23, "libx264", None, cancel)

            self.assertEqual(list(Path(folder).glob("cancel_compressed*.mp4")), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
