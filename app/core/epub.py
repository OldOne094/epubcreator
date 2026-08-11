"""مولّد EPUB3 (zipfile): بنية رسمية mimetype/container/opf/nav/css/xhtml/cover."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

from xml.sax.saxutils import escape as _xml_escape

from app.models import Book
from app.core.format import split_paragraphs
from app.core.templates import build_font_faces

_MIMETYPE = "application/epub+zip"
_OPF_NS = "http://www.idpf.org/2007/opf"
_CONTAINER = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>"""
_IMAGE_MEDIA = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def package_fonts_dir() -> Path | None:
    """مجلد الخطوط المضمّنة داخل الحزمة (app/assets/fonts) إن وُجد."""
    p = Path(__file__).resolve().parent.parent / "assets" / "fonts"
    return p if p.is_dir() else None


def available_font_files(fonts_dir: Path | None = None) -> list[Path]:
    """ملفات الخطوط (.ttf/.otf) المتاحة للتضمين."""
    d = fonts_dir if fonts_dir is not None else package_fonts_dir()
    if d is None or not d.is_dir():
        return []
    return sorted(p for p in d.iterdir() if p.suffix.lower() in {".ttf", ".otf"})


def _font_assets(fonts_dir: Path | None) -> tuple[str, list[tuple[str, str, Path]]]:
    """(قواعد @font-face، [(media_type, href, الملف المصدر)]) داخل OEBPS/."""
    files = available_font_files(fonts_dir)
    faces = build_font_faces([(f.stem, f.name) for f in files])
    items: list[tuple[str, str, Path]] = []
    for f in files:
        media = "font/otf" if f.suffix.lower() == ".otf" else "font/ttf"
        items.append((media, f"fonts/{f.name}", f))
    return faces, items


def _slug(index: int, title: str) -> str:
    """اسم فريد/آمن لملف الفصل."""
    base = "".join(ch for ch in title.strip() if ch.isalnum())[:24] or "chapter"
    return f"k{index}_{base}"


def _css(options) -> str:  # noqa: ANN001
    from app.core.templates import build_css
    return build_css(options)


def chapter_xhtml(chapter, index: int, options, css_href: str = "style.css", lang: str = "ar") -> str:
    """فصل → مستند XHTML مستقل (EPUB3)."""
    title = _xml_escape(chapter.title)
    paras = split_paragraphs(chapter.body)
    paras_html = "\n".join(f"<p>{_xml_escape(p)}</p>" for p in paras)
    body = (f"<h1>{title}</h1>" if chapter.title.strip() else "") + paras_html
    direction = options.direction
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<!DOCTYPE html>\n'
        f'<html xmlns="http://www.w3.org/1999/xhtml" '
        f'xmlns:epub="http://www.idpf.org/2007/ops" '
        f'xml:lang="{lang}" lang="{lang}" dir="{direction}">\n'
        f"<head><title>{title}</title>"
        f'<link rel="stylesheet" type="text/css" href="{css_href}"/></head>\n'
        f"<body>{body}</body>\n</html>\n"
    )


def nav_xhtml(chapters, title_root: str = "فهرس") -> str:
    """فهرس التنقل EPUB3 (nav)."""
    items = "\n".join(
        f'<li><a href="{_slug(i, c.title)}.xhtml">{_xml_escape(c.title or "(بلا عنوان)")}</a></li>'
        for i, c in enumerate(chapters)
    )
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<html xmlns="http://www.w3.org/1999/xhtml" '
        f'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ar" lang="ar" dir="rtl">\n'
        f"<head><title>{_xml_escape(title_root)}</title></head>\n"
        f"<body>\n<nav epub:type=\"toc\" id=\"toc\"><h1>{_xml_escape(title_root)}</h1>\n"
        f"<ol>\n{items}\n</ol></nav>\n</body>\n</html>\n"
    )


