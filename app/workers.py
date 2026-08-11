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
                result.books = [import_file(self.paths[0])]
            else:
                result.books = import_batch(self.paths)
        except Exception as exc:  # noqa: BLE001 — تُبلَّغ للواجهة بلا إنهاء
            result.ok = False
            result.errors.append(str(exc))
            self.signals.error.emit(str(exc))
            return
        self.signals.finished.emit(result)


class ExportSignals(QObject):
    """إشارات تُبث عند انتهاء التصدير."""

    finished = Signal(object)   # emits Path
    error = Signal(str)
    progress = Signal(int, str)  # (0..100, رسالة)


class ExportJob(QRunnable):
    """يبني EPUB من Book عبر EpubWriter داخل خيط."""

    def __init__(self, book: Book, destination: Path) -> None:
        super().__init__()
        # لقطة عميقة: لا تتأثر الكتابة بتحرير المستخدم أثناء البناء في الخيط
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