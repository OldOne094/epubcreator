"""حفظ/فتح مشروع EPubCreator (صيغة .epubproj = JSON).

يحفظ الكتاب كاملًا: البيانات الوصفية + خيارات التنسيق/الغلاف + الفصول +
ملفات المصدر. المسارات تُخزَّن نصًّا وتُعاد كـ Path.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.models import Book, Chapter, EpubOptions, Metadata, ParagraphFormat

_FORMAT_VERSION = 1


# ------------------------------------------------------------- تسلسل ---

def _meta_to_dict(m: Metadata) -> dict:
    return {
        "title": m.title,
        "author": m.author,
        "translator": m.translator,
        "publisher": m.publisher,
        "description": m.description,
        "keywords": m.keywords,
        "language": m.language,
        "isbn": m.isbn,
        "series": m.series,
        "part": m.part,
        "rights": m.rights,
    }


def _meta_from_dict(d: dict) -> Metadata:
    return Metadata(**{k: d.get(k, "") for k in (
        "title", "author", "translator", "publisher", "description",
        "keywords", "language", "isbn", "series", "part", "rights",
    )})


def _para_to_dict(p: ParagraphFormat) -> dict:
    return {
        "alignment": p.alignment,
        "line_height": p.line_height,
        "spacing_after": p.spacing_after,
        "first_line_indent": p.first_line_indent,
        "font_size": p.font_size,
        "margin_top": p.margin_top,
        "margin_bottom": p.margin_bottom,
        "color": p.color,
    }


def _para_from_dict(d: dict) -> ParagraphFormat:
    p = ParagraphFormat()
    for k in (
        "alignment", "line_height", "spacing_after", "first_line_indent",
        "font_size", "margin_top", "margin_bottom", "color",
    ):
        if k in d:
            setattr(p, k, d[k])
    return p


def _options_to_dict(o: EpubOptions) -> dict:
    cover = str(o.cover_image) if o.cover_image is not None else None
    return {
        "epub_version": o.epub_version,
        "direction": o.direction,
        "title_font": o.title_font,
        "body_font": o.body_font,
        "embed_fonts": o.embed_fonts,
        "template": o.template,
        "custom_css": o.custom_css,
        "paragraph": _para_to_dict(o.paragraph),
        "cover_image": cover,
        "auto_cover": o.auto_cover,
        "compress_images": o.compress_images,
        "max_image_width": o.max_image_width,
        "image_format": o.image_format,
    }


def _options_from_dict(d: dict) -> EpubOptions:
    o = EpubOptions()
    for k in (
        "epub_version", "direction", "title_font", "body_font", "embed_fonts",
        "template", "custom_css", "auto_cover", "compress_images",
        "max_image_width", "image_format",
    ):
        if k in d:
            setattr(o, k, d[k])
    para = d.get("paragraph")
    if isinstance(para, dict):
        o.paragraph = _para_from_dict(para)
    cover = d.get("cover_image")
    o.cover_image = Path(cover) if cover else None
    return o


def _chapter_from_dict(d: dict) -> Chapter:
    return Chapter(title=d.get("title", ""), body=d.get("body", ""))


# ------------------------------------------------------------ واجهة ---

def save_project(book: Book, path: Path) -> None:
    """كتابة المشروع إلى مسار (JSON UTF-8)."""
    data = {
        "format_version": _FORMAT_VERSION,
        "metadata": _meta_to_dict(book.metadata),
        "options": _options_to_dict(book.options),
        "chapters": [{"title": c.title, "body": c.body} for c in book.chapters],
        "source_files": [str(p) for p in book.source_files],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_project(path: Path) -> Book:
    """قراءة مشروع من مسار. يرفع ValueError عند تلف الصيغة."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("صيغة مشروع غير سليمة")
    book = Book()
    meta = data.get("metadata")
    if isinstance(meta, dict):
        book.metadata = _meta_from_dict(meta)
    opts = data.get("options")
    if isinstance(opts, dict):
        book.options = _options_from_dict(opts)
    for ch in data.get("chapters", []):
        if isinstance(ch, dict):
            book.chapters.append(_chapter_from_dict(ch))
    for src in data.get("source_files", []):
        if src:
            book.source_files.append(Path(str(src)))
    return book
