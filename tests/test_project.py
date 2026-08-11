"""اختبارات حفظ/فتح المشروع (C1): دورة كاملة عبر .epubproj."""
from __future__ import annotations

from pathlib import Path

from app.models import Book, Chapter, EpubOptions, Metadata
from app.project import load_project, save_project


def _book() -> Book:
    b = Book(
        metadata=Metadata(
            title="كتاب",
            author="مؤلف",
            translator="مترجم",
            publisher="دار النشر",
            description="وصف",
            keywords="أدب، رواية",
            language="ar",
            isbn="123456",
            series="سلسلة",
            part="2",
            rights="حقوق",
        )
    )
    b.add_chapter(Chapter(title="الفصل الأول", body="نص أ.\n\nفقرة ثانية."))
    b.add_chapter(Chapter(title="الفصل الثاني", body="نص ب."))
    b.options.template = "poetry"
    b.options.direction = "rtl"
    b.options.epub_version = 2
    b.options.paragraph.alignment = "center"
    b.options.paragraph.color = "#b45309"
    b.options.cover_image = Path("C:/covers/img.png")
    b.source_files = [Path("C:/src/book.txt")]
    return b


def test_save_load_roundtrip(tmp_path):
    p = tmp_path / "proj.epubproj"
    save_project(_book(), p)
    assert p.exists()

    b = load_project(p)
    assert b.metadata.title == "كتاب"
    assert b.metadata.translator == "مترجم"
    assert b.metadata.publisher == "دار النشر"
    assert b.metadata.description == "وصف"
    assert b.metadata.keywords == "أدب، رواية"
    assert b.metadata.series == "سلسلة"
    assert b.metadata.part == "2"
    assert b.metadata.rights == "حقوق"
    assert b.metadata.isbn == "123456"
    assert len(b.chapters) == 2
    assert b.chapters[0].title == "الفصل الأول"
    assert b.chapters[0].body == "نص أ.\n\nفقرة ثانية."
    assert b.options.template == "poetry"
    assert b.options.direction == "rtl"
    assert b.options.epub_version == 2
    assert b.options.paragraph.alignment == "center"
    assert b.options.paragraph.color == "#b45309"
    assert b.options.cover_image == Path("C:/covers/img.png")
    assert b.source_files == [Path("C:/src/book.txt")]


def test_load_missing_keys_uses_defaults(tmp_path):
    p = tmp_path / "min.epubproj"
    p.write_text('{"chapters": [{"title": "ف", "body": "ن."}]}', encoding="utf-8")
    b = load_project(p)
    assert b.metadata.title == ""
    assert b.options.direction == "rtl"
    assert len(b.chapters) == 1


def test_load_corrupt_raises(tmp_path):
    p = tmp_path / "bad.epubproj"
    p.write_text("{not json", encoding="utf-8")
    try:
        load_project(p)
    except ValueError:
        return
    raise AssertionError("expected ValueError")
