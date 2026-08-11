"""اختبارات الصفحات (M3.4): محرر الفصول المربوط بـ BookState (offscreen)."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.models import Book, Chapter
from app.state import BookState
from app.ui.pages import ChapterEditor, build_pages

app = QApplication.instance() or QApplication([])


def _state() -> BookState:
    b = Book()
    b.add_chapter(Chapter(title="فصل أ", body="نص أ."))
    b.add_chapter(Chapter(title="فصل ب", body="نص ب."))
    return BookState(book=b)


def test_build_pages_has_editor():
    pages = build_pages(BookState())
    assert "editor" in pages


def test_editor_lists_chapters():
    editor = ChapterEditor(_state())
    assert editor.chapter_list.count() == 2
    assert editor.chapter_list.item(0).text() == "فصل أ"


def test_selecting_chapter_loads_into_editors():
    editor = ChapterEditor(_state())
    editor.chapter_list.setCurrentRow(1)
    assert editor.title_edit.text() == "فصل ب"
    assert editor.body_edit.toPlainText() == "نص ب."


def test_editing_body_updates_state():
    editor = ChapterEditor(_state())
    editor.body_edit.setPlainText("نص مُحدّث.")
    assert editor.state.current_chapter().body == "نص مُحدّث."


def test_editing_title_updates_state():
    editor = ChapterEditor(_state())
    editor.state.select_chapter(1)
    editor.reload()
    editor.title_edit.setText("عنوان جديد")
    assert editor.state.current_chapter().title == "عنوان جديد"