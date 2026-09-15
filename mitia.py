import ctypes
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import tempfile
from contextlib import contextmanager
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageOps
from tkinterdnd2 import DND_FILES, TkinterDnD

NAME = "Mitia"
VERSION = "2.9.8"

IMG = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VID = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".m4v"}

C = {
    "bg": "#0f172a", "panel": "#1e293b", "field": "#020617", "line": "#334155",
    "text": "#f8fafc", "muted": "#94a3b8", "blue": "#3b82f6", "hover": "#2563eb",
    "danger": "#ef4444", "danger_hover": "#dc2626"
}

T = {
    "fa": {
        "image": "تصاویر",
        "video": "ویدئوها",
        "lang": "English",

        "output_hint": "خالی بگذارید: ذخیره کنار فایل اصلی",
        "drop": "فایل‌ها را اینجا رها کنید",
        "add": "افزودن فایل",
        "folder": "افزودن پوشه",
        "remove": "حذف",
        "clear": "پاک کردن همه",

        "compression": "میزان فشرده‌سازی",
        "original": "اصلی",
        "custom_option": "دلخواه",
        "pixel": "پیکسل",

        "quality": "کیفیت",
        "format": "فرمت خروجی",
        "dimensions": "ابعاد",
        "width": "عرض",
        "height": "ارتفاع",
        "gray": "سیاه‌وسفید",

        "output": "پوشه خروجی",
        "browse": "انتخاب",
        "start": "شروع فشرده‌سازی",

        "codec": "کدگذاری",
        "resolution": "وضوح تصویر",

        "selected": "{count} فایل انتخاب شد",
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

        "already_optimized_count": (
            "با تنظیمات فعلی، امکان کاهش بیشتر حجم {count} فایل وجود نداشت "
            "و خروجی آن‌ها ذخیره نشد. برای حجم کمتر، کیفیت یا ابعاد را کاهش دهید."
        ),

        "all_already_optimized": (
            "با تنظیمات فعلی امکان کاهش بیشتر حجم فایل وجود ندارد. "
            "برای حجم کمتر، کیفیت یا ابعاد را کاهش دهید."
        ),

        "msg_wrong_media_image": (
            "{count} فایل ویدئویی اضافه نشد. "
            "لطفاً آن را در بخش ویدئوها اضافه کنید."
        ),

        "msg_wrong_media_video": (
            "{count} فایل تصویری اضافه نشد. "
            "لطفاً آن را در بخش تصاویر اضافه کنید."
        ),

        "msg_unsupported": (
            "{count} فایل با فرمت پشتیبانی‌نشده نادیده گرفته شد."
        ),
    },

    "en": {
        "image": "Images",
        "video": "Videos",
        "lang": "فارسی",

        "output_hint": "Leave blank to save beside each original file",
        "drop": "Drop files here",
        "add": "Add files",
        "folder": "Add folder",
        "remove": "Remove",
        "clear": "Clear all",

        "compression": "Compression level",
        "original": "Original",
        "custom_option": "Custom",
        "pixel": "px",

        "quality": "Quality",
        "format": "Output format",
        "dimensions": "Dimensions",
        "width": "Width",
        "height": "Height",
        "gray": "Black & white",

        "output": "Output folder",
        "browse": "Browse",
        "start": "Start Compress",

        "codec": "Codec",
        "resolution": "Resolution",

        "selected": "{count} files selected",
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

        "already_optimized_count": (
            "{count} file(s) could not be made smaller with the current settings, "
            "so no output was saved. Lower the quality or dimensions to reduce the file size."
        ),

        "all_already_optimized": (
            "The file cannot be made smaller with the current settings. "
            "Lower the quality or dimensions to reduce its size."
        ),

        "msg_wrong_media_image": (
            "{count} video file(s) were not added. "
            "Please add them from the Videos section."
        ),

        "msg_wrong_media_video": (
            "{count} image file(s) were not added. "
            "Please add them from the Images section."
        ),

        "msg_unsupported": (
            "{count} unsupported file(s) were ignored."
        ),
    }
}


def asset(name):
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / name


def load_persian_font():
    font = asset("Vazirmatn-Regular.ttf")
    if not font.is_file():
        font = asset("fonts/ttf/Vazirmatn-Regular.ttf")
    if font.is_file() and sys.platform == "win32":
        ctypes.windll.gdi32.AddFontResourceExW(str(font), 0x10, 0)


