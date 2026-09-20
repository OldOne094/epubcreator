"""اختبارات الإتاحة: ربط التسميات، أسماء قارئ الشاشة، تركيز مرئي، تباين AA."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFormLayout, QLabel

from app.models import Book, Chapter, Metadata
from app.state import BookState
from app.ui.themes import DARK, LIGHT, tokens

app = QApplication.instance() or QApplication([])


def _form_labels_have_buddies(widget) -> list[str]:
    """كل QLabel في QFormLayout داخل الويدجت يجب أن يكون مربوطًا (buddy)."""
    missing: list[str] = []
    for form in widget.findChildren(QFormLayout):
        for row in range(form.rowCount()):
            label = form.itemAt(row, QFormLayout.ItemRole.LabelRole)
            field = form.itemAt(row, QFormLayout.ItemRole.FieldRole)
            if label is None or field is None:
                continue
            w = label.widget()
            if isinstance(w, QLabel) and w.buddy() is None:
                missing.append(w.text())
    return missing


def _state() -> BookState:
    st = BookState(book=Book(metadata=Metadata(title="كتاب")))
    st.book.add_chapter(Chapter(title="فصل", body="نص."))
    return st


def test_metadata_labels_have_buddies():
    from app.ui.pages import MetadataPage

    page = MetadataPage(_state())
    assert _form_labels_have_buddies(page) == []


def test_style_labels_have_buddies():
    from app.ui.style_page import StylePage

    page = StylePage(_state())
    assert _form_labels_have_buddies(page) == []


def test_cover_labels_have_buddies():
    from app.ui.cover_page import CoverPage

    page = CoverPage(_state())
    assert _form_labels_have_buddies(page) == []


def test_export_labels_have_buddies():
    from app.ui.export_page import ExportPage

    page = ExportPage(_state(), lambda dest: None)
    assert _form_labels_have_buddies(page) == []


def test_key_widgets_have_accessible_names():
    from app.ui.cover_page import CoverPage
    from app.ui.export_page import ExportPage
    from app.ui.pages import ChapterEditor
    from app.ui.preview import PreviewPage

    st = _state()
    editor = ChapterEditor(st)
    assert editor.chapter_list.accessibleName()
    assert editor.title_edit.accessibleName()
    assert editor.body_edit.accessibleName()

    preview = PreviewPage(st)
    assert preview.view.accessibleName()
    assert preview.chapter_combo.accessibleName()
    assert preview.direction_combo.accessibleName()

    cover = CoverPage(st)
    assert cover.cover_display.accessibleName()
    assert cover.max_width.accessibleName()

    export = ExportPage(st, lambda dest: None)
    assert export.destination.accessibleName()
    assert export.report_list.accessibleName()


def test_stylesheet_has_visible_focus_and_no_forced_font():
    for sheet in (LIGHT, DARK):
        assert ":focus" in sheet
        assert "Segoe UI" not in sheet
    assert "width: 6px" in LIGHT  # مقبض التقسيم قابل للإمساك


def _luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    rgb = [int(hex_color[i : i + 2], 16) / 255 for i in (0, 2, 4)]

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(fg: str, bg: str) -> float:
    l1, l2 = _luminance(fg), _luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def test_contrast_aa_for_key_combinations():
    for name in ("light", "dark"):
        t = tokens(name)
        primary_text = t.get("primary_text", "#ffffff")
        assert _contrast(primary_text, t["primary"]) >= 4.5, f"{name} primary"
        assert _contrast(t["accent_text"], t["accent_soft"]) >= 4.5, f"{name} badge"
        assert _contrast(t["muted"], t["surface"]) >= 4.5, f"{name} muted"
        assert _contrast(t["text"], t["surface"]) >= 7.0, f"{name} body"


def test_open_folder_uses_desktop_services(tmp_path):
    from PySide6.QtGui import QDesktopServices

    from app.ui.export_page import ExportPage

    opened: list = []
    real = QDesktopServices.openUrl
    QDesktopServices.openUrl = lambda url: opened.append(url) or True
    try:
        page = ExportPage(_state(), lambda dest: None)
        dest = tmp_path / "k.epub"
        dest.write_text("x")
        page._last_dest = dest
        page._open_folder()
    finally:
        QDesktopServices.openUrl = real
    assert opened
    from pathlib import Path

    assert Path(opened[0].toLocalFile()) == tmp_path
