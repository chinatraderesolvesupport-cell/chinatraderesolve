#!/usr/bin/env python3
"""Production-safe SEO checks for ChinaTradeResolve v3.7.59.

Usage:
    python scripts/seo_smoke_test.py
    CTR_BASE_URL=https://chinatraderesolve.com python scripts/seo_smoke_test.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from html.parser import HTMLParser
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

import httpx

BASE_URL = os.getenv("CTR_BASE_URL", "https://chinatraderesolve.com").rstrip("/")
EXPECTED_VERSION = "3.7.59"
EXPECTED_GUIDE_DATE = "2026-10-09"
SAMPLE_PATHS = [
    "/ru/guides",
    "/en/guides",
    "/fr/guides/supplier-not-refunding",
    "/de/guides/alibaba-dispute-closed-no-refund",
    "/es/guides/customs-clearance-problem",
    "/sr/guides/order-not-delivered-tracking-problem",
]


class HeadParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self._in_title = False
        self.meta: dict[str, str] = {}
        self.links: list[dict[str, str]] = []
        self.h1_count = 0
        self.json_ld_blocks: list[str] = []
        self._json_ld = False
        self._json_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        data = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = data.get("name") or data.get("property")
            if key:
                self.meta[key] = data.get("content", "")
        elif tag == "link":
            self.links.append(data)
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "script" and data.get("type") == "application/ld+json":
            self._json_ld = True
            self._json_buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._json_ld:
            self._json_ld = False
            self.json_ld_blocks.append("".join(self._json_buffer).strip())

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._json_ld:
            self._json_buffer.append(data)


def check(condition: bool, label: str, failures: list[str]) -> None:
    if condition:
        print(f"PASS  {label}")
    else:
        print(f"FAIL  {label}")
        failures.append(label)


def main() -> int:
    failures: list[str] = []
    with httpx.Client(timeout=25.0, follow_redirects=True, headers={"User-Agent": "ChinaTradeResolve-SEO-Smoke/3.7.59"}) as client:
        # The Render auto-deploy starts independently of GitHub CI. Wait for the
        # new sitemap marker so a successful smoke test cannot inspect old code.
        for attempt in range(24):
            try:
                marker = client.get(BASE_URL + "/sitemap.xml")
                if marker.status_code == 200 and f"<lastmod>{EXPECTED_GUIDE_DATE}</lastmod>" in marker.text:
                    break
            except httpx.RequestError:
                pass
            if attempt < 23:
                time.sleep(5)
        else:
            print("FAIL  October guide deployment was not visible within two minutes")
            return 1

        ready = client.get(urljoin(BASE_URL + "/", "ready"))
        check(ready.status_code == 200 and ready.json().get("status") == "ready", "/ready returns HTTP 200 and ready", failures)
        health = client.get(urljoin(BASE_URL + "/", "health"))
        check(health.status_code == 200, "health returns HTTP 200", failures)
        if health.status_code == 200:
            payload = health.json()
            check(payload.get("version") == EXPECTED_VERSION, f"health version is {EXPECTED_VERSION}", failures)
            check(payload.get("public_launch_ready") is True, "public launch is ready", failures)

        robots = client.get(urljoin(BASE_URL + "/", "robots.txt"))
        check(robots.status_code == 200, "robots.txt returns HTTP 200", failures)
        check("Allow: /" in robots.text, "robots.txt allows crawling", failures)
        check("/sitemap.xml" in robots.text, "robots.txt advertises sitemap", failures)

        sitemap = client.get(urljoin(BASE_URL + "/", "sitemap.xml"))
        check(sitemap.status_code == 200, "sitemap.xml returns HTTP 200", failures)
        check("/ru/guides/supplier-not-refunding" in sitemap.text, "Russian refund guide is in sitemap", failures)
        check("/en/guides/supplier-not-refunding" in sitemap.text, "English refund guide is in sitemap", failures)
        for language in ("ru", "en", "fr", "de", "es", "sr"):
            check(f"/{language}/guides/supplier-not-refunding" in sitemap.text, f"{language} refund guide is in sitemap", failures)
        if sitemap.status_code == 200:
            ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            urls = ET.fromstring(sitemap.content).findall("s:url", ns)
            locations = {entry.findtext("s:loc", namespaces=ns): entry for entry in urls}
            check(len(locations) == len(urls) == 90, "sitemap contains 90 unique public URLs", failures)
            for language in ("ru", "en", "fr", "de", "es", "sr"):
                check(sum(f"/{language}/guides/" in url for url in locations) == 12, f"{language} has all 12 guides", failures)
            check(locations.get(BASE_URL + "/ru/guides/supplier-not-refunding") is not None, "refund page has a sitemap entry", failures)

        for path in SAMPLE_PATHS:
            response = client.get(BASE_URL + path)
            check(response.status_code == 200, f"{path} returns HTTP 200", failures)
            if response.status_code != 200:
                continue
            parser = HeadParser()
            parser.feed(response.text)
            check(bool(parser.title.strip()), f"{path} has a title", failures)
            check(bool(parser.meta.get("description", "").strip()), f"{path} has a meta description", failures)
            check(parser.meta.get("robots", "").startswith("index,follow"), f"{path} is indexable", failures)
            canonical = next((item.get("href") for item in parser.links if item.get("rel") == "canonical"), None)
            check(canonical == BASE_URL + path, f"{path} has the expected canonical", failures)
            check(parser.h1_count == 1, f"{path} has exactly one H1", failures)
            if "/guides/" in path:
                check(parser.meta.get("article:modified_time") == EXPECTED_GUIDE_DATE, f"{path} has current modification date", failures)
                alternates = {item.get("hreflang"): item.get("href") for item in parser.links if item.get("rel") == "alternate"}
                check(all(alternates.get(lang) == BASE_URL + path.replace(path.split("/")[1], lang, 1) for lang in ("ru", "en", "fr", "de", "es", "sr")), f"{path} has reciprocal language targets", failures)
            for block in parser.json_ld_blocks:
                try:
                    json.loads(block)
                except json.JSONDecodeError:
                    check(False, f"{path} has valid JSON-LD", failures)
                    break
            else:
                check(bool(parser.json_ld_blocks), f"{path} has valid JSON-LD", failures)

    print()
    if failures:
        print(f"SEO smoke test failed: {len(failures)} problem(s).")
        return 1
    print("SEO smoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
