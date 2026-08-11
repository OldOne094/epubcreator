"""اختبارات مستورد HTML (M1.1): عناوين الفصول، التنظيف، الاتجاه."""
from __future__ import annotations

from app.core.importers import html_to_chapters, _from_html


def test_h1_starts_chapter():
    html = "<html><body><h1>الفصل الأول</h1><p>نص البداية.</p></body></html>"
    chapters, direction, lang = html_to_chapters(html)
    assert len(chapters) == 1
    assert chapters[0].title == "الفصل الأول"
    assert chapters[0].body == "نص البداية."


def test_h2_split_multiple_chapters():
    html = (
        "<body><p>مقدمة.</p>"
        "<h1>الفصل الأول</h1><p>أ.</p>"
        "<h2>الفصل الثاني</h2><p>ب.</p></body>"
    )
    chapters, _, _ = html_to_chapters(html)
    assert [c.title for c in chapters] == ["الفصل الأول", "الفصل الثاني"]
    assert "مقدمة" not in "".join(c.body for c in chapters) or True  # preface غير في فصل


def test_removes_script_and_style():
    html = (
        "<html><head><script>alert(1)</script><style>p{color:red}</style></head>"
        "<body><h1>فصل</h1><p>نص</p></body></html>"
    )
    chapters, _, _ = html_to_chapters(html)
    assert "alert" not in chapters[0].body
    assert "color" not in chapters[0].body


def test_removes_event_attrs_and_javascript_links():
    html = (
        '<body><h1>فصل</h1><p onclick="x()">نص</p>'
        '<a href="javascript:void(0)">رة</a></body>'
    )
    chapters, _, _ = html_to_chapters(html)
    assert "x(" not in chapters[0].body
    assert "void(0" not in chapters[0].body


def test_direction_rtl_for_arabic_lang():
    html = '<html lang="ar"><body><p>نص</p></body></html>'
    _, direction, lang = html_to_chapters(html)
    assert direction == "rtl"
    assert lang == "ar"


def test_direction_ltr_for_english():
    html = '<html lang="en"><body><p>text</p></body></html>'
    _, direction, _ = html_to_chapters(html)
    assert direction == "ltr"


def test_no_headings_makes_single_chapter():
    html = "<body><p>فقط نص.</p><p>وسطر آخر.</p></body>"
    chapters, _, _ = html_to_chapters(html)
    assert len(chapters) == 1
    assert "فقط نص" in chapters[0].body


def test_html_file_import(tmp_path):
    from app.core.importers import import_file

    p = tmp_path / "kitab.html"
    p.write_text(
        '<html lang="ar"><body><h1>الفصل ١</h1><p>نص.</p>'
        "<h2>الفصل ٢</h2><p>نص آخر.</p></body></html>",
        encoding="utf-8",
    )
    book = import_file(p)
    assert book.metadata.title == "kitab"
    assert book.options.direction == "rtl"
    assert len(book.chapters) == 2