def ffmpeg():
    p = asset("ffmpeg.exe")
    return str(p) if p.exists() else shutil.which("ffmpeg")


def _find_ffprobe(exe):
    """ffprobe را کنار ffmpeg یا در PATH پیدا می‌کند."""
    exe_path = Path(exe)
    if exe_path.exists():
        for name in ("ffprobe.exe", "ffprobe"):
            candidate = exe_path.parent / name
            if candidate.exists():
                return str(candidate)
    return shutil.which("ffprobe")


def get_duration(exe, source):
    """مدت ویدئو به ثانیه. اول با ffprobe، در نبودش با ffmpeg -i."""
    # مسیر ۱: ffprobe
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

    # مسیر ۲ (fallback): استخراج از stderr در ffmpeg -i
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
    return f"{n/1024:.0f} KB" if n < 1048576 else f"{n/1048576:.2f} MB"


class ProcessingCancelled(Exception):
    pass


def pack_image(source, folder, quality, wanted, width, height, gray, cancel=None):
    source = Path(source)
    with Image.open(source) as opened:
        fmt = wanted or (opened.format or "JPEG").upper()
        fmt = "JPEG" if fmt == "JPG" else fmt
        ext = {"JPEG": ".jpg", "WEBP": ".webp", "PNG": ".png", "BMP": ".bmp", "TIFF": ".tiff"}.get(fmt, source.suffix) if wanted else source.suffix
        image = ImageOps.exif_transpose(opened)
        image.load()

    if cancel is not None and cancel.is_set():
        raise ProcessingCancelled()

    if width or height:
        if width and height:
            ow, oh = image.size
            ratio = min(width / ow, height / oh)
            image = image.resize((max(1, round(ow * ratio)), max(1, round(oh * ratio))), Image.Resampling.LANCZOS)
        else:
            ow, oh = image.size
            new = (width, max(1, round(oh * width / ow))) if width else (max(1, round(ow * height / oh)), height)
            image = image.resize(new, Image.Resampling.LANCZOS)

    if cancel is not None and cancel.is_set():
        raise ProcessingCancelled()

    if gray:
        alpha = image.getchannel("A") if "A" in image.getbands() else None
        image = ImageOps.grayscale(image.convert("RGB"))
        if alpha:
            image = image.convert("RGBA")
            image.putalpha(alpha)

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
        args = {"optimize": True, "compress_level": level}
    else:
        args = {}

    # فقط فشرده‌سازی خالص؟ (تبدیل/Resize/Gray درخواست نشده)
    compression_only = (
        wanted is None and width is None and height is None and not gray
    )

    old_size = source.stat().st_size
    with output_file(folder, source, ext) as (handle, target):
        image.save(handle, fmt, **args)
    new_size = target.stat().st_size

    # اگر فقط فشرده‌سازی بود و خروجی بزرگ‌تر شد، حذف کن
    if compression_only and new_size >= old_size:
        target.unlink(missing_ok=True)
        return old_size, old_size, "already_optimized"

    return old_size, new_size, "compressed"


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

    cmd = [
        exe, "-nostdin", "-hide_banner", "-loglevel", "error", "-n",
        "-progress", "pipe:1",
        "-i", str(source),
        "-map", "0:v:0", "-map", "0:a?", "-map", "0:s?", "-map", "0:t?",
        "-c:v", codec, "-preset", "slow", "-crf", str(crf),
        "-vf", scale, "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-c:s", "mov_text",
        "-map_metadata", "0", "-map_chapters", "0",
        "-movflags", "+faststart",
    ]

    with tempfile.TemporaryDirectory(prefix=".mitia-", dir=folder) as temp_folder:
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
                    # pipe را تخلیه کن تا بلاک نشود
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

        with output_file(folder, source, ".mp4") as (handle, target), temp.open("rb") as encoded:
            shutil.copyfileobj(encoded, handle)

    return source.stat().st_size, target.stat().st_size, "compressed"


class DnDApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)


