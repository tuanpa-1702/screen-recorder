# Screen Recorder - Copyright (C) 2026 TuanPA <tuanpa1702@gmail.com>
# SPDX-License-Identifier: GPL-3.0-only
# This program is free software under the GNU GPL v3; see LICENSE. It comes WITHOUT ANY WARRANTY.
"""Screen Recorder - PySide6 GUI. © 2026 TuanPA"""
import ctypes, ctypes.wintypes as wt, os, sys, threading, time, datetime, subprocess

from PySide6.QtCore import Qt, QTimer, QRect, QPoint, Signal, QObject, QSettings, QStandardPaths
from PySide6.QtGui import QPainter, QColor, QPen, QGuiApplication, QFont, QIcon, QPixmap, QKeySequence
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
                               QPushButton, QComboBox, QCheckBox, QGroupBox, QSlider, QLineEdit,
                               QFileDialog, QMessageBox, QProgressBar, QRadioButton, QButtonGroup,
                               QSystemTrayIcon, QMenu, QSpinBox, QFrame, QStackedWidget, QSizePolicy, QScrollArea)
from PySide6.QtCore import QSize

import rec_core
import theme
import i18n
import installer
import hotkeys
import snip
import editor
import monitor_map
from i18n import T

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "TuanPA.ScreenRecorder"

APP = "Screen Recorder"
VER = "1.0.2"
REPO_URL = "https://github.com/tuanpa-1702/screen-recorder"
# The shipped exe is a small launcher that runs the app from a cache folder; it passes its own path here
LAUNCHER = os.environ.get("SR_LAUNCHER") or (sys.executable if getattr(sys, "frozen", False) else None)
APP_DIR = os.path.dirname(LAUNCHER) if LAUNCHER else os.path.dirname(os.path.abspath(__file__))


def settings():
    p = os.path.join(APP_DIR, "ScreenRecorder.ini")
    try:
        open(p, "a").close()
    except OSError:
        p = os.path.join(os.environ.get("APPDATA", APP_DIR), "ScreenRecorder.ini")
    return QSettings(p, QSettings.IniFormat)


RESOLUTIONS = [("Gốc (giữ nguyên)", 0), ("2160p (4K)", 2160), ("1440p (2K)", 1440), ("1080p (Full HD)", 1080),
               ("720p (HD)", 720), ("480p", 480), ("360p", 360)]
FPS = [10, 15, 24, 25, 30, 50, 60]
QUALITY = [("Rất cao", 16), ("Cao", 20), ("Trung bình", 24), ("Thấp (file nhỏ)", 30)]

def card(title, icon_name):
    """Glass card with an icon + uppercase section title. Returns (frame, body_layout)."""
    f = QFrame(); f.setObjectName("card")
    v = QVBoxLayout(f); v.setContentsMargins(14, 10, 14, 12); v.setSpacing(8)
    h = QHBoxLayout(); h.setSpacing(6)
    ic = QLabel(); ic.setPixmap(theme.icon(icon_name, theme.ACCENT).pixmap(18, 18))
    t = QLabel(title.upper()); t.setObjectName("sec")
    h.addWidget(ic); h.addWidget(t); h.addStretch()
    v.addLayout(h)
    return f, v


# ---------------- global hotkeys ----------------
class HotkeyThread(QObject):
    fired = Signal(int)

    def start(self, keys):
        """keys: {id: (mods, vk)}"""
        self.keys = keys
        self.tid = None
        self.th = threading.Thread(target=self._run, daemon=True)
        self.th.start()

    def _run(self):
        u = ctypes.windll.user32
        self.tid = ctypes.windll.kernel32.GetCurrentThreadId()
        self.failed = [i for i, (m, vk) in self.keys.items() if not u.RegisterHotKey(None, i, m | 0x4000, vk)]
        msg = wt.MSG()
        while u.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == 0x0312:
                self.fired.emit(msg.wParam)
        for i in self.keys:
            u.UnregisterHotKey(None, i)

    def stop(self):
        if self.tid:
            ctypes.windll.user32.PostThreadMessageW(self.tid, 0x0012, 0, 0)
            self.th.join(1)


# ---------------- region selection overlay ----------------
def logical_to_physical(screen, rect):
    """QRect in a screen's logical coords -> physical (x,y,w,h)."""
    g = screen.geometry()
    dpr = screen.devicePixelRatio()
    ox, oy = monitor_map.phys_origin(screen)
    return (ox + round((rect.x() - g.x()) * dpr), oy + round((rect.y() - g.y()) * dpr),
            round(rect.width() * dpr), round(rect.height() * dpr))


class RegionOverlay(QWidget):
    done = Signal(object)  # (x,y,w,h) physical or None

    def __init__(self, screen, siblings):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self.scr = screen
        self.siblings = siblings
        self.setGeometry(screen.geometry())
        self.p0 = self.p1 = None

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 110))
        if self.p0 and self.p1:
            r = QRect(self.p0, self.p1).normalized()
            p.setCompositionMode(QPainter.CompositionMode_Clear)
            p.fillRect(r, Qt.transparent)
            p.setCompositionMode(QPainter.CompositionMode_SourceOver)
            p.setPen(QPen(QColor("#ef4444"), 2))
            p.drawRect(r.adjusted(-1, -1, 0, 0))
            _, _, w, h = logical_to_physical(self.scr, r.translated(self.geometry().topLeft()))
            p.setPen(Qt.white)
            p.setFont(QFont("Segoe UI", 10, QFont.Bold))
            p.drawText(r.x() + 4, max(r.y() - 6, 14), f"{w} × {h}")
        else:
            p.setPen(Qt.white)
            p.setFont(QFont("Segoe UI", 14))
            p.drawText(self.rect(), Qt.AlignCenter, T("Kéo chuột để chọn vùng quay  •  Esc để huỷ"))

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            return self.finish(None)
        self.p0 = self.p1 = e.position().toPoint(); self.update()

    def mouseMoveEvent(self, e):
        if self.p0:
            self.p1 = e.position().toPoint(); self.update()

    def mouseReleaseEvent(self, e):
        if not self.p0:
            return
        r = QRect(self.p0, self.p1).normalized()
        if r.width() < 16 or r.height() < 16:
            self.p0 = self.p1 = None; self.update(); return
        self.finish(logical_to_physical(self.scr, r.translated(self.geometry().topLeft())))

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.finish(None)

    def finish(self, res):
        for w in self.siblings:
            w.close()
        self.done.emit(res)


class BorderFrame(QWidget):
    """Red click-through frame drawn just OUTSIDE the recorded area."""

    def __init__(self, phys):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool |
                         Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        x, y, w, h = phys
        scr = QGuiApplication.screenAt(QPoint(0, 0))
        # find screen containing the physical point
        for s in QGuiApplication.screens():
            gx, gy, gw, gh = logical_to_physical(s, s.geometry())
            if gx <= x < gx + gw and gy <= y < gy + gh:
                scr = s; break
        dpr = scr.devicePixelRatio()
        gx, gy, _, _ = logical_to_physical(scr, scr.geometry())
        g = scr.geometry()
        lx, ly = g.x() + (x - gx) / dpr, g.y() + (y - gy) / dpr
        b = 3
        self.setGeometry(int(lx) - b, int(ly) - b, int(w / dpr) + 2 * b, int(h / dpr) + 2 * b)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setPen(QPen(QColor("#ef4444"), 3, Qt.DashLine))
        p.drawRect(self.rect().adjusted(1, 1, -2, -2))


