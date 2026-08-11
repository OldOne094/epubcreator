"""اختبارات نظام فحص التحديثات (app/updates.py)."""
from __future__ import annotations

import json

from app import __version__ as APP_VERSION
from app.updates import fetch_latest, is_newer, normalize_version, resolve_url


def test_normalize_version():
    assert normalize_version("v1.2.3") == (1, 2, 3)
    assert normalize_version("0.2.0-beta") == (0, 2, 0)
    assert normalize_version("10.0.0") == (10, 0, 0)
    assert normalize_version("garbage") == (0, 0, 0)
    assert normalize_version("") == (0, 0, 0)


def test_is_newer():
    assert is_newer("1.0.0", APP_VERSION) is True  # نسخة أكبر دوما أحدث
    assert is_newer("0.1.9", "0.2.0") is False
    assert is_newer("0.2.0", "0.2.0") is False
    assert is_newer("0.2.1", "0.2.0") is True
    assert is_newer("garbage", "0.2.0") is False


def test_fetch_no_such_url(tmp_path):
    result = fetch_latest((tmp_path / "missing.json").as_uri())
    assert result.ok is False
    assert result.error


def test_fetch_has_newer_version(tmp_path):
    p = tmp_path / "latest.json"
    p.write_text(
        json.dumps({
            "version": "9.9.9",
            "url": "https://example.com/EPubCreator.exe",
            "note": "إصلاحات وتحسينات",
        }),
        encoding="utf-8",
    )
    result = fetch_latest(p.as_uri())
    assert result.ok is True
    assert result.has_update is True
    assert result.latest == "9.9.9"
    assert result.current == APP_VERSION
    assert result.change_url == "https://example.com/EPubCreator.exe"
    assert result.note == "إصلاحات وتحسينات"


def test_fetch_current_is_latest(tmp_path):
    p = tmp_path / "latest.json"
    p.write_text(json.dumps({"version": APP_VERSION}), encoding="utf-8")
    result = fetch_latest(p.as_uri())
    assert result.ok is True
    assert result.has_update is False


def test_fetch_older_version_no_update(tmp_path):
    p = tmp_path / "latest.json"
    p.write_text(json.dumps({"version": "0.1.0"}), encoding="utf-8")
    assert fetch_latest(p.as_uri()).has_update is False


def test_fetch_empty_url():
    result = fetch_latest("")
    assert result.ok is False
    assert "update_url" in result.error


def test_fetch_invalid_json(tmp_path):
    p = tmp_path / "latest.json"
    p.write_text("not json", encoding="utf-8")
    result = fetch_latest(p.as_uri())
    assert result.ok is False


def test_fetch_missing_version_key(tmp_path):
    p = tmp_path / "latest.json"
    p.write_text(json.dumps({"note": "x"}), encoding="utf-8")
    result = fetch_latest(p.as_uri())
    assert result.ok is False
    assert "بلا إصدار" in result.error


def test_fetch_non_dict_payload(tmp_path):
    p = tmp_path / "latest.json"
    p.write_text("[1,2,3]", encoding="utf-8")
    result = fetch_latest(p.as_uri())
    assert result.ok is False


def test_updatecheckjob_emits_result(tmp_path):
    from app.workers import UpdateCheckJob

    p = tmp_path / "latest.json"
    p.write_text(json.dumps({"version": "9.0.0"}), encoding="utf-8")
    job = UpdateCheckJob(p.as_uri())
    got = []
    job.signals.finished.connect(got.append)
    job.signals.error.connect(lambda m: got.append(m))
    job.run()
    assert len(got) == 1
    assert got[0].ok and got[0].has_update and got[0].latest == "9.0.0"


def test_update_url_in_default_config():
    from app.settings import DEFAULT_CONFIG

    assert DEFAULT_CONFIG["update_url"] == ""


# ------------------------------------------------- GitHub Releases API ---


def test_resolve_url_owner_slug():
    url = resolve_url("myuser/EPubCreator")
    assert url == "https://api.github.com/repos/myuser/EPubCreator/releases/latest"


def test_resolve_url_passthrough():
    assert resolve_url("https://example.com/latest.json").startswith("https://")
    assert resolve_url("file:///c:/x.json") != ""
    assert resolve_url("") == ""


def test_fetch_github_shape_newer(tmp_path):
    p = tmp_path / "release.json"
    p.write_text(json.dumps({
        "tag_name": "v9.0.0",
        "html_url": "https://github.com/me/repo/releases/tag/v9.0.0",
        "body": "تحسينات الواجهة",
        "assets": [{"name": "EPubCreator.exe",
                    "browser_download_url": "https://github.com/me/repo/releases/download/v9.0.0/EPubCreator.exe"}],
    }), encoding="utf-8")
    result = fetch_latest(p.as_uri())
    assert result.ok
    assert result.has_update
    assert result.latest == "v9.0.0"
    assert result.change_url.endswith("EPubCreator.exe")
    assert result.note == "تحسينات الواجهة"


def test_fetch_github_shape_no_assets(tmp_path):
    p = tmp_path / "release.json"
    p.write_text(json.dumps({
        "tag_name": "v9.0.0",
        "html_url": "https://github.com/me/repo/releases/tag/v9.0.0",
    }), encoding="utf-8")
    result = fetch_latest(p.as_uri())
    assert result.ok and result.has_update
    assert result.change_url.startswith("https://github.com/")


def test_fetch_github_no_release_error(tmp_path):
    p = tmp_path / "release.json"
    p.write_text(json.dumps({"message": "Not Found", "documentation_url": "https://docs"}), encoding="utf-8")
    result = fetch_latest(p.as_uri())
    assert result.ok is False
    assert "لا توجد إصدارات" in result.error


def test_fetch_github_rate_limit_error(tmp_path):
    p = tmp_path / "release.json"
    p.write_text(json.dumps({"message": "API rate limit exceeded"}), encoding="utf-8")
    result = fetch_latest(p.as_uri())
    assert result.ok is False
    assert "rate limit" in result.error


def test_fetch_github_older_or_same_no_update(tmp_path):
    p = tmp_path / "release.json"
    p.write_text(json.dumps({"tag_name": "v0.1.0"}), encoding="utf-8")
    assert fetch_latest(p.as_uri()).has_update is False