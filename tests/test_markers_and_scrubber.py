"""Unit tests for timeline scrubber markers, drag & drop repositioning, and Clear In/Out button."""
from __future__ import annotations

import pytest
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QMessageBox

from klipwerk.widgets.scrubber import ScrubberWidget

pytest.importorskip("pytestqt")


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    from klipwerk import app as app_mod
    ini_path = str(tmp_path / "test.ini")

    real_settings_cls = app_mod.Settings
    monkeypatch.setattr(
        app_mod, "Settings",
        lambda: real_settings_cls(ini_path),
    )
    monkeypatch.setattr(
        QMessageBox, "warning",
        lambda *a, **kw: QMessageBox.StandardButton.Ok,
    )

    from klipwerk.app import Klipwerk
    w = Klipwerk()
    qtbot.addWidget(w)
    yield w
    w.close()


@pytest.fixture
def scrubber(qtbot):
    s = ScrubberWidget()
    s.resize(800, 48)
    qtbot.addWidget(s)
    return s


class TestScrubberMarkers:
    def test_initial_state(self, scrubber) -> None:
        assert not scrubber.isEnabled()
        assert not scrubber._has_in
        assert not scrubber._has_out
        assert scrubber._dragging_marker is None
        assert scrubber._hover_marker is None

    def test_set_and_clear_markers(self, scrubber) -> None:
        scrubber.set_markers(0.2, 0.8, has_in=True, has_out=True)
        assert scrubber._in == pytest.approx(0.2)
        assert scrubber._out == pytest.approx(0.8)
        assert scrubber._has_in is True
        assert scrubber._has_out is True

        scrubber.clear_markers()
        assert scrubber._in == pytest.approx(0.0)
        assert scrubber._out == pytest.approx(1.0)
        assert scrubber._has_in is False
        assert scrubber._has_out is False
        assert scrubber._dragging_marker is None
        assert scrubber._hover_marker is None

    def test_hit_test_marker(self, scrubber) -> None:
        scrubber.setEnabled(True)
        scrubber.set_video("/dummy/path.mp4", 100.0)
        scrubber.resize(800, 48)
        # Track pixel width = 800 - 16 = 784
        # In at 0.2 -> 8 + int(0.2 * 784) = 8 + 156 = 164
        # Out at 0.8 -> 8 + int(0.8 * 784) = 8 + 627 = 635
        # ty = 48 - 12 = 36
        scrubber.set_markers(0.2, 0.8, has_in=True, has_out=True)

        # Hit near In marker badge / needle
        assert scrubber._hit_test_marker(164, 30) == "in"
        assert scrubber._hit_test_marker(167, 24) == "in"

        # Hit near Out marker
        assert scrubber._hit_test_marker(635, 30) == "out"
        assert scrubber._hit_test_marker(632, 24) == "out"

        # Hit in between (no marker)
        assert scrubber._hit_test_marker(400, 30) is None

        # Hit above badge range (y < ty - 22, so y < 14)
        assert scrubber._hit_test_marker(164, 5) is None

    def test_drag_in_marker_and_clamping(self, scrubber, qtbot) -> None:
        scrubber.setEnabled(True)
        scrubber.set_video("/dummy/path.mp4", 100.0)
        scrubber.resize(800, 48)
        scrubber.set_markers(0.2, 0.8, has_in=True, has_out=True)

        m = scrubber._MARGIN
        track_px = scrubber.width() - m * 2
        in_x = m + int(0.2 * track_px)
        ty = scrubber.height() - 12

        moved_events: list[tuple[str, float]] = []
        finished_events: list[tuple[str, float]] = []
        scrubber.markerMoved.connect(lambda w, t: moved_events.append((w, t)))
        scrubber.markerDragFinished.connect(lambda w, t: finished_events.append((w, t)))

        # Press on In marker
        press_ev = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(in_x, ty),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        scrubber.mousePressEvent(press_ev)
        assert scrubber._dragging_marker == "in"

        # Drag to 0.4 position: x = m + int(0.4 * track_px)
        target_x = m + int(0.4 * track_px)
        move_ev = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(target_x, ty),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        scrubber.mouseMoveEvent(move_ev)
        assert scrubber._in == pytest.approx(0.4, abs=0.01)
        assert len(moved_events) > 0
        assert moved_events[-1][0] == "in"
        assert moved_events[-1][1] == pytest.approx(40.0, abs=1.0)

        # Drag past Out marker (try dragging to 0.95, while Out is 0.8)
        past_out_x = m + int(0.95 * track_px)
        move_past_ev = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(past_out_x, ty),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        scrubber.mouseMoveEvent(move_past_ev)
        # In marker must be clamped to Out marker (0.8)
        assert scrubber._in <= scrubber._out
        assert scrubber._in == pytest.approx(0.8, abs=0.01)

        # Release mouse
        rel_ev = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(target_x, ty),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        scrubber.mouseReleaseEvent(rel_ev)
        assert scrubber._dragging_marker is None
        assert len(finished_events) == 1
        assert finished_events[0][0] == "in"

    def test_drag_out_marker_and_clamping(self, scrubber) -> None:
        scrubber.setEnabled(True)
        scrubber.set_video("/dummy/path.mp4", 100.0)
        scrubber.resize(800, 48)
        scrubber.set_markers(0.3, 0.7, has_in=True, has_out=True)

        m = scrubber._MARGIN
        track_px = scrubber.width() - m * 2
        out_x = m + int(0.7 * track_px)
        ty = scrubber.height() - 12

        moved_events: list[tuple[str, float]] = []
        scrubber.markerMoved.connect(lambda w, t: moved_events.append((w, t)))

        # Press on Out marker
        press_ev = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(out_x, ty),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        scrubber.mousePressEvent(press_ev)
        assert scrubber._dragging_marker == "out"

        # Drag before In marker (try dragging to 0.1, while In is 0.3)
        before_in_x = m + int(0.1 * track_px)
        move_ev = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(before_in_x, ty),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        scrubber.mouseMoveEvent(move_ev)
        # Out marker must be clamped to In marker (0.3)
        assert scrubber._out >= scrubber._in
        assert scrubber._out == pytest.approx(0.3, abs=0.01)

        # Release mouse
        rel_ev = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(before_in_x, ty),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        scrubber.mouseReleaseEvent(rel_ev)
        assert scrubber._dragging_marker is None

    def test_hover_cursor_changes(self, scrubber) -> None:
        scrubber.setEnabled(True)
        scrubber.set_video("/dummy/path.mp4", 100.0)
        scrubber.resize(800, 48)
        scrubber.set_markers(0.2, 0.8, has_in=True, has_out=True)

        m = scrubber._MARGIN
        track_px = scrubber.width() - m * 2
        in_x = m + int(0.2 * track_px)
        ty = scrubber.height() - 12

        # Hover over In marker
        hover_marker_ev = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(in_x, ty),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        scrubber.mouseMoveEvent(hover_marker_ev)
        assert scrubber.cursor().shape() == Qt.CursorShape.SizeHorCursor

        # Hover away from markers
        hover_empty_ev = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(400, ty),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        scrubber.mouseMoveEvent(hover_empty_ev)
        assert scrubber.cursor().shape() == Qt.CursorShape.PointingHandCursor


