"""The right-hand sidebar: video info, crop controls, mark in/out, clip
list, export settings.

Extracted from the monolithic ``Klipwerk._build_sidebar`` (~300 lines).
The builder returns a dict of references to every widget the main
window needs to interact with later.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .core.formats import FORMATS
from .ui.theme import ACC, ACC3, BORDER, BORDER2, FONT_BUMP, MUTED, MUTED2, S1, S2, S3, TEXT
from .widgets.guarded import (
    GuardedComboBox,
    GuardedDoubleSpinBox,
    GuardedSpinBox,
)
from .widgets.helpers import btn, hsep, label, section_label


@dataclass
class SidebarRefs:
    """Every widget in the sidebar that the main window needs to touch later."""

    widget: QWidget
    sections_splitter: QSplitter   # user-resizable divider between the three panels

    # Video info panel
    info_header: QWidget
    info_label: QLabel
    info_subtitle_lbl: QLabel
    info_toggle_lbl: QLabel
    info_panel: QWidget
    info_rows: dict[str, QLabel]

    # Crop controls
    crop_x: GuardedSpinBox
    crop_y: GuardedSpinBox
    crop_w: GuardedSpinBox
    crop_h: GuardedSpinBox
    crop_info: QLabel
    lbl_x: QLabel
    lbl_y: QLabel
    lbl_w: QLabel
    lbl_h: QLabel
    btn_ex_crop: QPushButton
    fname_preview_crop: QLabel
    preset_btns: list[QPushButton]

    # Mark In/Out
    mark_in_spin: GuardedDoubleSpinBox
    mark_out_spin: GuardedDoubleSpinBox
    lbl_in: QLabel
    lbl_out: QLabel
    btn_add_sidebar: QPushButton

    # Clips list
    klips_section_label: QLabel
    clips_count_label: QLabel
    clips_scroll: QScrollArea
    clips_container: QWidget
    clips_vlay: QVBoxLayout

    # Export
    export_fmt: GuardedComboBox
    export_crf: GuardedSpinBox
    export_preset: GuardedComboBox
    lbl_fmt: QLabel
    lbl_crf: QLabel
    lbl_preset: QLabel
    codec_note: QLabel
    export_prefix: QLineEdit
    export_suffix_crop: QLineEdit
    export_suffix_clip: QLineEdit
    export_suffix_seq: QLineEdit
    fname_preview: QLabel
    btn_ex_seq: QPushButton
    btn_ex_clip: QPushButton

    # GIF export
    gif_fps:         GuardedComboBox
    gif_width:       GuardedComboBox
    btn_ex_gif_clip: QPushButton
    btn_ex_gif_seq:  QPushButton


def build_sidebar(
    *,
    on_crop_changed: Callable,
    on_mark_in_changed: Callable[[float], None],
    on_mark_out_changed: Callable[[float], None],
    on_fmt_changed: Callable[[int], None],
    on_prefix_changed: Callable[[str], None],
    on_suffix_crop_changed: Callable[[str], None],
    on_suffix_clip_changed: Callable[[str], None],
    on_suffix_seq_changed: Callable[[str], None],
    set_crop_preset: Callable[[int, int], None],
    on_add_klip: Callable[[], None],
    on_export_crop: Callable[[], None],
    on_export_clip: Callable[[], None],
    on_export_seq: Callable[[], None],
    on_export_gif_clip: Callable[[], None],
    on_export_gif_seq: Callable[[], None],
) -> SidebarRefs:
    """Build the sidebar and wire up all callbacks. Returns all widget refs."""
    root = QWidget()
    root.setStyleSheet(f"background:{S1};")
    root_lay = QVBoxLayout(root)
    root_lay.setContentsMargins(0, 0, 0, 0)
    root_lay.setSpacing(0)

    # ── Video info section (collapsible) ────────────────────────────
    info_header = QWidget()
    info_header.setFixedHeight(48)
    info_header.setStyleSheet(
        f"QWidget {{ background:{S2}; }}"
        f"QWidget:hover {{ background:{S3}; }}"
    )
    info_header.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    ih_lay = QHBoxLayout(info_header)
    ih_lay.setContentsMargins(14, 6, 14, 6)

    ih_text_lay = QVBoxLayout()
    ih_text_lay.setSpacing(2)
    ih_text_lay.setContentsMargins(0, 0, 0, 0)

    ih_title_row = QHBoxLayout()
    ih_title_row.setSpacing(6)
    ih_title_row.setContentsMargins(0, 0, 0, 0)
    info_label = label("Video-Infos", color=TEXT, size=12)
    info_toggle_lbl = label("— click to expand", color=MUTED2, size=10)
    ih_title_row.addWidget(info_label)
    ih_title_row.addWidget(info_toggle_lbl)
    ih_title_row.addStretch()

    info_subtitle_lbl = label("No video loaded", color=MUTED2, size=10)
    ih_text_lay.addLayout(ih_title_row)
    ih_text_lay.addWidget(info_subtitle_lbl)

    ih_lay.addLayout(ih_text_lay)

    info_panel = QWidget()
    info_panel.setStyleSheet(f"background:{S2};")
    info_panel.hide()
    ip_lay = QVBoxLayout(info_panel)
    ip_lay.setContentsMargins(14, 8, 14, 10)
    ip_lay.setSpacing(3)

    info_rows: dict[str, QLabel] = {}
    for key in [
        "File", "Container", "Size", "Bitrate", "Duration",
        "Resolution", "Aspect", "FPS", "Video Codec", "Pixel Format",
        "Color Space", "Audio Codec", "Audio",
    ]:
        row = QHBoxLayout()
        row.setSpacing(6)
        k_lbl = label(key, color=MUTED, size=10)
        k_lbl.setFixedWidth(86)
        v_lbl = label("—", color=TEXT, size=10)
        v_lbl.setWordWrap(True)
        row.addWidget(k_lbl)
        row.addWidget(v_lbl, 1)
        ip_lay.addLayout(row)
        info_rows[key] = v_lbl

    # ── Crop section ───────────────────────────────────────────────
    crop_w_widget = QWidget()
    crop_lay = QVBoxLayout(crop_w_widget)
    crop_lay.setContentsMargins(14, 14, 14, 14)
    crop_lay.setSpacing(8)
    crop_lay.addWidget(section_label("Crop Region"))

    crop_grid_w, (crop_x, crop_y, crop_w, crop_h, lbl_x, lbl_y, lbl_w, lbl_h) = \
        _build_crop_grid(on_crop_changed)
    crop_lay.addWidget(crop_grid_w)

    crop_info = label("No crop — draw on preview or enter values", color=MUTED2, size=11)
    crop_info.setWordWrap(True)
    crop_info.setContentsMargins(10, 0, 0, 0)
    crop_lay.addWidget(crop_info)

    # Aspect ratio presets
    presets_w = QWidget()
    presets_outer = QHBoxLayout(presets_w)
    presets_outer.setContentsMargins(10, 2, 10, 6)
    presets_outer.setSpacing(6)
    preset_btn_style = (
        f"QPushButton {{ background:{S3}; border:1.5px solid {BORDER2};"
        f" color:{TEXT}; font-size:{11 + FONT_BUMP}px; border-radius:4px;"
        f" padding:3px 6px; min-height:0px; outline:none; }}"
        f"QPushButton:hover {{ border-color:{ACC}; color:{ACC}; background:{S3}; }}"
        f"QPushButton:checked {{ background:{S2}; border-color:{ACC}; color:{ACC}; font-weight:bold; }}"
        f"QPushButton:disabled {{ color:{MUTED}; border-color:{BORDER}; background:{S2}; }}"
    )
    preset_btns: list[QPushButton] = []
    for name, wr, hr in [("16:9", 16, 9), ("9:16", 9, 16), ("1:1", 1, 1), ("4:3", 4, 3)]:
        b = QPushButton(name)
        b.setCheckable(True)
        b.setFixedHeight(28)
        b.setStyleSheet(preset_btn_style)
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        def _make_handler(w_=wr, h_=hr, btn_=b):
            def handler(_checked=False):
                for other in preset_btns:
                    if other is not btn_:
                        other.blockSignals(True)
                        other.setChecked(False)
                        other.blockSignals(False)
                btn_.blockSignals(True)
                btn_.setChecked(True)
                btn_.blockSignals(False)
                set_crop_preset(w_, h_)
            return handler

        b.clicked.connect(_make_handler(wr, hr, b))
        presets_outer.addWidget(b)
        preset_btns.append(b)
    crop_lay.addWidget(presets_w)

    from .ui.icons import SVG_DOWNLOAD, make_icon
    btn_ex_crop = btn("  Export Cropped Video")
    btn_ex_crop.setFixedHeight(34)
    btn_ex_crop.setIcon(make_icon(SVG_DOWNLOAD, MUTED2))
    btn_ex_crop.clicked.connect(on_export_crop)
    btn_ex_crop.setDisabled(True)

    fname_preview_crop = label("", color=ACC3, size=10)
    fname_preview_crop.setWordWrap(True)
    fname_preview_crop.setContentsMargins(10, 0, 0, 0)
    crop_lay.addWidget(fname_preview_crop)
    crop_lay.addWidget(btn_ex_crop)

    # ── Mark In/Out section ────────────────────────────────────────
    mark_w = QWidget()
    mark_lay = QVBoxLayout(mark_w)
    mark_lay.setContentsMargins(14, 14, 14, 14)
    mark_lay.setSpacing(8)
    mark_lay.addWidget(hsep())
    mark_lay.addWidget(section_label("Mark In / Out"))

    mark_grid_w, (mark_in_spin, mark_out_spin, lbl_in, lbl_out) = \
        _build_mark_grid(on_mark_in_changed, on_mark_out_changed)
    mark_lay.addWidget(mark_grid_w)

    btn_add_sidebar = btn("+  Add as Klip")
    btn_add_sidebar.setFixedHeight(34)
    btn_add_sidebar.clicked.connect(on_add_klip)
    mark_lay.addWidget(btn_add_sidebar)

    # ── Clips header ───────────────────────────────────────────────
    clips_header = QWidget()
    clips_header.setFixedHeight(34)
    clips_header.setStyleSheet(
        f"background:{S2}; border-top:1px solid {BORDER2};"
        f" border-bottom:1px solid {BORDER};"
    )
    ch_lay = QHBoxLayout(clips_header)
    ch_lay.setContentsMargins(14, 0, 14, 0)
    klips_section_label = section_label("Klips")
    ch_lay.addWidget(klips_section_label)
    ch_lay.addStretch()
    clips_count_label = label("0 Klips", color=MUTED, size=11)
    ch_lay.addWidget(clips_count_label)

    clips_scroll = QScrollArea()
    clips_scroll.setWidgetResizable(True)
    clips_scroll.setStyleSheet(f"background:{S1}; border:none;")
    clips_container = QWidget()
    clips_container.setStyleSheet(f"background:{S1};")
    clips_vlay = QVBoxLayout(clips_container)
    clips_vlay.setContentsMargins(10, 10, 10, 10)
    clips_vlay.setSpacing(6)
    clips_vlay.addStretch()
    clips_scroll.setWidget(clips_container)

    # ── Export settings ────────────────────────────────────────────
    export_w = QWidget()
    export_lay = QVBoxLayout(export_w)
    export_lay.setContentsMargins(14, 14, 14, 14)
    export_lay.setSpacing(8)
    export_lay.addWidget(hsep())
    export_lay.addWidget(section_label("Export Settings"))

    (egrid_w, export_fmt, export_crf, export_preset, lbl_fmt, lbl_crf, lbl_preset) = \
        _build_export_grid(on_fmt_changed)
    export_lay.addWidget(egrid_w)

    codec_note = label("", color=MUTED, size=10)
    codec_note.setWordWrap(True)
    codec_note.setContentsMargins(10, 0, 0, 4)
    export_lay.addWidget(codec_note)

    export_lay.addWidget(hsep())
    export_lay.addWidget(section_label("Output Filename"))

    (naming_w, export_prefix,
     export_suffix_crop, export_suffix_clip, export_suffix_seq) = _build_naming_grid(
        on_prefix_changed,
        on_suffix_crop_changed,
        on_suffix_clip_changed,
        on_suffix_seq_changed,
    )
    export_lay.addWidget(naming_w)

    fname_preview = label("", color=ACC3, size=10)
    fname_preview.setWordWrap(True)
    fname_preview.setContentsMargins(10, 0, 0, 0)
    export_lay.addWidget(fname_preview)

    from .ui.icons import SVG_CLIP, SVG_LAYERS
    btn_ex_seq = btn("  Export Sequence")
    btn_ex_clip = btn("  Export Active Klip")
    btn_ex_seq.setIcon(make_icon(SVG_LAYERS, MUTED2))
    btn_ex_clip.setIcon(make_icon(SVG_CLIP, MUTED2))
    for b in (btn_ex_seq, btn_ex_clip):
        b.setFixedHeight(34)
    btn_ex_seq.clicked.connect(on_export_seq)
    btn_ex_clip.clicked.connect(on_export_clip)
    btn_ex_seq.setDisabled(True)
    btn_ex_clip.setDisabled(True)
    export_lay.addWidget(btn_ex_seq)
    export_lay.addWidget(btn_ex_clip)

    # ── GIF export section ─────────────────────────────────────────
    export_lay.addWidget(hsep())
    export_lay.addWidget(section_label("GIF Export"))

    gif_fps = GuardedComboBox()
    gif_fps.addItems(["8 fps", "12 fps", "15 fps", "24 fps"])
    gif_fps.setCurrentIndex(1)   # 12 fps default

    gif_width = GuardedComboBox()
    gif_width.addItems(["320 px", "480 px", "640 px", "Original"])
    gif_width.setCurrentIndex(3)  # Original default

    gif_grid_wrap = QWidget()
    gif_outer = QHBoxLayout(gif_grid_wrap)
    gif_outer.setContentsMargins(10, 0, 0, 0)
    gif_outer.setSpacing(0)
    gif_grid = QGridLayout()
    gif_grid.setSpacing(7)
    gif_grid.setColumnStretch(1, 1)
    lgf = label("FPS",   color=MUTED2, size=12); lgf.setFixedWidth(52)
    lgw = label("Width", color=MUTED2, size=12); lgw.setFixedWidth(52)
    gif_grid.addWidget(lgf, 0, 0); gif_grid.addWidget(gif_fps,   0, 1)
    gif_grid.addWidget(lgw, 1, 0); gif_grid.addWidget(gif_width, 1, 1)
    gif_outer.addLayout(gif_grid)
    export_lay.addWidget(gif_grid_wrap)

    btn_ex_gif_clip = btn("  Klip → GIF")
    btn_ex_gif_seq  = btn("  Seq → GIF")
    for b in (btn_ex_gif_clip, btn_ex_gif_seq):
        b.setFixedHeight(34)
    btn_ex_gif_clip.clicked.connect(on_export_gif_clip)
    btn_ex_gif_seq.clicked.connect(on_export_gif_seq)
    btn_ex_gif_clip.setDisabled(True)
    btn_ex_gif_seq.setDisabled(True)
    export_lay.addWidget(btn_ex_gif_clip)
    export_lay.addWidget(btn_ex_gif_seq)

    # ── Wrap scrollable regions & assemble ────────────────────────
    # Top section: crop + mark, scrollable together
    sections_w = QWidget()
    sections_w.setStyleSheet(f"background:{S1};")
    sections_inner = QVBoxLayout(sections_w)
    sections_inner.setContentsMargins(0, 0, 0, 0)
    sections_inner.setSpacing(0)
    sections_inner.addWidget(crop_w_widget)
    sections_inner.addWidget(mark_w)

    sections_scroll = _make_scroll(sections_w)

    # Middle section: clips list header + scrollable clip list, grouped
    # into one widget so the splitter treats them as one resizable unit.
    clips_group = QWidget()
    clips_group.setStyleSheet(f"background:{S1};")
    cg_lay = QVBoxLayout(clips_group)
    cg_lay.setContentsMargins(0, 0, 0, 0)
    cg_lay.setSpacing(0)
    cg_lay.addWidget(clips_header)
    cg_lay.addWidget(clips_scroll, 1)

    # Bottom section: export settings, scrollable
    export_scroll = _make_scroll(export_w)

    # Three-way vertical splitter — user can drag the handles to
    # rebalance how much room each section gets. All three panels have
    # a sensible minimum so collapsing one to zero isn't accidental.
    sections_scroll.setMinimumHeight(60)
    clips_group.setMinimumHeight(60)
    export_scroll.setMinimumHeight(60)

    sections_splitter = QSplitter(Qt.Orientation.Vertical)
    sections_splitter.setChildrenCollapsible(False)
    sections_splitter.setHandleWidth(4)
    sections_splitter.setOpaqueResize(False)  # prevents repaint glitches on Windows
    sections_splitter.setStyleSheet(
        f"QSplitter::handle {{ background:{BORDER}; }}"
        f"QSplitter::handle:hover {{ background:{BORDER2}; }}"
    )
    sections_splitter.addWidget(sections_scroll)
    sections_splitter.addWidget(clips_group)
    sections_splitter.addWidget(export_scroll)

    # Initial size distribution — rough proportions. The user's own
    # resize preference is restored in app._apply_settings() if saved.
    sections_splitter.setSizes([400, 300, 320])

    # Let the clip list grab extra room by default when the window is
    # resized vertically, since that's the most elastic content.
    sections_splitter.setStretchFactor(0, 0)
    sections_splitter.setStretchFactor(1, 1)
    sections_splitter.setStretchFactor(2, 0)

    root_lay.addWidget(info_header)
    root_lay.addWidget(info_panel)
    root_lay.addWidget(sections_splitter, 1)

    return SidebarRefs(
        widget=root,
        sections_splitter=sections_splitter,
        info_header=info_header,
        info_label=info_label,
        info_subtitle_lbl=info_subtitle_lbl,
        info_toggle_lbl=info_toggle_lbl,
        info_panel=info_panel,
        info_rows=info_rows,
        crop_x=crop_x, crop_y=crop_y, crop_w=crop_w, crop_h=crop_h,
        lbl_x=lbl_x, lbl_y=lbl_y, lbl_w=lbl_w, lbl_h=lbl_h,
        crop_info=crop_info,
        btn_ex_crop=btn_ex_crop,
        fname_preview_crop=fname_preview_crop,
        preset_btns=preset_btns,
        mark_in_spin=mark_in_spin, mark_out_spin=mark_out_spin,
        lbl_in=lbl_in, lbl_out=lbl_out,
        btn_add_sidebar=btn_add_sidebar,
        klips_section_label=klips_section_label,
        clips_count_label=clips_count_label,
        clips_scroll=clips_scroll,
        clips_container=clips_container,
        clips_vlay=clips_vlay,
        export_fmt=export_fmt,
        export_crf=export_crf,
        export_preset=export_preset,
        lbl_fmt=lbl_fmt, lbl_crf=lbl_crf, lbl_preset=lbl_preset,
        codec_note=codec_note,
        export_prefix=export_prefix,
        export_suffix_crop=export_suffix_crop,
        export_suffix_clip=export_suffix_clip,
        export_suffix_seq=export_suffix_seq,
        fname_preview=fname_preview,
        btn_ex_seq=btn_ex_seq,
        btn_ex_clip=btn_ex_clip,
        gif_fps=gif_fps,
        gif_width=gif_width,
        btn_ex_gif_clip=btn_ex_gif_clip,
        btn_ex_gif_seq=btn_ex_gif_seq,
    )


# ── Helpers to build each sub-grid ─────────────────────────────────
def _build_crop_grid(on_change):
    wrap = QWidget()
    outer = QHBoxLayout(wrap)
    outer.setContentsMargins(10, 0, 0, 0)
    outer.setSpacing(0)

    grid = QGridLayout()
    grid.setSpacing(7)
    grid.setColumnStretch(1, 1)
    grid.setColumnStretch(3, 1)

    crop_x = GuardedSpinBox(); crop_x.setRange(0, 9999); crop_x.setValue(0)
    crop_y = GuardedSpinBox(); crop_y.setRange(0, 9999); crop_y.setValue(0)
    crop_w = GuardedSpinBox(); crop_w.setRange(2, 9999); crop_w.setValue(0)
    crop_h = GuardedSpinBox(); crop_h.setRange(2, 9999); crop_h.setValue(0)
    for sp in (crop_x, crop_y, crop_w, crop_h):
        sp.valueChanged.connect(on_change)
        sp.setMinimumWidth(70)

    lx = label("X", color=MUTED2, size=12); lx.setFixedWidth(20)
    ly = label("Y", color=MUTED2, size=12); ly.setFixedWidth(20)
    lw = label("W", color=MUTED2, size=12); lw.setFixedWidth(20)
    lh = label("H", color=MUTED2, size=12); lh.setFixedWidth(20)

    grid.addWidget(lx, 0, 0); grid.addWidget(crop_x, 0, 1)
    grid.addWidget(lw, 0, 2); grid.addWidget(crop_w, 0, 3)
    grid.addWidget(ly, 1, 0); grid.addWidget(crop_y, 1, 1)
    grid.addWidget(lh, 1, 2); grid.addWidget(crop_h, 1, 3)
    outer.addLayout(grid)
    return wrap, (crop_x, crop_y, crop_w, crop_h, lx, ly, lw, lh)


def _build_mark_grid(on_in, on_out):
    wrap = QWidget()
    outer = QHBoxLayout(wrap)
    outer.setContentsMargins(10, 0, 0, 0)
    outer.setSpacing(0)

    grid = QGridLayout()
    grid.setSpacing(7)
    grid.setColumnStretch(1, 1)

    in_spin = GuardedDoubleSpinBox()
    out_spin = GuardedDoubleSpinBox()
    for sp in (in_spin, out_spin):
        sp.setRange(0, 99999)
        sp.setDecimals(2)
        sp.setSingleStep(0.1)
        sp.setMinimumWidth(90)
    in_spin.valueChanged.connect(on_in)
    out_spin.valueChanged.connect(on_out)

    lin = label("In",  color=MUTED2, size=12); lin.setFixedWidth(32)
    lot = label("Out", color=MUTED2, size=12); lot.setFixedWidth(32)

    grid.addWidget(lin, 0, 0); grid.addWidget(in_spin,  0, 1)
    grid.addWidget(lot, 1, 0); grid.addWidget(out_spin, 1, 1)
    outer.addLayout(grid)
    return wrap, (in_spin, out_spin, lin, lot)


def _build_export_grid(on_fmt_changed):
    wrap = QWidget()
    outer = QHBoxLayout(wrap)
    outer.setContentsMargins(10, 0, 0, 0)
    outer.setSpacing(0)

    grid = QGridLayout()
    grid.setSpacing(7)
    grid.setColumnStretch(1, 1)

    export_fmt = GuardedComboBox()
    export_fmt.addItems([spec.label for spec in FORMATS])

    export_crf = GuardedSpinBox()
    export_crf.setRange(0, 63)
    export_crf.setValue(23)

    export_preset = GuardedComboBox()
    export_preset.addItems(list(FORMATS[0].presets))
    export_preset.setCurrentIndex(2)

    export_fmt.currentIndexChanged.connect(on_fmt_changed)

    lf = label("Format", color=MUTED2, size=12); lf.setFixedWidth(52)
    lc = label("CRF",    color=MUTED2, size=12); lc.setFixedWidth(52)
    lp = label("Preset", color=MUTED2, size=12); lp.setFixedWidth(52)

    grid.addWidget(lf, 0, 0); grid.addWidget(export_fmt,    0, 1)
    grid.addWidget(lc, 1, 0); grid.addWidget(export_crf,    1, 1)
    grid.addWidget(lp, 2, 0); grid.addWidget(export_preset, 2, 1)
    outer.addLayout(grid)
    return wrap, export_fmt, export_crf, export_preset, lf, lc, lp


def _build_naming_grid(on_prefix, on_suffix_crop, on_suffix_clip, on_suffix_seq):
    wrap = QWidget()
    outer = QHBoxLayout(wrap)
    outer.setContentsMargins(10, 0, 0, 0)
    outer.setSpacing(0)

    grid = QGridLayout()
    grid.setSpacing(7)
    grid.setColumnStretch(1, 1)

    prefix = QLineEdit()
    prefix.setPlaceholderText("e.g.  project_")
    prefix.textChanged.connect(on_prefix)

    suffix_crop = QLineEdit()
    suffix_crop.setText("_crop")
    suffix_crop.textChanged.connect(on_suffix_crop)

    suffix_clip = QLineEdit()
    suffix_clip.setText("_clip")
    suffix_clip.textChanged.connect(on_suffix_clip)

    suffix_seq = QLineEdit()
    suffix_seq.setText("_seq")
    suffix_seq.textChanged.connect(on_suffix_seq)

    lpr   = label("Prefix",    color=MUTED2, size=12); lpr.setFixedWidth(52)
    lcrop = label("→ Crop",    color=MUTED2, size=12); lcrop.setFixedWidth(52)
    lclip = label("→ Clip",    color=MUTED2, size=12); lclip.setFixedWidth(52)
    lseq  = label("→ Seq",     color=MUTED2, size=12); lseq.setFixedWidth(52)

    grid.addWidget(lpr,   0, 0); grid.addWidget(prefix,     0, 1)
    grid.addWidget(lcrop, 1, 0); grid.addWidget(suffix_crop, 1, 1)
    grid.addWidget(lclip, 2, 0); grid.addWidget(suffix_clip, 2, 1)
    grid.addWidget(lseq,  3, 0); grid.addWidget(suffix_seq,  3, 1)
    outer.addLayout(grid)
    return wrap, prefix, suffix_crop, suffix_clip, suffix_seq


def _make_scroll(inner: QWidget) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidget(inner)
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setStyleSheet(f"QScrollArea {{ background:{S1}; border:none; }}")
    scroll.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding,
    )
    return scroll
