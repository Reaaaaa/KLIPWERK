# Changelog

All notable changes to this project will be documented in this file.

## [0.5.0]

### Added
- **Interactive Move & Aspect-Ratio-Preserving Scaling for Crop Presets**:
  - Selecting an aspect ratio preset (`16:9`, `9:16`, `1:1`, `4:3`) now creates a fully movable and resizable crop box on the video preview.
  - Dragging inside the crop box repositions it anywhere within video boundaries with boundary clamping.
  - Dragging any of the 8 resize handles scales the crop box while strictly locking and preserving the aspect ratio.
  - Added visual corner and midpoint resize handles and context-aware cursor feedback (`SizeAllCursor`, `SizeFDiagCursor`, `SizeBDiagCursor`, `SizeHorCursor`, `SizeVerCursor`).
  - Synced video pixel coordinates live with sidebar spinboxes and export buttons.
- **Unified Single Thick Timeline Bar & Embedded Waveform**:
  - Replaced the confusing two-tier timeline layout with a single, modern 14 px timeline capsule bar.
  - Audio waveforms are now rendered directly on/inside the timeline bar, preventing peaks from reaching into the video preview.
  - Eliminated zero-amplitude horizontal line artifacts during audio silence.
  - Added subtle luminous played progress tint behind the waveform peaks and refined playhead handle.
- **Aspect Ratio Preset Buttons Styling**:
  - Fixed cut-off/obscured lower border on aspect ratio preset buttons (`16:9`, `9:16`, `1:1`, `4:3`) by adjusting box sizing, padding, and layout margins.
  - Added active checked state highlighting the selected aspect ratio preset with exclusive toggle behavior, auto-cleared on "Clear Crop".
- **"Clear In/Out" toolbar button & shortcut**:
  - Added a dedicated `✕ Clear In/Out` danger button in the top toolbar next to `[ In` and `Out ]` to reset accidentally set cut points.
  - Added `Alt`+`X` keyboard shortcut to quickly clear In and Out markers.
  - Button auto-enables whenever In or Out marks are set or adjusted, and auto-disables on clear or close.
  - Fully resets timeline markers, range highlights, sidebar In/Out spinboxes, and timecode labels (`In: --:--:--` / `Out: --:--:--`).
- **Enlarged In/Out timeline markers with Drag & Drop**:
  - Replaced small marker triangles with prominent 16×16 px pentagon badges labeled "I" (cyan) and "O" (coral), complete with a vertical needle line through the track for precise visual alignment.
  - Interactive horizontal drag & drop: hover changes cursor to `SizeHorCursor` with an active white outline; dragging repositions markers smoothly along the timeline.
  - Collision clamping: In marker cannot be dragged past Out; Out marker cannot be dragged before In.
  - Live video preview: scrubbing/dragging an In or Out marker seeks video frames in real-time, syncing sidebar spinboxes and timecode displays immediately.
- **Unit test suites**:
  - `tests/test_crop_interaction.py`: 7 tests covering crop hit-testing, dragging/moving, aspect-ratio locked scaling, boundary clamping, and preset button synchronization.
  - `tests/test_markers_and_scrubber.py`: 11 tests covering marker hit-testing, drag & drop, clamping, hover cursor changes, and state resets.
  - `tests/test_window_scaling.py`: 12 tests covering 8-way resize hit testing, window state maximize/restore icon synchronization, and hover persistence.

### Fixed
- **Frameless window resizing glitches and edge detection**:
  - Resolved window resizing flicker and cursor thrashing by using `QApplication.changeOverrideCursor()` and atomic `setGeometry()` calculations instead of separate `resize()` and `move()` steps.
  - Implemented full 8-direction resize detection (left, right, top, bottom, and all 4 corners with a 14 px corner hit zone).
  - Fixed event swallowing on the bottom and right window edges where child scroll areas (`QAbstractScrollArea`) previously consumed mouse press events before resizing could trigger.
