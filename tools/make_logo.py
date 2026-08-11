"""مولِّد شعار EPubCreator — كتاب مفتوح على لوحة ذهبية.

يُنتج `app/assets/logo.png` (512³) و `app/assets/EPubCreator.ico`
(أيقونة متعددة الأبعاد للـ EXE). يعمل بدون حزمة واجهة مرئية (offscreen).
الاستخدام:  python tools/make_logo.py
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QIODevice, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QColor,
    QGuiApplication,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)

ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
LOGO_SIZE = 512

_GOLD_TOP = QColor("#cfa347")
_GOLD_BOTTOM = QColor("#8a5f12")
_PAGE = QColor("#fff7e6")
_PAGE_EDGE = QColor("#e8d9b8")
_SPINE = QColor("#f2e4c3")
_LINES = QColor("#d8c69a")


def render(size: int) -> QImage:
    """رسم الشعار بحجم given (شفاف الخلفية) عبر QPainter."""
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    radius = size * 0.22
    tile = QPainterPath()
    tile.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
    p.setClipPath(tile)
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, _GOLD_TOP)
    grad.setColorAt(1.0, _GOLD_BOTTOM)
    p.fillRect(0, 0, size, size, grad)

    _book(p, size)
    p.end()
    return img


def _book(p: QPainter, s: float) -> None:
    """كتاب مفتوح أبيض في منتصف اللوحة."""
    cx = s * 0.5
    top = s * 0.30
    w = s * 0.66
    h = s * 0.44
    r = s * 0.035

    left = QRectF(cx - w / 2, top, w / 2, h)
    right = QRectF(cx, top, w / 2, h)

    p.setPen(QPen(_PAGE_EDGE, max(s * 0.012, 1)))
    p.setBrush(_PAGE)
    p.drawRoundedRect(left.x(), left.y(), left.width(), left.height(), r, r)
    p.drawRoundedRect(right.x(), right.y(), right.width(), right.height(), r, r)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(_SPINE)
    p.drawRoundedRect(
        QRectF(cx - s * 0.015, top + s * 0.02, s * 0.03, h - s * 0.04),
        s * 0.015,
        s * 0.015,
    )

    pen = QPen(_LINES, max(s * 0.008, 1))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    for i in range(1, 4):
        y = top + h * 0.22 * i
        p.drawLine(QPointF(left.right() - s * 0.05, y), QPointF(left.left() + s * 0.045, y))
        p.drawLine(QPointF(right.left() + s * 0.045, y), QPointF(right.right() - s * 0.05, y))

    # وهج علوي خفيف فوق صفحات الشعاع
    p.setPen(Qt.PenStyle.NoPen)
    glow = QLinearGradient(0, top, 0, top + h * 0.5)
    glow.setColorAt(0.0, QColor(255, 247, 230, 90))
    glow.setColorAt(1.0, QColor(255, 247, 230, 0))
    p.setBrush(glow)
    p.drawRoundedRect(right.x(), right.y(), right.width(), right.height() * 0.5, r, r)


def _to_png_bytes(qimg: QImage) -> bytes:
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    qimg.save(buf, "PNG")
    data = bytes(buf.data())
    buf.close()
    return data


def main() -> int:
    _ = QGuiApplication(sys.argv)

    from PIL import Image

    roots = Path(__file__).resolve().parents
    assets = roots[1] / "app" / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    big = render(LOGO_SIZE)
    (assets / "logo.png").write_bytes(_to_png_bytes(big))

    frame = render(256)
    Image.open(io.BytesIO(_to_png_bytes(frame))).save(
        assets / "EPubCreator.ico",
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
    )
    print(f"written: {assets / 'logo.png'}  {assets / 'EPubCreator.ico'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())