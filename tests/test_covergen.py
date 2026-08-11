"""اختبارات الغلاف (covergen): تشكيل عربي، ألوان القالب، توليد JPEG."""
from __future__ import annotations

import io

from PIL import Image

from app.models import Book, EpubOptions, Metadata
from app.core.covergen import _shape, _template_colors, generate_cover_bytes


def _book(title: str = "عنوان", author: str = "مؤلف") -> Book:
    b = Book()
    b.metadata = Metadata(title=title, author=author)
    return b


def test_shape_joins_arabic_letters():
    shaped = _shape("السلام عليكم")
    # التشكيل يُخرج أشكال العرض العربيّة (نطاقات FB50-FDFF / FE70-FEFF)
    assert shaped != "السلام عليكم"
    assert any(0xFE70 <= ord(c) <= 0xFEFF or 0xFB50 <= ord(c) <= 0xFDFF for c in shaped)


def test_shape_keeps_latin_unchanged():
    assert _shape("Hello 123") == "Hello 123"


def test_shape_empty_unchanged():
    assert _shape("") == ""


def test_cover_bytes_valid_jpeg():
    data = generate_cover_bytes(_book(), EpubOptions())
    img = Image.open(io.BytesIO(data))
    assert img.format == "JPEG"
    assert img.size == (1200, 1600)


def test_cover_user_image_used():
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "c.png"
        Image.new("RGB", (200, 300), (200, 30, 30)).save(p)
        opts = EpubOptions()
        opts.cover_image = p
        data = generate_cover_bytes(_book(), opts)
        img = Image.open(io.BytesIO(data))
        assert img.format in {"JPEG", "PNG"}


def test_template_colors_classic_palette():
    colors = _template_colors("classic")
    assert colors["accent"] != (216, 173, 92)  # ذهب القالب المخصص وليس الافتراضي
    assert sum(colors["bg"]) < sum((255, 255, 255))  # خلفية داكنة


def test_template_colors_fallback_defaults():
    colors = _template_colors("")
    assert colors == {"bg": (30, 34, 45), "fg": (255, 255, 255), "accent": (216, 173, 92)}
