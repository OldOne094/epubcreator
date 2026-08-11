"""اختبارات الدخان للصفحات الجديدة: تنسيق/غلاف/تصدير/رئيسية/شريط جانبي (offscreen)."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.models import Book, Chapter, Metadata
from app.state import BookState
from app.ui.cover_page import CoverPage
from app.ui.export_page import ExportPage
from app.ui.home_page import HomePage
from app.ui.preview import PreviewPage
from app.ui.sidebar import Sidebar
from app.ui.style_page import StylePage

app = QApplication.instance() or QApplication([])


def _state() -> BookState:
    b = Book(metadata=Metadata(title="كتاب اختبار", author="مؤلف"))
    b.add_chapter(Chapter(title="الفصل الأول", body="محتوى."))
    return BookState(book=b)


def _dummy(*_args, **_kwargs):  # noqa: ANN002
    return None


def test_style_page_builds_and_links_templates():
    page = StylePage(_state())
    assert len(page._template_buttons) == 5
    assert page._template_buttons["novel-ar"].isChecked()


def test_style_page_changes_paragraph():
    state = _state()
    page = StylePage(state)
    page.line_height.setCurrentText("2.2")
    assert state.book.options.paragraph.line_height == "2.2"


def test_style_page_changes_template():
    state = _state()
    page = StylePage(state)
    page._template_buttons["poetry"].setChecked(True)
    page._select_template("poetry")
    assert state.book.options.template == "poetry"


def test_style_page_custom_css():
    state = _state()
    page = StylePage(state)
    page.custom_css.setPlainText("body { margin: 1em; }")
    assert state.book.options.custom_css == "body { margin: 1em; }"


def test_cover_page_builds_and_auto():
    state = _state()
    page = CoverPage(state)
    page.auto_radio.setChecked(True)
    assert state.book.options.cover_image is None
    assert page.cover_display is not None


def test_cover_page_format_option():
    state = _state()
    page = CoverPage(state)
    page.image_format.setCurrentText("png")
    assert state.book.options.image_format == "png"


def test_export_page_builds_and_version():
    state = _state()
    page = ExportPage(state, _dummy)
    assert page.version_combo.currentData() == 3
    assert page.export_button is not None


def test_export_page_empty_book_blocks(monkeypatch):
    called = []
    import app.ui.dialogs as dialogs_mod

    monkeypatch.setattr(dialogs_mod, "error_dialog", lambda parent, msg: called.append(msg))
    page = ExportPage(BookState(book=Book()), _dummy)
    page.trigger_export()
    assert called  # يظهر حوار خطأ ولا يتصدّر


def test_home_page_empty_state():
    page = HomePage(BookState(book=Book()), _dummy, _dummy)
    assert page.overview.isHidden()
    assert not page.empty.isHidden()


def test_home_page_summary_after_import():
    page = HomePage(_state(), _dummy, _dummy)
    assert not page.overview.isHidden()
    assert page.title_label.text() == "كتاب اختبار"


def test_preview_page_builds_and_renders():
    state = _state()
    page = PreviewPage(state)
    assert page.chapter_combo.count() == 2  # كتاب كاملًا + فصل واحد
    html = page.view.toHtml()
    assert "الفصل الأول" in html


def test_preview_page_refresh_keeps_combo():
    state = _state()
    page = PreviewPage(state)
    state.book.add_chapter(Chapter(title="ثانٍ", body="نص."))
    page.refresh()
    assert page.chapter_combo.count() == 3


def test_sidebar_navigates():
    nav = []
    side = Sidebar(lambda k: nav.append(k), _dummy, "light")
    side._buttons["editor"].click()
    assert nav == ["editor"]


def test_sidebar_theme_label():
    side = Sidebar(_dummy, _dummy, "light")
    assert "داكن" in side.theme_button.text()
    side.set_theme_label("dark")
    assert "فاتح" in side.theme_button.text()
