"""نماذج البيانات الأساسية (Metadata, Chapter, EpubOptions, Book)."""
from __future__ import annotations

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
