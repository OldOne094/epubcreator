"""اختبارات مولّد EPUB (M4): بنية zip رسمية + XML سليم + مسارات."""
from __future__ import annotations

from zipfile import ZipFile

import pytest
from lxml import etree

from app.core.epub import EpubWriter, chapter_xhtml, content_opf, nav_xhtml
from app.models import Book, Chapter, EpubOptions, Metadata


def _book(n=2, title="كتاب تجريبي", author="مؤلف") -> Book:
    b = Book(metadata=Metadata(title=title, author=author, language="ar"))
    for i in range(n):
        b.add_chapter(Chapter(title=f"الفصل {i + 1}", body=f"نص الفصل {i + 1}.\n\nفقرة ثانية."))
    b.options.direction = "rtl"
    return b


def test_chapter_xhtml_is_wellformed():
    b = _book()
    x = chapter_xhtml(b.chapters[0], 0, b.options)
    etree.fromstring(x.encode("utf-8"))  # إن لم تُثبت، ترفع هذه
    assert 'dir="rtl"' in x
    assert "<p>" in x


def test_nav_is_wellformed_and_links_chapters():
    b = _book()
    n = nav_xhtml(b.chapters, "فهرس")
    root = etree.fromstring(n.encode("utf-8"))
    links = root.xpath("//*[local-name()='a']")
    assert len(links) == len(b.chapters)


def test_content_opf_manifest_spine():
    b = _book()
    files = ["k0_x0.xhtml", "k1_x1.xhtml", "k2_x2.xhtml"]
    opf = content_opf(b, files, has_cover=True, cover_href="cover.jpeg")
    etree.fromstring(opf.encode("utf-8"))
    assert "properties=\"cover-image\"" in opf
    assert "image/jpeg" in opf


def test_writer_produces_valid_zip(tmp_path):
    b = _book()
    out = tmp_path / "book.epub"
    EpubWriter(b, tmp_path).write(out)
    assert out.exists()

    with ZipFile(out) as zf:
        names = zf.namelist()
        assert "mimetype" in names
        assert "META-INF/container.xml" in names
        assert "OEBPS/content.opf" in names
        assert "OEBPS/toc.xhtml" in names or "OEBPS/nav.xhtml" in names
        assert "OEBPS/style.css" in names
        # mimetype غير مضغوط وأول عنصر
        info = zf.getinfo("mimetype")
        assert info.compress_type == 0  # STORE
        assert names[0] == "mimetype"
        # محتوى mimetype سليم
        assert zf.read("mimetype") == b"application/epub+zip"
        # opf يُحلل XML سليم
        etree.fromstring(zf.read("OEBPS/content.opf"))


def test_writer_cover_bytes_present_when_auto(tmp_path):
    b = _book()
    b.options.auto_cover = True
    b.options.cover_image = None
    out = tmp_path / "w.epub"
    EpubWriter(b, tmp_path).write(out)
    with ZipFile(out) as zf:
        assert "OEBPS/cover.jpeg" in zf.namelist()
        data = zf.read("OEBPS/cover.jpeg")
        assert data[:2] == b"\xff\xd8"  # رأس JPEG


def test_epub2_export_writes_ncx(tmp_path):
    from app.core.epub import toc_ncx

    b = _book()
    b.options.epub_version = 2
    out = tmp_path / "v2.epub"
    EpubWriter(b, tmp_path).write(out)
    with ZipFile(out) as zf:
        names = zf.namelist()
        assert "OEBPS/toc.ncx" in names
        assert "OEBPS/nav.xhtml" not in names
        opf = zf.read("OEBPS/content.opf").decode("utf-8")
        assert 'version="2.0"' in opf
        assert 'toc="ncx"' in opf
        etree.fromstring(zf.read("OEBPS/toc.ncx"))


def test_epub3_writes_nav(tmp_path):
    b = _book()
    b.options.epub_version = 3
    out = tmp_path / "v3.epub"
    EpubWriter(b, tmp_path).write(out)
    with ZipFile(out) as zf:
        assert "OEBPS/nav.xhtml" in zf.namelist()
        assert "OEBPS/toc.ncx" not in zf.namelist()


