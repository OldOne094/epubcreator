"""QA (M6.4): دفعة 100 ملف — استيراد + توليد EPUB + تحقق هيكلي لكل ملف."""
from __future__ import annotations

from pathlib import Path

from app.core.epub import EpubWriter
from app.core.importers import import_batch
from app.core.validate import validate_epub


def _make_files(tmp_path: Path, n: int = 100) -> list[Path]:
    paths = []
    for i in range(n):
        p = tmp_path / f"k{i}.txt"
        p.write_text(f"الفصل {i + 1}\n\nمحتوى الكتاب رقم {i + 1} بالعربية.", encoding="utf-8")
        paths.append(p)
    return paths


def test_batch_100_import(tmp_path):
    books = import_batch(_make_files(tmp_path))
    assert len(books) == 100
    assert all(b.chapters for b in books)


def test_batch_100_export_and_validate(tmp_path):
    books = import_batch(_make_files(tmp_path, 100))
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    for i, book in enumerate(books):
        out = EpubWriter(book, out_dir).write(out_dir / f"b{i}.epub")
        issues = validate_epub(out)
        assert issues == [], [f"{x.severity}: {x.message}" for x in issues]