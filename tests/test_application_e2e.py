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
def isolated_app(secret=PASS_SECRET, expected_mail_failure=False, extra_env=None):
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
        env.update(extra_env or {})
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
                deadline = time.time() + 5
                while len(sink.messages) < 2 and time.time() < deadline:
                    time.sleep(0.05)
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


def test_sourcing_mobile_photo_to_operator_report():
    """Real UI: multipart photo, private ownership, operator report, buyer delivery."""
    with isolated_app(extra_env={"ENABLE_SOURCING_PILOT":"true", "ENABLE_SOURCING_LIVE":"true", "TURNSTILE_SITE_KEY":"", "TURNSTILE_SECRET_KEY":""}) as (base, database, sink, http, env):
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True)
            buyer=browser.new_context(viewport={"width":390,"height":844},locale="ru-RU")
            operator=browser.new_context(viewport={"width":1280,"height":900},locale="ru-RU")
            try:
                page=buyer.new_page()
                for language in ("ru","en","de","fr","es","sr"):
                    page.goto(base+"/?lang="+language)
                    expect(page.locator('.combined-card')).to_have_count(2)
                    expect(page.locator('#homeBuy')).to_have_attribute('href','/buying?lang='+language)
                    expect(page.locator('#caseForm')).to_have_count(1)
                    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                    page.goto(base+"/sourcing/preview?lang="+language)
                    expect(page.locator("html")).to_have_attribute("lang",language)
                    expect(page.locator(".path-card")).to_have_count(2)
                    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.goto(base+"/sourcing/preview?lang=ru")
                page.locator('#previewDispute').click()
                expect(page.locator('#existingDisputeForm')).to_have_attribute('href','/?lang=ru#submit')
                page.goto(base+"/sourcing/preview/account?lang=ru")
                expect(page.locator('.dashboard-example')).to_contain_text('Только пример интерфейса')
                page.goto(base+"/?lang=ru")
                page.locator('#menuBtn').click()
                page.locator('#mobileLangSelect').select_option('en')
                expect(page.locator('#homeBuy')).to_have_attribute('href','/buying?lang=en')
                expect(page.locator('.combined-free').first).to_have_text('Help is free')
                page.locator('#menuBtn').click()
                page.locator('#mobileLangSelect').select_option('ru')
                page.locator('#homeDispute').click()
                expect(page.locator('#fullName')).to_be_visible()
                page.goto(base+"/?lang=ru")
                page.locator('#homeBuy').click()
                page.locator('#buyingApply').click()
                expect(page.locator('#service')).to_have_value('search')
                photo=BytesIO();Image.new("RGB",(16,16),"blue").save(photo,format="JPEG")
                page.locator("#photos").set_input_files({"name":"key.jpg","mimeType":"image/jpeg","buffer":photo.getvalue()})
                expect(page.locator("#preview img")).to_be_visible()
                page.locator("#unknown").check()
                page.locator("#quantity").fill("100 or 1000")
                page.locator("#destination").fill("Serbia")
                page.locator("#email").fill("buyer@example.com")
                page.locator('details').filter(has=page.locator('#platform')).locator('summary').click()
                page.locator('#platform').select_option('alibaba')
                page.locator('#purchase_purpose').select_option('resale')
                page.locator("#alternatives").check()
                page.locator("#goal").fill("Найти современный вариант ключа с экраном")
                page.locator('input[name="consent"]').check()
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.locator("#submitButton").click()
                page.wait_for_url(re.compile(r"/sourcing/requests/SRC-"))
                rid=page.locator("h1").inner_text();buyer_url=page.url
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                expect(page.locator("main .badge")).to_have_text("Заявка получена")
                assert http.get(buyer_url).status_code==404
                op=operator.new_page();op.goto(base+"/admin/login")
                op.locator('input[name="token"]').fill(env["ADMIN_TOKEN"])
                op.locator('button[type="submit"]').click()
                op.get_by_role('link',name='Заявки на подбор',exact=True).click()
                op.locator('a[href="/admin/sourcing/'+rid+'"]').click()
                expect(op.locator('h1')).to_have_text(rid)
                op.goto(base+"/admin/sourcing-statistics?lang=ru")
                expect(op.locator('h1')).to_have_text('Посещения и использование')
                expect(op.locator('tbody tr')).to_have_count(3)
                op.goto(base+"/admin/sourcing/"+rid)
                expect(op.locator('main')).to_contain_text('Для перепродажи')
                expect(op.locator('img[alt^="Фото товара"]')).to_be_visible()
                for state in ("reviewing","in_progress"):
                    op.locator('select[name="status"]').select_option(state)
                    op.get_by_role("button",name="Обновить статус").click()
                for name,value in {"summary":"Протестированный результат","findings":"Совпадение требует подтверждения","risks":"Завод не подтверждён","next_steps":"Запросить документы","sources":"https://example.com/source"}.items():
                    op.locator('textarea[name="'+name+'"]').fill(value)
                op.get_by_role("button",name="Сохранить черновик").click()
                page.reload();expect(page.locator(".report")).to_have_count(0)
                op.locator('input[name="reviewed"]').check()
                op.get_by_role("button",name="Выдать отчёт клиенту").click()
                page.reload();expect(page.locator(".report")).to_contain_text("Протестированный результат")
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                for language in ("ru","en","de","fr","es","sr"):
                    page.goto(base+"/sourcing/help/supplier?lang="+language)
                    expect(page.locator("html")).to_have_attribute("lang",language)
                    expect(page.locator('main article p')).to_have_count(4)
                    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                # Language switch also translates dynamic photo-validation copy.
                page.goto(base+"/sourcing?lang=en")
                expect(page.locator("html")).to_have_attribute("lang","en")
                expect(page.locator("#counter")).to_have_text("At least 50 more characters needed.")
                expect(page.locator(".free")).to_contain_text("Help is free")
                for code,title in {"de":"Lieferanten finden","fr":"Trouver un fournisseur","es":"Buscar un proveedor","sr":"Pronađi dobavljača"}.items():
                    page.goto(base+"/sourcing?lang="+code)
                    expect(page.locator("html")).to_have_attribute("lang",code)
                    expect(page.locator("#service")).to_contain_text(title)
                    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.goto(base+"/sourcing/feedback?lang=en&request_id="+rid)
                page.locator('select[name="kind"]').select_option("review")
                page.locator('select[name="rating"]').select_option("1")
                page.locator('textarea[name="message"]').fill("The test service needs clearer instructions.")
                page.locator('input[name="consent"]').check()
                page.locator('input[name="publish_consent"]').check()
                page.get_by_role("button",name="Send message",exact=True).click()
                expect(page.locator('main')).to_contain_text("Your message has been saved")
                page.goto(base+"/sourcing/reviews")
                expect(page.locator("blockquote")).to_have_count(0)
                op.goto(base+"/admin/sourcing/feedback?lang=en")
                expect(op.locator("main")).to_contain_text("The test service needs clearer instructions.")
                op.get_by_role("button",name="Publish review",exact=True).click()
                page.reload()
                expect(page.locator("blockquote")).to_contain_text("The test service needs clearer instructions.")
                expect(page.locator(".report")).to_contain_text("1 / 5")
                assert case_count(database)==0
                assert sink.messages==[]
            finally:
                buyer.close();operator.close();browser.close()


