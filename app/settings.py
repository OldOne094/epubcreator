"""إدارة إعدادات التطبيق (config.json) وتجهيز السجل (Logging).

يخزّن آخر إعدادات: template/css/fonts/folder/theme/geometry/recent ... في platformdirs.
Logging عبر QueueHandler + QueueListener (غير حاجز) بصيغة JSON Lines.
"""
from __future__ import annotations

import base64
import copy
import json
import logging
import logging.handlers
import sys
from pathlib import Path
from queue import Queue

from platformdirs import PlatformDirs

APP_NAME = "EPubCreator"

_DIRS = PlatformDirs(APP_NAME, appauthor=False)

DEFAULT_CONFIG: dict[str, object] = {
    "language": "ar",
    "last_template": "novel-ar",
    "last_css": "",
    "last_folder": "",
    "last_font": "Amiri",
    "epub_version": 3,
    "theme": "light",
    "recent_projects": [],
    "geometry": "",
    "update_url": "",
}

_listener_ref: logging.handlers.QueueListener | None = None
_config_override: Path | None = None


# ----------------------------------------------------------------- config ---

def set_config_override(path: Path | None) -> None:
    """توجيه ملف الإعدادات إلى مسار بديل (تُستخدم في الاختبارات)."""
    global _config_override
    _config_override = path


def config_path() -> Path:
    if _config_override is not None:
        return _config_override
    return Path(_DIRS.user_config_dir) / "config.json"


def load_config() -> dict:
    """تحميل الإعدادات مع دمج الافتراضيات (قيمة جزئية أو ملف مفقود)."""
    base = copy.deepcopy(DEFAULT_CONFIG)
    path = config_path()
    if not path.exists():
        return base
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            base.update(data)
    except (OSError, ValueError):
        logging.getLogger(__name__).warning("Ignoring unreadable config at %s", path)
    return base


def save_config(config: dict) -> None:
    path = config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except OSError:  # pragma: no cover
        logging.getLogger(__name__).exception("Config save failed")


# ----------------------------------------------------- توحيد التخزين ---


def get_config(key: str, default: object = None) -> object:
    """قراءة مفتاح من الإعدادات (مع دمج الافتراضيات)."""
    return load_config().get(key, default)


def set_config(**values: object) -> None:
    """تحديث مفتاح مفتاحي، ثم الحفظ. يبقي ما يردّ في load_config افتراضيًّا."""
    cfg = load_config()
    cfg.update(values)
    save_config(cfg)


def save_window_geometry(data: bytes) -> None:
    """حفظ هندسة النافذة (بايتات QByteArray) بصيغة base64 في config.json."""
    set_config(geometry=base64.b64encode(data).decode("ascii"))


def window_geometry_bytes() -> bytes | None:
    """استعادة هندسة النافذة المحفوظة وإن لم توجد تُعيد None."""
    raw = get_config("geometry", "")
    if not raw:
        return None
    try:
        return base64.b64decode(raw)
    except (ValueError, TypeError):
        logging.getLogger(__name__).warning("Invalid geometry value in config")
        return None


# ---------------------------------------------------------------- logging ---


class JsonFormatter(logging.Formatter):
    """تنسيق السجلات سطرًا بصيغة JSON."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "context"):
            entry["context"] = record.context
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def configure_logging(level: int = logging.INFO) -> None:
    """تهيئة السجل غير الحاجز عبر طابور + مستمع في خيط 뒷면.

    يُستدعى مرة واحدة (يُتجنّب الإطباق عند إعادة الاستدعاء). الملفات الزاهية دائرة.
    """
    root = logging.getLogger()
    if hasattr(root, "_epubcreator_configured"):
        return
    root._epubcreator_configured = True

    formatter = JsonFormatter()

    logs = Path(_DIRS.user_log_dir)
    try:
        logs.mkdir(parents=True, exist_ok=True)
        sink = logging.handlers.RotatingFileHandler(
            logs / "epubcreator.log",
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        sink.setFormatter(formatter)
    except OSError:  # pragma: no cover
        sink = logging.StreamHandler(sys.stderr)
        sink.setFormatter(formatter)

    queue: Queue = Queue()
    handler = logging.handlers.QueueHandler(queue)
    root.addHandler(handler)
    root.setLevel(level)

    listener = logging.handlers.QueueListener(queue, sink)
    listener.start()

    global _listener_ref
    _listener_ref = listener  # إبقاء المرجع حيًّا طول عمر التطبيق