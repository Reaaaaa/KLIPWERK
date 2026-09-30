"""Tests for interactive crop moving, aspect-ratio locked scaling, and preset buttons."""
from __future__ import annotations

import pytest
from PyQt6.QtCore import QPoint, QPointF, QRect, Qt
from PyQt6.QtGui import QMouseEvent, QPixmap

from klipwerk.widgets.preview import PreviewWidget

pytest.importorskip("pytestqt")


@pytest.fixture
def preview(qtbot):
    p = PreviewWidget()
    p.resize(800, 600)
    # Simulate a 1920x1080 video frame loaded
    pix = QPixmap(1920, 1080)
    pix.fill(Qt.GlobalColor.black)
    p.set_frame(pix, 1920, 1080)
    qtbot.addWidget(p)
    return p


class TestCropHitTest:
    def test_hit_test_corners_and_inside(self, preview) -> None:
        # Set a crop rect in video coordinates: center 800x450
        preview.set_crop_from_video(560, 315, 800, 450)
        cr = preview.crop_rect
        assert cr is not None

        # Inside -> move
        inside_pt = cr.center()
        hit = preview._hit_test_crop(inside_pt)
        assert hit is not None
        assert hit[0] == "move"
        assert hit[1] == Qt.CursorShape.SizeAllCursor

        # Corners
        tl_hit = preview._hit_test_crop(cr.topLeft())
        assert tl_hit is not None and tl_hit[0] == "resize-tl"
        assert tl_hit[1] == Qt.CursorShape.SizeFDiagCursor

        br_hit = preview._hit_test_crop(cr.bottomRight())
        assert br_hit is not None and br_hit[0] == "resize-br"
        assert br_hit[1] == Qt.CursorShape.SizeFDiagCursor

        tr_hit = preview._hit_test_crop(cr.topRight())
        assert tr_hit is not None and tr_hit[0] == "resize-tr"
        assert tr_hit[1] == Qt.CursorShape.SizeBDiagCursor

        bl_hit = preview._hit_test_crop(cr.bottomLeft())
        assert bl_hit is not None and bl_hit[0] == "resize-bl"
        assert bl_hit[1] == Qt.CursorShape.SizeBDiagCursor

        # Outside -> None
        assert preview._hit_test_crop(QPoint(10, 10)) is None


class TestCropMove:
    def test_drag_inside_moves_crop_rect(self, preview) -> None:
        preview.set_crop_from_video(500, 300, 400, 400)
        cr_before = QRect(preview.crop_rect)

        emitted_crops = []
        preview.cropChanged.connect(lambda c: emitted_crops.append(c))

        start_pt = cr_before.center()
        # Mouse press inside
        press_ev = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(start_pt),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        preview.mousePressEvent(press_ev)
        assert preview._drag_mode == "move"

        # Drag by +30 px in x and +20 px in y
        target_pt = start_pt + QPoint(30, 20)
        move_ev = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(target_pt),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        preview.mouseMoveEvent(move_ev)
        cr_after = preview.crop_rect
        assert cr_after.topLeft() == cr_before.topLeft() + QPoint(30, 20)
        assert cr_after.size() == cr_before.size()
        assert len(emitted_crops) > 0

        # Mouse release
        release_ev = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(target_pt),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        preview.mouseReleaseEvent(release_ev)
        assert preview._drag_mode is None

    def test_drag_move_clamps_to_video_boundaries(self, preview) -> None:
        preview.set_crop_from_video(500, 300, 400, 400)
        img = preview._img_rect()

        # Drag way past the left and top edges
        start_pt = preview.crop_rect.center()
        press_ev = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(start_pt),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        preview.mousePressEvent(press_ev)

        drag_far_away = QPoint(-500, -500)
        move_ev = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(drag_far_away),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        preview.mouseMoveEvent(move_ev)

        # Top-left must be clamped to image rect top-left
        assert preview.crop_rect.left() == img.left()
        assert preview.crop_rect.top() == img.top()


