"""مكوّنات واجهة مشتركة: بطاقات الأقسام والعناوين والشريط الإرشادي."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


def muted_label(text: str, wrap: bool = True) -> QLabel:
    """نص ثانوي (مُصغّر/رمادي) قابل للالتفاف."""
    label = QLabel(text)
    label.setObjectName("Muted")
    if wrap:
        label.setWordWrap(True)
    return label


class Section(QFrame):
    """بطاقة قسم بعنوان ووصف اختياريين وحاوية للمحتوى.

    ```python
    sec = Section("القالب", "اختر قالبًا جاهزًا")
    sec.layout.addWidget(...)
    ```
    """

    def __init__(self, title: str = "", description: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(10)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("SectionTitle")
        outer.addWidget(self.title_label)

        self.desc_label = muted_label(description)
        self.desc_label.hide()
        if description:
            self.desc_label.show()
            outer.addWidget(self.desc_label)

        self.layout = QVBoxLayout()
        self.layout.setSpacing(10)
        outer.addLayout(self.layout)

    def set_description(self, text: str) -> None:
        self.desc_label.setText(text)
        self.desc_label.setVisible(bool(text))


class PageHeader(QWidget):
    """رأس الصفحة: عنوان + وصف اختياري + شارة إحصائية يسارها."""

    def __init__(self, title: str, description: str = "", badge: str = "") -> None:
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)

        texts = QVBoxLayout()
        texts.setSpacing(3)
        texts.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("PageTitle")
        texts.addWidget(self.title_label)
        self.desc_label = muted_label(description)
        self.desc_label.hide()
        if description:
            self.desc_label.show()
            texts.addWidget(self.desc_label)
        row.addLayout(texts, 1)

        self.badge = QLabel(badge)
        self.badge.setObjectName("Badge")
        self.badge.hide()
        if badge:
            self.badge.show()
        row.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignTop)
