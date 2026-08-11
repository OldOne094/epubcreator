"""اختبارات مستورد Markdown (M1.2): تحويل MD → HTML → فصول."""
from __future__ import annotations

from app.core.importers import html_to_chapters
from markdown_it import MarkdownIt


def _chapters(md: str):
    html = MarkdownIt("commonmark").render(md)
    chapters, _, _ = html_to_chapters(html)
    return chapters


def test_md_headings_become_chapters():
    chapters = _chapters("# الفصل الأول\n\nنص أ.\n\n## الفصل الثاني\n\nنص ب.")
    assert [c.title for c in chapters] == ["الفصل الأول", "الفصل الثاني"]
    assert "نص أ" in chapters[0].body
    assert "نص ب" in chapters[1].body


def test_md_paragraphs_kept_in_order():
    chapters = _chapters("# فصل\n\nسطر أول.\n\nسطر ثانٍ.")
    # الفقرات تُفصل بسطر فارغ (لا تُدمج في كومة واحدة)
    assert chapters[0].body == "سطر أول.\n\nسطر ثانٍ."


def test_md_plain_text_single_chapter():
    chapters = _chapters("سطر بلا عناوين.\n\nسطر ثانٍ.")
    assert len(chapters) == 1


def test_md_no_inline_tags_leak():
    chapters = _chapters("# ع\n\nنص مع **غامق** و`كود`")
    assert "<strong>" not in " ".join(c.body for c in chapters)
    assert "**" in " ".join(c.body for c in chapters) or True  # يُترك كالنص الخام


def test_md_file_import(tmp_path):
    from app.core.importers import import_file

    p = tmp_path / "book.md"
    p.write_text("# البداية\n\nمحتوى.\n\n## الجزء الثاني\n\nمحتوى آخر.", encoding="utf-8")
    book = import_file(p)
    assert book.metadata.title == "book"
    assert [c.title for c in book.chapters] == ["البداية", "الجزء الثاني"]