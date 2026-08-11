"""اختبارات التراجع/الإعادة الهيكلية في BookState (B6)."""
from __future__ import annotations

from app.models import Book, Chapter
from app.state import BookState


def _book(n: int = 2) -> Book:
    b = Book()
    for i in range(n):
        b.add_chapter(Chapter(title=f"فصل {i}", body=f"نص {i}."))
    return b


def test_undo_restores_removed_chapter():
    s = BookState(book=_book())
    s.remove_chapter(0)
    assert len(s.book.chapters) == 1
    s.undo()
    assert len(s.book.chapters) == 2
    assert s.book.chapters[0].title == "فصل 0"


def test_undo_restores_snapshot_content():
    s = BookState(book=_book())
    s.book.chapters[0].body = "معدّل"
    s.remove_chapter(0)
    s.undo()
    assert s.book.chapters[0].body == "معدّل"


def test_redo_after_undo():
    s = BookState(book=_book())
    s.remove_chapter(0)
    s.undo()
    s.redo()
    assert len(s.book.chapters) == 1


def test_undo_move_restores_order():
    s = BookState(book=_book(3))
    s.move_chapter(0, 2)
    assert [c.title for c in s.book.chapters] == ["فصل 1", "فصل 2", "فصل 0"]
    s.undo()
    assert [c.title for c in s.book.chapters] == ["فصل 0", "فصل 1", "فصل 2"]


def test_add_then_undo():
    s = BookState(book=_book())
    s.add_chapter()
    assert len(s.book.chapters) == 3
    s.undo()
    assert len(s.book.chapters) == 2


def test_undo_empty_is_noop():
    s = BookState(book=_book())
    s.undo()
    assert len(s.book.chapters) == 2


def test_undo_set_book_restores_previous():
    s = BookState(book=_book(1))
    s.set_book(_book(4))
    assert len(s.book.chapters) == 4
    s.undo()
    assert len(s.book.chapters) == 1


def test_structural_op_clears_redo():
    s = BookState(book=_book())
    s.remove_chapter(0)
    s.undo()
    s.add_chapter()
    s.redo()  # المكدّس فارغ بعد عملية جديدة → لا شيء
    assert len(s.book.chapters) == 3
