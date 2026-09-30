"""Smoke tests for the main window.

These aren't trying to verify pixel output — they just ensure the
``Klipwerk`` window can be constructed, common actions don't crash,
and teardown is clean. Think "does the thing turn on?".

Uses pytest-qt's ``qtbot`` fixture which manages ``QApplication``
lifecycle properly, avoiding the teardown segfaults we saw with
hand-rolled application fixtures.

Dialogs are mocked throughout — ``QFileDialog``, ``QMessageBox``, and
``QProgressDialog`` all block the event loop modally, so we replace
them with stubs that return immediately.
"""
from __future__ import annotations

from typing import Any

import pytest
from PyQt6.QtWidgets import QMessageBox

pytest.importorskip("pytestqt")


@pytest.fixture(autouse=True)
def _stub_ffmpeg(monkeypatch):
    """Make the ffmpeg binary lookup succeed without actually having ffmpeg.

    Klipwerk doesn't call ffmpeg during construction, but some code
    paths under test (export button clicks) resolve the binary. Faking
    it lets the tests run on CI boxes without the binary installed.
    """
    from klipwerk.core import ffmpeg_runner
    monkeypatch.setattr(ffmpeg_runner, "_FFMPEG", "/usr/bin/ffmpeg")
    monkeypatch.setattr(ffmpeg_runner, "_FFPROBE", "/usr/bin/ffprobe")


@pytest.fixture(autouse=True)
def _stub_modal_dialogs(monkeypatch):
    """Neutralize modal dialogs so tests don't block forever.

    Every dialog is replaced with a no-op or Cancel-equivalent. Tests
    that need to observe dialog invocations should override these on a
    case-by-case basis.
    """
    # QMessageBox.warning/critical/information all return StandardButton.Ok
    monkeypatch.setattr(
        QMessageBox, "warning",
        lambda *a, **kw: QMessageBox.StandardButton.Ok,
    )
    monkeypatch.setattr(
        QMessageBox, "critical",
        lambda *a, **kw: QMessageBox.StandardButton.Ok,
    )
    monkeypatch.setattr(
        QMessageBox, "information",
        lambda *a, **kw: QMessageBox.StandardButton.Ok,
    )
    monkeypatch.setattr(
        QMessageBox, "question",
        lambda *a, **kw: QMessageBox.StandardButton.No,
    )


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    """Fresh Klipwerk main window, registered with qtbot for clean teardown.

    Redirects the settings file to ``tmp_path`` so tests don't clobber
    the user's real config.
    """
    # Point QSettings at a throwaway ini so restored geometry / K-mode
    # from the host machine can't interfere with test expectations.
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
    yield w
    w.close()


# ── Construction ───────────────────────────────────────────────────────
class TestConstruction:
    def test_window_constructs(self, window) -> None:
        """The bare minimum: __init__ doesn't throw."""
        assert window.windowTitle() == "Klipwerk"
        assert window.video_path is None
        assert window.clips == []

    def test_sidebar_refs_populated(self, window) -> None:
        """Regression: every sidebar attribute the app uses must exist."""
        sb = window.sidebar
        # These are the ones we rely on across the app
        assert sb.export_fmt is not None
        assert sb.export_crf is not None
        assert sb.export_preset is not None
        assert sb.codec_note is not None
        assert sb.mark_in_spin is not None
        assert sb.btn_ex_clip is not None
        # Resizable three-section splitter
        assert sb.sections_splitter is not None
        assert sb.sections_splitter.count() == 3
        assert sb.btn_ex_seq is not None

    def test_show_then_close_no_crash(self, window, qtbot) -> None:
        window.show()
        qtbot.waitExposed(window)
        assert window.isVisible()
        window.close()
        assert not window.isVisible()