def test_unified_sourcing_navigation_and_example_at_phone_and_desktop_widths():
    """Buyer can reach the form, understand the sample and retain language on return."""
    from app.sourcing_i18n import COPY
    with isolated_app(extra_env={"ENABLE_SOURCING_PILOT":"true", "ENABLE_SOURCING_LIVE":"true", "TURNSTILE_SITE_KEY":"", "TURNSTILE_SECRET_KEY":""}) as (base, *_):
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True)
            try:
                for width in (390,1280):
                    context=browser.new_context(viewport={"width":width,"height":900})
                    page=context.new_page()
                    for language in COPY:
                        page.goto(base+"/?lang="+language)
                        expect(page.locator('.buyer-overview')).to_contain_text(COPY[language]['u_buy_process'])
                        page.locator('#homeBuy').click()
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                        page.locator('#buyingApply').click()
                        page.locator('.quick-actions a[href="#sourcingForm"]').click()
                        expect(page.locator('#product')).to_be_in_viewport()
                        page.locator('.quick-actions a[href="#sample-report"]').click()
                        expect(page.locator('#sample-report')).to_have_attribute('open','')
                        expect(page.locator('#sample-report')).to_contain_text(COPY[language]['sample_notice'])
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                        page.get_by_role('link',name=COPY[language]['access'],exact=True).click()
                        expect(page.locator('html')).to_have_attribute('lang',language)
                        expect(page.locator('input[name="access_code"]')).to_have_attribute('type','password')
                        page.locator('details summary').click()
                        expect(page.locator('main')).to_contain_text(COPY[language]['lost_code_help'])
                        page.goto(base+'/disputes?lang='+language)
                        expect(page.locator('#caseForm')).to_be_visible()
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                        if language=='ru' and os.environ.get('CTR_UX_SCREENSHOT_DIR'):
                            target=Path(os.environ['CTR_UX_SCREENSHOT_DIR']);target.mkdir(parents=True,exist_ok=True)
                            page.goto(base+'/sourcing?lang=ru')
                            page.screenshot(path=str(target/f'sourcing-{width}.png'),full_page=True)
                            page.goto(base+'/?lang=ru')
                            page.screenshot(path=str(target/f'home-{width}.png'),full_page=True)
                    context.close()
            finally:
                browser.close()


