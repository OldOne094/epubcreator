# -*- mode: python ; coding: utf-8 -*-
"""مخطط PyInstaller لـ EPubCreator (يبقي الحجم ≤50MB).

يستثني وحدات Qt الثقيلة غير المستخدمة (QtWebEngine ~100MB) للحفاظ على الحجم.
الاستخدام (من جذر المشروع):
    .venv\Scripts\pyinstaller epubcreator.spec
"""
import os

from PyInstaller.utils.hooks import collect_submodules

# استثناء وحدات Qt الكبيرة/غير المستخدمة (محرّك Chromium أخطر مساهم في الحجم)
HEAVY_QT = [
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebChannel",
    "PySide6.QtQuick",
    "PySide6.QtQml",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtNetwork",
    "PySide6.QtDesigner",
]

hidden = collect_submodules("app") + [
    "platformdirs",   # يُستورد كسلاً في app.settings ففات التحليل
    "docx",
    "lxml",
    "markdown_it",
    "striprtf",
    "PIL",
    "arabic_reshaper",   # تشكيل العربية في الغلاف (تُستورد كسلاً داخل الدوال)
    "bidi",              # ترتيب بصري RTL للغلاف
] if os.path.exists("app") else []

a = Analysis(
    ["app/main.py"],
    pathex=[],
    binaries=[],
    datas=[("app/assets", "app/assets")],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=HEAVY_QT,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="EPubCreator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                 # يبقى الحجم مستقرًا دون اعتماد UPX
    console=False,            # تطبيق GUI بلا نافذة طرفية
    disable_windowed_traceback=False,
)