# Screen Recorder - Copyright (C) 2026 TuanPA <tuanpa1702@gmail.com>
# SPDX-License-Identifier: GPL-3.0-only
# This program is free software under the GNU GPL v3; see LICENSE. It comes WITHOUT ANY WARRANTY.
"""Snip editor: annotate a captured image (pen, highlighter, line, arrow, rect, ellipse, text, step number,
blur/pixelate, crop) with undo/redo, auto-copy to clipboard, save."""
import datetime, math, os

from PySide6.QtCore import Qt, QPointF, QRectF, QTimer, Signal, QSize, QLineF
from PySide6.QtGui import (QPainter, QColor, QPen, QBrush, QPixmap, QImage, QPainterPath, QFont, QKeySequence,
                           QShortcut, QGuiApplication, QUndoStack, QUndoCommand, QPolygonF, QTextCursor)
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsItem,
                               QGraphicsPixmapItem, QGraphicsPathItem, QGraphicsRectItem, QGraphicsEllipseItem,
                               QGraphicsTextItem, QPushButton, QButtonGroup, QLabel, QSpinBox, QFrame, QColorDialog,
                               QFileDialog, QComboBox, QToolButton, QMenu)

import theme
from i18n import T

COLORS = ["#ef4444", "#f97316", "#facc15", "#22c55e", "#3b82f6", "#a855f7", "#0f172a", "#ffffff"]
FLAGS = QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable


def _pen(color, w):
    return QPen(QColor(color), w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)


class HighlightItem(QGraphicsPathItem):
    def paint(self, p, opt, w=None):
        p.setCompositionMode(QPainter.CompositionMode_Multiply)
        p.setPen(self.pen()); p.setBrush(Qt.NoBrush); p.drawPath(self.path())
        if self.isSelected():
            p.setCompositionMode(QPainter.CompositionMode_SourceOver)
            p.setPen(QPen(QColor("#2563eb"), 1, Qt.DashLine)); p.drawRect(self.boundingRect())


class ArrowItem(QGraphicsPathItem):
    def __init__(self, a, b, pen, arrow=True):
        super().__init__()
        self.a, self.b, self.arrow = QPointF(a), QPointF(b), arrow
        self.setPen(pen); self.rebuild()

    def set_end(self, b):
        self.b = QPointF(b); self.rebuild()

    def rebuild(self):
        path = QPainterPath(self.a)
        w = self.pen().widthF()
        if self.arrow:
            line = QLineF(self.b, self.a)
            L = max(10.0, w * 3.6)
            if line.length() > 1:
                ang = math.atan2(-line.dy(), line.dx())
                base = self.b + QPointF(math.cos(ang) * L * 0.8, -math.sin(ang) * L * 0.8)
                path.lineTo(base)
            else:
                path.lineTo(self.b)
        else:
            path.lineTo(self.b)
        self.setPath(path)

    def boundingRect(self):
        w = self.pen().widthF() * 4 + 4
        return QRectF(self.a, self.b).normalized().adjusted(-w, -w, w, w)

    def shape(self):
        ps = QPainterPath(); ps.moveTo(self.a); ps.lineTo(self.b)
        from PySide6.QtGui import QPainterPathStroker
        s = QPainterPathStroker(); s.setWidth(max(10, self.pen().widthF() * 3))
        return s.createStroke(ps)

    def paint(self, p, opt, w=None):
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(self.pen()); p.drawPath(self.path())
        if self.arrow:
            line = QLineF(self.b, self.a)
            if line.length() > 1:
                ang = math.atan2(-line.dy(), line.dx())
                L = max(10.0, self.pen().widthF() * 3.6)
                p1 = self.b + QPointF(math.cos(ang + 0.45) * L, -math.sin(ang + 0.45) * L)
                p2 = self.b + QPointF(math.cos(ang - 0.45) * L, -math.sin(ang - 0.45) * L)
                p.setPen(Qt.NoPen); p.setBrush(self.pen().color())
                p.drawPolygon(QPolygonF([self.b, p1, p2]))
        if self.isSelected():
            p.setPen(QPen(QColor("#2563eb"), 1, Qt.DashLine)); p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(self.a, self.b).normalized())


class StepItem(QGraphicsItem):
    def __init__(self, n, color, size):
        super().__init__()
        self.n, self.color, self.size = n, QColor(color), size

    def boundingRect(self):
        s = self.size
        return QRectF(-s / 2 - 2, -s / 2 - 2, s + 4, s + 4)

    def paint(self, p, opt, w=None):
        p.setRenderHint(QPainter.Antialiasing)
        s = self.size
        p.setPen(QPen(QColor("white"), 2)); p.setBrush(self.color)
        p.drawEllipse(QRectF(-s / 2, -s / 2, s, s))
        p.setPen(QColor("white") if self.color.lightness() < 170 else QColor("#0f172a"))
        f = QFont("Segoe UI", 1, QFont.Bold); f.setPixelSize(int(s * 0.55)); p.setFont(f)
        p.drawText(QRectF(-s / 2, -s / 2, s, s), Qt.AlignCenter, str(self.n))
        if self.isSelected():
            p.setPen(QPen(QColor("#2563eb"), 1, Qt.DashLine)); p.setBrush(Qt.NoBrush); p.drawRect(self.boundingRect())


