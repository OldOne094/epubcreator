"""مستوردات الملفات: TXT/DOCX/RTF/HTML/Markdown → Book.

M1: TXT + HTML + Markdown تعمل. DOCX/RTF في M2.
"""
from __future__ import annotations

from pathlib import Path
from collections.abc import Iterable

from lxml import html as _lxml_html
from lxml.etree import ParserError as _ParserError

from app.models import Book, Chapter
from app.core.clean import clean_arabic, detect_chapters, is_chapter_heading

SUPPORTED_EXTENSIONS = {
    ".txt": "txt",
    ".md": "markdown",
    ".markdown": "markdown",
    ".html": "html",
    ".htm": "html",
    ".docx": "docx",
    ".rtf": "rtf",
}


def detect_type(path: Path) -> str | None:
    """نوع الملف من الامتداد."""
    return SUPPORTED_EXTENSIONS.get(path.suffix.lower())


def import_batch(paths: Iterable[Path]) -> list[Book]:
    """دفعة: كل ملف يُستورد ككتاب مستقل (السلوك الافتراضي)."""
    return [import_file(p) for p in paths]


def import_file(path: Path, merge_into_one: bool = False) -> Book:
    """استيراد ملف واحد إلى Book. يلتزم بالسلوك الافتراضي: كل ملف كتاب مستقل."""
    kind = detect_type(path)
    if kind is None:
        raise ValueError(f"unsupported file type: {path.suffix}")

    source = _read_text_auto(path)
    if kind == "txt":
        book = _book_from_plain(path, source)
    elif kind in ("html", "markdown"):
        html_text = source
        if kind == "markdown":
            from markdown_it import MarkdownIt
            html_text = MarkdownIt("commonmark").render(source)
        book = _from_html(path, html_text)
    elif kind == "docx":
        book = docx_to_book(path)
    elif kind == "rtf":
        book = rtf_to_book(path)
    else:
        raise NotImplementedError(f"import for {kind!r} is scheduled (M4)")

    book.source_files.append(path)
    return book


def _book_from_plain(path: Path, text: str) -> Book:
    book = Book()
    book.metadata.title = path.stem
    for block in detect_chapters(clean_arabic(text)):
        title, body = _split_title_body(block)
        book.add_chapter(Chapter(title=title, body=body))
    return book


def _split_title_body(block: str) -> tuple[str, str]:
    """فصل العنوان عن الجسم دون إتلاف أول فقرة.

    - أول سطر يُعدّ عنوانًا فقط إن بدا عنوان فصل (الفصل/الباب/Chapter…).
    - وإلا فكل الكتلة جسم (بلا لقب)، فلا تبتلع أول فقرة.
    """
    first, _, rest = block.partition("\n")
    if is_chapter_heading(first):
        return first.strip(), rest.strip()
    return "", block.strip()


# ------------------------------------------------------------- HTML / Markdown

# هو المستورد النّظيف للمحتوى النصّي
_HTML_CHAPTER_HEADINGS = frozenset({"h1", "h2"})
_HTML_BODY_BLOCKS = frozenset(
    {"h3", "h4", "h5", "h6", "p", "li", "blockquote", "pre", "div", "td", "th"}
)
_HTML_DROP_TAGS = frozenset(
    {"script", "style", "noscript", "head", "iframe", "object", "embed", "template", "title"}
)
_HTML_EVENT_ATTRS = (
    "onclick", "ondblclick", "onload", "onerror", "onchange", "onsubmit",
    "onkeydown", "onkeyup", "onkeypress", "onfocus", "onblur", "onmouseover",
    "onmouseout", "onmouseenter", "onunload",
)


def html_to_chapters(html_text: str) -> tuple[list[Chapter], str, str]:
    """تحويل HTML إلى فصول + اتجاه + لغة.

    - عناوين h1/h2 = بداية فصل جديد.
    - تُحذف العناصر (script/style/...)، وتُمسح سمات الأحداث/روابط javascript:.
    - تُرجع (chapters, direction, language) لمعايرة الاتجاه.
    """
    try:
        tree = _lxml_html.fromstring(html_text)
    except (ValueError, _ParserError):
        return [], "rtl", "ar"
    if tree is None:
        return [], "rtl", "ar"
    if tree.tag.lower() == "html":
        root = tree
    else:  # fragment
        root = tree
    _sanitize_html(root)

    lang = root.get("lang") or "ar"
    direction = root.get("dir") or ("rtl" if lang.lower().startswith("ar") else "ltr")

    chapters: list[Chapter] = []
    current: Chapter | None = None
    body_chunks: list[str] = []

    def flush() -> None:
        nonlocal body_chunks
        if current is not None:
            # كل عنصر HTML (p/li/...) فقرة مستقلة مفصولة بسطر فارغ
            current.body = "\n\n".join(body_chunks).strip("\n")
        if current is not None and (current.title or current.body):
            chapters.append(current)

    for node in root.iter():
        tag = node.tag if isinstance(node.tag, str) else None
        if tag in ("html", "body"):
            continue
        if tag in _HTML_CHAPTER_HEADINGS:
            flush()
            body_chunks = []
            current = Chapter(title=_text(node).strip())
            continue
        if tag in _HTML_BODY_BLOCKS:
            txt = _text(node)
            if txt:
                body_chunks.append(txt)
    flush()

    if not chapters:
        chapters = [Chapter(title="", body="\n\n".join(body_chunks).strip("\n"))]
    return chapters, direction, lang


