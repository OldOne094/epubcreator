"""اختبارات الثيمات (M6.1) — offscreen."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app import settings as app_settings
from app.ui.main_window import MainWindow
from app.ui.themes import DARK, LIGHT, apply_theme, stylesheet

app = QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _isolate_config(tmp_path):
    """عزل config.json عن بيئة المستخدم حتى لا تتسرّب قيمة الثيم بين الاختبارات."""
    app_settings.set_config_override(tmp_path / "config.json")
    yield
    app_settings.set_config_override(None)


def test_stylesheets_exist_and_distinct():
    assert LIGHT != DARK
    assert "background:" in stylesheet("light")
    assert "background:" in stylesheet("dark")


def test_unknown_falls_back_to_light():
    assert stylesheet("nope") == LIGHT


def test_apply_theme_sets_stylesheet():
    apply_theme(app, "dark")
    assert "16171a" in app.styleSheet()
    apply_theme(app, "light")
    assert "f4f1ea" in app.styleSheet()


def test_main_window_has_toggle():
    win = MainWindow()
    assert win._theme == "light"
    win._toggle_theme()
    assert win._theme == "dark"
    assert "16171a" in app.styleSheet()