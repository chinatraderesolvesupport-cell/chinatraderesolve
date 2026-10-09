"""Real-browser application flow against an isolated app, official Turnstile test keys and local mail sink.

No test here can reach the production database or send mail to an external address.
"""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time

import httpx
from PIL import Image
from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PASS_SITE = "1x00000000000000000000AA"
PASS_SECRET = "1x0000000000000000000000000000000AA"
FAIL_SECRET = "2x0000000000000000000000000000000AA"
DUPLICATE_SECRET = "3x0000000000000000000000000000000AA"
DUMMY_TOKEN = "XXXX.DUMMY.TOKEN.XXXX"


class MailSink(BaseHTTPRequestHandler):
    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if payload.get("secret") != "isolated-test-mail-secret":
            self.send_error(403)
            return
        if self.server.fail_mail:
            self.send_error(503)
            return
        self.server.messages.append(payload)
        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextmanager
def isolated_app(secret=PASS_SECRET, expected_mail_failure=False):
    with tempfile.TemporaryDirectory(prefix="ctr-e2e-") as directory:
        sink = ThreadingHTTPServer(("127.0.0.1", 0), MailSink)
        sink.messages = []
        sink.fail_mail = False
        sink_thread = threading.Thread(target=sink.serve_forever, daemon=True)
        sink_thread.start()
        port = free_port()
        base = f"http://127.0.0.1:{port}"
        database = Path(directory) / "cases.db"
        env = os.environ.copy()
        for name in ("DATABASE_URL", "SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "OPENAI_API_KEY"):
            env.pop(name, None)
        env.update({
            "DATABASE_PATH": str(database),
            "PUBLIC_BASE_URL": base,
            "PUBLIC_LAUNCH_MODE": "false",
            "ENABLE_AI_TRIAGE": "false",
            "OPENAI_BILLING_READY": "false",
            "TURNSTILE_SITE_KEY": PASS_SITE,
            "TURNSTILE_SECRET_KEY": secret,
            "EMAIL_BRIDGE_URL": f"http://127.0.0.1:{sink.server_address[1]}/mail",
            "EMAIL_BRIDGE_SECRET": "isolated-test-mail-secret",
            "ADMIN_EMAIL": "admin@example.com",
            "ADMIN_TOKEN": "isolated-admin-token-abcdefghijklmnopqrstuvwxyz",
            "APP_SECRET": "isolated-app-secret-abcdefghijklmnopqrstuvwxyz-0123456789",
            "NO_PROXY": "localhost,127.0.0.1",
            "no_proxy": "localhost,127.0.0.1",
        })
        log_path = Path(directory) / "server.log"
        with log_path.open("w+") as log:
            process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
            )
            try:
                with httpx.Client(trust_env=False, timeout=3) as http:
                    for _ in range(100):
                        if process.poll() is not None:
                            raise AssertionError("Isolated server exited before readiness")
                        try:
                            if http.get(base + "/health").status_code == 200:
                                break
                        except httpx.TransportError:
                            time.sleep(0.1)
                    else:
                        raise AssertionError("Isolated server never became ready")
                    yield base, database, sink, http, env
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                sink.shutdown()
                sink.server_close()
                sink_thread.join(timeout=5)
                log.flush()
                log.seek(0)
                output = log.read()
                if expected_mail_failure:
                    assert "Email delivery failed" in output, "Expected mail failure was not logged"
                else:
                    assert "Traceback" not in output and "ERROR:" not in output, "Isolated server error in test log"


def application_payload(**overrides):
    payload = {
        "full_name": "Тестовый Покупатель",
        "email": "buyer@example.com",
        "preferred_language": "Russian",
        "purchasing_channel": "Alibaba",
        "main_problem": "Goods not delivered",
        "description": "Тестовый заказ оплачен, но товар не отправлен. Сохранились счёт, переписка с поставщиком и подтверждение оплаты.",
        "free_access_terms": True,
        "sharing_authority": True,
        "ai_consent": False,
        "no_guarantee": True,
        "turnstile_token": DUMMY_TOKEN,
        "company_website": "",
    }
    payload.update(overrides)
    return payload


def case_count(database):
    with sqlite3.connect(database) as conn:
        return conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]


def fill_application(page, base):
    page.goto(base + "/?lang=ru", wait_until="domcontentloaded")
    expect(page.locator("html")).to_have_attribute("lang", "ru")
    expect(page.locator("#applicationTurnstileWidget")).to_have_attribute("data-sitekey", PASS_SITE)
    page.locator("#fullName").fill("Тестовый Покупатель")
    page.locator("#email").fill("buyer@example.com")
    page.locator("#channel").select_option(label="Alibaba")
    page.locator("#mainProblem").select_option(value="Goods not delivered")
    page.locator("#nextBtn").click()
    expect(page.locator("#stepTwo")).to_have_class(re.compile("active"))
    page.locator("#description").fill(application_payload()["description"])
    for name in ("free_access_terms", "sharing_authority", "no_guarantee"):
        page.locator(f'input[name="{name}"]').check()
    expect(page.locator("#submitBtn")).to_be_enabled(timeout=30000)


