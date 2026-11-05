# Screen Recorder - Copyright (C) 2026 TuanPA <tuanpa1702@gmail.com>
# SPDX-License-Identifier: GPL-3.0-only
# This program is free software under the GNU GPL v3; see LICENSE. It comes WITHOUT ANY WARRANTY.
"""Clickable map of the monitor layout + 'identify' overlay."""
from PySide6.QtCore import Qt, QRectF, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QGuiApplication, QLinearGradient
from PySide6.QtWidgets import QWidget

import theme


def screen_for(m):
    """QScreen for a rec_core.monitors() entry. Qt may name screens by model ('DELL U2419H'), not \\\\.\\DISPLAYn,
    so fall back to matching physical size + position."""
    for s in QGuiApplication.screens():
        if s.name() == m["name"]:
            return s
    for s in QGuiApplication.screens():
        g, d = s.geometry(), s.devicePixelRatio()
        if round(g.width() * d) == m["w"] and round(g.height() * d) == m["h"] and \
                (g.x() == m["x"] or abs(round(g.x() * d) - m["x"]) <= 2) and (g.y() == m["y"] or abs(round(g.y() * d) - m["y"]) <= 2):
            return s
    return None


def phys_origin(screen):
    """Physical top-left (x, y) of a QScreen in virtual-desktop pixels."""
    import rec_core
    for m in rec_core.monitors():
        if screen_for(m) is screen:
            return m["x"], m["y"]
    d = screen.devicePixelRatio(); g = screen.geometry()
    return round(g.x() * d), round(g.y() * d)


def friendly_names(mons):
    """Display names for rec_core.monitors() entries, taken from Qt screens (e.g. 'DELL U2419H')."""
    out = []
    for m in mons:
        name = ""
        s = screen_for(m)
        if s is not None:
            if True:
                model = (s.model() or "").strip()
                manu = (s.manufacturer() or "").strip()
                nm = s.name() if not s.name().startswith("\\\\.\\") else ""
                name = nm or (model if len(model) > 3 else "")   # manufacturer alone is often junk ("Inc")
        out.append(name)
    return out


class MonitorMap(QWidget):
    picked = Signal(int)          # index into mons (last = "all" when several)

    def __init__(self):
        super().__init__()
        self.mons, self.names, self.sel, self.hover = [], [], 0, -1
        self.setMinimumHeight(132)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

    def set_monitors(self, mons, names):
        self.mons, self.names = mons, names
        self.update()

    def _real(self):
        return [m for m in self.mons if m["name"] != "all"]

    def _rects(self):
        real = self._real()
        if not real:
            return [], QRectF()
        x0 = min(m["x"] for m in real); y0 = min(m["y"] for m in real)
        x1 = max(m["x"] + m["w"] for m in real); y1 = max(m["y"] + m["h"] for m in real)
        W, H = self.width() - 150 if len(real) > 1 else self.width() - 20, self.height() - 16
        k = min(W / (x1 - x0), H / (y1 - y0))
        ox = 10 + (W - (x1 - x0) * k) / 2; oy = 8 + (H - (y1 - y0) * k) / 2
        rs = [QRectF(ox + (m["x"] - x0) * k + 3, oy + (m["y"] - y0) * k + 3, m["w"] * k - 6, m["h"] * k - 6) for m in real]
        all_r = QRectF(self.width() - 130, self.height() / 2 - 26, 120, 52) if len(real) > 1 else QRectF()
        return rs, all_r

    def _hit(self, pos):
        rs, all_r = self._rects()
        for i, r in enumerate(rs):
            if r.contains(pos):
                return i
        if not all_r.isNull() and all_r.contains(pos):
            return len(rs)
        return -1

    def mouseMoveEvent(self, e):
        h = self._hit(e.position())
        if h != self.hover:
            self.hover = h; self.update()

    def leaveEvent(self, e):
        self.hover = -1; self.update()

    def mousePressEvent(self, e):
        h = self._hit(e.position())
        if h >= 0:
            self.sel = h; self.update(); self.picked.emit(h)

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        rs, all_r = self._rects()
        blue = QColor(theme.ACCENT)
        all_sel = self.sel == len(rs) and len(rs) > 1
        for i, r in enumerate(rs):
            m = self._real()[i]
            on = self.sel == i or all_sel
            g = QLinearGradient(r.topLeft(), r.bottomRight())
            if on:
                g.setColorAt(0, QColor("#3b82f6")); g.setColorAt(1, QColor("#1d4ed8"))
            else:
                g.setColorAt(0, QColor("#f8fafc") if self.hover != i else QColor("#eff6ff")); g.setColorAt(1, QColor("#e2e8f0"))
            p.setPen(QPen(blue if (on or self.hover == i) else QColor("#94a3b8"), 2))
            p.setBrush(g); p.drawRoundedRect(r, 8, 8)
            p.setPen(QColor("white") if on else QColor("#0f172a"))
            f = QFont("Segoe UI", 1, QFont.Bold); f.setPixelSize(int(min(r.height() * 0.32, 30))); p.setFont(f)
            top = QRectF(r.x(), r.y() + 4, r.width(), r.height() * 0.55)
            p.drawText(top, Qt.AlignCenter, str(i + 1))
            f.setPixelSize(11); f.setBold(False); p.setFont(f)
            sub = f"{m['w']}×{m['h']}" + ("  ★" if m.get("primary") else "")
            nm = self.names[i] if i < len(self.names) else ""
            txt = (nm + "\n" if nm and r.height() > 60 else "") + sub
            p.drawText(QRectF(r.x() + 4, r.y() + r.height() * 0.52, r.width() - 8, r.height() * 0.46),
                       Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, txt)
        if not all_r.isNull():
            on = all_sel
            p.setPen(QPen(blue if on or self.hover == len(rs) else QColor("#94a3b8"), 2, Qt.SolidLine if on else Qt.DashLine))
            p.setBrush(QColor("#2563eb") if on else (QColor("#eff6ff") if self.hover == len(rs) else QColor("#f8fafc")))
            p.drawRoundedRect(all_r, 10, 10)
            p.setPen(QColor("white") if on else QColor("#0f172a"))
            f = QFont("Segoe UI", 1, QFont.DemiBold); f.setPixelSize(12); p.setFont(f)
            a = self.mons[-1]
            p.drawText(all_r, Qt.AlignCenter, f"{self.all_label}\n{a['w']}×{a['h']}")

    all_label = "All"


class IdentifyOverlay(QWidget):
    """Big number in the middle of every screen for 2 s."""

    def __init__(self, screen, number, label):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground); self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.n, self.label = number, label
        g = screen.geometry()
        self.setGeometry(g.x() + g.width() // 2 - 130, g.y() + g.height() // 2 - 130, 260, 260)
        QTimer.singleShot(2200, self.close)

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen); p.setBrush(QColor(37, 99, 235, 225)); p.drawRoundedRect(self.rect().adjusted(4, 4, -4, -4), 36, 36)
        p.setPen(QColor("white"))
        f = QFont("Segoe UI", 1, QFont.Bold); f.setPixelSize(130); p.setFont(f)
        p.drawText(QRectF(0, 10, 260, 180), Qt.AlignCenter, str(self.n))
        f.setPixelSize(16); f.setBold(False); p.setFont(f)
        p.drawText(QRectF(10, 180, 240, 60), Qt.AlignCenter | Qt.TextWordWrap, self.label)
