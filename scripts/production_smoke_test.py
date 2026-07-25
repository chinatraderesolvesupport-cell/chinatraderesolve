from __future__ import annotations

"""Deep production verification for ChinaTradeResolve.

Run this script from a Render Shell after a deploy. It deliberately performs
real provider calls and sends real test email. A live run requires the explicit
``--confirm-live`` flag so it cannot be triggered accidentally by CI.
"""

import argparse
import asyncio
import json
import os
import secrets
import sys
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
import pikepdf
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app import main as main_module
from app.ai_assistant import assistant_reply
from app.config import settings
from app.db import delete_case_now, execute, get_case_by_public, transaction
from app.notifications import deliver_pending
from app.schemas import AssistantChatRequest
from app.voice_transcription import transcribe_audio


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VOICE_FILE = ROOT / "tests" / "fixtures" / "production-smoke-voice.wav"
DEFAULT_REPORT = ROOT / "production_smoke_report.json"


class SmokeFailure(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_error(exc: BaseException) -> str:
    text = " ".join(str(exc).split())
    for marker in ("sk-", "Bearer "):
        if marker in text:
            text = text.split(marker, 1)[0] + marker + "[redacted]"
    return text[:500] or type(exc).__name__


def record(report: dict[str, Any], name: str, ok: bool, **details: Any) -> None:
    report["checks"][name] = {"ok": bool(ok), **details}
    if not ok:
        report["failures"].append(name)


def public_json(client: httpx.Client, base_url: str, path: str) -> tuple[int, dict[str, Any], dict[str, str]]:
    response = client.get(urljoin(base_url.rstrip("/") + "/", path.lstrip("/")))
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text[:1000]}
    return response.status_code, payload, dict(response.headers)


def make_png() -> bytes:
    image = Image.new("RGB", (900, 520), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 880, 500), outline="black", width=4)
    draw.text((60, 70), "ChinaTradeResolve production smoke test", fill="black")
    draw.text((60, 120), utc_now(), fill="black")
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def make_pdf() -> bytes:
    output = BytesIO()
    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page(page_size=(595, 842))
        pdf.save(output)
    return output.getvalue()


def notification_rows(case_id: int) -> list[dict[str, Any]]:
    with transaction() as conn:
        rows = execute(
            conn,
            "SELECT recipient,subject,body,status,attempts,error "
            "FROM notification_outbox WHERE case_id=? ORDER BY id",
            (case_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def wait_for_notifications(case_id: int, timeout_seconds: float = 35) -> list[dict[str, Any]]:
    deadline = time.monotonic() + timeout_seconds
    rows: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        deliver_pending(max_messages=10)
        rows = notification_rows(case_id)
        if rows and all(row.get("status") in {"sent", "failed"} for row in rows):
            return rows
        time.sleep(1)
    return rows


async def run_provider_checks(report: dict[str, Any], voice_file: Path) -> None:
    try:
        payload = AssistantChatRequest(
            language="ru",
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Это техническая проверка. Кратко назови три вида доказательств, "
                        "которые полезны в споре с китайским поставщиком."
                    ),
                }
            ],
        )
        reply = await assistant_reply(payload)
        record(
            report,
            "openai_assistant",
            bool(reply.strip()),
            reply_preview=" ".join(reply.split())[:300],
            model=settings.openai_assistant_model,
        )
    except Exception as exc:
        record(report, "openai_assistant", False, error=safe_error(exc))

    try:
        audio = voice_file.read_bytes()
        transcript = await transcribe_audio(
            audio,
            "audio/wav",
            "ru",
            "ctr-production-smoke-test",
        )
        record(
            report,
            "voice_transcription",
            bool(transcript.strip()),
            transcript=" ".join(transcript.split())[:500],
            model=settings.openai_transcription_model,
            fixture=voice_file.name,
        )
    except Exception as exc:
        record(report, "voice_transcription", False, error=safe_error(exc))


