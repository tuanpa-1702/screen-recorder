# Screen Recorder - Copyright (C) 2026 TuanPA <tuanpa1702@gmail.com>
# SPDX-License-Identifier: GPL-3.0-only
# This program is free software under the GNU GPL v3; see LICENSE. It comes WITHOUT ANY WARRANTY.
"""Snipping: freeze all screens, pick a region / window / full screen, return a QImage. Plus a toast."""
import ctypes, ctypes.wintypes as wt

from PySide6.QtCore import Qt, QRect, QRectF, QPoint, QTimer, Signal, QObject, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QGuiApplication, QFont, QCursor, QImage, QPainterPath
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFrame, QButtonGroup

import rec_core
import theme
from i18n import T


def _windows_phys():
    """Visible top-level windows in z-order (top first): [(title, (x,y,w,h))] physical px."""
    out = []
    for t, h in rec_core.windows():
        try:
            x, y, w, hh = rec_core.window_rect(h)
            if w > 20 and hh > 20:
                out.append((t, (x, y, w, hh)))
        except Exception:
            pass
    return out


class SnipOverlay(QWidget):
    picked = Signal(object)          # QImage or None

    def __init__(self, ctl, screen, pix, phys_origin):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.ctl, self.scr, self.pix = ctl, screen, pix
        self.dpr = pix.devicePixelRatio()
        self.phys = phys_origin
        self.setGeometry(screen.geometry())
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)
        self.p0 = self.p1 = None
        self.pts = []                # freeform outline (local logical coords)
        self.drawing = False
        self.hover = None            # QRect (logical, local) under the cursor in window mode

    # physical rect -> local logical rect
    def _to_local(self, r):
        x, y, w, h = r
        return QRect(round((x - self.phys[0]) / self.dpr), round((y - self.phys[1]) / self.dpr),
                     round(w / self.dpr), round(h / self.dpr)).intersected(self.rect())

    def _free_path(self):
        if self.ctl.mode != "free" or len(self.pts) < 2:
            return None
        path = QPainterPath(self.pts[0])
        for q in self.pts[1:]:
            path.lineTo(q)
        path.closeSubpath()
        return path

    def _sel(self):
        if self.ctl.mode == "free":
            fp = self._free_path()
            return fp.boundingRect().toAlignedRect() if fp else None
        if self.ctl.mode == "rect" and self.p0 and self.p1:
            return QRect(self.p0, self.p1).normalized()
        if self.ctl.mode == "window":
            return self.hover
        if self.ctl.mode == "full" and self.underMouse():
            return self.rect()
        return None

    def paintEvent(self, e):
        p = QPainter(self)
        p.drawPixmap(self.rect(), self.pix)
        p.fillRect(self.rect(), QColor(15, 23, 42, 120))
        fp = self._free_path()
        if fp is not None:
            p.save(); p.setClipPath(fp); p.drawPixmap(self.rect(), self.pix); p.restore()
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(QPen(QColor("#3b82f6"), 2)); p.setBrush(Qt.NoBrush); p.drawPath(fp)
            return
        r = self._sel()
        if r and not r.isEmpty():
            src = QRect(round(r.x() * self.dpr), round(r.y() * self.dpr), round(r.width() * self.dpr), round(r.height() * self.dpr))
            p.drawPixmap(r, self.pix, src)
            p.setPen(QPen(QColor("#3b82f6"), 2)); p.setBrush(Qt.NoBrush)
            p.drawRect(r.adjusted(0, 0, -1, -1))
            txt = f"{src.width()} × {src.height()}"
            p.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
            fm = p.fontMetrics(); tw = fm.horizontalAdvance(txt) + 14
            ty = r.y() - 26 if r.y() > 30 else r.y() + 6
            path = QPainterPath(); path.addRoundedRect(QRectF(r.x(), ty, tw, 20), 6, 6)
            p.fillPath(path, QColor(37, 99, 235, 230)); p.setPen(Qt.white)
            p.drawText(QRect(r.x(), ty, tw, 20), Qt.AlignCenter, txt)
        if self.ctl.mode == "rect" and not self.p0 and self.underMouse():   # crosshair guides
            c = self.mapFromGlobal(QCursor.pos())
            p.setPen(QPen(QColor(255, 255, 255, 110), 1, Qt.DashLine))
            p.drawLine(0, c.y(), self.width(), c.y()); p.drawLine(c.x(), 0, c.x(), self.height())

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            return self.ctl.finish(None)
        if self.ctl.mode == "rect":
            self.p0 = self.p1 = e.position().toPoint()
        elif self.ctl.mode == "free":
            self.pts = [e.position()]
            self.drawing = True
        self.update()

    def mouseMoveEvent(self, e):
        pt = e.position().toPoint()
        if self.ctl.mode == "rect" and self.p0:
            self.p1 = pt
        elif self.ctl.mode == "free" and self.drawing:
            self.pts.append(e.position())
        elif self.ctl.mode == "window":
            gp = (self.phys[0] + pt.x() * self.dpr, self.phys[1] + pt.y() * self.dpr)
            self.hover = None
            for _, (x, y, w, h) in self.ctl.wins:
                if x <= gp[0] < x + w and y <= gp[1] < y + h:
                    self.hover = self._to_local((x, y, w, h)); break
        self.update()

    def enterEvent(self, e):
        for o in self.ctl.overlays:
            o.update()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        if self.ctl.mode == "free":
            self.drawing = False
            fp = self._free_path()
            r = fp.boundingRect() if fp else None
            if not r or r.width() < 4 or r.height() < 4:
                self.pts = []; self.update(); return
            return self.ctl.finish(self._cut_free(fp))
        r = self._sel()
        if self.ctl.mode == "rect":
            if not r or r.width() < 4 or r.height() < 4:
                self.p0 = self.p1 = None; self.update(); return
        if not r or r.isEmpty():
            return
        src = QRect(round(r.x() * self.dpr), round(r.y() * self.dpr), round(r.width() * self.dpr), round(r.height() * self.dpr))
        img = self.pix.copy(src).toImage()
        img.setDevicePixelRatio(1)
        self.ctl.finish(img)

    def _cut_free(self, fp):
        """Crop to the path's bounds; everything outside the drawn shape becomes transparent."""
        from PySide6.QtGui import QTransform
        br = fp.boundingRect().toAlignedRect().intersected(self.rect())
        d = self.dpr
        src = QRect(round(br.x() * d), round(br.y() * d), round(br.width() * d), round(br.height() * d))
        # outside the shape = white (like Snipping Tool) so pasting into Word/Teams/mail never shows black
        img = QImage(src.size(), QImage.Format_ARGB32_Premultiplied); img.fill(Qt.white)
        p = QPainter(img); p.setRenderHint(QPainter.Antialiasing)
        path = QTransform().scale(d, d).map(fp).translated(-src.x(), -src.y())
        p.setClipPath(path)
        p.drawPixmap(0, 0, self.pix.copy(src))
        p.end()
        return img

    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key_Escape:
            self.ctl.finish(None)
        elif k in (Qt.Key_R, Qt.Key_1): self.ctl.set_mode("rect")
        elif k in (Qt.Key_W, Qt.Key_2): self.ctl.set_mode("window")
        elif k in (Qt.Key_F, Qt.Key_3): self.ctl.set_mode("full")
        elif k in (Qt.Key_D, Qt.Key_4): self.ctl.set_mode("free")
        elif k in (Qt.Key_Return, Qt.Key_Enter):
            self.ctl.set_mode("full"); img = self.pix.toImage(); img.setDevicePixelRatio(1); self.ctl.finish(img)


