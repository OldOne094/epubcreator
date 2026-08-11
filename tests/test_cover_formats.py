"""إصلاحات الغلاف (B1/B2): الامتداد ومحتوى البايتات ونوع MIME مطابقة للصيغة المختارة."""
from __future__ import annotations

import io
from pathlib import Path
from zipfile import ZipFile

from PIL import Image

from app.core.covergen import generate_cover_bytes
from app.core.epub import EpubWriter
from app.models import Book, Chapter, EpubOptions, Metadata

_PNG_HEADER = b"\x89PNG\r\n\x1a\n"


def _book() -> Book:
    b = Book(metadata=Metadata(title="كتاب", author="مؤلف", language="ar"))
    b.add_chapter(Chapter(title="فصل", body="نص."))
    b.options.direction = "rtl"
    return b


def _user_image(tmp_path: Path) -> Path:
    p = tmp_path / "user.png"
    Image.new("RGB", (200, 300), (10, 20, 30)).save(p, format="PNG")
    return p


def _opf(zf: ZipFile) -> str:
    return zf.read("OEBPS/content.opf").decode("utf-8")


def test_writer_png_cover_named_typed_and_bytes(tmp_path):
    b = _book()
    b.options.image_format = "png"
    b.options.cover_image = _user_image(tmp_path)
    b.options.auto_cover = False
    out = tmp_path / "b.epub"
    EpubWriter(b, tmp_path).write(out)
    with ZipFile(out) as zf:
        assert "OEBPS/cover.png" in zf.namelist()
        assert "OEBPS/cover.jpeg" not in zf.namelist()
        assert zf.read("OEBPS/cover.png")[:8] == _PNG_HEADER
        opf = _opf(zf)
        assert 'href="cover.png"' in opf
        assert "image/png" in opf


def test_writer_webp_cover(tmp_path):
    b = _book()
    b.options.image_format = "webp"
    b.options.cover_image = _user_image(tmp_path)
    b.options.auto_cover = False
    out = tmp_path / "w.epub"
    EpubWriter(b, tmp_path).write(out)
    with ZipFile(out) as zf:
        assert "OEBPS/cover.webp" in zf.namelist()
        data = zf.read("OEBPS/cover.webp")
        assert data[:4] == b"RIFF"
        assert b"WEBP" in data[:12]
        assert "image/webp" in _opf(zf)


def test_writer_default_remains_jpeg(tmp_path):
    b = _book()
    b.options.cover_image = _user_image(tmp_path)
    b.options.auto_cover = False
    out = tmp_path / "j.epub"
    EpubWriter(b, tmp_path).write(out)
    with ZipFile(out) as zf:
        assert "OEBPS/cover.jpeg" in zf.namelist()
        assert zf.read("OEBPS/cover.jpeg")[:2] == b"\xff\xd8"
        assert "image/jpeg" in _opf(zf)


def test_writer_auto_cover_respects_format(tmp_path):
    b = _book()
    b.options.image_format = "png"
    b.options.cover_image = None
    b.options.auto_cover = True
    out = tmp_path / "a.epub"
    EpubWriter(b, tmp_path).write(out)
    with ZipFile(out) as zf:
        assert "OEBPS/cover.png" in zf.namelist()
        assert zf.read("OEBPS/cover.png")[:8] == _PNG_HEADER


def test_covergen_user_png_is_real_png(tmp_path):
    opts = EpubOptions()
    opts.image_format = "png"
    opts.cover_image = _user_image(tmp_path)
    data = generate_cover_bytes(_book(), opts)
    assert Image.open(io.BytesIO(data)).format == "PNG"


def test_covergen_webp_is_real_webp(tmp_path):
    opts = EpubOptions()
    opts.image_format = "webp"
    opts.cover_image = _user_image(tmp_path)
    data = generate_cover_bytes(_book(), opts)
    assert Image.open(io.BytesIO(data)).format == "WEBP"
