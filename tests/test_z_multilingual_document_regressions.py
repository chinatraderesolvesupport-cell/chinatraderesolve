from __future__ import annotations

import os
import tempfile
from io import BytesIO
from pathlib import Path

_tmp = tempfile.TemporaryDirectory()
os.environ.setdefault("DATABASE_PATH", str(Path(_tmp.name) / "multilingual-documents.db"))
os.environ.setdefault("ADMIN_TOKEN", "test-admin-token-abcdefghijklmnopqrstuvwxyz")
os.environ.setdefault("APP_SECRET", "test-app-secret-abcdefghijklmnopqrstuvwxyz-0123456789")
os.environ.setdefault("OPENAI_BILLING_READY", "false")
os.environ.setdefault("ENABLE_AI_TRIAGE", "false")
os.environ.setdefault("FREE_ACCESS_MODE", "true")
os.environ.setdefault("RENDER", "true")

import pikepdf
from PIL import Image
from fastapi.testclient import TestClient

from app.document_analysis import LANGUAGE_NAMES, _developer_prompt
from app.main import DOCUMENT_COPY, DOCUMENT_UPLOAD_ERROR_COPY, app


client = TestClient(app)

LANGUAGES = {
    "English": "en",
    "French": "fr",
    "German": "de",
    "Spanish": "es",
    "Russian": "ru",
    "Serbian": "sr",
}


def _payload(language: str, index: int) -> dict:
    return {
        "full_name": f"Language Test Buyer {index}",
        "email": f"language-doc-{index}@example.com",
        "country": "Serbia",
        "preferred_language": language,
        "purchasing_channel": "Alibaba",
        "amount_in_dispute": "EUR 4,000",
        "main_problem": "Wrong material or specification",
        "supplier_name": "Supplier Ltd",
        "order_number": f"LANG-{index}",
        "order_value": "EUR 12,000",
        "requested_result": "Partial refund",
        "description": (
            "The written order specifies the material, the supplier confirmed it in messages, "
            "and the delivered goods appear different. The buyer has an invoice, screenshots, "
            "photographs and a PDF order record for review."
        ),
        "company_website": "",
        "free_access_terms": True,
        "sharing_authority": True,
        "ai_consent": True,
        "no_guarantee": True,
    }


def _png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (80, 50), (245, 245, 245)).save(output, format="PNG")
    return output.getvalue()


def _jpg_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (80, 50), (235, 235, 235)).save(output, format="JPEG", quality=90)
    return output.getvalue()


def _pdf_bytes() -> bytes:
    output = BytesIO()
    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page(page_size=(595, 842))
        pdf.save(output)
    return output.getvalue()


def test_complete_document_workflow_is_localized_for_all_public_languages() -> None:
    for index, (language, code) in enumerate(LANGUAGES.items(), start=1):
        created = client.post(
            "/api/applications",
            json=_payload(language, index),
            headers={"x-forwarded-for": f"198.51.100.{20 + index}"},
        )
        assert created.status_code == 201, (language, created.text)
        status_url = created.json()["status_url"]

        initial = client.get(status_url)
        assert initial.status_code == 200
        assert f'<html lang="{code}">' in initial.text
        assert DOCUMENT_COPY[language]["heading"] in initial.text
        assert DOCUMENT_COPY[language]["select"] in initial.text
        assert DOCUMENT_COPY[language]["consent"] in initial.text

        upload = client.post(
            status_url + "/documents",
            data={"document_consent": "true"},
            files=[
                ("files", (f"screenshot-{code}.png", _png_bytes(), "image/png")),
                ("files", (f"photo-{code}.jpg", _jpg_bytes(), "image/jpeg")),
                ("files", (f"invoice-{code}.pdf", _pdf_bytes(), "application/pdf")),
            ],
            follow_redirects=False,
            headers={"x-forwarded-for": f"198.51.100.{20 + index}"},
        )
        assert upload.status_code == 303, (language, upload.text)

        uploaded_page = client.get(upload.headers["location"])
        assert uploaded_page.status_code == 200
        assert DOCUMENT_COPY[language]["uploaded"] in uploaded_page.text
        assert f"screenshot-{code}.png" in uploaded_page.text
        assert f"photo-{code}.jpg" in uploaded_page.text
        assert f"invoice-{code}.pdf" in uploaded_page.text
        if language != "English":
            assert DOCUMENT_COPY["English"]["uploaded"] not in uploaded_page.text

        broken = client.post(
            status_url + "/documents",
            data={"document_consent": "true"},
            files=[("files", (f"broken-{code}.pdf", b"%PDF-1.4\nnot-a-valid-pdf", "application/pdf"))],
            follow_redirects=False,
            headers={"x-forwarded-for": f"198.51.100.{20 + index}"},
        )
        assert broken.status_code == 303, (language, broken.text)
        broken_page = client.get(broken.headers["location"])
        assert broken_page.status_code == 200
        assert DOCUMENT_UPLOAD_ERROR_COPY[language]["invalid_pdf"] in broken_page.text
        if language != "English":
            assert DOCUMENT_UPLOAD_ERROR_COPY["English"]["invalid_pdf"] not in broken_page.text


def test_document_analysis_prompt_forces_selected_language_for_all_public_languages() -> None:
    assert set(LANGUAGES) == set(LANGUAGE_NAMES)
    for language in LANGUAGES:
        prompt = _developer_prompt(language)
        assert f"produce the structured report in {LANGUAGE_NAMES[language]}" in prompt
        assert "All user-facing prose must be entirely in the requested output language." in prompt


def test_serbian_document_copy_and_error_copy_are_not_english_fallbacks() -> None:
    critical_page_keys = (
        "heading", "intro", "privacy", "select", "consent", "upload", "uploaded",
        "analysis_title", "analysis_notice", "readiness", "inventory", "timeline",
        "key_evidence", "contradictions", "missing_evidence", "risk_flags", "next_steps",
    )
    for key in critical_page_keys:
        assert DOCUMENT_COPY["Serbian"][key].strip()
        assert DOCUMENT_COPY["Serbian"][key] != DOCUMENT_COPY["English"][key]

    for key, value in DOCUMENT_UPLOAD_ERROR_COPY["Serbian"].items():
        assert value.strip()
        assert value != DOCUMENT_UPLOAD_ERROR_COPY["English"][key]