class SnipToolbar(QFrame):
    def __init__(self, ctl):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setObjectName("snipbar")
        self.setStyleSheet("QFrame#snipbar{background:#ffffff;border:1px solid #cbd5e1;border-radius:12px;}"
                           "QPushButton{border:none;border-radius:8px;padding:6px 10px;background:transparent;}"
                           "QPushButton:hover{background:#eff6ff;} QPushButton:checked{background:#2563eb;color:white;}")
        h = QHBoxLayout(self); h.setContentsMargins(6, 6, 6, 6); h.setSpacing(4)
        self.btns = {}
        g = QButtonGroup(self)
        for key, txt, ic, tip in [("rect", T("Vùng"), "region", "R"), ("free", T("Tự do"), "lasso", "D"),
                                  ("window", T("Cửa sổ"), "window", "W"), ("full", T("Toàn màn hình"), "monitor", "F")]:
            b = QPushButton(" " + txt); b.setCheckable(True); b.setIconSize(QSize(18, 18)); b.setProperty("ic", ic)
            b.setToolTip(tip); g.addButton(b); self.btns[key] = b; h.addWidget(b)
            b.clicked.connect(lambda _=False, k=key: ctl.set_mode(k))
        sep = QFrame(); sep.setFixedWidth(1); sep.setStyleSheet("background:#e2e8f0"); h.addWidget(sep)
        x = QPushButton(theme.icon("close", "#475569"), ""); x.setToolTip(T("Huỷ (Esc)")); x.setIconSize(QSize(16, 16))
        x.clicked.connect(lambda: ctl.finish(None)); h.addWidget(x)

    def set_mode(self, m):
        for k, b in self.btns.items():
            b.setChecked(k == m); b.setIcon(theme.icon(b.property("ic"), "white" if k == m else "#334155"))


