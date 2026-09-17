"""صفحة التصدير: إصدار EPUB + الوجهة + التصدير في الخلفية + تقرير التحقق."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.state import BookState
from app.ui.widgets import PageHeader, Section, muted_label


class ExportPage(QWidget):
    """إعدادات التصدير + زر التصدير + تقرير التحقق بعد الانتهاء."""

    def __init__(self, state: BookState, on_export) -> None:  # noqa: ANN001
        super().__init__()
        self.state = state
        self._on_export = on_export

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 18, 24, 18)
        outer.setSpacing(14)
        outer.addWidget(
            PageHeader("التصدير", "اختر إصدار EPUB ووجهة الحفظ ثم صدّر؛ يتحقق التطبيق من النتيجة تلقائيًّا.")
        )

        section = Section("الإعدادات")
        form = QFormLayout()
        form.setSpacing(10)

        self.version_combo = QComboBox()
        self.version_combo.addItem("EPUB 3 (موصى به)", 3)
        self.version_combo.addItem("EPUB 2 (توافق أوسع)", 2)
        self.version_combo.currentIndexChanged.connect(self._on_version)
        form.addRow(QLabel("الإصدار"), self.version_combo)

        dest_row = QHBoxLayout()
        dest_row.setSpacing(8)
        self.destination = QLineEdit()
        self.destination.setPlaceholderText("مسار حفظ ملف .epub (فارغ = يُطلب عند التصدير)")
        browse = QPushButton("تصفح…")
        browse.setCursor(Qt.CursorShape.PointingHandCursor)
        browse.clicked.connect(self._browse_destination)
        dest_row.addWidget(self.destination, 1)
        dest_row.addWidget(browse)
        form.addRow(QLabel("الوجهة"), dest_row)

        self.book_info = muted_label("")
        form.addRow(QLabel("الكتاب"), self.book_info)
        section.layout.addLayout(form)
        outer.addWidget(section)

        export_row = QHBoxLayout()
        export_row.setSpacing(10)
        self.export_button = QPushButton("تصدير EPUB")
        self.export_button.setObjectName("Primary")
        self.export_button.setMinimumHeight(42)
        self.export_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_button.clicked.connect(self.trigger_export)
        export_row.addWidget(self.export_button)
        export_row.addStretch(1)
        outer.addLayout(export_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("")
        self.progress.hide()
        outer.addWidget(self.progress)

        result_section = Section("تقرير التحقق", "النتيجة تظهر هنا بعد التصدير.")
        self.report_list = QListWidget()
        self.report_list.setMinimumHeight(140)
        result_section.layout.addWidget(self.report_list)
        self.open_folder_button = QPushButton("فتح مجلد الإخراج")
        self.open_folder_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_folder_button.clicked.connect(self._open_folder)
        result_section.layout.addWidget(self.open_folder_button)
        outer.addWidget(result_section, 1)

        self._last_dest: Path | None = None
        self.refresh()

    # ---- عرض ----
    def refresh(self) -> None:
        opts = self.state.book.options
        idx = self.version_combo.findData(opts.epub_version)
        self.version_combo.setCurrentIndex(idx if idx >= 0 else 0)
        meta = self.state.book.metadata
        title = meta.title.strip() or "(بلا عنوان)"
        self.book_info.setText(f"{title} · {len(self.state.book.chapters)} فصلًا")

    def _on_version(self) -> None:
        self.state.book.options.epub_version = int(self.version_combo.currentData() or 3)
        self.state.notify()

    def _default_filename(self) -> str:
        from app.models import sanitize_filename

        return sanitize_filename(self.state.book.metadata.title.strip() or "book") + ".epub"

    def _browse_destination(self) -> None:
        default = self.destination.text().strip() or self._default_filename()
        path, _ = QFileDialog.getSaveFileName(self, "احفظ EPUB", default, "EPUB (*.epub)")
        if path:
            self.destination.setText(path)

    def _open_folder(self) -> None:
        if not self._last_dest:
            return
        import subprocess

        subprocess.Popen(["explorer", "/select,", str(self._last_dest)])

    # ---- تصدير ----
    def trigger_export(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        from app.models import has_invalid_filename_chars, is_valid_isbn
        from app.ui.dialogs import error_dialog

        book = self.state.book
        if not book.chapters:
            error_dialog(self, "لا يوجد أي فصل للتصدير — استورد كتابًا أولًا.")
            return
        if not book.metadata.title.strip():
            error_dialog(self, "أُدخل عنوان الكتاب أولًا قبل التصدير (صفحة البيانات).")
            return
        isbn = book.metadata.isbn.strip()
        if isbn and not is_valid_isbn(isbn):
            answer = QMessageBox.question(
                self,
                "ISBN غير صالح",
                f"الرقم «{isbn}» ليس ISBN-10/13 صالحًا. المتابعة ستكتبه كما هو في الملف.\nهل تريد المتابعة؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        dest = self.destination.text().strip()
        if not dest:
            start, _ = QFileDialog.getSaveFileName(
                self, "احفظ EPUB", self._default_filename(), "EPUB (*.epub)"
            )
            if not start:
                return
            dest = start
        dest_path = Path(dest)
        if not dest_path.suffix:
            dest_path = dest_path.with_suffix(".epub")
        # محارف غير صالحة في اسم الملف؟
        if has_invalid_filename_chars(dest_path.name):
            error_dialog(
                self,
                f"اسم الملف يحتوي محارف غير صالحة (<>:\"/\\|?*): {dest_path.name}",
            )
            return
        # مجلد الوجهة: أنشئه أو ارفض بوضوح
        try:
            if dest_path.parent and str(dest_path.parent) not in ("", "."):
                dest_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            error_dialog(self, f"تعذّر إنشاء مجلد الوجهة: {exc}")
            return
        # تأكيد الكتابة فوق ملف موجود أُدخل يدويًا
        if dest_path.exists():
            answer = QMessageBox.question(
                self,
                "ملف موجود",
                f"الملف «{dest_path.name}» موجود. هل تريد الكتابة فوقه؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        dest = str(dest_path)
        self.destination.setText(dest)
        self.progress.setValue(0)
        self.progress.setFormat("جارٍ التصدير…")
        self.progress.show()
        self._on_export(Path(dest))

    def show_progress(self, value: int, message: str) -> None:
        """تحديث شريط التقدم أثناء التصدير (0..100)."""
        self.progress.setValue(int(value))
        self.progress.setFormat(message)

    def show_result(self, path: Path, issues) -> None:  # noqa: ANN001
        """عرض نتيجة التصدير + تقرير التحقق (issues: قائمة ValidationIssue)."""
        self._last_dest = path
        self.progress.hide()
        self.report_list.clear()
        if issues:
            for issue in issues:
                item = QListWidgetItem(issue.message)
                if issue.severity == "error":
                    item.setForeground(QColor("#b5452f"))
                else:
                    item.setForeground(QColor("#a8761d"))
                self.report_list.addItem(item)
        else:
            item = QListWidgetItem("الكتاب سليم — لا توجد أخطاء تحقق.")
            item.setForeground(QColor("#2e7d46"))
            self.report_list.addItem(item)