# ── Keyboard shortcuts (no-op paths) ───────────────────────────────────
class TestShortcuts:
    def test_undo_with_empty_history_is_noop(self, window, qtbot) -> None:
        """Ctrl+Z on a virgin window must not crash or raise."""
        assert window.history.undo_depth == 0
        # Call the undo method directly — simulating the QShortcut firing.
        # Going through keyPressEvent would require window focus which is
        # flaky under offscreen Qt.
        window._undo()
        # No exception == pass. State should be unchanged.
        assert window.clips == []
        assert window.history.undo_depth == 0

    def test_redo_with_empty_stack_is_noop(self, window) -> None:
        window._redo()
        assert window.history.redo_depth == 0


# ── Format combo → codec note (double-definition regression) ───────────
class TestCodecNote:
    def test_changing_format_updates_codec_note(self, window) -> None:
        """Regression: the old duplicate _update_codec_note had only 3
        entries and would IndexError on H.265+. We loop through the
        whole FORMATS table to make sure no index is unreachable."""
        from klipwerk.core.formats import FORMATS
        combo = window.sidebar.export_fmt
        for idx in range(len(FORMATS)):
            combo.setCurrentIndex(idx)
            # Note text is the human-readable label from the spec
            assert window.sidebar.codec_note.text() == FORMATS[idx].note

    def test_format_change_repopulates_presets(self, window) -> None:
        """When the user picks AV1, the preset dropdown should update
        with AV1's numeric preset options, not H.264's 'fast/slow' ones."""
        from klipwerk.core.formats import FORMATS
        combo = window.sidebar.export_fmt

        # Pick the first AV1 format
        av1_idx = next(i for i, f in enumerate(FORMATS) if f.encoder == "libaom-av1")
        combo.setCurrentIndex(av1_idx)

        preset_combo = window.sidebar.export_preset
        presets_in_ui = [
            preset_combo.itemText(i) for i in range(preset_combo.count())
        ]
        assert presets_in_ui == list(FORMATS[av1_idx].presets)


# ── Export refuses invalid states ──────────────────────────────────────
class TestExportGuards:
    def test_export_crop_refuses_without_video(
        self, window, monkeypatch,
    ) -> None:
        """No video loaded → export_crop is guarded by MessageBox.warning."""
        warn_calls: list[Any] = []
        monkeypatch.setattr(
            QMessageBox, "warning",
            lambda *a, **kw: warn_calls.append(a) or QMessageBox.StandardButton.Ok,
        )
        # Nothing loaded
        assert window.video_path is None
        window._export("crop")
        # The guard tripped — no worker got spawned
        assert window._worker is None

    def test_export_clip_refuses_without_active_clip(
        self, window, monkeypatch,
    ) -> None:
        """Video loaded but no active clip → refused."""
        window.video_path = "/tmp/fake.mp4"
        window.active_clip = -1
        # Also need to bypass the crop_rect check for the right branch
        window.crop_rect = None

        warn_calls: list[Any] = []
        monkeypatch.setattr(
            QMessageBox, "warning",
            lambda *a, **kw: warn_calls.append(a) or QMessageBox.StandardButton.Ok,
        )
        window._export("clip")
        assert window._worker is None

    def test_export_sequence_refuses_with_one_clip(
        self, window, monkeypatch,
    ) -> None:
        """Sequence export needs >=2 clips — the guard lives in _export."""
        from klipwerk.core.models import Clip
        window.video_path = "/tmp/fake.mp4"
        window.clips = [Clip("only_one", 0.0, 1.0)]

        window._export("sequence")
        assert window._worker is None


# ── K/C toggle ──────────────────────────────────────────────────────────
class TestKCToggle:
    def test_k_mode_default_true(self, window) -> None:
        """Default is K-mode (Klip) per the spec comment in __init__."""
        assert window._use_k_mode is True

    def test_labels_contain_k_when_k_mode(self, window) -> None:
        """The sidebar Export button should say 'Klip' in K-mode."""
        # _refresh_klip_labels is called at startup, but we re-run it to
        # make sure the current state is reflected.
        window._refresh_klip_labels()
        assert "Klip" in window.sidebar.btn_ex_clip.text()