class BlurItem(QGraphicsRectItem):
    """Pixelates whatever part of the base image lies under it (follows moves and crops)."""

    def __init__(self, rect, editor):
        super().__init__(rect)
        self.ed = editor
        self.block = 12
        self.setPen(Qt.NoPen)

    def paint(self, p, opt, w=None):
        r = self.mapRectToScene(self.rect()).intersected(self.ed.base.sceneBoundingRect())
        if r.width() >= 1 and r.height() >= 1:
            src = self.ed.base.pixmap().copy(r.toAlignedRect())
            b = self.block
            small = src.scaled(max(1, src.width() // b), max(1, src.height() // b), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            big = small.scaled(src.size(), Qt.IgnoreAspectRatio, Qt.FastTransformation)
            p.drawPixmap(self.mapRectFromScene(QRectF(r.toAlignedRect())), big, QRectF(big.rect()))
        if self.isSelected() or self.ed.tool == "blur":
            p.setPen(QPen(QColor("#2563eb"), 1, Qt.DashLine)); p.setBrush(Qt.NoBrush); p.drawRect(self.rect())


class TextItem(QGraphicsTextItem):
    def __init__(self, ed):
        super().__init__()
        self.ed = ed

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        if not self.toPlainText().strip():
            QTimer.singleShot(0, lambda: self.ed.drop_empty_text(self))
        else:
            self.ed.changed()

    def mouseDoubleClickEvent(self, e):
        self.setTextInteractionFlags(Qt.TextEditorInteraction); self.setFocus()
        super().mouseDoubleClickEvent(e)


# ---------------- undo commands ----------------
class AddCmd(QUndoCommand):
    def __init__(self, scene, items, text="add"):
        super().__init__(text); self.sc, self.items, self.first = scene, items, True

    def redo(self):
        for it in self.items:
            if it.scene() is None:
                self.sc.addItem(it)

    def undo(self):
        for it in self.items:
            self.sc.removeItem(it)


class RemoveCmd(AddCmd):
    def redo(self): AddCmd.undo(self)
    def undo(self): AddCmd.redo(self)


class MoveCmd(QUndoCommand):
    def __init__(self, moves):
        super().__init__("move"); self.moves = moves  # [(item, old, new)]

    def redo(self):
        for it, o, n in self.moves: it.setPos(n)

    def undo(self):
        for it, o, n in self.moves: it.setPos(o)


class StyleCmd(QUndoCommand):
    def __init__(self, items, fn_new, fn_old):
        super().__init__("style"); self.fn_new, self.fn_old = fn_new, fn_old

    def redo(self): self.fn_new()
    def undo(self): self.fn_old()


class CropCmd(QUndoCommand):
    def __init__(self, ed, rect):
        super().__init__("crop")
        self.ed, self.rect = ed, rect.toAlignedRect()
        self.old = ed.base.pixmap()
        self.new = self.old.copy(self.rect)

    def _apply(self, pix, dx, dy):
        self.ed.base.setPixmap(pix)
        for it in self.ed.scene.items():
            if it is not self.ed.base and not isinstance(it, Handles) and it.parentItem() is None:
                it.moveBy(dx, dy)
        self.ed.scene.setSceneRect(QRectF(pix.rect()))
        self.ed.update_info()

    def redo(self): self._apply(self.new, -self.rect.x(), -self.rect.y())
    def undo(self): self._apply(self.old, self.rect.x(), self.rect.y())


# ---------------- transform handles (resize / rotate) ----------------
RECT_LIKE = (QGraphicsRectItem, QGraphicsEllipseItem)       # BlurItem is a QGraphicsRectItem too


def item_state(it):
    s = dict(pos=QPointF(it.pos()), rot=it.rotation(), scale=it.scale(), origin=QPointF(it.transformOriginPoint()))
    if isinstance(it, ArrowItem):
        s["a"], s["b"] = QPointF(it.a), QPointF(it.b)
    elif isinstance(it, RECT_LIKE):
        s["rect"] = QRectF(it.rect())
    return s


def set_item_state(it, s):
    it.prepareGeometryChange()
    if "a" in s:
        it.a, it.b = QPointF(s["a"]), QPointF(s["b"]); it.rebuild()
    if "rect" in s:
        it.setRect(s["rect"])
    it.setTransformOriginPoint(s["origin"]); it.setRotation(s["rot"]); it.setScale(s["scale"]); it.setPos(s["pos"])
    it.update()


class TransformCmd(QUndoCommand):
    def __init__(self, it, old, new):
        super().__init__("transform"); self.it, self.old, self.new = it, old, new
        self.done = True

    def redo(self):
        if self.done:          # first redo happens when pushed: state is already applied
            self.done = False; return
        set_item_state(self.it, self.new)

    def undo(self):
        set_item_state(self.it, self.old)


class Handles(QGraphicsItem):
    """Selection frame for ONE item: 8 resize grips + a rotate grip; lines/arrows get 2 end grips."""
    R = 5           # grip radius in view pixels

    def __init__(self, ed):
        super().__init__()
        self.ed = ed
        self.target = None
        self.setZValue(1e9)
        self.setAcceptedMouseButtons(Qt.NoButton)

    def zoom(self):
        return max(1e-3, self.ed.view.transform().m11())

    def refresh(self):
        try:
            sel = [i for i in self.ed.scene.selectedItems() if i is not self.ed.base and i is not self]
        except RuntimeError:          # editor is being destroyed
            return
        if self.ed.tool == "select":
            self.target = sel[0] if len(sel) == 1 else None
        else:   # drawing tools: the shape just drawn keeps its grips until the next one
            li = self.ed.last_item
            self.target = li if li is not None and li.scene() is self.ed.scene and self.ed.tool != "crop" else None
        self.prepareGeometryChange(); self.update()

    def boundingRect(self):
        return self.ed.scene.sceneRect().adjusted(-4000, -4000, 4000, 4000)

    def local_rect(self):
        t = self.target
        if isinstance(t, ArrowItem):
            return QRectF(t.a, t.b).normalized()
        if isinstance(t, RECT_LIKE):
            return t.rect().normalized()
        return t.boundingRect()

    def grips(self):
        """{name: scene point}"""
        t = self.target
        if t is None:
            return {}
        if isinstance(t, ArrowItem):
            return {"a": t.mapToScene(t.a), "b": t.mapToScene(t.b)}
        r = self.local_rect()
        cx, cy = r.center().x(), r.center().y()
        pts = {"tl": (r.left(), r.top()), "t": (cx, r.top()), "tr": (r.right(), r.top()), "r": (r.right(), cy),
               "br": (r.right(), r.bottom()), "b": (cx, r.bottom()), "bl": (r.left(), r.bottom()), "l": (r.left(), cy)}
        g = {k: t.mapToScene(QPointF(*v)) for k, v in pts.items()}
        # rotate grip: 26 view-px above the top-middle, along the item's "up" direction
        up = g["t"] - t.mapToScene(QPointF(cx, cy))
        L = math.hypot(up.x(), up.y()) or 1
        g["rot"] = g["t"] + up / L * (26 / self.zoom())
        return g

    def hit(self, scene_pt):
        tol = (self.R + 4) / self.zoom()
        for k, p in self.grips().items():
            if math.hypot(p.x() - scene_pt.x(), p.y() - scene_pt.y()) <= tol:
                return k
        return None

    def paint(self, p, opt, w=None):
        t = self.target
        if t is None or t.scene() is None:
            return
        z = self.zoom()
        g = self.grips()
        p.setRenderHint(QPainter.Antialiasing)
        blue = QColor("#2563eb")
        if not isinstance(t, ArrowItem):
            r = self.local_rect()
            poly = QPolygonF([t.mapToScene(c) for c in (r.topLeft(), r.topRight(), r.bottomRight(), r.bottomLeft())])
            p.setPen(QPen(blue, 1.2 / z, Qt.DashLine)); p.setBrush(Qt.NoBrush); p.drawPolygon(poly)
            p.setPen(QPen(blue, 1.2 / z)); p.drawLine(g["t"], g["rot"])
        rr = self.R / z
        for k, pt in g.items():
            p.setPen(QPen(blue, 1.5 / z))
            p.setBrush(QColor("#2563eb") if k == "rot" else QColor("white"))
            if k == "rot":
                p.drawEllipse(pt, rr * 1.15, rr * 1.15)
            else:
                p.drawRect(QRectF(pt.x() - rr, pt.y() - rr, 2 * rr, 2 * rr))


CURSORS = {"tl": Qt.SizeFDiagCursor, "br": Qt.SizeFDiagCursor, "tr": Qt.SizeBDiagCursor, "bl": Qt.SizeBDiagCursor,
           "t": Qt.SizeVerCursor, "b": Qt.SizeVerCursor, "l": Qt.SizeHorCursor, "r": Qt.SizeHorCursor,
           "a": Qt.CrossCursor, "b_": Qt.CrossCursor}
OPP = {"tl": "br", "tr": "bl", "br": "tl", "bl": "tr", "t": "b", "b": "t", "l": "r", "r": "l"}


class GripDrag:
    """Resize / rotate the handle target; keeps the opposite grip fixed on screen."""

    def __init__(self, ed, item, grip, scene_pt):
        self.ed, self.it, self.g = ed, item, grip
        self.old = item_state(item)
        r = ed.handles.local_rect()
        self.r0 = QRectF(r)
        c = item.mapToScene(r.center())
        self.c = c
        self.a0 = math.degrees(math.atan2(scene_pt.y() - c.y(), scene_pt.x() - c.x()))
        self.rot0 = item.rotation()
        self.scale0 = item.scale()
        if grip in OPP:
            corner = {"tl": r.topLeft(), "tr": r.topRight(), "br": r.bottomRight(), "bl": r.bottomLeft(),
                      "t": QPointF(r.center().x(), r.top()), "b": QPointF(r.center().x(), r.bottom()),
                      "l": QPointF(r.left(), r.center().y()), "r": QPointF(r.right(), r.center().y())}
            self.anchor_local = corner[OPP[grip]]
            self.anchor_scene = item.mapToScene(self.anchor_local)
            self.grip0 = ed.handles.grips()[grip]

    def _recenter(self, anchor_local_new):
        """Move the rotation origin to the new center, then shift pos so the anchor stays put on screen."""
        it = self.it
        it.setTransformOriginPoint(self.ed.handles.local_rect().center())
        d = self.anchor_scene - it.mapToScene(anchor_local_new)
        it.setPos(it.pos() + d)

    def move(self, sp, mods):
        it, g = self.it, self.g
        it.prepareGeometryChange()
        if g == "rot":
            a = math.degrees(math.atan2(sp.y() - self.c.y(), sp.x() - self.c.x()))
            ang = self.rot0 + a - self.a0
            if mods & Qt.ShiftModifier:
                ang = round(ang / 15) * 15
            if not it.transformOriginPoint() == self.r0.center():
                anchor = self.r0.center(); self.anchor_scene = it.mapToScene(anchor)
                it.setTransformOriginPoint(anchor); it.setPos(it.pos() + self.anchor_scene - it.mapToScene(anchor))
            it.setRotation(ang)
        elif g in ("a", "b"):
            lp = it.mapFromScene(sp)
            if mods & Qt.ShiftModifier:
                o = it.b if g == "a" else it.a
                d = lp - o; ang = round(math.atan2(d.y(), d.x()) / (math.pi / 4)) * (math.pi / 4)
                L = math.hypot(d.x(), d.y()); lp = o + QPointF(math.cos(ang) * L, math.sin(ang) * L)
            if g == "a": it.a = lp
            else: it.b = lp
            it.rebuild()
        elif isinstance(it, RECT_LIKE):
            lp = it.mapFromScene(sp)
            r = QRectF(self.r0)
            if g in ("tl", "tr", "bl", "br"):
                r = QRectF(self.anchor_local, lp).normalized()
                if mods & Qt.ShiftModifier:          # keep aspect ratio
                    k = max(r.width() / max(self.r0.width(), 1), r.height() / max(self.r0.height(), 1))
                    w, h = self.r0.width() * k, self.r0.height() * k
                    sx = 1 if lp.x() >= self.anchor_local.x() else -1
                    sy = 1 if lp.y() >= self.anchor_local.y() else -1
                    r = QRectF(self.anchor_local, self.anchor_local + QPointF(sx * w, sy * h)).normalized()
            elif g in ("t", "b"):
                r.setTop(min(lp.y(), self.anchor_local.y())); r.setBottom(max(lp.y(), self.anchor_local.y()))
            else:
                r.setLeft(min(lp.x(), self.anchor_local.x())); r.setRight(max(lp.x(), self.anchor_local.x()))
            if r.width() < 2: r.setWidth(2)
            if r.height() < 2: r.setHeight(2)
            it.setRect(r)
            self._recenter(self.anchor_local)
        else:
            # paths, text, step numbers: proportional scale around the center
            # project the mouse onto the anchor→grip axis: ratio to the original length = new scale
            ax = self.grip0 - self.anchor_scene
            L0 = math.hypot(ax.x(), ax.y()) or 1
            v = sp - self.anchor_scene
            proj = (v.x() * ax.x() + v.y() * ax.y()) / L0
            k = max(0.05, self.scale0 * proj / L0)
            it.setTransformOriginPoint(self.r0.center())
            it.setScale(k)
            it.setPos(it.pos() + self.anchor_scene - it.mapToScene(self.anchor_local))
        it.update()
        self.ed.handles.refresh()

    def finish(self):
        new = item_state(self.it)
        if new != self.old:
            self.ed.undo.push(TransformCmd(self.it, self.old, new))


# ---------------- view ----------------
class Canvas(QGraphicsView):
    def __init__(self, ed):
        super().__init__(ed.scene)
        self.ed = ed
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setBackgroundBrush(QColor("#eef2f7"))
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setFrameShape(QFrame.NoFrame)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.cur = None
        self.start = None
        self.grip = None
        self.tool_cursor = Qt.CrossCursor
        pm =theme.icon("refresh", "#2563eb").pixmap(22, 22)
        from PySide6.QtGui import QCursor
        self.rot_cursor = QCursor(pm, 11, 11)

    def keyPressEvent(self, e):
        f = self.ed.scene.focusItem()
        if isinstance(f, QGraphicsTextItem) and f.textInteractionFlags() & Qt.TextEditorInteraction:
            if e.key() == Qt.Key_Escape:
                f.clearFocus(); return
            return super().keyPressEvent(e)           # typing text: letters are not tool shortcuts
        k = e.key()
        if e.modifiers() in (Qt.NoModifier, Qt.KeypadModifier):
            if k in self.ed.key_tools:
                return self.ed.set_tool(self.ed.key_tools[k])
            if k in (Qt.Key_Delete, Qt.Key_Backspace):
                return self.ed.delete_selected()
            if k == Qt.Key_Escape:
                return self.ed.scene.clearSelection()
        super().keyPressEvent(e)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
            self.scale(f, f); self.ed.update_info()
        else:
            super().wheelEvent(e)

    def drawForeground(self, p, rect):
        if self.ed.tool == "crop" and self.cur is not None:
            r = self.cur
            full = self.ed.scene.sceneRect()
            path = QPainterPath(); path.addRect(full); hole = QPainterPath(); hole.addRect(r)
            p.fillPath(path.subtracted(hole), QColor(15, 23, 42, 130))
            p.setPen(QPen(QColor("white"), 0, Qt.DashLine)); p.drawRect(r)

    def _constrain(self, a, b, mods, kind):
        if not (mods & Qt.ShiftModifier):
            return b
        d = b - a
        if kind in ("rect", "ellipse", "blur", "crop"):
            s = max(abs(d.x()), abs(d.y()))
            return a + QPointF(math.copysign(s, d.x() or 1), math.copysign(s, d.y() or 1))
        ang = round(math.atan2(d.y(), d.x()) / (math.pi / 4)) * (math.pi / 4)
        L = math.hypot(d.x(), d.y())
        return a + QPointF(math.cos(ang) * L, math.sin(ang) * L)

    def mousePressEvent(self, e):
        ed = self.ed
        t = ed.tool
        if e.button() == Qt.LeftButton and ed.handles.target is not None:
            sp = self.mapToScene(e.position().toPoint())
            g = ed.handles.hit(sp)
            if g:
                self.grip = GripDrag(ed, ed.handles.target, g, sp)
                return
        if e.button() != Qt.LeftButton or t == "select":
            if t == "select":
                ed.begin_move()
            super().mousePressEvent(e)
            ed.handles.refresh()
            return
        pt = self.mapToScene(e.position().toPoint())
        self.start = pt
        c, w = ed.color, ed.stroke
        if t in ("pen", "highlight"):
            path = QPainterPath(pt)
            it = HighlightItem() if t == "highlight" else QGraphicsPathItem()
            if t == "highlight":
                col = QColor(c); it.setPen(QPen(col, w * 4, Qt.SolidLine, Qt.FlatCap, Qt.RoundJoin))
            else:
                it.setPen(_pen(c, w))
            it.setPath(path); self.cur = it
        elif t in ("line", "arrow"):
            self.cur = ArrowItem(pt, pt, _pen(c, w), t == "arrow")
        elif t == "rect":
            self.cur = QGraphicsRectItem(QRectF(pt, pt)); self.cur.setPen(_pen(c, w)); self.cur.setBrush(ed.fill_brush())
        elif t == "ellipse":
            self.cur = QGraphicsEllipseItem(QRectF(pt, pt)); self.cur.setPen(_pen(c, w)); self.cur.setBrush(ed.fill_brush())
        elif t == "blur":
            self.cur = BlurItem(QRectF(pt, pt), ed)
        elif t == "crop":
            self.cur = QRectF(pt, pt); self.viewport().update(); return
        elif t == "text":
            return ed.add_text(pt)
        elif t == "step":
            return ed.add_step(pt)
        if self.cur is not None:
            ed.scene.addItem(self.cur)

    def mouseMoveEvent(self, e):
        sp = self.mapToScene(e.position().toPoint())
        if self.grip is not None:
            return self.grip.move(sp, e.modifiers())
        if self.cur is None:
            g = self.ed.handles.hit(sp) if self.ed.handles.target is not None else None
            if g == "rot":
                self.viewport().setCursor(self.rot_cursor)
            elif g:
                self.viewport().setCursor(CURSORS.get(g, Qt.CrossCursor))
            else:
                self.viewport().setCursor(self.tool_cursor)
            super().mouseMoveEvent(e)
            if e.buttons():
                self.ed.handles.refresh()
            return
        t = self.ed.tool
        pt = self._constrain(self.start, self.mapToScene(e.position().toPoint()), e.modifiers(), t)
        if t in ("pen", "highlight"):
            path = self.cur.path(); path.lineTo(pt); self.cur.setPath(path)
        elif t in ("line", "arrow"):
            self.cur.prepareGeometryChange(); self.cur.set_end(pt)
        elif t == "crop":
            self.cur = QRectF(self.start, pt).normalized().intersected(self.ed.scene.sceneRect())
            self.viewport().update()
        else:
            self.cur.setRect(QRectF(self.start, pt).normalized())

    def mouseReleaseEvent(self, e):
        ed = self.ed
        if self.grip is not None:
            self.grip.finish(); self.grip = None; ed.handles.refresh(); return
        if ed.tool == "select":
            super().mouseReleaseEvent(e); ed.end_move(); ed.handles.refresh(); return
        if self.cur is None:
            if ed.tool in ("text", "step"):
                return          # forwarding the release would steal focus from the new text box
            return super().mouseReleaseEvent(e)
        it, self.cur = self.cur, None
        if ed.tool == "crop":
            self.viewport().update()
            if it.width() > 4 and it.height() > 4:
                ed.undo.push(CropCmd(ed, it)); ed.fit()
            return
        br = it.boundingRect()
        if br.width() < 3 and br.height() < 3 and ed.tool not in ("pen", "highlight"):
            ed.scene.removeItem(it); return
        ed.scene.removeItem(it)
        it.setFlags(FLAGS)
        ed.last_item = it
        ed.undo.push(AddCmd(ed.scene, [it]))


class Swatch(QPushButton):
    def __init__(self, color):
        super().__init__()
        self.color = color
        self.setFixedSize(22, 22); self.setCheckable(True)
        self.setStyleSheet(f"QPushButton{{background:{color};border:1px solid #cbd5e1;border-radius:11px;padding:0}}"
                           f"QPushButton:checked{{border:3px solid #2563eb;}}")


class Editor(QWidget):
    new_snip = Signal()

    def __init__(self, img, save_dir):
        super().__init__()
        self.setObjectName("editor")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(T("Chỉnh sửa ảnh chụp") + " - Screen Recorder")
        self.setWindowIcon(theme.app_icon_icon())
        self.setStyleSheet("QWidget#editor{background:#ffffff;}")
        self.save_dir = save_dir
        self.saved_path = None
        self.scene = QGraphicsScene(self)
        self.base = QGraphicsPixmapItem(QPixmap.fromImage(img)); self.base.setZValue(-1000)
        self.base.setTransformationMode(Qt.SmoothTransformation)
        self.scene.addItem(self.base)
        self.scene.setSceneRect(QRectF(self.base.pixmap().rect()))
        self.undo = QUndoStack(self)
        self.tool = "arrow"
        self.color = COLORS[0]
        self.stroke = 4
        self.fill = 0
        self.step_n = 1
        self.last_item = None
        self._moving = None
        self._copy_t = QTimer(self, singleShot=True, interval=350, timeout=self.copy_clip)
        self.undo.indexChanged.connect(lambda _: self.changed())
        self.build()
        self.handles = Handles(self)
        self.scene.addItem(self.handles)
        self.scene.selectionChanged.connect(lambda: self.handles.refresh())
        self.undo.indexChanged.connect(lambda _: self.handles.refresh())
        self.set_tool("arrow")
        self.resize_to_image()

    # ---- UI ----
    def build(self):
        I = theme.icon
        L = QVBoxLayout(self); L.setContentsMargins(0, 0, 0, 0); L.setSpacing(0)
        bar = QFrame(); bar.setObjectName("bar")
        bar.setStyleSheet(
            "QFrame#bar{background:#ffffff;border:none;border-bottom:1px solid #e2e8f0;border-radius:0}"
            "QFrame#grp{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(239,246,255,0.95),stop:1 rgba(238,242,255,0.9));"
            "border:1px solid rgba(191,219,254,0.85);border-radius:12px}"
            "QPushButton#tool{border:none;border-radius:8px;padding:6px;background:transparent;min-width:20px}"
            "QPushButton#tool:hover{background:rgba(219,234,254,0.95)}"
            "QPushButton#tool:checked{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #3b82f6,stop:1 #2563eb)}"
            "QPushButton#step{border:1px solid #cbd5e1;border-radius:7px;background:white;padding:0;min-width:24px;max-width:24px;min-height:24px;max-height:24px;font-weight:700}"
            "QPushButton#step:hover{border-color:#60a5fa;background:#eff6ff}"
            "QLabel#val{min-width:44px;qproperty-alignment:AlignCenter;font-weight:600;background:transparent}"
            "QLabel#glbl{color:#64748b;font-size:8pt;background:transparent}")
        h = QHBoxLayout(bar); h.setContentsMargins(10, 8, 10, 8); h.setSpacing(6)

        def group(title=None):
            f = QFrame(); f.setObjectName("grp")
            gh = QHBoxLayout(f); gh.setContentsMargins(6, 4, 6, 4); gh.setSpacing(2)
            h.addWidget(f)
            return gh

        self.tool_btns = {}
        self.key_tools = {}
        g = QButtonGroup(self)
        groups = [[("select", "select", T("Chọn / di chuyển / xoay / co giãn") + " (V)", "V")],
                  [("pen", "pen", T("Bút vẽ") + " (P)", "P"), ("highlight", "highlight", T("Bút dạ quang") + " (H)", "H")],
                  [("line", "line", T("Đường thẳng") + " (L)", "L"), ("arrow", "arrow", T("Mũi tên") + " (A)", "A"),
                   ("rect", "rect", T("Hình chữ nhật") + " (R)", "R"), ("ellipse", "ellipse", T("Hình elip") + " (E)", "E")],
                  [("text", "text", T("Chữ") + " (T)", "T"), ("step", "step", T("Đánh số thứ tự") + " (N)", "N"),
                   ("blur", "blur", T("Làm mờ / che thông tin") + " (B)", "B"), ("crop", "crop", T("Cắt ảnh") + " (C)", "C")]]
        for grp in groups:
            gh = group()
            for key, ic, tip, sc in grp:
                b = QPushButton(); b.setObjectName("tool"); b.setCheckable(True); b.setToolTip(tip)
                b.setIconSize(QSize(20, 20)); b.setProperty("ic", ic)
                g.addButton(b); self.tool_btns[key] = b; gh.addWidget(b)
                b.clicked.connect(lambda _=False, k=key: self.set_tool(k))
                self.key_tools[getattr(Qt, "Key_" + sc)] = key

        # colors
        gh = group(); gh.setSpacing(5); gh.setContentsMargins(10, 4, 6, 4)
        self.swatches = []
        for c in COLORS:
            sw = Swatch(c); sw.clicked.connect(lambda _=False, c=c: self.set_color(c)); self.swatches.append(sw); gh.addWidget(sw)
        more = QPushButton(I("palette", "#475569"), ""); more.setObjectName("tool"); more.setToolTip(T("Màu khác…"))
        more.clicked.connect(self.pick_color); gh.addWidget(more)

        # stroke width stepper + fill mode
        gh = group(); gh.setSpacing(4); gh.setContentsMargins(8, 4, 8, 4)
        minus = QPushButton("−"); minus.setObjectName("step"); minus.setToolTip(T("Mảnh hơn / nhỏ hơn"))
        plus = QPushButton("+"); plus.setObjectName("step"); plus.setToolTip(T("Dày hơn / lớn hơn"))
        self.lbl_w = QLabel(); self.lbl_w.setObjectName("val"); self.lbl_w.setToolTip(T("Độ dày nét / cỡ chữ"))
        minus.clicked.connect(lambda: self.set_width(max(1, self.stroke - 1)))
        plus.clicked.connect(lambda: self.set_width(min(40, self.stroke + 1)))
        for wdg in (minus, self.lbl_w, plus):
            gh.addWidget(wdg)
        sep = QFrame(); sep.setFixedSize(1, 22); sep.setStyleSheet("background:#cbd5e1;border:none"); gh.addSpacing(4); gh.addWidget(sep); gh.addSpacing(4)
        self.fill_btns = []
        fg = QButtonGroup(self)
        for i, (ic, tip) in enumerate([("fill-none", T("Không tô")), ("fill-light", T("Tô mờ")), ("fill-solid", T("Tô đặc"))]):
            b = QPushButton(); b.setObjectName("tool"); b.setCheckable(True); b.setIconSize(QSize(20, 20))
            b.setToolTip(tip + " – " + T("Tô nền cho hình chữ nhật / elip")); b.setProperty("ic", ic)
            fg.addButton(b); self.fill_btns.append(b); gh.addWidget(b)
            b.clicked.connect(lambda _=False, i=i: self.set_fill(i))
        h.addStretch()

        gh = group()
        for ic, tip, red in [("undo", T("Hoàn tác") + " (Ctrl+Z)", False), ("redo", T("Làm lại") + " (Ctrl+Y)", True)]:
            b = QPushButton(I(ic, "#334155"), ""); b.setObjectName("tool"); b.setToolTip(tip); b.setIconSize(QSize(20, 20))
            b.clicked.connect(lambda _=False, r=red: self._undo_key(r)); gh.addWidget(b)
        QShortcut(QKeySequence.Undo, self, activated=lambda: self._undo_key(False))
        QShortcut(QKeySequence.Redo, self, activated=lambda: self._undo_key(True))
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, activated=lambda: self._undo_key(True))

        self.btn_new = QPushButton(I("plus", "#334155"), ""); self.btn_new.setToolTip(T("Chụp mới") + " (Ctrl+N)")
        self.btn_new.clicked.connect(self.new_snip.emit)
        self.btn_copy = QPushButton(I("copy", "#334155"), ""); self.btn_copy.setToolTip(T("Copy") + " (Ctrl+C)")
        self.btn_copy.clicked.connect(lambda: self.copy_clip(True))
        self.btn_save = QPushButton(I("save", "white"), " " + T("Lưu"))
        self.btn_save.setToolTip(T("Lưu nhanh vào thư mục ảnh (Ctrl+S) • Shift+Ctrl+S: Lưu thành…"))
        self.btn_save.setStyleSheet("QPushButton{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #3b82f6,stop:1 #2563eb);"
                                    "color:white;border:none;font-weight:600;border-radius:8px;padding:7px 16px}"
                                    "QPushButton:hover{background:#1d4ed8}")
        self.btn_save.clicked.connect(self.quick_save)
        for b in (self.btn_new, self.btn_copy, self.btn_save):
            b.setIconSize(QSize(18, 18)); b.setMinimumHeight(36); h.addWidget(b)
        QShortcut(QKeySequence.New, self, activated=self.new_snip.emit)
        QShortcut(QKeySequence.Copy, self, activated=self._copy_key)
        QShortcut(QKeySequence.Save, self, activated=self.quick_save)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, activated=self.save_as)
        QShortcut(QKeySequence("Ctrl+0"), self, activated=self.fit)
        QShortcut(QKeySequence("Ctrl+1"), self, activated=self.zoom100)
        QShortcut(QKeySequence("Ctrl+="), self, activated=lambda: self.set_width(min(40, self.stroke + 1)))
        QShortcut(QKeySequence("Ctrl+-"), self, activated=lambda: self.set_width(max(1, self.stroke - 1)))
        for w in bar.findChildren(QPushButton):
            w.setFocusPolicy(Qt.NoFocus)          # clicking a tool must not grab the keyboard
        L.addWidget(bar)
        self.view = Canvas(self)
        self.view.setFocus()
        L.addWidget(self.view, 1)
        st = QFrame(); st.setStyleSheet("QFrame{background:#f8fafc;border-top:1px solid #e2e8f0}")
        sh = QHBoxLayout(st); sh.setContentsMargins(12, 4, 12, 4)
        self.lbl_info = QLabel(); self.lbl_info.setObjectName("hint")
        self.lbl_state = QLabel(); self.lbl_state.setObjectName("hint")
        z1 = QPushButton(T("Vừa khung")); z1.clicked.connect(self.fit)
        z2 = QPushButton("100%"); z2.clicked.connect(self.zoom100)
        for z in (z1, z2):
            z.setStyleSheet("padding:2px 10px")
        sh.addWidget(self.lbl_info); sh.addStretch(); sh.addWidget(self.lbl_state); sh.addSpacing(12); sh.addWidget(z1); sh.addWidget(z2)
        L.addWidget(st)
        self.set_color(self.color)
        self.set_width(self.stroke, apply=False)
        self.set_fill(self.fill, apply=False)

    def resize_to_image(self):
        scr = QGuiApplication.primaryScreen().availableGeometry()
        r = self.base.pixmap().rect()
        w = min(max(r.width() + 60, self.minimumSizeHint().width(), 980), int(scr.width() * 0.96))
        h = min(max(r.height() + 150, 520), int(scr.height() * 0.9))
        self.resize(w, h)
        self.move(scr.x() + (scr.width() - w) // 2, scr.y() + (scr.height() - h) // 2)
        QTimer.singleShot(0, self.fit_if_big)

    def fit_if_big(self):
        vr = self.view.viewport().rect()
        r = self.scene.sceneRect()
        if r.width() > vr.width() - 20 or r.height() > vr.height() - 20:
            self.fit()
        else:
            self.zoom100()

    def fit(self):
        self.view.fitInView(self.scene.sceneRect().adjusted(-10, -10, 10, 10), Qt.KeepAspectRatio); self.update_info()

    def zoom100(self):
        self.view.resetTransform(); self.view.centerOn(self.scene.sceneRect().center()); self.update_info()

    def update_info(self):
        r = self.base.pixmap().rect()
        z = self.view.transform().m11() * 100 if hasattr(self, "view") else 100
        if hasattr(self, "lbl_info"):
            self.lbl_info.setText(f"{r.width()} × {r.height()} px  •  {z:.0f}%")

    # ---- tool state ----
    def set_tool(self, k):
        self.tool = k
        for key, b in self.tool_btns.items():
            b.setChecked(key == k); b.setIcon(theme.icon(b.property("ic"), "white" if key == k else "#334155"))
        self.view.setDragMode(QGraphicsView.RubberBandDrag if k == "select" else QGraphicsView.NoDrag)
        cur = Qt.ArrowCursor if k == "select" else (Qt.IBeamCursor if k == "text" else Qt.CrossCursor)
        self.view.tool_cursor = cur
        self.view.viewport().setCursor(cur)
        movable = k == "select"
        for it in self.scene.items():
            if it is not self.base and it is not self.handles:
                it.setFlag(QGraphicsItem.ItemIsMovable, movable); it.setFlag(QGraphicsItem.ItemIsSelectable, movable)
        if not movable:
            self.scene.clearSelection()
        if hasattr(self, "handles"):
            self.handles.refresh()
        self.scene.update()

    def set_color(self, c):
        self.color = c
        for s in self.swatches:
            s.setChecked(s.color == c)
        self.restyle(color=c)

    def pick_color(self):
        c = QColorDialog.getColor(QColor(self.color), self, T("Chọn màu"))
        if c.isValid():
            self.set_color(c.name())

    def set_width(self, w, apply=True):
        self.stroke = w
        self.lbl_w.setText(f"{w} px")
        if apply:
            self.restyle(width=w)

    def set_fill(self, i, apply=True):
        self.fill = i
        for j, b in enumerate(self.fill_btns):
            b.setChecked(j == i)
            b.setIcon(theme.icon(b.property("ic"), "white" if j == i else "#334155"))
        if apply:
            self.restyle(fill=True)

    def fill_brush(self, color=None):
        c = QColor(color or self.color)
        if self.fill == 0:
            return QBrush(Qt.NoBrush)
        if self.fill == 1:
            c.setAlpha(70)
        return QBrush(c)

    def restyle(self, color=None, width=None, fill=False):
        """Apply the current style to selected items (undoable)."""
        sel = [i for i in self.scene.selectedItems() if i is not self.base]
        if not sel:
            return
        olds = [self._style_of(i) for i in sel]

        def new():
            for i in sel: self._set_style(i, color, width, fill)

        def old():
            for i, s in zip(sel, olds): self._restore(i, s)
        self.undo.push(StyleCmd(sel, new, old))

    def _style_of(self, i):
        if isinstance(i, QGraphicsTextItem):
            return (i.defaultTextColor(), i.font())
        if isinstance(i, StepItem):
            return (QColor(i.color), i.size)
        if hasattr(i, "pen"):
            return (QPen(i.pen()), QBrush(i.brush()) if hasattr(i, "brush") else None)
        return None

    def _restore(self, i, s):
        if s is None: return
        if isinstance(i, QGraphicsTextItem):
            i.setDefaultTextColor(s[0]); i.setFont(s[1])
        elif isinstance(i, StepItem):
            i.prepareGeometryChange(); i.color, i.size = s; i.update()
        else:
            i.prepareGeometryChange(); i.setPen(s[0])
            if s[1] is not None: i.setBrush(s[1])
            if isinstance(i, ArrowItem): i.rebuild()

    def _set_style(self, i, color, width, fill):
        if isinstance(i, QGraphicsTextItem):
            if color: i.setDefaultTextColor(QColor(color))
            if width: f = i.font(); f.setPixelSize(max(10, width * 5)); i.setFont(f)
        elif isinstance(i, StepItem):
            i.prepareGeometryChange()
            if color: i.color = QColor(color)
            if width: i.size = max(18, width * 6)
            i.update()
        elif isinstance(i, BlurItem):
            if width: i.block = max(4, width * 3); i.update()
        elif hasattr(i, "pen"):
            i.prepareGeometryChange()
            p = QPen(i.pen())
            hl = isinstance(i, HighlightItem)
            if color:
                p.setColor(QColor(color))
            if width:
                p.setWidthF(width * 4 if hl else width)
            i.setPen(p)
            if isinstance(i, (QGraphicsRectItem, QGraphicsEllipseItem)) and (fill or color):
                i.setBrush(self.fill_brush(p.color().name()))
            if isinstance(i, ArrowItem):
                i.rebuild()

    # ---- item helpers ----
    def add_text(self, pt):
        it = TextItem(self)
        f = QFont("Segoe UI", 1, QFont.DemiBold); f.setPixelSize(max(12, self.stroke * 5)); it.setFont(f)
        it.setDefaultTextColor(QColor(self.color))
        it.setPos(pt - QPointF(4, f.pixelSize() * 0.7))
        it.setFlags(FLAGS)
        self.undo.push(AddCmd(self.scene, [it]))
        self.last_item = it
        self.view.setFocus()                      # keyboard must go to the canvas, not a toolbar button
        it.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.scene.setFocusItem(it)
        it.setFocus()

    def drop_empty_text(self, it):
        if it.scene() is not None and not it.toPlainText().strip():
            self.scene.removeItem(it)

    def add_step(self, pt):
        it = StepItem(self.step_n, self.color, max(18, self.stroke * 6))
        it.setPos(pt); it.setFlags(FLAGS)
        self.step_n += 1
        self.last_item = it
        self.undo.push(AddCmd(self.scene, [it]))

    def delete_selected(self):
        if self.scene.focusItem() and isinstance(self.scene.focusItem(), QGraphicsTextItem) \
                and self.scene.focusItem().textInteractionFlags() & Qt.TextEditorInteraction:
            return
        sel = [i for i in self.scene.selectedItems() if i is not self.base]
        if sel:
            self.undo.push(RemoveCmd(self.scene, sel))

    def begin_move(self):
        self._moving = {i: i.pos() for i in self.scene.items() if i is not self.base and i is not self.handles}

    def end_move(self):
        if not self._moving:
            return
        mv = [(i, o, i.pos()) for i, o in self._moving.items() if i.pos() != o]
        self._moving = None
        if mv:
            self.undo.push(MoveCmd(mv))

    # ---- output ----
    def _copy_key(self):
        if self._editing_text():          # while typing, Ctrl+C copies the selected words
            sel = self.scene.focusItem().textCursor().selectedText()
            if sel:
                QGuiApplication.clipboard().setText(sel)
            return
        self.copy_clip(True)

    def _undo_key(self, redo):
        if self._editing_text():          # while typing, undo/redo the text itself
            doc = self.scene.focusItem().document()
            doc.redo() if redo else doc.undo()
            return
        self.undo.redo() if redo else self.undo.undo()

    def _editing_text(self):
        f = self.scene.focusItem()
        return isinstance(f, QGraphicsTextItem) and bool(f.textInteractionFlags() & Qt.TextEditorInteraction)

    def render(self):
        # never touch keyboard focus here (it used to kill a text box being typed); hide selection only meanwhile
        sel = self.scene.selectedItems()
        self.scene.blockSignals(True)
        for i in sel:
            i.setSelected(False)
        r = self.scene.sceneRect()
        img = QImage(int(r.width()), int(r.height()), QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        p = QPainter(img); p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        tool = self.tool; self.tool = ""          # hide blur dashed borders
        self.handles.setVisible(False)
        self.scene.render(p, QRectF(img.rect()), r)
        self.handles.setVisible(True)
        self.tool = tool
        p.end()
        for i in sel:
            i.setSelected(True)
        self.scene.blockSignals(False)
        return img

    def changed(self):
        self._copy_t.start()

    def copy_clip(self, explicit=False):
        if self._editing_text() and not explicit:
            return          # auto-copy waits until typing ends (the text box's focus-out calls changed())
        QGuiApplication.clipboard().setImage(self.render())
        self.lbl_state.setText("✔ " + T("Đã copy vào bộ nhớ tạm"))

    def _filename(self):
        os.makedirs(self.save_dir, exist_ok=True)
        return os.path.join(self.save_dir, datetime.datetime.now().strftime("Snip_%Y-%m-%d_%H-%M-%S.png"))

    def quick_save(self):
        path = self.saved_path or self._filename()
        self._write(path)

    def save_as(self):
        p, _ = QFileDialog.getSaveFileName(self, T("Lưu ảnh"), self.saved_path or self._filename(),
                                           "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp)")
        if p:
            self._write(p)

    def _write(self, path):
        img = self.render()
        if path.lower().endswith((".jpg", ".jpeg")):
            img = img.convertToFormat(QImage.Format_RGB32)
        if img.save(path, quality=95):
            self.saved_path = path
            self.lbl_state.setText("✔ " + T("Đã lưu: ") + path)
        else:
            self.lbl_state.setText("⚠ " + T("Không lưu được: ") + path)
