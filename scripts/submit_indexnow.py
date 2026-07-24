from __future__ import annotations

import json
import os
import re
import sys
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from app.seo_content import GUIDES, SUPPORTED_LANGUAGES

BASE_URL = (os.getenv("PUBLIC_BASE_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").rstrip("/")
KEY = (os.getenv("INDEXNOW_KEY") or "").strip()

parsed_base = urlsplit(BASE_URL)
if parsed_base.scheme != "https" or not parsed_base.hostname or parsed_base.path not in {"", "/"}:
    raise SystemExit("Set PUBLIC_BASE_URL or RENDER_EXTERNAL_URL to the production HTTPS site root")
if not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", KEY):
    raise SystemExit("Set a unique INDEXNOW_KEY (8-128 letters, digits, hyphens or underscores)")

home_paths = ["/" if language == "ru" else f"/?lang={language}" for language in SUPPORTED_LANGUAGES]
guide_paths = [f"/{language}/guides" for language in SUPPORTED_LANGUAGES]
guide_paths.extend(
    f"/{language}/guides/{slug}"
    for language in SUPPORTED_LANGUAGES
    for slug in GUIDES[language]
)
paths = home_paths + guide_paths
payload = {
    "host": parsed_base.netloc,
    "key": KEY,
    "keyLocation": f"{BASE_URL}/indexnow/{KEY}.txt",
    "urlList": [BASE_URL + path for path in paths],
}
request = Request(
    "https://api.indexnow.org/indexnow",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "ChinaTradeResolve/1.0"},
    method="POST",
)
try:
    with urlopen(request, timeout=30) as response:
        print(f"IndexNow response: {response.status}; submitted URLs: {len(paths)}")
except Exception as exc:
    print(f"IndexNow submission failed: {exc}", file=sys.stderr)
    raise SystemExit(1)