class CompactMenu(ctk.CTkOptionMenu):
    def destroy(self):
        for variable, token in getattr(self, "model_traces", []):
            variable.trace_remove("write", token)
        super().destroy()

    def _open_dropdown_menu(self):
        root = self.winfo_toplevel()
        if self._state == "disabled":
            return
        if root.menu_owner is self:
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
        scale = self._get_widget_scaling()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 4
        desired = int((len(self._values) * 36 + 12) * scale)
        height = min(desired, max(72, popup.winfo_screenheight() - y - 8))
        popup.geometry(f"{self.winfo_width()}x{height}+{x}+{y}")
        frame_type = ctk.CTkScrollableFrame if height < desired else ctk.CTkFrame
        body = frame_type(popup, fg_color=C["panel"], corner_radius=6)
        body.pack(fill="both", expand=True, padx=1, pady=1)
        for value in self._values:
            selected = value == self.get()
            button = ctk.CTkButton(
                body, text=value, height=32, width=0, corner_radius=5,
                fg_color=C["line"] if selected else "transparent",
                hover_color=C["hover"], text_color=C["text"],
                font=ctk.CTkFont(size=13),
                command=lambda v=value: self.choose(v))
            button.pack(fill="x", padx=5, pady=2)
        popup.bind("<Escape>", lambda _e: root.dismiss_menu())
        popup.deiconify()
        popup.lift()

    def choose(self, value):
        self.set(value)
        self.winfo_toplevel().dismiss_menu(restore_focus=True)
        if self._command:
            self._command(value)


class ErrorDialog(ctk.CTkToplevel):
    def __init__(self, master, title, summary, errors, lang="en"):
        super().__init__(master)
        t = T[lang]
        rtl = lang == "fa"

        def tr(k):
            value = t[k]
            return value if lang == "en" else get_display(arabic_reshaper.reshape(value))

        self.title(title)
        self.geometry("620x420")
        self.minsize(420, 300)
        self.configure(fg_color=C["bg"])
        self.transient(master)
        self.grab_set()

        header = ctk.CTkLabel(
            self, text=summary, font=ctk.CTkFont(size=14, weight="bold"),
            text_color=C["text"], anchor="e" if rtl else "w",
            justify="right" if rtl else "left"
        )
        header.pack(fill="x", padx=20, pady=(18, 8))

        box = ctk.CTkTextbox(
            self, fg_color=C["field"], text_color=C["text"],
            font=ctk.CTkFont(size=12)
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
                filetypes=[("Text", "*.txt"), ("All", "*.*")]
            )
            if path:
                Path(path).write_text("\n".join(errors), encoding="utf-8")

        ctk.CTkButton(
            row, text="📋 " + tr("copy"),
            command=copy_all, width=100, height=34,
            fg_color=C["panel"], hover_color=C["line"]
        ).pack(side="right" if rtl else "left")
        ctk.CTkButton(
            row, text="💾 " + tr("save_log"),
            command=save_log, width=120, height=34,
            fg_color=C["panel"], hover_color=C["line"]
        ).pack(side="right" if rtl else "left", padx=8)
        ctk.CTkButton(
            row, text="✕ " + tr("close"),
            command=self.destroy, width=100, height=34,
            fg_color=C["blue"], hover_color=C["hover"]
        ).pack(side="left" if rtl else "right")


