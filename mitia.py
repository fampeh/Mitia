import ctypes
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageOps
from tkinterdnd2 import DND_FILES, TkinterDnD

# ---------------------------------------------------------------------------
# پیش‌نیازها (پیشنهاد pin کردن نسخه‌ها):
#   customtkinter==5.2.2
#   Pillow>=10.0
#   arabic-reshaper>=3.0.0
#   python-bidi>=0.6.0
#   tkinterdnd2>=0.4.0
# فایل‌های همراه برنامه:
#   ffmpeg.exe / ffprobe.exe / Vazirmatn-Regular.ttf / mitia.ico
# ---------------------------------------------------------------------------

NAME = "Mitia"
VERSION = "3.0.0"

IMG = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VID = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".m4v"}

C = {
    "bg": "#0f172a", "panel": "#1e293b", "field": "#020617", "line": "#334155",
    "text": "#f8fafc", "muted": "#94a3b8", "blue": "#3b82f6", "hover": "#2563eb",
    "danger": "#ef4444", "danger_hover": "#dc2626"
}

T = {
    "fa": {
        "image": "تصاویر", "video": "ویدئوها", "lang": "English",
        "output_hint": "خالی بگذارید: ذخیره کنار فایل اصلی",
        "drop": "فایل‌ها را اینجا رها کنید", "add": "افزودن فایل",
        "folder": "افزودن پوشه", "remove": "حذف", "clear": "پاک کردن همه",
        "compression": "میزان فشرده‌سازی", "original": "اصلی", "custom_option": "دلخواه", "pixel": "پیکسل",
        "quality": "کیفیت", "format": "فرمت خروجی", "dimensions": "ابعاد",
        "width": "عرض", "height": "ارتفاع", "gray": "سیاه‌وسفید",
        "output": "پوشه خروجی", "browse": "انتخاب", "start": "شروع فشرده‌سازی",
        "codec": "کدگذاری", "resolution": "وضوح تصویر", "selected": "{count} فایل انتخاب شد",
        "processing": "در حال پردازش: {number} از {total} · {name}",
        "processing_pct": "در حال پردازش: {number} از {total} · {name} · {pct}٪",
        "done": "پایان یافت: {count} فایل · {old} ← {new}",
        "need_files": "لطفاً حداقل یک فایل انتخاب کنید.",
        "need_output": "لطفاً پوشه خروجی را مشخص کنید.",
        "custom": "مقدار ابعاد دلخواه باید یک عدد مثبت باشد.",
        "ffmpeg": "ابزار FFmpeg در این نسخه یافت نشد.",
        "close_busy": "پردازش متوقف شود و برنامه بسته شود؟",
        "errors": "خطا در پردازش",
        "errors_title": "خطاهای پردازش",
        "cancelled": "پردازش لغو شد",
        "cancel": "توقف",
        "close": "بستن",
        "copy": "کپی",
        "save_log": "ذخیره لاگ",
        "estimate_running": "در حال محاسبه حجم تقریبی: {name}",
        "estimate_result": "حجم تقریبی: {new} · حجم اصلی: {old}",
        "estimate_unavailable": "امکان تخمین سریع حجم این فایل وجود ندارد.",
        "already_optimized_count": (
            "با تنظیمات فعلی، امکان کاهش بیشتر حجم {count} فایل وجود نداشت "
            "و خروجی آن‌ها ذخیره نشد. برای حجم کمتر، کیفیت یا ابعاد را کاهش دهید."
        ),
        "all_already_optimized": (
            "با تنظیمات فعلی امکان کاهش بیشتر حجم فایل وجود ندارد. "
            "برای حجم کمتر، کیفیت یا ابعاد را کاهش دهید."
        ),
        "msg_unsupported": "{count} فایل با فرمت پشتیبانی‌نشده نادیده گرفته شد.",
    },
    "en": {
        "image": "Images", "video": "Videos", "lang": "فارسی",
        "output_hint": "Leave blank to save beside each original file",
        "drop": "Drop files here", "add": "Add files",
        "folder": "Add folder", "remove": "Remove", "clear": "Clear all",
        "compression": "Compression level", "original": "Original", "custom_option": "Custom", "pixel": "px",
        "quality": "Quality", "format": "Output format", "dimensions": "Dimensions",
        "width": "Width", "height": "Height", "gray": "Black & white",
        "output": "Output folder", "browse": "Browse", "start": "Start Compress",
        "codec": "Codec", "resolution": "Resolution", "selected": "{count} files selected",
        "processing": "Processing: {number} / {total} · {name}",
        "processing_pct": "Processing: {number} / {total} · {name} · {pct}%",
        "done": "Completed: {count} files · {old} → {new}",
        "need_files": "Please choose at least one file.",
        "need_output": "Please choose an output folder.",
        "custom": "Custom dimension must be a positive number.",
        "ffmpeg": "FFmpeg is unavailable in this build.",
        "close_busy": "Stop processing and close the app?",
        "errors": "Processing errors",
        "errors_title": "Processing errors",
        "cancelled": "Processing cancelled",
        "cancel": "Stop",
        "close": "Close",
        "copy": "Copy",
        "save_log": "Save log",
        "estimate_running": "Estimating size: {name}",
        "estimate_result": "Estimated size: {new} · Original: {old}",
        "estimate_unavailable": "A quick size estimate is unavailable for this file.",
        "already_optimized_count": (
            "{count} file(s) could not be made smaller with the current settings, "
            "so no output was saved. Lower the quality or dimensions to reduce the file size."
        ),
        "all_already_optimized": (
            "The file cannot be made smaller with the current settings. "
            "Lower the quality or dimensions to reduce its size."
        ),
        "msg_unsupported": "{count} unsupported file(s) were ignored.",
    }
}


def asset(name):
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / name


_FONT_LOADED = False


def load_persian_font():
    """بارگذاری فونت Vazirmatn روی هر سه سیستم؛ فقط یک‌بار."""
    global _FONT_LOADED
    if _FONT_LOADED:
        return
    _FONT_LOADED = True

    font = asset("Vazirmatn-Regular.ttf")
    if not font.is_file():
        font = asset("fonts/ttf/Vazirmatn-Regular.ttf")
    if not font.is_file():
        return

    try:
        if sys.platform == "win32":
            ctypes.windll.gdi32.AddFontResourceExW(str(font), 0x10, 0)
        elif sys.platform == "darwin":
            target_dir = Path.home() / "Library/Fonts"
            target_dir.mkdir(parents=True, exist_ok=True)
            dest = target_dir / font.name
            if not dest.exists():
                shutil.copy(font, dest)
        else:  # Linux
            target_dir = Path.home() / ".local/share/fonts"
            target_dir.mkdir(parents=True, exist_ok=True)
            dest = target_dir / font.name
            if not dest.exists():
                shutil.copy(font, dest)
                subprocess.run(["fc-cache", "-f", str(target_dir)],
                               capture_output=True, timeout=10)
    except Exception:
        pass


def ffmpeg():
    p = asset("ffmpeg.exe")
    return str(p) if p.exists() else shutil.which("ffmpeg")


def _find_ffprobe(exe):
    exe_path = Path(exe)
    if exe_path.exists():
        for name in ("ffprobe.exe", "ffprobe"):
            candidate = exe_path.parent / name
            if candidate.exists():
                return str(candidate)
    return shutil.which("ffprobe")


