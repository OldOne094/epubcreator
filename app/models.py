"""نماذج البيانات الأساسية (Metadata, Chapter, EpubOptions, Book)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Metadata:
    """البيانات الوصفية لكتاب EPUB (Dublin Core)."""
    title: str = ""
    author: str = ""
    translator: str = ""
    publisher: str = ""
    description: str = ""
    keywords: str = ""
    language: str = "ar"          # رمز اللغة؛ الافتراضي العربية
    isbn: str = ""
    series: str = ""
    part: str = ""
    rights: str = ""
    cover: Path | None = None     # صورة الغلاف (إن وجدت)

    def is_valid(self) -> bool:
        """الحد الأدنى الإلزامي: عنوان + لغة."""
        return bool(self.title.strip()) and bool(self.language.strip())


def normalize_isbn(raw: str) -> str:
    """ISBN مجرّد من الشرطات/المسافات (أرقام + X أخيرة محتملة)."""
    return re.sub(r"[\s\-‐‑‒–—―]+", "", (raw or "").strip().upper())


def is_valid_isbn(raw: str) -> bool:
    """تحقق خفيف من ISBN-10/ISBN-13 (فارغ = صالح/اختياري)."""
    s = normalize_isbn(raw)
    if not s:
        return True
    if len(s) == 10:
        if not re.fullmatch(r"\d{9}[\dX]", s):
            return False
        total = sum((10 - i) * (10 if ch == "X" else int(ch)) for i, ch in enumerate(s))
        return total % 11 == 0
    if len(s) == 13:
        if not re.fullmatch(r"\d{13}", s):
            return False
        total = sum(int(ch) * (1 if i % 2 == 0 else 3) for i, ch in enumerate(s))
        return total % 10 == 0
    return False


_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def has_invalid_filename_chars(name: str) -> bool:
    """هل يحتوي اسم الملف على محارف محظورة؟"""
    return bool(_INVALID_FILENAME_CHARS.search(name or ""))


def sanitize_filename(name: str, fallback: str = "book") -> str:
    """تعقيم اسم ملف: إزالة المحارف المحظورة في Windows (تُستبدل بشرطة سفلية)."""
    clean = _INVALID_FILENAME_CHARS.sub("_", (name or "").strip()).strip(" .")
    return clean or fallback


@dataclass
class Chapter:
    """فصل واحد من الكتاب؛ يُحفظ نصه خامًا ثم يتحول إلى XHTML عند البناء."""
    title: str = ""
    body: str = ""                # نص خام (يُحافظ عليه حرفيًا UTF-8)

    @property
    def has_body(self) -> bool:
        return bool(self.body.strip())


@dataclass
class ParagraphFormat:
    """تنسيق الفقرة."""
    alignment: str = "justify"    # left|right|center|justify|start|end
    line_height: str = "1.8"
    spacing_after: str = "1em"
    first_line_indent: str = "1.5em"
    font_size: str = "1em"
    margin_top: str = "0"
    margin_bottom: str = "0"
    color: str = ""               # فارغ = لون النسق


@dataclass
class EpubOptions:
    """خيارات البناء/التصدير."""
    epub_version: int = 3         # 2 أو 3
    direction: str = "rtl"
    title_font: str = "Amiri"     # خط العناوين
    body_font: str = "Amiri"      # خط النص
    embed_fonts: bool = True
    template: str = "novel-ar"    # قالب جاهز
    theme: str = ""               # اسم الثيم (فارغ = قالب)
    custom_css: str = ""          # CSS مخصص للمستخدم
    paragraph: ParagraphFormat = field(default_factory=ParagraphFormat)
    cover_image: Path | None = None
    auto_cover: bool = True       # توليد غلاف تلقائي عند غياب الصورة
    compress_images: bool = True
    max_image_width: int = 1200
    image_format: str = "jpeg"    # png|jpeg|webp


@dataclass
class Book:
    """الكتاب النشط داخل الجلسة."""
    metadata: Metadata = field(default_factory=Metadata)
    options: EpubOptions = field(default_factory=EpubOptions)
    chapters: list[Chapter] = field(default_factory=list)
    source_files: list[Path] = field(default_factory=list)

    def add_chapter(self, chapter: Chapter) -> None:
        self.chapters.append(chapter)
