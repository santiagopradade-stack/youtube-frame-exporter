@echo off
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0download_deno.ps1"
if errorlevel 1 goto :failed

where py >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.11 or newer from https://python.org/downloads/
  pause
  exit /b 1
)

py -m venv .build-env
if errorlevel 1 goto :failed
call .build-env\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto :failed
python -m pip install -r requirements.txt pyinstaller==6.22.2
if errorlevel 1 goto :failed

python -m PyInstaller --noconfirm --clean --onefile --windowed --name YouTubeSceneFrameExporter --add-binary "deno.exe;." --collect-all imageio_ffmpeg --collect-all yt_dlp --collect-all yt_dlp_ejs --collect-all scenedetect app.py
if errorlevel 1 goto :failed

echo.
echo Build complete: dist\YouTubeSceneFrameExporter.exe
pause
exit /b 0

:failed
echo.
echo The build failed. Review the messages above.
pause
exit /b 1