def test_language_switch_keeps_draft_photos_and_a_valid_submission():
    """Language switching must preserve the buyer's work without storing it or reloading."""
    with isolated_app(extra_env={"ENABLE_SOURCING_PILOT":"true","ENABLE_SOURCING_LIVE":"true","TURNSTILE_SITE_KEY":"","TURNSTILE_SECRET_KEY":""}) as (base,database,sink,http,env):
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True)
            page=browser.new_page(viewport={"width":390,"height":844})
            try:
                page.goto(base+'/sourcing?lang=ru')
                page.locator('#product').fill('Cordless drill')
                page.locator('#quantity').fill('100 or 1000')
                page.locator('#destination').fill('Serbia')
                page.locator('#email').fill('buyer@example.com')
                page.locator('#requirements').fill('A professional cordless drill with two batteries, spare parts and a written specification.')
                page.locator('#supplier').fill('https://example.com/supplier')
                photo=BytesIO();Image.new('RGB',(16,16),'blue').save(photo,format='JPEG')
                page.locator('#photos').set_input_files({'name':'drill.jpg','mimeType':'image/jpeg','buffer':photo.getvalue()})
                page.locator('#service').select_option('prepare')
                page.locator('#documents').fill('Please prepare the specification and supplier questions.')
                for language in ('de','en','fr','es','sr','ru','en'):
                    page.locator('.languages a[lang="'+language+'"]').click()
                    expect(page.locator('html')).to_have_attribute('lang',language)
                    expect(page.locator('#service')).to_have_value('prepare')
                    expect(page.locator('#product')).to_have_value('Cordless drill')
                    expect(page.locator('#email')).to_have_value('buyer@example.com')
                    expect(page.locator('#documents')).to_have_value('Please prepare the specification and supplier questions.')
                    assert page.locator('#photos').evaluate('el=>el.files.length')==1
                page.locator('#service').select_option('search')
                expect(page.locator('#preview img')).to_have_count(1)
                page.locator('input[name="consent"]').check()
                page.locator('#submitButton').click()
                page.wait_for_url(re.compile(r'/sourcing/requests/SRC-'))
                expect(page.locator('main')).to_contain_text('Cordless drill')
                assert sink.messages==[]
                # Old /#submit links must reveal the existing dispute form.
                page.goto(base+'/?lang=ru#submit')
                expect(page.locator('#legacyDispute')).to_have_attribute('open','')
                expect(page.locator('#fullName')).to_be_visible()
                page.goto(base+'/sourcing/feedback?lang=ru')
                page.locator('select[name="kind"]').select_option('bug')
                expect(page.locator('select[name="rating"]')).to_be_hidden()
                expect(page.locator('input[name="publish_consent"]')).to_be_disabled()
            finally:
                browser.close()