class App(DnDApp):
    def __init__(self):
        super().__init__()

        load_persian_font()
        ctk.ThemeManager.theme["CTkFont"]["family"] = "Vazirmatn"
        ctk.set_appearance_mode("dark")

        self.lang = "fa"
        self.mode = None
        self.busy = False
        self.files = {"image": [], "video": []}
        self.events = queue.Queue()
        self.out = tk.StringVar(master=self)
        self.saved_settings = {}
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

    def title_text(self):
        return "میتیا" if self.rtl() else NAME

    def close(self):
        if self.busy:
            if not messagebox.askyesno(
                self.title_text(), T[self.lang]["close_busy"], parent=self
            ):
                return
            self.cancel_event.set()
            self.withdraw()
            self.wait_for_close()
        else:
            self.destroy()

    def wait_for_close(self):
        if self.worker is not None and self.worker.is_alive():
            self.after(100, self.wait_for_close)
        else:
            self.destroy()

    def tr(self, k):
        value = T[self.lang][k]
        return value if self.lang == "en" or k in {"selected", "processing", "done"} else get_display(arabic_reshaper.reshape(value))

    def msg(self, k, **values):
        value = T[self.lang][k].format(**values)

        if self.lang == "en":
            return value

        return get_display(
            arabic_reshaper.reshape(value),
            base_dir="R"
        )

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
        self.out.set(self.output_entry.get())
        keys = ("q", "gray", "fmt", "dim", "custom") if self.mode == "image" else ("q", "codec", "res")
        state = {key: getattr(self, key).get() for key in keys}
        if self.mode == "image":
            state["axis"] = "width" if self.axis.get() == self.tr("width") else "height"
        self.saved_settings[self.mode] = state

    def button(self, p, text, cmd, active=False, width=0, danger=False):
        fg_col = C["danger"] if danger else (C["blue"] if active else C["panel"])
        hov_col = C["danger_hover"] if danger else (C["hover"] if active else C["line"])
        border_col = C["danger"] if danger else (C["blue"] if active else C["line"])

        return ctk.CTkButton(
            p, text=text, command=cmd, width=width, height=40, corner_radius=8,
            fg_color=fg_col, hover_color=hov_col, text_color=C["text"],
            border_width=1, border_color=border_col,
            font=ctk.CTkFont(size=13, weight="bold")
        )

    def header(self, p):
        name = get_display(arabic_reshaper.reshape("میتیا")) if self.rtl() else NAME
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
        if self.busy:
            return
        self.save_settings()
        self.lang = "en" if self.rtl() else "fa"
        self.home() if self.mode is None else self.workspace()

    def pick(self, mode):
        if self.busy or self.mode == mode:
            return
        self.save_settings()
        self.mode = mode
        self.workspace()

    def workspace(self):
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
            fg_color=C["blue"], hover_color=C["hover"], text_color="#ffffff"
        )
        self.start_button.pack(side="right" if self.rtl() else "left")

        self.cancel_button = ctk.CTkButton(
            status_frame, text="⏹ " + self.tr("cancel"), command=self.cancel,
            width=120, height=45, corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=C["danger"], hover_color=C["danger_hover"],
            text_color="#ffffff",
            text_color_disabled="#cbd5e1",
            state="disabled"
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
            relief="flat", highlightthickness=0, borderwidth=0, font=("Vazirmatn", 12)
        )
        self.list.pack(fill="both", expand=True, padx=10, pady=10)
        self.list.drop_target_register(DND_FILES)
        self.list.dnd_bind("<<Drop>>", self.drop)
        self.list.bind("<Double-Button-1>", lambda _e: self.add())

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
            getattr(self, key).set(self.tr(value) if key == "axis" else value)
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

    def menu(self, p, var, values, width=120):
        labels = {"Original": self.tr("original"), "Custom": self.tr("custom_option")}
        reverse = {labels.get(v, v): v for v in values}
        display = tk.StringVar(master=self, value=labels.get(var.get(), var.get()))
        display_trace = display.trace_add("write", lambda *_: var.set(reverse.get(display.get(), display.get())) if var.get() != reverse.get(display.get(), display.get()) else None)
        model_trace = var.trace_add("write", lambda *_: display.set(labels.get(var.get(), var.get())) if display.get() != labels.get(var.get(), var.get()) else None)
        menu = CompactMenu(
            p, variable=display, values=[labels.get(v, v) for v in values], width=width, dynamic_resizing=False, height=36, corner_radius=6,
            fg_color=C["field"], button_color=C["line"], button_hover_color=C["blue"], text_color=C["text"],
            anchor="center", dropdown_fg_color=C["panel"], dropdown_hover_color=C["line"],
            dropdown_font=ctk.CTkFont(family="Vazirmatn", size=13), font=ctk.CTkFont(size=13)
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
            progress_color=C["blue"], button_color=C["text"], button_hover_color=C["blue"]
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

        menu = self.menu(f, self.dim, ["Original", "1920 × 1080", "1280 × 720", "800 × 600", "Custom"], width=110)
        menu.configure(command=lambda _value: self.custom_toggle(self.dim.get()))
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
            text_color=C["text"]
        )
        self.custom_entry = entry
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
        if self.busy or self.dialog_open:
            return
        self.dialog_open = True
        try:
            title = "انتخاب فایل" if self.rtl() else "Select files"
            types = [("تصاویر و ویدئوها" if self.rtl() else "Media", " ".join(f"*{x}" for x in self.ext())),
                     ("همهٔ فایل‌ها" if self.rtl() else "All files", "*.*")]
            self.add_paths(filedialog.askopenfilenames(parent=self, title=title, filetypes=types))
        finally:
            self.dialog_open = False

    def folder(self):
        if self.busy:
            return
        p = filedialog.askdirectory(parent=self)
        if p:
            self.add_paths([p])

    def drop(self, e):
        self.add_paths(self.tk.splitlist(e.data))

    def add_paths(self, paths):
        if self.busy:
            return
        items = self.files[self.mode]
        known = {os.path.normcase(x) for x in items}
        valid_ext = self.ext()
        wrong_ext = self.other_ext()
        wrong_media = 0
        unsupported = 0
        try:
            for path in paths:
                source = Path(path).resolve()
                candidates = source.iterdir() if source.is_dir() else [source]
                for candidate in candidates:
                    if not candidate.is_file():
                        continue
                    p = str(candidate)
                    suffix = candidate.suffix.lower()
                    norm = os.path.normcase(p)
                    if norm in known:
                        continue
                    if suffix in valid_ext:
                        items.append(p)
                        known.add(norm)
                    elif suffix in wrong_ext:
                        wrong_media += 1
                    else:
                        unsupported += 1
        except OSError as error:
            messagebox.showwarning(self.title_text(), str(error), parent=self)

        self.refresh()

        # هشدار تجمیعی (نه به ازای هر فایل)
        if wrong_media or unsupported:
            parts = []
            if wrong_media:
                key = "msg_wrong_media_image" if self.mode == "image" else "msg_wrong_media_video"
                parts.append(T[self.lang][key].format(count=wrong_media))
            if unsupported:
                parts.append(T[self.lang]["msg_unsupported"].format(count=unsupported))
            text = "\n".join(parts)
            messagebox.showwarning(self.title_text(), text, parent=self)

    def refresh(self):
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
        if self.busy:
            return
        chosen = set(self.list.curselection())
        self.files[self.mode][:] = [p for i, p in enumerate(self.files[self.mode]) if i not in chosen]
        self.refresh()

    def clear_files(self):
        if self.busy:
            return
        self.files[self.mode].clear()
        self.refresh()

    def choose_output(self):
        if self.busy:
            return
        p = filedialog.askdirectory(parent=self)
        if p:
            self.out.set(p)

    def opts(self):
        if not self.files[self.mode]:
            raise ValueError(self.tr("need_files"))
        if self.out.get().strip() and not Path(self.out.get().strip()).is_dir():
            raise ValueError(self.tr("need_output"))

        if self.mode == "video":
            return (
                ffmpeg(),
                round(self.q.get()),
                "libx265" if self.codec.get().startswith("H.265") else "libx264",
                {"Original": None, "1080p": 1080, "720p": 720, "480p": 480}[self.res.get()]
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
                raise ValueError(self.tr("custom"))
            d["Custom"] = (v, None) if self.axis.get() == self.tr("width") else (None, v)

        w, h = d[self.dim.get()]
        return round(self.q.get()), None if self.fmt.get() == "Original" else self.fmt.get().upper(), w, h, self.gray.get()

    def start(self):
        if self.busy:
            return
        self.out.set(self.output_entry.get())
        try:
            o = self.opts()
        except ValueError as e:
            messagebox.showwarning(self.title_text(), str(e), parent=self)
            return

        if self.mode == "video" and not o[0]:
            messagebox.showwarning(self.title_text(), self.tr("ffmpeg"), parent=self)
            return

        self.busy = True
        self.cancel_event.clear()
        self.dismiss_menu()
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.bar.set(0)
        self.worker = threading.Thread(
            target=self.work,
            args=(self.mode, list(self.files[self.mode]), self.out.get().strip(), o),
            daemon=True
        )
        self.worker.start()

    def cancel(self):
        if not self.busy:
            return
        self.cancel_event.set()
        self.cancel_button.configure(state="disabled")
        self.status.set(self.tr("cancelled"))

    def work(self, mode, files, folder, o):
        old = new = ok = 0
        skipped_optimized = 0
        errors = []
        total = len(files)

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
                        pct=int(ratio * 100)
                    ))

                elif e[0] == "c":
                    self.busy = False
                    self.start_button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
                    self.status.set(self.tr("cancelled"))

                else:  # "d"
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
                            self.tr("errors_title"),
                            report,
                            errors,
                            lang=self.lang,
                        )
        except queue.Empty:
            pass
        except Exception as err:
            print("poll error:", err, file=sys.stderr)
        finally:
            self.after(100, self.poll)


if __name__ == "__main__":
    app = App()
    app.mainloop()