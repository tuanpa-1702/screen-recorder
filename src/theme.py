# Screen Recorder - Copyright (C) 2026 TuanPA <tuanpa1702@gmail.com>
# SPDX-License-Identifier: GPL-3.0-only
# This program is free software under the GNU GPL v3; see LICENSE. It comes WITHOUT ANY WARRANTY.
"""Light frosted-glass theme (Windows 11 Acrylic) + vector icons for Screen Recorder."""
import ctypes, os, sys

from PySide6.QtCore import Qt, QObject, QEvent, QPointF, QRectF
from PySide6.QtGui import (QPainter, QColor, QPen, QPixmap, QIcon, QPalette, QLinearGradient,
                           QPainterPath, QBrush, QRadialGradient)
from PySide6.QtWidgets import QWidget, QMenu, QApplication, QStyleFactory, QDialog, QMessageBox

GLASS = sys.platform == "win32" and sys.getwindowsversion().build >= 22000
ACCENT = "#2563eb"

STYLE = """
* { color:#0f172a; font-family:'Segoe UI'; font-size:10pt; }
QWidget#root { background:{BG}; }
QDialog, QMessageBox { background:{DLG}; }
QLabel { background:transparent; }
QLabel#title { font-size:15pt; font-weight:700; }
QLabel#sub { color:#64748b; font-size:9pt; }
QLabel#tag { color:#2563eb; background:transparent; padding:0; font-size:8pt; font-weight:600; }
QLabel#hint { color:#64748b; font-size:9pt; }
QLabel#timer { font-family:'Consolas'; font-size:24pt; font-weight:700; color:#0f172a; }
QLabel#sec { color:#2563eb; font-weight:700; font-size:9.5pt; letter-spacing:0.5px; }

QFrame#card { background:qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba(239,246,255,0.85), stop:0.55 rgba(248,250,252,0.75), stop:1 rgba(238,242,255,0.85));
              border:1px solid rgba(191,219,254,0.75); border-top:1px solid rgba(255,255,255,1); border-radius:14px; }
QFrame#card:disabled { background:rgba(248,250,252,0.7); }
QFrame#bar  { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 rgba(238,242,255,0.95), stop:1 rgba(253,242,248,0.9));
              border:1px solid rgba(199,210,254,0.8); border-radius:16px; }
QPushButton#pill { border-radius:12px; padding:3px 12px; font-size:9pt; font-weight:600; background:rgba(241,245,249,0.9); }
QPushButton#pill:hover { background:#dbeafe; border-color:#93c5fd; }

QPushButton { background:rgba(255,255,255,0.78); border:1px solid rgba(203,213,225,0.95); border-radius:7px; padding:6px 14px; }
QPushButton:hover { background:rgba(239,246,255,0.98); border-color:#93c5fd; }
QPushButton:pressed { background:#dbeafe; }
QPushButton:disabled { color:#94a3b8; background:rgba(255,255,255,0.45); }
QPushButton#mode { padding:9px 10px; font-weight:600; border-radius:9px; text-align:center; }
QPushButton#mode:checked { background:qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #3b82f6, stop:1 #2563eb); color:white; border:1px solid #2563eb; }
QPushButton#rec { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #f43f5e, stop:1 #dc2626); color:white; border:none;
                  font-size:12pt; font-weight:700; border-radius:22px; min-height:44px; padding:0 24px; }
QPushButton#rec:hover { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #e11d48, stop:1 #b91c1c); }
QPushButton#rec[recording="true"] { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #334155, stop:1 #0f172a); }
QPushButton#rec:disabled { background:#94a3b8; }
QPushButton#icon { padding:5px; min-width:30px; }

QLineEdit, QComboBox, QSpinBox { background:rgba(255,255,255,0.82); border:1px solid rgba(203,213,225,0.95);
    border-radius:7px; padding:4px 8px; min-height:22px; selection-background-color:#bfdbfe; selection-color:#0f172a; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QComboBox:hover, QSpinBox:hover { border-color:#60a5fa; }
QComboBox:disabled, QLineEdit:disabled, QSpinBox:disabled { color:#94a3b8; background:rgba(255,255,255,0.45); }
QComboBox::drop-down { border:none; width:22px; }
QComboBox::down-arrow { image:url({ARROW}); width:11px; height:11px; margin-right:8px; }
QSpinBox::up-button, QSpinBox::down-button { width:0; border:none; }
QComboBox { combobox-popup:0; padding-left:10px; }
QComboBox:on { border-color:#3b82f6; background:#ffffff; }
QComboBox QAbstractItemView { background:rgba(255,255,255,0.86); border:1px solid rgba(203,213,225,0.9);
    border-radius:10px; padding:4px; outline:0; margin-top:4px; }
QComboBox QAbstractItemView::item { border:none; background:transparent; }

QMenu { background:rgba(255,255,255,0.80); border:none; padding:6px; }
QMenu::item { padding:6px 24px 6px 12px; border-radius:6px; background:transparent; }
QMenu::item:selected { background:rgba(219,234,254,0.95); }
QMenu::separator { height:1px; background:#e2e8f0; margin:4px 8px; }

QCheckBox { background:transparent; spacing:7px; }
QCheckBox::indicator { width:16px; height:16px; border-radius:4px; border:1px solid #94a3b8; background:rgba(255,255,255,0.9); }
QCheckBox::indicator:hover { border-color:#2563eb; }
QCheckBox::indicator:checked { image:url({CHECK}); background:#2563eb; border-color:#2563eb; }
QCheckBox:disabled { color:#94a3b8; }

QProgressBar { border:none; border-radius:3px; background:rgba(148,163,184,0.30); max-height:6px; min-height:6px; }
QProgressBar::chunk { border-radius:3px; background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #22c55e, stop:0.7 #84cc16, stop:1 #f59e0b); }
QToolTip { background:#ffffff; color:#0f172a; border:1px solid #cbd5e1; padding:4px; }
QScrollBar:vertical { background:transparent; width:10px; }
QScrollBar::handle:vertical { background:rgba(148,163,184,0.7); border-radius:4px; margin:2px; min-height:24px; }
QScrollBar::add-line, QScrollBar::sub-line { height:0; width:0; }
QMessageBox QPushButton { min-width:72px; }
"""


