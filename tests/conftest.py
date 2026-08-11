"""إعدادات الاختبار المشتركة: وضع الشاشة offscreen + ملف إعدادات مؤقت."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session", autouse=True)
def _isolated_config(tmp_path_factory):
    """توجيه config.json إلى مجلد مؤقت حتى لا تُلوَّث إعدادات المستخدم."""
    from app import settings as app_settings

    override = Path(tmp_path_factory.mktemp("config")) / "config.json"
    app_settings.set_config_override(override)
    yield override
    app_settings.set_config_override(None)
