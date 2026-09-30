"""Global pytest configuration and fixtures for Klipwerk test suite."""
from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QMessageBox


@pytest.fixture(autouse=True)
def _stub_ffmpeg(monkeypatch):
    """Make the ffmpeg binary lookup succeed without actually having ffmpeg.

    Klipwerk doesn't call ffmpeg during construction, but some code
    paths under test resolve the binary. Faking it lets the tests run
    reliably on CI boxes without the binary installed.
    """
    from klipwerk.core import ffmpeg_runner
    monkeypatch.setattr(ffmpeg_runner, "_FFMPEG", "/usr/bin/ffmpeg")
    monkeypatch.setattr(ffmpeg_runner, "_FFPROBE", "/usr/bin/ffprobe")


@pytest.fixture(autouse=True)
def _stub_modal_dialogs(monkeypatch):
    """Neutralize modal dialogs so tests don't block forever or segfault.

    Every dialog is replaced with a no-op or Ok/Cancel-equivalent.
    """
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
