"""حالة الجلسة: الكتاب النشط + مؤشر الفصل الحالي + إشعارات تغيّر.

نواة نقية (لا تعتمد على Qt) تستخدمها الواجهة والوظائف الخلفية معًا.
عند الحاجة إلى إشارات Qt تُغلَّف الطبقة في M3.2+.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from app.models import Book, Chapter

_MAX_UNDO = 50  # سقف مكدّس التراجع للحفاظ على الذاكرة


@dataclass
class BookState:
    """تتتبع الكتاب النشط والتحديد الحالي، وتبليغ المستمعين بالتغيير."""

    book: Book = field(default_factory=Book)
    current_index: int = 0
    _on_change: "callable | None" = None  # noqa: F821
    _undo: list = field(default_factory=list)
    _redo: list = field(default_factory=list)

    # -------------------------------------------------------- تراجع ---
    def _snapshot(self) -> tuple[Book, int]:
        return (copy.deepcopy(self.book), self.current_index)

    def _push_undo(self) -> None:
        self._undo.append(self._snapshot())
        if len(self._undo) > _MAX_UNDO:
            self._undo.pop(0)
        self._redo.clear()

    def _restore(self, book: Book, index: int) -> None:
        self.book = book
        self.current_index = (
            max(min(index, len(book.chapters) - 1), 0) if book.chapters else 0
        )

    def undo(self) -> None:
        """الرجوع خطوة: يعيد الكتاب كاملًا (فصول/بيانات) إلى ما قبل آخر عملية بنيوية."""
        if not self._undo:
            return
        self._redo.append(self._snapshot())
        book, index = self._undo.pop()
        self._restore(book, index)
        self._notify()

    def redo(self) -> None:
        """إعادة ما أُلغي بالتراجع."""
        if not self._redo:
            return
        self._undo.append(self._snapshot())
        book, index = self._redo.pop()
        self._restore(book, index)
        self._notify()

    # -------------------------------------------------------- حالة ---
    def set_book(self, book: Book) -> None:
        self._push_undo()
        self.book = book
        self.current_index = 0
        self._notify()

    def current_chapter(self) -> Chapter | None:
        if 0 <= self.current_index < len(self.book.chapters):
            return self.book.chapters[self.current_index]
        return None

    def select_chapter(self, index: int) -> None:
        if 0 <= index < len(self.book.chapters) and index != self.current_index:
            self.current_index = index
            self._notify()

    def update_current_body(self, body: str) -> None:
        ch = self.current_chapter()
        if ch is not None and ch.body != body:
            ch.body = body
            self._notify()

    def update_current_title(self, title: str) -> None:
        ch = self.current_chapter()
        if ch is not None and ch.title != title:
            ch.title = title
            self._notify()

    def add_chapter(self, chapter: "Chapter | None" = None, index: "int | None" = None) -> None:  # noqa: F821
        """إضافة فصل (جديد أو منقول) واختياره تلقائيًّا."""
        self._push_undo()
        ch = chapter or Chapter()
        if index is None:
            self.book.chapters.append(ch)
            self.current_index = len(self.book.chapters) - 1
        else:
            self.book.chapters.insert(index, ch)
            self.current_index = index
        self._notify()

    def remove_chapter(self, index: "int | None" = None) -> None:  # noqa: F821
        """حذف الفصل الحالي (أو بمؤشر محدد) مع إصلاح التحديد."""
        idx = self.current_index if index is None else index
        if not self.book.chapters or not (0 <= idx < len(self.book.chapters)):
            return
        self._push_undo()
        self.book.chapters.pop(idx)
        self.current_index = max(min(idx, len(self.book.chapters) - 1), 0)
        self._notify()

    def move_chapter(self, source: int, target: int) -> None:
        """نقل فصل من مؤشر إلى آخر مع اختياره بعد النقل."""
        n = len(self.book.chapters)
        if not n or not (0 <= source < n and 0 <= target < n):
            return
        self._push_undo()
        ch = self.book.chapters.pop(source)
        self.book.chapters.insert(target, ch)
        self.current_index = target
        self._notify()

    @property
    def has_chapters(self) -> bool:
        return bool(self.book.chapters)

    def set_on_change(self, callback: "callable") -> None:  # noqa: F821
        self._on_change = callback

    def notify(self) -> None:
        """إبلاغ المستمعين الخارجيين بتغيير يدوي (خارج الطُّرق البنية)."""
        self._notify()

    def _notify(self) -> None:
        if self._on_change is not None:
            self._on_change()