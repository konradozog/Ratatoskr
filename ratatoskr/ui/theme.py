"""Ratatoskr – Qt dark theme (based on mamrot v4 design)."""

# ── Color palette ────────────────────────────────────────────
BG        = "#0F0F0F"
SURFACE   = "#181818"
SURFACE2  = "#1F1F1F"
SURFACE3  = "#262626"
ELEVATED  = "#2C2C2C"

BORDER       = "rgba(255, 255, 255, 18)"
BORDER_HOVER = "rgba(255, 255, 255, 36)"

ACCENT       = "#F5A623"
ACCENT_LIGHT = "#FBC96C"
ACCENT_DIM   = "rgba(245, 166, 35, 26)"
ACCENT_GLOW  = "rgba(245, 166, 35, 46)"

TEXT  = "#E2DDD5"
TEXT2 = "#9B9590"
TEXT3 = "#5C5752"

SUCCESS     = "#7DD3A0"
SUCCESS_DIM = "rgba(125, 211, 160, 26)"
ERROR       = "#E87171"
ERROR_DIM   = "rgba(232, 113, 113, 26)"

REC_RED     = "#E05252"
REC_RED_DIM = "rgba(224, 82, 82, 30)"

# ── Spacing / radius ────────────────────────────────────────
SP_XS, SP_SM, SP_MD, SP_LG = 4, 8, 12, 16
R_SM, R_MD, R_LG, R_XL = 6, 8, 10, 12

# ── Font family ──────────────────────────────────────────────
FONT_FAMILY = '"DM Sans", "Segoe UI", "SF Pro Text", system-ui, sans-serif'
MONO_FAMILY = '"DM Mono", "SF Mono", Consolas, monospace'


def build_stylesheet() -> str:
    return f"""
    QWidget {{
        background-color: {BG};
        color: {TEXT};
        font-family: {FONT_FAMILY};
        font-size: 10pt;
    }}

    QLabel {{
        color: {TEXT};
        background: transparent;
    }}

    QPushButton {{
        background: {SURFACE2};
        color: {TEXT};
        border: 1px solid {BORDER};
        border-radius: {R_MD}px;
        padding: 8px 18px;
        font-weight: 500;
        font-size: 10pt;
    }}
    QPushButton:hover {{
        background: {SURFACE3};
        border-color: {BORDER_HOVER};
    }}
    QPushButton:pressed {{
        background: {ELEVATED};
    }}
    QPushButton:disabled {{
        color: {TEXT3};
        background: {SURFACE};
        border-color: {BORDER};
    }}

    QPushButton[accent="true"] {{
        background: {ACCENT};
        color: {BG};
        border: none;
        font-weight: 600;
        padding: 10px 22px;
        border-radius: {R_LG}px;
    }}
    QPushButton[accent="true"]:hover {{
        background: {ACCENT_LIGHT};
    }}

    QComboBox {{
        background: {SURFACE3};
        color: {TEXT};
        border: 1px solid {BORDER};
        border-radius: {R_MD}px;
        padding: 7px 12px;
        font-size: 9pt;
    }}
    QComboBox:focus {{
        border: 1px solid {ACCENT};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 26px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {TEXT2};
        margin-right: 8px;
    }}
    QComboBox QAbstractItemView {{
        background: {ELEVATED};
        color: {TEXT};
        selection-background-color: {ACCENT_DIM};
        border: 1px solid {BORDER_HOVER};
        border-radius: {R_MD}px;
        padding: 4px;
        outline: none;
    }}

    QCheckBox {{
        color: {TEXT};
        spacing: 8px;
        font-size: 9pt;
    }}
    QCheckBox::indicator {{
        width: 16px; height: 16px;
        border: 1px solid {BORDER_HOVER};
        border-radius: 4px;
        background: {SURFACE3};
    }}
    QCheckBox::indicator:checked {{
        background: {ACCENT};
        border-color: {ACCENT};
    }}

    QProgressBar {{
        background: {SURFACE3};
        border: none;
        border-radius: 3px;
        height: 5px;
        text-align: center;
        color: transparent;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {ACCENT}, stop:1 {ACCENT_LIGHT});
        border-radius: 3px;
    }}

    QToolTip {{
        background: {ELEVATED};
        color: {TEXT};
        border: 1px solid {BORDER_HOVER};
        padding: 6px 10px;
        border-radius: {R_SM}px;
        font-size: 8pt;
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background: {SURFACE3};
        border-radius: 3px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {TEXT3};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    """
