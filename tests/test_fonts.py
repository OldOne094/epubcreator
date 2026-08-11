"""اختبارات تضمين الخطوط (C3/B3): @font-face + OEBPS/fonts + manifest + تحقق."""
from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from app.core.epub import EpubWriter, available_font_files
from app.core.validate import validate_epub
from app.models import Book, Chapter, Metadata


def _book() -> Book:
    b = Book(metadata=Metadata(title="كتاب", language="ar"))
    b.add_chapter(Chapter(title="ف", body="ن."))
    b.options.title_font = "Amiri"
    b.options.body_font = "Amiri"
    return b


def _fonts_dir(tmp_path: Path) -> Path:
    d = tmp_path / "fonts"
    d.mkdir()
    (d / "Amiri.ttf").write_bytes(b"fake-ttf-data")
    (d / "Note.otf").write_bytes(b"fake-otf-data")
    return d


def test_available_font_files_filters_by_ext(tmp_path):
    d = _fonts_dir(tmp_path)
    (d / "readme.txt").write_text("x", encoding="utf-8")
    names = [p.name for p in available_font_files(d)]
    assert "Amiri.ttf" in names
    assert "Note.otf" in names
    assert "readme.txt" not in names


def test_embed_fonts_writes_fonts_faces_and_manifest(tmp_path):
    b = _book()
    b.options.embed_fonts = True
    out = tmp_path / "f.epub"
    EpubWriter(b, tmp_path, fonts_dir=_fonts_dir(tmp_path)).write(out)

    with ZipFile(out) as zf:
        names = zf.namelist()
        assert "OEBPS/fonts/Amiri.ttf" in names
        assert "OEBPS/fonts/Note.otf" in names
        css = zf.read("OEBPS/style.css").decode("utf-8")
        assert "@font-face { font-family: 'Amiri'; src: url('fonts/Amiri.ttf'); }" in css
        assert "@font-face { font-family: 'Note'; src: url('fonts/Note.otf'); }" in css
        opf = zf.read("OEBPS/content.opf").decode("utf-8")
        assert 'href="fonts/Amiri.ttf" media-type="font/ttf"' in opf
        assert 'href="fonts/Note.otf" media-type="font/otf"' in opf

    assert validate_epub(out) == []


def test_no_embed_when_disabled(tmp_path):
    b = _book()
    b.options.embed_fonts = False
    out = tmp_path / "no.epub"
    EpubWriter(b, tmp_path, fonts_dir=_fonts_dir(tmp_path)).write(out)
    with ZipFile(out) as zf:
        names = zf.namelist()
        css = zf.read("OEBPS/style.css").decode("utf-8")
    assert not any("fonts/" in n for n in names)
    assert "@font-face" not in css


def test_empty_fonts_dir_is_safe(tmp_path):
    b = _book()
    b.options.embed_fonts = True
    out = tmp_path / "e.epub"
    EpubWriter(b, tmp_path, fonts_dir=tmp_path / "empty").write(out)
    with ZipFile(out) as zf:
        css = zf.read("OEBPS/style.css").decode("utf-8")
    assert "@font-face" not in css
    assert validate_epub(out) == []


def test_font_family_used_in_css_after_embed(tmp_path):
    """قواعد @font-face تسبق قواعد الجسم فلا يهزمها CSS القالب."""
    b = _book()
    out = tmp_path / "fc.epub"
    EpubWriter(b, tmp_path, fonts_dir=_fonts_dir(tmp_path)).write(out)
    with ZipFile(out) as zf:
        css = zf.read("OEBPS/style.css").decode("utf-8")
    assert css.index("@font-face") < css.index("body {")