- **Window titlebar maximize / restore icon inconsistency**:
  - Synchronized the maximize button icon and tooltip with native window state (`SVG_MAXIMIZE` when windowed, `SVG_RESTORE` when maximized/fullscreen).
  - Removed unstable polling timer in favor of Qt's native `changeEvent(QEvent.Type.WindowStateChange)`.

## [0.4.1]

### Fixed
- **Sidebar ghost artifacts on splitter drag**: `WA_OpaquePaintEvent` was
  set to `True` at widget init even without a video loaded, so Windows left
  stale pixels behind when the splitter was moved. Flag now starts `False`
  and is only enabled once `set_frame()` renders a real frame. Both
  splitters additionally call `setOpaqueResize(False)` to prevent live
  repaint glitches, and `splitterMoved` triggers a full central-widget
  repaint as a belt-and-suspenders fallback.
- **`gif_vf` test false positive**: `assert "scale" not in vf` incorrectly
  matched `bayer_scale=5` inside the palette filter. Fixed to check
  `"flags=lanczos" not in vf` instead.
- **CLI flags section in README**: clarified that the `klipwerk` shorthand
  requires an active venv on Windows; `python -m klipwerk` always works.

## [0.4.0]

### Added
- **GIF export** — animated GIF from any clip or the full sequence.
  - Per-clip crop is applied automatically for **Clip → GIF** exports.
  - **Seq → GIF** applies the current global crop to all clips and
    concatenates them into one palette-optimised GIF.
  - FPS options: 8 / 12 / 15 / 24.  Width options: 320 / 480 / 640 px
    or Original (no resize).  Both persist across sessions.
  - Tiered duration safety: silent below 15 s, confirmation dialog
    15–30 s, hard block above 30 s.
  - Uses a two-branch ffmpeg palette filter
    (`palettegen stats_mode=diff` + `paletteuse dither=bayer`) for
    maximum colour fidelity in 256 colours.
  - 10 new unit tests for `gif_vf()` in `tests/test_export_builder.py`.
- **Mouse wheel seek on preview**: scroll up/down on the video preview
  steps one frame back/forward. `Shift`+scroll = 10 frames.
- **Shift+I / Shift+O shortcuts**: jump playhead to the In or Out marker
  without resetting it (previously only setting was possible).
- **Auto-pause at Out marker** (`⏸ at Out` toggle in the playback bar):
  when active, playback stops automatically the moment the playhead
  reaches `mark_out` — useful for previewing a marked range precisely.
  Resets to off when a video is closed.

### Fixed
- **Preview not clearing on Close Video**: `WA_OpaquePaintEvent` prevented
  Qt from erasing the background before drawing the placeholder text, so
  the last video frame showed through. Flag is now disabled in `reset()`
  and re-enabled in `set_frame()` when full-canvas rendering resumes.

### Changed
- **`FONT_BUMP` scale constant** (`ui/theme.py`): a single integer that
  scales all font sizes uniformly. Set to `2` by default for better
  readability on 2K/4K displays; set to `0` to restore original sizes.
  `label()` and `section_label()` in `widgets/helpers.py` apply it
  automatically; inline stylesheets in `app.py` and `seq_preview.py`
  reference it via f-string expressions.

## [0.3.0]

### Added
- **Standalone sequence preview window** (`widgets/seq_preview.py`):
  clicking "Preview Sequence" now opens an independent floating window
  with its own `VideoCapture` and timer — no conflict with the main
  player. Includes the same frameless custom title bar as the main
  window (drag, resize, min/max/close), transport buttons, clip counter,
  and keyboard shortcuts (`Space`, `←`/`→`, `Esc`).
- **Per-mode export suffix fields**: the single generic suffix input is
  replaced by three independent fields — `→ Crop` (default `_crop`),
  `→ Clip` (default `_clip`), `→ Seq` (default `_seq`). All three
  persist across sessions via `QSettings`.
- **Stream-copy fast path for sequence export**: when no clip has a crop
  and all clips have positive duration, sequence export skips
  re-encoding entirely and uses `-c copy`. Cuts snap to the nearest
  keyframe; the status label reads "stream-copy (fast)…" while active.
