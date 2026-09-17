"""توليد صورة الغلاف (Pillow) + معالجة صورة المستخدم.

منطق الغلاف المُختار:
1. إن وجدت صورة مستخدم (options.cover_image) → تُستخدم وتُعالَج (resize/ضغط).
2. وإلا و auto_cover → توليد غلاف من العنوان/المؤلف.
3. وإلا → بلا غلاف (يرجعه المتصل إلى None).

إصلاحات مهمة:
- تكوين الحروف العربية: تعتمد Pillow الحالية على Raqm وهو غير متوفّر هنا،
  لذلك نُشكّل النص يدويًّا (arabic_reshaper) ونحوّله إلى ترتيب بصري
  (python-bidi) قبل الرسم، فيخرج العنوان متصلاً لا مقطّعًا.
- احترام تنسيق الكتاب: تُؤخذ ألوان القالب المختار وخطوطه (title_font/
  body_font) من خيارات الكتاب بدل الألوان الثابتة.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.models import Book

_COVER_W, _COVER_H = 1200, 1600
_FALLBACK_BG = (30, 34, 45)
_FALLBACK_FG = (255, 255, 255)
_FALLBACK_ACCENT = (216, 173, 92)

# عائلات الخطوط (من إعدادات الكتاب) → ملفات Windows
_FONT_PATHS: dict[str, list[str]] = {
    "amiri": ["C:/Windows/Fonts/Amiri.ttf"],
    "traditional arabic": ["C:/Windows/Fonts/trado.ttf"],
    "arial": ["C:/Windows/Fonts/arial.ttf"],
    "times new roman": ["C:/Windows/Fonts/times.ttf"],
    "tahoma": ["C:/Windows/Fonts/tahoma.ttf"],
}
_ARABIC_SAFE = ["C:/Windows/Fonts/Amiri.ttf", "C:/Windows/Fonts/trado.ttf"]


def _shape(text: str) -> str:
    """تشكيل النص العربي + الترتيب البصري (يعمل بلا Raqm)."""
    if not text or not re.search(r"[\u0600-\u06FF]", text):
        return text
    from arabic_reshaper import reshape
    from bidi.algorithm import get_display
    return get_display(reshape(text))


def _hex_to_rgb(value: str, fallback) -> tuple[int, int, int]:  # noqa: ANN001
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    try:
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return fallback


def _template_colors(template: str) -> dict[str, tuple[int, int, int]]:
    """استخراج ألوان القالب من CSS (خلفية/نص/عناوين) إن وُجدت."""
    colors = {"bg": _FALLBACK_BG, "fg": _FALLBACK_FG, "accent": _FALLBACK_ACCENT}
    from app.core.templates import _TEMPLATES

    css = _TEMPLATES.get(template or "", {}).get("css", "")
    for prop, key in (("background", "bg"), ("color", "fg")):
        m = re.search(rf"{prop}:\s*(#[0-9a-fA-F]{{3,8}})", css)
        if m:
            colors[key] = _hex_to_rgb(m.group(1), colors[key])
    m = re.search(r"h1\s*\{[^}]*color:\s*(#[0-9a-fA-F]{3,8})", css)
    if m:
        colors["accent"] = _hex_to_rgb(m.group(1), colors["accent"])
    return colors


def _load_font(size: int, family: str = "") -> ImageFont.FreeTypeFont:
    """تحميل الخط: من العائلة المطلوبة ثم عائلات عربية داعمة للشكل ثم Arial."""
    candidates: list[str] = []
    if family:
        candidates.extend(_FONT_PATHS.get(family.strip().lower(), []))
    candidates.extend(_ARABIC_SAFE)
    candidates.append("C:/Windows/Fonts/arial.ttf")
    for path in candidates:
        if path and Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _fit_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> str:
    """اقتصاص النص ليلائم عرض الصورة مع علامة حذف (بعد التشكيل)."""
    if not text:
        return text
    if draw.textbbox((0, 0), text, font=font)[2] <= max_width:
        return text
    ellipsis = "…"
    trimmed = text
    while trimmed and draw.textbbox((0, 0), trimmed + ellipsis, font=font)[2] > max_width:
        trimmed = trimmed[:-1]
    return (trimmed + ellipsis) if trimmed else ellipsis


def _wrap_title(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int = 3) -> list[str]:
    """التفاف العنوان على عدة أسطر (يفضل حدود الكلمات) مع اقتصاص آمن."""
    if not text:
        return []
    words = text.split()
    if not words:
        return [_fit_text(draw, text, font, max_width)]
    lines: list[str] = []
    current = ""
    for w in words:
        trial = f"{current} {w}".strip()
        if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = w
            if len(lines) == max_lines - 1:
                # السطر الأخير: ادمج الباقي مع اقتصاص
                rest = " ".join([current] + words[words.index(w) + 1 :])
                lines.append(_fit_text(draw, rest, font, max_width))
                return lines
    if current:
        lines.append(_fit_text(draw, current, font, max_width))
    return lines[:max_lines]


def _save_with_format(buf: io.BytesIO, img: Image.Image, options) -> None:  # noqa: ANN001
    """حفظ الصورة بالصيغة الفعلية المختارة (jpeg/png/webp) دون خلط."""
    fmt = (getattr(options, "image_format", "jpeg") or "jpeg").lower()
    if fmt == "png":
        img.save(buf, format="PNG", optimize=True)
    elif fmt == "webp":
        img.save(buf, format="WEBP", quality=85, method=4)
    else:
        img.save(buf, format="JPEG", quality=85, optimize=True, progressive=True)


def generate_cover_bytes(book: Book, options) -> bytes:  # noqa: ANN001
    """إرجاع بايت الغلاف: صورة المستخدم أو توليد تلقائي."""
    cover_path = getattr(options, "cover_image", None)
    if cover_path is not None and Path(cover_path).exists():
        return _user_cover_bytes(Path(cover_path), options)
    if not (getattr(options, "auto_cover", True) and (book.metadata.title or "").strip()):
        raise ValueError("لا صورة غلاف ولا عنوان للتوليد التلقائي")
    return _auto_cover_bytes(book, options)


def cover_bytes(book: Book, options) -> bytes:  # noqa: ANN001
    """اسم بديل متوافق للاستدعاء من EpubWriter."""
    return generate_cover_bytes(book, options)


def _auto_cover_bytes(book: Book, options) -> bytes:  # noqa: ANN001
    colors = _template_colors(options.template)
    bg, fg, accent = colors["bg"], colors["fg"], colors["accent"]

    img = Image.new("RGB", (_COVER_W, _COVER_H), bg)
    draw = ImageDraw.Draw(img)

    # شريط زخرفي بلون القالب
    draw.rectangle([0, _COVER_H - 200, _COVER_W, _COVER_H], fill=accent)

    title_font = _load_font(96, options.title_font)
    sub_font = _load_font(56, options.body_font)

    title_raw = book.metadata.title or "بلا عنوان"
    author_raw = book.metadata.author or ""
    title_shaped = _shape(title_raw)
    author_shaped = _shape(author_raw) if author_raw else ""
    title_lines = _wrap_title(draw, title_shaped, title_font, _COVER_W - 200)
    author_line = _fit_text(draw, author_shaped, sub_font, _COVER_W - 200) if author_shaped else ""

    # رسم العنوان متعدد الأسطر متمركزًا
    line_heights = []
    for ln in title_lines:
        bbox = draw.textbbox((0, 0), ln, font=title_font)
        line_heights.append(bbox[3] - bbox[1])
    line_gap = 12
    total_h = sum(line_heights) + line_gap * max(len(title_lines) - 1, 0)
    ty = _COVER_H // 3 - total_h // 2
    for ln, lh in zip(title_lines, line_heights):
        tbox = draw.textbbox((0, 0), ln, font=title_font)
        tx = (_COVER_W - (tbox[2] - tbox[0])) // 2
        draw.text((tx, ty), ln, font=title_font, fill=fg)
        ty += lh + line_gap

    if author_line:
        abox = draw.textbbox((0, 0), author_line, font=sub_font)
        draw.text(
            ((_COVER_W - (abox[2] - abox[0])) // 2, ty + 60),
            author_line,
            font=sub_font,
            fill=accent,
        )

    buf = io.BytesIO()
    _save_with_format(buf, img, options)
    return buf.getvalue()


def _user_cover_bytes(path: Path, options) -> bytes:  # noqa: ANN001
    """فتح صورة المستخدم وتكييفها (تدوير EXIF + دمج شفافية + resize + ضغط)."""
    from PIL import ImageOps

    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "LA", "PA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            alpha = img.split()[-1]
            bg.paste(img.convert("RGB"), mask=alpha)
            img = bg
        else:
            img = img.convert("RGB")
        max_w = int(options.max_image_width or 1200)
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        _save_with_format(buf, img, options)
    return buf.getvalue()