def test_admin_workspace_refresh_periods_and_navigation():
    with isolated_app(extra_env={"ENABLE_SOURCING_PILOT":"true","ENABLE_SOURCING_LIVE":"true","TURNSTILE_SITE_KEY":"","TURNSTILE_SECRET_KEY":""}) as (base,database,sink,http,env):
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True)
            page=browser.new_page(viewport={"width":1280,"height":900})
            try:
                page.goto(base+'/admin/login')
                page.locator('input[name="token"]').fill(env['ADMIN_TOKEN'])
                page.locator('button[type="submit"]').click()
                nav=page.locator('.admin-toolbar')
                nav.get_by_role('link',name='Посещаемость',exact=True).click()
                expect(page.locator('.admin-metric')).to_have_count(9)
                page.get_by_role('link',name='30 дней',exact=True).click()
                nav.get_by_role('link',name='Обновить',exact=True).click()
                expect(page.locator('.admin-periods a[aria-current="page"]')).to_have_text('30 дней')
                expect(page.locator('#statsMethod')).not_to_have_attribute('open','')
                for width in (1280,390):
                    page.set_viewport_size({"width":width,"height":900})
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    for href in ('/admin/sourcing','/admin/sourcing/feedback','/admin/feedback','/admin'):
                        nav.locator('nav a[href="'+href+'"]').click()
                        expect(page.locator('.admin-toolbar')).to_be_visible()
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    nav.get_by_role('link',name='Посещаемость',exact=True).click()
                    if os.environ.get('CTR_ADMIN_SCREENSHOT_DIR'):
                        target=Path(os.environ['CTR_ADMIN_SCREENSHOT_DIR']);target.mkdir(parents=True,exist_ok=True)
                        page.screenshot(path=str(target/('admin-statistics-'+str(width)+'.png')),full_page=True)
                nav.get_by_role('link',name='Рабочий кабинет',exact=True).click()
                page.locator('.queue-nav a[href="/admin?view=closed"]').click()
                nav.get_by_role('link',name='Обновить',exact=True).click()
                assert 'view=closed' in page.url
                nav.get_by_role('link',name='Открыть сайт',exact=True).click()
                expect(page.locator('.combined-card')).to_have_count(2)
                page.goto(base+'/admin')
                page.locator('.admin-toolbar').get_by_role('button',name='Выйти',exact=True).click()
                expect(page.locator('input[name="token"]')).to_be_visible()
                assert http.get(base+'/admin/sourcing-statistics').status_code==401
                assert sink.messages==[]
            finally:
                browser.close()


