"""اختبارات توحيد الإعدادات (DEFAULT_CONFIG + helpers + geometry)."""
from __future__ import annotations

import pytest

from app import settings as app_settings


@pytest.fixture(autouse=True)
def _reset_override():
    yield
    app_settings.set_config_override(None)


def test_default_config_has_tidy_keys():
    for key in ("theme", "recent_projects", "geometry", "last_template", "last_folder"):
        assert key in app_settings.DEFAULT_CONFIG


def test_get_config_falls_back_to_defaults(tmp_path):
    app_settings.set_config_override(tmp_path / "config.json")
    assert app_settings.get_config("theme", "light") == "light"
    assert app_settings.get_config("recent_projects", []) == []


def test_set_config_merges_and_persists(tmp_path):
    app_settings.set_config_override(tmp_path / "config.json")
    app_settings.set_config(theme="dark", last_font="Cairo")
    cfg = app_settings.load_config()
    assert cfg["theme"] == "dark"
    assert cfg["last_font"] == "Cairo"
    # التحديث اللاحق لا يُفقد القيم السابقة
    app_settings.set_config(last_template="docs")
    cfg = app_settings.load_config()
    assert cfg["theme"] == "dark"
    assert cfg["last_template"] == "docs"


def test_window_geometry_roundtrip(tmp_path):
    app_settings.set_config_override(tmp_path / "config.json")
    data = bytes(range(64))
    app_settings.save_window_geometry(data)
    assert app_settings.window_geometry_bytes() == data


def test_window_geometry_missing_returns_none(tmp_path):
    app_settings.set_config_override(tmp_path / "config.json")
    assert app_settings.window_geometry_bytes() is None


def test_window_geometry_corrupt_returns_none(tmp_path):
    app_settings.set_config_override(tmp_path / "config.json")
    app_settings.save_config({**app_settings.DEFAULT_CONFIG, "geometry": "@@@not-base64@@@"})
    assert app_settings.window_geometry_bytes() is None