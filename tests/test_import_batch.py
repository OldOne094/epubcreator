"""اختبارات الدفعة (M2.4): كل ملف ← كتاب مستقل."""
from __future__ import annotations

from app.core.importers import import_batch


def test_batch_returns_independent_books(tmp_path):
    for name in ("one.txt", "two.txt", "three.md"):
        suffix = "txt" if name.endswith("txt") else "md"
        content = "# البداية\n\nنص." if suffix == "md" else "البداية\n\nنص."
        (tmp_path / name).write_text(content, encoding="utf-8")

    books = import_batch([tmp_path / "one.txt", tmp_path / "two.txt", tmp_path / "three.md"])

    assert len(books) == 3
    # كل ملف كتاب مستقل عن غيره (لا دمج)
    assert all(len(b.chapters) >= 1 for b in books)
    titles = [b.metadata.title for b in books]
    assert titles == ["one", "two", "three"]


def test_batch_preserves_source_files(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("نص.", encoding="utf-8")
    books = import_batch([p])
    assert books[0].source_files == [p]