def test_operator_reads_cancels_and_permanently_deletes_one_sourcing_request():
    with isolated_app(extra_env={"ENABLE_SOURCING_PILOT":"true","ENABLE_SOURCING_LIVE":"true","TURNSTILE_SITE_KEY":"","TURNSTILE_SECRET_KEY":""}) as (base,database,sink,http,env):
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True)
            page=browser.new_page(viewport={"width":390,"height":844})
            try:
                page.goto(base+'/sourcing?lang=ru')
                page.locator('#product').fill('Isolated test drill')
                page.locator('#quantity').fill('100')
                page.locator('#destination').fill('Serbia')
                page.locator('#requirements').fill('A professional drill with spare batteries and documented safety specifications.')
                page.locator('#email').fill('buyer@example.com')
                page.locator('input[name="consent"]').check()
                page.locator('#submitButton').click()
                page.wait_for_url(re.compile(r'/sourcing/requests/SRC-'))
                rid=page.locator('h1').inner_text();private_url=page.url
                page.goto(base+'/admin/login')
                page.locator('input[name="token"]').fill(env['ADMIN_TOKEN'])
                page.locator('button[type="submit"]').click()
                expect(page.locator('.admin-directions')).to_contain_text('В работе: 1 · Всего: 1')
                page.locator('.admin-toolbar').get_by_role('link',name='Заявки на подбор',exact=True).click()
                page.get_by_role('link',name=rid,exact=True).click()
                page.get_by_role('link',name='Удалить навсегда',exact=True).click()
                expect(page.locator('main')).to_contain_text(rid)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.get_by_role('link',name='Отмена, вернуться к заявке',exact=True).click()
                expect(page.locator('h1')).to_have_text(rid)
                page.get_by_role('link',name='Удалить навсегда',exact=True).click()
                if os.environ.get('CTR_ADMIN_SCREENSHOT_DIR'):
                    target=Path(os.environ['CTR_ADMIN_SCREENSHOT_DIR']);target.mkdir(parents=True,exist_ok=True)
                    page.screenshot(path=str(target/'delete-confirmation-390.png'),full_page=True)
                page.locator('input[name="confirm"]').check()
                page.get_by_role('button',name='Удалить навсегда',exact=True).click()
                expect(page.get_by_role('status')).to_have_text('Заявка удалена из рабочей базы.')
                expect(page.get_by_role('link',name=rid,exact=True)).to_have_count(0)
                assert http.get(private_url).status_code==404
                with sqlite3.connect(database) as conn:
                    assert conn.execute('SELECT COUNT(*) FROM sourcing_requests WHERE id=?',(rid,)).fetchone()[0]==0
                page.locator('.admin-toolbar').get_by_role('link',name='Рабочий кабинет',exact=True).click()
                expect(page.locator('.admin-directions')).to_contain_text('В работе: 0 · Всего: 0')
                assert sink.messages==[]
            finally:
                browser.close()


