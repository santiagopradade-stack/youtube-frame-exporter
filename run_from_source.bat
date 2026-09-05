@echo off
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0download_deno.ps1"
if errorlevel 1 (
  echo Deno could not be downloaded.
  pause
  exit /b 1
)

where py >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.11 or newer from https://python.org/downloads/
  pause
  exit /b 1
)

if not exist .run-env\Scripts\python.exe (
  py -m venv .run-env
  call .run-env\Scripts\activate.bat
  python -m pip install -r requirements.txt
) else (
  call .run-env\Scripts\activate.bat
)

python app.py
