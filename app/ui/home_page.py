"""صفحة الرئيسية: نظرة عامة على الكتاب النشط + حالة البداية قبل الاستيراد."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.state import BookState
from app.ui.widgets import PageHeader, Section, muted_label


class HomePage(QWidget):
    """حالة فارغة (استيراد أول) أو ملخّص الكتاب الحالي مع إجراءات سريعة."""

    def __init__(self, state: BookState, on_import, on_navigate) -> None:  # noqa: ANN001
        super().__init__()
        self.state = state
        self._on_import = on_import
        self._on_navigate = on_navigate

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 18, 24, 18)
        outer.setSpacing(14)
        outer.addWidget(PageHeader("الرئيسية", "ابدأ بإنشاء كتاب EPUB عربي أو تابع العمل على كتابك الحالي."))

        self.overview = Section("الكتاب الحالي")
        self.overview.layout.setSpacing(8)
        self.title_label = QLabel("")
        self.title_label.setObjectName("PageTitle")
        self.overview.layout.addWidget(self.title_label)
        self.author_label = muted_label("")
        self.overview.layout.addWidget(self.author_label)
        self.stats_label = muted_label("")
        self.overview.layout.addWidget(self.stats_label)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.to_editor = QPushButton("فتح المحرر")
        self.to_editor.setCursor(Qt.CursorShape.PointingHandCursor)
        self.to_editor.clicked.connect(lambda: self._on_navigate("editor"))
        self.to_preview = QPushButton("معاينة")
        self.to_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.to_preview.clicked.connect(lambda: self._on_navigate("preview"))
        self.to_export = QPushButton("تصدير")
        self.to_export.setObjectName("Primary")
        self.to_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.to_export.clicked.connect(lambda: self._on_navigate("export"))
        actions.addWidget(self.to_editor)
        actions.addWidget(self.to_preview)
        actions.addWidget(self.to_export)
        actions.addStretch(1)
        self.overview.layout.addLayout(actions)
        outer.addWidget(self.overview)

        # ---- حالة البداية ----
        self.empty = Section("ابدأ بكتاب جديد")
        hint = muted_label(
            "استورد ملفًّا نصيًّا (TXT / Markdown / HTML / DOCX / RTF) وستُكتشف الفصول تلقائيًّا. "
            "يمكنك أيضًا سحب الملفات وإفلاتها في أي مكان داخل النافذة."
        )
        self.empty.layout.addWidget(hint)
        import_btn = QPushButton("استيراد ملفات…")
        import_btn.setObjectName("Primary")
        import_btn.setMinimumHeight(42)
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.clicked.connect(self._on_import)
        self.empty.layout.addWidget(import_btn, 0, Qt.AlignmentFlag.AlignRight)
        outer.addWidget(self.empty)

        outer.addStretch(1)
        self.refresh()

    def refresh(self) -> None:
        """تحديث الملخّص حسب حالة الكتاب."""
        meta = self.state.book.metadata
        n = len(self.state.book.chapters)
        has_book = bool(meta.title.strip() or n)

        self.overview.setVisible(has_book)
        self.empty.setVisible(not has_book)

        if not has_book:
            return
        self.title_label.setText(meta.title.strip() or "(بلا عنوان)")
        self.author_label.setText(f"المؤلف: {meta.author.strip() or 'غير محدد'}")
        src = self.state.book.source_files
        sources = "، ".join(p.name for p in src[:3])
        extra = f" +{len(src) - 3}" if len(src) > 3 else ""
        self.stats_label.setText(f"{n} فصلًا · المصدر: {sources}{extra}")