def test_browser_application_mobile_case_upload_and_local_mail_delivery():
    with isolated_app() as (base, database, sink, http, _env):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(locale="ru-RU", viewport={"width": 390, "height": 844}, device_scale_factor=1)
                fill_application(page, base)
                page.evaluate("window.ctrApplicationTurnstileExpired()")
                expect(page.locator("#submitBtn")).to_be_enabled(timeout=30000)
                page.evaluate("window.ctrApplicationTurnstileError('110200')")
                expect(page.locator("#submitBtn")).to_be_disabled()
                expect(page.locator("#applicationTurnstileRetry")).to_be_visible()
                page.locator("#applicationTurnstileRetry").click()
                expect(page.locator("#submitBtn")).to_be_enabled(timeout=30000)
                page.locator("#submitBtn").click()
                expect(page.locator("#confirmation")).to_be_visible(timeout=30000)
                reference = page.locator("#caseNumber").inner_text()
                assert re.fullmatch(r"CTR-[A-Z0-9-]+", reference), reference
                link = page.locator("#statusLink").get_attribute("href")
                assert link and link.startswith(base + "/case/" + reference + "/")
                assert case_count(database) == 1
                assert len(sink.messages) == 2
                assert {message["to"] for message in sink.messages} == {"buyer@example.com", "admin@example.com"}
                assert all(reference in message["subject"] for message in sink.messages)
                assert link in next(message["body"] for message in sink.messages if message["to"] == "buyer@example.com")
                assert all(message["secret"] == "isolated-test-mail-secret" for message in sink.messages)
                assert http.get(link).status_code == 200
                page.goto(link)
                expect(page.locator("#documents")).to_be_visible()
                image = BytesIO()
                Image.new("RGB", (16, 16), "white").save(image, format="PNG")
                page.locator("#documentFiles").set_input_files({"name": "test-evidence.png", "mimeType": "image/png", "buffer": image.getvalue()})
                page.locator('input[name="document_consent"]').check()
                page.locator("#documentUploadButton").click()
                expect(page.locator("#documentUploadNotice")).to_be_visible(timeout=15000)
                assert "test-evidence.png" in page.locator("#documents").inner_text()
                assert http.get(link.replace(reference, "CTR-NOT-FOUND", 1)).status_code == 404
            finally:
                browser.close()


def test_browser_rejected_token_keeps_input_and_shows_russian_error():
    with isolated_app(DUPLICATE_SECRET) as (base, database, sink, _http, _env):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(locale="ru-RU", viewport={"width": 390, "height": 844})
                fill_application(page, base)
                page.locator("#submitBtn").click()
                expect(page.locator("#submitStatus")).to_contain_text("Не удалось завершить проверку", timeout=30000)
                assert page.locator("#description").input_value() == application_payload()["description"]
                assert page.locator("#email").input_value() == "buyer@example.com"
                expect(page.locator("#caseForm")).to_be_visible()
                assert case_count(database) == 0
                assert sink.messages == []
            finally:
                browser.close()


def test_siteverify_rejects_missing_bad_and_spent_tokens_without_creating_cases():
    with isolated_app() as (base, database, _sink, http, _env):
        for payload, expected in (
            (application_payload(turnstile_token=""), 400),
            (application_payload(email="not-an-email"), 422),
            (application_payload(sharing_authority=False), 422),
        ):
            assert http.post(base + "/api/applications", json=payload).status_code == expected
        assert case_count(database) == 0
    # The official always-pass secret accepts arbitrary nonempty tokens.
    with isolated_app(FAIL_SECRET) as (base, database, _sink, http, _env):
        assert http.post(base + "/api/applications", json=application_payload(turnstile_token="not-a-cloudflare-token")).status_code == 400
        assert case_count(database) == 0
    # Cloudflare's documented test secret simulates an expired or reused token.
    with isolated_app(DUPLICATE_SECRET) as (base, database, _sink, http, _env):
        assert http.post(base + "/api/applications", json=application_payload()).status_code == 400
        assert case_count(database) == 0


def test_mail_transport_failure_keeps_notifications_for_retry():
    with isolated_app(expected_mail_failure=True) as (base, database, sink, http, env):
        sink.fail_mail = True
        response = http.post(base + "/api/applications", json=application_payload())
        assert response.status_code == 201
        reference = response.json()["case_reference"]
        assert http.get(base + response.json()["status_url"]).status_code == 200
        assert sink.messages == []
        for _ in range(100):
            with sqlite3.connect(database) as conn:
                rows = conn.execute("SELECT status,attempts FROM notification_outbox ORDER BY id").fetchall()
            if rows == [("pending", 1), ("pending", 1)]:
                break
            time.sleep(0.1)
        assert rows == [("pending", 1), ("pending", 1)]
        sink.fail_mail = False
        with sqlite3.connect(database) as conn:
            conn.execute("UPDATE notification_outbox SET next_attempt_at=NULL WHERE status='pending'")
        retry = subprocess.run([sys.executable, "scripts/send_notifications.py"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=20)
        assert retry.returncode == 0, retry.stderr
        assert len(sink.messages) == 2
        assert all(reference in message["subject"] for message in sink.messages)
        with sqlite3.connect(database) as conn:
            assert conn.execute("SELECT COUNT(*) FROM notification_outbox WHERE status='sent'").fetchone()[0] == 2
