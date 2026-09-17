"""الوظائف الخلفية QThreadPool: ImportJob, ExportJob, UpdateCheckJob, BatchQueue."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal

from app.core.importers import import_batch, import_file
from app.models import Book


@dataclass
class JobResult:
    """نتاج المهمة بشكل مستقل عن Qt (يُستخدم في الاختبارات والواجهة)."""

    ok: bool
    books: list[Book] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ImportSignals(QObject):
    """إشارات آمنة للخيط تُبث من عامل الاستيراد إلى الواجهة."""

    finished = Signal(object)   # emits JobResult
    error = Signal(str)


class ImportJob(QRunnable):
    """يجري في QThreadPool؛ يستورد ملفًا أو دفعة ويعيد النتيجة."""

    def __init__(self, paths: list[Path]) -> None:
        super().__init__()
        self.paths = paths
        self.signals = ImportSignals()

    def run(self) -> None:
        result = JobResult(ok=True)
        try:
            if len(self.paths) == 1:
                try:
                    result.books = [import_file(self.paths[0])]
                except Exception as exc:  # noqa: BLE001
                    result.ok = False
                    result.errors.append(f"{self.paths[0].name}: {exc}")
            else:
                books: list[Book] = []
                for p in self.paths:
                    try:
                        books.append(import_file(p))
                    except Exception as exc:  # noqa: BLE001
                        result.errors.append(f"{p.name}: {exc}")
                result.books = books
                result.ok = bool(books)
        except Exception as exc:  # noqa: BLE001 — تُبلَّغ للواجهة بلا إنهاء
            result.ok = False
            result.errors.append(str(exc))
        # أبث finished دائمًا (مع نتائج جزئية) + error عند الفشل
        self.signals.finished.emit(result)
        if not result.ok:
            self.signals.error.emit("; ".join(result.errors))


class ExportSignals(QObject):
    """إشارات تُبث عند انتهاء التصدير."""

    finished = Signal(object)   # emits Path
    error = Signal(str)
    progress = Signal(int, str)  # (0..100, رسالة)


class ExportJob(QRunnable):
    """يبني EPUB من Book عبر EpubWriter داخل خيط."""

    def __init__(self, book: Book, destination: Path) -> None:
        super().__init__()
        # لقطة عميقة لحظة الإنشاء: لا تتأثر الكتابة بتحرير المستخدم أثناء البناء
        self.book = copy.deepcopy(book)
        self.destination = destination
        self.signals = ExportSignals()

    def run(self) -> None:
        try:
            from app.core.epub import EpubWriter

            writer = EpubWriter(
                self.book, self.destination.parent, on_progress=self._on_progress
            )
            out = writer.write(self.destination)
        except Exception as exc:  # noqa: BLE001
            self.signals.error.emit(str(exc))
            return
        self.signals.finished.emit(out)

    def _on_progress(self, value: int, message: str) -> None:
        self.signals.progress.emit(value, message)


class UpdateSignals(QObject):
    """إشارات فحص التحديثات."""

    finished = Signal(object)   # emits UpdateResult
    error = Signal(str)


class UpdateCheckJob(QRunnable):
    """فحص التحديثات في خيط، ثم بث UpdateResult إلى الواجهة."""

    def __init__(self, update_url: str) -> None:
        super().__init__()
        self.update_url = update_url
        self.signals = UpdateSignals()

    def run(self) -> None:
        try:
            from app.updates import fetch_latest

            result = fetch_latest(self.update_url)
        except Exception as exc:  # noqa: BLE001
            self.signals.error.emit(str(exc))
            return
        self.signals.finished.emit(result)


class CoverSignals(QObject):
    """إشارات توليد معاينة الغلاف (token لتمييز النتائج القديمة)."""

    finished = Signal(int, object)  # (token, bytes)
    error = Signal(int, str)  # (token, message)


class CoverJob(QRunnable):
    """يولّد بايتات الغلاف من لقطة خفيفة (بلا نسخ الكتاب كاملًا) في خيط."""

    def __init__(self, token: int, snapshot: dict) -> None:
        super().__init__()
        self.token = token
        self.snapshot = snapshot
        self.signals = CoverSignals()

    def run(self) -> None:
        try:
            from types import SimpleNamespace

            from app.core.covergen import generate_cover_bytes

            s = self.snapshot
            cover_image = s.get("cover_image")
            book = SimpleNamespace(
                metadata=SimpleNamespace(title=s.get("title", ""), author=s.get("author", ""))
            )
            options = SimpleNamespace(
                cover_image=Path(cover_image) if cover_image else None,
                auto_cover=s.get("auto_cover", True),
                template=s.get("template", ""),
                title_font=s.get("title_font", ""),
                body_font=s.get("body_font", ""),
                image_format=s.get("image_format", "jpeg"),
                max_image_width=s.get("max_image_width", 1200),
            )
            data = generate_cover_bytes(book, options)
        except Exception as exc:  # noqa: BLE001
            self.signals.error.emit(self.token, str(exc))
            return
        self.signals.finished.emit(self.token, bytes(data))


class ValidateSignals(QObject):
    """إشارات التحقق من EPUB بعد التصدير."""

    finished = Signal(object, object)  # (Path, issues)
    error = Signal(object, str)  # (Path, message)


class ValidateJob(QRunnable):
    """يفحص EPUB الناتج في خيط حتى لا يجمّد الواجهة مع الملفات الكبيرة."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self.signals = ValidateSignals()

    def run(self) -> None:
        try:
            from app.core.validate import validate_epub

            issues = validate_epub(Path(self.path))
        except Exception as exc:  # noqa: BLE001
            self.signals.error.emit(self.path, str(exc))
            return
        self.signals.finished.emit(self.path, issues)