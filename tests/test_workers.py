"""اختبارات ImportJob (M3.2): استيراد ملف/دفعة عبر QThreadPool (offscreen)."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QThreadPool

from app.models import Book
from app.workers import ExportJob, ImportJob


def test_importjob_single_file(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("الفصل الأول\n\nنص.", encoding="utf-8")

    job = ImportJob([p])
    got = []
    job.signals.finished.connect(got.append)

    app = QCoreApplication.instance() or QCoreApplication([])
    pool = QThreadPool()
    pool.start(job)
    for _ in range(300):
        pool.waitForDone(10)
        app.processEvents()
        if got:
            break

    assert got, "النتيجة لم تصل"
    result = got[0]
    assert result.ok
    assert len(result.books) == 1
    assert isinstance(result.books[0], Book)
    assert result.books[0].chapters[0].title == "الفصل الأول"


def test_importjob_batch(tmp_path):
    for name in ("one.txt", "two.txt"):
        (tmp_path / name).write_text("نص.", encoding="utf-8")
    job = ImportJob([tmp_path / "one.txt", tmp_path / "two.txt"])
    got = []
    job.signals.finished.connect(got.append)
    job.run()  # تشغيل مباشر (نفس الخيط)
    assert got and got[0].ok
    assert len(got[0].books) == 2


def test_importjob_collects_error(tmp_path):
    bad = tmp_path / "a.pdf"  # نوع غير مدعوم
    bad.write_text("x", encoding="utf-8")
    job = ImportJob([bad])
    errors = []
    job.signals.error.connect(errors.append)
    job.run()
    assert errors  # خطأ مُلتقى


def test_exportjob_writes_epub(tmp_path):
    from app.models import Chapter, Metadata

    book = Book(metadata=Metadata(title="تصدير"))
    book.add_chapter(Chapter(title="ف", body="ن."))
    dest = tmp_path / "out.epub"

    job = ExportJob(book, dest)
    done = []
    job.signals.finished.connect(done.append)
    job.run()
    assert done and done[0] == dest
    assert dest.exists()
    assert dest.stat().st_size > 0


def test_exportjob_reports_progress(tmp_path):
    from app.models import Chapter, Metadata

    book = Book(metadata=Metadata(title="تقدم"))
    book.add_chapter(Chapter(title="ف", body="ن."))
    dest = tmp_path / "p.epub"

    job = ExportJob(book, dest)
    seen = []
    job.signals.progress.connect(lambda value, message: seen.append((value, message)))
    job.run()
    assert dest.exists()
    assert seen  # وُجدت تقارير تقدم
    assert seen[0][0] >= 0
    assert seen[-1][0] == 100


def test_exportjob_snapshots_book_at_start(tmp_path):
    """التصدير يلتقط الكتاب لحظة الإنشاء ولا يتأثر بالتحرير اللاحق."""
    from app.models import Chapter, Metadata
    from zipfile import ZipFile

    book = Book(metadata=Metadata(title="لقطة"))
    book.add_chapter(Chapter(title="فصل أصلي", body="نص أصلي."))
    dest = tmp_path / "snap.epub"

    job = ExportJob(book, dest)
    # تعديل بعد إنشاء المهمة (كما يحدث من المحرر أثناء التصدير)
    book.chapters[0].body = "نص معدل."
    book.chapters[0].title = "معدل"
    job.run()

    with ZipFile(dest) as zf:
        xhtml = [n for n in zf.namelist() if n.startswith("OEBPS/k")][0]
        content = zf.read(xhtml).decode("utf-8")
    assert "نص أصلي" in content
    assert "فصل أصلي" in content
    assert "معدل" not in content