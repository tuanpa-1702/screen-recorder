# Screen Recorder - Copyright (C) 2026 TuanPA <tuanpa1702@gmail.com>
# SPDX-License-Identifier: GPL-3.0-only
# This program is free software under the GNU GPL v3; see LICENSE. It comes WITHOUT ANY WARRANTY.
"""Per-user install (no admin, HKCU only): copy exe to %LOCALAPPDATA%\\Programs, shortcuts, Apps & Features entry."""
import os, shutil, subprocess, sys, winreg

APP = "Screen Recorder"
PUBLISHER = "TuanPA"
HKCU = winreg.HKEY_CURRENT_USER
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\TuanPA.ScreenRecorder"
EXE_NAME = APP + ".exe"


def default_dir():
    return os.path.join(os.environ["LOCALAPPDATA"], "Programs", APP)


def current_exe():
    return os.path.abspath(os.environ.get("SR_LAUNCHER") or (sys.executable if getattr(sys, "frozen", False) else sys.argv[0]))


def installed_dir():
    try:
        with winreg.OpenKey(HKCU, UNINSTALL_KEY) as k:
            return winreg.QueryValueEx(k, "InstallLocation")[0]
    except OSError:
        return None


def is_installed():
    d = installed_dir()
    return bool(d and os.path.exists(os.path.join(d, EXE_NAME)))


def is_installed_copy():
    d = installed_dir()
    return bool(d) and os.path.normcase(os.path.dirname(current_exe())) == os.path.normcase(os.path.abspath(d))


def _shell_folder(name):
    import win32com.client
    return win32com.client.Dispatch("WScript.Shell").SpecialFolders(name)


def _shortcut(lnk, target, desc):
    import win32com.client
    s = win32com.client.Dispatch("WScript.Shell").CreateShortcut(lnk)
    s.TargetPath = target; s.WorkingDirectory = os.path.dirname(target)
    s.IconLocation = target + ",0"; s.Description = desc
    s.Save()


def _lnk(folder):
    return os.path.join(_shell_folder(folder), APP + ".lnk")


def install(version, desktop=True, target_dir=None):
    if not getattr(sys, "frozen", False):
        raise RuntimeError("Chỉ cài được từ bản exe.")
    d = target_dir or default_dir()
    os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, EXE_NAME)
    mei = getattr(sys, "_MEIPASS", "")
    boot = os.path.join(mei, "onedir_boot.exe")
    if os.path.exists(boot):
        # Running the single-file exe: install the unpacked (onedir) form instead -> starts in ~3 s instead of
        # unpacking 130 MB on every launch. Files in _MEIPASS are exactly the onedir build's _internal folder.
        internal = os.path.join(d, "_internal")
        if os.path.isdir(internal):
            shutil.rmtree(internal, ignore_errors=True)
        shutil.copytree(mei, internal, ignore=shutil.ignore_patterns("onedir_boot.exe"), dirs_exist_ok=True)
        shutil.copy2(boot, dst)
    elif os.path.normcase(dst) != os.path.normcase(current_exe()):
        shutil.copy2(current_exe(), dst)
    # carry over portable settings once
    ini_src = os.path.join(os.path.dirname(current_exe()), "ScreenRecorder.ini")
    ini_dst = os.path.join(d, "ScreenRecorder.ini")
    if os.path.exists(ini_src) and not os.path.exists(ini_dst):
        shutil.copy2(ini_src, ini_dst)
    _shortcut(_lnk("Programs"), dst, "Quay màn hình")
    if desktop:
        _shortcut(_lnk("Desktop"), dst, "Quay màn hình")
    size_kb = os.path.getsize(dst) // 1024
    with winreg.CreateKeyEx(HKCU, UNINSTALL_KEY, 0, winreg.KEY_WRITE) as k:
        for n, v in dict(DisplayName=APP, DisplayVersion=version, Publisher=PUBLISHER, InstallLocation=d,
                         DisplayIcon=dst + ",0", UninstallString=f'"{dst}" --uninstall',
                         QuietUninstallString=f'"{dst}" --uninstall --quiet').items():
            winreg.SetValueEx(k, n, 0, winreg.REG_SZ, v)
        winreg.SetValueEx(k, "EstimatedSize", 0, winreg.REG_DWORD, size_kb)
        winreg.SetValueEx(k, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(k, "NoRepair", 0, winreg.REG_DWORD, 1)
    return dst


def uninstall():
    """Remove shortcuts + registry; delete the install folder after this process exits."""
    d = installed_dir()
    for f in ("Programs", "Desktop"):
        try:
            os.remove(_lnk(f))
        except OSError:
            pass
    try:
        winreg.DeleteKey(HKCU, UNINSTALL_KEY)
    except OSError:
        pass
    if d and os.path.isdir(d) and os.path.basename(os.path.normpath(d)) == APP:
        # the running exe may live there: let cmd wait for us to exit, then remove the folder
        subprocess.Popen(f'cmd /c ping 127.0.0.1 -n 4 >nul & rmdir /s /q "{d}"',
                         creationflags=0x08000000, close_fds=True)
    return d
