"""الصفحات الأساسية: محرر الفصول (بقائمة وترتيب) + البيانات الوصفية المنظمة."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.state import BookState
from app.ui.widgets import PageHeader, Section, muted_label


class ChapterEditor(QWidget):
    """قائمة فصول + حقل عنوان + محرر جسم، مع إضافة/حذف/إعادة ترتيب.

    يحافظ على السمات المألوفة للاختبارات: `chapter_list` / `title_edit` / `body_edit`.
    """

    def __init__(self, state: BookState) -> None:
        super().__init__()
        self.state = state
        self._loading = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 18, 24, 18)
        outer.setSpacing(14)
        outer.addWidget(PageHeader("المحرر", "حرّر فصول الكتاب: أعد كتابة النص أو أضف فصلًا جديدًا."))

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(10)

        # ---- عمود الفصول ----
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        left_layout.addWidget(QLabel("فصول الكتاب"))
        self.chapter_list = QListWidget()
        self.chapter_list.setToolTip("اختر فصلًا للتعديل")
        self.chapter_list.setMinimumWidth(190)
        self.chapter_list.currentRowChanged.connect(self._on_row_changed)
        left_layout.addWidget(self.chapter_list, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.add_button = QPushButton("+ فصل")
        self.add_button.setToolTip("إضافة فصل جديد")
        self.add_button.clicked.connect(self._add_chapter)
        self.remove_button = QPushButton("حذف")
        self.remove_button.setToolTip("حذف الفصل الحالي")
        self.remove_button.clicked.connect(self._remove_chapter)
        self.move_up_button = QPushButton("↑")
        self.move_up_button.setToolTip("نقل الفصل لأعلى")
        self.move_up_button.clicked.connect(lambda: self._move_chapter(-1))
        self.move_down_button = QPushButton("↓")
        self.move_down_button.setToolTip("نقل الفصل لأسفل")
        self.move_down_button.clicked.connect(lambda: self._move_chapter(1))
        self.undo_button = QPushButton("تراجع")
        self.undo_button.setToolTip("التراجع عن آخر عملية على الفصول")
        self.undo_button.clicked.connect(self._undo)
        self.redo_button = QPushButton("إعادة")
        self.redo_button.setToolTip("إعادة ما أُلغي بالتراجع")
        self.redo_button.clicked.connect(self._redo)
        for b in (
            self.add_button, self.remove_button, self.move_up_button,
            self.move_down_button, self.undo_button, self.redo_button,
        ):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_row.addWidget(b)
        left_layout.addLayout(btn_row)
        splitter.addWidget(left)

        # ---- عمود التحرير ----
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("عنوان الفصل")
        self.title_edit.setToolTip("عنوان الفصل الحالي")
        self.title_edit.textChanged.connect(self._on_title_edited)
        right_layout.addWidget(self.title_edit)
        self.body_edit = QTextEdit()
        self.body_edit.setToolTip("نص الفصل (سطر فارغ = فقرة جديدة، والأسطر القصيرة تُحفظ مستقلة)")
        right_layout.addWidget(self.body_edit, 1)
        self.count_label = muted_label("")
        right_layout.addWidget(self.count_label)
        splitter.addWidget(right)

        splitter.setStretchFactor(1, 1)
        outer.addWidget(splitter, 1)

        self.title_edit.textChanged.connect(self._on_title_edited)
        self.body_edit.textChanged.connect(self._on_body_edited)
        self.body_edit.textChanged.connect(self._update_count)

        self.reload()

    # ---- عرض ----
    def reload(self) -> None:
        self._loading = True
        self.chapter_list.clear()
        for ch in self.state.book.chapters:
            self.chapter_list.addItem(ch.title or "(بلا عنوان)")
        if self.state.has_chapters:
            self.chapter_list.setCurrentRow(self.state.current_index)
            self._loading = False
            self._show_current()
        else:
            self.title_edit.clear()
            self.body_edit.clear()
            self._loading = False
        self._update_count()

    def _update_count(self) -> None:
        n = len(self.state.book.chapters)
        words = len(self.body_edit.toPlainText().split())
        self.count_label.setText(f"{n} فصلًا · {words} كلمة في الفصل الحالي")

    # ---- إدارة الفصول ----
    def _add_chapter(self) -> None:
        self.state.add_chapter()
        self.reload()
        self.title_edit.setFocus()

    def _remove_chapter(self) -> None:
        if not self.state.has_chapters:
            return
        ch = self.state.current_chapter()
        name = (ch.title.strip() or "(بلا عنوان)") if ch is not None else "(بلا عنوان)"
        answer = QMessageBox.question(
            self,
            "حذف الفصل",
            f"حذف فصل «{name}»؟ لا يمكن التراجع عن هذا الإجراء.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.state.remove_chapter()
        self.reload()

    def _move_chapter(self, delta: int) -> None:
        if not self.state.has_chapters:
            return
        source = self.state.current_index
        target = source + delta
        if not (0 <= target < len(self.state.book.chapters)):
            return
        self.state.move_chapter(source, target)
        self.reload()
        self.chapter_list.setCurrentRow(target)

    def _undo(self) -> None:
        self.state.undo()
        self.reload()

    def _redo(self) -> None:
        self.state.redo()
        self.reload()

    # ---- إشعارات ----
    def _on_row_changed(self, row: int) -> None:
        if self._loading or row < 0:
            return
        self.state.select_chapter(row)
        self._show_current()

    def _on_title_edited(self) -> None:
        if self._loading:
            return
        self.state.update_current_title(self.title_edit.text())

    def _on_body_edited(self) -> None:
        if self._loading:
            return
        self.state.update_current_body(self.body_edit.toPlainText())

    def _show_current(self) -> None:
        ch = self.state.current_chapter()
        if ch is None:
            return
        self._loading = True
        self.title_edit.setText(ch.title)
        self.body_edit.setPlainText(ch.body)
        item = self.chapter_list.currentItem()
        if item is not None:
            item.setText(ch.title or "(بلا عنوان)")
        self._loading = False


_FIELD_MAP = (
    ("title", "العنوان", "بيانات أساسية"),
    ("author", "المؤلف", "بيانات أساسية"),
    ("translator", "المترجم", "بيانات أساسية"),
    ("publisher", "الناشر", "بيانات أساسية"),
    ("description", "الوصف", "بيانات أساسية"),
    ("language", "اللغة", "بيانات أساسية"),
    ("isbn", "الرقم المعياري ISBN", "بيانات إضافية"),
    ("series", "السلسلة", "بيانات إضافية"),
    ("part", "الجزء", "بيانات إضافية"),
    ("rights", "الحقوق", "بيانات إضافية"),
    ("keywords", "الكلمات المفتاحية", "بيانات إضافية"),
)

_LANGUAGES = (
    ("ar", "العربية"),
    ("en", "الإنجليزية"),
    ("fr", "الفرنسية"),
    ("de", "الألمانية"),
    ("es", "الإسبانية"),
    ("tr", "التركية"),
    ("ur", "الأردية"),
    ("other", "أخرى"),
)


class MetadataPage(QWidget):
    """نموذج البيانات الوصفية منظمًا في أقسام، مربوط بـ BookState."""

    def __init__(self, state: BookState) -> None:
        super().__init__()
        self.state = state
        self._loading = False
        self._fields: dict[str, QLineEdit] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 18, 24, 18)
        outer.setSpacing(14)
        outer.addWidget(
            PageHeader(
                "البيانات",
                "العنوان إلزامي قبل التصدير؛ البقية اختيارية وتُكتب داخل ملف EPUB.",
                badge="مطلوب: العنوان",
            )
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(14)

        basic = Section("بيانات أساسية", "العنوان والمؤلف والناشر والوصف واللغة.")
        basic_form = QFormLayout()
        basic_form.setSpacing(10)
        basic_form.setHorizontalSpacing(18)
        body_layout.addWidget(basic)

        extra = Section("بيانات إضافية", "ISBN والسلسلة والحقوق والكلمات المفتاحية.")
        extra_form = QFormLayout()
        extra_form.setSpacing(10)
        extra_form.setHorizontalSpacing(18)

        self.description = QTextEdit()
        self.description.setFixedHeight(110)
        self.description.setPlaceholderText("نبذة عن الكتاب…")
        self.description.textChanged.connect(self._on_edited)

        self.language = QComboBox()
        for code, name in _LANGUAGES:
            self.language.addItem(name, code)
        self.language.currentIndexChanged.connect(self._on_edited)

        for attr, label, group in _FIELD_MAP:
            if attr == "description":
                widget: QWidget = self.description
            elif attr == "language":
                widget = self.language
            else:
                edit = QLineEdit()
                edit.textChanged.connect(self._on_edited)
                self._fields[attr] = edit
                widget = edit
            form = basic_form if group == "بيانات أساسية" else extra_form
            form.addRow(QLabel(label), widget)

        basic.layout.addLayout(basic_form)
        extra.layout.addLayout(extra_form)
        body_layout.addWidget(extra)
        body_layout.addStretch(1)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        self.reload()

    def reload(self) -> None:
        self._loading = True
        meta = self.state.book.metadata
        for attr, edit in self._fields.items():
            edit.setText(getattr(meta, attr, ""))
        self.description.setPlainText(meta.description)
        code = meta.language or "ar"
        idx = self.language.findData(code)
        self.language.setCurrentIndex(idx if idx >= 0 else 0)
        self._loading = False

    def _on_edited(self) -> None:
        if self._loading:
            return
        meta = self.state.book.metadata
        for attr, edit in self._fields.items():
            setattr(meta, attr, edit.text())
        meta.description = self.description.toPlainText()
        meta.language = self.language.currentData() or "ar"


def build_pages(state: BookState) -> dict[str, QWidget]:
    """إنشاء الصفحات الأساسية الجاهزة للمعرض الرئيسي."""
    return {"editor": ChapterEditor(state), "metadata": MetadataPage(state)}