def toc_ncx(chapters, uid: str, title_root: str = "فهرس") -> str:
    """فهرس NCX (مطلوب في EPUB2)."""
    items = "\n".join(
        f'<navPoint id="n{i}" playOrder="{i + 1}">'
        f'<navLabel><text>{_xml_escape(c.title or "(بلا عنوان)")}</text></navLabel>'
        f'<content src="{_slug(i, c.title)}.xhtml"/>'
        f"</navPoint>"
        for i, c in enumerate(chapters)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{_xml_escape(uid)}"/>
    <meta name="dtb:depth" content="1"/>
  </head>
  <docTitle><text>{_xml_escape(title_root)}</text></docTitle>
  <navMap>
    {items}
  </navMap>
</ncx>
"""


def _split_keywords(raw: str) -> list[str]:
    """تقسيم الكلمات المفتاحية إلى عناصر dc:subject مستقلة."""
    return [kw.strip() for kw in re.split(r"[,،;؛]+", raw or "") if kw.strip()]


def _meta_fields(meta, epub_version: int) -> str:  # noqa: ANN001
    """كل حقول الواجهة تصل إلى OPF: ناشر/وصف/كلمات/مترجم/حقوق/سلسلة/جزء."""
    parts: list[str] = []
    if meta.publisher:
        parts.append(f"<dc:publisher>{_xml_escape(meta.publisher)}</dc:publisher>")
    if meta.description:
        parts.append(f"<dc:description>{_xml_escape(meta.description)}</dc:description>")
    for kw in _split_keywords(meta.keywords):
        parts.append(f"<dc:subject>{_xml_escape(kw)}</dc:subject>")
    if meta.translator:
        parts.append(f"<dc:contributor>{_xml_escape(meta.translator)}</dc:contributor>")
    if meta.rights:
        parts.append(f"<dc:rights>{_xml_escape(meta.rights)}</dc:rights>")
    if meta.series:
        if epub_version == 3:
            parts.append(
                f'<meta property="belongs-to-collection" id="series">{_xml_escape(meta.series)}</meta>'
            )
            if meta.part:
                parts.append(
                    f'<meta refines="#series" property="group-position">{_xml_escape(meta.part)}</meta>'
                )
        else:
            parts.append(f'<meta name="calibre:series" content="{_xml_escape(meta.series)}"/>')
            if meta.part:
                parts.append(
                    f'<meta name="calibre:series_index" content="{_xml_escape(meta.part)}"/>'
                )
    return "\n    ".join(parts)


def content_opf(book: Book, chapter_files: list[str], has_cover: bool, cover_href: str | None, epub_version: int = 3, font_files: list[tuple[str, str]] | None = None) -> str:
    """content.opf: metadata + manifest + spine + cover + خطوط مضمّنة."""
    meta = book.metadata
    lang = meta.language or "ar"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    identifier = meta.isbn or f"urn:uuid:{uuid.uuid4()}"
    version = "3.0" if epub_version == 3 else "2.0"

    manifest = [
        '<item id="css" href="style.css" media-type="text/css"/>',
    ]
    if epub_version == 3:
        manifest.append('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')
    else:
        manifest.append('<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')
    spine = []
    for i, href in enumerate(chapter_files):
        manifest.append(f'<item id="k{i}" href="{href}" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="k{i}"/>')

    if has_cover and cover_href:
        ext = cover_href.rsplit(".", 1)[-1]
        manifest.append(
            f'<item id="cover-image" href="{cover_href}" media-type="{_IMAGE_MEDIA.get(ext, "image/jpeg")}" properties="cover-image"/>'
        )

    for i, (media, href) in enumerate(font_files or []):
        manifest.append(f'<item id="font{i}" href="{href}" media-type="{media}"/>')

    creator = f"<dc:creator>{_xml_escape(meta.author)}</dc:creator>" if meta.author else ""
    extra_meta = _meta_fields(meta, epub_version)
    spine_attr = ' toc="ncx"' if epub_version == 2 else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="{_OPF_NS}" version="{version}" unique-identifier="uid" xml:lang="{lang}">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="uid">{_xml_escape(identifier)}</dc:identifier>
    <dc:title>{_xml_escape(meta.title)}</dc:title>
    <dc:language>{_xml_escape(lang)}</dc:language>
    {creator}
    {extra_meta}
    <meta property="dcterms:modified">{_xml_escape(now)}</meta>
  </metadata>
  <manifest>
    {chr(10).join(manifest)}
  </manifest>
  <spine{spine_attr}>
    {chr(10).join(spine)}
  </spine>
</package>
"""


class EpubWriter:
    """يبني كتاب EPUB3 من نموذج Book إلى ملف zip."""

    def __init__(self, book: Book, output_dir: Path, on_progress=None, fonts_dir: Path | None = None) -> None:  # noqa: ANN001
        self.book = book
        self.output = output_dir
        self._on_progress = on_progress
        self._fonts_dir = fonts_dir

    def _progress(self, value: int, message: str) -> None:
        """إبلاغ التقدم (قيمة 0..100 + رسالة) عبر الاستدعاء الاختياري."""
        if self._on_progress is None:
            return
        try:
            self._on_progress(value, message)
        except Exception:  # noqa: BLE001 — التقدم لا يوقف الكتابة أبدًا
            pass

    def write(self, destination: Path) -> Path:
        meta = self.book.metadata
        opts = self.book.options
        chapters = self.book.chapters

        self._progress(5, "تحضير الملفات…")
        chapter_files = [_slug(i, c.title) + ".xhtml" for i, c in enumerate(chapters)]

        cover_href = None
        has_cover = bool(chapters) and (
            opts.cover_image is not None or (opts.auto_cover and meta.title.strip())
        )
        if has_cover:
            cover_ext = (opts.image_format or "jpeg").lower()
            if cover_ext not in ("jpeg", "jpg", "png", "webp"):
                cover_ext = "jpeg"
            cover_href = f"cover.{cover_ext}"

        css = _css(opts)
        font_faces, font_items = "", []
        if opts.embed_fonts:
            font_faces, font_items = _font_assets(self._fonts_dir)
        if font_faces:
            css = font_faces + "\n" + css
        nav = nav_xhtml(chapters, meta.title or "فهرس")
        v2 = opts.epub_version == 2
        opf = content_opf(
            self.book, chapter_files, has_cover, cover_href,
            epub_version=opts.epub_version,
            font_files=[(media, href) for media, href, _ in font_items],
        )

        self._progress(25, "كتابة الهيكل (OPF/NAV/CSS)…")
        with ZipFile(destination, "w") as zf:
            # mimetype أولًا، بدون ضغط (شرط رسمي EPUB)
            zf.writestr("mimetype", _MIMETYPE, compress_type=ZIP_STORED)
            zf.writestr("META-INF/container.xml", _CONTAINER)
            zf.writestr("OEBPS/content.opf", opf)
            if v2:
                zf.writestr("OEBPS/toc.ncx", toc_ncx(chapters, meta.isbn or "", meta.title or "فهرس"))
            else:
                zf.writestr("OEBPS/nav.xhtml", nav)
            zf.writestr("OEBPS/style.css", css)
            total = len(chapters) or 1
            for i, ch in enumerate(chapters):
                self._progress(30 + int(55 * i / total), f"كتابة الفصل {i + 1}…")
                zf.writestr(f"OEBPS/{chapter_files[i]}", chapter_xhtml(ch, i, opts, "style.css", meta.language))
            for _, href, src in font_items:
                zf.writestr(f"OEBPS/{href}", src.read_bytes())
            if has_cover:
                self._progress(90, "توليد الغلاف…")
                zf.writestr(f"OEBPS/{cover_href}", self._cover_bytes(opts))
        self._progress(100, "اكتمل التصدير")
        return destination

    def _cover_bytes(self, opts) -> bytes:  # noqa: ANN001
        from app.core.covergen import cover_bytes

        return cover_bytes(self.book, opts)