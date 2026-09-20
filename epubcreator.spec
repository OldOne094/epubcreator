# -*- mode: python ; coding: utf-8 -*-
"""مخطط PyInstaller لـ EPubCreator (هدف الحجم ≤50MB).

يستثني وحدات Qt الثقيلة غير المستخدمة (QtWebEngine ~100MB) للحفاظ على الحجم.
الاستخدام (من جذر المشروع):
    .venv\Scripts\pyinstaller epubcreator.spec
"""
import os

from PyInstaller.utils.hooks import collect_submodules

ROOT = os.path.abspath(SPECPATH)  # مجلد المشروع (يعمل من أي cwd)

# استثناء وحدات Qt الكبيرة/غير المستخدمة (محرّك Chromium أخطر مساهم في الحجم).
# ملاحظة: QtNetwork/QtSvg مُستثنيان لأن الكود لا يستوردهما (يُتحقق بـ grep) —
# أي استيراد مستقبلي لهما يتطلب إسقاطهما من هنا وإعادة اختبار الدخان.
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
    "PySide6.QtSvg",
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
]

a = Analysis(
    [os.path.join(ROOT, "app", "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[(os.path.join(ROOT, "app", "assets"), "app/assets")],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=HEAVY_QT,
)

# ترجمات Qt (‎.qm ~15MB خام) غير محمّلة أبدًا (لا QTranslator في الكود) —
# إسقاطها وزن ميت. تُعاد إن أُضيف مثبّت ترجمات مستقبلًا.
a.datas = [
    (dest, src, kind) for (dest, src, kind) in a.datas
    if not (dest.lower().endswith(".qm") and "translation" in dest.lower())
]

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
    upx=False,                 # معطّل عمدًا: بلاغات AV كاذبة شائعة مع UPX
    console=False,            # تطبيق GUI بلا نافذة طرفية
    disable_windowed_traceback=False,
    icon=os.path.join(ROOT, "app", "assets", "EPubCreator.ico"),
)