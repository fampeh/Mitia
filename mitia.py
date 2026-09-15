import ctypes
import os
import queue
import shutil
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageOps
from tkinterdnd2 import DND_FILES, TkinterDnD

NAME = "Mitia"
VERSION = "2.6.0"

IMG = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
VID = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".m4v"}

C = {
    "bg": "#0f172a",
    "panel": "#1e293b",
    "field": "#020617",
    "line": "#334155",
    "text": "#f8fafc",
    "muted": "#94a3b8",
    "blue": "#3b82f6",
    "hover": "#2563eb",
    "danger": "#ef4444",
    "danger_hover": "#dc2626"
}

T = {
    "fa": {
        "image": "تصاویر", "video": "ویدئوها", "lang": "English", 
        "drop": "فایل‌ها را اینجا رها کنید", "add": "افزودن فایل", 
        "folder": "افزودن پوشه", "remove": "حذف", "clear": "پاک کردن", 
        "quality": "کیفیت", "format": "فرمت خروجی", "dimensions": "ابعاد", 
        "width": "عرض", "height": "ارتفاع", "gray": "سیاه‌وسفید", 
        "output": "پوشه خروجی", "browse": "انتخاب", "start": "شروع فشرده‌سازی", 
        "codec": "کدک", "resolution": "رزولوشن", "selected": "{count} فایل انتخاب شد", 
        "processing": "در حال پردازش: {number} از {total} · {name}", 
        "done": "پایان یافت: {count} فایل · {old} ← {new}", 
        "need_files": "لطفاً حداقل یک فایل انتخاب کنید.", 
        "need_output": "لطفاً پوشه خروجی را مشخص کنید.", 
        "custom": "مقدار ابعاد دلخواه باید یک عدد مثبت باشد.", 
        "ffmpeg": "ابزار FFmpeg در این نسخه یافت نشد.", 
        "errors": "خطا در پردازش"
    },
    "en": {
        "image": "Images", "video": "Videos", "lang": "فارسی", 
        "drop": "Drop files here", "add": "Add files", 
        "folder": "Add folder", "remove": "Remove", "clear": "Clear", 
        "quality": "Quality", "format": "Output format", "dimensions": "Dimensions", 
        "width": "Width", "height": "Height", "gray": "Black & white", 
        "output": "Output folder", "browse": "Browse", "start": "Start Compress", 
        "codec": "Codec", "resolution": "Resolution", "selected": "{count} files selected", 
        "processing": "Processing: {number} / {total} · {name}", 
        "done": "Completed: {count} files · {old} → {new}", 
        "need_files": "Please choose at least one file.", 
        "need_output": "Please choose an output folder.", 
        "custom": "Custom dimension must be a positive number.", 
        "ffmpeg": "FFmpeg is unavailable in this build.", 
        "errors": "Processing errors"
    }
}


def asset(name):
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / name

def load_persian_font():
    font = asset("Vazirmatn-Regular.ttf")
    if font.is_file() and sys.platform == "win32":
        ctypes.windll.gdi32.AddFontResourceExW(str(font), 0x10, 0)

def ffmpeg():
    p = asset("ffmpeg.exe")
    return str(p) if p.exists() else shutil.which("ffmpeg")

def unique(folder, source, ext):
    p = Path(folder) / f"{Path(source).stem}_compressed{ext}"
    n = 2
    while p.exists():
        p = Path(folder) / f"{Path(source).stem}_compressed_{n}{ext}"
        n += 1
    return p

def size(n):
    return f"{n/1024:.0f} KB" if n < 1048576 else f"{n/1048576:.2f} MB"


def pack_image(source, folder, quality, wanted, width, height, gray):
    source = Path(source)
    with Image.open(source) as opened:
        fmt = wanted or (opened.format or "JPEG").upper()
        fmt = "JPEG" if fmt == "JPG" else fmt
        ext = ".jpg" if fmt == "JPEG" else ".webp" if fmt == "WEBP" else source.suffix
        image = ImageOps.exif_transpose(opened)
        image.load()
        
    if width or height:
        if width and height:
            image.thumbnail((width, height), Image.Resampling.LANCZOS)
        else:
            ow, oh = image.size
            new = (width, max(1, round(oh * width / ow))) if width else (max(1, round(ow * height / oh)), height)
            image = image.resize(new, Image.Resampling.LANCZOS)
            
    if gray:
        alpha = image.getchannel("A") if "A" in image.getbands() else None
        image = ImageOps.grayscale(image.convert("RGB"))
        if alpha:
            image = image.convert("RGBA")
            image.putalpha(alpha)
            
    if fmt == "JPEG" and image.mode in ("RGBA", "LA", "P"):
        rgba = image.convert("RGBA")
        bg = Image.new("RGB", rgba.size, "white")
        bg.paste(rgba, mask=rgba.getchannel("A"))
        image = bg
    elif image.mode == "P" and fmt != "PNG":
        image = image.convert("RGB")
        
    target = unique(folder, source, ext)
    args = {"quality": quality, "optimize": True, "progressive": True} if fmt == "JPEG" else \
           {"quality": quality, "method": 6} if fmt == "WEBP" else \
           {"optimize": True, "compress_level": 9} if fmt == "PNG" else {}
           
    image.save(target, fmt, **args)
    return source.stat().st_size, target.stat().st_size

