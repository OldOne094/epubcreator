"""نقطة إدخال التطبيق: تُنشئ QApplication + MainWindow."""
from __future__ import annotations

import os
import sys


def _enable_dpi_awareness() -> None:
    """جعله الوعي بـ High-DPI (يصلّح تشوّه الأزرار/النص الضبابي على الشاشات عالية الدقة)."""
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # per-monitor V1
        except Exception:  # noqa: BLE001 — غير حرج إن لم يتوفر
            pass


def main() -> int:
    _enable_dpi_awareness()

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    # سياسة تقريب عامل القياس حتى لا يُضاعف العناصر أو يشوّهها
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except AttributeError:
        pass

    from app.settings import configure_logging
    from app.ui.main_window import MainWindow

    configure_logging()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    from app.ui.themes import apply_theme

    apply_theme(app, "light")
    window = MainWindow()
    window.show()

    # وضع الدخان (Smoke): يُغلق التطبيق تلقائيًّا بعد ثوانٍ لاختبار إقلاع الحزمة
    if os.environ.get("EPUBCREATOR_SMOKE") == "1":
        from PySide6.QtCore import QTimer

        QTimer.singleShot(2000, app.quit)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())