def test_supplier_photos_all_services_and_private_draft_approval_in_browser():
    """Real UI with an isolated seeded draft; the provider adapter is tested separately."""
    with isolated_app(extra_env={'ENABLE_SOURCING_PILOT':'true','ENABLE_SOURCING_LIVE':'true',
                                'ENABLE_SOURCING_EMAIL':'true','TURNSTILE_SITE_KEY':'','TURNSTILE_SECRET_KEY':''}) as (base,database,sink,http,env):
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True)
            buyer=browser.new_context(viewport={'width':390,'height':844})
            operator=browser.new_context(viewport={'width':1280,'height':900})
            try:
                page=buyer.new_page();requests={}
                photo=BytesIO();Image.new('RGB',(20,20),'blue').save(photo,format='JPEG')
                for service in ('search','check','prepare'):
                    page.goto(base+'/sourcing?lang=ru&service='+service)
                    page.locator('#service').select_option(service)
                    expect(page.locator('#photos')).to_be_visible()
                    expect(page.locator('#photos')).to_be_enabled()
                    if service=='check':page.locator('#purchaseFields summary').click()
                    page.locator('#product').fill('Leather sofa')
                    page.locator('#quantity').fill('10')
                    page.locator('#destination').fill('Serbia')
                    page.locator('#email').fill('isolated-buyer@example.com')
                    page.locator('#supplier').fill('Example Furniture Company')
                    page.locator('#photos').set_input_files({'name':'sofa.jpg','mimeType':'image/jpeg','buffer':photo.getvalue()})
                    page.locator('#requirements').fill('Black corner sofa')
                    page.locator('input[name="consent"]').check()
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    page.locator('#submitButton').click()
                    page.wait_for_url(re.compile(r'/sourcing/requests/SRC-'))
                    requests[service]=page.url.split('/')[-1]
                    expect(page.get_by_text('Прикреплено фотографий: 1',exact=True)).to_be_visible()
                rid=requests['check']
                draft={'summary':'PRIVATE SEEDED DRAFT','findings':'The seller claims to operate a factory [1].',
                       'risks':'Legal identity and factory status need verification.',
                       'next_steps':'Request a business licence and sample terms.',
                       'sources':'https://example.com/company','suppliers':[]}
                with sqlite3.connect(database) as conn:
                    conn.execute("UPDATE sourcing_requests SET status='in_progress',draft_json=?,version=version+1 WHERE id=?",(json.dumps(draft),rid))
                    conn.execute("INSERT INTO sourcing_research(request_id,state,base_version,updated_at,evidence_json) VALUES (?,'ready',1,'2026-10-17T00:00:00+00:00',?)",(rid,json.dumps({'text':'Seller claims [1].','sources':['https://example.com/company'],'checked_at':'2026-10-17','model':'isolated fixture'})))
                page.goto(base+'/sourcing/requests/'+rid)
                expect(page.locator('main')).not_to_contain_text('PRIVATE SEEDED DRAFT')
                admin=operator.new_page();admin.goto(base+'/admin/login')
                admin.locator('input[name="token"]').fill(env['ADMIN_TOKEN']);admin.locator('button[type="submit"]').click()
                expect(admin.locator('.admin-inbox h2')).to_have_text('Новые обращения: 3')
                expect(admin.locator('.admin-inbox')).to_contain_text('Черновики на проверку: 1')
                for width in (390,1280):
                    admin.set_viewport_size({'width':width,'height':900})
                    assert admin.evaluate('document.documentElement.scrollWidth <= innerWidth')
                admin.locator('.admin-inbox a[href="/admin/sourcing/'+rid+'"]').first.click()
                report=admin.locator('form[action="/admin/sourcing/'+rid+'/report"]')
                expect(report.locator('textarea[name="summary"]')).to_have_value('PRIVATE SEEDED DRAFT')
                expect(admin.locator('#research')).to_contain_text('Клиент его не видит')
                expect(admin.locator('#research a[href="https://example.com/company"]')).to_have_count(2)
                report.locator('textarea[name="summary"]').fill('Reviewed supplier research')
                report.locator('input[name="reviewed"]').check()
                report.get_by_role('button',name='Выдать отчёт клиенту',exact=True).click()
                expect(admin.locator('.badge').first).to_have_text('Отчёт готов')
                page.reload()
                expect(page.locator('article.report')).to_contain_text('Reviewed supplier research')
                assert page.locator('article.report a[href="https://example.com/company"]').count()==1
                for _ in range(50):
                    if any('Готовность отчёта' in msg['subject'] for msg in sink.messages):break
                    time.sleep(.05)
                assert any('Готовность отчёта' in msg['subject'] for msg in sink.messages)
                # The actual queued email must work in a brand-new browser context.
                report_mail=next(msg for msg in sink.messages if 'Готовность отчёта' in msg['subject'])
                email_url=re.search(r'https?://[^\s]+/sourcing/email-access\?[^\s]+',report_mail['body']).group(0)
                fresh=browser.new_context(viewport={'width':390,'height':844})
                try:
                    reader=fresh.new_page();reader.goto(email_url)
                    expect(reader.locator('article.report')).to_contain_text('Reviewed supplier research')
                    assert 'token=' not in reader.url
                    assert reader.locator('form[action$="/delete"]').count()==0
                    assert reader.locator('.access-code').count()==0
                    reader.goto(base+'/sourcing/access?request_id='+rid)
                    # Existing read-only ownership goes straight to the report.
                    expect(reader.locator('article.report')).to_be_visible()
                finally:fresh.close()
                # Old generic emails can recover access using only the reference.
                recovery=browser.new_context(viewport={'width':390,'height':844})
                try:
                    recovery_page=recovery.new_page();recovery_page.goto(base+'/sourcing/access?request_id='+rid)
                    expect(recovery_page.locator('input[name="request_id"]')).to_have_value(rid)
                    recovery_page.get_by_role('button',name='Отправить ссылку на мою почту',exact=True).click()
                    expect(recovery_page.locator('[role="status"]')).to_contain_text('Если номер верен')
                    for _ in range(50):
                        recovery_mail=next((msg for msg in sink.messages if 'Ссылка для просмотра заявки' in msg['subject']),None)
                        if recovery_mail:break
                        time.sleep(.05)
                    assert recovery_mail
                    recovery_url=re.search(r'https?://[^\s]+/sourcing/email-access\?[^\s]+',recovery_mail['body']).group(0)
                    recovery_page.goto(recovery_url)
                    expect(recovery_page.locator('article.report')).to_contain_text('Reviewed supplier research')
                    assert recovery_page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                finally:recovery.close()
                expect(page.locator('#mailStatus')).to_contain_text('Передано почтовому сервису')
                admin.goto(base+'/admin')
                expect(admin.locator('.admin-inbox h2')).to_have_text('Новые обращения: 2')
                assert rid not in admin.locator('.admin-inbox').inner_text()
                if os.environ.get('CTR_ADMIN_SCREENSHOT_DIR'):
                    target=Path(os.environ['CTR_ADMIN_SCREENSHOT_DIR']);target.mkdir(parents=True,exist_ok=True)
                    admin.screenshot(path=str(target/'admin-unified-inbox.png'),full_page=True)
            finally:
                buyer.close();operator.close();browser.close()


