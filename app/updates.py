"""نظام فحص التحديثات (Check for Updates) — مكتبة قياسية فقط (لا تبعيات).

يقرأ إصدار التطبيق الحالي من `app.__version__` ويقارنه بإصدارٍ يُجلب من
رابط JSON (config: `update_url`) بصيغتين:

1. **رابط JSON مباشر** (http/https أو file:// للاختبار):
       {"version": "0.2.0", "url": "…", "note": "…"}
2. **مستودع GitHub** — اكتب `owner/repo` (أو رابط release API كاملًا) فيستعمل
   GitHub Releases API (`…/releases/latest`) ويقرأ `tag_name`/`html_url` وملف الرفع.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from app import __version__ as APP_CURRENT_VERSION

_VERSION_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)([.-]?(.+))?", re.IGNORECASE)

_EMPTY: tuple[int, int, int] = (0, 0, 0)

_GITHUB_API_LATEST = "https://api.github.com/repos/{owner}/{repo}/releases/latest"


def normalize_version(text: str) -> tuple[int, int, int]:
    """تحويل نص إصدار (مثل v1.2.3 أو 0.2.0-beta) إلى ثلاثية قابلة للمقارنة."""
    match = _VERSION_RE.match(str(text).strip())
    if not match:
        return _EMPTY
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def is_newer(candidate: str, current: str) -> bool:
    """هل c‌andidate أحدث من current (مقارنة ثلاثية الإصدار)؟"""
    candidate_ver = normalize_version(candidate)
    current_ver = normalize_version(current)
    if candidate_ver == _EMPTY or current_ver == _EMPTY:
        return False
    return candidate_ver > current_ver


def resolve_url(update_url: str) -> str:
    """تحويل update_url إلى عنوان قابل للجلب.

    - إن لم يكن رابطًا (أي بصيغة owner/repo) يُبنى رابط GitHub latest.
    - وإن كان رابطًا (http/https/file) يُبقى كما هو.
    """
    value = str(update_url).strip()
    if not value:
        return ""
    if "://" in value:
        return value
    parts = value.split("/")
    if len(parts) == 2 and parts[0] and parts[1]:
        return _GITHUB_API_LATEST.format(owner=parts[0], repo=parts[1])
    return value


@dataclass
class UpdateResult:
    """نتاج فحص التحديثات — مستقل عن Qt لسهولة الاختبار."""

    ok: bool
    has_update: bool = False
    current: str = field(default_factory=lambda: APP_CURRENT_VERSION)
    latest: str = ""
    change_url: str = ""
    note: str = ""
    error: str = ""


def _user_agent() -> dict[str, str]:
    return {"User-Agent": f"EPubCreator/{APP_CURRENT_VERSION}"}


def _parse_payload(payload: Any) -> UpdateResult:
    """تحويل JSON من خادم HTML/GitHub إلى UpdateResult."""
    if not isinstance(payload, dict):
        return UpdateResult(ok=False, error="استجابة خادم التحديثات غير صالحة")
    # GitHub Release API يردّ بكائن خطأ عند غياب الإصدارات أو تجاوز الحد
    message = payload.get("message")
    if message and "tag_name" not in payload and "version" not in payload:
        text = str(message)
        if "404" in text or "Not Found" in text:
            text = "لا توجد إصدارات بعد على المستودع"
        return UpdateResult(ok=False, error=f"GitHub: {text}")

    latest = str(payload.get("tag_name") or payload.get("version", "")).strip()
    if not latest:
        return UpdateResult(ok=False, error="استجابة خادم التحديثات بلا إصدار")

    change_url = str(payload.get("url") or payload.get("html_url", "") or "")
    assets = payload.get("assets")
    if isinstance(assets, list):
        for asset in assets:
            if isinstance(asset, dict) and asset.get("browser_download_url"):
                name = str(asset.get("name", "")).lower()
                if name.endswith(".exe") or not change_url:
                    change_url = str(asset["browser_download_url"])
                    if name.endswith(".exe"):
                        break
    return UpdateResult(
        ok=True,
        has_update=is_newer(latest, APP_CURRENT_VERSION),
        latest=latest,
        change_url=change_url,
        note=str(payload.get("body") or payload.get("note", "") or ""),
    )


def fetch_latest(update_url: str, timeout: float = 5.0) -> UpdateResult:
    """أحدث إصدار من update_url (JSON أو GitHub releases) ومقارنته بالحالي."""
    url = resolve_url(update_url)
    if not url:
        return UpdateResult(ok=False, error="لم يُضبط رابط فحص التحديثات (config: update_url)")
    try:
        request = urllib.request.Request(url, headers=_user_agent())
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload: Any = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            body = json.load(exc)
        except (ValueError, UnicodeDecodeError):
            body = None
        if isinstance(body, dict) and body.get("message"):
            detail = str(body["message"])
        code_note = " (لا توجد إصدارات بعد؟)" if exc.code == 404 else ""
        return UpdateResult(ok=False, error=f"فشل الجلب (HTTP {exc.code}){code_note} {detail}".strip())
    except (OSError, ValueError) as exc:
        return UpdateResult(ok=False, error=f"تعذّر الوصول إلى خادم التحديثات: {exc}")
    return _parse_payload(payload)