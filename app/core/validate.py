"""تحقق EPUB (داخلي عبر lxml + zipfile)."""
from __future__ import annotations

import io
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

from lxml import etree

_MIMETYPE_EXPECTED = b"application/epub+zip"


class ValidationIssue:
    """ملاحظة (error | warning) ضمن تقرير التحقق."""

    __slots__ = ("severity", "message")

    def __init__(self, severity: str, message: str) -> None:
        self.severity = severity  # error | warning
        self.message = message

    def __repr__(self) -> str:  # pragma: no cover
        return f"[{self.severity}] {self.message}"


def _add(issues: list[ValidationIssue], severity: str, message: str) -> None:
    issues.append(ValidationIssue(severity, message))


def validate_epub(path: Path) -> list[ValidationIssue]:
    """فحوصات داخلية على ملف EPUB. قائمة فارغة = سليم."""
    issues: list[ValidationIssue] = []

    if not path.exists():
        _add(issues, "error", f"الملف غير موجود: {path}")
        return issues

    try:
        zf = ZipFile(path)
    except Exception as exc:  # noqa: BLE001
        _add(issues, "error", f"غير قادر على فتح zip: {exc}")
        return issues

    with zf:
        names = zf.namelist()

        # 1) mimetype: أول عنصر + غير مضغوط + محتوى صحيح
        if "mimetype" not in names:
            _add(issues, "error", "مفقود mimetype")
        else:
            if names[0] != "mimetype":
                _add(issues, "error", "mimetype يجب أن يكون أول عنصر في الأرشيف")
            if zf.getinfo("mimetype").compress_type != ZIP_STORED:
                _add(issues, "warning", "mimetype مضغوط (يُفضَّل بدون ضغط)")
            if zf.read("mimetype") != _MIMETYPE_EXPECTED:
                _add(issues, "error", "محتوى mimetype غير صحيح")

        # 2) container.xml
        if "META-INF/container.xml" not in names:
            _add(issues, "error", "مفقود META-INF/container.xml")
        else:
            try:
                root = etree.fromstring(zf.read("META-INF/container.xml"))
            except etree.XMLSyntaxError as exc:
                _add(issues, "error", f"container.xml غير سليم: {exc}")
            else:
                rf = root.find(".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile")
                full = rf.get("full-path") if rf is not None else None
                if full and full not in names:
                    _add(issues, "error", f"rootfile يشير إلى ملف غير موجود: {full}")

        # 3) content.opf
        opf_names = [n for n in names if n.endswith("content.opf") or n.endswith(".opf")]
        if not opf_names:
            _add(issues, "error", "مفقود content.opf")
        else:
            opf_name = opf_names[0]
            try:
                opf_root = etree.fromstring(zf.read(opf_name))
            except etree.XMLSyntaxError as exc:
                _add(issues, "error", f"content.opf غير سليم: {exc}")
            else:
                _check_opf(zf, opf_root, names, issues)

    return issues


def _check_opf(zf: ZipFile, root, names: list[str], issues: list[ValidationIssue]) -> None:  # noqa: ANN001
    ns = {"o": "http://www.idpf.org/2007/opf", "dc": "http://purl.org/dc/elements/1.1/"}

    # بيانات إلزامية
    if not root.findtext(".//dc:title", namespaces=ns):
        _add(issues, "error", "dc:title مفقود")
    if not root.findtext(".//dc:language", namespaces=ns):
        _add(issues, "error", "dc:language مفقود")
    if root.find(".//dc:identifier", namespaces=ns) is None:
        _add(issues, "error", "dc:identifier مفقود")

    # manifest hrefs موجودة فعلًا
    for item in root.xpath(".//o:item", namespaces=ns):
        href = item.get("href")
        media = item.get("media-type")
        if not href or not media:
            _add(issues, "error", "عنصر manifest ناقص href أو media-type")
            continue
        if f"OEBPS/{href}" not in names:
            _add(issues, "error", f"manifest يشير إلى مفقود: {href}")

    # spine: كل idref له item
    item_ids = {i.get("id") for i in root.xpath(".//o:item", namespaces=ns)}
    for ref in root.xpath(".//o:itemref", namespaces=ns):
        if ref.get("idref") not in item_ids:
            _add(issues, "error", f"spine يشير إلى idref غير موجود: {ref.get('idref')}")

    # cover-image موجودة
    covers = root.xpath(".//o:item[@properties='cover-image']", namespaces=ns)
    for c in covers:
        if c.get("href") and f"OEBPS/{c.get('href')}" not in names:
            _add(issues, "error", "ملف صورة الغلاف مفقود")

    # فصل (xhtml) قابل للتحليل
    for item in root.xpath(".//o:item[@media-type='application/xhtml+xml']", namespaces=ns):
        href = item.get("href")
        if not href or f"OEBPS/{href}" not in names:
            continue
        try:
            etree.fromstring(zf.read(f"OEBPS/{href}"))
        except etree.XMLSyntaxError as exc:
            _add(issues, "error", f"XHTML غير سليم ({href}): {exc}")