def get_duration(exe, source):
    probe = _find_ffprobe(exe)
    if probe:
        try:
            result = subprocess.run(
                [probe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(source)],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                timeout=15,
            )
            val = result.stdout.strip()
            if val and val != "N/A":
                return float(val)
        except Exception:
            pass
    try:
        result = subprocess.run(
            [exe, "-hide_banner", "-i", str(source)],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            timeout=15,
        )
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", result.stderr)
        if m:
            h, mi, s, cs = m.groups()
            return int(h) * 3600 + int(mi) * 60 + int(s) + int(cs) / 100
    except Exception:
        pass
    return None


def unique(folder, source, ext):
    p = Path(folder) / f"{Path(source).stem}_compressed{ext}"
    n = 2
    while p.exists():
        p = Path(folder) / f"{Path(source).stem}_compressed_{n}{ext}"
        n += 1
    return p


@contextmanager
def output_file(folder, source, ext):
    while True:
        target = unique(folder, source, ext)
        try:
            handle = target.open("xb")
            break
        except FileExistsError:
            continue
    success = False
    try:
        with handle:
            yield handle, target
        success = True
    finally:
        if not success:
            target.unlink(missing_ok=True)


def size(n):
    if n is None:
        return "—"
    return f"{n/1024:.0f} KB" if n < 1048576 else f"{n/1048576:.2f} MB"


class ProcessingCancelled(Exception):
    pass


def pack_image(source, folder, quality, wanted, width, height, gray, cancel=None):
    source = Path(source)

    with Image.open(source) as opened:
        source_fmt = (
            opened.format
            or source.suffix.lstrip(".")
            or "JPEG"
        ).upper()

        if source_fmt in {"JPG", "JPEG"}:
            source_fmt = "JPEG"

        fmt = (wanted or source_fmt).upper()

        if fmt in {"JPG", "JPEG"}:
            fmt = "JPEG"

        ext = {
            "JPEG": ".jpg",
            "WEBP": ".webp",
            "PNG": ".png",
            "BMP": ".bmp",
            "TIFF": ".tiff",
        }.get(fmt, source.suffix) if wanted else source.suffix

        image = ImageOps.exif_transpose(opened)
        image.load()

    if cancel is not None and cancel.is_set():
        raise ProcessingCancelled()

    did_resize = False

    if width or height:
        ow, oh = image.size

        if width and height:
            ratio = min(width / ow, height / oh)
            new = (
                max(1, round(ow * ratio)),
                max(1, round(oh * ratio)),
            )
        else:
            new = (
                (width, max(1, round(oh * width / ow)))
                if width
                else (max(1, round(ow * height / oh)), height)
            )

        if new != image.size:
            image = image.resize(new, Image.Resampling.LANCZOS)
            did_resize = True

    if cancel is not None and cancel.is_set():
        raise ProcessingCancelled()

    if gray:
        has_transparency = (
            "A" in image.getbands()
            or "transparency" in image.info
        )

        if has_transparency:
            rgba = image.convert("RGBA")
            alpha = rgba.getchannel("A")

            image = ImageOps.grayscale(
                rgba.convert("RGB")
            ).convert("RGBA")

            image.putalpha(alpha)

        else:
            image = ImageOps.grayscale(
                image.convert("RGB")
            )

    if fmt == "JPEG" and ("A" in image.getbands() or "transparency" in image.info):
        rgba = image.convert("RGBA")
        bg = Image.new("RGB", rgba.size, "white")
        bg.paste(rgba, mask=rgba.getchannel("A"))
        image = bg
    elif image.mode == "P" and fmt != "PNG":
        image = image.convert("RGB")
    if fmt == "JPEG" and image.mode not in ("L", "RGB", "CMYK"):
        image = image.convert("RGB")
    if fmt in ("WEBP", "PNG", "BMP") and image.mode == "CMYK":
        image = image.convert("RGB")

    if fmt == "JPEG":
        args = {"quality": quality, "optimize": True, "progressive": True}
    elif fmt == "WEBP":
        args = {"quality": quality, "method": 6}
    elif fmt == "PNG":
        level = max(0, min(9, round((100 - quality) / 100 * 9)))
        args = {"compress_level": level}
    else:
        args = {}

    # مقایسه‌ی فرمت واقعی (نه صرفاً None بودن wanted) + ردیابی Resize
    compression_only = (
        fmt == source_fmt
        and not did_resize
        and not gray
    )

    old_size = source.stat().st_size
    with output_file(folder, source, ext) as (handle, target):
        image.save(handle, fmt, **args)
        if cancel is not None and cancel.is_set():
            raise ProcessingCancelled()

    new_size = target.stat().st_size

    if compression_only and new_size >= old_size:
        target.unlink(missing_ok=True)
        # new_size = None چون فایلی ذخیره نشده
        return old_size, None, "already_optimized"

    return old_size, new_size, "compressed"


def estimate_image_size(source, quality, wanted, width, height, gray):
    """تخمین سریع حجم تصویر بدون ساخت خروجی واقعی."""
    source = Path(source)
    old_size = source.stat().st_size

    with Image.open(source) as opened:
        ow, oh = opened.size
        source_fmt = (opened.format or source.suffix.lstrip(".") or "JPEG").upper()

    if source_fmt in {"JPG", "JPEG"}:
        source_fmt = "JPEG"

    fmt = (wanted or source_fmt).upper()
    if fmt in {"JPG", "JPEG"}:
        fmt = "JPEG"

    # دقیقاً منطق ابعاد pack_image را دنبال می‌کنیم.
    tw, th = ow, oh
    if width or height:
        if width and height:
            ratio = min(width / ow, height / oh)
            tw = max(1, round(ow * ratio))
            th = max(1, round(oh * ratio))
        elif width:
            tw = width
            th = max(1, round(oh * width / ow))
        else:
            th = height
            tw = max(1, round(ow * height / oh))

    pixel_ratio = (tw * th) / max(1, ow * oh)

    # ضرایب تجربی‌اند؛ هدف تخمین فوری است، نه پیش‌بینی بایت‌به‌بایت.
    format_factor = {
        "JPEG": 1.00,
        "WEBP": 0.72,
        "PNG": 2.10,
        "BMP": 7.00,
    }
    source_factor = format_factor.get(source_fmt, 1.0)
    target_factor = format_factor.get(fmt, 1.0)

    if fmt in {"JPEG", "WEBP"}:
        q = max(1, min(100, quality))
        quality_factor = 0.28 + 0.72 * (q / 80) ** 1.55
        quality_factor = max(0.18, min(1.65, quality_factor))
    else:
        # PNG lossless است؛ اسلایدر بیشتر زمان/فشرده‌سازی را تغییر می‌دهد.
        quality_factor = 1.0

    same_format_base = 0.78 if fmt in {"JPEG", "WEBP"} else 0.96
    conversion_factor = target_factor / max(0.01, source_factor)
    gray_factor = 0.72 if gray else 1.0

    estimate = old_size * pixel_ratio * conversion_factor * quality_factor * gray_factor
    if fmt == source_fmt:
        estimate *= same_format_base

    return max(1024, int(estimate))