def test_writer_active_links_resolve(tmp_path):
    """كل spine itemref → ملف manifest موجود فعلًا في zip."""
    b = _book(3)
    out = tmp_path / "res.epub"
    EpubWriter(b, tmp_path).write(out)
    with ZipFile(out) as zf:
        opf = zf.read("OEBPS/content.opf")
        names = zf.namelist()
        root = etree.fromstring(opf)
        hrefs = root.xpath("//*[local-name()='item']/@href")
        normalized = {f"OEBPS/{h}" for h in hrefs}
        nav_links = root.xpath(
            "//*[local-name()='itemref']/@idref"
        )
        ids = root.xpath("//*[local-name()='item']/@id")
        assert nav_links and all(i in ids for i in nav_links)
        for n in normalized:
            assert n in names, f"ناقص: {n}"


def test_writer_user_cover_used(tmp_path):
    from PIL import Image
    import io

    img = Image.new("RGB", (300, 400), (10, 20, 30))
    p = tmp_path / "user.png"
    img.save(p, format="PNG")

    b = _book()
    b.options.auto_cover = False
    b.options.cover_image = p
    out = tmp_path / "c.epub"
    EpubWriter(b, tmp_path).write(out)
    with ZipFile(out) as zf:
        assert "OEBPS/cover.jpeg" in zf.namelist()
        cover_data = zf.read("OEBPS/cover.jpeg")
        assert cover_data[:2] == b"\xff\xd8"

    # قراءة بالـ Pillow للتأكد من أنها صورة سليمة
    with Image.open(io.BytesIO(cover_data)) as im:
        assert im.format == "JPEG"


def test_full_metadata_exported_to_opf(tmp_path):
    """كل حقول الواجهة تصل إلى OPF (الناشر/الوصف/الكلمات/المترجم/الحقوق/السلسلة/الجزء)."""
    b = Book(
        metadata=Metadata(
            title="كتاب",
            author="مؤلف",
            translator="مترجم",
            publisher="دار النشر",
            description="وصف الكتاب",
            keywords="أدب، رواية ; تاريخ",
            rights="جميع الحقوق",
            series="سلسلة كبرى",
            part="2",
            language="ar",
        )
    )
    b.add_chapter(Chapter(title="فصل", body="نص."))
    out = tmp_path / "meta.epub"
    EpubWriter(b, tmp_path).write(out)
    with ZipFile(out) as zf:
        opf = zf.read("OEBPS/content.opf").decode("utf-8")
    assert "<dc:publisher>دار النشر</dc:publisher>" in opf
    assert "<dc:description>وصف الكتاب</dc:description>" in opf
    assert "<dc:subject>أدب</dc:subject>" in opf
    assert "<dc:subject>رواية</dc:subject>" in opf
    assert "<dc:subject>تاريخ</dc:subject>" in opf
    assert "<dc:contributor>مترجم</dc:contributor>" in opf
    assert "<dc:rights>جميع الحقوق</dc:rights>" in opf
    assert 'property="belongs-to-collection"' in opf
    assert 'property="group-position"' in opf
    assert "سلسلة كبرى" in opf


def test_full_metadata_epub2_uses_calibre_meta(tmp_path):
    b = Book(
        metadata=Metadata(title="كتاب", language="ar", series="سلسلة", part="3")
    )
    b.add_chapter(Chapter(title="ف", body="ن."))
    b.options.epub_version = 2
    out = tmp_path / "meta2.epub"
    EpubWriter(b, tmp_path).write(out)
    with ZipFile(out) as zf:
        opf = zf.read("OEBPS/content.opf").decode("utf-8")
    assert 'meta name="calibre:series"' in opf
    assert 'meta name="calibre:series_index"' in opf
    assert "belongs-to-collection" not in opf


def test_empty_keywords_emit_no_subjects(tmp_path):
    b = _book()
    b.metadata.keywords = "  ،  "
    out = tmp_path / "kw.epub"
    EpubWriter(b, tmp_path).write(out)
    with ZipFile(out) as zf:
        opf = zf.read("OEBPS/content.opf").decode("utf-8")
    assert "<dc:subject>" not in opf