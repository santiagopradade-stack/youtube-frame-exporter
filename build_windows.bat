@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -File "%~dp0build.ps1"
if errorlevel 1 (
  echo.
  echo The build failed. Review the messages above.
  pause
  exit /b 1
)
echo.
echo The single EXE is in the dist folder.
explorer.exe "%~dp0dist"
pause