def _quick_video_info(source):
    """اطلاعات سبک و سریع ویدئو برای بهترشدن تخمین؛ بدون encode."""
    exe = ffmpeg()
    probe = _find_ffprobe(exe) if exe else shutil.which("ffprobe")
    if not probe:
        return None, None

    try:
        result = subprocess.run(
            [
                probe, "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=height,codec_name",
                "-of", "json",
                str(source),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            timeout=3,
        )
        data = json.loads(result.stdout or "{}")
        streams = data.get("streams") or []
        if not streams:
            return None, None
        stream = streams[0]
        return stream.get("height"), str(stream.get("codec_name") or "").lower()
    except Exception:
        return None, None


def estimate_video_size(source, crf, codec, height):
    """تخمین فوری حجم ویدئو از متادیتا و تنظیمات؛ هیچ encodeای انجام نمی‌شود."""
    source = Path(source)
    old_size = source.stat().st_size
    source_height, source_codec = _quick_video_info(source)

    # CRF تقریباً هر ۶ واحد می‌تواند bitrate را حدود دو برابر/نصف کند.
    crf_factor = 2 ** ((23 - crf) / 6.0)

    target_codec_factor = 0.74 if codec == "libx265" else 1.0
    source_codec_factor = {
        "hevc": 0.74,
        "h265": 0.74,
        "av1": 0.62,
        "vp9": 0.70,
        "h264": 1.0,
        "avc1": 1.0,
    }.get(source_codec, 1.0)
    codec_factor = target_codec_factor / max(0.1, source_codec_factor)

    resolution_factor = 1.0
    if height and source_height and source_height > height:
        # bitrate تقریباً با تعداد پیکسل تغییر می‌کند، ولی نه کاملاً خطی.
        resolution_factor = (height / source_height) ** 1.7

    # مبنای تجربی برای یک encode معمولی با CRF 23/H.264.
    estimate_ratio = 0.58 * crf_factor * codec_factor * resolution_factor
    estimate_ratio = max(0.05, min(4.0, estimate_ratio))

    return max(1024, int(old_size * estimate_ratio))


def pack_video(exe, source, folder, crf, codec, height, cancel=None, progress_callback=None):
    source = Path(source)

    duration = None
    if progress_callback is not None:
        duration = get_duration(exe, source)

    if height:
        scale = (
            f"scale=w='if(gt(ih,{height}),-2,trunc(iw/2)*2)':"
            f"h='if(gt(ih,{height}),{height},trunc(ih/2)*2)'"
        )
    else:
        scale = "scale=trunc(iw/2)*2:trunc(ih/2)*2"

    # -map 0:t? حذف شد (بعضی MKVها با attachment خراب می‌شدند)
    cmd = [
        exe, "-nostdin", "-hide_banner", "-loglevel", "error", "-n",
        "-progress", "pipe:1",
        "-i", str(source),
        "-map", "0:v:0", "-map", "0:a?", "-map", "0:s?",
        "-c:v", codec, "-preset", "slow", "-crf", str(crf),
        "-vf", scale, "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-c:s", "mov_text",
        "-map_metadata", "0", "-map_chapters", "0",
        "-movflags", "+faststart",
    ]

    with tempfile.TemporaryDirectory(prefix="mitia-") as temp_folder:
        temp = Path(temp_folder) / "video.mp4"
        with subprocess.Popen(
            cmd + [str(temp)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ) as process:
            stderr_lines = []
            cancelled = False

            def read_stderr():
                try:
                    for line in process.stderr:
                        stderr_lines.append(line)
                except Exception:
                    pass

            def read_stdout():
                if progress_callback is None or not duration or duration <= 0:
                    try:
                        for _ in process.stdout:
                            pass
                    except Exception:
                        pass
                    return
                try:
                    for line in process.stdout:
                        if cancel is not None and cancel.is_set():
                            break
                        line = line.strip()
                        if line.startswith("out_time="):
                            t = line.split("=", 1)[1].strip()
                            parts = t.split(":")
                            if len(parts) == 3:
                                try:
                                    seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                                    ratio = min(1.0, seconds / duration)
                                    progress_callback(ratio)
                                except (ValueError, ZeroDivisionError):
                                    pass
                except Exception:
                    pass

            t_err = threading.Thread(target=read_stderr, daemon=True)
            t_out = threading.Thread(target=read_stdout, daemon=True)
            t_err.start()
            t_out.start()

            while process.poll() is None:
                if cancel is not None and cancel.is_set():
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    cancelled = True
                    break
                try:
                    process.wait(timeout=0.1)
                except subprocess.TimeoutExpired:
                    pass

            t_err.join(timeout=2)
            t_out.join(timeout=2)

            if cancelled:
                raise ProcessingCancelled()

            if process.returncode:
                error = "".join(stderr_lines).strip()
                raise RuntimeError(error[-2000:] or "FFmpeg failed")

        if cancel is not None and cancel.is_set():
            raise ProcessingCancelled()

        # کپی نهایی Cancel-aware (chunked، نه shutil.copyfileobj)
        with output_file(folder, source, ".mp4") as (handle, target), temp.open("rb") as encoded:
            while True:
                if cancel is not None and cancel.is_set():
                    raise ProcessingCancelled()

                chunk = encoded.read(1024 * 1024)

                if not chunk:
                    break

                handle.write(chunk)

    return source.stat().st_size, target.stat().st_size, "compressed"


class DnDApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)


class CompactMenu(ctk.CTkOptionMenu):
    """منوی سفارشی مقاوم در برابر تغییرات داخلی CTk."""

    def __init__(self, *args, **kwargs):
        self._user_callback = kwargs.get("command")
        super().__init__(*args, **kwargs)

    def destroy(self):
        for variable, token in getattr(self, "model_traces", []):
            try:
                variable.trace_remove("write", token)
            except tk.TclError:
                pass
        super().destroy()

    def _open_dropdown_menu(self):
        try:
            state = self.cget("state")
        except Exception:
            state = "normal"
        if state == "disabled":
            return

        try:
            values = list(self.cget("values"))
            current = self.get()
        except Exception:
            return super()._open_dropdown_menu()

        try:
            scaling = self._get_widget_scaling()
        except Exception:
            scaling = 1.0

        root = self.winfo_toplevel()
        if getattr(root, "menu_owner", None) is self:
            root.dismiss_menu()
            return
        root.dismiss_menu()
        root.update_idletasks()
        root.menu_owner = self

        popup = tk.Toplevel(root)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.transient(root)
        popup.configure(bg=C["line"])
        popup.attributes("-topmost", True)
        root.menu_popup = popup

        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 4
        desired = int((len(values) * 36 + 12) * scaling)
        height = min(desired, max(72, popup.winfo_screenheight() - y - 8))
        popup.geometry(f"{self.winfo_width()}x{height}+{x}+{y}")

        frame_type = ctk.CTkScrollableFrame if height < desired else ctk.CTkFrame
        body = frame_type(popup, fg_color=C["panel"], corner_radius=6)
        body.pack(fill="both", expand=True, padx=1, pady=1)
        for value in values:
            selected = value == current
            ctk.CTkButton(
                body, text=value, height=32, width=0, corner_radius=5,
                fg_color=C["line"] if selected else "transparent",
                hover_color=C["hover"], text_color=C["text"],
                font=ctk.CTkFont(size=13),
                command=lambda v=value: self.choose(v),
            ).pack(fill="x", padx=5, pady=2)

        popup.bind("<Escape>", lambda _e: root.dismiss_menu())
        popup.deiconify()
        popup.lift()

    def choose(self, value):
        self.set(value)
        self.winfo_toplevel().dismiss_menu(restore_focus=True)
        if self._user_callback:
            self._user_callback(value)


class ErrorDialog(ctk.CTkToplevel):
    def __init__(self, master, title, summary, errors, lang="en"):
        super().__init__(master)
        t = T[lang]
        rtl = lang == "fa"

        def tr(k):
            value = t[k]
            return value if lang == "en" else get_display(arabic_reshaper.reshape(value), base_dir="R")

        self.title(title)
        self.geometry("620x420")
        self.minsize(420, 300)
        self.configure(fg_color=C["bg"])
        self.transient(master)
        self.grab_set()

        header = ctk.CTkLabel(
            self, text=summary, font=ctk.CTkFont(size=14, weight="bold"),
            text_color=C["text"], anchor="e" if rtl else "w",
            justify="right" if rtl else "left",
        )
        header.pack(fill="x", padx=20, pady=(18, 8))

        box = ctk.CTkTextbox(
            self, fg_color=C["field"], text_color=C["text"],
            font=ctk.CTkFont(size=12),
        )
        box.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        box.insert("1.0", "\n".join(errors))
        box.configure(state="disabled")

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 18))

        def copy_all():
            self.clipboard_clear()
            self.clipboard_append("\n".join(errors))

        def save_log():
            path = filedialog.asksaveasfilename(
                parent=self, defaultextension=".txt",
                filetypes=[("Text", "*.txt"), ("All", "*.*")],
            )
            if path:
                Path(path).write_text("\n".join(errors), encoding="utf-8")

        ctk.CTkButton(
            row, text="📋 " + tr("copy"),
            command=copy_all, width=100, height=34,
            fg_color=C["panel"], hover_color=C["line"],
        ).pack(side="right" if rtl else "left")
        ctk.CTkButton(
            row, text="💾 " + tr("save_log"),
            command=save_log, width=120, height=34,
            fg_color=C["panel"], hover_color=C["line"],
        ).pack(side="right" if rtl else "left", padx=8)
        ctk.CTkButton(
            row, text="✕ " + tr("close"),
            command=self.destroy, width=100, height=34,
            fg_color=C["blue"], hover_color=C["hover"],
        ).pack(side="left" if rtl else "right")


