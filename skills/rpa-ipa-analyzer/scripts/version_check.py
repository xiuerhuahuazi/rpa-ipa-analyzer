#!/usr/bin/env python3
"""
Version checker for rpa-ipa-analyzer skill.
Compares installed version (VERSION file) against GitHub latest release.
Outputs a JSON report. Used by SKILL.md session initialization.

Exit codes: 0 = up to date, 1 = update available, 2 = error (network/GitHub)
"""
import json
import urllib.request
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
VERSION_FILE = SKILL_DIR / "VERSION"
CACHE_FILE = SKILL_DIR / ".version_check_cache"
CACHE_TTL_HOURS = 24


def get_installed_version() -> str:
    return VERSION_FILE.read_text().strip()


def read_cache() -> dict | None:
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text())
        checked_at = datetime.fromisoformat(data.get("checked_at", ""))
        if datetime.now(timezone.utc) - checked_at < timedelta(hours=CACHE_TTL_HOURS):
            return data.get("result")
    except Exception:
        pass
    return None


def write_cache(result: dict) -> None:
    CACHE_FILE.write_text(json.dumps({
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "result": result
    }, ensure_ascii=False))


def get_latest_github_version() -> dict:
    url = "https://api.github.com/repos/xiuerhuahuazi/rpa-ipa-analyzer/releases/latest"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "rpa-ipa-analyzer-version-check"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)
        tag = data.get("tag_name", "")
        version = tag.lstrip("v")
        return {"latest": version, "tag": tag, "url": data.get("html_url", ""),
                "published_at": data.get("published_at", ""),
                "name": data.get("name", "")}
    except Exception as e:
        return {"error": str(e)}


def main():
    installed = get_installed_version()

    # Check cache first
    cached = read_cache()
    if cached is not None:
        print(json.dumps(cached, ensure_ascii=False))
        return 0 if cached.get("status") == "up_to_date" else 1

    latest_info = get_latest_github_version()
    if "error" in latest_info:
        result = {"status": "error", "installed": installed, "error": latest_info["error"]}
        print(json.dumps(result, ensure_ascii=False))
        return 2

    latest = latest_info["latest"]
    if installed == latest:
        result = {"status": "up_to_date", "installed": installed, "latest": latest}
        write_cache(result)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    else:
        result = {"status": "update_available", "installed": installed, **latest_info}
        write_cache(result)
        print(json.dumps(result, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    exit(main())
