"""النافذة الرئيسية: شريط جانبي + رأس + صفحات + استيراد/تصدير بالخلفية + سحب وإفلات.

تربط كل الصفحات بـ `BookState` واحد وتحدّث المعاينة حيًّا.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app import settings as app_settings
from app.state import BookState
from app.ui.cover_page import CoverPage
from app.ui.dialogs import error_dialog
from app.ui.export_page import ExportPage
from app.ui.home_page import HomePage
from app.ui.pages import build_pages
from app.ui.preview import Preview, PreviewPage
from app.ui.sidebar import Sidebar
from app.ui.style_page import StylePage
from app.ui.themes import apply_theme
from app.workers import ExportJob, ImportJob

PAGE_EDITOR = "editor"
PAGE_METADATA = "metadata"
PAGE_PREVIEW = "preview"

_FILE_FILTER = "مدعومة (*.txt *.md *.markdown *.html *.htm *.docx *.rtf);;جميع الملفات (*.*)"
_PROJECT_FILTER = "مشروع EPubCreator (*.epubproj)"


class MainWindow(QMainWindow):
    """نافذة التطبيق: رئيسية/محرر/بيانات/تنسيق/غلاف/معاينة/تصدير."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("EPubCreator — مصنّع الكتب العربية")
        self.resize(1240, 820)
        self.setMinimumSize(980, 640)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setAcceptDrops(True)

        self.state = BookState()
        self._config = app_settings.load_config()
        self._theme = self._config.get("theme", "light")
        self._last_template = self._config.get("last_template", "novel-ar")
        self._project_path: Path | None = None
        self._dirty = False
        self._restore_geometry()

        self.preview = Preview()
        self._pool = QThreadPool()
        self._build_ui()
        self._build_menu()

        # الثيم يُطبَّق على مستوى التطبيق (لا النافذة) حتى لا يظلّل تبديله؛
        # فشريط النمط الخاص بالنافذة يتفوّق على النمط العام ويمنع ظهور التغيير
        qapp = QApplication.instance() or self
        apply_theme(qapp, self._theme)
        self.setStyleSheet("")  # إزالة أي نمط عالق من نافذة قديمة
        self.sidebar.set_theme_label(self._theme)

        self.statusBar().showMessage("جاهز: استورد ملفات للبدء، أو اسحبها وأفلتها داخل النافذة")
        self.state.set_on_change(self._on_state_changed)
        self.go("home")

    # ------------------------------------------------------------ بناء ---
    def _build_ui(self) -> None:
        self.sidebar = Sidebar(self.go, self._toggle_theme, self._theme)

        # ---- الصفحات ----
        core = build_pages(self.state)
        home = HomePage(self.state, self._on_open, self.go)
        style = StylePage(self.state)
        cover = CoverPage(self.state)
        export = ExportPage(self.state, self._run_export)
        preview_page = PreviewPage(self.state, view=self.preview.view)

        self.pages: dict[str, QWidget] = {
            "home": home,
            PAGE_EDITOR: core["editor"],
            PAGE_METADATA: core["metadata"],
            "style": style,
            "cover": cover,
            PAGE_PREVIEW: preview_page,
            "export": export,
        }

        self.stack = QStackedWidget()
        self.page: dict[str, int] = {}
        for key, widget in self.pages.items():
            self.stack.addWidget(widget)
            self.page[key] = self.stack.count() - 1

        # ---- الرأس ----
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 10, 18, 6)
        header_layout.setSpacing(10)

        self.book_title_label = QLabel("لا يوجد كتاب مفتوح")
        self.book_title_label.setObjectName("PageTitle")
        header_layout.addWidget(self.book_title_label, 1)

        self.import_button = QPushButton("استيراد ملفات…")
        self.import_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_button.clicked.connect(self._on_open)
        header_layout.addWidget(self.import_button)

        self.export_button = QPushButton("تصدير EPUB")
        self.export_button.setObjectName("Primary")
        self.export_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_button.clicked.connect(self._on_export)
        header_layout.addWidget(self.export_button)

        # ---- التجميع ----
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(header)
        content_layout.addWidget(self.stack, 1)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.sidebar)
        root.addWidget(content, 1)
        self.setCentralWidget(central)

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("ملف")
        self.open_action = QAction("استيراد ملفات…", self)
        self.open_action.setToolTip("استيراد TXT/Markdown/HTML/DOCX/RTF أو سحبها وإفلاتها")
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self._on_open)
        file_menu.addAction(self.open_action)

        self.export_action = QAction("تصدير EPUB…", self)
        self.export_action.setToolTip("تصدير الكتاب بصيغة EPUB3/EPUB2")
        self.export_action.setShortcut("Ctrl+E")
        self.export_action.triggered.connect(self._on_export)
        file_menu.addAction(self.export_action)
        file_menu.addSeparator()

        self.save_action = QAction("حفظ المشروع", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self._save_project)
        file_menu.addAction(self.save_action)

        self.save_as_action = QAction("حفظ المشروع باسم…", self)
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.triggered.connect(self._save_project_as)
        file_menu.addAction(self.save_as_action)

        self.open_project_action = QAction("فتح مشروع…", self)
        self.open_project_action.setShortcut("Ctrl+Shift+O")
        self.open_project_action.triggered.connect(self._open_project)
        file_menu.addAction(self.open_project_action)

        self.recent_menu = file_menu.addMenu("مشاريع حديثة")
        self._rebuild_recent_menu()
        file_menu.addSeparator()

        quit_action = QAction("خروج", self)
        quit_action.setShortcut("Alt+F4")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = self.menuBar().addMenu("عرض")
        self.theme_action = QAction("تبديل الثيم (فاتح/داكن)", self)
        self.theme_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(self.theme_action)

        help_menu = self.menuBar().addMenu("مساعدة")
        self.check_updates_action = QAction("تحقق من التحديثات…", self)
        self.check_updates_action.setToolTip("فحص الإصدار الأحدث من خادم التحديثات")
        self.check_updates_action.triggered.connect(self._check_updates)
        help_menu.addAction(self.check_updates_action)
        about_action = QAction("حول EPubCreator", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _show_about(self) -> None:
        from app import __version__
        from app.resources import asset_path
        from PySide6.QtGui import QPixmap

        dialog = QMessageBox(self)
        dialog.setWindowTitle("حول EPubCreator")
        logo = asset_path("logo.png")
        if logo.exists():
            pix = QPixmap(str(logo)).scaled(
                96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            dialog.setIconPixmap(pix)
        dialog.setText(
            f"مصنّع كتب EPUB لسطح المكتب\n"
            f"الإصدار {__version__}\n"
            "دعم عربي احترافي (RTL) · EPUB3/EPUB2 · 5 قوالب جاهزة\n"
            "Python + PySide6"
        )
        dialog.exec()

    def _check_updates(self) -> None:
        """فحص التحديثات في خلفية وعرض النتيجة عند اكتمالها."""
        from app.workers import UpdateCheckJob

        url = app_settings.effective_update_url(self._config)
        self.statusBar().showMessage("جارٍ فحص التحديثات…")
        job = UpdateCheckJob(url)
        job.signals.finished.connect(self._on_update_check_done)
        job.signals.error.connect(self._on_update_check_error)
        self._pool.start(job)

    def _on_update_check_error(self, msg: str) -> None:
        self.statusBar().showMessage("تعذّر فحص التحديثات.")
        error_dialog(self, f"تعذّر فحص التحديثات: {msg}")

    def _on_update_check_done(self, result) -> None:  # noqa: ANN001
        if not result.ok:
            self.statusBar().showMessage("توصّل محدود: تعذّر فحص التحديثات.")
            QMessageBox.information(
                self,
                "فحص التحديثات",
                "تعذّر التحقق من التحديثات الآن.\n"
                f"{result.error}\n\n"
                "تأكد من اتصال الإنترنت ومن ضبط رابط الفحص في config (update_url).",
            )
            return
        if not result.has_update:
            self.statusBar().showMessage(f"لا توجد تحديثات (الإصدار الحالي {result.current}).")
            QMessageBox.information(
                self,
                "فحص التحديثات",
                f"إصدارك الحالي {result.current} هو الأحدث.",
            )
            return
        message = (
            f"يتوفر إصدار أحدث: {result.latest} (الحالي: {result.current})."
            + (f"\n\n{result.note}" if result.note else "")
        )
        answer = QMessageBox.question(
            self,
            "تحديث متاح",
            message + "\n\nهل تريد فتح صفحة التنزيل؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer == QMessageBox.StandardButton.Yes and result.change_url:
            import webbrowser

            webbrowser.open(result.change_url)
        self.statusBar().showMessage(f"تحديث متاح: الإصدار {result.latest}.")

    # ---------------------------------------------------------- تنقل ---
    def go(self, key: str) -> None:
        """الانتقال إلى صفحة + تمييزها في الشريط الجانبي."""
        if key in self.page:
            self.stack.setCurrentIndex(self.page[key])
        if key == PAGE_PREVIEW:
            self.pages[PAGE_PREVIEW].refresh(keep_selection=True)
        elif key == "cover":
            self.pages["cover"].refresh_preview()
        self.sidebar.set_active(key)

    def _toggle_theme(self) -> None:
        self._theme = "dark" if self._theme == "light" else "light"
        qapp = QApplication.instance() or self
        apply_theme(qapp, self._theme)
        self.setStyleSheet("")  # لا نمط خاص بالنافذة يوقف انتشار الثيم
        self.sidebar.set_theme_label(self._theme)
        app_settings.set_config(theme=self._theme)

    def _restore_geometry(self) -> None:
        """استعادة حجم/موقع النافذة من config (لا تُكتب إن لم تكن محفوظة)."""
        data = app_settings.window_geometry_bytes()
        if data is not None:
            from PySide6.QtCore import QByteArray

            self.restoreGeometry(QByteArray(data))

    # ------------------------------------------------------ مشروع ---
    def _rebuild_recent_menu(self) -> None:
        """إعادة بناء قائمة المشاريع الحديثة من config."""
        self.recent_menu.clear()
        recent = [r for r in self._config.get("recent_projects", []) if r]
        if not recent:
            empty = QAction("لا مشاريع حديثة", self)
            empty.setEnabled(False)
            self.recent_menu.addAction(empty)
            return
        for path_str in recent:
            action = QAction(path_str, self)
            action.triggered.connect(
                lambda _=False, p=path_str: self._open_project(Path(p))
            )
            self.recent_menu.addAction(action)

    def _record_recent(self, path: Path) -> None:
        recent = [str(p) for p in self._config.get("recent_projects", []) if p]
        key = str(path)
        recent = [key] + [r for r in recent if r != key]
        self._config["recent_projects"] = recent[:8]
        app_settings.set_config(recent_projects=recent[:8])
        self._rebuild_recent_menu()

    def _update_window_title(self) -> None:
        title = self.state.book.metadata.title.strip()
        base = f"{title} — EPubCreator" if title else "EPubCreator — مصنّع الكتب العربية"
        if self._project_path is not None:
            base = f"{base} ({self._project_path.name})"
        if self._dirty:
            base = "• " + base
        self.setWindowTitle(base)

    def _save_project(self) -> bool:
        """حفظ المشروع الحالي. يُعيد True عند نجاح الحفظ."""
        if self._project_path is None:
            return self._save_project_as()
        try:
            from app.project import save_project

            save_project(self.state.book, self._project_path)
        except OSError as exc:
            error_dialog(self, f"تعذّر الحفظ: {exc}")
            return False
        self._dirty = False
        self._record_recent(self._project_path)
        self._update_window_title()
        self.statusBar().showMessage(f"حُفظ المشروع: {self._project_path.name}")
        return True

    def _save_project_as(self) -> bool:
        default = Path(self.state.book.metadata.title.strip() or "كتاب").with_suffix(
            ".epubproj"
        )
        if self._project_path is not None:
            default = self._project_path.with_suffix(".epubproj")
        start_dir = (
            str(default.parent)
            if self._project_path is not None
            else str(self._config.get("last_folder", ""))
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "حفظ المشروع", str(Path(start_dir) / default.name), _PROJECT_FILTER
        )
        if not path:
            return False
        if not path.lower().endswith(".epubproj"):
            path += ".epubproj"
        self._project_path = Path(path)
        return self._save_project()

    def _open_project(self, path: Path | None = None) -> None:
        if path is None:
            folder = (
                str(self._project_path.parent)
                if self._project_path is not None
                else str(self._config.get("last_folder", ""))
            )
            chosen, _ = QFileDialog.getOpenFileName(self, "فتح مشروع", folder, _PROJECT_FILTER)
            if not chosen:
                return
            path = Path(chosen)
        try:
            from app.project import load_project

            book = load_project(path)
        except (OSError, ValueError) as exc:
            error_dialog(self, f"تعذّر فتح المشروع: {exc}")
            return
        self._project_path = path
        self.state.set_book(book)
        self.pages[PAGE_EDITOR].reload()
        self.pages[PAGE_METADATA].reload()
        self._on_state_changed()
        self._dirty = False
        self._record_recent(path)
        self._update_window_title()
        self.statusBar().showMessage(f"فُتح المشروع: {path.name}")
        self.go(PAGE_EDITOR)

    # --------------------------------------------------------- أعمال ---
    def _on_open(self) -> None:
        folder = str(self._config.get("last_folder", ""))
        files, _ = QFileDialog.getOpenFileNames(self, "اختر ملفات", folder, _FILE_FILTER)
        if not files:
            return
        self._import_paths([Path(f) for f in files])

    def _import_paths(self, paths: list[Path]) -> None:
        self._set_busy(True, "جارٍ استيراد الملفات…")
        job = ImportJob(paths)
        job.signals.finished.connect(self._on_import_done)
        job.signals.error.connect(self._on_import_error)
        self._pool.start(job)

    def _on_import_error(self, msg: str) -> None:
        self._set_busy(False)
        error_dialog(self, f"تعذّر استيراد الملف: {msg}")

    def _on_import_done(self, result) -> None:  # noqa: ANN001
        self._set_busy(False)
        if not result.books:
            return
        self.state.set_book(result.books[0])
        self.pages[PAGE_EDITOR].reload()
        self.pages[PAGE_METADATA].reload()
        self._project_path = None
        self._dirty = False
        self._on_state_changed()
        self._update_window_title()
        if result.books[0].source_files:
            self._config["last_folder"] = str(result.books[0].source_files[0].parent)
            app_settings.set_config(last_folder=self._config["last_folder"])
        if len(result.books) > 1:
            self.statusBar().showMessage(
                f"تم استيراد {len(result.books)} كتب — يُعرض الأول «{result.books[0].metadata.title}»"
            )
        else:
            self.statusBar().showMessage(f"تم الاستيراد: {result.books[0].metadata.title}")
        self.go(PAGE_EDITOR)

    def _set_busy(self, busy: bool, message: str = "") -> None:
        self.import_button.setEnabled(not busy)
        self.export_button.setEnabled(not busy)
        self.export_action.setEnabled(not busy)
        if message:
            self.statusBar().showMessage(message)

    def _on_state_changed(self) -> None:
        self._dirty = True
        book = self.state.book
        title = book.metadata.title.strip()
        self.book_title_label.setText(title or ("لا يوجد كتاب مفتوح" if not book.chapters else "(بلا عنوان)"))
        self.pages["home"].refresh()
        self.pages["export"].refresh()
        preview_page = self.pages[PAGE_PREVIEW]
        # أعد رسم المعاينة فورًا إن كانت ظاهرة أو تغيّر عدد الفصول؛ وإلا عند فتحها
        if self.stack.currentWidget() is preview_page or len(book.chapters) != preview_page._last_count:
            preview_page.refresh()
        if self.stack.currentWidget() is self.pages["cover"]:
            self.pages["cover"].refresh_preview()
        if self._last_template != book.options.template:
            self._last_template = book.options.template
            app_settings.set_config(last_template=self._last_template)
        self._update_window_title()

    # -------------------------------------------------------- تصدير ---
    def _on_export(self) -> None:
        self.go("export")
        self.pages["export"].trigger_export()

    def _run_export(self, dest: Path) -> None:
        if not self.state.book.chapters:
            return
        self._set_busy(True, "جارٍ بناء كتاب EPUB…")
        # ExportJob يلتقط لقطة عميقة للكتاب فورًا (لا تتأثر بتحرير المستخدم)
        job = ExportJob(self.state.book, dest)
        job.signals.finished.connect(self._on_export_done)
        job.signals.error.connect(self._on_export_error)
        job.signals.progress.connect(self.pages["export"].show_progress)
        self._pool.start(job)

    def _on_export_done(self, path) -> None:  # noqa: ANN001
        self._set_busy(False)
        from app.core.validate import validate_epub

        issues = validate_epub(Path(path))
        self.pages["export"].show_result(Path(path), issues)
        if issues:
            self.statusBar().showMessage("صُدّر الكتاب — يوجد تحذيرات/أخطاء تحقق.")
        else:
            self.statusBar().showMessage(f"صُدّر بنجاح وسليم: {Path(path).name}")

    def _on_export_error(self, msg: str) -> None:
        self._set_busy(False)
        error_dialog(self, f"تعذّر التصدير: {msg}")

    # ---------------------------------------------------- سحب وإفلات ---
    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            self._import_paths([Path(p) for p in paths])
        event.acceptProposedAction()

    # ------------------------------------------------------ إغلاق ---
    def closeEvent(self, event) -> None:  # noqa: N802
        app_settings.save_window_geometry(bytes(self.saveGeometry()))
        if not self._dirty:
            event.accept()
            return
        answer = QMessageBox.question(
            self,
            "حفظ المشروع",
            "لديك تغييرات غير محفوظة. هل تريد الحفظ قبل الخروج؟",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            event.ignore()
            return
        if answer == QMessageBox.StandardButton.Save and not self._save_project():
            event.ignore()
            return
        event.accept()
