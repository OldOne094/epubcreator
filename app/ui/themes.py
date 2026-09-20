"""ثيمات QSS (داكن/فاتح) بألوان محايدة دافئة تناسب أداة صناعة الكتب.

تصميم معاصر: لوحة فاتحة بلون الورق، سطوح بيضاء، حافة ذهبية (accent)،
وعناصر تنقّل كبيرة سهلة الاستخدام. كل الألوان مترجمة إلى "توكنات" (tokens)
تُستخدم من الثيمين معًا لضمان الاتساق.
"""
from __future__ import annotations

from PySide6.QtGui import QFont

# ------------------------------------------------------------------ tokens ---

_LIGHT = {
    "bg": "#f4f1ea",          # خلفية النافذة (لون ورق دافئ)
    "surface": "#ffffff",     # البطاقات والحقول
    "surface_alt": "#ece7dc", # تمرير/ثانوي
    "border": "#e0d9ca",      # حدود الحقول
    "text": "#2b2620",        # النص الأساسي
    "muted": "#6f675c",       # نص ثانوي (تباين AA على الأبيض)
    "accent": "#a8761d",      # الذهبي الأساسي (زخرفة/حدود)
    "accent_dark": "#8a5f12",
    "accent_text": "#8a5f12", # نص ذهبي على الفاتح (تباين AA)
    "primary": "#8a5f12",     # خلفية الزر الأساسي (أبيض عليها AA)
    "primary_hover": "#6f4c0e",
    "accent_soft": "#f5ecd4", # خلفية التحديد
    "danger": "#b5452f",
    "ok": "#2e7d46",
}

_DARK = {
    "bg": "#16171a",
    "surface": "#1e2026",
    "surface_alt": "#272a31",
    "border": "#34383f",
    "text": "#e9e7e1",
    "muted": "#9a9ca4",
    "accent": "#d9a441",
    "accent_dark": "#e0b257",
    "accent_text": "#e8bd63", # نص ذهبي على الداكن (تباين AA)
    "primary": "#d9a441",     # خلفية الزر الأساسي (نص داكن عليها AA)
    "primary_text": "#1c1a15",
    "primary_hover": "#e8bd63",
    "accent_soft": "#322916",
    "danger": "#e0634e",
    "ok": "#4da06a",
}


def tokens(name: str) -> dict[str, str]:
    """عودة توكنات الثيم (فاتح/داكن)."""
    return _DARK if name == "dark" else _LIGHT


