# Build

Requirements: Windows 10/11 x64, Python 3.13.

```bat
pip install -r requirements.txt
build.bat
```

`build.bat` (→ `src\build.bat`):
1. copies `ffmpeg.exe` from the `imageio-ffmpeg` wheel and renders the app icon;
2. runs `collect_licenses.py` → `src\licenses\` (all third-party license texts, bundled in the exe);
3. builds a PyInstaller **onedir** copy and keeps its small bootloader (`onedir_boot.exe`);
4. builds the **onefile** `src\dist\Screen Recorder.exe` with that bootloader inside, so *Install* can lay out a fast-starting
   unpacked copy in `%LOCALAPPDATA%\Programs\Screen Recorder`.

Run from source without building: `cd src` then `python screen_recorder.py`.

## Source layout (`src/`)
| File | Purpose |
|---|---|
| `screen_recorder.py` | main window, settings, tray, single instance, hotkeys F12 / Shift+F12 |
| `rec_core.py` | recording engine: FFmpeg gdigrab segments + WASAPI audio, muxing |
| `snip.py` | screen freeze + region / freeform / window / full-screen selection, toast |
| `editor.py` | image editor (shapes, text, blur, crop, resize/rotate handles, undo) |
| `hotkeys.py` | global hotkey via low-level keyboard hook (can take Win+Shift+S) |
| `monitor_map.py` | monitor layout picker and identify overlay |
| `theme.py` | light theme, Acrylic dropdowns, vector icons |
| `i18n.py` | Vietnamese → English strings |
| `installer.py` | per-user install / uninstall (HKCU only) |
| `collect_licenses.py` | gathers license texts |
