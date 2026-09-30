"""The timeline scrubber: waveform, playhead, in/out markers, hover thumbnail.

Design notes:

* The waveform is a numpy array of peaks (one per pixel column) produced
  by :class:`klipwerk.workers.waveform.WaveformWorker`. We colorize the
  played portion differently from the unplayed one without having to
  blit an image — each 1-pixel-wide rect is drawn in-place.
* The hover thumbnail machinery from the original script was half-
  implemented (fetch existed, paint never called). We either wire it up
  properly or remove it. Kept the API but disabled by default until the
  calling code explicitly opts in.
"""
from __future__ import annotations

import numpy as np
from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPolygon,
)
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..ui.theme import ACC, ACC2, ACC3, BORDER2, S2, TEXT


class ScrubberWidget(QWidget):
    """Custom timeline control with waveform and in/out markers."""

    seeked             = pyqtSignal(float)                # percent 0.0 – 1.0
    hoverTime          = pyqtSignal(float, int, int)      # (seconds, widget-x, global-y); -1 on leave
    markerMoved        = pyqtSignal(str, float)           # ("in" | "out", seconds)
    markerDragFinished = pyqtSignal(str, float)           # ("in" | "out", seconds)

    # Layout constants
    _MARGIN = 8        # horizontal padding inside the widget
    _TRACK_H = 30      # height of the seekbar track
    _HANDLE_R = 7      # playhead circle radius

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(58)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMouseTracking(True)

        self._pos: float = 0.0
        self._in: float = 0.0
        self._out: float = 1.0
        self._has_in: bool = False
        self._has_out: bool = False
        self._dragging_marker: str | None = None
        self._hover_marker: str | None = None
        self._waveform: np.ndarray | None = None
        self._hover_x: int = -1
        self._duration: float = 0.0
        self._video_path: str | None = None
        self.setEnabled(False)

    # ── Public API ──────────────────────────────────────────────────
    def set_video(self, path: str, duration: float) -> None:
        self._video_path = path
        self._duration = duration
        self._waveform = None
        self._has_in = False
        self._has_out = False
        self._dragging_marker = None
        self._hover_marker = None
        self.update()

    def clear_video(self) -> None:
        self._video_path = None
        self._duration = 0.0
        self._waveform = None
        self._pos = 0.0
        self._in = 0.0
        self._out = 1.0
        self._has_in = False
        self._has_out = False
        self._dragging_marker = None
        self._hover_marker = None
        self.setEnabled(False)
        self.update()

    def set_waveform(self, peaks: np.ndarray | None) -> None:
        self._waveform = peaks
        self.update()

    def set_position(self, pct: float) -> None:
        self._pos = max(0.0, min(1.0, pct))
        self.update()

    def set_markers(
        self,
        in_pct: float,
        out_pct: float,
        has_in: bool | None = None,
        has_out: bool | None = None,
    ) -> None:
        self._in = max(0.0, min(1.0, in_pct))
        self._out = max(0.0, min(1.0, out_pct))
        if has_in is not None:
            self._has_in = has_in
        else:
            self._has_in = self._in > 0.0001
        if has_out is not None:
            self._has_out = has_out
        else:
            self._has_out = self._out < 0.9999
        self.update()

    def clear_markers(self) -> None:
        self._in = 0.0
        self._out = 1.0
        self._has_in = False
        self._has_out = False
        self._dragging_marker = None
        self._hover_marker = None
        self.update()

    # ── Painting ────────────────────────────────────────────────────
    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            w = self.width()
            m = self._MARGIN
            track_px = max(1, w - m * 2)
            track_y = 20
            track_h = self._TRACK_H

            # 1. Base track capsule
            self._paint_track_bg(painter, m, track_px, track_y, track_h)

            if not self.isEnabled():
                return

            # 2. In/Out selection highlight on the track
            self._paint_in_out_zone(painter, m, track_px, track_y, track_h)

            # 3. Waveform rendered directly on/inside the track bar
            self._paint_waveform(painter, m, track_px, track_y, track_h)

            # 4. Played progress glow
            self._paint_played(painter, m, track_px, track_y, track_h)

            # 5. Marker badges & needles pointing down to the track
            self._paint_markers(painter, m, track_px, track_y, track_h)

            # 6. Playhead handle
            self._paint_playhead(painter, m, track_px, track_y, track_h)

            # 7. Hover guide line
            if self._hover_x >= 0 and self._dragging_marker is None:
                painter.setPen(QPen(QColor(TEXT + "66"), 1, Qt.PenStyle.DashLine))
                painter.drawLine(self._hover_x, track_y, self._hover_x, track_y + track_h)
        finally:
            painter.end()

    def _paint_waveform(self, painter: QPainter, m: int, track_px: int, ty: int, th: int) -> None:
        wf = self._waveform
        if wf is None or not self.isEnabled():
            return

        n = len(wf)
        if n == 0:
            return

        wf_h = max(2, th - 4)
        mid = ty + th // 2
        played_color = QColor(ACC)
        unplayed_color = QColor(BORDER2).lighter(145)

        painter.setPen(Qt.PenStyle.NoPen)
        for i in range(track_px):
            idx = int(i / track_px * n)
            peak = float(wf[min(idx, n - 1)])
            if peak <= 0.02:
                continue
            bar = max(1, int(peak * wf_h * 0.48))
            xi = m + i
            if i / track_px <= self._pos:
                painter.setBrush(QBrush(played_color))
            else:
                painter.setBrush(QBrush(unplayed_color))
            painter.drawRect(xi, mid - bar, 1, bar * 2)

    def _paint_track_bg(self, painter: QPainter, m: int, track_px: int,
                        ty: int, th: int) -> None:
        painter.setBrush(QBrush(QColor(S2)))
        painter.setPen(QPen(QColor(BORDER2), 1.5))
        painter.drawRoundedRect(m, ty, track_px, th, 4, 4)

    def _paint_in_out_zone(self, painter: QPainter, m: int, track_px: int,
                           ty: int, th: int) -> None:
        if (not self._has_in and not self._has_out) or self._out <= self._in:
            return
        ix = m + int(self._in * track_px)
        ox = m + int(self._out * track_px)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(200, 245, 58, 40)))
        painter.drawRoundedRect(ix, ty, ox - ix, th, 2, 2)

    def _paint_played(self, painter: QPainter, m: int, track_px: int,
                      ty: int, th: int) -> None:
        px = m + int(self._pos * track_px)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(200, 245, 58, 30)))
        painter.drawRoundedRect(m, ty, max(0, px - m), th, 4, 4)

    def _paint_markers(self, painter: QPainter, m: int, track_px: int,
                       ty: int, th: int) -> None:
        font = QFont()
        font.setPointSize(7)
        font.setBold(True)
        painter.setFont(font)

        # Draw In marker
        if self._has_in:
            ix = m + int(self._in * track_px)
            is_active = (self._hover_marker == "in" or self._dragging_marker == "in")
            color = QColor(ACC3)

            # Needle extending through the track
            painter.setPen(QPen(color, 2))
            painter.drawLine(ix, ty, ix, ty + th)

            # Badge polygon: pentagon pointing down
            poly = QPolygon([
                QPoint(ix - 8, ty - 18),
                QPoint(ix + 8, ty - 18),
                QPoint(ix + 8, ty - 5),
                QPoint(ix, ty),
                QPoint(ix - 8, ty - 5),
            ])
            painter.setBrush(QBrush(color))
            if is_active:
                painter.setPen(QPen(QColor("#ffffff"), 1.8))
            else:
                painter.setPen(QPen(QColor("#000000"), 1.0))
            painter.drawPolygon(poly)

            # Draw "I" letter
            painter.setPen(QPen(QColor("#0b0f19")))
            painter.drawText(QRect(ix - 8, ty - 18, 16, 13), Qt.AlignmentFlag.AlignCenter, "I")

        # Draw Out marker
        if self._has_out:
            ox = m + int(self._out * track_px)
            is_active = (self._hover_marker == "out" or self._dragging_marker == "out")
            color = QColor(ACC2)

            # Needle extending through the track
            painter.setPen(QPen(color, 2))
            painter.drawLine(ox, ty, ox, ty + th)

            # Badge polygon: pentagon pointing down
            poly = QPolygon([
                QPoint(ox - 8, ty - 18),
                QPoint(ox + 8, ty - 18),
                QPoint(ox + 8, ty - 5),
                QPoint(ox, ty),
                QPoint(ox - 8, ty - 5),
            ])
            painter.setBrush(QBrush(color))
            if is_active:
                painter.setPen(QPen(QColor("#ffffff"), 1.8))
            else:
                painter.setPen(QPen(QColor("#000000"), 1.0))
            painter.drawPolygon(poly)

            # Draw "O" letter
            painter.setPen(QPen(QColor("#0b0f19")))
            painter.drawText(QRect(ox - 8, ty - 18, 16, 13), Qt.AlignmentFlag.AlignCenter, "O")

    def _paint_playhead(self, painter: QPainter, m: int, track_px: int,
                        ty: int, th: int) -> None:
        px = m + int(self._pos * track_px)
        mid = ty + th // 2
        # Vertical needle line through the track
        painter.setPen(QPen(QColor(ACC), 2))
        painter.drawLine(px, ty, px, ty + th)
        # Playhead handle circle
        painter.setBrush(QBrush(QColor(ACC)))
        painter.setPen(QPen(QColor("#000000"), 1.2))
        painter.drawEllipse(QPoint(px, mid), self._HANDLE_R, self._HANDLE_R)

    # ── Input ──────────────────────────────────────────────────────
    def _pct(self, x: float) -> float:
        usable = max(1, self.width() - self._MARGIN * 2)
        return max(0.0, min(1.0, (x - self._MARGIN) / usable))

    def _hit_test_marker(self, x: int, y: int) -> str | None:
        if not self.isEnabled():
            return None
        m = self._MARGIN
        track_px = max(1, self.width() - m * 2)
        ty = 20
        th = self._TRACK_H

        if not (6 <= y <= ty + th + 6):
            return None

        candidates: list[tuple[str, int]] = []
        if self._has_in:
            ix = m + int(self._in * track_px)
            if abs(x - ix) <= 10:
                candidates.append(("in", abs(x - ix)))
        if self._has_out:
            ox = m + int(self._out * track_px)
            if abs(x - ox) <= 10:
                candidates.append(("out", abs(x - ox)))

        if not candidates:
            return None
        candidates.sort(key=lambda c: c[1])
        return candidates[0][0]

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self.isEnabled():
            return
        if event.button() == Qt.MouseButton.LeftButton:
            x = int(event.position().x())
            y = int(event.position().y())
            hit = self._hit_test_marker(x, y)
            if hit is not None:
                self._dragging_marker = hit
                self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
                self.update()
                return
            self.seeked.emit(self._pct(x))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self.isEnabled():
            return
        x = int(event.position().x())
        y = int(event.position().y())
        pct = self._pct(x)
        self._hover_x = x

        if self._dragging_marker is not None:
            if self._dragging_marker == "in":
                self._in = max(0.0, min(self._out, pct))
                self._has_in = True
                if self._duration > 0:
                    self.markerMoved.emit("in", self._in * self._duration)
            elif self._dragging_marker == "out":
                self._out = max(self._in, min(1.0, pct))
                self._has_out = True
                if self._duration > 0:
                    self.markerMoved.emit("out", self._out * self._duration)
            self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
            self.update()
        else:
            hit = self._hit_test_marker(x, y)
            if hit != self._hover_marker:
                self._hover_marker = hit
                self.update()

            if hit is not None:
                self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
            else:
                self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

            if event.buttons() & Qt.MouseButton.LeftButton:
                self.seeked.emit(pct)

        if self._duration:
            self.hoverTime.emit(
                pct * self._duration, x,
                int(event.globalPosition().y()),
            )

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if not self.isEnabled():
            return
        if event.button() == Qt.MouseButton.LeftButton and self._dragging_marker is not None:
            which = self._dragging_marker
            self._dragging_marker = None
            val_sec = (self._in if which == "in" else self._out) * self._duration
            self.markerDragFinished.emit(which, val_sec)

            x = int(event.position().x())
            y = int(event.position().y())
            hit = self._hit_test_marker(x, y)
            self._hover_marker = hit
            if hit is not None:
                self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
            else:
                self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.update()

    def leaveEvent(self, _event) -> None:
        self._hover_x = -1
        if self._dragging_marker is None:
            self._hover_marker = None
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.update()
        self.hoverTime.emit(-1.0, -1, -1)
