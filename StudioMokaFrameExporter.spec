from pathlib import Path
import os

from PyInstaller.utils.hooks import collect_all


project_root = Path(SPECPATH)
deno_exe = os.environ.get("DENO_EXE")
if not deno_exe or not Path(deno_exe).is_file():
    raise SystemExit("DENO_EXE no apunta a un deno.exe válido. Ejecuta build.ps1.")

datas = [(str(project_root / "assets" / "studio_moka_logo.png"), "assets")]
binaries = [(deno_exe, ".")]
hiddenimports = []

for package in ("imageio_ffmpeg", "yt_dlp", "yt_dlp_ejs"):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

a = Analysis(
    [str(project_root / "src" / "app.py")],
    pathex=[str(project_root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Exportador de fotogramas de YouTube - Studio Moka",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "assets" / "studio_moka.ico"),
    version=str(project_root / "version_info.txt"),
)