def _text(node) -> str:  # noqa: ANN001
    return " ".join(node.itertext()).strip()


def _sanitize_html(root) -> None:  # noqa: ANN001
    for el in root.xpath(".//*"):
        tag = el.tag if isinstance(el.tag, str) else ""
        if tag in _HTML_DROP_TAGS:
            el.getparent().remove(el)
            continue
        for attr in list(el.attrib):
            if attr.lower().startswith("on") or attr.lower() in _HTML_EVENT_ATTRS:
                del el.attrib[attr]
        if el.get("href", "").lower().startswith("javascript:"):
            el.set("href", "#")


def _from_html(path: Path, html_text: str) -> Book:
    chapters, direction, lang = html_to_chapters(html_text)
    book = Book()
    book.metadata.title = path.stem
    book.options.direction = direction
    book.metadata.language = lang
    book.chapters = list(chapters)
    return book


def _read_text_auto(path: Path) -> str:
    """قراءة نص مع BOM والأخطاء الصغيرة (UTF-8 افتراضي)."""
    data = path.read_bytes()
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16", errors="replace")
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig", errors="replace")
    try:
        return data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return data.decode("cp1256", errors="replace")  # Windows Arabic


# ------------------------------------------------------------- DOCX (M2)

_DOCX_CHAPTER_LEVEL = 2  # Heading 1..2 → فصل؛ الأها≥3 فقرة داخلية


def _docx_heading_level(style_name: str | None) -> int | None:
    """مستوى العنوان (1..9) أو None إن لم يكن عنوانًا. يتعامل مع إنجليزي وعربي."""
    if not style_name:
        return None
    name = style_name.strip().lower()
    for level in range(1, 10):
        if name in (f"heading {level}", f"عنوان {level}"):
            return level
    return None


def docx_to_chapters(path: Path) -> list[Chapter]:
    """استخراج الفصول من DOCX. الجداول/الصور تُتجاهل (M2.1)."""
    from docx import Document

    doc = Document(path)
    chapters: list[Chapter] = []
    current: Chapter | None = None
    body: list[str] = []

    def flush() -> None:
        nonlocal body
        if current is not None:
            # كل فقرة DOCX تُحفظ مفصولة بسطر فارغ لتحافظ على البنية
            current.body = "\n\n".join(body).strip("\n")
            if current.title or current.body:
                chapters.append(current)

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        level = _docx_heading_level(para.style.name if para.style else None)
        if level is not None and level <= _DOCX_CHAPTER_LEVEL:
            flush()
            body = []
            current = Chapter(title=text)
        else:
            body.append(text)
    flush()

    if not chapters:
        chapters = [Chapter(title="", body="\n\n".join(body).strip("\n"))]
    return chapters


def docx_to_book(path: Path) -> Book:
    book = Book()
    book.metadata.title = path.stem
    book.options.direction = "rtl"
    book.metadata.language = "ar"
    book.chapters = list(docx_to_chapters(path))
    return book


# ------------------------------------------------------------- RTF (M2.2)


def rtf_to_text(path: Path) -> str:
    """تحويل RTF إلى نص خام."""
    from striprtf.striprtf import rtf_to_text as _rtf

    return _rtf(_read_text_auto(path)) or ""


def rtf_to_book(path: Path) -> Book:
    book = Book()
    book.metadata.title = path.stem
    book.options.direction = "rtl"
    book.metadata.language = "ar"
    text = clean_arabic(rtf_to_text(path))
    blocks = detect_chapters(text)
    if not blocks:
        blocks = [text]
    for block in blocks:
        title, body = _split_title_body(block)
        book.add_chapter(Chapter(title=title, body=body))
    return book