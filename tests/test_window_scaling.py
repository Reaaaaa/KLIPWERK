"""Tests for frameless window scaling, edge resize detection, and title bar icons."""
from __future__ import annotations

import pytest
from PyQt6.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from PyQt6.QtGui import QEnterEvent, QMouseEvent
from PyQt6.QtWidgets import QApplication

from klipwerk.ui.icons import SVG_MAXIMIZE, SVG_RESTORE

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

    from klipwerk.app import Klipwerk
    w = Klipwerk()
    qtbot.addWidget(w)
    return w


class TestMaximizeRestoreIcon:
    def test_initial_state_windowed(self, window) -> None:
        """When windowed, the button must show the maximize/fullscreen icon."""
        assert not window.isMaximized()
        assert window._btn_max._icon_svg == SVG_MAXIMIZE
        assert window._btn_max.toolTip() == "Maximize"

    def test_toggle_maximize_updates_icon_and_tooltip(self, window) -> None:
        """Toggling maximize flips between maximize and restore icons/tooltips."""
        # 1. Maximize
        window._toggle_maximize()
        assert window._btn_max._icon_svg == SVG_RESTORE
        assert window._btn_max.toolTip() == "Restore"

        # 2. Restore
        window._toggle_maximize()
        assert window._btn_max._icon_svg == SVG_MAXIMIZE
        assert window._btn_max.toolTip() == "Maximize"

    def test_hover_leave_preserves_current_state_icon(self, window) -> None:
        """Hovering and leaving must not revert the icon to the initial SVG."""
        # Maximize
        window._toggle_maximize()
        assert window._btn_max._icon_svg == SVG_RESTORE

        # Simulate mouse enter
        enter_ev = QEnterEvent(QPointF(5, 5), QPointF(5, 5), QPointF(5, 5))
        window._btn_max.enterEvent(enter_ev)
        assert window._btn_max._icon_svg == SVG_RESTORE

        # Simulate mouse leave
        leave_ev = QEvent(QEvent.Type.Leave)
        window._btn_max.leaveEvent(leave_ev)
        assert window._btn_max._icon_svg == SVG_RESTORE

    def test_window_state_change_event_syncs_icon(self, window) -> None:
        """Emulated WindowStateChange event triggers _update_max_button."""
        window._update_max_button(True)
        assert window._btn_max._icon_svg == SVG_RESTORE
        assert window._btn_max.toolTip() == "Restore"

        window._update_max_button(False)
        assert window._btn_max._icon_svg == SVG_MAXIMIZE
        assert window._btn_max.toolTip() == "Maximize"


class TestResizeDirections:
    def test_all_eight_directions_detected(self, window) -> None:
        """Check edge and corner directions on normal window."""
        window.resize(1000, 640)
        w, h = 1000, 640

        # Corners
        assert window._get_resize_dir(QPoint(2, 2)) == "top-left"
        assert window._get_resize_dir(QPoint(w - 2, 2)) == "top-right"
        assert window._get_resize_dir(QPoint(2, h - 2)) == "bottom-left"
        assert window._get_resize_dir(QPoint(w - 2, h - 2)) == "bottom-right"

        # Edges
        assert window._get_resize_dir(QPoint(w // 2, 2)) == "top"
        assert window._get_resize_dir(QPoint(w // 2, h - 2)) == "bottom"
        assert window._get_resize_dir(QPoint(2, h // 2)) == "left"
        assert window._get_resize_dir(QPoint(w - 2, h // 2)) == "right"

        # Center (no resize)
        assert window._get_resize_dir(QPoint(w // 2, h // 2)) is None

    def test_window_buttons_do_not_trigger_resize(self, window, qtbot) -> None:
        """Hovering over title bar buttons (min, max, close) must not trigger resize."""
        window.show()
        qtbot.waitExposed(window)
        btn_pos = window._btn_close.mapTo(window, QPoint(10, 10))
        assert window._get_resize_dir(btn_pos) is None

    def test_no_resize_when_maximized(self, window) -> None:
        """When maximized, all positions return None."""
        window._toggle_maximize()
        assert window._get_resize_dir(QPoint(2, 2)) is None
        assert window._get_resize_dir(QPoint(window.width() - 2, window.height() - 2)) is None


class TestResizeExecution:
    def test_bottom_resize_extends_height(self, window) -> None:
        window.setGeometry(100, 100, 1000, 640)
        window._resize_dir = "bottom"
        window._resize_start_geo = QRect(100, 100, 1000, 640)
        window._resize_start_pos = QPoint(500, 740)

        # Drag down by 40px
        window._do_resize(QPoint(500, 780))
        assert window.height() == 680
        assert window.width() == 1000
        assert window.geometry().topLeft() == QPoint(100, 100)

    def test_bottom_right_resize_extends_both(self, window) -> None:
        window.setGeometry(100, 100, 1000, 640)
        window._resize_dir = "bottom-right"
        window._resize_start_geo = QRect(100, 100, 1000, 640)
        window._resize_start_pos = QPoint(1100, 740)

        # Drag down and right by (50, 60)
        window._do_resize(QPoint(1150, 800))
        assert window.width() == 1050
        assert window.height() == 700
        assert window.geometry().topLeft() == QPoint(100, 100)

    def test_left_resize_anchors_right_edge(self, window) -> None:
        window.setGeometry(100, 100, 1200, 700)
        window._resize_dir = "left"
        window._resize_start_geo = QRect(100, 100, 1200, 700)
        window._resize_start_pos = QPoint(100, 400)

        # Drag left edge to the right by 50px (shrinking window width from 1200 to 1150)
        window._do_resize(QPoint(150, 400))
        assert window.geometry().left() == 150
        assert window.geometry().width() == 1150
        # Right edge must stay at 100 + 1200 = 1300
        assert window.geometry().left() + window.geometry().width() == 1300

        # Drag beyond min width (min_w is 1000)
        window._do_resize(QPoint(400, 400))
        assert window.geometry().width() == window.minimumWidth()
        assert window.geometry().left() == 1300 - window.minimumWidth()

    def test_top_resize_anchors_bottom_edge(self, window) -> None:
        window.setGeometry(100, 100, 1000, 750)
        window._resize_dir = "top"
        window._resize_start_geo = QRect(100, 100, 1000, 750)
        window._resize_start_pos = QPoint(500, 100)

        # Drag top edge down by 50px (shrinking window height from 750 to 700)
        window._do_resize(QPoint(500, 150))
        assert window.geometry().top() == 150
        assert window.geometry().height() == 700
        # Bottom edge must stay at 100 + 750 = 850
        assert window.geometry().top() + window.geometry().height() == 850

        # Drag beyond min height (min_h is 640)
        window._do_resize(QPoint(500, 300))
        assert window.geometry().height() == window.minimumHeight()
        assert window.geometry().top() == 850 - window.minimumHeight()


class TestEventFilterInterception:
    def test_click_on_bottom_edge_starts_resizing(self, window) -> None:
        """Even if child widget (like timeline) is under cursor, click at bottom edge starts resizing."""
        window.setGeometry(100, 100, 1000, 640)
        local_pt = QPoint(500, 638)
        global_pt = window.mapToGlobal(local_pt)
        target = QApplication.widgetAt(global_pt) or window

        press_ev = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(local_pt),
            QPointF(global_pt),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        handled = QApplication.sendEvent(target, press_ev)
        assert handled is True
        assert window._resizing is True
        assert window._resize_dir == "bottom"

        # Release ends resizing
        release_ev = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(local_pt),
            QPointF(global_pt),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(target, release_ev)
        assert window._resizing is False
        assert window._resize_dir is None
