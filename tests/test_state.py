"""اختبارات BookState (M3.1)."""
from __future__ import annotations

from app.models import Book, Chapter
from app.state import BookState


def _book(n: int = 3) -> Book:
    b = Book()
    for i in range(n):
        b.add_chapter(Chapter(title=f"فصل {i}", body=f"نص {i}."))
    return b


def test_set_book_resets_index():
    s = BookState(book=_book(2), current_index=1)
    s.set_book(_book(4))
    assert s.current_index == 0
    assert len(s.book.chapters) == 4


def test_current_chapter():
    s = BookState(book=_book())
    assert s.current_chapter().title == "فصل 0"


def test_select_chapter_clamps():
    s = BookState(book=_book())
    s.select_chapter(99)  # خارج النطاق: يبقى كما هو
    assert s.current_index == 0
    s.select_chapter(2)
    assert s.current_index == 2


def test_update_current_body_modifies_and_notifies():
    events = []
    s = BookState(book=_book())
    s.set_on_change(lambda: events.append("changed") if len(events) == 0 else None)
    # أعد ضبط المستمع بحيث يعدّ كل تغيير
    events.clear()
    s._on_change = lambda: events.append("change")

    s.update_current_body("جسم جديد.")
    assert s.current_chapter().body == "جسم جديد."
    assert events == ["change"]

    # نفس القيمة لا تُشغّل إشعارًا
    s.update_current_body("جسم جديد.")
    assert events == ["change"]


def test_update_current_title():
    s = BookState(book=_book())
    s.update_current_title("عنوان محدّث")
    assert s.current_chapter().title == "عنوان محدّث"


def test_empty_book_has_no_current_chapter():
    s = BookState(book=Book())
    assert s.current_chapter() is None