# ---------------- main window ----------------
class Main(QWidget):
    stopped = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self.setWindowTitle(f"{APP} v{VER}")
        self.setWindowIcon(make_icon())
        self.s = settings()
        self.rec = None
        self.region = None
        self.frame = None
        self.countdown_left = 0
        self._quitting = False
        self._switching = False
        self.editors = []
        self.snipper = snip.SnipController()
        self.snipper.captured.connect(self.on_snip)
        self.ghk = hotkeys.GlobalHotkeys()
        self.ghk.fired.connect(lambda name: self.start_snip() if name == "snip" else None)
        self.build()
        self.load()
        app = QGuiApplication.instance()
        app.screenAdded.connect(self.on_screens_changed); app.screenRemoved.connect(self.on_screens_changed)
        self.stopped.connect(self.on_stopped)
        self.timer = QTimer(self, interval=200, timeout=self.tick)
        self.timer.start()
        threading.Thread(target=self._probe_encoders, daemon=True).start()
        self.hk = HotkeyThread()
        self.hk.fired.connect(self.on_hotkey)
        # F12 rec/stop, Shift+F12 pause (no F11: it would steal browser full-screen)
        self.hk.start({1: (0, 0x7B), 2: (0x4, 0x7B)})
        self.tray = QSystemTrayIcon(make_icon(), self)
        m = QMenu()
        m.addAction(theme.icon("scissors"), T("Chụp ảnh màn hình"), lambda: self.start_snip())
        m.addAction(theme.icon("rec", "#dc2626"), T("Bắt đầu / Dừng (F12)"), self.toggle_rec)
        m.addSeparator()
        m.addAction(T("Hiện cửa sổ"), self.show_main)
        m.addAction(T("Thoát"), self.quit_app)
        self.tray.setContextMenu(m)
        self.tray.activated.connect(lambda r: self.show_main() if r == QSystemTrayIcon.Trigger else None)
        self.tray.setToolTip(APP)
        self.tray.show()

    # ---- tray / lifetime ----
    def show_main(self):
        self.restore_win(); self.raise_(); self.activateWindow()

    # ---- adaptive layout: the record page always fits the window without scrolling ----
    def resizeEvent(self, e):
        super().resizeEvent(e)
        QTimer.singleShot(0, self.fit_layout); QTimer.singleShot(200, self.fit_layout)

    def fit_layout(self):
        if not hasattr(self, "v_grid"):
            return
        cols = 2 if self.width() >= 1150 else 1
        if cols != self.v_cols:
            self.v_cols = cols
            for g in self.v_cards:
                self.v_grid.removeWidget(g)
            t, vid, aud, out = self.v_cards
            if cols == 2:      # left: target + output, right: video + audio
                self.v_grid.addWidget(t, 0, 0); self.v_grid.addWidget(out, 1, 0)
                self.v_grid.addWidget(vid, 0, 1); self.v_grid.addWidget(aud, 1, 1)
                self.v_grid.setColumnStretch(0, 1); self.v_grid.setColumnStretch(1, 1)
                self.inner.setMaximumWidth(1500)
            else:
                for r, g in enumerate(self.v_cards):
                    self.v_grid.addWidget(g, r, 0)
                self.v_grid.setColumnStretch(1, 0)
                self.inner.setMaximumWidth(980)
        # compact spacing + shrink the monitor map until the page fits the visible height
        avail = self.scroll.viewport().height()
        for sp, mh in ((10, 140), (6, 140), (6, 110), (4, 90), (4, 70)):
            for lay in (self.L, self.PV, self.v_grid):
                lay.setSpacing(sp)
            self.mon_map.setFixedHeight(mh)
            self.inner.layout().activate()
            if self.scroll.widget().minimumSizeHint().height() <= avail:
                break

    def restore_win(self):
        # un-minimize but keep the maximized state
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized); self.show()

    def quit_app(self):
        self._quitting = True
        self.close()

    def set_tab(self, i):
        self.stack.setCurrentIndex(i)
        for j in range(self.stack.count()):      # stack takes the height of the visible tab only
            pol = QSizePolicy.Preferred if j == i else QSizePolicy.Ignored
            self.stack.widget(j).setSizePolicy(pol, pol)
        self.stack.adjustSize(); QTimer.singleShot(0, self.fit_layout)
        for j, b in enumerate(self.tab_btns):
            b.setChecked(j == i); b.setIcon(theme.icon(b.property("ic"), "white" if j == i else "#334155"))

    # ---- snipping ----
    def apply_snip_hotkey(self):
        key = self.cb_snip_key.currentData()
        if key == "off" or key not in hotkeys.PRESET_MAP:
            self.ghk.bind("snip", set(), 0)
            self.lbl_key_hint.setText(T("Phím tắt đang tắt. Dùng nút Chụp ngay hoặc menu ở khay hệ thống."))
            return
        mods, vk = hotkeys.PRESET_MAP[key]
        self.ghk.bind("snip", mods, vk)
        self.lbl_status.setText(T("Phím tắt:  F12 bắt đầu/dừng  •  Shift+F12 tạm dừng") + f"  •  {key} " + T("chụp ảnh"))
        txt = T(f"Nhấn {key} ở bất cứ đâu để chụp. App cần đang chạy (cửa sổ đóng thì vẫn chạy ở khay hệ thống).")
        if key == "Win + Shift + S":
            txt += "\n" + T("Tổ hợp này thay thế Snipping Tool của Windows khi Screen Recorder đang chạy.")
        elif key == "Print Screen":
            txt += "\n" + T("Nếu Windows vẫn mở Snipping Tool: Settings › Accessibility › Keyboard › tắt “Use the Print screen key to open screen capture”.")
        if not self.ghk.ok:
            txt = "⚠ " + T("Không cài được phím tắt toàn cục trên máy này.")
        self.lbl_key_hint.setText(txt)

    def apply_autostart(self, on):
        import winreg
        try:
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_WRITE) as k:
                if on and getattr(sys, "frozen", False):
                    winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, f'"{LAUNCHER}" --tray')
                else:
                    try:
                        winreg.DeleteValue(k, RUN_NAME)
                    except OSError:
                        pass
        except OSError as e:
            self.lbl_status.setText(str(e))

    def start_snip(self, mode=None):
        if self.snipper.active:
            return
        self.snipper.start(self.cb_delay.currentData() or 0, mode or self.cb_snip_mode.currentData())

    def snip_dir(self):
        d = self.ed_snip_out.text().strip() or os.path.join(self.out_dir(), "Screenshots")
        os.makedirs(d, exist_ok=True)
        return d

    def pick_snip_folder(self):
        d = QFileDialog.getExistingDirectory(self, T("Chọn thư mục lưu ảnh"), self.snip_dir())
        if d: self.ed_snip_out.setText(os.path.normpath(d))

    def on_snip(self, img):
        QGuiApplication.clipboard().setImage(img)
        saved = None
        if self.chk_snip_save.isChecked():
            saved = os.path.join(self.snip_dir(), datetime.datetime.now().strftime("Snip_%Y-%m-%d_%H-%M-%S.png"))
            img.save(saved)
        ed = None
        if self.chk_snip_edit.isChecked():
            ed = self.open_editor(img, saved)
        if self.chk_snip_toast.isChecked():
            text = T("Đã copy vào bộ nhớ tạm – dán bằng Ctrl+V.")
            if saved:
                text += "\n" + T("Đã lưu: ") + os.path.basename(saved)
            acts = [] if ed else [(T("Chỉnh sửa"), lambda: self.open_editor(img, saved))]
            if saved:
                acts.append((T("Mở thư mục"), lambda: subprocess.Popen(["explorer", "/select,", saved])))
            else:
                acts.append((T("Lưu"), lambda: self._quick_save(img)))
            self._toast = snip.Toast(img, T("Đã chụp ảnh màn hình"), text, acts)
            self._toast.show()

    def _quick_save(self, img):
        p = os.path.join(self.snip_dir(), datetime.datetime.now().strftime("Snip_%Y-%m-%d_%H-%M-%S.png"))
        img.save(p)
        self.tray.showMessage(APP, T("Đã lưu: ") + p, QSystemTrayIcon.Information, 2500)

    def open_editor(self, img, saved=None):
        ed = editor.Editor(img, self.snip_dir())
        ed.saved_path = saved
        ed.new_snip.connect(lambda: self.start_snip())
        ed.destroyed.connect(lambda *_: self.editors.remove(ed) if ed in self.editors else None)
        self.editors.append(ed)
        ed.show(); ed.raise_(); ed.activateWindow()
        return ed

    # ---- UI ----
    def build(self):
        I = theme.icon
        # content column: max ~980 px wide, centered, so a maximized window on a big screen stays tidy
        # whole content scrolls, so the window can be any size (REC never ends up off-screen)
        top = QVBoxLayout(self); top.setContentsMargins(0, 0, 0, 0)
        sa = self.scroll = QScrollArea(); sa.setWidgetResizable(True); sa.setFrameShape(QFrame.NoFrame)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sa.setStyleSheet("QScrollArea{background:transparent}")
        host = QWidget(); host.setObjectName("scrollhost"); host.setStyleSheet("#scrollhost{background:transparent}")
        sa.setWidget(host); top.addWidget(sa)
        outer = QHBoxLayout(host); outer.setContentsMargins(0, 0, 0, 0)
        inner = self.inner = QWidget(); inner.setMaximumWidth(980)
        outer.addStretch(1); outer.addWidget(inner, 100); outer.addStretch(1)
        L = self.L = QVBoxLayout(inner); L.setContentsMargins(16, 12, 16, 14); L.setSpacing(10)

        head = QHBoxLayout(); head.setSpacing(10)
        logo = QLabel(); logo.setPixmap(theme.app_icon(128).scaled(52, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        tt = QVBoxLayout(); tt.setSpacing(0); tt.setContentsMargins(0, 0, 0, 0)
        t1 = QLabel(APP); t1.setObjectName("title")
        tag = QLabel("by TuanPA"); tag.setObjectName("tag")
        t2 = QLabel(T(f"v{VER} • Quay màn hình & chụp ảnh")); t2.setObjectName("sub")
        for lb in (t1, tag, t2):
            lb.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            tt.addWidget(lb)
        self.btn_lang = QPushButton("EN" if i18n.LANG == "vi" else "VI"); self.btn_lang.setObjectName("pill")
        self.btn_lang.setToolTip(T("Chuyển ngôn ngữ")); self.btn_lang.clicked.connect(self.switch_lang)
        self.btn_install = QPushButton(); self.btn_install.setObjectName("pill")
        self.btn_install.clicked.connect(self.install_toggle)
        self.update_install_btn()
        rt = QVBoxLayout(); rt.setSpacing(6)
        r2 = QHBoxLayout(); r2.addStretch(); r2.addWidget(self.btn_install); r2.addWidget(self.btn_lang)
        rt.addLayout(r2); rt.addStretch()
        logo.setFixedSize(52, 52)
        head.addWidget(logo, 0, Qt.AlignVCenter); head.addLayout(tt); head.addStretch(); head.addLayout(rt)
        L.addLayout(head)

        # --- tabs: video / snip ---
        tabs = QHBoxLayout(); tabs.setSpacing(8)
        self.tab_btns = []
        tg = QButtonGroup(self)
        for i, (txt, ic) in enumerate([(T("Quay video"), "video"), (T("Chụp ảnh"), "scissors")]):
            b = QPushButton(" " + txt); b.setObjectName("mode"); b.setCheckable(True); b.setIconSize(QSize(20, 20))
            b.setProperty("ic", ic); tg.addButton(b); self.tab_btns.append(b); tabs.addWidget(b)
            b.clicked.connect(lambda _=False, i=i: self.set_tab(i))
        L.addLayout(tabs)
        self.stack = QStackedWidget()
        page_v = QWidget(); PV = self.PV = QVBoxLayout(page_v); PV.setContentsMargins(0, 0, 0, 0); PV.setSpacing(10)
        self.v_cards = []
        page_s = QWidget(); PS = QVBoxLayout(page_s); PS.setContentsMargins(0, 0, 0, 0); PS.setSpacing(10)
        self.stack.addWidget(page_v); self.stack.addWidget(page_s)
        L.addWidget(self.stack)

        # --- target ---
        g, gl = card(T("Vùng quay"), "crop")
        row = QHBoxLayout(); row.setSpacing(8)
        self.mode_grp = QButtonGroup(self)
        self.btn_modes = {}
        for key, txt, ic in [("monitor", T("Toàn màn hình"), "monitor"), ("region", T("Vùng chọn"), "region"),
                             ("window", T("Cửa sổ"), "window")]:
            b = QPushButton(txt); b.setObjectName("mode"); b.setCheckable(True)
            b.setIconSize(QSize(20, 20)); b.setProperty("ic", ic)
            self.mode_grp.addButton(b); self.btn_modes[key] = b; row.addWidget(b)
            b.clicked.connect(lambda _=False, k=key: self.set_mode(k))
        gl.addLayout(row)
        self.cb_monitor = QComboBox()
        self.btn_region = QPushButton(I("region"), T(" Chọn vùng…")); self.btn_region.setIconSize(QSize(18, 18))
        self.btn_region.clicked.connect(self.pick_region)
        self.lbl_region = QLabel(T("Chưa chọn vùng")); self.lbl_region.setObjectName("hint")
        rgx = QHBoxLayout(); rgx.setSpacing(6)
        self.sp = {}
        for k in ("X", "Y", "W", "H"):
            sp = QSpinBox(); sp.setRange(-20000, 20000); sp.setPrefix(k + "  ")
            sp.valueChanged.connect(self.region_from_spins); self.sp[k] = sp; rgx.addWidget(sp)
        self.cb_preset = QComboBox()
        self.cb_preset.addItems([T(x) for x in ["Kích thước nhanh…", "1920×1080", "1280×720", "854×480", "1080×1920 (dọc)", "800×800"]])
        self.cb_preset.activated.connect(self.apply_preset)
        rgx.addWidget(self.cb_preset)
        self.cb_window = QComboBox(); self.cb_window.setMinimumWidth(300)
        self.btn_refresh = QPushButton(I("refresh"), ""); self.btn_refresh.setObjectName("icon")
        self.btn_refresh.setToolTip(T("Làm mới danh sách cửa sổ"))
        self.btn_refresh.clicked.connect(self.fill_windows)
        self.w_mon = QWidget(); vm = QVBoxLayout(self.w_mon); vm.setContentsMargins(0, 0, 0, 0); vm.setSpacing(6)
        self.mon_map = monitor_map.MonitorMap()
        self.mon_map.all_label = T("Tất cả màn hình")
        self.mon_map.picked.connect(self.cb_monitor.setCurrentIndex)
        self.cb_monitor.currentIndexChanged.connect(lambda i: (setattr(self.mon_map, "sel", i), self.mon_map.update()))
        vm.addWidget(self.mon_map)
        h = QHBoxLayout(); h.setSpacing(8)
        h.addWidget(QLabel(T("Màn hình"))); h.addWidget(self.cb_monitor, 1)
        b_id = QPushButton(I("monitor"), " " + T("Nhận diện")); b_id.setToolTip(T("Hiện số thứ tự trên từng màn hình"))
        b_id.clicked.connect(self.identify_monitors); h.addWidget(b_id)
        vm.addLayout(h)
        self.w_reg = QWidget(); v = QVBoxLayout(self.w_reg); v.setContentsMargins(0, 0, 0, 0)
        h2 = QHBoxLayout(); h2.addWidget(self.btn_region); h2.addWidget(self.lbl_region, 1); v.addLayout(h2); v.addLayout(rgx)
        self.w_win = QWidget(); h3 = QHBoxLayout(self.w_win); h3.setContentsMargins(0, 0, 0, 0)
        h3.addWidget(QLabel(T("Cửa sổ"))); h3.addWidget(self.cb_window, 1); h3.addWidget(self.btn_refresh)
        for w in (self.w_mon, self.w_reg, self.w_win):
            gl.addWidget(w)
        self.v_cards.append(g)

        # --- video ---
        g, gv = card("Video", "video"); gr = QGridLayout(); gr.setHorizontalSpacing(10); gr.setVerticalSpacing(8)
        gv.addLayout(gr)
        self.cb_res = QComboBox(); [self.cb_res.addItem(T(a), b) for a, b in RESOLUTIONS]
        self.cb_fps = QComboBox(); [self.cb_fps.addItem(f"{f} fps", f) for f in FPS]
        self.cb_q = QComboBox(); [self.cb_q.addItem(T(a), b) for a, b in QUALITY]
        self.cb_enc = QComboBox(); self.cb_enc.addItem("H.264 (CPU)", "libx264")
        self.cb_fmt = QComboBox(); self.cb_fmt.addItem("MP4", "mp4"); self.cb_fmt.addItem(T("MKV (an toàn khi mất điện)"), "mkv")
        self.chk_cursor = QCheckBox(T("Quay con trỏ chuột"))
        self.chk_count = QCheckBox(T("Đếm ngược 3 giây"))
        self.chk_min = QCheckBox(T("Thu nhỏ cửa sổ khi quay"))
        gr.addWidget(QLabel(T("Độ phân giải")), 0, 0); gr.addWidget(self.cb_res, 0, 1)
        gr.addWidget(QLabel(T("Khung hình")), 0, 2); gr.addWidget(self.cb_fps, 0, 3)
        gr.addWidget(QLabel(T("Chất lượng")), 1, 0); gr.addWidget(self.cb_q, 1, 1)
        gr.addWidget(QLabel(T("Bộ mã hoá")), 1, 2); gr.addWidget(self.cb_enc, 1, 3)
        gr.addWidget(QLabel(T("Định dạng")), 2, 0); gr.addWidget(self.cb_fmt, 2, 1)
        chk_row = QHBoxLayout(); chk_row.setSpacing(24)
        for c in (self.chk_count, self.chk_cursor, self.chk_min):
            chk_row.addWidget(c)
        chk_row.addStretch()
        gr.addLayout(chk_row, 3, 0, 1, 4)
        gr.setColumnStretch(1, 1); gr.setColumnStretch(3, 1)
        self.v_cards.append(g)

        # --- audio ---
        g, ga = card(T("Âm thanh"), "speaker"); gr = QGridLayout(); gr.setHorizontalSpacing(10); gr.setVerticalSpacing(8)
        ga.addLayout(gr)
        self.chk_sys = QCheckBox(T("Âm thanh hệ thống")); self.chk_sys.setIcon(I("speaker"))
        self.cb_sys = QComboBox()
        self.chk_mic = QCheckBox("Micro"); self.chk_mic.setIcon(I("mic"))
        self.cb_mic = QComboBox()
        self.lv_sys = QProgressBar(); self.lv_sys.setTextVisible(False); self.lv_sys.setFixedWidth(90)
        self.lv_mic = QProgressBar(); self.lv_mic.setTextVisible(False); self.lv_mic.setFixedWidth(90)
        gr.addWidget(self.chk_sys, 0, 0); gr.addWidget(self.cb_sys, 0, 1); gr.addWidget(self.lv_sys, 0, 2)
        gr.addWidget(self.chk_mic, 1, 0); gr.addWidget(self.cb_mic, 1, 1); gr.addWidget(self.lv_mic, 1, 2)
        gr.setColumnStretch(1, 1)
        self.v_cards.append(g)

        # --- snip settings (page 2) ---
        g, gs = card(T("Chụp ảnh màn hình"), "scissors")
        gr = QGridLayout(); gr.setHorizontalSpacing(10); gr.setVerticalSpacing(10); gs.addLayout(gr)
        self.cb_snip_key = QComboBox()
        for lbl, _ in hotkeys.PRESETS:
            self.cb_snip_key.addItem(lbl, lbl)
        self.cb_snip_key.addItem(T("Tắt phím tắt"), "off")
        self.cb_snip_key.currentIndexChanged.connect(self.apply_snip_hotkey)
        self.cb_delay = QComboBox()
        for d in (0, 3, 5, 10):
            self.cb_delay.addItem(T("Không hẹn giờ") if d == 0 else T(f"Hẹn giờ {d} giây"), d)
        self.cb_snip_mode = QComboBox()
        for k, txt in [("rect", T("Vùng chữ nhật")), ("free", T("Tự do (theo nét kéo chuột)")), ("window", T("Cửa sổ")), ("full", T("Toàn màn hình"))]:
            self.cb_snip_mode.addItem(txt, k)
        gr.addWidget(QLabel(T("Phím tắt")), 0, 0); gr.addWidget(self.cb_snip_key, 0, 1)
        gr.addWidget(QLabel(T("Chế độ mặc định")), 1, 0); gr.addWidget(self.cb_snip_mode, 1, 1)
        gr.addWidget(QLabel(T("Hẹn giờ")), 2, 0); gr.addWidget(self.cb_delay, 2, 1)
        gr.setColumnStretch(1, 1)
        self.lbl_key_hint = QLabel(); self.lbl_key_hint.setObjectName("hint"); self.lbl_key_hint.setWordWrap(True)
        gs.addWidget(self.lbl_key_hint)
        PS.addWidget(g)
        g, gs2 = card(T("Sau khi chụp"), "settings")
        self.chk_snip_edit = QCheckBox(T("Mở trình chỉnh sửa ảnh"))
        self.chk_snip_save = QCheckBox(T("Tự động lưu ảnh vào thư mục bên dưới"))
        self.chk_snip_toast = QCheckBox(T("Hiện thông báo (ảnh luôn được copy vào bộ nhớ tạm)"))
        self.chk_autostart = QCheckBox(T("Khởi động cùng Windows (chạy nền ở khay hệ thống để phím tắt luôn hoạt động)"))
        self.chk_autostart.toggled.connect(self.apply_autostart)
        for c in (self.chk_snip_edit, self.chk_snip_save, self.chk_snip_toast, self.chk_autostart):
            gs2.addWidget(c)
        PS.addWidget(g)
        g, gs3 = card(T("Mẹo sử dụng"), "select")
        tips = QLabel(T("Khi chụp:  kéo chuột = chọn vùng  •  R / D / W / F = vùng / tự do / cửa sổ / toàn màn hình  •  "
                        "Enter = chụp cả màn hình  •  Esc hoặc chuột phải = huỷ\n"
                        "Trình chỉnh sửa:  V P H L A R E T N B C = công cụ  •  giữ Shift = vuông / thẳng góc  •  "
                        "kéo ô vuông = co giãn, chấm tròn = xoay  •  Ctrl+Z / Ctrl+Y  •  Ctrl+C copy  •  Ctrl+S lưu  •  Ctrl+lăn chuột = phóng to"))
        tips.setObjectName("hint"); tips.setWordWrap(True); gs3.addWidget(tips)
        PS.addWidget(g)
        self.btn_snip =QPushButton(I("scissors", "white"), "  " + T("Chụp ngay")); self.btn_snip.setObjectName("rec")
        self.btn_snip.setIconSize(QSize(20, 20)); self.btn_snip.clicked.connect(lambda: self.start_snip())
        rb = QHBoxLayout(); rb.addStretch(); rb.addWidget(self.btn_snip)
        PS.addLayout(rb)
        PS.addStretch()

        # --- output ---
        # video folder (Record tab) and screenshot folder (Snip tab) are set independently
        g, go = card(T("Lưu video vào"), "save"); h = QHBoxLayout(); go.addLayout(h)
        self.ed_out = QLineEdit()
        b1 = QPushButton(I("folder"), T(" Chọn…")); b1.clicked.connect(self.pick_folder)
        b2 = QPushButton(I("folder-open"), T(" Mở thư mục")); b2.clicked.connect(lambda: os.startfile(self.out_dir()))
        h.addWidget(self.ed_out, 1); h.addWidget(b1); h.addWidget(b2)
        self.v_cards.append(g)
        # record cards: 1 column on narrow/portrait windows, 2 columns on wide ones (see fit_layout)
        self.v_grid_w = QWidget(); self.v_grid = QGridLayout(self.v_grid_w)
        self.v_grid.setContentsMargins(0, 0, 0, 0); self.v_grid.setSpacing(10)
        PV.addWidget(self.v_grid_w)
        self.mon_map_h = 140; self.v_cols = 0
        g, gsd = card(T("Lưu ảnh vào"), "save"); h = QHBoxLayout(); gsd.addLayout(h)
        self.ed_snip_out = QLineEdit()
        b1 = QPushButton(I("folder"), T(" Chọn…")); b1.clicked.connect(self.pick_snip_folder)
        b2 = QPushButton(I("folder-open"), T(" Mở thư mục")); b2.clicked.connect(lambda: os.startfile(self.snip_dir()))
        h.addWidget(self.ed_snip_out, 1); h.addWidget(b1); h.addWidget(b2)
        PS.insertWidget(PS.count() - 2, g)       # above the "Snip now" row
        self.cards = [w for w in self.findChildren(QFrame) if w.objectName() == "card"]

        # --- controls bar ---
        bar = QFrame(); bar.setObjectName("bar")
        h = QHBoxLayout(bar); h.setContentsMargins(16, 10, 12, 10); h.setSpacing(8)
        self.lbl_dot = QLabel(); self.lbl_dot.setFixedSize(12, 12)
        self.lbl_time = QLabel("00:00:00"); self.lbl_time.setObjectName("timer")
        self.lbl_info = QLabel(T("Sẵn sàng")); self.lbl_info.setObjectName("hint")
        tv = QVBoxLayout(); tv.setSpacing(0)
        tr = QHBoxLayout(); tr.setSpacing(8); tr.addWidget(self.lbl_dot); tr.addWidget(self.lbl_time); tr.addStretch()
        tv.addLayout(tr); tv.addWidget(self.lbl_info)
        h.addLayout(tv); h.addStretch()
        self.btn_shot = QPushButton(I("camera"), T(" Chụp")); self.btn_shot.setToolTip(T("Chụp ảnh màn hình"))
        self.btn_pause = QPushButton(I("pause"), T(" Tạm dừng")); self.btn_pause.setEnabled(False)
        self.btn_pause.setToolTip(T("Tạm dừng / tiếp tục (Shift+F12)"))
        self.btn_rec = QPushButton(I("rec", "white"), "  REC"); self.btn_rec.setObjectName("rec")
        self.btn_rec.setToolTip(T("Bắt đầu / dừng quay (F12)"))
        for b in (self.btn_shot, self.btn_pause):
            b.setIconSize(QSize(18, 18)); b.setMinimumHeight(38)
        self.btn_rec.setIconSize(QSize(20, 20))
        self.btn_shot.clicked.connect(lambda: self.start_snip())
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.btn_rec.clicked.connect(self.toggle_rec)
        h.addWidget(self.btn_shot); h.addWidget(self.btn_pause); h.addWidget(self.btn_rec)
        PV.addWidget(bar)
        self.lbl_status = QLabel(T("Phím tắt:  F12 bắt đầu/dừng  •  Shift+F12 tạm dừng"))
        self.lbl_status.setObjectName("hint"); self.lbl_status.setWordWrap(True)
        L.addWidget(self.lbl_status)
        lic = QLabel(f"© 2026 TuanPA • {T('Phần mềm tự do')} GPL-3.0 • "
                     f"<a href='lic' style='color:#2563eb;text-decoration:none'>{T('Giấy phép')}</a> • "
                     f"<a href='{REPO_URL}' style='color:#2563eb;text-decoration:none'>{T('Mã nguồn')}</a>")
        lic.setObjectName("hint"); lic.setTextInteractionFlags(Qt.TextBrowserInteraction)
        lic.linkActivated.connect(self.open_link)
        L.addWidget(lic)
        L.addStretch(1)            # extra height goes here, never into the header
        self.setMinimumSize(560, 360)
        self.set_dot(None)

    # ---- language / install ----
    def switch_lang(self):
        if self.rec or self.countdown_left:
            return
        self.save()
        self.s.setValue("lang", "en" if i18n.LANG == "vi" else "vi"); self.s.sync()
        self._switching = True
        geo = self.geometry()
        self.close()
        start_main(geo)

    def update_install_btn(self):
        if installer.is_installed_copy():
            self.btn_install.setText(T(" Gỡ cài đặt")); self.btn_install.setIcon(theme.icon("trash", "#dc2626"))
        else:
            self.btn_install.setText(T(" Cài vào máy")); self.btn_install.setIcon(theme.icon("download", theme.ACCENT))
            if installer.is_installed():
                self.btn_install.setToolTip(T("Đã cài đặt") + ": " + installer.installed_dir())

    def install_toggle(self):
        if self.rec:
            return
        try:
            if installer.is_installed_copy():
                if not ask(self, T("Gỡ Screen Recorder khỏi máy? (Video đã quay không bị xoá)"), T("Gỡ"), T("Huỷ")):
                    return
                installer.uninstall()
                QMessageBox.information(self, APP, T("Đã gỡ cài đặt. Ứng dụng sẽ đóng."))
                self.apply_autostart(False)
                self.quit_app()
                return
            if not ask(self, T("Cài Screen Recorder cho tài khoản này (không cần quyền admin)?\n\nVị trí: %LOCALAPPDATA%\\Programs\\Screen Recorder\nTạo lối tắt ở Start Menu và Desktop, khởi động cùng Windows (tắt được ở tab Chụp ảnh)."),
                       T("Cài đặt"), T("Huỷ")):
                return
            self.save()
            dst = installer.install(VER)
            self.update_install_btn()
            # installed copy starts with Windows by default (tray only); can be turned off in the Snip tab
            import winreg
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_WRITE) as k:
                winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, f'"{dst}" --tray')
            self.chk_autostart.blockSignals(True); self.chk_autostart.setChecked(True); self.chk_autostart.blockSignals(False)
            if ask(self, T("Đã cài đặt xong. Mở bản đã cài ngay bây giờ?"), T("Có"), T("Không")):
                self.quit_app()
                release_single_instance()
                subprocess.Popen([dst], close_fds=True)
        except Exception as e:
            QMessageBox.critical(self, APP, T("Lỗi cài đặt:\n") + T(str(e)))

    def open_link(self, href):
        if href != "lic":
            os.startfile(href); return
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        d = os.path.join(base, "licenses")
        if os.path.isdir(d):
            os.startfile(d)
        else:
            os.startfile(REPO_URL)

    def set_dot(self, color):
        pm = QPixmap(24, 24); pm.fill(Qt.transparent)
        if color:
            p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
            p.setPen(Qt.NoPen); p.setBrush(QColor(color)); p.drawEllipse(2, 2, 20, 20); p.end()
        self.lbl_dot.setPixmap(pm.scaled(12, 12, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _probe_encoders(self):
        encs = rec_core.available_encoders()
        QTimer.singleShot(0, lambda: self._set_encoders(encs))

    def _set_encoders(self, encs):
        cur = self.s.value("encoder", "libx264")
        self.cb_enc.clear()
        for e, lbl in encs:
            self.cb_enc.addItem(lbl, e)
        i = self.cb_enc.findData(cur)
        self.cb_enc.setCurrentIndex(max(i, 0))

    def fill_monitors(self):
        prev = self.cb_monitor.currentIndex()
        self.cb_monitor.blockSignals(True)
        self.cb_monitor.clear()
        self.mons = rec_core.monitors()
        names = monitor_map.friendly_names(self.mons)
        for i, m in enumerate(self.mons):
            nm = f"{names[i]} • " if names[i] else ""
            self.cb_monitor.addItem(T(f"Màn hình {i + 1}{' (chính)' if m['primary'] else ''} — {nm}{m['w']}×{m['h']}"), i)
        if len(self.mons) > 1:
            x0 = min(m["x"] for m in self.mons); y0 = min(m["y"] for m in self.mons)
            x1 = max(m["x"] + m["w"] for m in self.mons); y1 = max(m["y"] + m["h"] for m in self.mons)
            self.mons.append(dict(name="all", x=x0, y=y0, w=x1 - x0, h=y1 - y0, primary=False))
            self.cb_monitor.addItem(T(f"Tất cả màn hình — {x1 - x0}×{y1 - y0}"), len(self.mons) - 1)
        self.mon_map.set_monitors(self.mons, names)
        self.cb_monitor.blockSignals(False)
        self.cb_monitor.setCurrentIndex(prev if 0 <= prev < self.cb_monitor.count() else 0)
        self.mon_map.sel = self.cb_monitor.currentIndex(); self.mon_map.update()

    def identify_monitors(self):
        self._ident = []
        for i, m in enumerate(self.mons):
            if m["name"] == "all":
                continue
            s = monitor_map.screen_for(m)
            if s is None:
                continue
            nm = monitor_map.friendly_names([m])[0]
            o = monitor_map.IdentifyOverlay(s, i + 1, (nm + "\n" if nm else "") + f"{m['w']}×{m['h']}")
            o.show(); self._ident.append(o)

    def on_screens_changed(self, *_):
        if self.rec:                      # never re-map while recording
            return
        QTimer.singleShot(500, self.fill_monitors)

    def fill_windows(self):
        self.cb_window.clear()
        me = self.windowTitle()
        for t, h in rec_core.windows():
            if t != me:
                self.cb_window.addItem(t[:90], (t, h))

    def fill_audio(self):
        try:
            spk, mic = rec_core.audio_devices()
        except Exception as e:
            spk, mic = [], []
            self.lbl_status.setText(T("Không đọc được thiết bị âm thanh: ") + str(e))
        self.cb_sys.clear(); self.cb_sys.addItem(T("Mặc định"), "")
        for n in spk: self.cb_sys.addItem(n, n)
        self.cb_mic.clear(); self.cb_mic.addItem(T("Mặc định"), "")
        for n in mic: self.cb_mic.addItem(n, n)

    def set_mode(self, k):
        self.mode = k
        self.btn_modes[k].setChecked(True)
        for key, b in self.btn_modes.items():
            b.setIcon(theme.icon(b.property("ic"), "white" if key == k else "#334155"))
        self.w_mon.setVisible(k == "monitor"); self.w_reg.setVisible(k == "region"); self.w_win.setVisible(k == "window")
        if k == "window" and self.cb_window.count() == 0:
            self.fill_windows()

    # ---- region ----
    def pick_region(self):
        self.hide()
        QTimer.singleShot(200, self._show_overlays)

    def _show_overlays(self):
        ovs = []
        for s in QGuiApplication.screens():
            ovs.append(RegionOverlay(s, ovs))
        for o in ovs:
            o.done.connect(self._region_done)
            o.show(); o.activateWindow()
        self._ovs = ovs

    def _region_done(self, r):
        self.restore_win(); self.activateWindow()
        if r:
            self.set_region(r)

    def set_region(self, r):
        self.region = tuple(int(v) for v in r)
        for k, v in zip("XYWH", self.region):
            self.sp[k].blockSignals(True); self.sp[k].setValue(v); self.sp[k].blockSignals(False)
        self.lbl_region.setText(T(f"Vùng: {self.region[2]}×{self.region[3]} tại ({self.region[0]}, {self.region[1]})"))

    def region_from_spins(self):
        self.set_region([self.sp[k].value() for k in "XYWH"])

    def apply_preset(self, i):
        if i == 0: return
        w, h = [int(x) for x in self.cb_preset.currentText().split(" ")[0].split("×")]
        x, y = (self.region[:2] if self.region else (0, 0))
        self.set_region((x, y, w, h)); self.cb_preset.setCurrentIndex(0)

    # ---- settings ----
    def out_dir(self):
        d = self.ed_out.text().strip() or default_out()
        os.makedirs(d, exist_ok=True)
        return d

    def pick_folder(self):
        d = QFileDialog.getExistingDirectory(self, T("Chọn thư mục lưu"), self.out_dir())
        if d: self.ed_out.setText(os.path.normpath(d))

    def load(self):
        s = self.s
        self.fill_monitors(); self.fill_audio()

        def sel(cb, v):
            i = cb.findData(v)
            if i >= 0: cb.setCurrentIndex(i)
        sel(self.cb_res, int(s.value("height", 0))); sel(self.cb_fps, int(s.value("fps", 30)))
        sel(self.cb_q, int(s.value("quality", 20))); sel(self.cb_fmt, s.value("fmt", "mp4"))
        sel(self.cb_sys, s.value("sys_dev", "")); sel(self.cb_mic, s.value("mic_dev", ""))
        self.cb_monitor.setCurrentIndex(min(int(s.value("monitor", 0)), self.cb_monitor.count() - 1))
        b = lambda k, d: str(s.value(k, d)).lower() == "true"
        self.chk_cursor.setChecked(b("cursor", True)); self.chk_count.setChecked(b("countdown", True))
        self.chk_min.setChecked(b("minimize", True))
        self.chk_sys.setChecked(b("sys_audio", True)); self.chk_mic.setChecked(b("mic", False))
        self.ed_out.setText(s.value("out", default_out()))
        # old versions saved screenshots in <video folder>\Screenshots: keep that as the default
        self.ed_snip_out.setText(s.value("snip_out", "") or os.path.join(self.ed_out.text() or default_out(), "Screenshots"))
        reg = s.value("region", "")
        if reg:
            try: self.set_region([int(x) for x in str(reg).split(",")])
            except ValueError: pass
        self.set_mode(s.value("mode", "monitor"))
        sel(self.cb_snip_key, s.value("snip_key", "Win + Shift + S"))
        sel(self.cb_delay, int(s.value("snip_delay", 0)))
        sel(self.cb_snip_mode, s.value("snip_mode", "rect"))
        self.chk_snip_edit.setChecked(b("snip_edit", True))
        self.chk_snip_save.setChecked(b("snip_save", False))
        self.chk_snip_toast.setChecked(b("snip_toast", True))
        self.chk_autostart.blockSignals(True)
        self.chk_autostart.setChecked(self._autostart_on())
        self.chk_autostart.blockSignals(False)
        self.chk_autostart.setEnabled(getattr(sys, "frozen", False))
        self.apply_snip_hotkey()
        self.set_tab(int(s.value("tab", 0)))

    def _autostart_on(self):
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
                winreg.QueryValueEx(k, RUN_NAME)
                return True
        except OSError:
            return False

    def save(self):
        s = self.s
        for k, v in dict(height=self.cb_res.currentData(), fps=self.cb_fps.currentData(), quality=self.cb_q.currentData(),
                         fmt=self.cb_fmt.currentData(), encoder=self.cb_enc.currentData(), sys_dev=self.cb_sys.currentData(),
                         mic_dev=self.cb_mic.currentData(), monitor=self.cb_monitor.currentIndex(),
                         cursor=self.chk_cursor.isChecked(), countdown=self.chk_count.isChecked(),
                         minimize=self.chk_min.isChecked(), sys_audio=self.chk_sys.isChecked(), mic=self.chk_mic.isChecked(),
                         out=self.ed_out.text(), snip_out=self.ed_snip_out.text(), mode=self.mode, snip_key=self.cb_snip_key.currentData(),
                         snip_delay=self.cb_delay.currentData(), snip_mode=self.cb_snip_mode.currentData(),
                         snip_edit=self.chk_snip_edit.isChecked(), snip_save=self.chk_snip_save.isChecked(),
                         snip_toast=self.chk_snip_toast.isChecked(), tab=self.stack.currentIndex(),
                         region=",".join(map(str, self.region)) if self.region else "").items():
            s.setValue(k, v)
        s.sync()

    # ---- recording ----
    def build_cfg(self):
        mode = self.mode
        cfg = dict(mode=mode, fps=self.cb_fps.currentData(), height=self.cb_res.currentData(),
                   encoder=self.cb_enc.currentData() or "libx264", quality=self.cb_q.currentData(),
                   cursor=self.chk_cursor.isChecked(), sys_audio=self.chk_sys.isChecked(), sys_dev=self.cb_sys.currentData(),
                   mic=self.chk_mic.isChecked(), mic_dev=self.cb_mic.currentData())
        if mode == "monitor":
            m = self.mons[self.cb_monitor.currentData() or 0]
            cfg["rect"] = (m["x"], m["y"], m["w"], m["h"])
        elif mode == "region":
            if not self.region:
                raise RuntimeError(T("Hãy chọn vùng quay trước."))
            cfg["rect"] = self.region
        else:
            d = self.cb_window.currentData()
            if not d:
                raise RuntimeError(T("Hãy chọn cửa sổ cần quay."))
            t, hwnd = d
            if not ctypes.windll.user32.IsWindow(wt.HWND(hwnd)):
                self.fill_windows()
                raise RuntimeError(T("Cửa sổ đã đóng, hãy chọn lại."))
            # record the window's area on the desktop (works for GPU apps / browsers, follows nothing if moved)
            cfg["mode"] = "region"
            cfg["rect"] = rec_core.window_rect(hwnd)
            ctypes.windll.user32.SetForegroundWindow(wt.HWND(hwnd))
        name = datetime.datetime.now().strftime("Rec_%Y-%m-%d_%H-%M-%S.") + self.cb_fmt.currentData()
        cfg["out_path"] = os.path.join(self.out_dir(), name)
        return cfg

    def toggle_rec(self):
        if self.countdown_left:
            self.countdown_left = 0; self.lbl_info.setText(T("Đã huỷ")); return
        if self.rec and self.rec.state in ("recording", "paused"):
            return self.stop_rec()
        if self.rec:  # stopping
            return
        try:
            self.cfg = self.build_cfg()
        except Exception as e:
            QMessageBox.warning(self, APP, str(e)); return
        self.save()
        if self.chk_count.isChecked():
            self.countdown_left = 3
            self._count()
        else:
            self.start_rec()

    def _count(self):
        if not self.countdown_left:
            return
        self.lbl_time.setText(f"   {self.countdown_left}…")
        self.tray.showMessage(APP, T(f"Bắt đầu quay sau {self.countdown_left}s"), QSystemTrayIcon.Information, 800)
        self.countdown_left -= 1
        if self.countdown_left == 0:
            QTimer.singleShot(1000, self.start_rec)
        else:
            QTimer.singleShot(1000, self._count)

    def start_rec(self):
        self.countdown_left = 0
        self.rec = rec_core.Recorder(self.cfg)
        try:
            self.rec.start()
        except Exception as e:
            self.rec = None
            QMessageBox.critical(self, APP, T(f"Không bắt đầu quay được:\n{e}")); return
        if self.cfg["mode"] == "region":
            self.frame = BorderFrame(self.cfg["rect"]); self.frame.show()
        self.btn_rec.setText(T("  DỪNG")); self.btn_rec.setIcon(theme.icon("stop", "white"))
        self.btn_rec.setProperty("recording", True)
        self.btn_rec.style().polish(self.btn_rec)
        self.btn_pause.setEnabled(True)
        self.set_inputs(False)
        self.tray.setToolTip(T(f"{APP} - đang quay"))
        if self.chk_min.isChecked():
            self.showMinimized()

    def toggle_pause(self):
        if not self.rec: return
        if self.rec.state == "recording":
            self.rec.pause(); self.btn_pause.setText(T(" Tiếp tục")); self.btn_pause.setIcon(theme.icon("play", "#16a34a"))
        elif self.rec.state == "paused":
            try:
                self.rec.resume(); self.btn_pause.setText(T(" Tạm dừng")); self.btn_pause.setIcon(theme.icon("pause"))
            except Exception as e:
                QMessageBox.critical(self, APP, str(e))

    def stop_rec(self):
        self.btn_rec.setEnabled(False); self.btn_pause.setEnabled(False)
        self.lbl_info.setText(T("Đang lưu file…"))
        if self.frame:
            self.frame.close(); self.frame = None
        rec = self.rec

        def work():
            try:
                out = rec.stop(); self.stopped.emit(out, rec.last_error)
            except Exception as e:
                self.stopped.emit("", str(e))
        threading.Thread(target=work, daemon=True).start()

    def on_stopped(self, out, err):
        self.rec = None
        self.btn_rec.setEnabled(True); self.btn_rec.setText("  REC"); self.btn_rec.setIcon(theme.icon("rec", "white"))
        self.btn_rec.setProperty("recording", False)
        self.btn_rec.style().polish(self.btn_rec)
        self.btn_pause.setText(T(" Tạm dừng")); self.btn_pause.setIcon(theme.icon("pause"))
        self.set_inputs(True)
        self.tray.setToolTip(APP)
        self.restore_win(); self.activateWindow()
        if out:
            mb = os.path.getsize(out) / 1048576
            self.lbl_status.setText(T(f"✔ Đã lưu: {out}  ({mb:.1f} MB)") + (T(f"\n⚠ Âm thanh: {err}") if err else ""))
            self.tray.showMessage(APP, T("Đã lưu ") + os.path.basename(out), QSystemTrayIcon.Information, 3000)
            if ask(self, T(f"Đã lưu video:\n{out}\n({mb:.1f} MB)\n\nMở thư mục chứa file?"), T("Mở thư mục"), T("Đóng")):
                subprocess.Popen(["explorer", "/select,", out])
        else:
            QMessageBox.critical(self, APP, T("Lỗi khi lưu:\n") + err)

    def set_inputs(self, on):
        for w in self.cards:
            w.setEnabled(on)

    def screenshot(self):
        try:
            cfg = self.build_cfg()
        except Exception as e:
            QMessageBox.warning(self, APP, str(e)); return
        x, y, w, h = cfg["rect"]
        out = os.path.join(self.out_dir(), datetime.datetime.now().strftime("Shot_%Y-%m-%d_%H-%M-%S.png"))
        r = rec_core.run_ff(["-y", "-f", "gdigrab", "-draw_mouse", "1" if cfg["cursor"] else "0",
                             "-offset_x", str(x), "-offset_y", str(y), "-video_size", f"{w}x{h}",
                             "-i", "desktop", "-frames:v", "1", out])
        if r.returncode == 0:
            self.lbl_status.setText(T("📷 Đã chụp: ") + out)
            self.tray.showMessage(APP, T("Đã chụp ") + os.path.basename(out), QSystemTrayIcon.Information, 2000)
        else:
            self.lbl_status.setText(T("Chụp lỗi: ") + r.stderr.decode("utf-8", "replace")[-300:])

    def on_hotkey(self, i):
        if i == 1: self.toggle_rec()
        elif i == 2: self.toggle_pause()

    def tick(self):
        r = self.rec
        if r and r.state in ("recording", "paused"):
            e = int(r.elapsed())
            self.lbl_time.setText(f"{e // 3600:02d}:{e // 60 % 60:02d}:{e % 60:02d}")
            self.lbl_time.setStyleSheet("color:#dc2626" if r.state == "recording" else "color:#d97706")
            size = sum(os.path.getsize(s) for s in r.segments if os.path.exists(s)) / 1048576
            self.lbl_info.setText((T("Đang quay") if r.state == "recording" else T("Tạm dừng")) + f"  •  {size:.1f} MB")
            blink = r.state == "recording" and int(time.time() * 2) % 2 == 0
            self.set_dot("#dc2626" if blink else ("#f59e0b" if r.state == "paused" else "#fecaca"))
            self.setWindowTitle(f"● {self.lbl_time.text()} - {APP}")
            for t in r.tracks:
                (self.lv_sys if t.kind == "system" else self.lv_mic).setValue(int(min(t.level, 1) * 100))
            if r.proc and r.proc.poll() is not None and r.state == "recording":
                self.lbl_status.setText(T("⚠ ffmpeg dừng bất thường (cửa sổ bị đóng / màn hình thay đổi?)"))
                self.stop_rec()
        elif not self.countdown_left and not r:
            self.lbl_time.setStyleSheet("")
            if self.windowTitle() != f"{APP} v{VER}":
                self.setWindowTitle(f"{APP} v{VER}"); self.lbl_time.setText("00:00:00")
                self.lbl_info.setText(T("Sẵn sàng")); self.set_dot(None)
            self.lv_sys.setValue(0); self.lv_mic.setValue(0)

    def closeEvent(self, e):
        if not self._quitting and not self._switching and self.cb_snip_key.currentData() != "off":
            # keep running in the tray so the snip hotkey keeps working
            e.ignore(); self.save(); self.hide()
            if not self.s.value("tray_hint_shown", False):
                self.tray.showMessage(APP, T("Screen Recorder vẫn chạy ở khay hệ thống để phím tắt chụp ảnh hoạt động. "
                                             "Chuột phải biểu tượng › Thoát để tắt hẳn."), QSystemTrayIcon.Information, 5000)
                self.s.setValue("tray_hint_shown", True)
            return
        if self.rec:
            if not ask(self, T("Đang quay. Dừng và lưu rồi thoát?"), T("Lưu và thoát"), T("Huỷ")):
                e.ignore(); return
            if self.rec.state in ("recording", "paused"):
                try: self.rec.stop()
                except Exception: pass
        self.save(); self.hk.stop(); self.ghk.stop(); self.tray.hide()
        self.timer.stop()
        for ed in list(self.editors):
            if not self._switching:
                ed.close()
        e.accept()
        if not getattr(self, "_switching", False):
            QApplication.quit()


def default_out():
    v = QStandardPaths.writableLocation(QStandardPaths.MoviesLocation) or os.path.expanduser("~\\Videos")
    return os.path.normpath(os.path.join(v, "Screen Recorder"))


def ask(parent, text, yes=T("Có"), no=T("Không")):
    m = QMessageBox(QMessageBox.Question, APP, text, QMessageBox.NoButton, parent)
    by = m.addButton(yes, QMessageBox.YesRole); m.addButton(no, QMessageBox.NoRole)
    m.setDefaultButton(by); m.exec()
    return m.clickedButton() is by


def make_icon():
    return QIcon(theme.app_icon(256))


def main():
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TuanPA.ScreenRecorder")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    theme.install(app)
    if "--uninstall" in sys.argv:
        i18n.LANG = str(settings().value("lang", "vi"))
        if "--quiet" in sys.argv or ask(None, T("Gỡ Screen Recorder khỏi máy? (Video đã quay không bị xoá)"), T("Gỡ"), T("Huỷ")):
            import winreg
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
                    winreg.DeleteValue(k, RUN_NAME)
            except OSError:
                pass
            installer.uninstall()
        return
    cmd = "snip" if "--snip" in sys.argv else ("tray" if "--tray" in sys.argv else "show")
    if not acquire_single_instance():
        send_to_running(cmd)          # another copy is running: hand the request over and exit
        return
    serve_instance(lambda c: on_remote(c))
    start_main(show=cmd != "tray" and cmd != "snip")
    if cmd == "snip":
        QTimer.singleShot(300, lambda: _windows[0].start_snip())
    sys.exit(app.exec())


_windows = []
_mutex = None
PIPE = "TuanPA.ScreenRecorder.ipc"


def acquire_single_instance():
    global _mutex
    _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\TuanPA.ScreenRecorder.single")
    return ctypes.windll.kernel32.GetLastError() != 183      # ERROR_ALREADY_EXISTS


def release_single_instance():
    global _mutex
    if _mutex:
        ctypes.windll.kernel32.CloseHandle(_mutex); _mutex = None
    srv = getattr(serve_instance, "srv", None)
    if srv:
        srv.close()


def send_to_running(cmd):
    from PySide6.QtNetwork import QLocalSocket
    s = QLocalSocket()
    s.connectToServer(PIPE)
    if s.waitForConnected(2000):
        s.write(cmd.encode()); s.flush(); s.waitForBytesWritten(1000); s.disconnectFromServer()


def serve_instance(handler):
    from PySide6.QtNetwork import QLocalServer
    QLocalServer.removeServer(PIPE)
    srv = QLocalServer()
    srv.listen(PIPE)

    def on_conn():
        c = srv.nextPendingConnection()
        c.readyRead.connect(lambda: handler(bytes(c.readAll()).decode(errors="ignore").strip()))
    srv.newConnection.connect(on_conn)
    serve_instance.srv = srv


def on_remote(cmd):
    if not _windows:
        return
    w = _windows[0]
    if cmd == "snip":
        w.start_snip()
    elif cmd != "tray":
        w.show_main()


def start_main(geo=None, show=True):
    i18n.LANG = str(settings().value("lang", "vi"))
    w = Main()
    _windows[:] = [w]
    if geo is not None:
        w.setGeometry(geo)
    if show:
        if geo is None:
            w.showMaximized()          # open full screen by default
        else:
            w.show()
    return w


if __name__ == "__main__":
    main()