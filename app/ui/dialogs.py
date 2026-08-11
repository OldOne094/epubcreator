"""حوارات: أخطاء، تقارير تحقق، تقدم."""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QMessageBox, QProgressBar, QVBoxLayout


def error_dialog(parent, message: str) -> None:
    """حوار خطأ موضعي لا يقطع التطبيق."""
    QMessageBox.critical(parent, "خطأ", message)


class ProgressDialog(QDialog):
    """حوار تقدّم بسيط خلال عمل الخلفية."""

    def __init__(self, parent=None, title: str = "جارٍ المعالجة…") -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        layout = QVBoxLayout(self)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)  # مؤشر غير محدد
        layout.addWidget(self.bar)

    def set_max(self, maximum: int) -> None:
        self.bar.setRange(0, maximum)
        self.bar.setValue(0)

    def advance(self) -> None:
        self.bar.setValue(self.bar.value() + 1)