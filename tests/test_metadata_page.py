"""اختبارات محرر البيانات الوصفية (M5.3) — offscreen."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.models import Book, Metadata
from app.state import BookState
from app.ui.pages import MetadataPage, build_pages

app = QApplication.instance() or QApplication([])


def test_metadata_page_in_pages():
    pages = build_pages(BookState())
    assert "metadata" in pages


def test_metadata_page_loads_values():
    b = Book(metadata=Metadata(title="كتاب", author="مؤلف", language="en"))
    page = MetadataPage(BookState(book=b))
    assert page._fields["title"].text() == "كتاب"
    assert page._fields["author"].text() == "مؤلف"
    assert page.language.currentData() == "en"


def test_editing_writes_back_to_state():
    b = Book(metadata=Metadata(title="قديم"))
    state = BookState(book=b)
    page = MetadataPage(state)
    page._fields["title"].setText("عنوان جديد")
    page._fields["publisher"].setText("دار النشر")
    assert state.book.metadata.title == "عنوان جديد"
    assert state.book.metadata.publisher == "دار النشر"