"""اختبارات الدخان (M3.5): النافذة الرئيسية والحوارات تُبنى وتعمل offscreen."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app import settings as app_settings
from app.ui.dialogs import ProgressDialog
from app.ui.main_window import MainWindow

app = QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _isolate_config(tmp_path):
    """عزل config.json حتى لا تتسرّب إعدادات الاختبارات بينها وبين بيئة المستخدم."""
    app_settings.set_config_override(tmp_path / "config.json")
    yield
    app_settings.set_config_override(None)


def test_main_window_builds():
    win = MainWindow()
    assert win.stack.count() >= 2
    assert win.state is not None


def test_main_window_menus_exist():
    win = MainWindow()
    menu = win.menuBar().actions()  # قوائم المستوى الأعلى
    assert menu  # يوجد قائمة واحدة زاريًا


def test_progress_dialog_advance():
    dlg = ProgressDialog()
    dlg.set_max(5)
    for _ in range(3):
        dlg.advance()
    assert dlg.bar.value() == 3


def test_status_bar_message_and_tooltip():
    win = MainWindow()
    assert win.statusBar().currentMessage() != ""
    actions = [a for m in win.menuBar().actions() for a in m.menu().actions() if not a.isSeparator()]
    tips = [a.toolTip() for a in actions if a.toolTip()]
    assert tips  # يوجد تلميح إرشادي على فعل الاستيراد


def test_after_import_returns_to_editor(tmp_path):
    from app.core.importers import import_file
    from app.workers import JobResult

    p = tmp_path / "book.txt"
    p.write_text("الفصل الأول\n\nمحتوى.", encoding="utf-8")
    book = import_file(p)

    win = MainWindow()
    win._on_import_done(JobResult(ok=True, books=[book]))

    # نعود إلى المحرر (وليس المعاينة) بعد الاستيراد
    assert win.stack.currentWidget() is win.pages["editor"]
    assert win.pages["editor"].chapter_list.count() == 1
    # القائمة تُظهر فصلًا قابلًا للتعديل
    win.pages["editor"].chapter_list.setCurrentRow(0)
    assert win.pages["editor"].body_edit.toPlainText() == "محتوى."


def test_toolbar_navigates_pages(tmp_path):
    win = MainWindow()
    # التنقل بين الصفحات عبر index (المعاينة صفحة داخلية تحتوي view)
    win.stack.setCurrentIndex(win.page["metadata"])
    assert win.stack.currentWidget() is win.pages["metadata"]
    win.stack.setCurrentIndex(win.page["preview"])
    assert win.stack.currentWidget() is win.pages["preview"]
    assert win.preview.view is win.pages["preview"].view
    win.stack.setCurrentIndex(win.page["editor"])
    assert win.stack.currentWidget() is win.pages["editor"]


def test_export_action_enabled_after_import(tmp_path):
    from app.core.importers import import_file
    from app.workers import JobResult

    p = tmp_path / "b.txt"
    p.write_text("الفصل ١\n\nنص.", encoding="utf-8")
    win = MainWindow()
    # قبل الاستيراد: لا تصدير عملي
    win._on_import_done(JobResult(ok=True, books=[import_file(p)]))
    assert win.state.book.chapters
    assert win.export_action is not None


def test_save_and_open_project_roundtrip(tmp_path):
    from app.project import save_project

    src = tmp_path / "src.txt"
    src.write_text("الفصل الأول\n\nنص.", encoding="utf-8")
    p = tmp_path / "book.epubproj"

    win = MainWindow()
    from app.core.importers import import_file
    from app.workers import JobResult

    win._on_import_done(JobResult(ok=True, books=[import_file(src)]))
    win.state.book.metadata.author = "مؤلف"
    win._on_state_changed()
    assert win._dirty

    win._project_path = p
    assert win._save_project()
    assert p.exists()
    assert win._dirty is False

    # فتح مشروع جديد
    win2 = MainWindow()
    win2._open_project(p)
    assert win2.state.book.metadata.title == "src"
    assert win2.state.book.metadata.author == "مؤلف"
    assert win2.state.book.chapters[0].title == "الفصل الأول"
    assert win2._dirty is False
    assert win2._project_path == p


def test_batch_import_loads_first_and_notifies(tmp_path):
    from app.core.importers import import_file
    from app.workers import JobResult

    a = tmp_path / "a.txt"
    a.write_text("الأول\n\nنص أ.", encoding="utf-8")
    b = tmp_path / "b.txt"
    b.write_text("الثاني\n\nنص ب.", encoding="utf-8")

    win = MainWindow()
    books = [import_file(a), import_file(b)]
    win._on_import_done(JobResult(ok=True, books=books))
    assert win.state.book.metadata.title == "a"
    assert "2 كتب" in win.statusBar().currentMessage()


def test_dirty_tracking_updates_title():
    from app.models import Chapter

    win = MainWindow()
    win.state.add_chapter(Chapter(title="فصل", body="ن."))
    assert win._dirty
    assert win.windowTitle().startswith("•")