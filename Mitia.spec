import ast
from pathlib import Path

source = ast.parse(Path('mitia.py').read_text(encoding='utf-8'))
version = next(ast.literal_eval(node.value) for node in source.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'VERSION' for target in node.targets))

a = Analysis(
    ['mitia.py'], pathex=[], binaries=[
        ('ffmpeg.exe', '.'), ('avcodec-58.dll', '.'), ('avdevice-58.dll', '.'),
        ('avfilter-7.dll', '.'), ('avformat-58.dll', '.'), ('avutil-56.dll', '.'),
        ('postproc-55.dll', '.'), ('swresample-3.dll', '.'), ('swscale-5.dll', '.'),
    ], datas=[('mitia.ico', '.'), ('fonts/ttf/Vazirmatn-Regular.ttf', '.')],
    hiddenimports=['customtkinter', 'tkinterdnd2'], hookspath=[], hooksconfig={},
    runtime_hooks=[], excludes=[], noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [], name=f'Mitia-{version}', icon='mitia.ico', version='version_info.txt', debug=False,
    bootloader_ignore_signals=False, strip=False, upx=True, upx_exclude=[],
    runtime_tmpdir=None, console=False, disable_windowed_traceback=False,
    argv_emulation=False, target_arch=None, codesign_identity=None,
    entitlements_file=None,
)