class _MARGINS(ctypes.Structure):
    _fields_ = [("l", ctypes.c_int), ("r", ctypes.c_int), ("t", ctypes.c_int), ("b", ctypes.c_int)]


def apply_acrylic(w):
    if not GLASS or w.property("_glass"):
        return
    try:
        hwnd = int(w.winId())
        dwm = ctypes.windll.dwmapi
        dwm.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(_MARGINS(-1, -1, -1, -1)))
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(0)), 4)   # light title bar
        dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(ctypes.c_int(2)), 4)   # rounded corners
        dwm.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(ctypes.c_int(3)), 4)   # Acrylic backdrop
        w.setProperty("_glass", True)
    except Exception:
        pass


def _wants_glass(w):
    # only popups (dropdowns / menus) are real Acrylic; windows and dialogs stay solid white
    return isinstance(w, QMenu) or w.inherits("QComboBoxPrivateContainer")


class GlassFilter(QObject):
    """Applies Acrylic to the main window, dialogs, menus and combo dropdowns."""

    def eventFilter(self, obj, ev):
        if isinstance(obj, QWidget) and obj.isWindow():
            t = ev.type()
            if t == QEvent.Polish and _wants_glass(obj) and not obj.testAttribute(Qt.WA_TranslucentBackground):
                obj.setAttribute(Qt.WA_TranslucentBackground)
                if isinstance(obj, QMenu) or obj.inherits("QComboBoxPrivateContainer"):
                    obj.setWindowFlag(Qt.NoDropShadowWindowHint, True)
            elif t == QEvent.Show and obj.testAttribute(Qt.WA_TranslucentBackground) and _wants_glass(obj):
                apply_acrylic(obj)
            elif t == QEvent.Paint and obj.property("_glass"):
                p = QPainter(obj)
                p.setCompositionMode(QPainter.CompositionMode_Clear)
                p.fillRect(ev.rect(), Qt.transparent)
                p.end()
            elif t == QEvent.UpdateRequest and obj.property("_glass") and not obj.property("_repainting"):
                obj.setProperty("_repainting", True)   # full repaint: partial repaints leave ghost text on Acrylic
                try:
                    obj.repaint()
                finally:
                    obj.setProperty("_repainting", False)
                return True
        return False


