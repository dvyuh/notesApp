# theme.py
from PyQt6.QtGui import QColor

# --- COLOR PALETTE ---
COLORS = {
    "dark_bg":      "#0F1B2D",   # Deep Navy
    "medium_blue":  "#1E3A5F",   # Medical Blue
    "panel":        "#162032",   # Slightly lighter panel
    "light_blue":   "#4A90C4",   # Accent Blue
    "cream":        "#E8EDF2",   # Off-White
    "white":        "#FFFFFF",
    "danger":       "#D9534F",   # Alert Red
    "success":      "#27AE60",   # Confirmation Green
    "warning":      "#F39C12",   # Caution Amber
    # --- Medical-specific ---
    "pulse_red":    "#E74C3C",   # Active listening / urgent
    "soft_blue":    "#5DADE2",   # Active field highlight (listening mode)
    "muted_text":   "#8FA8BE",   # Secondary / placeholder text
    "border":       "#2C4A6E",   # Default border
    "active_border":"#5DADE2",   # Active/listening field border
    "confirm_bg":   "#1A3A2A",   # Confirmation overlay bg
}

def get_stylesheet(is_dark_mode):
    if is_dark_mode:
        bg        = COLORS["dark_bg"]
        text      = COLORS["cream"]
        card      = COLORS["panel"]
        btn       = COLORS["medium_blue"]
        border    = COLORS["border"]
        tab_bg    = COLORS["dark_bg"]
        tab_active= COLORS["medium_blue"]
        input_bg  = "#1A2E44"
        muted     = COLORS["muted_text"]
    else:
        bg        = "#EEF3F8"
        text      = "#0F1B2D"
        card      = "#FFFFFF"
        btn       = COLORS["medium_blue"]
        border    = "#B0C8E0"
        tab_bg    = "#DDE7F0"
        tab_active= "#FFFFFF"
        input_bg  = "#F7FAFD"
        muted     = "#6A8FAD"

    return f"""
        /* ── Global ── */
        QMainWindow  {{ background-color: {bg}; }}
        QWidget      {{ background-color: transparent; }}
        QLabel       {{ color: {text}; font-family: 'Segoe UI', sans-serif; }}

        /* ── Scroll bars ── */
        QScrollBar:vertical {{
            background: {card}; width: 8px; border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {border}; border-radius: 4px;
        }}

        /* ── Input fields (QLineEdit) ── */
        QLineEdit {{
            background-color: {input_bg};
            color: {text};
            border: 2px solid {border};
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 13px;
            font-family: 'Consolas', 'Courier New', monospace;
        }}
        QLineEdit:focus {{
            border: 2px solid {COLORS['light_blue']};
        }}
        /* Active-listening state applied programmatically via setObjectName */
        QLineEdit[listening="true"] {{
            border: 2px solid {COLORS['soft_blue']};
            background-color: #0E2038;
        }}

        /* ── Text areas ── */
        QTextEdit {{
            background-color: {card};
            color: {text};
            border: 2px solid {border};
            border-radius: 8px;
            padding: 10px;
            font-size: 13px;
            font-family: 'Segoe UI', sans-serif;
        }}
        QTextEdit:focus {{
            border: 2px solid {COLORS['light_blue']};
        }}

        /* ── Buttons ── */
        QPushButton {{
            background-color: {btn};
            color: {COLORS['cream']};
            border: none;
            border-radius: 6px;
            padding: 8px 14px;
            font-size: 12px;
            font-family: 'Segoe UI', sans-serif;
        }}
        QPushButton:hover {{
            background-color: {COLORS['light_blue']};
            color: {COLORS['dark_bg']};
        }}
        QPushButton:disabled {{
            background-color: #2A3A4A;
            color: #556677;
        }}
        QPushButton#record_btn {{
            background-color: {COLORS['medium_blue']};
            font-size: 13px;
            font-weight: bold;
        }}
        QPushButton#save_new_btn {{
            background-color: {COLORS['success']};
            color: white;
            font-weight: bold;
        }}
        QPushButton#save_new_btn:hover {{
            background-color: #2ECC71;
        }}
        QPushButton#override_btn {{
            background-color: #2A3A4A;
            color: {muted};
            border: 1px solid {border};
            padding: 4px 8px;
            font-size: 10px;
        }}
        QPushButton#override_btn[active="true"] {{
            background-color: {COLORS['warning']};
            color: white;
        }}

        /* ── Tab Widget ── */
        QTabWidget::pane {{
            border: 2px solid {border};
            border-radius: 8px;
            background-color: {card};
        }}
        QTabBar::tab {{
            background-color: {tab_bg};
            color: {muted};
            padding: 8px 20px;
            margin-right: 3px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }}
        QTabBar::tab:selected {{
            background-color: {tab_active};
            color: {text};
            border-bottom: 2px solid {COLORS['soft_blue']};
        }}

        /* ── Status / info containers ── */
        #status_container {{
            background-color: {card};
            border-radius: 8px;
            border: 1px solid {border};
            padding: 4px;
        }}
        #section_card {{
            background-color: {card};
            border: 1px solid {border};
            border-radius: 8px;
        }}
        #patient_list_panel {{
            background-color: {card};
            border: 1px solid {border};
            border-radius: 8px;
        }}

        /* ── Progress bar ── */
        QProgressBar {{
            border: 1px solid {border};
            border-radius: 4px;
            background-color: {card};
            height: 8px;
            text-align: center;
        }}
        QProgressBar::chunk {{
            background-color: {COLORS['soft_blue']};
            border-radius: 4px;
        }}

        /* ── List Widget (patient list) ── */
        QListWidget {{
            background-color: {input_bg};
            color: {text};
            border: 1px solid {border};
            border-radius: 6px;
            font-size: 12px;
        }}
        QListWidget::item:selected {{
            background-color: {COLORS['medium_blue']};
            color: white;
        }}
        QListWidget::item:hover {{
            background-color: #1E3550;
        }}

        /* ── ComboBox ── */
        QComboBox {{
            background-color: {input_bg};
            color: {text};
            border: 2px solid {border};
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 13px;
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background-color: {card};
            color: {text};
            selection-background-color: {COLORS['medium_blue']};
        }}

        /* ── Splitter ── */
        QSplitter::handle {{
            background-color: {border};
        }}

        /* ── Tooltips ── */
        QToolTip {{
            background-color: {COLORS['medium_blue']};
            color: white;
            border: 1px solid {COLORS['light_blue']};
            padding: 4px;
            border-radius: 4px;
        }}
    """