class App(DnDApp):
    def __init__(self):
        super().__init__()

        load_persian_font()
        ctk.ThemeManager.theme["CTkFont"]["family"] = "Vazirmatn"
        ctk.set_appearance_mode("dark")

        try:
            self.settings_path = self._settings_path()
        except Exception:
            self.settings_path = None

        self.persistent = self._load_persistent()

        self.lang = self.persistent["lang"]
        self.mode = None
        self.busy = False
        self.estimate_request = 0
        self.files = {"image": [], "video": []}
        self.events = queue.Queue()
        self.out = tk.StringVar(master=self)
        self.saved_settings = self.persistent["settings"]
        self.output_trace = None
        self.cancel_event = threading.Event()
        self.worker = None
        self.dialog_open = False
        self.menu_popup = None
        self.menu_owner = None
        self.bind("<Button-1>", self.dismiss_outside, add="+")
        self.bind("<Escape>", lambda _e: self.dismiss_menu(), add="+")
        self.bind("<Configure>", lambda e: self.dismiss_menu() if e.widget is self else None, add="+")

        self.title(f"{NAME} {VERSION}")
        self.geometry("980x820")
        self.minsize(800, 720)
        self.configure(fg_color=C["bg"])

        try:
            self.iconbitmap(default=str(asset("mitia.ico")))
        except tk.TclError:
            pass

        self.after(100, self.poll)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.home()

    # ---------- تنظیمات پایدار ----------
    def _settings_path(self):
        if sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", Path.home()))
        elif sys.platform == "darwin":
            base = Path.home() / "Library/Application Support"
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        folder = base / "Mitia"
        folder.mkdir(parents=True, exist_ok=True)
        return folder / "settings.json"

    def _load_persistent(self):
        if self.settings_path is None or not self.settings_path.is_file():
            return {"lang": "fa", "settings": {}}
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {"lang": "fa", "settings": {}}
            lang = data.get("lang", "fa")
            if lang not in ("fa", "en"):
                lang = "fa"
            settings = data.get("settings", {})
            if not isinstance(settings, dict):
                settings = {}
            return {"lang": lang, "settings": settings}
        except Exception:
            return {"lang": "fa", "settings": {}}

    def _save_persistent(self):
        if self.settings_path is None:
            return
        try:
            self.settings_path.write_text(
                json.dumps({"lang": self.lang, "settings": self.saved_settings},
                           ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    # ---------- عمومی ----------
    def title_text(self):
        return "میتیا" if self.rtl() else NAME

    def locked(self):
        return self.busy

    def close(self):
        if self.locked():
            if not messagebox.askyesno(
                self.title_text(), T[self.lang]["close_busy"], parent=self
            ):
                return
            self.cancel_event.set()
            self.save_settings()
            self._save_persistent()
            self.withdraw()
            self.wait_for_close()
        else:
            self.save_settings()
            self._save_persistent()
            self.destroy()

    def wait_for_close(self):
        if self.worker is not None and self.worker.is_alive():
            self.after(100, self.wait_for_close)
        else:
            self.destroy()

    def tr(self, k):
        value = T[self.lang][k]
        if self.lang == "en" or k in {"selected", "processing", "done"}:
            return value
        return get_display(arabic_reshaper.reshape(value), base_dir="R")

    def raw(self, k, **values):
        """ترجمه خالص بدون reshape — مناسب برای messagebox ویندوز."""
        return T[self.lang][k].format(**values)

    def msg(self, k, **values):
        value = T[self.lang][k].format(**values)
        if self.lang == "en":
            return value
        return get_display(arabic_reshaper.reshape(value), base_dir="R")

    def rtl(self):
        return self.lang == "fa"

    def side(self):
        return "right" if self.rtl() else "left"

    def anchor(self):
        return "e" if self.rtl() else "w"

    def clear(self):
        self.dismiss_menu()
        if self.output_trace is not None:
            self.out.trace_remove("write", self.output_trace)
            self.output_trace = None
        for w in self.winfo_children():
            w.destroy()

    def dismiss_menu(self, restore_focus=False):
        if self.menu_popup is not None:
            self.menu_popup.destroy()
            if restore_focus:
                self.focus_force()
        self.menu_popup = None
        self.menu_owner = None

    def dismiss_outside(self, event):
        widget = event.widget
        while widget is not None:
            if widget in (self.menu_popup, self.menu_owner):
                return
            widget = getattr(widget, "master", None)
        self.dismiss_menu(restore_focus=True)

    def save_settings(self):
        if self.mode is None:
            return
        try:
            self.out.set(self.output_entry.get())
        except tk.TclError:
            pass
        keys = ("q", "gray", "fmt", "dim", "custom") if self.mode == "image" else ("q", "codec", "res")
        try:
            state = {key: getattr(self, key).get() for key in keys}
        except (AttributeError, tk.TclError):
            return
        if self.mode == "image":
            state["axis"] = "width" if self.axis.get() == self.tr("width") else "height"
        self.saved_settings[self.mode] = state
        self._save_persistent()

    def button(self, p, text, cmd, active=False, width=0, danger=False):
        fg_col = C["danger"] if danger else (C["blue"] if active else C["panel"])
        hov_col = C["danger_hover"] if danger else (C["hover"] if active else C["line"])
        border_col = C["danger"] if danger else (C["blue"] if active else C["line"])

        return ctk.CTkButton(
            p, text=text, command=cmd, width=width, height=40, corner_radius=8,
            fg_color=fg_col, hover_color=hov_col, text_color=C["text"],
            border_width=1, border_color=border_col,
            font=ctk.CTkFont(size=13, weight="bold"),
        )

    def header(self, p):
        name = get_display(arabic_reshaper.reshape("میتیا"), base_dir="R") if self.rtl() else NAME
        self.title(f"{'میتیا' if self.rtl() else NAME} {VERSION}")
        h = ctk.CTkFrame(p, fg_color="transparent")
        h.pack(fill="x", pady=(0, 12))

        logo_frame = ctk.CTkFrame(h, fg_color="transparent")
        logo_frame.pack(side=self.side())
        ctk.CTkLabel(logo_frame, text=name, font=ctk.CTkFont(size=28, weight="bold"), text_color=C["text"]).pack(side=self.side())
        ctk.CTkLabel(logo_frame, text=f"v{VERSION}", text_color=C["muted"], font=ctk.CTkFont(size=12)).pack(side=self.side(), padx=8, pady=(10, 0))

        controls = ctk.CTkFrame(h, fg_color="transparent")
        controls.pack(side="left" if self.rtl() else "right")

        self.button(controls, "🌐 " + self.tr("lang"), self.change_lang, width=100).pack(side=self.side())

    def home(self):
        self.mode = None
        self.clear()

        root = ctk.CTkFrame(self, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=50, pady=40)
        self.header(root)

        holder = ctk.CTkFrame(root, fg_color="transparent")
        holder.pack(expand=True)

        modes = (("video", "▶"), ("image", "▧")) if self.rtl() else (("image", "▧"), ("video", "▶"))
        for mode, icon in modes:
            self.card(holder, mode, icon)

    def card(self, p, mode, icon):
        card = ctk.CTkFrame(p, width=240, height=260, fg_color=C["panel"], corner_radius=20, border_width=1, border_color=C["line"], cursor="hand2")
        card.pack(side="left", padx=20)
        card.pack_propagate(False)

        iconw = ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=56), text_color=C["blue"])
        iconw.pack(expand=True, pady=(40, 0))

        title = ctk.CTkLabel(card, text=self.tr(mode), font=ctk.CTkFont(size=20, weight="bold"), text_color=C["text"])
        title.pack(expand=True, pady=(0, 40))

        for w in (card, iconw, title):
            w.bind("<Enter>", lambda _e: card.configure(fg_color=C["line"], border_color=C["blue"]))
            w.bind("<Leave>", lambda _e: card.configure(fg_color=C["panel"], border_color=C["line"]))
            w.bind("<Button-1>", lambda _e: self.pick(mode))

    def change_lang(self):
        if self.locked():
            return
        self.save_settings()
        self.lang = "en" if self.rtl() else "fa"
        self._save_persistent()
        self.home() if self.mode is None else self.workspace()

    def pick(self, mode):
        if self.locked() or self.mode == mode:
            return
        self.save_settings()
        self.mode = mode
        self.workspace()

    def workspace(self):
        self.estimate_request += 1
        self.clear()

        root = ctk.CTkFrame(self, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=40, pady=20)
        self.header(root)

        tabs = ctk.CTkFrame(root, fg_color="transparent")
        tabs.pack(fill="x", pady=(0, 16))

        modes = ("video", "image") if self.rtl() else ("image", "video")
        for m in modes:
            self.button(tabs, self.tr(m), lambda v=m: self.pick(v), m == self.mode, 140).pack(side=self.side(), padx=5)

        self.status = tk.StringVar(value=self.msg("selected", count=len(self.files[self.mode])))

        bottom = ctk.CTkFrame(root, fg_color="transparent")
        bottom.pack(fill="x", side="bottom", pady=(15, 0))

        self.bar = ctk.CTkProgressBar(bottom, height=10, corner_radius=5, progress_color=C["blue"], fg_color=C["line"])
        self.bar.set(0)
        self.bar.pack(fill="x", pady=(0, 10))

        status_frame = ctk.CTkFrame(bottom, fg_color="transparent")
        status_frame.pack(fill="x")

        ctk.CTkLabel(status_frame, textvariable=self.status, font=ctk.CTkFont(size=13), text_color=C["muted"], anchor=self.anchor()).pack(side=self.side(), fill="x", expand=True)

        self.start_button = ctk.CTkButton(
            status_frame, text="⚡ " + self.tr("start"), command=self.start,
            width=200, height=45, corner_radius=8, font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=C["blue"], hover_color=C["hover"], text_color="#ffffff",
        )
        self.start_button.pack(side="right" if self.rtl() else "left")

        self.cancel_button = ctk.CTkButton(
            status_frame, text="⏹ " + self.tr("cancel"), command=self.cancel,
            width=120, height=45, corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=C["danger"], hover_color=C["danger_hover"],
            text_color="#ffffff",
            text_color_disabled="#cbd5e1",
            state="disabled",
        )
        self.cancel_button.pack(side="right" if self.rtl() else "left", padx=(8, 0))

        self.settings_ui(root)
        self.dropzone(root)

    def dropzone(self, p):
        card = ctk.CTkFrame(p, fg_color=C["panel"], corner_radius=12, border_width=1, border_color=C["line"], height=210)
        card.pack(fill="both", expand=True, pady=(0, 15))
        card.pack_propagate(False)

        top_bar = ctk.CTkFrame(card, fg_color="transparent")
        top_bar.pack(fill="x", padx=16, pady=12)
        ctk.CTkLabel(top_bar, text=self.tr("drop"), font=ctk.CTkFont(size=14, weight="bold"), text_color=C["muted"], anchor=self.anchor()).pack(side=self.side())

        self.list_area = tk.Frame(card, bg=C["field"], highlightthickness=0)
        self.list_area.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        self.list = tk.Listbox(
            self.list_area, selectmode=tk.EXTENDED, justify="right" if self.rtl() else "left",
            bg=C["field"], fg=C["text"], selectbackground=C["blue"],
            relief="flat", highlightthickness=0, borderwidth=0, font=("Vazirmatn", 12),
        )
        self.list.pack(fill="both", expand=True, padx=10, pady=10)
        self.list.drop_target_register(DND_FILES)
        self.list.dnd_bind("<<Drop>>", self.drop)
        self.list.bind("<Double-Button-1>", lambda _e: self.add())
        self.list.bind("<<ListboxSelect>>", self.estimate_selected, add="+")

        self.drop_hint = tk.Label(self.list_area, text="+", bg=C["field"], fg=C["blue"], font=("Vazirmatn", 60, "bold"), cursor="hand2")
        self.drop_hint.drop_target_register(DND_FILES)
        self.drop_hint.dnd_bind("<<Drop>>", self.drop)
        self.drop_hint.bind("<Button-1>", lambda _e: self.add())

        self.refresh()

        actions = (("clear", self.clear_files), ("remove", self.remove), ("folder", self.folder), ("add", self.add)) if self.rtl() else (("add", self.add), ("folder", self.folder), ("remove", self.remove), ("clear", self.clear_files))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", side="bottom", before=self.list_area, padx=16, pady=(0, 12))

        for k, fn in actions:
            is_danger = k in ["clear", "remove"]
            self.button(row, self.tr(k), fn, width=100, danger=is_danger).pack(side=self.side(), padx=5)

    def settings_ui(self, p):
        panel = ctk.CTkFrame(p, fg_color=C["panel"], corner_radius=12, border_width=1, border_color=C["line"])
        panel.pack(fill="x", side="bottom", pady=(0, 5))
        columns = 4 if self.mode == "image" else 3
        panel.grid_columnconfigure(tuple(range(columns)), weight=1, uniform="settings")
        if self.mode == "image":
            panel.grid_columnconfigure(tuple(range(columns)), uniform="")
            panel.grid_columnconfigure(1 if self.rtl() else 2, weight=2)
            panel.grid_columnconfigure(0 if self.rtl() else 3, weight=0)

        self.q = tk.IntVar(value=80 if self.mode == "image" else 23)
        self.gray = tk.BooleanVar()

        self.group(panel, columns - 1 if self.rtl() else 0, 0, self.tr("quality") if self.mode == "image" else self.tr("compression"), self.quality)

        if self.mode == "image":
            self.fmt = tk.StringVar(value="Original")
            self.dim = tk.StringVar(value="Original")
            self.axis = tk.StringVar(value=self.tr("width"))
            self.custom = tk.StringVar()

            self.group(panel, 2 if self.rtl() else 1, 0, self.tr("format"), lambda p: self.menu(p, self.fmt, ["Original", "JPEG", "WebP"], width=100))
            self.group(panel, 1 if self.rtl() else 2, 0, self.tr("dimensions"), self.dimension)
            self.group(panel, 0 if self.rtl() else 3, 0, "", self.grayscale)
        else:
            self.codec = tk.StringVar(value="H.264 / AVC")
            self.res = tk.StringVar(value="Original")

            self.group(panel, 1, 0, self.tr("codec"), lambda p: self.menu(p, self.codec, ["H.264 / AVC", "H.265 / HEVC"]))
            self.group(panel, 0 if self.rtl() else 2, 0, self.tr("resolution"), lambda p: self.menu(p, self.res, ["Original", "1080p", "720p", "480p"]))

        out_frame = ctk.CTkFrame(panel, fg_color="transparent")
        out_frame.grid(row=3, column=0, columnspan=columns, sticky="ew", padx=25, pady=(10, 20))
        out_frame.grid_columnconfigure(1, weight=1)

        a, b = (2, 0) if self.rtl() else (0, 2)

        ctk.CTkLabel(out_frame, text=self.tr("output"), width=90, anchor=self.anchor(), font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=a, padx=(0, 15))
        self.output_entry = ctk.CTkEntry(out_frame, placeholder_text=self.tr("output_hint"), justify="left", height=40, fg_color=C["field"], border_color=C["line"], corner_radius=6, text_color=C["text"], font=ctk.CTkFont(size=13))
        entry = self.output_entry

        def sync_output(*_):
            if entry.winfo_exists() and entry.get() != self.out.get():
                entry.delete(0, tk.END)
                if self.out.get():
                    entry.insert(0, self.out.get())

        self.output_trace = self.out.trace_add("write", sync_output)
        entry.bind("<KeyRelease>", lambda _e: self.out.set(entry.get()), add="+")
        entry.bind("<FocusOut>", lambda _e: self.out.set(entry.get()), add="+")
        sync_output()
        self.output_entry.grid(row=0, column=1, sticky="ew", padx=10)
        self.output_browse_button = self.button(out_frame, self.tr("browse"), self.choose_output, width=110)
        self.output_browse_button.grid(row=0, column=b)

        state = self.saved_settings.get(self.mode, {})
        for key, value in state.items():
            try:
                getattr(self, key).set(self.tr(value) if key == "axis" else value)
            except (AttributeError, tk.TclError):
                pass
        if self.mode == "image":
            self.custom_toggle(self.dim.get())

    def group(self, p, col, row, label, build, span=1):
        g = ctk.CTkFrame(p, fg_color="transparent")
        padding = (25, 6) if self.rtl() else (6, 25)
        g.grid(row=row, column=col, columnspan=span, sticky="ew", padx=padding if label == "" else 6, pady=12)
        g.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(g, text=label, anchor=self.anchor(), font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="ew", pady=(0, 6))
        sticky = self.anchor()
        if label in (self.tr("quality"), self.tr("compression")):
            sticky = "ew"
        elif label == "":
            sticky = "w" if self.rtl() else "e"
        build(g).grid(row=1, column=0, sticky=sticky)

    def menu(self, p, var, values, width=120, command=None):
        labels = {"Original": self.tr("original"), "Custom": self.tr("custom_option")}
        reverse = {labels.get(v, v): v for v in values}
        display = tk.StringVar(master=self, value=labels.get(var.get(), var.get()))
        display_trace = display.trace_add("write", lambda *_: var.set(reverse.get(display.get(), display.get())) if var.get() != reverse.get(display.get(), display.get()) else None)
        model_trace = var.trace_add("write", lambda *_: display.set(labels.get(var.get(), var.get())) if display.get() != labels.get(var.get(), var.get()) else None)

        menu = CompactMenu(
            p,
            variable=display,
            values=[labels.get(v, v) for v in values],
            width=width, dynamic_resizing=False, height=36, corner_radius=6,
            fg_color=C["field"], button_color=C["line"], button_hover_color=C["blue"], text_color=C["text"],
            anchor="center", dropdown_fg_color=C["panel"], dropdown_hover_color=C["line"],
            dropdown_font=ctk.CTkFont(family="Vazirmatn", size=13),
            font=ctk.CTkFont(size=13),
            command=command,
        )
        menu.model_traces = [(display, display_trace), (var, model_trace)]
        return menu

    def grayscale(self, p):
        holder = ctk.CTkFrame(p, fg_color="transparent", height=36, width=100)
        holder.grid_propagate(False)
        self.gray_checkbox = ctk.CTkCheckBox(holder, text=self.tr("gray"), variable=self.gray, width=100, checkbox_width=20, checkbox_height=20, fg_color=C["blue"], hover_color=C["hover"], text_color=C["text"], font=ctk.CTkFont(size=12))
        self.gray_checkbox.place(relx=0 if self.rtl() else 1, rely=.5, anchor="w" if self.rtl() else "e")
        return holder

    def quality(self, p):
        f = ctk.CTkFrame(p, fg_color="transparent")
        f.grid_columnconfigure(0, weight=1)

        value = ctk.CTkLabel(f, textvariable=self.q, width=32, font=ctk.CTkFont(size=13, weight="bold"), text_color=C["blue"])
        slider = ctk.CTkSlider(
            f, from_=1 if self.mode == "image" else 0, to=100 if self.mode == "image" else 51,
            variable=self.q, number_of_steps=99 if self.mode == "image" else 51, width=80 if self.mode == "image" else 120,
            progress_color=C["blue"], button_color=C["text"], button_hover_color=C["blue"],
        )

        if self.rtl():
            value.grid(row=0, column=0)
            slider.grid(row=0, column=1, sticky="ew", padx=(10, 0))
            f.grid_columnconfigure(1, weight=1)
        else:
            slider.grid(row=0, column=0, sticky="ew", padx=(0, 10))
            value.grid(row=0, column=1)
        return f

    def dimension(self, p):
        f = ctk.CTkFrame(p, fg_color="transparent")

        menu = self.menu(
            f, self.dim,
            ["Original", "1920 × 1080", "1280 × 720", "800 × 600", "Custom"],
            width=110,
            command=lambda _value: self.custom_toggle(self.dim.get()),
        )
        self.dimension_menu = menu
        menu.grid(row=0, column=1 if self.rtl() else 0)

        slot = ctk.CTkFrame(f, fg_color="transparent", width=221, height=36)
        slot.grid(row=0, column=0 if self.rtl() else 1, padx=4)
        slot.grid_propagate(False)
        slot.grid_columnconfigure(0, weight=1)
        self.custombox = ctk.CTkFrame(slot, fg_color=C["field"], corner_radius=6, border_width=1, border_color=C["line"])
        self.custombox.grid(row=0, column=0, sticky="ew")
        self.custombox.grid_columnconfigure(1, weight=1)

        axis = self.menu(self.custombox, self.axis, [self.tr("width"), self.tr("height")], width=88)
        numeric = (self.register(lambda v: v == "" or v.isdecimal()), "%P")
        entry = ctk.CTkEntry(
            self.custombox, textvariable=self.custom, validate="key",
            validatecommand=numeric, justify="center", width=72, height=36,
            fg_color=C["bg"], border_width=1, border_color=C["blue"],
            text_color=C["text"],
        )
        self.custom_entry = entry

        entry._entry.bind(
            "<Control-KeyPress>",
            self._custom_ctrl_shortcut,
            add="+",
        )

        px = ctk.CTkLabel(self.custombox, text=self.tr("pixel"), width=45, text_color=C["muted"], font=ctk.CTkFont(size=13))

        if self.rtl():
            axis.grid(row=0, column=2, padx=(0, 4))
            entry.grid(row=0, column=1, sticky="ew")
            px.grid(row=0, column=0, padx=(4, 0))
        else:
            axis.grid(row=0, column=0, padx=(0, 4))
            entry.grid(row=0, column=1, sticky="ew")
            px.grid(row=0, column=2, padx=(4, 0))

        self.custombox.grid_remove()
        return f

    def _custom_ctrl_shortcut(self, event):
        is_ctrl_a = (
            str(event.keysym).lower() == "a"
            or (sys.platform == "win32" and event.keycode == 65)
        )

        if is_ctrl_a:
            event.widget.select_range(0, tk.END)
            event.widget.icursor(tk.END)
            return "break"

    def custom_toggle(self, value=None):
        target = value if value is not None else self.dim.get()
        if target == "Custom":
            self.custombox.grid()
        else:
            self.custombox.grid_remove()

    def ext(self):
        return IMG if self.mode == "image" else VID

    def other_ext(self):
        return VID if self.mode == "image" else IMG

    def add(self):
        if self.locked() or self.dialog_open:
            return
        self.dialog_open = True
        try:
            title = "انتخاب فایل" if self.rtl() else "Select files"
            media_patterns = " ".join(f"*{x}" for x in sorted(IMG | VID))
            types = [
                ("تصاویر و ویدئوها" if self.rtl() else "Media", media_patterns),
                ("همهٔ فایل‌ها" if self.rtl() else "All files", "*.*"),
            ]
            self.add_paths(filedialog.askopenfilenames(parent=self, title=title, filetypes=types))
        finally:
            self.dialog_open = False

    def folder(self):
        if self.locked():
            return
        p = filedialog.askdirectory(parent=self)
        if p:
            self.add_paths([p])

    def drop(self, e):
        self.add_paths(self.tk.splitlist(e.data))

    def add_paths(self, paths):
        if self.locked():
            return

        current_mode = self.mode
        other_mode = "video" if current_mode == "image" else "image"

        known = {
            "image": {os.path.normcase(x) for x in self.files["image"]},
            "video": {os.path.normcase(x) for x in self.files["video"]},
        }
        added = {"image": 0, "video": 0}
        unsupported = 0

        try:
            for path in paths:
                source = Path(path).resolve()
                candidates = source.iterdir() if source.is_dir() else [source]

                for candidate in candidates:
                    if not candidate.is_file():
                        continue

                    suffix = candidate.suffix.lower()
                    if suffix in IMG:
                        target_mode = "image"
                    elif suffix in VID:
                        target_mode = "video"
                    else:
                        unsupported += 1
                        continue

                    p = str(candidate)
                    norm = os.path.normcase(p)
                    if norm in known[target_mode]:
                        continue

                    self.files[target_mode].append(p)
                    known[target_mode].add(norm)
                    added[target_mode] += 1

        except OSError as error:
            messagebox.showwarning(self.title_text(), str(error), parent=self)

        # اگر کاربر فقط فایل نوع دیگر را انداخت، خودکار به همان بخش برو.
        if added[current_mode] == 0 and added[other_mode] > 0:
            self.save_settings()
            self.mode = other_mode
            self.workspace()
        else:
            self.refresh()

        # عکس/ویدئو دیگر «نوع اشتباه» نیستند؛ فقط فرمت ناشناخته هشدار می‌گیرد.
        if unsupported:
            messagebox.showwarning(
                self.title_text(),
                self.raw("msg_unsupported", count=unsupported),
                parent=self,
            )

    def refresh(self):
        self.estimate_request += 1
        if not hasattr(self, "list"):
            return
        self.list.delete(0, tk.END)
        for p in self.files[self.mode]:
            self.list.insert(tk.END, Path(p).name)

        if self.files[self.mode]:
            self.drop_hint.place_forget()
        else:
            self.drop_hint.place(relx=.5, rely=.5, anchor="center")

        self.status.set(self.msg("selected", count=len(self.files[self.mode])))

    def remove(self):
        if self.locked():
            return
        chosen = set(self.list.curselection())
        self.files[self.mode][:] = [p for i, p in enumerate(self.files[self.mode]) if i not in chosen]
        self.refresh()

    def clear_files(self):
        if self.locked():
            return
        self.files[self.mode].clear()
        self.refresh()

    def choose_output(self):
        if self.locked():
            return
        p = filedialog.askdirectory(parent=self)
        if p:
            self.out.set(p)

    def opts(self):
        if not self.files[self.mode]:
            raise ValueError(self.raw("need_files"))
        if self.out.get().strip() and not Path(self.out.get().strip()).is_dir():
            raise ValueError(self.raw("need_output"))

        if self.mode == "video":
            return (
                ffmpeg(),
                round(self.q.get()),
                "libx265" if self.codec.get().startswith("H.265") else "libx264",
                {"Original": None, "1080p": 1080, "720p": 720, "480p": 480}[self.res.get()],
            )

        d = {"Original": (None, None), "1920 × 1080": (1920, 1080), "1280 × 720": (1280, 720), "800 × 600": (800, 600)}
        if self.dim.get() == "Custom":
            try:
                raw = self.custom.get().translate(str.maketrans(
                    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
                v = int(raw)
                if v <= 0:
                    raise ValueError()
            except (ValueError, AssertionError):
                raise ValueError(self.raw("custom"))
            d["Custom"] = (v, None) if self.axis.get() == self.tr("width") else (None, v)

        w, h = d[self.dim.get()]
        return round(self.q.get()), None if self.fmt.get() == "Original" else self.fmt.get().upper(), w, h, self.gray.get()

    def start(self):
        if self.locked():
            return
        self.out.set(self.output_entry.get())
        try:
            o = self.opts()
        except ValueError as e:
            messagebox.showwarning(self.title_text(), str(e), parent=self)
            return

        if self.mode == "video" and not o[0]:
            messagebox.showwarning(self.title_text(), self.raw("ffmpeg"), parent=self)
            return

        self.estimate_request += 1
        self.busy = True
        self.cancel_event.clear()
        self.dismiss_menu()
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.bar.set(0)
        self.worker = threading.Thread(
            target=self.work,
            args=(self.mode, list(self.files[self.mode]), self.out.get().strip(), o),
            daemon=True,
        )
        self.worker.start()

    def estimate_selected(self, _event=None):
        if self.busy:
            return

        selected = self.list.curselection()
        if not selected:
            return

        index = selected[0]
        if index >= len(self.files[self.mode]):
            return

        path = self.files[self.mode][index]
        mode = self.mode

        try:
            if mode == "image":
                d = {
                    "Original": (None, None),
                    "1920 × 1080": (1920, 1080),
                    "1280 × 720": (1280, 720),
                    "800 × 600": (800, 600),
                }
                if self.dim.get() == "Custom":
                    raw = self.custom.get().translate(str.maketrans(
                        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
                    value = int(raw)
                    if value <= 0:
                        raise ValueError()
                    d["Custom"] = (
                        (value, None)
                        if self.axis.get() == self.tr("width")
                        else (None, value)
                    )

                width, height = d[self.dim.get()]
                options = (
                    round(self.q.get()),
                    None if self.fmt.get() == "Original" else self.fmt.get().upper(),
                    width,
                    height,
                    self.gray.get(),
                )
            else:
                options = (
                    round(self.q.get()),
                    "libx265" if self.codec.get().startswith("H.265") else "libx264",
                    {"Original": None, "1080p": 1080, "720p": 720, "480p": 480}[self.res.get()],
                )
        except (ValueError, KeyError, tk.TclError):
            self.status.set(self.tr("estimate_unavailable"))
            return

        self.estimate_request += 1
        request_id = self.estimate_request
        self.status.set(self.msg("estimate_running", name=Path(path).name))

        threading.Thread(
            target=self._estimate_worker,
            args=(request_id, mode, path, options),
            daemon=True,
        ).start()

    def _estimate_worker(self, request_id, mode, path, options):
        try:
            old_size = Path(path).stat().st_size
            if mode == "image":
                estimated = estimate_image_size(path, *options)
            else:
                estimated = estimate_video_size(path, *options)
            self.events.put(("est", request_id, old_size, estimated))
        except Exception:
            self.events.put(("est_err", request_id))

    def cancel(self):
        if not self.locked():
            return
        self.cancel_event.set()
        self.cancel_button.configure(state="disabled")
        self.bar.set(0)
        if self.busy:
            self.status.set(self.tr("cancelled"))

    def work(self, mode, files, folder, o):
        old = new = ok = 0
        skipped_optimized = 0
        errors = []
        total = len(files)

        def process_one(p):
            if self.cancel_event.is_set():
                raise ProcessingCancelled()
            destination = folder or str(Path(p).parent)
            if mode == "image":
                return pack_image(p, destination, *o, cancel=self.cancel_event)
            return pack_video(
                o[0], p, destination, *o[1:],
                cancel=self.cancel_event,
                progress_callback=None,
            )

        if mode == "image" and total > 1:
            workers = min(4, max(1, (os.cpu_count() or 2) - 1))
            pool = ThreadPoolExecutor(max_workers=workers)
            done = 0
            try:
                future_map = {pool.submit(process_one, p): p for p in files}
                for fut in as_completed(future_map):
                    if self.cancel_event.is_set():
                        break
                    p = future_map[fut]
                    try:
                        a, b, status = fut.result()
                        if status == "already_optimized":
                            skipped_optimized += 1
                        else:
                            old += a
                            new += b
                            ok += 1
                    except ProcessingCancelled:
                        break
                    except Exception as e:
                        errors.append(f"{Path(p).name}: {e}")
                    done += 1
                    self.events.put(("p", done, total, Path(p).name))
            finally:
                pool.shutdown(wait=True, cancel_futures=True)

            if self.cancel_event.is_set():
                self.events.put(("c",))
                return
        else:
            for i, p in enumerate(files, 1):
                if self.cancel_event.is_set():
                    self.events.put(("c",))
                    return
                try:
                    destination = folder or str(Path(p).parent)
                    if mode == "image":
                        a, b, status = pack_image(p, destination, *o, cancel=self.cancel_event)
                    else:
                        def progress_cb(ratio, _i=i, _name=Path(p).name, _total=total):
                            overall = ((_i - 1) + ratio) / _total
                            self.events.put(("vp", _i, _total, _name, ratio, overall))

                        a, b, status = pack_video(
                            o[0], p, destination, *o[1:],
                            cancel=self.cancel_event,
                            progress_callback=progress_cb,
                        )

                    if status == "already_optimized":
                        skipped_optimized += 1
                    else:
                        old += a
                        new += b
                        ok += 1
                except ProcessingCancelled:
                    self.events.put(("c",))
                    return
                except Exception as e:
                    errors.append(f"{Path(p).name}: {e}")

                self.events.put(("p", i, total, Path(p).name))

        self.events.put(("d", ok, old, new, errors, skipped_optimized))

    def poll(self):
        try:
            while True:
                e = self.events.get_nowait()

                if e[0] == "p":
                    _, n, total, name = e
                    self.bar.set(n / total)
                    self.status.set(self.msg("processing", number=n, total=total, name=name))

                elif e[0] == "vp":
                    _, n, total, name, ratio, overall = e
                    self.bar.set(overall)
                    self.status.set(self.msg(
                        "processing_pct",
                        number=n, total=total, name=name,
                        pct=int(ratio * 100),
                    ))

                elif e[0] == "c":
                    self.busy = False
                    self.start_button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
                    self.bar.set(0)
                    self.status.set(self.tr("cancelled"))

                elif e[0] == "est":
                    _, request_id, old_size, estimated = e
                    if request_id == self.estimate_request and not self.busy:
                        self.status.set(self.msg(
                            "estimate_result",
                            old=size(old_size),
                            new=size(estimated),
                        ))

                elif e[0] == "est_err":
                    _, request_id = e
                    if request_id == self.estimate_request and not self.busy:
                        self.status.set(self.tr("estimate_unavailable"))

                elif e[0] == "d":
                    _, n, old, new, errors, skipped = e
                    self.busy = False
                    self.start_button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")

                    if n == 0 and skipped > 0:
                        report = self.msg("all_already_optimized", count=skipped)
                    else:
                        report = self.msg("done", count=n, old=size(old), new=size(new))
                        if skipped:
                            report = report + "\n" + self.msg("already_optimized_count", count=skipped)
                    self.status.set(report)

                    if errors:
                        ErrorDialog(
                            self,
                            self.raw("errors_title"),
                            report,
                            errors,
                            lang=self.lang,
                        )
        except queue.Empty:
            pass
        except Exception as err:
            print("poll error:", err, file=sys.stderr)
        finally:
            interval = 100 if self.locked() else 250
            self.after(interval, self.poll)


if __name__ == "__main__":
    app = App()
    app.mainloop()