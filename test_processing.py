import tempfile
import unittest
import subprocess
import threading
from unittest.mock import patch
from pathlib import Path

from PIL import Image

from mitia import pack_image, pack_video, ffmpeg, ProcessingCancelled


class ImageProcessingTests(unittest.TestCase):
    def test_palette_transparency_survives_grayscale(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "palette.png"
            image = Image.new("P", (4, 4), 0)
            image.putpalette([255, 0, 0, 0, 255, 0] + [0] * 762)
            image.putpixel((1, 1), 1)
            image.save(source, transparency=0)
            pack_image(source, folder, 80, "PNG", None, None, True)
            with Image.open(Path(folder) / "palette_compressed.png") as output:
                self.assertEqual(output.convert("RGBA").getpixel((0, 0))[3], 0)
                self.assertEqual(output.convert("RGBA").getpixel((1, 1))[3], 255)

    def test_cmyk_to_png(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "cmyk.jpg"
            Image.new("CMYK", (20, 20), (0, 100, 100, 0)).save(source)
            pack_image(source, folder, 80, "PNG", None, None, False)
            with Image.open(Path(folder) / "cmyk_compressed.png") as output:
                self.assertEqual(output.format, "PNG")

    def test_sixteen_bit_png_to_jpeg(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "depth.png"
            Image.new("I;16", (20, 20), 200).save(source)
            pack_image(source, folder, 80, "JPEG", None, None, False)
            with Image.open(Path(folder) / "depth_compressed.jpg") as output:
                self.assertEqual(output.format, "JPEG")

    def test_failed_save_leaves_no_partial_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "photo.png"
            Image.new("RGB", (20, 20), "red").save(source)
            with patch.object(Image.Image, "save", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    pack_image(source, folder, 80, "JPEG", None, None, False)
            self.assertEqual(list(Path(folder).iterdir()), [source])

    def test_exif_rotation_and_unique_names(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "rotated.jpg"
            exif = Image.Exif()
            exif[274] = 6
            Image.new("RGB", (40, 20), "red").save(source, exif=exif)
            before = source.read_bytes()
            pack_image(source, folder, 80, "JPEG", 10, None, False)
            pack_image(source, folder, 80, "JPEG", None, 10, False)
            with Image.open(Path(folder) / "rotated_compressed.jpg") as output:
                self.assertEqual(output.size, (10, 20))
            with Image.open(Path(folder) / "rotated_compressed_2.jpg") as output:
                self.assertEqual(output.size, (5, 10))
            self.assertEqual(source.read_bytes(), before)


@unittest.skipUnless(ffmpeg(), "Bundled FFmpeg required")
class VideoProcessingTests(unittest.TestCase):
    def test_odd_dimensions_unicode_path_and_codecs(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "ویدئو نمونه.mkv"
            subprocess.run([ffmpeg(), "-nostdin", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=321x241:rate=4", "-t", "0.5", "-c:v", "ffv1", str(source)], check=True, capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            for codec, height, expected in (("libx264", None, (320, 240)), ("libx265", 480, (640, 480))):
                pack_video(ffmpeg(), source, folder, 28, codec, height)
                videos = list(Path(folder).glob("*.mp4"))
                target = max(videos, key=lambda p: p.stat().st_mtime_ns)
                frame = Path(folder) / f"{codec}.png"
                subprocess.run([ffmpeg(), "-nostdin", "-loglevel", "error", "-i", str(target), "-frames:v", "1", str(frame)], check=True, capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                with Image.open(frame) as output:
                    self.assertEqual(output.size, expected)

    def test_bad_video_and_cancellation_leave_no_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "broken.mp4"
            source.write_bytes(b"not a video")
            with self.assertRaises(RuntimeError):
                pack_video(ffmpeg(), source, folder, 23, "libx264", None)
            self.assertEqual(list(Path(folder).iterdir()), [source])
            cancel = threading.Event()
            cancel.set()
            with self.assertRaises(ProcessingCancelled):
                pack_video(ffmpeg(), source, folder, 23, "libx264", None, cancel)
            self.assertEqual(list(Path(folder).iterdir()), [source])


if __name__ == "__main__":
    unittest.main()
