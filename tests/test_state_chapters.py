"""اختبارات إدارة الفصول في BookState (إضافة/حذف/نقل)."""
from __future__ import annotations

from app.models import Book, Chapter
from app.state import BookState


def _state(n: int = 3) -> BookState:
    b = Book()
    for i in range(n):
        b.add_chapter(Chapter(title=f"فصل {i}", body=f"نص {i}."))
    return BookState(book=b)


def test_add_chapter_appends_and_selects():
    s = _state(2)
    s.add_chapter()
    assert len(s.book.chapters) == 3
    assert s.current_index == 2
    assert s.current_chapter().title == ""


def test_add_chapter_inserts_at_index():
    s = _state(3)
    s.add_chapter(Chapter(title="بين"), index=1)
    assert [c.title for c in s.book.chapters] == ["فصل 0", "بين", "فصل 1", "فصل 2"]
    assert s.current_index == 1


def test_remove_chapter_current():
    s = _state(3)
    s.select_chapter(1)
    s.remove_chapter()
    assert [c.title for c in s.book.chapters] == ["فصل 0", "فصل 2"]
    assert s.current_index == 1


def test_remove_last_chapter_adjusts_index():
    s = _state(2)
    s.select_chapter(1)
    s.remove_chapter()
    assert s.current_index == 0
    assert s.current_chapter().title == "فصل 0"


def test_remove_from_empty_is_noop():
    s = BookState(book=Book())
    s.remove_chapter()
    assert s.book.chapters == []


def test_move_chapter_down():
    s = _state(3)
    s.select_chapter(0)
    s.move_chapter(0, 2)
    assert [c.title for c in s.book.chapters] == ["فصل 1", "فصل 2", "فصل 0"]
    assert s.current_index == 2


def test_move_chapter_out_of_range_noop():
    s = _state(2)
    s.move_chapter(0, 9)
    assert [c.title for c in s.book.chapters] == ["فصل 0", "فصل 1"]


def test_has_chapters():
    assert _state().has_chapters is True
    assert BookState(book=Book()).has_chapters is False


def test_notify_manual():
    events = []
    s = _state(1)
    s.set_on_change(lambda: events.append(1))
    s.notify()
    assert events == [1]
