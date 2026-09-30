<div align="center">

<img src="assets/logo.svg" alt="KLIPWERK" width="315"/>

**clips, sequences, trim, crop, convert**

[![CI](https://github.com/Reaaaaa/klipwerk/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Reaaaaa/klipwerk/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/UI-PyQt6-41cd52?logo=qt&logoColor=white)](https://pypi.org/project/PyQt6/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-155%20passing-brightgreen)](tests/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](https://github.com/Reaaaaa/klipwerk)

<br/>

*Drop in a video. Mark in and out. Draw a crop. Export. Nothing else.*

<br/>

<!-- Replace with an actual screenshot/GIF once you have one -->
![Klipwerk demo](assets/2026-04-27_21-49-05_crop.gif)

</div>

---

## Why KLIPWERK?

Most video editors are built around complex timelines with dozens of tracks. KLIPWERK focuses on one thing: cutting and cropping clips as fast as possible.
Export clips individually or stitch them into a sequence. Every action is keyboard-first, and the interface stays out of your way.
Import a video, crop exactly what you need with pixel-precise controls, and export it as a video or a GIF in seconds, supporting multiple formats and modern codecs like H.265, AV1, and WebM.

Under the hood, KLIPWERK is a thin wrapper around `ffmpeg`. It works with standard formats and keeps your workflow simple and transparent.

---

## Features

| | |
|---|---|
| **Live preview** | OpenCV-powered frame display with drag-to-crop, rule-of-thirds overlay, and aspect-ratio presets |
| **Waveform scrubber** | Timeline with waveform visualization (numpy-vectorized peak extraction), hover thumbnails, and draggable I/O markers with live scrubbing |
| **Clip list** | Drag-to-reorder, rename, undo/redo (command-pattern, no full list copies per edit) |
| **Sequence export** | Concatenate any number of clips into one video in a single click |
| **Stream-copy fast path** | No crop + all positive durations → skips re-encoding entirely, making exports significantly faster |
| **7 output formats** | H.264, H.265, AV1, VP9 across MP4, MKV, WebM |
| **Animated GIF export** | One click from any clip or the full sequence — two-branch palette filter (palettegen + paletteuse) for best-in-class 256-colour quality. FPS: 8/12/15/24. Width: 320/480/640/original. Tiered 15 s / 30 s duration safety. |
| **Rich media info** | ffprobe panel: codec, container, bitrate, color space, pixel format, duration |
| **Settings persistence** | Window geometry, export defaults, format/CRF/preset survive restarts via `QSettings` |
| **Frameless chrome** | Custom title bar with 8-direction resize handles on all edges and corners |
| **Zero config** | Drop `ffmpeg`/`ffprobe` next to the script or put them on `$PATH` — done |

> [!NOTE]
> KLIPWERK is a **cut-and-crop tool**, not a full media player. The waveform in the scrubber is a visual orientation aid — it helps you spot audio peaks so you can land on the right frame faster. Audio playback in the preview is intentionally out of scope; for a quick listen while you work, run your system's media player alongside KLIPWERK.

---

## Installation

### From source

```bash
git clone https://github.com/Reaaaaa/klipwerk
cd klipwerk
pip install -e .
klipwerk
```

### ffmpeg

KLIPWERK calls your existing `ffmpeg` installation — nothing is bundled. It searches in this order: `$PATH` → package directory → `./bin/` → `~/Documents/ffmpeg/` → `C:\ffmpeg\bin\` → `C:\Program Files\ffmpeg\bin\`.

| Platform | How to get ffmpeg |
|---|---|
| **Windows** | [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) → `ffmpeg-release-essentials.zip` → drop `ffmpeg.exe` + `ffprobe.exe` next to the package or on `%PATH%` |
| **Linux** | `sudo apt install ffmpeg` |
| **macOS** | `brew install ffmpeg` |

---

## Keyboard shortcuts

| Key | Action |
|---|---|
| `Space` | Play / pause |
| `I` | Set **In** marker at current frame |
| `O` | Set **Out** marker at current frame |
| `Shift`+`I` | Jump to **In** marker |
| `Shift`+`O` | Jump to **Out** marker |
| `Alt`+`X` | Clear **In** and **Out** markers |
| `C` | Add clip from In → Out |
| `←` / `→` | Step one frame |
| `Shift` + `←` / `→` | Step ten frames |
| `Scroll wheel` on preview | Step one frame (up = back, down = forward) |
| `Shift` + `Scroll wheel` | Step ten frames |
| `Ctrl`+`Z` | Undo |
| `Ctrl`+`Y` / `Ctrl`+`Shift`+`Z` | Redo |
| `Delete` | Delete active clip |

---

## CLI flags

```
# Always works — no PATH setup needed
python -m klipwerk
python -m klipwerk --version          # print version and exit
python -m klipwerk --help             # show flag summary
python -m klipwerk --reset-settings   # clear saved preferences

# Shorthand — available after pip install -e . (venv must be active on Windows)
klipwerk
klipwerk --version
klipwerk --help
klipwerk --reset-settings
```

---

## Development

```bash
pip install -e ".[dev]"

pytest                       # run all 148 tests
pytest -v                    # verbose output
ruff check klipwerk          # lint
mypy klipwerk                # type-check

# Headless (CI / no display)
QT_QPA_PLATFORM=offscreen pytest -q
```

CI runs the full matrix on every push: **Ubuntu × Windows × macOS** × **Python 3.10, 3.11, 3.12**.

---

## Project layout

```
klipwerk/
├── __main__.py           # entry point, CLI flag parsing
├── app.py                # main window orchestration
├── history.py            # command-pattern undo/redo
├── sidebar.py            # export controls panel builder
├── settings.py           # QSettings facade
│
├── core/
│   ├── models.py         # Clip dataclass + CropRect
│   ├── ffmpeg_runner.py  # binary lookup, platform flags, subprocess
│   ├── probe.py          # ffprobe wrapper
│   ├── formats.py        # 7 FormatSpec entries + codec arg builder
│   └── export_builder.py # pure-function planner, fast-copy decision
│
├── widgets/
│   ├── preview.py        # live video preview + crop drag
│   ├── scrubber.py       # timeline scrubber with waveform
│   ├── seq_preview.py    # standalone sequence preview window
│   ├── clip_item.py      # sidebar list row + timeline tile
│   ├── guarded.py        # scroll-safe QSpinBox / QComboBox
│   └── helpers.py        # styled label / button / separator
│
├── workers/
│   ├── ffmpeg_worker.py  # QThread for export (with cancel + kill escalation)
│   ├── waveform.py       # vectorized peak extraction
│   └── thumbnail.py      # scrubber hover thumbnails
│
└── ui/
    ├── theme.py          # dark palette + Qt stylesheet
    └── icons.py          # SVG → QIcon with lru_cache
```

---

## Architecture highlights

- **Pure-function export planner** (`SequencePlan`) — the fast-copy decision, argv construction, and GIF filter chain are fully testable without Qt, covered by dedicated unit tests in `tests/test_export_builder.py`.
- **Command-pattern undo/redo** — edits push/pop `Command` objects; no deep-copying the clip list on every action.
- **Vectorized waveform** — `numpy.reshape` + `max(axis=1)` avoids a Python loop over samples, keeping peak extraction fast even for longer files.
- **Platform-safe subprocess flags** — `CREATE_NO_WINDOW` is gated behind `getattr` so the same code path works on Linux and macOS without `AttributeError`.
- **Zombie-process cleanup** — `FFmpegWorker` waits 2 s after `terminate()`, escalates to `kill()` on timeout, then waits again. Especially relevant for sequence exports that spawn many back-to-back ffmpeg processes.

---

## License

MIT — see [LICENSE](LICENSE).