class TestCropAspectPreservingScale:
    def test_corner_drag_maintains_9_16_ratio(self, preview) -> None:
        # Set 9:16 aspect ratio
        preview.set_aspect_ratio((9, 16))
        # Initial 9:16 crop: e.g. 180x320 in video coords
        preview.set_crop_from_video(800, 300, 360, 640)
        cr_before = QRect(preview.crop_rect)

        # Drag bottom-right corner to scale up
        start_pt = cr_before.bottomRight()
        press_ev = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(start_pt),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        preview.mousePressEvent(press_ev)
        assert preview._drag_mode == "resize-br"

        # Drag diagonally by +50 px
        target_pt = start_pt + QPoint(50, 50)
        move_ev = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(target_pt),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        preview.mouseMoveEvent(move_ev)

        cr_after = preview.crop_rect
        # Top-left must stay anchored
        assert cr_after.topLeft() == cr_before.topLeft()
        # Aspect ratio 9/16: w / h must match within 1 pixel rounding
        expected_ratio = 9 / 16
        actual_ratio = cr_after.width() / cr_after.height()
        assert actual_ratio == pytest.approx(expected_ratio, abs=0.03)

    def test_corner_drag_maintains_1_1_ratio(self, preview) -> None:
        preview.set_aspect_ratio((1, 1))
        preview.set_crop_from_video(800, 300, 400, 400)
        cr_before = QRect(preview.crop_rect)

        start_pt = cr_before.bottomRight()
        press_ev = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(start_pt),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        preview.mousePressEvent(press_ev)

        target_pt = start_pt + QPoint(60, 20)
        move_ev = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(target_pt),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        preview.mouseMoveEvent(move_ev)

        cr_after = preview.crop_rect
        # Width and height must be identical (1:1) within 1 px
        assert abs(cr_after.width() - cr_after.height()) <= 1


class TestPresetButtonsAndAppIntegration:
    @pytest.fixture
    def app_window(self, qtbot, tmp_path, monkeypatch):
        from klipwerk import app as app_mod
        ini_path = str(tmp_path / "test.ini")
        real_settings_cls = app_mod.Settings
        monkeypatch.setattr(app_mod, "Settings", lambda *a, **kw: real_settings_cls(ini_path))
        from klipwerk.app import Klipwerk
        w = Klipwerk()
        qtbot.addWidget(w)
        # Mock video dimensions
        w.vid_w = 1920
        w.vid_h = 1080
        w.video_path = "/dummy/video.mp4"
        yield w
        w.close()

    def test_clicking_preset_sets_aspect_ratio_and_checks_button(self, app_window) -> None:
        sb = app_window.sidebar
        preset_9_16 = [b for b in sb.preset_btns if b.text() == "9:16"][0]
        preset_16_9 = [b for b in sb.preset_btns if b.text() == "16:9"][0]

        # Click 9:16
        preset_9_16.click()
        assert preset_9_16.isChecked()
        assert not preset_16_9.isChecked()
        assert app_window.preview._aspect_ratio == (9, 16)
        assert app_window.crop_rect is not None
        # Video crop rect must be 9:16
        cr = app_window.crop_rect
        assert cr["w"] / cr["h"] == pytest.approx(9 / 16, abs=0.02)

        # Click 16:9
        preset_16_9.click()
        assert preset_16_9.isChecked()
        assert not preset_9_16.isChecked()
        assert app_window.preview._aspect_ratio == (16, 9)

    def test_clear_crop_unchecks_all_preset_buttons(self, app_window) -> None:
        sb = app_window.sidebar
        preset_1_1 = [b for b in sb.preset_btns if b.text() == "1:1"][0]
        preset_1_1.click()
        assert preset_1_1.isChecked()

        # Clear crop
        app_window._clear_crop()
        assert app_window.crop_rect is None
        assert app_window.preview.crop_rect is None
        assert app_window.preview._aspect_ratio is None
        assert not any(b.isChecked() for b in sb.preset_btns)
