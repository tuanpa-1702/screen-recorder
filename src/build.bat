@echo off
rem dist\Screen Recorder.exe = one portable file (PyInstaller onefile).
rem It also carries the onedir bootloader, so "Install" puts an unpacked copy in
rem %LOCALAPPDATA%\Programs\Screen Recorder that starts fast (no per-launch unpacking).
cd /d "%~dp0"
for /f "delims=" %%F in ('python -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"') do set FF=%%F
if not exist build mkdir build
copy /y "%FF%" build\ffmpeg.exe >nul
python -c "import sys;sys.argv=['x'];from PySide6.QtWidgets import QApplication;a=QApplication([]);import theme;theme.app_icon(256).save('build/app.ico')"
python collect_licenses.py || exit /b 1
set OPTS=--noconfirm --windowed --name "Screen Recorder" --icon build\app.ico --workpath build\work ^
  --add-binary "build\ffmpeg.exe;." --add-data "licenses;licenses" --hidden-import win32com.client ^
  --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick --exclude-module PySide6.QtWebEngineCore ^
  --exclude-module PySide6.QtOpenGL --exclude-module PySide6.QtPdf ^
  --exclude-module tkinter --exclude-module soundcard --exclude-module cv2
rem 1) onedir build -> take its small bootloader exe
python -m PyInstaller %OPTS% --onedir --distpath build\onedir screen_recorder.py || exit /b 1
copy /y "build\onedir\Screen Recorder\Screen Recorder.exe" build\onedir_boot.exe >nul
rem 2) onefile build that embeds the bootloader
python -m PyInstaller %OPTS% --onefile --distpath dist --add-binary "build\onedir_boot.exe;." screen_recorder.py || exit /b 1
