"""اختبارات التحقق (M5.1): فحوصات داخلية على ملفات EPUB مولّدة/تالفة."""
from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from app.core.epub import EpubWriter
from app.core.validate import validate_epub
from app.models import Book, Chapter, Metadata


def _book() -> Book:
    b = Book(metadata=Metadata(title="كتاب", language="ar"))
    b.add_chapter(Chapter(title="الفصل 1", body="نص."))
    b.add_chapter(Chapter(title="الفصل 2", body="نص ثانٍ."))
    return b


def test_valid_book_passes(tmp_path):
    out = tmp_path / "ok.epub"
    EpubWriter(_book(), tmp_path).write(out)
    issues = validate_epub(out)
    assert issues == [], [f"{i.severity}: {i.message}" for i in issues]


def test_missing_file_is_error(tmp_path):
    issues = validate_epub(tmp_path / "no.epub")
    assert issues and issues[0].severity == "error"


def test_bad_mimetype_first(tmp_path):
    p = tmp_path / "bad.epub"
    b = EpubWriter(_book(), tmp_path)
    good = tmp_path / "good.epub"
    b.write(good)
    with ZipFile(good, "r") as zf:
        data = {n: zf.read(n) for n in zf.namelist()}
    with ZipFile(p, "w") as zf:
        zf.writestr("META-INF/container.xml", data["META-INF/container.xml"])
        zf.writestr("mimetype", data["mimetype"], compress_type=ZIP_DEFLATED)
        for n, d in data.items():
            if n not in ("META-INF/container.xml", "mimetype"):
                zf.writestr(n, d)
    issues = validate_epub(p)
    sev = " ".join(i.message for i in issues)
    assert "أول عنصر" in sev or "مضغوط" in sev


def test_broken_xhtml_detected(tmp_path):
    p = tmp_path / "broken.epub"
    good = tmp_path / "good.epub"
    EpubWriter(_book(), tmp_path).write(good)
    with ZipFile(good, "r") as zf:
        data = {n: zf.read(n) for n in zf.namelist()}
    # نحوّل أحد ملفات xhtml إلى XML غير سليم
    chap = [n for n in data if n.endswith(".xhtml") and n.startswith("OEBPS/k")]
    data[chap[0]] = "<html><p>غير مغلق".encode("utf-8")
    with ZipFile(p, "w") as zf:
        zf.writestr("mimetype", data["mimetype"], compress_type=ZIP_STORED)
        for n in data:
            if n != "mimetype":
                zf.writestr(n, data[n])
    issues = validate_epub(p)
    assert any("XHTML غير سليم" in i.message for i in issues)