def pack_video(exe, source, folder, crf, codec, height):
    source = Path(source)
    target = unique(folder, source, ".mp4")
    cmd = [exe, "-y", "-i", str(source), "-c:v", codec, "-preset", "slow", "-crf", str(crf), "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart"]
    if height:
        cmd += ["-vf", f"scale=-2:{height}:force_original_aspect_ratio=decrease"]
        
    result = subprocess.run(cmd + [str(target)], capture_output=True, text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        raise RuntimeError(result.stderr.splitlines()[-1] if result.stderr else "FFmpeg failed")
    return source.stat().st_size, target.stat().st_size


class DnDApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)


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
        
        self.title(f"{NAME} {VERSION}")
        self.geometry("980x820")
        self.minsize(800, 720)
        self.configure(fg_color=C["bg"])
        
        try:
            self.iconbitmap(default=str(asset("mitia.ico")))
        except tk.TclError:
            pass
            
        self.after(100, self.poll)
        self.home()

    def tr(self, k):
        value = T[self.lang][k]
        return value if self.lang == "en" or k in {"selected", "processing", "done"} else get_display(arabic_reshaper.reshape(value))

    def msg(self, k, **values):
        value = T[self.lang][k].format(**values)
        return value if self.lang == "en" else get_display(arabic_reshaper.reshape(value))

    def rtl(self):
        return self.lang == "fa"

    def side(self):
        return "right" if self.rtl() else "left"

    def anchor(self):
        return "e" if self.rtl() else "w"

    def clear(self):
        for w in self.winfo_children():
            w.destroy()

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
        h = ctk.CTkFrame(p, fg_color="transparent")
        h.pack(fill="x", pady=(0, 20))
        
        logo_frame = ctk.CTkFrame(h, fg_color="transparent")
        logo_frame.pack(side=self.side())
        ctk.CTkLabel(logo_frame, text=NAME, font=ctk.CTkFont(size=28, weight="bold"), text_color=C["text"]).pack(side=self.side())
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
        self.lang = "en" if self.rtl() else "fa"
        self.home() if self.mode is None else self.workspace()

    def pick(self, mode):
        if self.busy or self.mode == mode:
            return
        self.mode = mode
        self.workspace()

    def workspace(self):
        self.clear()
        
        root = ctk.CTkFrame(self, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=40, pady=25)
        self.header(root)
        
        tabs = ctk.CTkFrame(root, fg_color="transparent")
        tabs.pack(fill="x", pady=(0, 16))
        
        modes = ("video", "image") if self.rtl() else ("image", "video")
        for m in modes:
            self.button(tabs, self.tr(m), lambda v=m: self.pick(v), m == self.mode, 140).pack(side=self.side(), padx=5)
            
        self.status = tk.StringVar(value=self.msg("selected", count=len(self.files[self.mode])))
        
        self.dropzone(root)
        self.settings_ui(root)
        
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

    def dropzone(self, p):
        card = ctk.CTkFrame(p, fg_color=C["panel"], corner_radius=12, border_width=1, border_color=C["line"], height=250)
        card.pack(fill="x", pady=(0, 15))
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
        
        self.drop_hint = tk.Label(self.list_area, text="+", bg=C["field"], fg=C["line"], font=("Vazirmatn", 60, "bold"), cursor="hand2")
        self.drop_hint.drop_target_register(DND_FILES)
        self.drop_hint.dnd_bind("<<Drop>>", self.drop)
        self.drop_hint.bind("<Double-Button-1>", lambda _e: self.add())
        self.drop_hint.bind("<Button-1>", lambda _e: self.add())
        
        self.refresh()
        
        actions = (("clear", self.clear_files), ("remove", self.remove), ("folder", self.folder), ("add", self.add)) if self.rtl() else (("add", self.add), ("folder", self.folder), ("remove", self.remove), ("clear", self.clear_files))
        
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 12))
        
        for k, fn in actions:
            is_danger = k in ["clear", "remove"]
            self.button(row, self.tr(k), fn, width=100, danger=is_danger).pack(side=self.side(), padx=5)

    def settings_ui(self, p):
        panel = ctk.CTkFrame(p, fg_color=C["panel"], corner_radius=12, border_width=1, border_color=C["line"])
        panel.pack(fill="x", pady=(0, 5))
        panel.grid_columnconfigure((0, 1), weight=1)
        
        self.q = tk.IntVar(value=80 if self.mode == "image" else 23)
        self.out = tk.StringVar()
        self.gray = tk.BooleanVar()
        
        left, right = (1, 0) if self.rtl() else (0, 1)
        
        self.group(panel, left, 0, self.tr("quality"), self.quality)
        
        if self.mode == "image":
            self.fmt = tk.StringVar(value="Original")
            self.dim = tk.StringVar(value="Original")
            self.axis = tk.StringVar(value=self.tr("width"))
            self.custom = tk.StringVar()
            
            self.group(panel, right, 0, self.tr("format"), lambda p: self.menu(p, self.fmt, ["Original", "JPEG", "WebP"]))
            self.group(panel, left, 1, self.tr("dimensions"), self.dimension)
            ctk.CTkCheckBox(panel, text=self.tr("gray"), variable=self.gray, fg_color=C["blue"], hover_color=C["hover"], text_color=C["text"], font=ctk.CTkFont(size=13)).grid(row=2, column=left, sticky=self.anchor(), padx=25, pady=(5, 15))
        else:
            self.codec = tk.StringVar(value="H.264 / AVC")
            self.res = tk.StringVar(value="Original")
            
            self.group(panel, right, 0, self.tr("codec"), lambda p: self.menu(p, self.codec, ["H.264 / AVC", "H.265 / HEVC"]))
            self.group(panel, left, 1, self.tr("resolution"), lambda p: self.menu(p, self.res, ["Original", "1080p", "720p", "480p"]))
            
        out_frame = ctk.CTkFrame(panel, fg_color="transparent")
        out_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=25, pady=(10, 20))
        out_frame.grid_columnconfigure(1, weight=1)
        
        a, b = (2, 0) if self.rtl() else (0, 2)
        
        ctk.CTkLabel(out_frame, text=self.tr("output"), width=90, anchor=self.anchor(), font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=a, padx=(0, 15))
        ctk.CTkEntry(out_frame, textvariable=self.out, justify="right" if self.rtl() else "left", height=40, fg_color=C["field"], border_color=C["line"], corner_radius=6, text_color=C["text"], font=ctk.CTkFont(size=13)).grid(row=0, column=1, sticky="ew")
        self.button(out_frame, self.tr("browse"), self.choose_output, width=110).grid(row=0, column=b, padx=(15, 0))

    def group(self, p, col, row, label, build):
        g = ctk.CTkFrame(p, fg_color="transparent")
        g.grid(row=row, column=col, sticky="ew", padx=25, pady=15)
        
        label_col, control_col = (1, 0) if self.rtl() else (0, 1)
        g.grid_columnconfigure(control_col, weight=1)
        
        ctk.CTkLabel(g, text=label, width=90, anchor=self.anchor(), font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=label_col, padx=(0, 15) if not self.rtl() else (15, 0))
        
        holder = ctk.CTkFrame(g, fg_color="transparent")
        holder.grid(row=0, column=control_col, sticky="ew")
        holder.grid_columnconfigure(0, weight=1)
        build(holder).grid(row=0, column=0, sticky="ew")

    def menu(self, p, var, values):
        menu = ctk.CTkOptionMenu(
            p, variable=var, values=values, height=40, corner_radius=6,
            fg_color=C["field"], button_color=C["line"], button_hover_color=C["blue"], text_color=C["text"],
            anchor="center", dropdown_fg_color=C["panel"], dropdown_hover_color=C["line"], 
            dropdown_font=ctk.CTkFont(family="Vazirmatn", size=13), font=ctk.CTkFont(size=13)
        )
        return menu

    def quality(self, p):
        f = ctk.CTkFrame(p, fg_color="transparent")
        f.grid_columnconfigure(0, weight=1)
        
        value = ctk.CTkLabel(f, text=str(self.q.get()), width=40, font=ctk.CTkFont(size=13, weight="bold"), text_color=C["blue"])
        slider = ctk.CTkSlider(
            f, from_=1 if self.mode == "image" else 0, to=100 if self.mode == "image" else 51,
            variable=self.q, command=lambda _x: value.configure(text=str(round(self.q.get()))),
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
        f.grid_columnconfigure(0, weight=1)
        
        menu = self.menu(f, self.dim, ["Original", "1920 × 1080", "1280 × 720", "800 × 600", "Custom"])
        menu.configure(command=self.custom_toggle)
        menu.grid(row=0, column=0, sticky="ew")
        
        self.custombox = ctk.CTkFrame(f, fg_color="transparent")
        self.custombox.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self.custombox.grid_columnconfigure(1, weight=1)
        
        axis = self.menu(self.custombox, self.axis, [self.tr("width"), self.tr("height")])
        numeric = (self.register(lambda v: v == "" or (v.isascii() and v.isdigit())), "%P")
        entry = ctk.CTkEntry(self.custombox, textvariable=self.custom, validate="key", validatecommand=numeric, justify="center", height=40, fg_color=C["field"], border_color=C["line"], text_color=C["text"])
        px = ctk.CTkLabel(self.custombox, text="px", width=30, text_color=C["muted"], font=ctk.CTkFont(size=13))
        
        if self.rtl():
            axis.grid(row=0, column=2, padx=(0, 10))
            entry.grid(row=0, column=1, sticky="ew")
            px.grid(row=0, column=0, padx=(10, 0))
        else:
            axis.grid(row=0, column=0, padx=(0, 10))
            entry.grid(row=0, column=1, sticky="ew")
            px.grid(row=0, column=2, padx=(10, 0))
            
        self.custombox.grid_remove()
        return f

    def custom_toggle(self, value):
        if value == "Custom":
            self.custombox.grid()
        else:
            self.custombox.grid_remove()

    def ext(self):
        return IMG if self.mode == "image" else VID

    def add(self):
        self.add_paths(filedialog.askopenfilenames(filetypes=[("Media", " ".join(f"*{x}" for x in self.ext())), ("All", "*.*")]))

    def folder(self):
        p = filedialog.askdirectory()
        if p:
            self.add_paths(str(x) for x in Path(p).iterdir() if x.is_file())

    def drop(self, e):
        self.add_paths(self.tk.splitlist(e.data))

    def add_paths(self, paths):
        items = self.files[self.mode]
        known = {os.path.normcase(x) for x in items}
        for p in paths:
            p = os.path.abspath(p)
            if Path(p).suffix.lower() in self.ext() and os.path.normcase(p) not in known:
                items.append(p)
                known.add(os.path.normcase(p))
        self.refresh()

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
        chosen = set(self.list.curselection())
        self.files[self.mode][:] = [p for i, p in enumerate(self.files[self.mode]) if i not in chosen]
        self.refresh()

    def clear_files(self):
        self.files[self.mode].clear()
        self.refresh()

    def choose_output(self):
        p = filedialog.askdirectory()
        if p:
            self.out.set(p)

    def opts(self):
        if not self.files[self.mode]:
            raise ValueError(self.tr("need_files"))
        if not self.out.get().strip() or not Path(self.out.get()).is_dir():
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
                v = int(self.custom.get())
                assert v > 0
            except (ValueError, AssertionError):
                raise ValueError(self.tr("custom"))
            d["Custom"] = (v, None) if self.axis.get() == self.tr("width") else (None, v)
            
        w, h = d[self.dim.get()]
        return round(self.q.get()), None if self.fmt.get() == "Original" else self.fmt.get().upper(), w, h, self.gray.get()

    def start(self):
        try:
            o = self.opts()
        except ValueError as e:
            messagebox.showwarning(NAME, str(e))
            return
            
        if self.mode == "video" and not o[0]:
            messagebox.showwarning(NAME, self.tr("ffmpeg"))
            return
            
        self.busy = True
        self.start_button.configure(state="disabled")
        self.bar.set(0)
        threading.Thread(target=self.work, args=(self.mode, list(self.files[self.mode]), self.out.get(), o), daemon=True).start()

    def work(self, mode, files, folder, o):
        old = new = ok = 0
        errors = []
        
        for i, p in enumerate(files, 1):
            try:
                if mode == "image":
                    a, b = pack_image(p, folder, *o)
                else:
                    a, b = pack_video(o[0], p, folder, *o[1:])
                old += a
                new += b
                ok += 1
            except Exception as e:
                errors.append(f"{Path(p).name}: {e}")
                
            self.events.put(("p", i, len(files), Path(p).name))
            
        self.events.put(("d", ok, old, new, errors))

    def poll(self):
        try:
            while True:
                e = self.events.get_nowait()
                if e[0] == "p":
                    _, n, total, name = e
                    self.bar.set(n / total)
                    self.status.set(self.msg("processing", number=n, total=total, name=name))
                else:
                    _, n, old, new, errors = e
                    self.busy = False
                    self.start_button.configure(state="normal")
                    report = self.msg("done", count=n, old=size(old), new=size(new))
                    self.status.set(report)
                    if errors:
                        messagebox.showwarning(self.tr("errors"), report + "\n\n" + "\n".join(errors))
        except queue.Empty:
            pass
            
        self.after(100, self.poll)


if __name__ == "__main__":
    app = App()
    app.mainloop()
