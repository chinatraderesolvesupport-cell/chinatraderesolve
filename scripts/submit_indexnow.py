from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

# When this file is executed as ``python scripts/submit_indexnow.py``, Python
# adds ``scripts/`` rather than the project root to sys.path. Add the root
# explicitly so the normal Render Shell command works without PYTHONPATH.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.seo_content import GUIDES, SUPPORTED_LANGUAGES

ENDPOINTS = (
    "https://yandex.com/indexnow",
    "https://api.indexnow.org/indexnow",
)


def validated_configuration() -> tuple[str, str, str]:
    base_url = (os.getenv("PUBLIC_BASE_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").rstrip("/")
    key = (os.getenv("INDEXNOW_KEY") or "").strip()
    parsed_base = urlsplit(base_url)
    if parsed_base.scheme != "https" or not parsed_base.hostname or parsed_base.path not in {"", "/"}:
        raise SystemExit("Set PUBLIC_BASE_URL or RENDER_EXTERNAL_URL to the production HTTPS site root")
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", key):
        raise SystemExit("Set a unique INDEXNOW_KEY (8-128 letters, digits, hyphens or underscores)")
    return base_url, key, parsed_base.netloc


def build_paths() -> list[str]:
    home_paths = ["/" if language == "ru" else f"/?lang={language}" for language in SUPPORTED_LANGUAGES]
    guide_paths = [f"/{language}/guides" for language in SUPPORTED_LANGUAGES]
    guide_paths.extend(
        f"/{language}/guides/{slug}"
        for language in SUPPORTED_LANGUAGES
        for slug in GUIDES[language]
    )
    # Preserve the intended order while ensuring a future content edit cannot
    # submit the same address twice.
    return list(dict.fromkeys(home_paths + guide_paths))


def build_payload(base_url: str, key: str, host: str, paths: list[str]) -> dict[str, object]:
    return {
        "host": host,
        "key": key,
        # The application exposes the verification file at the site root.
        # A keyLocation under /indexnow/ would only authorize URLs below that
        # path and causes HTTP 422 for the public guides.
        "keyLocation": f"{base_url}/{key}.txt",
        "urlList": [base_url + path for path in paths],
    }


def submit(endpoint: str, payload: dict[str, object], url_count: int) -> int:
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "ChinaTradeResolve/3.7.55",
        },
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        print(f"IndexNow {endpoint}: {response.status}; submitted URLs: {url_count}")
        return response.status


def main() -> int:
    base_url, key, host = validated_configuration()
    paths = build_paths()
    payload = build_payload(base_url, key, host, paths)
    successes = 0
    for endpoint in ENDPOINTS:
        try:
            submit(endpoint, payload, len(paths))
            successes += 1
        except Exception as exc:
            print(f"IndexNow {endpoint} failed: {exc}", file=sys.stderr)
    return 0 if successes else 1


if __name__ == "__main__":
    raise SystemExit(main())