def run_application_flow(report: dict[str, Any], email: str, base_url: str, cleanup: bool) -> None:
    case_id: int | None = None
    case_reference = ""
    original_verify = main_module.verify_turnstile

    async def allow_smoke_turnstile(_token: str, _request: Any) -> bool:
        # This override exists only inside this administrator-run Python process.
        # It does not add a bypass to the deployed web application.
        return True

    main_module.verify_turnstile = allow_smoke_turnstile
    try:
        with TestClient(main_module.app, base_url=base_url) as client:
            nonce = secrets.token_hex(4).upper()
            payload = {
                "full_name": "PRODUCTION SMOKE TEST — DO NOT PROCESS",
                "email": email,
                "country": "Serbia",
                "preferred_language": "Russian",
                "purchasing_channel": "Alibaba",
                "amount_in_dispute": "EUR 1.00 TEST",
                "main_problem": "Wrong material or specification",
                "supplier_name": "TEST SUPPLIER — DO NOT PROCESS",
                "order_number": f"SMOKE-{nonce}",
                "order_value": "EUR 1.00 TEST",
                "requested_result": "Not sure",
                "description": (
                    "Автоматическая production-проверка формы, базы, приватной страницы, "
                    "почтовой очереди и загрузки документов. Это техническое тестовое дело; "
                    "его не нужно обрабатывать. Поставщик и сумма являются вымышленными."
                ),
                "company_website": "",
                "free_access_terms": True,
                "sharing_authority": True,
                "ai_consent": False,
                "no_guarantee": True,
                "turnstile_token": "administrator-render-shell-smoke-test",
                "utm_source": "production_smoke",
                "utm_medium": "render_shell",
                "utm_campaign": Path(ROOT / "VERSION.txt").read_text(encoding="utf-8").strip(),
                "utm_content": "deep_check",
                "landing_path": "/?lang=ru",
                "referrer": base_url,
            }
            response = client.post("/api/applications", json=payload)
            data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            record(
                report,
                "application_submit",
                response.status_code == 201,
                status_code=response.status_code,
                response=data,
            )
            if response.status_code != 201:
                return

            case_reference = str(data.get("case_reference") or "")
            status_path = str(data.get("status_url") or "")
            parts = [part for part in status_path.split("/") if part]
            if len(parts) < 3:
                raise SmokeFailure("Application response did not contain a valid private status URL")
            public_token = parts[-1]
            case = get_case_by_public(case_reference, public_token)
            if not case:
                raise SmokeFailure("Created case was not found in the configured database")
            case_id = int(case["id"])

            status_response = client.get(status_path)
            record(
                report,
                "private_status_page",
                status_response.status_code == 200 and case_reference in status_response.text,
                status_code=status_response.status_code,
                noindex=status_response.headers.get("x-robots-tag"),
                cache_control=status_response.headers.get("cache-control"),
            )

            files = [
                ("files", ("production-smoke.pdf", make_pdf(), "application/pdf")),
                ("files", ("production-smoke.png", make_png(), "image/png")),
            ]
            upload = client.post(
                f"{status_path}/documents",
                files=files,
                data={"document_consent": "true"},
                follow_redirects=False,
            )
            location = upload.headers.get("location", "")
            uploaded_page = client.get(location or status_path)
            upload_ok = (
                upload.status_code == 303
                and "production-smoke.pdf" in uploaded_page.text
                and "production-smoke.png" in uploaded_page.text
            )
            record(
                report,
                "document_upload",
                upload_ok,
                status_code=upload.status_code,
                redirect=location,
            )

            rows = wait_for_notifications(case_id)
            public_host = urlparse(base_url).netloc
            expected_count = 2 if settings.admin_email else 1
            all_sent = len(rows) == expected_count and all(row.get("status") == "sent" for row in rows)
            client_rows = [
                row for row in rows
                if not str(row.get("subject") or "").startswith("Новое дело ChinaTradeResolve:")
            ]
            links_use_public_domain = bool(client_rows) and all(
                public_host in str(row.get("body") or "") for row in client_rows
            )
            record(
                report,
                "email_delivery",
                all_sent and links_use_public_domain,
                expected_messages=expected_count,
                messages=[
                    {
                        "recipient": row.get("recipient"),
                        "subject": row.get("subject"),
                        "status": row.get("status"),
                        "attempts": row.get("attempts"),
                        "error": row.get("error"),
                    }
                    for row in rows
                ],
                links_use_public_domain=links_use_public_domain,
                public_domain=public_host,
            )
    except Exception as exc:
        record(report, "application_flow_exception", False, error=safe_error(exc))
    finally:
        main_module.verify_turnstile = original_verify
        if cleanup and case_id is not None:
            try:
                deleted = delete_case_now(case_id)
                record(
                    report,
                    "test_case_cleanup",
                    bool(deleted),
                    case_reference=case_reference,
                )
            except Exception as exc:
                record(report, "test_case_cleanup", False, error=safe_error(exc))
        elif case_id is not None:
            report["test_case_retained"] = {"case_id": case_id, "case_reference": case_reference}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the real ChinaTradeResolve production readiness, email, application, AI and voice checks."
    )
    parser.add_argument("--confirm-live", action="store_true", help="Required: permit real email and OpenAI calls")
    parser.add_argument("--base-url", default=os.getenv("SMOKE_TEST_BASE_URL") or settings.public_base_url)
    parser.add_argument("--email", default=os.getenv("SMOKE_TEST_EMAIL") or settings.admin_email or "")
    parser.add_argument("--voice-file", type=Path, default=DEFAULT_VOICE_FILE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--keep-test-case", action="store_true", help="Do not anonymise the generated test case")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report: dict[str, Any] = {
        "started_at": utc_now(),
        "version": (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip(),
        "base_url": args.base_url.rstrip("/"),
        "checks": {},
        "failures": [],
    }

    if not args.confirm_live:
        raise SystemExit("Refusing live provider calls without --confirm-live")
    if not args.email:
        raise SystemExit("Provide --email or set SMOKE_TEST_EMAIL")
    parsed = urlparse(args.base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise SystemExit("The production smoke test requires an HTTPS --base-url")
    if not args.voice_file.is_file():
        raise SystemExit(f"Voice fixture not found: {args.voice_file}")

    try:
        with httpx.Client(timeout=30, follow_redirects=True) as public_client:
            health_status, health, health_headers = public_json(public_client, args.base_url, "/health")
            record(
                report,
                "public_health",
                health_status == 200 and health.get("status") == "ok" and health.get("version") == report["version"],
                status_code=health_status,
                payload=health,
                x_app_version=health_headers.get("x-app-version"),
            )
            ready_status, ready, _ = public_json(public_client, args.base_url, "/ready")
            record(
                report,
                "public_ready",
                ready_status == 200 and ready.get("status") == "ready" and all(ready.get("checks", {}).values()),
                status_code=ready_status,
                payload=ready,
            )
            robots = public_client.get(urljoin(args.base_url.rstrip("/") + "/", "robots.txt"))
            record(
                report,
                "public_indexing",
                robots.status_code == 200 and "Allow: /" in robots.text and "Disallow: /" not in robots.text,
                status_code=robots.status_code,
                body=robots.text[:500],
            )
    except Exception as exc:
        record(report, "public_network_exception", False, error=safe_error(exc))

    run_application_flow(report, args.email, args.base_url, cleanup=not args.keep_test_case)
    asyncio.run(run_provider_checks(report, args.voice_file))

    report["completed_at"] = utc_now()
    report["ok"] = not report["failures"]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Report written to {args.report}", file=sys.stderr)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
