"""حل مسارات الأصول — يعمل في التطوير وفي الحزمة (PyInstaller onefile).

في الوضع المجمّد تُوضع الأصول داخل `sys._MEIPASS` كما يُعلن مخطط البناء
(datas=[("app/assets", "app/assets")]).
"""
from __future__ import annotations

import sys
from pathlib import Path

_DEV_ASSETS = Path(__file__).resolve().parent / "assets"


def _frozen_base() -> Path | None:
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) if base else None


def asset_path(*parts: str) -> Path:
    """مسار داخل مجلد assets (مثل asset_path("logo.png"))."""
    frozen = _frozen_base()
    if frozen is not None:
        # المخطط يضمّن datas=[("app/assets","app/assets")] → جرّب app/assets أولًا
        candidate = frozen / "app" / "assets" / Path(*parts)
        if candidate.exists():
            return candidate
        return frozen / "assets" / Path(*parts)
    return _DEV_ASSETS.joinpath(*parts)