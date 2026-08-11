"""اختبارات المتانة والمسارات (M1.3/M1.4): ترميزات، HTML تالف، ملفات فارغة."""
from __future__ import annotations

import pytest

from app.core.importers import import_file, detect_type, html_to_chapters


def test_detect_type_routes_html_and_md(tmp_path):
    assert detect_type(tmp_path / "a.html") == "html"
    assert detect_type(tmp_path / "a.htm") == "html"
    assert detect_type(tmp_path / "a.md") == "markdown"
    assert detect_type(tmp_path / "a.markdown") == "markdown"
    assert detect_type(tmp_path / "a.unknown") is None


@pytest.mark.parametrize(
    "name, content, expect_chapters",
    [
        ("broken.html", "<html><body><h1>مفتوح</h1><p>نص بلا إغلاق", 1),
        ("plain.html", "سطر بلا جذر html", 1),
        ("empty.html", "", 0),
    ],
)
def test_broken_or_plain_html_no_crash(tmp_path, name, content, expect_chapters):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    book = import_file(p)
    assert len(book.chapters) == expect_chapters


def test_empty_txt_no_crash(tmp_path):
    p = tmp_path / "empty.txt"
    p.write_text("", encoding="utf-8")
    book = import_file(p)
    assert isinstance(book.chapters, list)


def test_strict_utf8_preserves_arabic(tmp_path):
    content = "<html lang=\"ar\"><body><h1>نجمة</h1></body></html>"
    p = tmp_path / "x.html"
    p.write_bytes(content.encode("utf-8", errors="surrogatepass"))
    book = import_file(p)
    assert book.chapters[0].title == "نجمة"


def test_unknown_file_raises(tmp_path):
    p = tmp_path / "a.pdf"
    p.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        import_file(p)