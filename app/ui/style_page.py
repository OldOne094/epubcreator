"""صفحة التنسيق والقالب: قوالب جاهزة + خطوط + تنسيق فقرة + CSS مخصص.

تُعدّل `options` مباشرةً (EpubOptions/ParagraphFormat) ليشارك المولّد
والمعاينة النتيجة نفسها.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QColorDialog,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import app.core.templates as core_templates
from app.models import ParagraphFormat
from app.state import BookState
from app.ui.widgets import PageHeader, Section, muted_label

_ALIGNMENTS = (
    ("justify", "مضبوط (justify)"),
    ("right", "يمين"),
    ("center", "وسط"),
    ("left", "يسار"),
)

_LINE_HEIGHTS = ("1.5", "1.6", "1.8", "2.0", "2.2", "2.5")
_SPACINGS = ("0.5em", "0.75em", "1em", "1.2em", "1.5em")
_INDENTS = ("0", "1em", "1.5em", "2em", "2.5em")
_FONT_SIZES = ("0.9em", "1em", "1.1em", "1.15em", "1.25em")
_MARGINS = ("0", "0.5em", "1em", "1.5em", "2em")
_FONT_FAMILIES = (
    "Amiri",
    "Traditional Arabic",
    "Arial",
    "Times New Roman",
    "Tahoma",
    "Segoe UI",
)


def _combo(items: list[str]) -> QComboBox:
    box = QComboBox()
    box.addItems(items)
    return box


def _select(box: QComboBox, value: str) -> None:
    idx = box.findText(value)
    box.setCurrentIndex(idx if idx >= 0 else 0)


class StylePage(QWidget):
    """صفحة التنسيق مرتبطة بخيارات الكتاب (`state.book.options`)."""

    def __init__(self, state: BookState) -> None:
        super().__init__()
        self.state = state
        self._loading = False
        self._template_buttons: dict[str, QPushButton] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 18, 24, 18)
        outer.setSpacing(14)
        outer.addWidget(
            PageHeader("التنسيق والقالب", "القوالب الجاهزة والتنسيق يسريان على المعاينة والتصدير معًا.")
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(14)

        self._build_template_section(body_layout)
        self._build_font_section(body_layout)
        self._build_paragraph_section(body_layout)
        self._build_custom_css_section(body_layout)

        body_layout.addStretch(1)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        self.reload()

    # ------------------------------------------------------------ قالب ---
    def _build_template_section(self, parent: QVBoxLayout) -> None:
        section = Section("القالب الجاهز", "خمسة قوالب جاهزة؛ ألوان القالب تنتقل تلقائيًّا إلى الغلاف.")
        grid = QHBoxLayout()
        grid.setSpacing(10)
        group = QButtonGroup(self)
        group.setExclusive(True)
        for name in core_templates.template_names():
            btn = QPushButton(core_templates.template_label(name))
            btn.setObjectName("Template")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(64)
            btn.clicked.connect(lambda _=False, n=name: self._select_template(n))
            group.addButton(btn)
            self._template_buttons[name] = btn
            grid.addWidget(btn, 1)
        section.layout.addLayout(grid)
        self.template_hint = muted_label("")
        section.layout.addWidget(self.template_hint)
        parent.addWidget(section)

    def _select_template(self, name: str) -> None:
        if self._loading:
            return
        self.state.book.options.template = name
        self.template_hint.setText(f"القالب: {core_templates.template_label(name)}")
        self._on_changed()

    # ------------------------------------------------------------ خطوط ---
    def _build_font_section(self, parent: QVBoxLayout) -> None:
        section = Section("الخطوط", "خط العناوين وخط النص داخل الكتاب.")
        form = QFormLayout()
        form.setSpacing(10)
        self.title_font = _combo(list(_FONT_FAMILIES))
        self.body_font = _combo(list(_FONT_FAMILIES))
        self.title_font.currentTextChanged.connect(self._on_fonts)
        self.body_font.currentTextChanged.connect(self._on_fonts)
        form.addRow(QLabel("خط العناوين"), self.title_font)
        form.addRow(QLabel("خط النص"), self.body_font)
        section.layout.addLayout(form)
        parent.addWidget(section)

    def _on_fonts(self) -> None:
        if self._loading:
            return
        opts = self.state.book.options
        opts.title_font = self.title_font.currentText()
        opts.body_font = self.body_font.currentText()
        self._on_changed()

    # ------------------------------------------------------- فقرة/خط ---
    def _build_paragraph_section(self, parent: QVBoxLayout) -> None:
        section = Section("تنسيق الفقرة", "التحكم في المحاذاة وارتفاع السطر والمسافات والإزاحة.")
        form = QFormLayout()
        form.setSpacing(10)
        form.setHorizontalSpacing(18)

        self.alignment = _combo([label for _, label in _ALIGNMENTS])
        self.line_height = _combo(list(_LINE_HEIGHTS))
        self.spacing_after = _combo(list(_SPACINGS))
        self.first_indent = _combo(list(_INDENTS))
        self.font_size = _combo(list(_FONT_SIZES))
        self.margin_top = _combo(list(_MARGINS))
        self.margin_bottom = _combo(list(_MARGINS))
        self.color_button = QPushButton("لون الفقرة")
        self.color_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_button.clicked.connect(self._pick_color)

        for box in (
            self.alignment, self.line_height, self.spacing_after,
            self.first_indent, self.font_size, self.margin_top, self.margin_bottom,
        ):
            box.currentIndexChanged.connect(self._on_paragraph)

        form.addRow(QLabel("المحاذاة"), self.alignment)
        form.addRow(QLabel("ارتفاع السطر"), self.line_height)
        form.addRow(QLabel("مسافة بعد الفقرة"), self.spacing_after)
        form.addRow(QLabel("إزاحة السطر الأول"), self.first_indent)
        form.addRow(QLabel("حجم الخط"), self.font_size)
        form.addRow(QLabel("هامش أعلى"), self.margin_top)
        form.addRow(QLabel("هامش أسفل"), self.margin_bottom)
        form.addRow(QLabel("اللون"), self.color_button)

        two_col = QHBoxLayout()
        first = QVBoxLayout()
        first.addLayout(form)
        two_col.addLayout(first, 2)
        section.layout.addLayout(two_col)
        parent.addWidget(section)

    def _pick_color(self) -> None:
        current = self.state.book.options.paragraph.color
        color = QColorDialog.getColor(QColor(current) if current else QColor("#000000"), self, "لون الفقرة")
        if color.isValid():
            self.state.book.options.paragraph.color = color.name()
            self._refresh_color_button()
            self._on_paragraph()

    def _refresh_color_button(self) -> None:
        value = self.state.book.options.paragraph.color
        self.color_button.setText(value or "لون الفقرة (افتراضي)")
        if value:
            self.color_button.setStyleSheet(f"background: {value}; color: #ffffff; border: none;")

    def _on_paragraph(self) -> None:
        if self._loading:
            return
        pf = self.state.book.options.paragraph
        pf.alignment = _ALIGNMENTS[self.alignment.currentIndex()][0]
        pf.line_height = self.line_height.currentText()
        pf.spacing_after = self.spacing_after.currentText()
        pf.first_line_indent = self.first_indent.currentText()
        pf.font_size = self.font_size.currentText()
        pf.margin_top = self.margin_top.currentText()
        pf.margin_bottom = self.margin_bottom.currentText()
        self._on_changed()

    # ------------------------------------------------------ CSS مخصص ---
    def _build_custom_css_section(self, parent: QVBoxLayout) -> None:
        section = Section("CSS مخصص", "أضف أنماطك الخاصة؛ تُضاف فوق القالب (متقدّم).")
        self.custom_css = QPlainTextEdit()
        self.custom_css.setPlaceholderText("/* مثال: */\nbody { color: #333; }\nh1 { letter-spacing: 1px; }")
        self.custom_css.setMinimumHeight(130)
        self.custom_css.textChanged.connect(self._on_custom_css)
        section.layout.addWidget(self.custom_css)
        parent.addWidget(section)

    def _on_custom_css(self) -> None:
        if self._loading:
            return
        self.state.book.options.custom_css = self.custom_css.toPlainText()
        self._on_changed()

    # ----------------------------------------------------------- ربط ---
    def reload(self) -> None:
        self._loading = True
        opts = self.state.book.options
        pf: ParagraphFormat = opts.paragraph

        for name, btn in self._template_buttons.items():
            btn.setChecked(name == (opts.template or "novel-ar"))
        self.template_hint.setText(
            f"القالب: {core_templates.template_label(opts.template or 'novel-ar')}"
        )

        _select(self.title_font, opts.title_font)
        _select(self.body_font, opts.body_font)

        align_idx = next((i for i, (code, _) in enumerate(_ALIGNMENTS) if code == pf.alignment), 0)
        self.alignment.setCurrentIndex(align_idx)
        _select(self.line_height, pf.line_height)
        _select(self.spacing_after, pf.spacing_after)
        _select(self.first_indent, pf.first_line_indent)
        _select(self.font_size, pf.font_size)
        _select(self.margin_top, pf.margin_top)
        _select(self.margin_bottom, pf.margin_bottom)
        self._refresh_color_button()

        self.custom_css.setPlainText(opts.custom_css)
        self._loading = False

    def _on_changed(self) -> None:
        """إبلاغ النافذة الرئيسية لتحديث المعاينة والبيانات التابعة."""
        if hasattr(self.state, "notify"):
            self.state.notify()