def _base(t: dict[str, str]) -> str:
    primary_text = t.get("primary_text", "#ffffff")
    return f"""
* {{ font-size: 13px; }}
QMainWindow, QDialog {{ background: {t['bg']}; }}
QWidget {{ color: {t['text']}; }}
QToolTip {{ background: {t['surface']}; color: {t['text']}; border: 1px solid {t['border']}; border-radius: 6px; padding: 5px 8px; }}
QStatusBar {{ background: {t['bg']}; color: {t['muted']}; }}
QStatusBar::item {{ border: none; }}
QMenuBar {{ background: {t['bg']}; color: {t['text']}; }}
QMenuBar::item {{ background: transparent; padding: 6px 10px; border-radius: 6px; }}
QMenuBar::item:selected {{ background: {t['surface_alt']}; }}
QMenu {{ background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 8px; padding: 6px; }}
QMenu::item {{ padding: 8px 22px; border-radius: 6px; }}
QMenu::item:selected {{ background: {t['accent_soft']}; color: {t['accent_text']}; }}

QLabel {{ background: transparent; }}
QLabel#Muted {{ color: {t['muted']}; font-size: 12.5px; }}
QLabel#PageTitle {{ font-size: 21px; font-weight: 600; }}
QLabel#PageDesc {{ color: {t['muted']}; font-size: 13px; }}
QLabel#SectionTitle {{ font-size: 15px; font-weight: 600; }}
QLabel#SectionDesc {{ color: {t['muted']}; font-size: 12px; }}
QLabel#EmptyTitle {{ font-size: 20px; font-weight: 600; }}
QLabel#EmptyHint {{ color: {t['muted']}; font-size: 13.5px; }}
QLabel#Badge {{ background: {t['accent_soft']}; color: {t['accent_text']}; border-radius: 9px; padding: 3px 10px; font-weight: 600; font-size: 11.5px; }}

QFrame#Card {{ background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 12px; }}
QFrame#Banner {{ background: {t['accent_soft']}; border: 1px solid {t['accent']}; border-radius: 10px; }}
QFrame#ErrorBanner {{ background: {t['accent_soft']}; border: 1px solid {t['danger']}; border-radius: 10px; }}
QFrame#Divider {{ background: {t['border']}; border: none; max-height: 1px; }}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 8px;
    padding: 6px 10px; selection-background-color: {t['accent']}; selection-color: #ffffff;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {t['accent']};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 8px;
    selection-background-color: {t['accent_soft']}; selection-color: {t['accent']};
}}

QPushButton {{
    background: {t['surface']}; color: {t['text']}; border: 1px solid {t['border']};
    border-radius: 8px; padding: 7px 14px; font-weight: 500;
}}
QPushButton:hover {{ background: {t['surface_alt']}; }}
QPushButton:pressed {{ background: {t['border']}; }}
QPushButton:disabled {{ color: {t['muted']}; border-color: {t['border']}; }}
QPushButton:focus {{ border: 2px solid {t['accent']}; }}
QPushButton#Primary {{
    background: {t['primary']}; color: {primary_text}; border: none; font-weight: 600; padding: 9px 20px;
}}
QPushButton#Primary:hover {{ background: {t['primary_hover']}; }}
QPushButton#Primary:pressed {{ background: {t['primary_hover']}; }}
QPushButton#Primary:disabled {{ background: {t['border']}; color: {t['muted']}; }}
QPushButton#Primary:focus {{ border: 2px solid {t['accent']}; }}
QPushButton#Ghost {{ background: transparent; border: none; color: {t['accent']}; padding: 6px 10px; }}
QPushButton#Ghost:hover {{ color: {t['accent_dark']}; background: transparent; }}
QPushButton#Danger {{ background: transparent; border: 1px solid {t['danger']}; color: {t['danger']}; }}
QPushButton#Danger:hover {{ background: {t['accent_soft']}; }}
QPushButton#Nav {{
    text-align: right; background: transparent; border: none; border-radius: 8px;
    padding: 11px 14px; font-size: 13.5px; color: {t['text']};
}}
QPushButton#Nav:hover {{ background: {t['surface_alt']}; }}
QPushButton#Nav:checked {{ background: {t['accent_soft']}; color: {t['accent_text']}; font-weight: 600; }}
QPushButton#Template {{
    background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 10px;
    padding: 12px; text-align: center; font-weight: 500;
}}
QPushButton#Template:hover {{ border-color: {t['accent']}; }}
QPushButton#Template:checked {{ border: 2px solid {t['accent']}; background: {t['accent_soft']}; color: {t['accent_text']}; }}

QListWidget {{ background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 10px; outline: 0; padding: 4px; }}
QListWidget:focus {{ border: 1px solid {t['accent']}; }}
QListWidget::item {{ padding: 9px 12px; border-radius: 7px; }}
QListWidget::item:selected {{ background: {t['accent_soft']}; color: {t['accent_text']}; }}
QListWidget::item:hover {{ background: {t['surface_alt']}; }}

QTextBrowser {{
    background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 10px; padding: 14px;
}}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {t['border']}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {t['muted']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {t['border']}; border-radius: 5px; min-width: 30px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QSplitter::handle {{ background: {t['border']}; }}
QSplitter::handle:horizontal {{ width: 6px; }}
QSplitter::handle:vertical {{ height: 6px; }}
QProgressBar {{ background: {t['surface_alt']}; border: none; border-radius: 6px; text-align: center; }}
QProgressBar::chunk {{ background: {t['accent']}; border-radius: 6px; }}
QCheckBox, QRadioButton {{ spacing: 8px; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 17px; height: 17px; }}
"""


LIGHT = _base(_LIGHT)
DARK = _base(_DARK)


def stylesheet(name: str) -> str:
    return {"light": LIGHT, "dark": DARK}.get(name, LIGHT)


def apply_theme(app, name: str) -> None:  # noqa: ANN001
    """تطبيق الثيم (بالتوكنات) مع خط النظام الافتراضي (لا فرض لاتيني يكسر العربية)."""
    app.setFont(QFont())
    app.setStyleSheet(stylesheet(name))
