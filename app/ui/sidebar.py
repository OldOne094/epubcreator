"""الشريط الجانبي للتنقل (Sidebar): عنوان التطبيق + خطوات سير العمل + التبديل الليلي."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app import __version__

#: ترتيب الصفحات وخطوات سير العمل (من الرئيسية إلى التصدير)
NAV_ITEMS: list[tuple[str, str]] = [
    ("home", "الرئيسية"),
    ("editor", "المحرر"),
    ("metadata", "البيانات"),
    ("style", "التنسيق والقالب"),
    ("cover", "الغلاف"),
    ("preview", "المعاينة"),
    ("export", "التصدير"),
]

#: أزرار للانتقال السريع لا تعدّ خطوة من سير العمل (غير مستخدمة حاليًّا)
SECONDARY: list[tuple[str, str]] = []


class Sidebar(QWidget):
    """شريط تنقّل عمودي بروابط قابلة للفحص تدعم وضع RTL."""

    def __init__(self, on_navigate, on_toggle_theme, theme_name: str = "light") -> None:  # noqa: ANN001
        super().__init__()
        self._on_navigate = on_navigate
        self._buttons: dict[str, QPushButton] = {}

        self.setFixedWidth(236)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 18, 14, 14)
        outer.setSpacing(4)

        # ---- العنوان ----
        brand = QLabel("EPubCreator")
        brand.setObjectName("PageTitle")
        outer.addWidget(brand)
        tag = QLabel("مصنّع كتب EPUB عربي")
        tag.setObjectName("Muted")
        outer.addWidget(tag)
        outer.addSpacing(8)

        rule = QFrame()
        rule.setObjectName("Divider")
        rule.setFixedHeight(1)
        outer.addWidget(rule)
        outer.addSpacing(10)

        # ---- سير العمل ----
        steps = QLabel("سير العمل")
        steps.setObjectName("SectionTitle")
        outer.addWidget(steps)
        outer.addSpacing(4)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for key, label in NAV_ITEMS:
            btn = QPushButton(label)
            btn.setObjectName("Nav")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(44)
            btn.clicked.connect(lambda _=False, k=key: self._on_navigate(k))
            self._group.addButton(btn)
            self._buttons[key] = btn
            outer.addWidget(btn)

        outer.addStretch(1)
        outer.addSpacing(6)

        # ---- الثيم ----
        self.theme_button = QPushButton("الوضع الداكن" if theme_name == "light" else "الوضع الفاتح")
        self.theme_button.setObjectName("Ghost")
        self.theme_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_button.clicked.connect(on_toggle_theme)
        outer.addWidget(self.theme_button)
        version = QLabel(f"v{__version__}")
        version.setObjectName("Muted")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(version)

    def set_active(self, key: str) -> None:
        """تمييز الصفحة النشطة في الشريط."""
        if key in self._buttons:
            self._buttons[key].setChecked(True)

    def set_theme_label(self, theme_name: str) -> None:
        self.theme_button.setText("الوضع الداكن" if theme_name == "light" else "الوضع الفاتح")
