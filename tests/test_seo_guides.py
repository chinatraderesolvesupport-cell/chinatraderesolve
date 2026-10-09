"""Indexability and useful entry points for all localized dispute guides."""

from html.parser import HTMLParser
from html import unescape
import json
import os
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_PATH", str(Path(tempfile.mkdtemp()) / "seo-test.db"))
os.environ.setdefault("ADMIN_TOKEN", "seo-test-admin-token-abcdefghijklmnopqrstuvwxyz")
os.environ.setdefault("APP_SECRET", "seo-test-app-secret-abcdefghijklmnopqrstuvwxyz-0123456789")

from app.main import app, settings
from app.seo_content import GUIDES, GUIDE_MODIFIED_DATE, SUPPORTED_LANGUAGES


class Headings(HTMLParser):
    def __init__(self):
        super().__init__()
        self.titles = []
        self.descriptions = []
        self.canonicals = []
        self.alternates = {}
        self.h1 = []
        self._capture = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._capture = (self.titles, [])
        elif tag == "h1":
            self._capture = (self.h1, [])
        elif tag == "meta" and attrs.get("name") == "description":
            self.descriptions.append(attrs.get("content"))
        elif tag == "link" and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs.get("href"))
        elif tag == "link" and attrs.get("rel") == "alternate":
            self.alternates[attrs.get("hreflang")] = attrs.get("href")

    def handle_endtag(self, tag):
        if tag in {"title", "h1"} and self._capture:
            target, parts = self._capture
            target.append("".join(parts))
            self._capture = None

    def handle_data(self, data):
        if self._capture:
            self._capture[1].append(data)


def test_all_72_guide_pages_have_unique_localized_metadata_and_reciprocal_links():
    base = settings.public_base_url.rstrip("/")
    assert len(SUPPORTED_LANGUAGES) == 6
    assert {len(GUIDES[lang]) for lang in SUPPORTED_LANGUAGES} == {12}
    with TestClient(app) as client:
        for lang in SUPPORTED_LANGUAGES:
            titles, descriptions = set(), set()
            home = client.get("/" if lang == "ru" else f"/?lang={lang}")
            assert home.status_code == 200
            for slug in ("supplier-not-refunding", "alibaba-dispute-closed-no-refund"):
                assert f'data-guide-slug="{slug}" href="/{lang}/guides/{slug}"' in home.text
                assert GUIDES[lang][slug]["title"] in unescape(home.text)
            for slug, guide in GUIDES[lang].items():
                path = f"/{lang}/guides/{slug}"
                page = client.get(path)
                assert page.status_code == 200
                assert 'name="robots" content="index,follow' in page.text
                parsed = Headings()
                parsed.feed(page.text)
                assert len(parsed.titles) == len(parsed.descriptions) == len(parsed.canonicals) == len(parsed.h1) == 1
                assert parsed.h1 == [guide["title"]]
                assert guide["title"] in parsed.titles[0]
                assert parsed.descriptions == [guide["description"]]
                assert parsed.canonicals == [base + path]
                assert parsed.alternates == {
                    **{code: f"{base}/{code}/guides/{slug}" for code in SUPPORTED_LANGUAGES},
                    "x-default": f"{base}/en/guides/{slug}",
                }
                assert guide.get("summary"), path
                assert f'href="/?lang={lang}#submit"' in page.text
                assert f'href="/{lang}/guides/{guide["related_slugs"][0]}"' in page.text
                assert f'"dateModified": "{GUIDE_MODIFIED_DATE}"' in page.text
                script = re.search(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', page.text, re.S)
                assert script, path
                graph = json.loads(script.group(1))["@graph"]
                article = next(item for item in graph if item["@type"] == "Article")
                assert article["headline"] == guide["title"]
                assert article["mainEntityOfPage"] == base + path
                assert article["dateModified"] == GUIDE_MODIFIED_DATE
                assert any(item["@type"] == "BreadcrumbList" for item in graph)
                assert parsed.titles[0] not in titles, path
                assert parsed.descriptions[0] not in descriptions, path
                titles.add(parsed.titles[0])
                descriptions.add(parsed.descriptions[0])


def test_sitemap_contains_every_localized_guide_and_truthful_dates(monkeypatch):
    base = settings.public_base_url.rstrip("/")
    monkeypatch.setattr("app.main.search_indexing_is_ready", lambda: True)
    with TestClient(app) as client:
        robots = client.get("/robots.txt")
        assert robots.status_code == 200
        assert "Allow: /" in robots.text
        assert f"Sitemap: {base}/sitemap.xml" in robots.text
        response = client.get("/sitemap.xml")
        assert response.status_code == 200
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "x": "http://www.w3.org/1999/xhtml"}
    urls = ET.fromstring(response.content).findall("s:url", ns)
    by_url = {url.findtext("s:loc", namespaces=ns): url for url in urls}
    assert len(by_url) == len(urls) == 90
    for lang in SUPPORTED_LANGUAGES:
        for slug in GUIDES[lang]:
            canonical = f"{base}/{lang}/guides/{slug}"
            entry = by_url[canonical]
            assert entry.findtext("s:lastmod", namespaces=ns) == GUIDE_MODIFIED_DATE
            alternates = {item.attrib["hreflang"]: item.attrib["href"] for item in entry.findall("x:link", ns)}
            assert alternates == {
                **{code: f"{base}/{code}/guides/{slug}" for code in SUPPORTED_LANGUAGES},
                "x-default": f"{base}/en/guides/{slug}",
            }
    assert by_url[f"{base}/privacy"].findtext("s:lastmod", namespaces=ns) == "2026-07-28"
    assert not any("/case/" in url or "/admin" in url or "/api/" in url for url in by_url)
