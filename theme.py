# theme.py
from PyQt6.QtGui import QColor

# --- COLOR PALETTE --
COLORS = {
    "dark_bg": "#213448",      # Deep Charcoal Blue
    "medium_blue": "#547792",  # Muted Blue
    "light_blue": "#94B4C1",   # Soft Blue Grey
    "cream": "#EAE0CF",        # Off-White/Beige
    "white": "#FFFFFF",
    "danger": "#D9534F"        # Red
}

def get_stylesheet(is_dark_mode):
    if is_dark_mode:
        bg = COLORS["dark_bg"]
        text = COLORS["cream"]
        card = "#2C445C"
        btn = COLORS["medium_blue"]
        border = COLORS["medium_blue"]
        tab_bg = COLORS["dark_bg"]
        tab_active = COLORS["medium_blue"]
    else:
        bg = COLORS["cream"]
        text = COLORS["dark_bg"]
        card = COLORS["white"]
        btn = COLORS["medium_blue"]
        border = COLORS["light_blue"]
        tab_bg = "#DED5C5"
        tab_active = COLORS["white"]

    return f"""
        QMainWindow {{ background-color: {bg}; }}
        QLabel {{ color: {text}; }}
        QTextEdit {{
            background-color: {card}; color: {text};
            border: 2px solid {border}; border-radius: 10px;
            padding: 15px; font-family: 'Segoe UI', sans-serif; font-size: 14px;
        }}
        QTabWidget::pane {{ border: 2px solid {border}; border-radius: 10px; background-color: {card}; }}
        QTabBar::tab {{
            background-color: {tab_bg}; color: {text};
            padding: 10px 25px; margin-right: 4px;
            border-top-left-radius: 8px; border-top-right-radius: 8px;
        }}
        QTabBar::tab:selected {{ background-color: {tab_active}; border-bottom: 2px solid {tab_active}; }}
        QPushButton {{
            background-color: {btn}; color: {COLORS['cream']};
            border: none; border-radius: 8px; padding: 10px;
        }}
        QPushButton:hover {{ background-color: {COLORS['light_blue']}; color: {COLORS['dark_bg']}; }}
        #status_container {{ background-color: {card}; border-radius: 8px; border: 1px solid {border}; }}
    """