class SnipController(QObject):
    captured = Signal(QImage)

    def __init__(self):
        super().__init__()
        self.overlays = []
        self.active = False
        self.mode = "rect"

    def start(self, delay=0, mode="rect"):
        if self.active:
            return
        self.active = True
        self.mode = mode
        QTimer.singleShot(int(delay * 1000) + 120, self._freeze)

    def _freeze(self):
        import monitor_map
        self.wins = _windows_phys()
        self.overlays = []
        for s in QGuiApplication.screens():
            pix = s.grabWindow(0)
            origin = monitor_map.phys_origin(s)
            self.overlays.append(SnipOverlay(self, s, pix, origin))
        for o in self.overlays:
            o.show()
        self.bar = SnipToolbar(self)
        self.bar.set_mode(self.mode)
        scr = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        self.bar.adjustSize()
        g = scr.geometry()
        self.bar.move(g.x() + (g.width() - self.bar.width()) // 2, g.y() + 18)
        self.bar.show()
        for o in self.overlays:
            if o.scr is scr:
                o.activateWindow(); o.raise_(); o.setFocus()
        self.bar.raise_()

    def set_mode(self, m):
        self.mode = m
        self.bar.set_mode(m)
        for o in self.overlays:
            o.p0 = o.p1 = None; o.hover = None; o.pts = []; o.update()

    def finish(self, img):
        for o in self.overlays:
            o.close()
        self.overlays = []
        if getattr(self, "bar", None):
            self.bar.close()
        self.active = False
        if img is not None and not img.isNull():
            self.captured.emit(img)


class Toast(QFrame):
    """Bottom-right notification with thumbnail and actions."""

    def __init__(self, img, title, text, actions):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setObjectName("toast")
        self.setStyleSheet("QFrame#toast{background:#ffffff;border:1px solid #dbe3ef;border-radius:14px;}"
                           "QLabel#tt{font-weight:700;font-size:10.5pt;} QLabel#tx{color:#475569;}"
                           "QPushButton{padding:4px 12px;border-radius:7px;}")
        h = QHBoxLayout(self); h.setContentsMargins(12, 12, 12, 12); h.setSpacing(12)
        th = QLabel()
        from PySide6.QtGui import QPixmap
        pm = QPixmap.fromImage(img).scaled(96, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        th.setPixmap(pm); th.setFixedSize(96, 72); th.setAlignment(Qt.AlignCenter)
        th.setStyleSheet("background:#f1f5f9;border-radius:8px;")
        v = QVBoxLayout(); v.setSpacing(3)
        a = QLabel(title); a.setObjectName("tt")
        b = QLabel(text); b.setObjectName("tx"); b.setWordWrap(True)
        v.addWidget(a); v.addWidget(b)
        r = QHBoxLayout(); r.setSpacing(6)
        for txt, fn in actions:
            btn = QPushButton(txt)
            btn.clicked.connect(lambda _=False, f=fn: (f(), self.close()))
            r.addWidget(btn)
        r.addStretch(); v.addLayout(r)
        x = QPushButton(theme.icon("close", "#64748b"), ""); x.setFlat(True); x.setFixedSize(24, 24)
        x.clicked.connect(self.close)
        h.addWidget(th); h.addLayout(v, 1); h.addWidget(x, 0, Qt.AlignTop)
        self.setFixedWidth(400)
        self.adjustSize()
        g = QGuiApplication.primaryScreen().availableGeometry()
        self.move(g.right() - self.width() - 16, g.bottom() - self.height() - 16)
        self._t = QTimer(self, singleShot=True, interval=6000, timeout=self.close)
        self._t.start()

    def enterEvent(self, e):
        self._t.stop()

    def leaveEvent(self, e):
        self._t.start(2500)