def test_first_visit_minimal_company_check_and_text_assistant():
    from app.sourcing_i18n import COPY
    with isolated_app(extra_env={"ENABLE_SOURCING_PILOT":"true","ENABLE_SOURCING_LIVE":"true","TURNSTILE_SITE_KEY":"","TURNSTILE_SECRET_KEY":"","ENABLE_AI_ASSISTANT":"true","OPENAI_BILLING_READY":"true","OPENAI_API_KEY":"isolated-ui-only-dummy-key","OPENAI_ASSISTANT_MODEL":"gpt-4.1-mini"}) as (base,database,sink,*_):
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            try:
                for width in (390,1280):
                    context=browser.new_context(viewport={"width":width,"height":900})
                    page=context.new_page()
                    for lang in COPY:
                        page.goto(base+'/?lang='+lang)
                        page.locator('.combined-card a[href*="service=check"]').click()
                        expect(page.locator('#service')).to_have_value('check')
                        expect(page.locator('#serviceHeadline')).to_have_text(COPY[lang]['check_headline'])
                        expect(page.locator('#purchaseFields')).not_to_have_attribute('open','')
                        expect(page.locator('#requirements')).not_to_have_attribute('required','')
                        page.locator('#supplier').fill('Example Furniture Co.')
                        page.locator('#email').fill('audit@example.com')
                        page.locator('[name="consent"]').check()
                        assert page.locator('#sourcingForm').evaluate('(f)=>f.checkValidity()')
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                        if lang=='ru':
                            page.locator('#submitButton').click()
                            expect(page).to_have_url(re.compile('/sourcing/requests/SRC-'))
                            expect(page.locator('main')).to_contain_text('Example Furniture Co.')
                        page.goto(base+'/?lang='+lang)
                        page.locator('#aiChatLauncher').click()
                        expect(page.locator('#aiChatPanel')).to_be_visible()
                        expect(page.locator('#voiceCaptureModal')).to_be_hidden()
                        expect(page.locator('#aiChatInput')).to_be_focused()
                        page.locator('#aiChatInput').fill('How can I check a supplier?')
                        expect(page.locator('#aiChatSend')).to_be_enabled()
                        page.locator('#aiChatClose').click()
                        if lang=='ru':
                            page.goto(base+'/disputes?lang=ru#submit')
                            page.locator('#caseForm').scroll_into_view_if_needed()
                            expect(page.locator('#aiChatLauncher')).to_be_visible()
                            page.locator('#aiChatLauncher').click()
                            expect(page.locator('#voiceCaptureModal')).to_be_hidden()
                            page.locator('#aiChatClose').click()
                    context.close()
                assert any('Example Furniture' not in str(m.get('subject','')) for m in sink.messages)
            finally:
                browser.close()
