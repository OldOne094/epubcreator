"""صفحة الغلاف: صورة مستخدم أو توليد تلقائي + إعدادات الضغط + معاينة فورية."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.models import Book
from app.state import BookState
from app.ui.widgets import PageHeader, Section, muted_label


class CoverPage(QWidget):
    """خيارات الغلاف + معاينة الصورة الناتجة (فورية عبر covergen)."""

    def __init__(self, state: BookState) -> None:
        super().__init__()
        self.state = state
        self._loading = False
        self._last_cover_sig = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 18, 24, 18)
        outer.setSpacing(14)
        outer.addWidget(
            PageHeader("الغلاف", "صورة من جهازك أو توليد تلقائي يعتمد ألوان القالب وخطوطه.")
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(14)

        section = Section("مصدر الغلاف")
        row = QHBoxLayout()
        row.setSpacing(14)
        self.user_radio = QRadioButton("صورة من الملف")
        self.auto_radio = QRadioButton("توليد تلقائي")
        row.addWidget(self.user_radio)
        row.addWidget(self.auto_radio)
        row.addStretch(1)
        section.layout.addLayout(row)

        file_row = QHBoxLayout()
        file_row.setSpacing(8)
        self.path_label = muted_label("لا توجد صورة مختارة", wrap=True)
        self.browse_button = QPushButton("اختيار صورة…")
        self.browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_button.clicked.connect(self._browse_image)
        file_row.addWidget(self.path_label, 1)
        file_row.addWidget(self.browse_button)
        section.layout.addLayout(file_row)

        settings = Section(
            "معالجة الصورة",
            "تُقنَّص الصور قبل إدراجها في الكتاب للحفاظ على الحجم الصغير.",
        )
        form = QFormLayout()
        form.setSpacing(10)
        self.compress_check = QCheckBox("ضغط الصور (JPEG جودة 85)")
        self.max_width = QSpinBox()
        self.max_width.setRange(400, 4000)
        self.max_width.setSingleStep(100)
        self.max_width.setSuffix(" px")
        self.image_format = QComboBox()
        self.image_format.addItems(["jpeg", "png", "webp"])
        self.compress_check.toggled.connect(self._on_options)
        self.max_width.valueChanged.connect(self._on_options)
        self.image_format.currentIndexChanged.connect(self._on_options)
        form.addRow(self.compress_check, QLabel(""))
        form.addRow(QLabel("أقصى عرض"), self.max_width)
        form.addRow(QLabel("الصيغة"), self.image_format)
        settings.layout.addLayout(form)
        body_layout.addWidget(section)
        body_layout.addWidget(settings)

        preview_section = Section("المعاينة")
        buttons = QHBoxLayout()
        self.preview_button = QPushButton("توليد معاينة الغلاف")
        self.preview_button.setObjectName("Primary")
        self.preview_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.preview_button.clicked.connect(self.refresh_preview)
        buttons.addWidget(self.preview_button)
        buttons.addStretch(1)
        preview_section.layout.addLayout(buttons)
        self.cover_display = QLabel("")
        self.cover_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_display.setMinimumHeight(320)
        self.cover_display.setScaledContents(False)
        preview_section.layout.addWidget(self.cover_display)
        body_layout.addWidget(preview_section)
        body_layout.addStretch(1)

        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        self.user_radio.toggled.connect(self._on_source)
        self.auto_radio.toggled.connect(self._on_source)

        self.reload()

    # ---- ربط ----
    def reload(self) -> None:
        self._loading = True
        opts = self.state.book.options
        self.user_radio.setChecked(bool(opts.cover_image))
        self.auto_radio.setChecked(not bool(opts.cover_image))
        self.path_label.setText(str(opts.cover_image) if opts.cover_image else "لا توجد صورة مختارة")
        self.compress_check.setChecked(opts.compress_images)
        self.max_width.setValue(int(opts.max_image_width or 1200))
        idx = self.image_format.findText(opts.image_format)
        self.image_format.setCurrentIndex(idx if idx >= 0 else 0)
        self._loading = False
        self.refresh_preview()

    def _browse_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "اختر صورة الغلاف",
            "",
            "صور (*.png *.jpg *.jpeg *.webp);;جميع الملفات (*.*)",
        )
        if path:
            self.state.book.options.cover_image = Path(path)
            self.state.notify()
            self.reload()

    def _on_source(self) -> None:
        if self._loading:
            return
        opts = self.state.book.options
        if self.user_radio.isChecked():
            if not opts.cover_image:
                self._browse_image()
        else:
            opts.cover_image = None
            self.path_label.setText("توليد تلقائي")
            self.state.notify()

    def _on_options(self) -> None:
        if self._loading:
            return
        opts = self.state.book.options
        opts.compress_images = self.compress_check.isChecked()
        opts.max_image_width = self.max_width.value()
        opts.image_format = self.image_format.currentText()
        self.state.notify()

    def refresh_preview(self) -> None:
        """توليد صورة الغلاف الفعلية وعرضها (مع تجاهل أخطاء الخطوط).

        تتحدث حيًّا عند تغيّر العنوان/القالب/الصورة عبر كاش بصمة يتجاهل
        عمليات إعادة التوليد غير المجدية.
        """
        book: Book = self.state.book
        opts = book.options
        if not opts.cover_image and not (opts.auto_cover and book.metadata.title.strip()):
            self.cover_display.setText("أضف عنوانًا في صفحة البيانات لتوليد غلاف تلقائي.")
            self._last_cover_sig = None
            return
        sig = (
            book.metadata.title, book.metadata.author, opts.template,
            opts.title_font, opts.body_font, str(opts.cover_image),
            opts.image_format, opts.max_image_width,
        )
        if sig == self._last_cover_sig:
            return
        try:
            from app.core.covergen import generate_cover_bytes

            data = generate_cover_bytes(book, opts)
            pix = QPixmap()
            pix.loadFromData(data)
            if pix.isNull():
                self.cover_display.setText("تعذّرت معاينة الغلاف.")
                self._last_cover_sig = None
                return
            max_h = 360
            if pix.height() > max_h:
                pix = pix.scaledToHeight(max_h, Qt.TransformationMode.SmoothTransformation)
            self.cover_display.setPixmap(pix)
            self._last_cover_sig = sig
        except Exception:  # noqa: BLE001 — المعاينة لا توقف التطبيق
            self.cover_display.setText("تعذّرت معاينة الغلاف (تأكد من توفر الخطوط).")
            self._last_cover_sig = None
