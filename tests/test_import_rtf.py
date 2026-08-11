"""اختبارات مستورد RTF (M2.2): ربط النص عبر striprtf + كشف الفصول."""
from __future__ import annotations

from striprtf.striprtf import rtf_to_text as _striprtf

from app.core.importers import rtf_to_text, rtf_to_book, import_file


def _rtf_escape(s: str) -> str:
    """تحويل نص إلى هروب RTF (unicode لدور المباي العربية)."""
    out = []
    for ch in s:
        o = ord(ch)
        out.append(ch if o < 128 else f"\\u{o}?")
    return "".join(out)


def build_rtf(*lines: str) -> str:
    content = "\\par".join(_rtf_escape(l) for l in lines)
    return "{\\rtf1\\ansi\\uc1{\\fonttbl{\\f0 Arial;}}\\f0\\fs24 " + content + "}"


def _norm(text: str) -> str:
    return "".join(text.split())


def test_rtf_text_extraction(tmp_path):
    p = tmp_path / "e.rtf"
    p.write_text(build_rtf("مرحبا", "سطر ثانٍ."), encoding="utf-8")
    assert "مرحبا" in rtf_to_text(p)


def test_rtf_to_book_chapters(tmp_path):
    p = tmp_path / "b.rtf"
    p.write_text(build_rtf("الفصل الأول", "نص أ.", "الفصل الثاني", "نص ب."), encoding="utf-8")
    book = rtf_to_book(p)
    assert [c.title for c in book.chapters] == ["الفصل الأول", "الفصل الثاني"]
    assert _norm(book.chapters[0].body) == _norm("نص أ.")
    assert _norm(book.chapters[1].body) == _norm("نص ب.")


def test_rtf_import_via_import_file(tmp_path):
    p = tmp_path / "كلam.rtf"
    p.write_text(build_rtf("الفصل الأول", "محتوى."), encoding="utf-8")
    book = import_file(p)
    assert book.metadata.title == "كلam"
    assert [c.title for c in book.chapters] == ["الفصل الأول"]