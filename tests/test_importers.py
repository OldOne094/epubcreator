"""اختبارات المستوردات."""
from __future__ import annotations

from pathlib import Path

from app.core import importers


def _write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


def test_detect_type(tmp_path: Path):
    txt = tmp_path / "a.txt"
    assert importers.detect_type(txt) == "txt"
    md = tmp_path / "b.md"
    assert importers.detect_type(md) == "markdown"
    unknown = tmp_path / "c.xyz"
    assert importers.detect_type(unknown) is None


def test_import_txt_utf8(tmp_path):
    p = _write(tmp_path / "kitab.txt", "الفصل الأول\n\nنص البداية.".encode("utf-8"))
    book = importers.import_file(p)
    assert book.metadata.title == "kitab"
    assert len(book.chapters) == 1
    assert book.chapters[0].title == "الفصل الأول"


def test_import_txt_with_bom(tmp_path):
    p = _write(tmp_path / "bom.txt", b"\xef\xbb\xbf" + "محتوى".encode("utf-8"))
    book = importers.import_file(p)
    # سطر بلا عنوان فصل: يبقى كاملًا في الجسم ولا يُبتلع كعنوان
    assert book.chapters[0].body == "محتوى"
    assert book.chapters[0].title == ""


def test_import_unsupported_raises(tmp_path):
    p = _write(tmp_path / "x.pdf", b"%PDF")
    try:
        importers.import_file(p)
    except ValueError as e:
        assert ".pdf" in str(e)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")