class TestAppClearAndDragMarks:
    def test_btn_clear_marks_initial_state(self, window) -> None:
        assert hasattr(window, "btn_clear_marks")
        assert not window.btn_clear_marks.isEnabled()
        assert not window._has_mark_in
        assert not window._has_mark_out

    def test_setting_marks_enables_clear_btn(self, window) -> None:
        window.video_path = "/dummy/video.mp4"
        window.duration = 60.0
        window.current_t = 10.0

        window._set_mark("in")
        assert window._has_mark_in is True
        assert window.mark_in == 10.0
        assert window.btn_clear_marks.isEnabled()
        assert window.in_label.text() == "In: 00:00:10"

    def test_clear_marks_resets_everything(self, window) -> None:
        window.video_path = "/dummy/video.mp4"
        window.duration = 60.0
        window.current_t = 15.0
        window._set_mark("in")
        window.current_t = 45.0
        window._set_mark("out")

        assert window._has_mark_in is True
        assert window._has_mark_out is True
        assert window.btn_clear_marks.isEnabled()

        # Clear marks
        window._clear_marks()

        assert window._has_mark_in is False
        assert window._has_mark_out is False
        assert window.mark_in == 0.0
        assert window.mark_out == 60.0
        assert window.sidebar.mark_in_spin.value() == 0.0
        assert window.sidebar.mark_out_spin.value() == 60.0
        assert window.in_label.text() == "In: --:--:--"
        assert window.out_label.text() == "Out: --:--:--"
        assert not window.btn_clear_marks.isEnabled()

    def test_marker_dragged_updates_app_state(self, window, monkeypatch) -> None:
        window.video_path = "/dummy/video.mp4"
        window.duration = 100.0

        seeked_to: list[float] = []
        monkeypatch.setattr(window, "_seek_to", lambda t: seeked_to.append(t))

        # Drag In marker to 22.5s
        window._on_marker_dragged("in", 22.5)
        assert window.mark_in == 22.5
        assert window._has_mark_in is True
        assert window.sidebar.mark_in_spin.value() == 22.5
        assert window.btn_clear_marks.isEnabled()
        assert seeked_to == [22.5]

        # Drag Out marker to 75.0s
        window._on_marker_dragged("out", 75.0)
        assert window.mark_out == 75.0
        assert window._has_mark_out is True
        assert window.sidebar.mark_out_spin.value() == 75.0
        assert window.btn_clear_marks.isEnabled()
        assert seeked_to == [22.5, 75.0]

    def test_sidebar_mark_in_out_triggers_enable(self, window) -> None:
        window.video_path = "/dummy/video.mp4"
        window.duration = 80.0

        window._on_sidebar_mark_in(5.0)
        assert window._has_mark_in is True
        assert window.mark_in == 5.0
        assert window.btn_clear_marks.isEnabled()