- **`SequencePlan` planner** (`core/export_builder.py`): the fast-copy
  decision and argv construction are pure functions, fully testable
  without Qt.
- **Settings persistence** (`settings.py`): window geometry, export
  format/CRF/preset/prefix/suffix, and K/C mode survive restarts via
  `QSettings`. Corrupt or missing values fall back to defaults silently.
- **`--version` / `-V` and `--help` CLI flags** — flag parsing happens
  before `QApplication` construction so they work on headless machines.
- **UI smoke-test suite** (`tests/test_app_smoke.py`): 12 tests that
  construct the main window, exercise common paths, and verify clean
  teardown.
- 61 new unit tests total across settings, export builder, sequence
  planner, and waveform modules.

### Fixed
- **Clips not cleared on Close Video** — `_close_video()` now resets
  the clip list, undo history, and active-clip index and re-renders the
  sidebar and timeline immediately.
- **Zombie ffmpeg processes on cancel** — worker now waits up to 2 s
  after `terminate()`, escalates to `kill()` on timeout, then waits
  again.
- **Hardcoded `.mp4` segment extension** in sequence export — segments
  now match the source or target container so the concat demuxer's
  consistency rule is always satisfied.
- **Taskbar minimize broken on frameless window** — added
  `WindowMinimizeButtonHint` alongside `FramelessWindowHint`.

### Changed
- Video info panel redesigned: permanent "Video-Infos" title with a
  subtitle line, hover effect, and inline "click to expand/collapse"
  hint — no longer shows the raw filename in the header.
- Button borders increased to 2 px, `border-radius` reduced to 4 px,
  toolbar height increased to 58 px for better visual clarity.
- "Preview Clips" button renamed to "Preview Sequence" consistently,
  independent of the K/C language toggle.

## [0.2.0] — refactor release

### Added
- Modular package layout (`core/`, `widgets/`, `workers/`, `ui/`)
- Command-pattern undo/redo — O(1) per edit instead of deep-copying the clip list
- `Clip.id` — stable UUID so UI widgets can be diffed instead of rebuilt
- Test suite covering formats, history, ffmpeg-runner, and waveform downsampling
- `pyproject.toml` with `klipwerk` console-script entry point
- Linting configuration: ruff + mypy
- README with install instructions, keyboard shortcuts, project layout

### Fixed
- **`BASE` was undefined** — `find_bin()` would raise `NameError` when ffmpeg
  wasn't on `$PATH`. Binary lookup now works reliably as a fallback.
- **`subprocess.CREATE_NO_WINDOW`** — referenced on Linux/macOS inside a ternary
  that Python eagerly evaluated, causing `AttributeError` at every export.
  Now gated behind `getattr` and exposed as a platform-safe constant.
- **`_update_codec_note` was defined twice** — the second override had only
  three entries, so selecting H.265/AV1/VP9 raised `IndexError`.
- **Timeline drag-to-self** — `_move_clip` now ignores from-index == to-index.
- **Bounds checks** — `_sel_clip`, `_rename_clip`, `_preview_clip`, `_del_clip`
  all validate the index before dereferencing.
- **QImage garbage-collection** — frames in the preview and thumbnails now
  `.copy()` the QImage so the numpy buffer can be freed safely.
- **Waveform worker leak** — re-loading a video now properly cancels the
  previous extraction's ffmpeg subprocess.
- **Bare `except:`** — replaced with specific exception types everywhere.

### Changed
- Waveform downsampling vectorized via `numpy.reshape` + `max(axis=1)`,
  avoiding a Python loop over samples.
- `SequenceFFmpegWorker` pulled out of the monkey-patched closure that used
  to live inside `_run_export`.
- Export format table moved to `core/formats.py` as a proper dataclass list.
- Icon rendering now cached via `functools.lru_cache` — no more re-parsing
  SVGs on every hover.
- `subprocess.run` in `probe_video` catches specific exception types instead
  of bare `except`.

## [0.1.0] — initial release

Monolithic single-file editor. See `klipwerk.py` in the project history.
