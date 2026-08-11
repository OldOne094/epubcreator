"""حل مسارات الأصول — يعمل في التطوير وفي الحزمة (PyInstaller onefile).

في الوضع المجمّد تُوضع الأصول داخل `sys._MEIPASS` كما يُعلن مخطط البناء
(datas=[("app/assets", "app/assets")]).
"""
from __future__ import annotations

import sys
from pathlib import Path

_ASSETS_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "assets"


def asset_path(*parts: str) -> Path:
    """مسار داخل مجلد assets (مثل asset_path("logo.png"))."""
    return _ASSETS_DIR.joinpath(*parts)