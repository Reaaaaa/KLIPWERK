"""The big video preview pane with interactive crop selection."""
from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QResizeEvent,
    QWheelEvent,
)
from PyQt6.QtWidgets import QLabel, QSizePolicy

from ..core.models import CropRect
from ..ui.theme import ACC, BG, BORDER, MUTED


class PreviewWidget(QLabel):
    """Displays video frames and hosts the crop-drag interaction.

    The widget keeps an internal ``_pixmap_base`` (the raw decoded
    frame) and re-composites it on every paint — drawing the frame,
    then darkening everything outside the crop rect, then the crop
    border with a rule-of-thirds overlay and draggable resize handles.
    """

    cropChanged   = pyqtSignal(dict)  # emits {x, y, w, h} in video pixels
    wheelScrolled = pyqtSignal(int)  # emits step count (neg = back, pos = forward)

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(400, 250)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(
            f"background:{BG}; border:1px solid {BORDER}; "
            f"color:{MUTED}; font-size:13px;"
        )
        self.setText("Drop a video here\nor click  Open File")

        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMouseTracking(True)

        # Crop state
        self.crop_mode: bool = False
        self.crop_rect: QRect | None = None   # widget coordinates
        self._aspect_ratio: tuple[int, int] | None = None
        self._drag_mode: str | None = None
        self._drag_start: QPoint | None = None
        self._orig_crop: QRect | None = None
        self._scale: float = 1.0
        self._offset: QPoint = QPoint(0, 0)      # top-left of image in widget
        self._vid_w: int = 0
        self._vid_h: int = 0
        self._pixmap_base: QPixmap | None = None

    # ── Frame update ────────────────────────────────────────────────
    def set_frame(self, pixmap: QPixmap, vid_w: int, vid_h: int) -> None:
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self._pixmap_base = pixmap
        self._vid_w = vid_w
        self._vid_h = vid_h
        self._recalc_scale()
        self._repaint_frame()

    def reset(self) -> None:
        """Clear the preview and return to the drop-a-video placeholder."""
        self._pixmap_base = None
        self._vid_w = self._vid_h = 0
        self.crop_rect = None
        self._aspect_ratio = None
        self._drag_mode = None
        self._drag_start = None
        self._orig_crop = None
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.clear()
        self.setText("Drop a video here\nor click  Open File")

    def _recalc_scale(self) -> None:
        if not self._vid_w or not self._vid_h:
            return
        ww, wh = self.width(), self.height()
        if ww <= 0 or wh <= 0:
            return
        self._scale = min(ww / self._vid_w, wh / self._vid_h)
        dw = int(self._vid_w * self._scale)
        dh = int(self._vid_h * self._scale)
        self._offset = QPoint((ww - dw) // 2, (wh - dh) // 2)

    def _img_rect(self) -> QRect:
        dw = int(self._vid_w * self._scale)
        dh = int(self._vid_h * self._scale)
        return QRect(self._offset, QSize(dw, dh))

    def _repaint_frame(self) -> None:
        if self._pixmap_base is None:
            return
        dw = int(self._vid_w * self._scale)
        dh = int(self._vid_h * self._scale)

        scaled = self._pixmap_base.scaled(
            dw, dh,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        canvas = QPixmap(self.width(), self.height())
        canvas.fill(QColor(BG))
        painter = QPainter(canvas)
        try:
            painter.drawPixmap(self._offset, scaled)

            if self.crop_rect and self.crop_rect.width() > 2:
                self._paint_crop_overlay(painter, dw, dh)
        finally:
            painter.end()

        self.setPixmap(canvas)

    def _paint_crop_overlay(self, painter: QPainter, dw: int, dh: int) -> None:
        cr = self.crop_rect
        assert cr is not None
        img_rect = QRect(self._offset, QSize(dw, dh))

        # Darken everything outside the crop — four rects around it.
        painter.setBrush(QBrush(QColor(0, 0, 0, 120)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(QRect(
            img_rect.left(), img_rect.top(),
            img_rect.width(), cr.top() - img_rect.top(),
        ))
        painter.drawRect(QRect(
            img_rect.left(), cr.bottom(),
            img_rect.width(), img_rect.bottom() - cr.bottom(),
        ))
        painter.drawRect(QRect(
            img_rect.left(), cr.top(),
            cr.left() - img_rect.left(), cr.height(),
        ))
        painter.drawRect(QRect(
            cr.right(), cr.top(),
            img_rect.right() - cr.right(), cr.height(),
        ))

        # Crop border
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(ACC), 1.5))
        painter.drawRect(cr)

        # Rule-of-thirds guides
        painter.setPen(QPen(QColor(ACC).darker(150), 0.5, Qt.PenStyle.DashLine))
        for i in (1, 2):
            painter.drawLine(
                cr.left() + cr.width() * i // 3, cr.top(),
                cr.left() + cr.width() * i // 3, cr.bottom(),
            )
            painter.drawLine(
                cr.left(), cr.top() + cr.height() * i // 3,
                cr.right(), cr.top() + cr.height() * i // 3,
            )

        # Resize handles (8 handles: 4 corners + 4 edge midpoints)
        hs = 8
        painter.setBrush(QBrush(QColor(ACC)))
        painter.setPen(QPen(QColor("#000000"), 1.2))
        corners = (cr.topLeft(), cr.topRight(), cr.bottomLeft(), cr.bottomRight())
        for pt in corners:
            painter.drawRect(QRect(pt.x() - hs // 2, pt.y() - hs // 2, hs, hs))

        mid_pts = (
            QPoint(cr.center().x(), cr.top()),
            QPoint(cr.center().x(), cr.bottom()),
            QPoint(cr.left(), cr.center().y()),
            QPoint(cr.right(), cr.center().y()),
        )
        for pt in mid_pts:
            painter.drawRect(QRect(pt.x() - hs // 2, pt.y() - hs // 2, hs, hs))

    # ── Crop interaction ────────────────────────────────────────────
    def set_crop_mode(self, enabled: bool) -> None:
        self.crop_mode = enabled
        if not enabled:
            self._drag_mode = None
        self._update_cursor()

    def set_aspect_ratio(self, aspect: tuple[int, int] | None) -> None:
        self._aspect_ratio = aspect

    def clear_crop(self) -> None:
        self.crop_rect = None
        self._aspect_ratio = None
        self._drag_mode = None
        self._drag_start = None
        self._orig_crop = None
        self._update_cursor()
        self._repaint_frame()

    def set_crop_from_video(self, x: int, y: int, w: int, h: int) -> None:
        """Set the crop rect from video-pixel coordinates."""
        s = self._scale
        ox, oy = self._offset.x(), self._offset.y()
        self.crop_rect = QRect(
            int(ox + x * s), int(oy + y * s),
            int(w * s), int(h * s),
        )
        self._repaint_frame()

    def _widget_to_video(self, point: QPoint) -> tuple[int, int]:
        s = self._scale
        if s == 0:
            return (0, 0)
        ox, oy = self._offset.x(), self._offset.y()
        return (int((point.x() - ox) / s), int((point.y() - oy) / s))

    def _hit_test_crop(self, pt: QPoint) -> tuple[str, Qt.CursorShape] | None:
        cr = self.crop_rect
        if not cr or cr.width() < 4 or cr.height() < 4:
            return None

        hs = 10  # hit size for corner handles
        em = 6   # hit margin for edges

        # Corners
        if abs(pt.x() - cr.left()) <= hs and abs(pt.y() - cr.top()) <= hs:
            return ("resize-tl", Qt.CursorShape.SizeFDiagCursor)
        if abs(pt.x() - cr.right()) <= hs and abs(pt.y() - cr.top()) <= hs:
            return ("resize-tr", Qt.CursorShape.SizeBDiagCursor)
        if abs(pt.x() - cr.left()) <= hs and abs(pt.y() - cr.bottom()) <= hs:
            return ("resize-bl", Qt.CursorShape.SizeBDiagCursor)
        if abs(pt.x() - cr.right()) <= hs and abs(pt.y() - cr.bottom()) <= hs:
            return ("resize-br", Qt.CursorShape.SizeFDiagCursor)

        # Edges
        if abs(pt.y() - cr.top()) <= em and cr.left() <= pt.x() <= cr.right():
            return ("resize-t", Qt.CursorShape.SizeVerCursor)
        if abs(pt.y() - cr.bottom()) <= em and cr.left() <= pt.x() <= cr.right():
            return ("resize-b", Qt.CursorShape.SizeVerCursor)
        if abs(pt.x() - cr.left()) <= em and cr.top() <= pt.y() <= cr.bottom():
            return ("resize-l", Qt.CursorShape.SizeHorCursor)
        if abs(pt.x() - cr.right()) <= em and cr.top() <= pt.y() <= cr.bottom():
            return ("resize-r", Qt.CursorShape.SizeHorCursor)

        # Inside crop rect -> move
        if cr.contains(pt):
            return ("move", Qt.CursorShape.SizeAllCursor)

        return None

    def _update_cursor(self, pt: QPoint | None = None) -> None:
        if pt is not None and self.crop_rect and self.crop_rect.width() > 4:
            hit = self._hit_test_crop(pt)
            if hit is not None:
                self.setCursor(QCursor(hit[1]))
                return
        if self.crop_mode:
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        pt = event.position().toPoint()
        if self.crop_rect and self.crop_rect.width() > 4:
            hit = self._hit_test_crop(pt)
            if hit is not None:
                self._drag_mode = hit[0]
                self._drag_start = pt
                self._orig_crop = QRect(self.crop_rect)
                self.setCursor(QCursor(hit[1]))
                return

        if self.crop_mode:
            self._drag_mode = "create"
            self._drag_start = pt
            self.crop_rect = None
            self._aspect_ratio = None
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pt = event.position().toPoint()

        if self._drag_mode is None:
            self._update_cursor(pt)
            return

        img = self._img_rect()
        cur = pt
        min_sz = 16

        if self._drag_mode == "create":
            x = min(self._drag_start.x(), cur.x())
            y = min(self._drag_start.y(), cur.y())
            w = abs(cur.x() - self._drag_start.x())
            h = abs(cur.y() - self._drag_start.y())

            x = max(img.left(), min(x, img.right()))
            y = max(img.top(),  min(y, img.bottom()))
            w = min(w, img.right()  - x)
            h = min(h, img.bottom() - y)
            self.crop_rect = QRect(x, y, w, h)
            self._repaint_frame()
            return

        if self._drag_mode == "move" and self._orig_crop:
            dx = cur.x() - self._drag_start.x()
            dy = cur.y() - self._drag_start.y()
            orig = self._orig_crop
            max_x = max(img.left(), img.right() - orig.width())
            max_y = max(img.top(), img.bottom() - orig.height())
            new_x = max(img.left(), min(orig.left() + dx, max_x))
            new_y = max(img.top(), min(orig.top() + dy, max_y))
            self.crop_rect = QRect(new_x, new_y, orig.width(), orig.height())
            self._repaint_frame()
            self._emit_crop()
            return

        if self._drag_mode.startswith("resize-") and self._orig_crop:
            mode = self._drag_mode
            orig = self._orig_crop

            if self._aspect_ratio is not None:
                wr, hr = self._aspect_ratio
                R = wr / hr

                if mode == "resize-br":
                    tl = orig.topLeft()
                    max_w = max(min_sz, img.right() - tl.x())
                    max_h = max(min_sz, img.bottom() - tl.y())
                    w = max(min_sz, cur.x() - tl.x())
                    h = int(w / R)
                    if h > max_h:
                        h = max_h
                        w = int(h * R)
                    if w > max_w:
                        w = max_w
                        h = int(w / R)
                    self.crop_rect = QRect(tl.x(), tl.y(), max(min_sz, w), max(min_sz, h))

                elif mode == "resize-tl":
                    br = orig.bottomRight()
                    max_w = max(min_sz, br.x() - img.left())
                    max_h = max(min_sz, br.y() - img.top())
                    w = max(min_sz, br.x() - cur.x())
                    h = int(w / R)
                    if h > max_h:
                        h = max_h
                        w = int(h * R)
                    if w > max_w:
                        w = max_w
                        h = int(w / R)
                    self.crop_rect = QRect(br.x() - w, br.y() - h, max(min_sz, w), max(min_sz, h))

                elif mode == "resize-tr":
                    bl = QPoint(orig.left(), orig.bottom())
                    max_w = max(min_sz, img.right() - bl.x())
                    max_h = max(min_sz, bl.y() - img.top())
                    w = max(min_sz, cur.x() - bl.x())
                    h = int(w / R)
                    if h > max_h:
                        h = max_h
                        w = int(h * R)
                    if w > max_w:
                        w = max_w
                        h = int(w / R)
                    self.crop_rect = QRect(bl.x(), bl.y() - h, max(min_sz, w), max(min_sz, h))

                elif mode == "resize-bl":
                    tr = QPoint(orig.right(), orig.top())
                    max_w = max(min_sz, tr.x() - img.left())
                    max_h = max(min_sz, img.bottom() - tr.y())
                    w = max(min_sz, tr.x() - cur.x())
                    h = int(w / R)
                    if h > max_h:
                        h = max_h
                        w = int(h * R)
                    if w > max_w:
                        w = max_w
                        h = int(w / R)
                    self.crop_rect = QRect(tr.x() - w, tr.y(), max(min_sz, w), max(min_sz, h))

                elif mode in ("resize-r", "resize-l"):
                    if mode == "resize-r":
                        w = max(min_sz, min(cur.x() - orig.left(), img.right() - orig.left()))
                    else:
                        w = max(min_sz, min(orig.right() - cur.x(), orig.right() - img.left()))
                    h = int(w / R)
                    cy = orig.center().y()
                    y = cy - h // 2
                    if y < img.top():
                        y = img.top()
                    if y + h > img.bottom():
                        y = img.bottom() - h
                    if h > img.height():
                        h = img.height()
                        w = int(h * R)
                        y = img.top()
                    x = orig.left() if mode == "resize-r" else orig.right() - w
                    self.crop_rect = QRect(x, max(img.top(), y), max(min_sz, w), max(min_sz, h))

                elif mode in ("resize-b", "resize-t"):
                    if mode == "resize-b":
                        h = max(min_sz, min(cur.y() - orig.top(), img.bottom() - orig.top()))
                    else:
                        h = max(min_sz, min(orig.bottom() - cur.y(), orig.bottom() - img.top()))
                    w = int(h * R)
                    cx = orig.center().x()
                    x = cx - w // 2
                    if x < img.left():
                        x = img.left()
                    if x + w > img.right():
                        x = img.right() - w
                    if w > img.width():
                        w = img.width()
                        h = int(w / R)
                        x = img.left()
                    y = orig.top() if mode == "resize-b" else orig.bottom() - h
                    self.crop_rect = QRect(max(img.left(), x), y, max(min_sz, w), max(min_sz, h))

            else:
                # Freehand resize
                cur_l, cur_t = orig.left(), orig.top()
                cur_r, cur_b = orig.right(), orig.bottom()
                if "r" in mode:
                    cur_r = min(img.right(), max(cur_l + min_sz, cur.x()))
                elif "l" in mode:
                    cur_l = max(img.left(), min(cur_r - min_sz, cur.x()))
                if "b" in mode:
                    cur_b = min(img.bottom(), max(cur_t + min_sz, cur.y()))
                elif "t" in mode:
                    cur_t = max(img.top(), min(cur_b - min_sz, cur.y()))
                self.crop_rect = QRect(cur_l, cur_t, cur_r - cur_l, cur_b - cur_t)

            self._repaint_frame()
            self._emit_crop()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag_mode is None:
            return

        was_create = (self._drag_mode == "create")
        self._drag_mode = None
        self._drag_start = None
        self._orig_crop = None
        self._emit_crop()
        if was_create:
            self.set_crop_mode(False)
        self._update_cursor(event.position().toPoint())

    def leaveEvent(self, _event) -> None:
        if self._drag_mode is None:
            self._update_cursor()

    def _emit_crop(self) -> None:
        cr = self.crop_rect
        if not cr or cr.width() < 4 or cr.height() < 4:
            return
        vx, vy = self._widget_to_video(cr.topLeft())
        vx2, vy2 = self._widget_to_video(cr.bottomRight())
        # ffmpeg encoders need even dimensions
        vw = (vx2 - vx) & ~1
        vh = (vy2 - vy) & ~1
        vw = max(2, min(vw, self._vid_w - vx))
        vh = max(2, min(vh, self._vid_h - vy))
        crop: CropRect = {"x": vx, "y": vy, "w": vw, "h": vh}
        self.cropChanged.emit(crop)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Scroll wheel steps through frames; Shift+wheel = 10 frames."""
        if self._pixmap_base is None:
            super().wheelEvent(event)
            return
        delta = event.angleDelta().y()
        if delta == 0:
            super().wheelEvent(event)
            return
        steps = 10 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
        # scroll up (delta > 0) → step backward; scroll down → step forward
        self.wheelScrolled.emit(-steps if delta > 0 else steps)
        event.accept()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._recalc_scale()
        self._repaint_frame()