from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QComboBox, QListView
from PySide6.QtCore import QSize as _QSize


class ComboDelegate(QStyledItemDelegate):
    """Dropdown rows: rounded hover pill, the current choice in bold blue with a check mark."""

    def __init__(self, combo):
        super().__init__(combo)
        self.cb = combo

    def sizeHint(self, opt, idx):
        return _QSize(max(120, super().sizeHint(opt, idx).width() + 44), 34)

    def paint(self, p, opt, idx):
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(opt.rect).adjusted(4, 2, -4, -2)
        current = idx.row() == self.cb.currentIndex()
        hover = bool(opt.state & (QStyle.State_MouseOver | QStyle.State_Selected))
        if hover or current:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#dbeafe") if hover else QColor("#eff6ff"))
            p.drawRoundedRect(r, 7, 7)
        if current:   # accent bar on the left
            p.setBrush(QColor(ACCENT)); p.drawRoundedRect(QRectF(r.left() + 3, r.top() + 8, 3, r.height() - 16), 1.5, 1.5)
        f = opt.font
        f.setBold(current); p.setFont(f)
        p.setPen(QColor(ACCENT) if current else QColor("#0f172a"))
        x = r.left() + 14
        ic = idx.data(Qt.DecorationRole)
        if ic:
            QIcon(ic).paint(p, int(x), int(r.center().y() - 9), 18, 18); x += 26
        p.drawText(QRectF(x, r.top(), r.width() - (x - r.left()) - 30, r.height()), Qt.AlignVCenter | Qt.AlignLeft,
                   str(idx.data(Qt.DisplayRole) or ""))
        if current:
            p.setPen(QPen(QColor(ACCENT), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            cx, cy = r.right() - 16, r.center().y()
            p.drawPolyline([QPointF(cx - 5, cy), QPointF(cx - 1.5, cy + 3.5), QPointF(cx + 5, cy - 4)])
        p.restore()


def polish_combo(cb):
    if cb.property("_polished"):
        return
    cb.setProperty("_polished", True)
    v = QListView(); v.setMouseTracking(True)
    cb.setView(v)
    cb.setItemDelegate(ComboDelegate(cb))
    cb.setMaxVisibleItems(12)
    v.installEventFilter(_POPUP_WIDTH)


class _PopupWidth(QObject):
    """The popup is at least as wide as its longest entry (+ room for icon and check mark)."""

    def eventFilter(self, v, ev):
        if ev.type() == QEvent.Show:
            fm = v.fontMetrics()
            m = v.model()
            bold = v.font(); bold.setBold(True)
            from PySide6.QtGui import QFontMetrics
            bfm = QFontMetrics(bold)
            w = max([bfm.horizontalAdvance(str(m.index(r, 0).data() or "")) for r in range(m.rowCount())] + [0])
            need = w + 80
            if v.width() < need:
                v.setMinimumWidth(need)
                c = v.window()
                if c is not v and c.width() < need + 10:
                    c.resize(need + 10, c.height())
        return False


_POPUP_WIDTH = _PopupWidth()


class ComboFilter(QObject):
    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Polish and isinstance(obj, QComboBox):
            polish_combo(obj)
        return False


def _theme_images():
    d = os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "ScreenRecorder_theme")
    os.makedirs(d, exist_ok=True)
    out = []
    for name in ("arrow.png", "check.png"):
        pm = QPixmap(32, 32); pm.fill(Qt.transparent)
        p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
        if name == "arrow.png":
            p.setPen(QPen(QColor("#475569"), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPolyline([QPointF(8, 12), QPointF(16, 21), QPointF(24, 12)])
        else:
            p.setPen(QPen(QColor("white"), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPolyline([QPointF(7, 17), QPointF(13, 23), QPointF(25, 9)])
        p.end()
        path = os.path.join(d, name); pm.save(path)
        out.append(path.replace("\\", "/"))
    return out


def install(app):
    """Fusion + forced light palette (so Windows dark mode can't produce dark-on-dark dialogs) + glass."""
    app.setStyle(QStyleFactory.create("Fusion"))
    try:
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    except Exception:
        pass
    pal = QPalette()
    for role, col in [(QPalette.Window, "#f1f5f9"), (QPalette.WindowText, "#0f172a"), (QPalette.Base, "#ffffff"),
                      (QPalette.AlternateBase, "#f8fafc"), (QPalette.Text, "#0f172a"), (QPalette.Button, "#ffffff"),
                      (QPalette.ButtonText, "#0f172a"), (QPalette.Highlight, ACCENT), (QPalette.HighlightedText, "#ffffff"),
                      (QPalette.ToolTipBase, "#ffffff"), (QPalette.ToolTipText, "#0f172a"), (QPalette.PlaceholderText, "#94a3b8")]:
        pal.setColor(role, QColor(col))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor("#94a3b8"))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#94a3b8"))
    pal.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#94a3b8"))
    app.setPalette(pal)
    arrow, check = _theme_images()
    bg, dlg = "#ffffff", "#ffffff"
    app.setStyleSheet(STYLE.replace("{BG}", bg).replace("{DLG}", dlg).replace("{ARROW}", arrow).replace("{CHECK}", check))
    app._combo = ComboFilter(app)
    app.installEventFilter(app._combo)
    if GLASS:
        app._glass = GlassFilter(app)
        app.installEventFilter(app._glass)


# ---------------- vector icons ----------------
def icon(name, color="#334155", size=48):
    pm = QPixmap(size, size); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    s = size / 24.0
    p.scale(s, s)
    pen = QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen); p.setBrush(Qt.NoBrush)
    c = QColor(color)
    if name == "monitor":
        p.drawRoundedRect(QRectF(2.5, 4, 19, 12.5), 2, 2)
        p.drawLine(QPointF(9, 20.5), QPointF(15, 20.5)); p.drawLine(QPointF(12, 16.5), QPointF(12, 20.5))
    elif name == "region":
        for x, y, dx, dy in [(3, 3, 1, 1), (21, 3, -1, 1), (3, 21, 1, -1), (21, 21, -1, -1)]:
            p.drawPolyline([QPointF(x, y + 5 * dy), QPointF(x, y), QPointF(x + 5 * dx, y)])
        p.setBrush(c); p.setPen(Qt.NoPen); p.drawEllipse(QPointF(12, 12), 2.2, 2.2)
    elif name == "window":
        p.drawRoundedRect(QRectF(2.5, 4, 19, 16), 2, 2); p.drawLine(QPointF(2.5, 8.5), QPointF(21.5, 8.5))
        p.setBrush(c); p.setPen(Qt.NoPen)
        for x in (5.2, 7.6, 10):
            p.drawEllipse(QPointF(x, 6.3), 0.8, 0.8)
    elif name == "camera":
        path = QPainterPath(); path.addRoundedRect(QRectF(2.5, 6.5, 19, 13.5), 2.5, 2.5)
        p.drawPath(path); p.drawPolyline([QPointF(8, 6.5), QPointF(9.5, 4), QPointF(14.5, 4), QPointF(16, 6.5)])
        p.drawEllipse(QPointF(12, 13.2), 3.6, 3.6)
    elif name == "pause":
        p.setBrush(c); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(6, 5, 4, 14), 1.2, 1.2); p.drawRoundedRect(QRectF(14, 5, 4, 14), 1.2, 1.2)
    elif name == "play":
        p.setBrush(c); p.setPen(QPen(c, 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPolygon([QPointF(8, 5), QPointF(19, 12), QPointF(8, 19)])
    elif name == "rec":
        p.setBrush(c); p.setPen(Qt.NoPen); p.drawEllipse(QPointF(12, 12), 6, 6)
    elif name == "stop":
        p.setBrush(c); p.setPen(Qt.NoPen); p.drawRoundedRect(QRectF(6.5, 6.5, 11, 11), 2, 2)
    elif name == "folder":
        p.drawPolyline([QPointF(2.5, 18.5), QPointF(2.5, 5.5), QPointF(9, 5.5), QPointF(11, 8), QPointF(21.5, 8),
                        QPointF(21.5, 18.5), QPointF(2.5, 18.5)])
    elif name == "folder-open":
        p.drawPolyline([QPointF(2.5, 18.5), QPointF(2.5, 5.5), QPointF(9, 5.5), QPointF(11, 8), QPointF(19, 8), QPointF(19, 11)])
        p.drawPolygon([QPointF(2.5, 18.5), QPointF(5.5, 11), QPointF(22, 11), QPointF(19, 18.5)])
    elif name == "refresh":
        p.drawArc(QRectF(4.5, 4.5, 15, 15), 40 * 16, 290 * 16)
        p.drawPolyline([QPointF(19.5, 3.5), QPointF(19.3, 8.3), QPointF(14.6, 7.8)])
    elif name == "crop":
        p.drawPolyline([QPointF(6, 2.5), QPointF(6, 18), QPointF(21.5, 18)])
        p.drawPolyline([QPointF(2.5, 6), QPointF(18, 6), QPointF(18, 21.5)])
    elif name == "speaker":
        p.setBrush(c); p.drawPolygon([QPointF(3, 9.5), QPointF(7, 9.5), QPointF(12, 5), QPointF(12, 19), QPointF(7, 14.5), QPointF(3, 14.5)])
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(10, 8, 7, 8), -60 * 16, 120 * 16); p.drawArc(QRectF(10, 5, 11, 14), -60 * 16, 120 * 16)
    elif name == "mic":
        p.drawRoundedRect(QRectF(9, 2.5, 6, 11), 3, 3)
        p.drawArc(QRectF(5.5, 6, 13, 11), 180 * 16, 180 * 16)
        p.drawLine(QPointF(12, 17), QPointF(12, 21)); p.drawLine(QPointF(8.5, 21), QPointF(15.5, 21))
    elif name == "video":
        p.drawRoundedRect(QRectF(2.5, 6, 13, 12), 2.5, 2.5)
        p.drawPolygon([QPointF(15.5, 10.5), QPointF(21.5, 7), QPointF(21.5, 17), QPointF(15.5, 13.5)])
    elif name == "save":
        p.drawRoundedRect(QRectF(3.5, 3.5, 17, 17), 2.5, 2.5)
        p.drawRect(QRectF(7.5, 3.5, 8, 5.5)); p.drawRoundedRect(QRectF(7, 13, 10, 7.5), 1, 1)
    elif name in ("fill-none", "fill-light", "fill-solid"):
        if name != "fill-none":
            fc = QColor(c); fc.setAlpha(90 if name == "fill-light" else 255); p.setBrush(fc)
        p.drawRoundedRect(QRectF(4, 5, 16, 14), 2.5, 2.5)
        if name == "fill-none":
            p.setPen(QPen(c, 1.4, Qt.SolidLine, Qt.RoundCap)); p.drawLine(QPointF(5.5, 17.5), QPointF(18.5, 6.5))
    elif name == "lasso":
        path = QPainterPath(QPointF(6, 15))
        path.cubicTo(1, 9, 8, 3, 14, 4); path.cubicTo(21, 5, 22, 12, 16, 14.5); path.cubicTo(12, 16, 8, 16, 6, 15)
        p.drawPath(path)
        p.drawPolyline([QPointF(6, 15), QPointF(7.5, 19), QPointF(5.5, 21.5)])
    elif name == "close":
        p.drawLine(QPointF(6, 6), QPointF(18, 18)); p.drawLine(QPointF(18, 6), QPointF(6, 18))
    elif name == "select":
        p.setBrush(c); p.drawPolygon([QPointF(6, 3.5), QPointF(18, 13), QPointF(12.5, 13.8), QPointF(15.5, 20),
                                      QPointF(13, 21), QPointF(10.2, 15), QPointF(6, 18.5)])
    elif name == "pen":
        p.drawPolygon([QPointF(4, 20), QPointF(5, 15.5), QPointF(16, 4.5), QPointF(19.5, 8), QPointF(8.5, 19)])
        p.drawLine(QPointF(14, 6.5), QPointF(17.5, 10))
    elif name == "highlight":
        p.drawPolygon([QPointF(9, 15), QPointF(16, 4), QPointF(20, 7), QPointF(13, 18)])
        p.drawPolyline([QPointF(9, 15), QPointF(7.5, 17.5), QPointF(10.5, 19.5), QPointF(13, 18)])
        hl = QColor(c); hl.setAlpha(110); p.setPen(QPen(hl, 2.6)); p.drawLine(QPointF(3, 21.5), QPointF(21, 21.5))
    elif name == "line":
        p.drawLine(QPointF(4.5, 19.5), QPointF(19.5, 4.5))
    elif name == "arrow":
        p.drawLine(QPointF(4.5, 19.5), QPointF(18.5, 5.5))
        p.drawPolyline([QPointF(10.5, 5), QPointF(19, 5), QPointF(19, 13.5)])
    elif name == "rect":
        p.drawRoundedRect(QRectF(3.5, 5.5, 17, 13), 1.5, 1.5)
    elif name == "ellipse":
        p.drawEllipse(QRectF(3, 5, 18, 14))
    elif name == "text":
        p.drawLine(QPointF(5, 5), QPointF(19, 5)); p.drawLine(QPointF(12, 5), QPointF(12, 19.5))
        p.drawLine(QPointF(9, 19.5), QPointF(15, 19.5))
    elif name == "step":
        p.drawEllipse(QPointF(12, 12), 8.5, 8.5)
        p.drawPolyline([QPointF(10, 9), QPointF(12.5, 7.5), QPointF(12.5, 16.5)]); p.drawLine(QPointF(10, 16.5), QPointF(15, 16.5))
    elif name == "blur":
        p.setPen(Qt.NoPen)
        for i in range(4):
            for j in range(4):
                cc = QColor(c); cc.setAlpha(255 if (i + j) % 2 == 0 else 90); p.setBrush(cc)
                p.drawRect(QRectF(4 + i * 4, 4 + j * 4, 4, 4))
    elif name == "palette":
        p.drawEllipse(QPointF(12, 12), 9, 9)
        p.setPen(Qt.NoPen)
        for (x, y), col in zip([(8, 9), (12, 7), (16, 9), (16.5, 13.5)], ["#ef4444", "#facc15", "#22c55e", "#3b82f6"]):
            p.setBrush(QColor(col)); p.drawEllipse(QPointF(x, y), 1.7, 1.7)
    elif name == "undo":
        p.drawPolyline([QPointF(8, 4.5), QPointF(4, 8.5), QPointF(8, 12.5)])
        path = QPainterPath(QPointF(4, 8.5)); path.lineTo(14, 8.5); path.cubicTo(22, 8.5, 22, 19.5, 14, 19.5)
        path.lineTo(8, 19.5); p.drawPath(path)
    elif name == "redo":
        p.drawPolyline([QPointF(16, 4.5), QPointF(20, 8.5), QPointF(16, 12.5)])
        path = QPainterPath(QPointF(20, 8.5)); path.lineTo(10, 8.5); path.cubicTo(2, 8.5, 2, 19.5, 10, 19.5)
        path.lineTo(16, 19.5); p.drawPath(path)
    elif name == "plus":
        p.drawLine(QPointF(12, 5), QPointF(12, 19)); p.drawLine(QPointF(5, 12), QPointF(19, 12))
    elif name == "copy":
        p.drawRoundedRect(QRectF(8, 8, 12, 12.5), 2, 2)
        p.drawPolyline([QPointF(16, 8), QPointF(16, 4), QPointF(4, 4), QPointF(4, 16.5), QPointF(8, 16.5)])
    elif name == "scissors":
        p.drawEllipse(QPointF(6.5, 17), 3, 3); p.drawEllipse(QPointF(17.5, 17), 3, 3)
        p.drawLine(QPointF(8.5, 14.8), QPointF(17, 3.5)); p.drawLine(QPointF(15.5, 14.8), QPointF(7, 3.5))
    elif name == "download":
        p.drawLine(QPointF(12, 3.5), QPointF(12, 15)); p.drawPolyline([QPointF(7, 10.5), QPointF(12, 15.5), QPointF(17, 10.5)])
        p.drawPolyline([QPointF(4, 15.5), QPointF(4, 20), QPointF(20, 20), QPointF(20, 15.5)])
    elif name == "trash":
        p.drawLine(QPointF(4, 6.5), QPointF(20, 6.5)); p.drawPolyline([QPointF(9, 6.5), QPointF(9.5, 3.5), QPointF(14.5, 3.5), QPointF(15, 6.5)])
        p.drawPolyline([QPointF(6, 6.5), QPointF(7, 20.5), QPointF(17, 20.5), QPointF(18, 6.5)])
        p.drawLine(QPointF(10.2, 10), QPointF(10.2, 17)); p.drawLine(QPointF(13.8, 10), QPointF(13.8, 17))
    elif name == "settings":
        p.drawEllipse(QPointF(12, 12), 3, 3)
        import math
        for i in range(8):
            a = i * math.pi / 4
            p.drawLine(QPointF(12 + 6 * math.cos(a), 12 + 6 * math.sin(a)), QPointF(12 + 9 * math.cos(a), 12 + 9 * math.sin(a)))
        p.drawEllipse(QPointF(12, 12), 6.2, 6.2)
    p.end()
    return QIcon(pm)


def app_icon_icon():
    return QIcon(app_icon(256))


def app_icon(size=256):
    pm = QPixmap(size, size); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    s = size / 64.0; p.scale(s, s)
    g = QLinearGradient(0, 0, 64, 64); g.setColorAt(0, QColor("#6366f1")); g.setColorAt(1, QColor("#2563eb"))
    p.setPen(Qt.NoPen); p.setBrush(g); p.drawRoundedRect(QRectF(3, 3, 58, 58), 15, 15)
    # glass highlight
    h = QLinearGradient(0, 3, 0, 34); h.setColorAt(0, QColor(255, 255, 255, 90)); h.setColorAt(1, QColor(255, 255, 255, 0))
    p.setBrush(h); p.drawRoundedRect(QRectF(5, 5, 54, 28), 13, 13)
    # screen frame
    p.setBrush(Qt.NoBrush); p.setPen(QPen(QColor("white"), 3.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawRoundedRect(QRectF(13, 15, 38, 26), 5, 5)
    p.drawLine(QPointF(25, 49), QPointF(39, 49)); p.drawLine(QPointF(32, 41), QPointF(32, 49))
    # rec dot
    rg = QRadialGradient(QPointF(30.5, 26.5), 9); rg.setColorAt(0, QColor("#fb7185")); rg.setColorAt(1, QColor("#e11d48"))
    p.setPen(QPen(QColor("white"), 2)); p.setBrush(rg); p.drawEllipse(QPointF(32, 28), 7, 7)
    p.end()
    return pm
