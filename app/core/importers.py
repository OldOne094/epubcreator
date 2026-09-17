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

    if kind == "txt":
        book = _book_from_plain(path, _read_text_auto(path))
    elif kind in ("html", "markdown"):
        source = _read_text_auto(path)
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

    if path not in book.source_files:
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
        fragments = _lxml_html.fragments_fromstring(html_text)
    except (ValueError, _ParserError):
        return [], "rtl", "ar"
    # fragments_fromstring قد يرجع سلسلة/عنصر واحد — وحّدها لقائمة
    if isinstance(fragments, (str, bytes)):
        fragments = [fragments]
    else:
        fragments = list(fragments)
    if not fragments:
        return [], "rtl", "ar"
    wrapper = _lxml_html.Element("div")
    for frag in fragments:
        if isinstance(frag, str):
            # نص حر بين العناصر — احفظه كفقرة
            if frag.strip():
                p = _lxml_html.Element("p")
                p.text = frag
                wrapper.append(p)
        else:
            wrapper.append(frag)
    root = wrapper
    _sanitize_html(root)

    lang = "ar"
    direction = "rtl"
    # ابحث عن عنصر html الأصلي لالتقاط lang/dir إن وُجد
    try:
        tree = _lxml_html.fromstring(html_text)
        html_el = tree if getattr(tree, "tag", "").lower() == "html" else tree.find(".//html")
        if html_el is not None:
            lang = html_el.get("lang") or lang
    except (ValueError, _ParserError):
        pass
    direction = root.get("dir") or ("rtl" if lang.lower().startswith("ar") else "ltr")

    chapters: list[Chapter] = []
    current: Chapter | None = None
    body_chunks: list[str] = []

    def flush() -> None:
        nonlocal body_chunks, current
        if current is not None:
            # كل عنصر HTML (p/li/...) فقرة مستقلة مفصولة بسطر فارغ
            current.body = "\n\n".join(body_chunks).strip("\n")
        if current is not None and (current.title or current.body):
            chapters.append(current)
        elif current is None and body_chunks:
            # مقدمة قبل أول عنوان — احفظها كفصل بدل مسحها
            chapters.append(Chapter(title="مقدمة", body="\n\n".join(body_chunks).strip("\n")))
        body_chunks = []
        current = None

    for node in root.iter():
        tag = node.tag if isinstance(node.tag, str) else None
        if tag in ("html", "body", "div") and node is root:
            continue
        if tag in _HTML_CHAPTER_HEADINGS:
            flush()
            current = Chapter(title=_text(node).strip())
            continue
        if tag in _HTML_BODY_BLOCKS:
            # تجنّب العد المزدوج: إن كان الأب كتلة نصية أُخذ نصها، تخطَّ الأبناء
            # نأخذ الحاوية الأبعد فقط — تخطَّ أي كتلة داخلها كتلة نصية فرعية
            if _has_block_child(node):
                continue
            txt = _text(node)
            if txt:
                if current is None:
                    current = Chapter(title="")
                body_chunks.append(txt)
    # إغلاق آخر فصل/مقدمة
    if current is not None:
        current.body = "\n\n".join(body_chunks).strip("\n")
        if current.title or current.body:
            chapters.append(current)
    elif body_chunks:
        chapters.append(Chapter(title="مقدمة", body="\n\n".join(body_chunks).strip("\n")))

    if not chapters:
        chapters = [Chapter(title="", body="")]
    return chapters, direction, lang


def _has_block_child(node) -> bool:  # noqa: ANN001
    """هل تحتوي الكتلة على كتلة نصية فرعية؟ (لمنع العد المزدوج)."""
    for child in node.iterchildren():
        tag = child.tag if isinstance(child.tag, str) else None
        if tag in _HTML_BODY_BLOCKS or tag in _HTML_CHAPTER_HEADINGS:
            return True
        if _has_block_child(child):
            return True
    return False


def _text(node) -> str:  # noqa: ANN001
    return " ".join(node.itertext()).strip()


def _sanitize_html(root) -> None:  # noqa: ANN001
    for el in root.xpath(".//*"):
        tag = el.tag if isinstance(el.tag, str) else ""
        if tag in _HTML_DROP_TAGS:
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)
            continue
        for attr in list(el.attrib):
            low = attr.lower()
            if low.startswith("on") or low in _HTML_EVENT_ATTRS or low in ("formaction", "action"):
                del el.attrib[attr]
                continue
            if low in ("src", "href", "xlink:href", "{http://www.w3.org/1999/xlink}href"):
                val = (el.get(attr) or "").strip().lower()
                if val.startswith(("javascript:", "data:text/html", "vbscript:")):
                    if low.startswith("src"):
                        del el.attrib[attr]
                    else:
                        el.set(attr, "#")
                continue
            if low == "style":
                val = (el.get(attr) or "").lower()
                if "javascript:" in val or "expression(" in val or "vbscript:" in val:
                    del el.attrib[attr]


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
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig", errors="replace")
    if data.startswith(b"\xff\xfe\x00\x00") or data.startswith(b"\x00\x00\xfe\xff"):
        return data.decode("utf-32", errors="replace")
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16", errors="replace")
    try:
        return data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        pass
    # UTF-16LE/BE بلا BOM (شائع في ملفات Windows) — تحقق إرشادي
    if len(data) >= 4 and sum(1 for b in data[:100:2] if b == 0) > 20:
        try:
            return data.decode("utf-16-le", errors="strict")
        except UnicodeDecodeError:
            pass
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
        elif body:
            # مقدمة قبل أول عنوان — احفظها بدل تجاهلها
            chapters.append(Chapter(title="مقدمة", body="\n\n".join(body).strip("\n")))
        body = []

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