# Screen Recorder - Copyright (C) 2026 TuanPA <tuanpa1702@gmail.com>
# SPDX-License-Identifier: GPL-3.0-only
# This program is free software under the GNU GPL v3; see LICENSE. It comes WITHOUT ANY WARRANTY.
"""Global hotkeys via a low-level keyboard hook (WH_KEYBOARD_LL).

RegisterHotKey cannot take combos Windows already owns (Win+Shift+S belongs to Snipping Tool),
a LL hook sees the key first and can swallow it.
"""
import ctypes, ctypes.wintypes as wt, threading

from PySide6.QtCore import QObject, Signal

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WH_KEYBOARD_LL = 13
WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x100, 0x101, 0x104, 0x105
LLKHF_INJECTED = 0x10
VK = dict(SHIFT=0x10, CTRL=0x11, ALT=0x12, LWIN=0x5B, RWIN=0x5C)
MOD_KEYS = {0x10, 0x11, 0x12, 0x5B, 0x5C, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5}

# preset hotkeys offered in the UI: label -> (mods set, vk)
PRESETS = [
    ("Win + Shift + S", ({"win", "shift"}, ord("S"))),
    ("Print Screen", (set(), 0x2C)),
    ("Ctrl + Shift + S", ({"ctrl", "shift"}, ord("S"))),
    ("Ctrl + Alt + S", ({"ctrl", "alt"}, ord("S"))),
    ("Win + Shift + A", ({"win", "shift"}, ord("A"))),
    ("Ctrl + Print Screen", ({"ctrl"}, 0x2C)),
]
PRESET_MAP = dict(PRESETS)


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wt.DWORD), ("scanCode", wt.DWORD), ("flags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wt.WPARAM, wt.LPARAM)
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wt.HINSTANCE, wt.DWORD]
user32.SetWindowsHookExW.restype = wt.HHOOK
user32.CallNextHookEx.argtypes = [wt.HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM]
user32.CallNextHookEx.restype = ctypes.c_ssize_t
user32.GetAsyncKeyState.restype = ctypes.c_short


def _down(vk):
    return user32.GetAsyncKeyState(vk) & 0x8000 != 0


def _mods_now():
    m = set()
    if _down(VK["SHIFT"]): m.add("shift")
    if _down(VK["CTRL"]): m.add("ctrl")
    if _down(VK["ALT"]): m.add("alt")
    if _down(VK["LWIN"]) or _down(VK["RWIN"]): m.add("win")
    return m


class GlobalHotkeys(QObject):
    """bind(name, mods, vk); emits fired(name) on the Qt thread (queued signal)."""
    fired = Signal(str)

    def __init__(self):
        super().__init__()
        self.binds = {}          # name -> (frozenset mods, vk)
        self._swallow_up = set()
        self.tid = None
        self.ok = False
        self._proc = HOOKPROC(self._hook)   # keep a reference or the callback is GC'd
        self._th = threading.Thread(target=self._run, daemon=True)
        self._ready = threading.Event()
        self._th.start()
        self._ready.wait(2)

    def bind(self, name, mods, vk):
        if vk:
            self.binds[name] = (frozenset(mods), vk)
        else:
            self.binds.pop(name, None)

    def _hook(self, code, wparam, lparam):
        try:
            if code == 0:
                k = ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                vk = k.vkCode
                if vk != 0xFF and vk not in MOD_KEYS:     # 0xFF = our own dummy key
                    if wparam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                        mods = _mods_now()
                        for name, (m, v) in self.binds.items():
                            if v == vk and mods == m:
                                if "win" in m:
                                    # dummy key so releasing Win doesn't pop the Start menu
                                    user32.keybd_event(0xFF, 0, 0, 0); user32.keybd_event(0xFF, 0, 2, 0)
                                self._swallow_up.add(vk)
                                self.fired.emit(name)
                                return 1
                    elif wparam in (WM_KEYUP, WM_SYSKEYUP) and vk in self._swallow_up:
                        self._swallow_up.discard(vk)
                        return 1
        except Exception:
            pass
        return user32.CallNextHookEx(None, code, wparam, lparam)

    def _run(self):
        self.tid = kernel32.GetCurrentThreadId()
        h = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, None, 0)
        self.ok = bool(h)
        self._ready.set()
        msg = wt.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            pass
        if h:
            user32.UnhookWindowsHookEx(h)

    def stop(self):
        if self.tid:
            user32.PostThreadMessageW(self.tid, 0x0012, 0, 0)
            self._th.join(1)


def label(mods, vk):
    order = [("ctrl", "Ctrl"), ("alt", "Alt"), ("shift", "Shift"), ("win", "Win")]
    names = {0x2C: "Print Screen", 0x7A: "F11", 0x7B: "F12"}
    parts = [n for k, n in order if k in mods]
    parts.append(names.get(vk, chr(vk) if 0x30 <= vk <= 0x5A else f"VK{vk:02X}"))
    return " + ".join(parts)
