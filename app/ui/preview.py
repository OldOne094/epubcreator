"""معاينة الفصول/الكتاب داخل QTextBrowser.

يتضمن:
- أدوات نقيّة (قابلة للاختبار): `chapter_to_html` / `book_to_html`.
- `PreviewPage`: صفحة كاملة بمحدّد الفصل + اتجاه + عرض الكتاب كاملًا.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.models import Book, Chapter
from app.core.format import body_to_html, escape as _escape_text
from app.ui.widgets import PageHeader

_CSS_RTL = """
body { direction: rtl; font-family: 'Amiri', serif; line-height: 1.8; }
h1   { font-family: 'Amiri', serif; margin-bottom: 0.5em; }
p    { text-align: justify; margin: 0 0 1em; }
"""


def split_paragraphs(body: str) -> list[str]:
    """تقسيم الجسم إلى فقرات عبر خوارزمية التنسيق العربي متعددة الطبقات."""
    from app.core.format import split_paragraphs as _split

    return _split(body)


def _options_css(options) -> str:  # noqa: ANN001
    """CSS الكتاب الحقيقي (نفس المولّد) للمعاينة المطابقة للتصدير."""
    from app.core.templates import build_css

    try:
        return build_css(options)
    except Exception:  # noqa: BLE001 — أي خطأ CSS يرجّع الأساس
        return _CSS_RTL


def chapter_to_html(ch: Chapter, direction: str = "rtl") -> str:
    """فصل واحد → HTML داخلي (بلا الغلاف الكامل)."""
    title = f"<h1>{_escape_text(ch.title)}</h1>" if ch.title.strip() else ""
    return f"<body dir='{direction}'>{title}{body_to_html(ch.body, direction)}</body>"


def book_to_html(book: Book, start: int = 0, count: int | None = None, options=None) -> str:  # noqa: ANN001
    """كتاب (من فهرس إلى عدد) → HTML كامل بتهيئة RTL وCSS (أو الأساس عند غيابه)."""
    chapters = book.chapters[start : start + count] if count else book.chapters[start:]
    inner = "\n".join(chapter_to_html(c, book.options.direction) for c in chapters)
    css = _options_css(options) if options is not None else _CSS_RTL
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{css}</style></head>{inner}</html>"


class Preview:
    """يعرض فصًّا أو كتابًا في QTextBrowser."""

    def __init__(self) -> None:
        self.view = QTextBrowser()

    def show_chapter(self, ch: Chapter, direction: str = "rtl") -> None:
        self.view.setHtml(chapter_to_html(ch, direction))

    def show_book(self, book: Book, start: int = 0, count: int | None = None, options=None) -> None:  # noqa: ANN001
        self.view.setHtml(book_to_html(book, start, count, options))


class PreviewPage(QWidget):
    """صفحة المعاينة: محدد فصل + اتجاه + عرض الكتاب كاملًا، مربوط بـ BookState."""

    def __init__(self, state, view: QTextBrowser | None = None) -> None:  # noqa: ANN001
        super().__init__()
        self.state = state
        self._last_count = -1

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 18, 24, 18)
        outer.setSpacing(14)
        outer.addWidget(PageHeader("المعاينة", "عرض حي لشكل الكتاب قبل التصدير — بنفس CSS المولّد."))

        self.view = view or QTextBrowser()

        controls = QHBoxLayout()
        controls.setSpacing(10)
        controls.addWidget(QLabel("عرض:"))
        self.chapter_combo = QComboBox()
        self.chapter_combo.currentIndexChanged.connect(self._on_changed)
        controls.addWidget(self.chapter_combo)
        controls.addStretch(1)
        controls.addWidget(QLabel("الاتجاه:"))
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["من اليمين (RTL)", "من اليسار (LTR)"])
        self.direction_combo.currentIndexChanged.connect(self._on_direction)
        controls.addWidget(self.direction_combo)
        outer.addLayout(controls)
        outer.addWidget(self.view, 1)

        self.refresh()

    def _direction(self) -> str:
        return "rtl" if self.direction_combo.currentIndex() == 0 else "ltr"

    def _on_direction(self) -> None:
        self.state.book.options.direction = self._direction()
        self.refresh(keep_selection=True)

    def _on_changed(self) -> None:
        self.refresh(keep_selection=True)

    def refresh(self, keep_selection: bool = False) -> None:
        """إعادة بناء قائمة الفصول (عند تغيّر عددها فقط) وإعادة رسم المعاينة."""
        book = self.state.book
        count = len(book.chapters)
        if count != self._last_count:
            self._last_count = count
            prev = self.chapter_combo.currentIndex() if keep_selection else 0
            self.chapter_combo.blockSignals(True)
            self.chapter_combo.clear()
            self.chapter_combo.addItem("الكتاب كاملًا")
            for ch in book.chapters:
                self.chapter_combo.addItem(ch.title or "(بلا عنوان)")
            self.chapter_combo.setCurrentIndex(prev if 0 <= prev < self.chapter_combo.count() else 0)
            self.chapter_combo.blockSignals(False)

        direction = self._direction()
        if not book.chapters:
            self.view.setHtml(
                "<html><body dir='rtl'><p style='color:#8b8172; font-size:15px;'>"
                "استورد كتابًا أولًا لعرض المعاينة هنا.</p></body></html>"
            )
            return
        index = self.chapter_combo.currentIndex()
        options = book.options
        if index <= 0:
            self.view.setHtml(book_to_html(book, options=options))
        else:
            self.view.setHtml(
                book_to_html(book, start=index - 1, count=1, options=options)
            )
