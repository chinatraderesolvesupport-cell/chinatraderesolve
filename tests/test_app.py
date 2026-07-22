from pathlib import Path
import os
import tempfile

_tmp = tempfile.TemporaryDirectory()
os.environ["DATABASE_PATH"] = str(Path(_tmp.name) / "test.db")
os.environ["ADMIN_TOKEN"] = "test-admin-token-abcdefghijklmnopqrstuvwxyz"
os.environ["APP_SECRET"] = "test-app-secret-abcdefghijklmnopqrstuvwxyz-0123456789"
os.environ["ENABLE_AI_TRIAGE"] = "false"
os.environ["FREE_ACCESS_MODE"] = "true"
os.environ["RENDER"] = "true"
os.environ["ENABLE_VOLUNTARY_SUPPORT"] = "true"
os.environ["SUPPORT_URL"] = "https://example.com/support"
os.environ["BTC_ADDRESS"] = "1BafLn5NLdKwyv8rvuPJVZUKwQnHyuMej9"
os.environ["ETH_ADDRESS"] = "0x69ace684f28b0a66157ab62ad06e93761a713c6b"
os.environ["USDT_TRC20_ADDRESS"] = "TV3CgZaUqRqQSAYnzyGaMH3M27AwZwGJNp"
os.environ["SOL_ADDRESS"] = "Er2tJEVwokTtCBroUi9eAbCRnYCxwVaBqbPDiNaQtMYg"

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def valid_payload(**overrides):
    data = {
        "full_name": "Test Buyer",
        "email": "buyer@example.com",
        "country": "Serbia",
        "preferred_language": "English",
        "purchasing_channel": "Alibaba",
        "amount_in_dispute": "EUR 4,000",
        "main_problem": "Wrong material or specification",
        "supplier_name": "Supplier Ltd",
        "order_number": "ORD-123",
        "order_value": "EUR 12,000",
        "requested_result": "Partial refund",
        "description": "The written order specifies leather. The supplier messages confirm leather, but delivered product photographs indicate a different material. We have the invoice, order, chat and photographs.",
        "company_website": "",
        "free_access_terms": True,
        "sharing_authority": True,
        "ai_consent": True,
        "no_guarantee": True,
    }
    data.update(overrides)
    return data


def test_health_and_home_free_access():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["free_access_mode"] is True
    assert health.json()["support_enabled"] is True
    home = client.get("/")
    assert home.status_code == 200
    assert "Заявки рассматриваются бесплатно" in home.text
    assert "Добровольная поддержка" in home.text
    assert "chinatraderesolve.support@gmail.com" in home.text
    assert health.json()["email_delivery_configured"] is False
    assert health.json()["secure_configuration"] is True


def test_submit_candidate_and_status_page():
    response = client.post("/api/applications", json=valid_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["case_reference"].startswith("CTR-")
    assert "PILOT" not in body["case_reference"]
    assert body["status"] in {"pilot_candidate", "needs_information", "human_review"}
    status = client.get(body["status_url"])
    assert status.status_code == 200
    assert body["case_reference"] in status.text
    assert "No service fee" in status.text


def test_urgent_case_escalates():
    payload = valid_payload(description="A court hearing is next week and a limitation deadline expires tomorrow. We need urgent representation and have order messages and an invoice.")
    response = client.post("/api/applications", json=payload)
    assert response.status_code == 201
    assert response.json()["status"] == "human_review"


def test_missing_free_access_consent_rejected():
    response = client.post("/api/applications", json=valid_payload(free_access_terms=False))
    assert response.status_code == 422


def test_ai_consent_is_optional():
    response = client.post("/api/applications", json=valid_payload(ai_consent=False, email="no-ai@example.com"))
    assert response.status_code == 201


def test_support_page_is_optional_and_non_priority():
    page = client.get("/support")
    assert page.status_code == 200
    assert "не является оплатой услуги" in page.text
    assert "https://example.com/support" in page.text


def test_admin_auth_queue_close_and_feedback():
    created = client.post("/api/applications", json=valid_payload(email="feedback@example.com")).json()
    login = client.post("/admin/login", data={"token": "test-admin-token-abcdefghijklmnopqrstuvwxyz"}, follow_redirects=False)
    assert login.status_code == 303
    dashboard = client.get("/admin")
    assert dashboard.status_code == 200
    assert "Очередь дел, требующих внимания" in dashboard.text

    # Find the case id and the per-session administrator form token.
    import re
    match = re.search(r'href="/admin/case/(\d+)">' + re.escape(created["case_reference"]), dashboard.text)
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', dashboard.text)
    assert match and csrf_match
    case_id = int(match.group(1))
    close = client.post(
        f"/admin/case/{case_id}/status",
        data={"status": "closed", "note": "Review completed", "csrf_token": csrf_match.group(1)},
        follow_redirects=False,
    )
    assert close.status_code == 303

    status_page = client.get(created["status_url"])
    assert "Help us improve the free service" in status_page.text
    feedback_url = created["status_url"] + "/feedback"
    feedback = client.post(
        feedback_url,
        data={
            "rating": "5",
            "feedback_text": "The chronology and next-step checklist made the dispute much easier to understand.",
            "display_name": "Verified user",
            "testimonial_consent": "true",
            "company_website": "",
        },
        follow_redirects=False,
    )
    assert feedback.status_code == 303
    saved = client.get(feedback.headers["location"])
    assert "Thank you. Your feedback has been recorded." in saved.text
    admin_case = client.get(f"/admin/case/{case_id}")
    assert "The chronology and next-step checklist" in admin_case.text
    assert "Согласие на публикацию:</b> да" in admin_case.text


def test_ai_triage_structured_response_mock(monkeypatch):
    import asyncio
    import json
    from types import SimpleNamespace
    import app.ai_triage as module
    from app.schemas import TriageResult

    expected = {
        "decision": "needs_information",
        "risk_level": "medium",
        "priority": 55,
        "confidence": 0.7,
        "position_strength": "unclear",
        "in_scope": True,
        "hard_stop": False,
        "reasons": ["More detail is required."],
        "missing_information": ["Timeline"],
        "risk_flags": [],
        "recommended_action": "Request a chronology.",
        "public_message": "More information is needed.",
        "source": "ai",
    }
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None
        def json(self):
            return {"output": [{"content": [{"type": "output_text", "text": json.dumps(expected)}]}]}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return None
        async def post(self, url, headers, json):
            captured["url"] = url
            captured["body"] = json
            return FakeResponse()

    monkeypatch.setattr(module, "settings", SimpleNamespace(
        enable_ai_triage=True,
        openai_api_key="test-key",
        openai_model="test-model",
        openai_timeout_seconds=5,
    ))
    monkeypatch.setattr(module.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(module.ai_triage(valid_payload_model()))
    assert isinstance(result, TriageResult)
    assert result.decision == "needs_information"
    assert captured["url"].endswith("/v1/responses")
    assert captured["body"]["store"] is False
    assert captured["body"]["text"]["format"]["strict"] is True


def valid_payload_model():
    from app.schemas import ApplicationCreate
    return ApplicationCreate.model_validate(valid_payload())


def test_russian_localization_and_security_headers():
    home = client.get("/")
    assert home.status_code == 200
    assert "Независимый сервис ChinaTradeResolve" in home.text
    assert "ChinaTradeResolve Case Review Team" not in home.text
    assert "Электронная почта" in home.text
    assert home.headers["x-content-type-options"] == "nosniff"
    assert home.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in home.headers["content-security-policy"]

    created = client.post(
        "/api/applications",
        json=valid_payload(
            preferred_language="Russian",
            email="russian@example.com",
            description=(
                "В письменном заказе указана натуральная кожа. Поставщик подтвердил это в переписке, "
                "но фотографии полученного товара показывают другой материал. У нас есть инвойс, заказ, "
                "переписка и фотографии, и мы просим частичный возврат средств."
            ),
        ),
    )
    assert created.status_code == 201
    status = client.get(created.json()["status_url"])
    assert status.status_code == 200
    assert "Статус дела" in status.text
    assert "No service fee" not in status.text
    assert status.headers["cache-control"] == "no-store"


def test_admin_login_rate_limit():
    headers = {"x-forwarded-for": "203.0.113.77"}
    for _ in range(5):
        response = client.post("/admin/login", data={"token": "wrong-token"}, headers=headers)
        assert response.status_code == 401
    blocked = client.post("/admin/login", data={"token": "wrong-token"}, headers=headers)
    assert blocked.status_code == 429
    assert "Слишком много попыток" in blocked.text


def test_retention_removes_related_confidential_data():
    from app.db import connect, execute, save_feedback, soft_delete_expired, transaction, update_status

    created = client.post(
        "/api/applications",
        json=valid_payload(email="retention@example.com", supplier_name="Confidential Supplier"),
    ).json()

    # Resolve the internal id and close the case through an allowed transition.
    with transaction() as conn:
        row = execute(conn, "SELECT id,status FROM cases WHERE case_reference=?", (created["case_reference"],)).fetchone()
        case_id = int(row["id"])
    current = row["status"]
    if current == "submitted":
        update_status(case_id, "needs_information", "test")
        current = "needs_information"
    update_status(case_id, "closed", "retention test")
    save_feedback(case_id, {
        "rating": 5,
        "feedback_text": "Confidential feedback that must be removed.",
        "display_name": "Private name",
        "testimonial_consent": True,
    })
    with transaction() as conn:
        execute(conn, "UPDATE cases SET created_at='2000-01-01T00:00:00+00:00', updated_at='2000-01-01T00:00:00+00:00' WHERE id=?", (case_id,))

    assert soft_delete_expired(90) >= 1
    with transaction() as conn:
        case = execute(conn, "SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        assert case["deleted_at"] is not None
        assert case["supplier_name"] == ""
        assert case["order_number"] == ""
        assert case["triage_json"] == '{"deleted":true}'
        assert execute(conn, "SELECT COUNT(*) AS n FROM feedback WHERE case_id=?", (case_id,)).fetchone()["n"] == 0
        assert execute(conn, "SELECT COUNT(*) AS n FROM notification_outbox WHERE case_id=?", (case_id,)).fetchone()["n"] == 0
        assert execute(conn, "SELECT COUNT(*) AS n FROM audit_log WHERE case_id=?", (case_id,)).fetchone()["n"] == 0


def test_application_form_does_not_render_object_object_errors():
    response = client.get("/")
    assert response.status_code == 200
    assert 'Array.isArray(result.detail)' in response.text
    assert 'minlength="2" name="full_name"' in response.text
    assert "result.detail||'Submission failed.'" not in response.text


def test_multilingual_frontend_assets_are_complete():
    import json

    home = client.get("/")
    assert home.status_code == 200
    for code in ("en", "fr", "de", "es", "ru", "sr"):
        assert f'value="{code}"' in home.text
    assert "/static/translations-v2.js" in home.text
    assert "ctr_lang_v20" in home.text
    assert "navigator.languages" in home.text

    translations = client.get("/static/translations-v2.json")
    assert translations.status_code == 200
    data = json.loads(translations.text)
    assert set(data) == {"en", "fr", "de", "es", "ru", "sr"}
    english_keys = set(data["en"])
    assert len(english_keys) >= 210
    for language, copy in data.items():
        assert set(copy) == english_keys, language
        assert "[object Object]" not in json.dumps(copy, ensure_ascii=False)
        assert all(isinstance(value, str) and value.strip() for value in copy.values())

    for path in (
        "/static/privacy.html",
        "/static/terms.html",
        "/static/refund.html",
        "/static/ai-notice.html",
        "/static/disclaimer.html",
        "/static/sample_case_assessment.html",
    ):
        page = client.get(path)
        assert page.status_code == 200
        assert "/static/legal-i18n-v2.js" in page.text
        assert 'value="fr"' in page.text
        assert 'value="de"' in page.text
        assert 'value="es"' in page.text


def test_french_german_and_spanish_status_localization():
    cases = [
        (
            "French",
            "french@example.com",
            "La commande écrite précise le cuir. Le fournisseur l’a confirmé dans les messages, mais les photos montrent un autre matériau. Nous avons la facture, la commande, les messages et les photos.",
            '<html lang="fr">',
            "Statut du dossier",
            "Aucun paiement n’est requis",
        ),
        (
            "German",
            "german@example.com",
            "Die schriftliche Bestellung nennt Leder. Der Lieferant bestätigte dies in Nachrichten, aber die Fotos zeigen ein anderes Material. Wir haben Rechnung, Bestellung, Nachrichten und Fotos.",
            '<html lang="de">',
            "Fallstatus",
            "Es ist keine Zahlung erforderlich",
        ),
        (
            "Spanish",
            "spanish@example.com",
            "El pedido escrito especifica cuero. El proveedor lo confirmó en mensajes, pero las fotografías muestran otro material. Tenemos factura, pedido, mensajes y fotografías.",
            '<html lang="es">',
            "Estado del caso",
            "No se requiere pago",
        ),
    ]
    for index, (language, email, description, html_lang, title, notice) in enumerate(cases, start=10):
        created = client.post(
            "/api/applications",
            headers={"x-forwarded-for": f"198.51.100.{index}"},
            json=valid_payload(
                preferred_language=language,
                email=email,
                description=description,
            ),
        )
        assert created.status_code == 201
        body = created.json()
        status = client.get(body["status_url"])
        assert status.status_code == 200
        assert html_lang in status.text
        assert title in status.text
        assert notice in status.text
        assert "No service fee" not in status.text
        assert body["public_message"] in status.text


def test_crypto_support_wallets_and_network_warnings():
    page = client.get("/support")
    assert page.status_code == 200
    expected = {
        "1BafLn5NLdKwyv8rvuPJVZUKwQnHyuMej9": "Bitcoin",
        "0x69ace684f28b0a66157ab62ad06e93761a713c6b": "Ethereum Mainnet",
        "TV3CgZaUqRqQSAYnzyGaMH3M27AwZwGJNp": "TRON (TRC20)",
        "Er2tJEVwokTtCBroUi9eAbCRnYCxwVaBqbPDiNaQtMYg": "Solana",
    }
    for address, network in expected.items():
        assert address in page.text
        assert network in page.text
    assert "Send BTC only through the Bitcoin network." in page.text
    assert "Отправляйте только ETH через Ethereum Mainnet." in page.text
    assert "Send USDT only through TRON (TRC20)." in page.text
    assert "Отправляйте только SOL через сеть Solana." in page.text
    assert page.text.count('data-copy=') == 4
    assert "seed phrase" in page.text
    assert "seed-фразу" in page.text


def test_crypto_qr_assets_are_served_as_png():
    for asset in ("btc", "eth", "usdt-trc20", "sol"):
        response = client.get(f"/support/qr/{asset}.png")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(response.content) > 500


def test_crypto_wallet_configuration_is_valid_and_support_is_enabled():
    from app.main import crypto_wallets, support_is_available

    wallets = crypto_wallets()
    assert [item["asset"] for item in wallets] == ["BTC", "ETH", "USDT", "SOL"]
    assert [item["network"] for item in wallets] == ["Bitcoin", "Ethereum Mainnet", "TRON (TRC20)", "Solana"]
    assert support_is_available() is True


def test_solana_address_validation_is_network_specific():
    from app.main import _valid_solana

    assert _valid_solana("Er2tJEVwokTtCBroUi9eAbCRnYCxwVaBqbPDiNaQtMYg") is True
    assert _valid_solana("Er2tJEVwokTtCBroUi9eAbCRnYCxwVaBqbPDiNaQtMY0") is False
    assert _valid_solana("short") is False


def test_ai_assistant_frontend_and_disabled_endpoint():
    import json

    home = client.get("/")
    assert home.status_code == 200
    assert 'id="aiChatRoot"' in home.text
    assert 'id="aiChatPanel"' in home.text
    assert "fetch('/api/assistant'" in home.text
    assert "ctr:language-changed" in home.text
    assert "resetAiChatForLanguageChange" in home.text
    assert "aiChatAbortController.abort()" in home.text
    assert "maxlength=\"1500\"" in home.text
    # The widget remains hidden until the server-side API key/model are configured.
    assert 'data-enabled="false" hidden' in home.text

    translations = json.loads(client.get("/static/translations-v2.json").text)
    for language in ("en", "fr", "de", "es", "ru", "sr"):
        assert translations[language]["ai_chat_button"].strip()
        assert translations[language]["ai_chat_notice"].strip()
        assert translations[language]["ai_chat_welcome"].strip()

    unavailable = client.post(
        "/api/assistant",
        json={
            "language": "ru",
            "messages": [{"role": "user", "content": "Как подготовить доказательства?"}],
        },
    )
    assert unavailable.status_code == 503
    assert "временно недоступен" in unavailable.json()["detail"]


def test_ai_assistant_request_validation():
    response = client.post(
        "/api/assistant",
        json={
            "language": "en",
            "messages": [{"role": "assistant", "content": "This cannot be the final message."}],
        },
    )
    assert response.status_code == 422

    too_long = client.post(
        "/api/assistant",
        json={
            "language": "en",
            "messages": [{"role": "user", "content": "x" * 2001}],
        },
    )
    assert too_long.status_code == 422


def test_ai_assistant_output_removes_unicode_noncharacters():
    from app.ai_assistant import _clean_output_text

    assert _clean_output_text("Bonjour.\U0008ffff") == "Bonjour."
    assert _clean_output_text("Line one\n\n\nLine two") == "Line one\n\nLine two"
    assert _clean_output_text("Normal français, Deutsch, русский, srpski.") == "Normal français, Deutsch, русский, srpski."


def test_ai_assistant_responses_api_mock(monkeypatch):
    import asyncio
    from types import SimpleNamespace

    import app.ai_assistant as module
    from app.schemas import AssistantChatRequest

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "output": [
                    {
                        "content": [
                            {
                                "type": "output_text",
                                "text": "Prepare the written order, invoice, supplier messages and a dated chronology.",
                            }
                        ]
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = json
            return FakeResponse()

    monkeypatch.setattr(
        module,
        "settings",
        SimpleNamespace(
            enable_ai_assistant=True,
            openai_api_key="test-key",
            openai_assistant_model="test-assistant-model",
            openai_moderation_model=None,
            ai_assistant_history_messages=8,
            ai_assistant_max_output_tokens=500,
            openai_timeout_seconds=7,
        ),
    )
    monkeypatch.setattr(module.httpx, "AsyncClient", FakeClient)
    payload = AssistantChatRequest.model_validate(
        {
            "language": "en",
            "messages": [
                {"role": "user", "content": "What documents should I prepare?"}
            ],
        }
    )
    reply = asyncio.run(module.assistant_reply(payload))
    assert "written order" in reply
    assert captured["url"].endswith("/v1/responses")
    assert captured["body"]["store"] is False
    assert captured["body"]["model"] == "test-assistant-model"
    assert captured["body"]["max_output_tokens"] == 500
    assert captured["body"]["input"][0]["role"] == "developer"
    assert "not legal advice" in captured["body"]["input"][0]["content"][0]["text"]
    assert captured["headers"]["Authorization"] == "Bearer test-key"


def test_ai_assistant_moderation_blocks_narrow_category(monkeypatch):
    import asyncio
    from types import SimpleNamespace

    import app.ai_assistant as module
    from app.schemas import AssistantChatRequest

    calls = []

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers, json):
            calls.append(url)
            if url.endswith("/v1/moderations"):
                return FakeResponse(
                    {
                        "results": [
                            {
                                "flagged": True,
                                "categories": {"sexual/minors": True},
                            }
                        ]
                    }
                )
            raise AssertionError("Responses API must not be called after a narrow moderation block")

    monkeypatch.setattr(
        module,
        "settings",
        SimpleNamespace(
            enable_ai_assistant=True,
            openai_api_key="test-key",
            openai_assistant_model="test-assistant-model",
            openai_moderation_model="omni-moderation-latest",
            ai_assistant_history_messages=8,
            ai_assistant_max_output_tokens=500,
            openai_timeout_seconds=7,
        ),
    )
    monkeypatch.setattr(module.httpx, "AsyncClient", FakeClient)
    payload = AssistantChatRequest.model_validate(
        {
            "language": "ru",
            "messages": [{"role": "user", "content": "unsafe test input"}],
        }
    )
    reply = asyncio.run(module.assistant_reply(payload))
    assert "не могу помочь" in reply
    assert calls == ["https://api.openai.com/v1/moderations"]


def test_v33_home_structure_and_translation_completeness():
    import json
    import re
    from pathlib import Path

    home = client.get("/")
    assert home.status_code == 200
    assert "Разложим спор по фактам" in home.text
    assert "Проверка до оплаты" not in home.text
    assert home.text.count('id="services"') == 1
    assert home.text.count('id="about"') == 1
    assert 'id="contact"' not in home.text
    assert "descriptionCount" in home.text
    assert 'maxlength="8000"' in home.text

    base = Path(__file__).resolve().parents[1]
    translations = json.loads((base / "app/static/translations-v2.json").read_text(encoding="utf-8"))
    template = (base / "app/templates/index.html").read_text(encoding="utf-8")
    required = set(re.findall(r'data-i18n="([^"]+)"', template))
    required |= set(re.findall(r'data-i18n-placeholder="([^"]+)"', template))
    required |= set(re.findall(r'data-i18n-aria-label="([^"]+)"', template))
    for language, copy in translations.items():
        missing = sorted(required - set(copy))
        assert not missing, f"{language} is missing translation keys: {missing}"


def _make_png_bytes() -> bytes:
    from io import BytesIO
    from PIL import Image
    output = BytesIO()
    image = Image.new("RGB", (32, 24), (245, 245, 245))
    image.save(output, format="PNG", pnginfo=None)
    return output.getvalue()


def test_private_document_upload_download_delete_and_admin_visibility():
    created = client.post(
        "/api/applications",
        json=valid_payload(email="documents@example.com", preferred_language="Russian"),
        headers={"x-forwarded-for": "198.51.100.201"},
    ).json()
    status_url = created["status_url"]
    png = _make_png_bytes()
    upload = client.post(
        status_url + "/documents",
        files=[("files", ("supplier-chat.png", png, "image/png"))],
        data={"document_consent": "true"},
        follow_redirects=False,
    )
    assert upload.status_code == 303
    page = client.get(upload.headers["location"])
    assert "supplier-chat.png" in page.text
    assert "Документы успешно загружены" in page.text

    import re
    match = re.search(r'/documents/(\d+)" target="_blank"', page.text)
    assert match
    document_id = int(match.group(1))
    download = client.get(status_url + f"/documents/{document_id}")
    assert download.status_code == 200
    assert download.headers["cache-control"] == "no-store"
    assert download.headers["content-type"].startswith("image/png")
    assert download.content.startswith(b"\x89PNG")

    login = client.post("/admin/login", data={"token": "test-admin-token-abcdefghijklmnopqrstuvwxyz"}, follow_redirects=False)
    assert login.status_code == 303
    dashboard = client.get("/admin")
    case_match = re.search(r'href="/admin/case/(\d+)">' + re.escape(created["case_reference"]), dashboard.text)
    assert case_match
    case_id = int(case_match.group(1))
    admin_page = client.get(f"/admin/case/{case_id}")
    assert "supplier-chat.png" in admin_page.text
    admin_download = client.get(f"/admin/case/{case_id}/documents/{document_id}")
    assert admin_download.status_code == 200

    deleted = client.post(status_url + f"/documents/{document_id}/delete", follow_redirects=False)
    assert deleted.status_code == 303
    assert "supplier-chat.png" not in client.get(status_url).text


def test_document_upload_rejects_unsafe_and_oversized_files():
    created = client.post(
        "/api/applications",
        json=valid_payload(email="unsafe-docs@example.com"),
        headers={"x-forwarded-for": "198.51.100.202"},
    ).json()
    status_url = created["status_url"]
    unsafe = client.post(
        status_url + "/documents",
        files=[("files", ("payload.html", b"<script>alert(1)</script>", "text/html"))],
        data={"document_consent": "true"},
    )
    assert unsafe.status_code == 400
    assert "Only PDF, JPG, PNG and WebP" in unsafe.text

    oversized = client.post(
        status_url + "/documents",
        files=[("files", ("large.png", b"\x89PNG\r\n\x1a\n" + b"x" * (8 * 1024 * 1024), "image/png"))],
        data={"document_consent": "true"},
    )
    assert oversized.status_code == 400
    assert "8 MB" in oversized.text


def test_document_analysis_mock_and_public_report(monkeypatch):
    import app.main as main_module

    created = client.post(
        "/api/applications",
        json=valid_payload(email="analysis@example.com", preferred_language="English"),
        headers={"x-forwarded-for": "198.51.100.203"},
    ).json()
    status_url = created["status_url"]
    upload = client.post(
        status_url + "/documents",
        files=[("files", ("invoice.png", _make_png_bytes(), "image/png"))],
        data={"document_consent": "true"},
        follow_redirects=False,
    )
    assert upload.status_code == 303

    expected = {
        "readiness_score": 72,
        "summary": "The invoice is readable, but payment and delivery evidence are still missing.",
        "document_inventory": [{
            "filename": "invoice.png", "document_type": "Invoice", "language": "English",
            "date_or_period": "2026-01-10", "key_content": "Order value EUR 12,000", "readability": "clear",
        }],
        "timeline": [{
            "date": "2026-01-10", "event": "Invoice issued", "source_files": ["invoice.png"], "confidence": "high",
        }],
        "key_evidence": ["Invoice identifies the order value."],
        "contradictions": [],
        "missing_evidence": ["Payment proof", "Delivery photographs"],
        "risk_flags": ["Only one document supplied"],
        "recommended_next_steps": ["Upload payment proof."],
        "human_review_note": "Important conclusions require human verification.",
        "model": "test-model",
    }

    async def fake_analysis(case, documents):
        assert case["case_reference"] == created["case_reference"]
        assert documents[0]["original_name"] == "invoice.png"
        return expected

    monkeypatch.setattr(main_module, "document_analysis_is_enabled", lambda: True)
    monkeypatch.setattr(main_module, "analyse_case_documents", fake_analysis)
    analyse = client.post(status_url + "/documents/analyse", follow_redirects=False)
    assert analyse.status_code == 303
    report = client.get(analyse.headers["location"])
    assert "Preliminary document analysis" in report.text
    assert "72%" in report.text
    assert "Payment proof" in report.text
    assert "Invoice issued" in report.text


def test_document_analysis_request_uses_multimodal_structured_output(monkeypatch):
    import asyncio
    import base64
    import json
    from types import SimpleNamespace
    import app.document_analysis as module

    expected = {
        "readiness_score": 60,
        "summary": "Summary",
        "document_inventory": [{"filename": "chat.png", "document_type": "Chat", "language": "English", "date_or_period": "Date not visible", "key_content": "Supplier statement", "readability": "clear"}],
        "timeline": [{"date": "Date not visible", "event": "Supplier made a statement", "source_files": ["chat.png"], "confidence": "medium"}],
        "key_evidence": ["Supplier statement"], "contradictions": [], "missing_evidence": ["Invoice"],
        "risk_flags": [], "recommended_next_steps": ["Add invoice"],
        "human_review_note": "Human verification required.",
    }
    captured = {}

    class FakeResponse:
        status_code = 200
        headers = {}
        def raise_for_status(self):
            return None
        def json(self):
            return {"output": [{"content": [{"type": "output_text", "text": json.dumps(expected)}]}]}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return None
        async def post(self, url, headers, json):
            captured["url"] = url
            captured["body"] = json
            return FakeResponse()

    monkeypatch.setattr(module, "settings", SimpleNamespace(
        enable_document_analysis=True,
        openai_api_key="test-key",
        openai_document_model="test-model",
        document_analysis_timeout_seconds=30,
        document_analysis_max_output_tokens=1200,
    ))
    monkeypatch.setattr(module.httpx, "AsyncClient", FakeClient)
    case = valid_payload()
    case["case_reference"] = "CTR-TEST"
    documents = [{
        "original_name": "chat.png", "content_type": "image/png", "content_blob": _make_png_bytes(),
    }]
    result = asyncio.run(module.analyse_case_documents(case, documents))
    assert result["readiness_score"] == 60
    assert captured["url"].endswith("/v1/responses")
    assert captured["body"]["store"] is False
    assert captured["body"]["text"]["format"]["strict"] is True
    image_part = captured["body"]["input"][1]["content"][1]
    assert image_part["type"] == "input_image"
    assert image_part["image_url"].startswith("data:image/png;base64,")
    base64.b64decode(image_part["image_url"].split(",", 1)[1])
    assert captured["body"]["max_output_tokens"] >= 2400


def test_desktop_autofill_cannot_silently_block_submission():
    home = client.get("/")
    assert home.status_code == 200
    # Browser/password-manager autofill used to populate the hidden honeypot on desktop.
    # The frontend then returned silently before making the request.
    assert 'name="company_website"' not in home.text
    assert "document.querySelector('.honeypot').value" not in home.text

    payload = valid_payload(
        email="desktop-autofill@example.com",
        company_website="https://autofilled.example",
    )
    response = client.post(
        "/api/applications",
        json=payload,
        headers={"x-forwarded-for": "198.51.100.220"},
    )
    assert response.status_code == 201
    assert response.json()["case_reference"].startswith("CTR-")
    assert response.json().get("status_url")


def test_document_limit_is_twenty_files():
    from app.documents import MAX_DOCUMENTS_PER_CASE, MAX_TOTAL_BYTES
    assert MAX_DOCUMENTS_PER_CASE == 20
    assert MAX_TOTAL_BYTES == 45 * 1024 * 1024
    created = client.post(
        "/api/applications",
        json=valid_payload(email="twenty-docs@example.com"),
        headers={"x-forwarded-for": "198.51.100.221"},
    ).json()
    page = client.get(created["status_url"])
    assert page.status_code == 200
    assert "0/20" in page.text
    assert "45 MB" in page.text or "45 МБ" in page.text



def test_document_analysis_distinguishes_consent_from_configuration(monkeypatch):
    import app.main as main_module

    created = client.post(
        "/api/applications",
        json=valid_payload(email="no-ai-consent@example.com", ai_consent=False, preferred_language="Russian"),
        headers={"x-forwarded-for": "198.51.100.230"},
    ).json()
    status_url = created["status_url"]
    client.post(
        status_url + "/documents",
        files=[("files", ("chat.png", _make_png_bytes(), "image/png"))],
        data={"document_consent": "true"},
        follow_redirects=False,
    )

    monkeypatch.setattr(main_module, "document_analysis_is_enabled", lambda: True)
    page = client.get(status_url)
    assert "подтвердите добровольное согласие" in page.text
    assert "ИИ-анализ документов не включён" not in page.text
    assert 'name="analysis_consent"' in page.text

    missing = client.post(status_url + "/documents/analyse", follow_redirects=False)
    assert missing.status_code == 303
    assert "analysis_issue=consent" in missing.headers["location"]


def test_document_analysis_can_receive_consent_on_case_page(monkeypatch):
    import app.main as main_module
    from app.db import get_case_by_public

    created = client.post(
        "/api/applications",
        json=valid_payload(email="grant-ai-consent@example.com", ai_consent=False),
        headers={"x-forwarded-for": "198.51.100.231"},
    ).json()
    status_url = created["status_url"]
    client.post(
        status_url + "/documents",
        files=[("files", ("invoice.png", _make_png_bytes(), "image/png"))],
        data={"document_consent": "true"},
        follow_redirects=False,
    )

    expected = {
        "readiness_score": 55,
        "summary": "Evidence was organised.",
        "document_inventory": [{"filename": "invoice.png", "document_type": "Invoice", "language": "English", "date_or_period": "Date not visible", "key_content": "Invoice", "readability": "clear"}],
        "timeline": [], "key_evidence": ["Invoice"], "contradictions": [], "missing_evidence": [],
        "risk_flags": [], "recommended_next_steps": ["Human review"],
        "human_review_note": "Important conclusions require human verification.",
    }

    async def fake_analysis(case, documents):
        assert case["ai_consent"] == 1
        return expected

    monkeypatch.setattr(main_module, "document_analysis_is_enabled", lambda: True)
    monkeypatch.setattr(main_module, "analyse_case_documents", fake_analysis)
    response = client.post(
        status_url + "/documents/analyse",
        data={"analysis_consent": "true"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    reference, token = status_url.rstrip("/").split("/")[-2:]
    assert get_case_by_public(reference, token)["ai_consent"] == 1
    report = client.get(response.headers["location"])
    assert "55%" in report.text


def test_document_analysis_failure_is_audited(monkeypatch):
    import app.main as main_module
    from app.db import get_audit, get_case_by_public
    from app.document_analysis import DocumentAnalysisProviderError

    created = client.post(
        "/api/applications",
        json=valid_payload(email="analysis-failure@example.com"),
        headers={"x-forwarded-for": "198.51.100.232"},
    ).json()
    status_url = created["status_url"]
    client.post(
        status_url + "/documents",
        files=[("files", ("chat.png", _make_png_bytes(), "image/png"))],
        data={"document_consent": "true"},
        follow_redirects=False,
    )

    async def failing_analysis(case, documents):
        raise DocumentAnalysisProviderError("OpenAI document analysis returned HTTP 429 (request req-test)")

    monkeypatch.setattr(main_module, "document_analysis_is_enabled", lambda: True)
    monkeypatch.setattr(main_module, "analyse_case_documents", failing_analysis)
    response = client.post(status_url + "/documents/analyse", follow_redirects=False)
    assert response.status_code == 303
    assert "analysis_started=1" in response.headers["location"]
    reference, token = status_url.rstrip("/").split("/")[-2:]
    case = get_case_by_public(reference, token)
    events = get_audit(case["id"])
    failed = next(event for event in events if event["event_type"] == "document_analysis_failed")
    assert "HTTP 429" in failed["details_json"]
    assert "req-test" in failed["details_json"]


def test_public_document_limit_uses_forty_five_megabytes_in_javascript():
    created = client.post(
        "/api/applications",
        json=valid_payload(email="client-limit@example.com"),
        headers={"x-forwarded-for": "198.51.100.233"},
    ).json()
    page = client.get(created["status_url"])
    assert "total > 45 * 1024 * 1024" in page.text
    assert "total > 25 * 1024 * 1024" not in page.text


def test_release_metadata_and_twenty_file_copy_are_consistent():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["version"] == "3.6.0"
    assert health.json()["document_limit"] == 20
    assert health.headers["x-app-version"] == "3.6.0"

    base = Path(__file__).resolve().parent.parent
    active_files = [
        base / "app" / "ai_assistant.py",
        base / "app" / "triage.py",
        base / "app" / "static" / "legal-i18n-v2.js",
        base / "app" / "templates" / "index.html",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in active_files).lower()
    for stale in ("up to five", "five key", "до 5 ключевых", "не более пяти ключевых"):
        assert stale not in combined

    privacy_ru = client.get("/static/privacy.html?lang=ru")
    assert privacy_ru.status_code == 200
    legal_script = client.get("/static/legal-i18n-v2.js")
    assert "до 20 ключевых PDF" in legal_script.text



def test_image_dimensions_checked_before_pixel_decode(monkeypatch):
    from io import BytesIO
    from PIL import Image
    import app.documents as module

    image = Image.new("RGB", (64, 64), "white")
    output = BytesIO()
    image.save(output, format="PNG")
    raw = output.getvalue()

    opened = Image.open(BytesIO(raw))
    original_load = type(opened).load
    calls = {"load": 0}

    def guarded_load(self, *args, **kwargs):
        calls["load"] += 1
        return original_load(self, *args, **kwargs)

    monkeypatch.setattr(type(opened), "load", guarded_load)
    module._sanitise_image(raw, "image/png")
    assert calls["load"] >= 1


def test_pdf_document_analysis_uses_data_url_without_image_detail(monkeypatch):
    import asyncio
    import json
    from types import SimpleNamespace
    import app.document_analysis as module

    expected = {
        "readiness_score": 55, "summary": "Summary",
        "document_inventory": [{"filename": "invoice.pdf", "document_type": "Invoice", "language": "English", "date_or_period": "2026", "key_content": "Invoice", "readability": "clear"}],
        "timeline": [], "key_evidence": [], "contradictions": [],
        "missing_evidence": [], "risk_flags": [], "recommended_next_steps": [],
        "human_review_note": "Human verification required.",
    }
    captured = {}

    class FakeResponse:
        status_code = 200
        headers = {}
        def raise_for_status(self):
            return None
        def json(self):
            return {"output_text": json.dumps(expected)}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return None
        async def post(self, url, headers, json):
            captured["body"] = json
            return FakeResponse()

    monkeypatch.setattr(module, "settings", SimpleNamespace(
        enable_document_analysis=True, openai_api_key="test-key",
        openai_document_model="test-model", document_analysis_timeout_seconds=30,
        document_analysis_max_output_tokens=3000,
    ))
    monkeypatch.setattr(module.httpx, "AsyncClient", FakeClient)
    case = valid_payload(); case["case_reference"] = "CTR-PDF"
    pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\n%%EOF"
    asyncio.run(module.analyse_case_documents(case, [{
        "original_name": "invoice.pdf", "content_type": "application/pdf", "content_blob": pdf,
    }]))
    file_part = captured["body"]["input"][1]["content"][1]
    assert file_part["type"] == "input_file"
    assert file_part["file_data"].startswith("data:application/pdf;base64,")
    assert "detail" not in file_part


def test_document_analysis_retries_temporary_provider_errors(monkeypatch):
    import asyncio
    import json
    from types import SimpleNamespace
    import app.document_analysis as module

    expected = {
        "readiness_score": 50, "summary": "Summary", "document_inventory": [],
        "timeline": [], "key_evidence": [], "contradictions": [], "missing_evidence": [],
        "risk_flags": [], "recommended_next_steps": [],
        "human_review_note": "Human verification required.",
    }
    calls = {"n": 0}

    class FakeResponse:
        headers = {}
        def __init__(self, status_code): self.status_code = status_code
        def raise_for_status(self):
            if self.status_code >= 400:
                request = __import__('httpx').Request('POST', 'https://api.openai.com/v1/responses')
                response = __import__('httpx').Response(self.status_code, request=request)
                raise __import__('httpx').HTTPStatusError('error', request=request, response=response)
        def json(self): return {"output_text": json.dumps(expected)}

    class FakeClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def post(self, *args, **kwargs):
            calls["n"] += 1
            return FakeResponse(503 if calls["n"] == 1 else 200)

    async def no_sleep(_delay): return None
    monkeypatch.setattr(module, "settings", SimpleNamespace(
        enable_document_analysis=True, openai_api_key="test-key",
        openai_document_model="test-model", document_analysis_timeout_seconds=30,
        document_analysis_max_output_tokens=3000,
    ))
    monkeypatch.setattr(module.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(module.asyncio, "sleep", no_sleep)
    case = valid_payload(); case["case_reference"] = "CTR-RETRY"
    result = asyncio.run(module.analyse_case_documents(case, [{
        "original_name": "chat.png", "content_type": "image/png", "content_blob": _make_png_bytes(),
    }]))
    assert result["readiness_score"] == 50
    assert calls["n"] == 2



def test_public_pdf_download_is_attachment_and_image_is_inline():
    created = client.post(
        "/api/applications",
        json=valid_payload(email="disposition@example.com"),
        headers={"x-forwarded-for": "198.51.100.240"},
    ).json()
    status_url = created["status_url"]
    pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\n%%EOF"
    client.post(
        status_url + "/documents",
        files=[
            ("files", ("invoice.pdf", pdf, "application/pdf")),
            ("files", ("photo.png", _make_png_bytes(), "image/png")),
        ],
        data={"document_consent": "true"},
        follow_redirects=False,
    )
    page = client.get(status_url)
    import re
    ids = list(dict.fromkeys(re.findall(r'/documents/(\d+)', page.text)))
    assert len(ids) >= 2
    responses = [client.get(status_url + f"/documents/{doc_id}") for doc_id in ids[:2]]
    dispositions = {response.headers["content-type"].split(";")[0]: response.headers["content-disposition"] for response in responses}
    assert dispositions["application/pdf"].startswith("attachment;")
    assert dispositions["image/png"].startswith("inline;")


def test_completed_public_analysis_is_not_restarted(monkeypatch):
    import app.main as main_module
    created = client.post(
        "/api/applications",
        json=valid_payload(email="single-analysis@example.com"),
        headers={"x-forwarded-for": "198.51.100.241"},
    ).json()
    status_url = created["status_url"]
    client.post(
        status_url + "/documents",
        files=[("files", ("invoice.png", _make_png_bytes(), "image/png"))],
        data={"document_consent": "true"},
        follow_redirects=False,
    )
    calls = {"n": 0}
    expected = {
        "readiness_score": 50, "summary": "Summary",
        "document_inventory": [], "timeline": [], "key_evidence": [],
        "contradictions": [], "missing_evidence": [], "risk_flags": [],
        "recommended_next_steps": [],
        "human_review_note": "Important conclusions require human verification.",
    }
    async def fake_analysis(case, documents):
        calls["n"] += 1
        return expected
    monkeypatch.setattr(main_module, "document_analysis_is_enabled", lambda: True)
    monkeypatch.setattr(main_module, "analyse_case_documents", fake_analysis)
    first = client.post(status_url + "/documents/analyse", follow_redirects=False)
    second = client.post(status_url + "/documents/analyse", follow_redirects=False)
    assert first.status_code == second.status_code == 303
    assert calls["n"] == 1
    page = client.get(status_url)
    assert 'id="documentAnalysisForm"' not in page.text


def test_running_analysis_page_auto_refreshes():
    from app.db import get_case_by_public, set_document_analysis_status
    created = client.post(
        "/api/applications",
        json=valid_payload(email="running-analysis@example.com"),
        headers={"x-forwarded-for": "198.51.100.242"},
    ).json()
    reference, token = created["status_url"].rstrip("/").split("/")[-2:]
    case = get_case_by_public(reference, token)
    set_document_analysis_status(case["id"], "running", "test-model", document_count=1)
    page = client.get(created["status_url"])
    assert "window.setTimeout(()=>window.location.reload(), 5000)" in page.text
    assert "Automatic document analysis is temporarily unavailable" not in page.text



def test_default_admin_token_disables_login():
    import app.main as main_module
    original = main_module.settings.admin_token
    object.__setattr__(main_module.settings, "admin_token", "change-me-before-deployment")
    try:
        response = client.get("/admin/login")
        assert response.status_code == 503
        assert "ADMIN_TOKEN" in response.text
    finally:
        object.__setattr__(main_module.settings, "admin_token", original)



def test_stale_running_analysis_becomes_failed():
    from app.db import execute, get_case_by_public, set_document_analysis_status, transaction
    created = client.post(
        "/api/applications",
        json=valid_payload(email="stale-analysis@example.com"),
        headers={"x-forwarded-for": "198.51.100.243"},
    ).json()
    reference, token = created["status_url"].rstrip("/").split("/")[-2:]
    case = get_case_by_public(reference, token)
    set_document_analysis_status(case["id"], "running", "test-model", document_count=1)
    with transaction() as conn:
        execute(conn, "UPDATE document_analyses SET updated_at=? WHERE case_id=?", ("2020-01-01T00:00:00+00:00", case["id"]))
    page = client.get(created["status_url"])
    assert "automated analysis could not be completed" in page.text.lower()
    assert "window.setTimeout(()=>window.location.reload(), 5000)" not in page.text


def test_completed_analysis_does_not_show_started_banner(monkeypatch):
    import app.main as main_module
    created = client.post(
        "/api/applications",
        json=valid_payload(email="completed-banner@example.com"),
        headers={"x-forwarded-for": "198.51.100.244"},
    ).json()
    status_url = created["status_url"]
    client.post(
        status_url + "/documents",
        files=[("files", ("invoice.png", _make_png_bytes(), "image/png"))],
        data={"document_consent": "true"},
        follow_redirects=False,
    )
    expected = {
        "readiness_score": 50, "summary": "Summary",
        "document_inventory": [], "timeline": [], "key_evidence": [],
        "contradictions": [], "missing_evidence": [], "risk_flags": [],
        "recommended_next_steps": [],
        "human_review_note": "Important conclusions require human verification.",
    }
    async def fake_analysis(case, documents): return expected
    monkeypatch.setattr(main_module, "document_analysis_is_enabled", lambda: True)
    monkeypatch.setattr(main_module, "analyse_case_documents", fake_analysis)
    client.post(status_url + "/documents/analyse", follow_redirects=False)
    page = client.get(status_url + "?analysis_started=1")
    assert "The analysis has started. This page updates automatically" not in page.text
    assert "50%" in page.text


def test_known_placeholder_secrets_are_not_treated_as_secure():
    import app.main as main_module

    original_admin = main_module.settings.admin_token
    original_secret = main_module.settings.app_secret
    object.__setattr__(main_module.settings, "admin_token", "replace-with-a-long-random-token")
    object.__setattr__(main_module.settings, "app_secret", "replace-with-a-long-random-secret")
    try:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["secure_configuration"] is False
        login = client.get("/admin/login")
        assert login.status_code == 503
    finally:
        object.__setattr__(main_module.settings, "admin_token", original_admin)
        object.__setattr__(main_module.settings, "app_secret", original_secret)


def test_render_external_url_is_used_when_public_base_url_is_missing(monkeypatch):
    from app.config import configured_public_base_url

    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://example-service.onrender.com/")
    assert configured_public_base_url() == "https://example-service.onrender.com"


def test_feedback_form_has_no_autofill_prone_honeypot():
    template = (Path(__file__).resolve().parents[1] / "app" / "templates" / "public_status.html").read_text()
    assert 'name="company_website"' not in template


def test_private_case_pages_are_not_indexable():
    created = client.post(
        "/api/applications",
        json=valid_payload(email="noindex@example.com"),
        headers={"x-forwarded-for": "198.51.100.250"},
    ).json()
    page = client.get(created["status_url"])
    assert page.status_code == 200
    assert page.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
    assert page.headers["cache-control"] == "no-store"


def test_docker_does_not_access_log_private_status_tokens():
    dockerfile = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text()
    assert "--no-access-log" in dockerfile


def test_duplicate_document_names_are_made_unique():
    from io import BytesIO
    from PIL import Image
    from app.db import get_case_by_public, list_case_documents

    created = client.post(
        "/api/applications",
        json=valid_payload(email="duplicate-names@example.com"),
        headers={"x-forwarded-for": "198.51.100.40"},
    ).json()

    def image_bytes(colour: str) -> bytes:
        output = BytesIO()
        Image.new("RGB", (2, 2), colour).save(output, format="PNG")
        return output.getvalue()

    uploaded = client.post(
        created["status_url"] + "/documents",
        data={"document_consent": "true"},
        files=[
            ("files", ("screenshot.png", image_bytes("red"), "image/png")),
            ("files", ("screenshot.png", image_bytes("blue"), "image/png")),
        ],
        follow_redirects=False,
        headers={"x-forwarded-for": "198.51.100.40"},
    )
    assert uploaded.status_code == 303

    reference, token = created["status_url"].rstrip("/").split("/")[-2:]
    case = get_case_by_public(reference, token)
    names = [item["original_name"] for item in list_case_documents(case["id"])]
    assert names == ["screenshot.png", "screenshot (2).png"]


def test_client_key_uses_render_first_forwarded_address(monkeypatch):
    from starlette.requests import Request
    from app.security import client_key

    monkeypatch.setenv("RENDER", "true")
    request = Request({
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"x-forwarded-for", b"198.51.100.250, 203.0.113.17")],
        "client": ("10.0.0.10", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
        "query_string": b"",
    })
    assert client_key(request) == "198.51.100.250"


def test_client_key_ignores_forwarded_header_outside_trusted_proxy(monkeypatch):
    from starlette.requests import Request
    from app.security import client_key

    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("TRUST_PROXY_HEADERS", raising=False)
    request = Request({
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"x-forwarded-for", b"198.51.100.250")],
        "client": ("203.0.113.22", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
        "query_string": b"",
    })
    assert client_key(request) == "203.0.113.22"


def test_rate_limiter_bounds_invented_client_keys():
    from app.security import SlidingWindowRateLimiter

    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=600, max_keys=3)
    for index in range(100):
        limiter.allow(f"invented-{index}")
    assert len(limiter.events) <= 4  # three normal buckets plus one shared overflow bucket


def test_decompression_bomb_error_becomes_validation_error(monkeypatch):
    from PIL import Image
    from app.documents import DocumentValidationError, _sanitise_image

    def explode(*_args, **_kwargs):
        raise Image.DecompressionBombError("too many pixels")

    monkeypatch.setattr(Image, "open", explode)
    try:
        _sanitise_image(b"not-used", "image/png")
    except DocumentValidationError as exc:
        assert "damaged or unsupported" in str(exc)
    else:
        raise AssertionError("Expected DocumentValidationError")


def test_short_secrets_are_not_treated_as_secure():
    from app.config import admin_token_is_secure, app_secret_is_secure

    assert admin_token_is_secure("123456") is False
    assert admin_token_is_secure("short-but-not-a-placeholder") is False
    assert app_secret_is_secure("short") is False
    assert app_secret_is_secure("not-a-placeholder-but-too-short") is False
    assert admin_token_is_secure("a" * 32) is False
    assert admin_token_is_secure("admin-token-0123456789-ABCDEFGHIJ") is True
    assert app_secret_is_secure("b" * 32) is False
    assert app_secret_is_secure("app-secret-0123456789-ABCDEFGHIJKL") is True


def test_public_api_documentation_is_disabled():
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_document_inventory_headers_are_localized():
    import app.main as main_module
    from pathlib import Path

    expected = {
        "English": ("File", "Type", "Date", "Readability"),
        "Russian": ("Файл", "Тип", "Дата", "Читаемость"),
        "Serbian": ("Fajl", "Vrsta", "Datum", "Čitljivost"),
        "French": ("Fichier", "Type", "Date", "Lisibilité"),
        "German": ("Datei", "Typ", "Datum", "Lesbarkeit"),
        "Spanish": ("Archivo", "Tipo", "Fecha", "Legibilidad"),
    }
    for language, labels in expected.items():
        copy = main_module.DOCUMENT_COPY[language]
        assert (
            copy["table_file"],
            copy["table_type"],
            copy["table_date"],
            copy["table_readability"],
        ) == labels

    template = (Path(__file__).resolve().parents[1] / "app" / "templates" / "public_status.html").read_text()
    assert "{{ document_copy.table_file }}" in template
    assert "<th>File</th><th>Type</th><th>Date</th><th>Readability</th>" not in template



def test_analysis_claim_is_atomic_and_blocks_evidence_changes():
    from app.db import (
        DocumentAnalysisInProgressError,
        claim_document_analysis,
        delete_case_document,
        get_case_by_public,
        list_case_documents,
        set_document_analysis_status,
    )

    created = client.post(
        "/api/applications",
        json=valid_payload(email="atomic-analysis@example.com"),
        headers={"x-forwarded-for": "198.51.100.61"},
    ).json()
    upload = client.post(
        created["status_url"] + "/documents",
        data={"document_consent": "true"},
        files=[("files", ("evidence.png", _make_png_bytes(), "image/png"))],
        follow_redirects=False,
        headers={"x-forwarded-for": "198.51.100.61"},
    )
    assert upload.status_code == 303
    reference, token = created["status_url"].rstrip("/").split("/")[-2:]
    case = get_case_by_public(reference, token)
    documents = list_case_documents(case["id"])
    assert len(documents) == 1

    run_token = claim_document_analysis(
        case["id"], "test-model", actor="client", document_count=1
    )
    assert isinstance(run_token, str) and run_token
    assert claim_document_analysis(
        case["id"], "test-model", actor="client", document_count=1
    ) is None

    blocked_upload = client.post(
        created["status_url"] + "/documents",
        data={"document_consent": "true"},
        files=[("files", ("second.png", _make_png_bytes(), "image/png"))],
        follow_redirects=False,
        headers={"x-forwarded-for": "198.51.100.62"},
    )
    assert blocked_upload.status_code == 409
    blocked_delete = client.post(
        created["status_url"] + f"/documents/{documents[0]['id']}/delete",
        follow_redirects=False,
        headers={"x-forwarded-for": "198.51.100.62"},
    )
    assert blocked_delete.status_code == 409
    with __import__("pytest").raises(DocumentAnalysisInProgressError):
        delete_case_document(case["id"], documents[0]["id"])

    page = client.get(created["status_url"])
    assert 'id="documentUploadForm"' not in page.text
    assert "/delete" not in page.text
    set_document_analysis_status(case["id"], "failed", "test-model", "test cleanup")


def test_document_batch_limit_is_atomic_without_partial_inserts():
    import hashlib
    import pytest
    from app.db import DocumentLimitError, add_case_documents, get_case_by_public, list_case_documents

    created = client.post(
        "/api/applications",
        json=valid_payload(email="atomic-batch@example.com"),
        headers={"x-forwarded-for": "198.51.100.63"},
    ).json()
    reference, token = created["status_url"].rstrip("/").split("/")[-2:]
    case = get_case_by_public(reference, token)
    one = _make_png_bytes()
    two = one + b"different"
    batch = [
        {"original_name": "one.png", "content_type": "image/png", "size_bytes": len(one), "sha256": hashlib.sha256(one).hexdigest(), "content": one},
        {"original_name": "two.png", "content_type": "image/png", "size_bytes": len(two), "sha256": hashlib.sha256(two).hexdigest(), "content": two},
    ]
    with pytest.raises(DocumentLimitError):
        add_case_documents(case["id"], batch, max_documents=1, max_total_bytes=1024 * 1024)
    assert list_case_documents(case["id"]) == []


def test_interrupted_running_analysis_is_failed_on_process_startup():
    from app.db import (
        fail_running_document_analyses_on_startup,
        get_case_by_public,
        get_document_analysis,
        set_document_analysis_status,
    )

    created = client.post(
        "/api/applications",
        json=valid_payload(email="startup-recovery@example.com"),
        headers={"x-forwarded-for": "198.51.100.64"},
    ).json()
    reference, token = created["status_url"].rstrip("/").split("/")[-2:]
    case = get_case_by_public(reference, token)
    set_document_analysis_status(case["id"], "running", "test-model", document_count=1)
    assert fail_running_document_analyses_on_startup() >= 1
    analysis = get_document_analysis(case["id"])
    assert analysis["status"] == "failed"
    assert "worker stopped or timed out" in analysis["error"]


def test_late_provider_result_does_not_overwrite_failed_claim():
    from app.db import (
        get_case_by_public,
        save_document_analysis,
        set_document_analysis_status,
    )

    created = client.post(
        "/api/applications",
        json=valid_payload(email="late-result@example.com"),
        headers={"x-forwarded-for": "198.51.100.65"},
    ).json()
    reference, token = created["status_url"].rstrip("/").split("/")[-2:]
    case = get_case_by_public(reference, token)
    set_document_analysis_status(case["id"], "running", "test-model", document_count=1)
    set_document_analysis_status(case["id"], "failed", "test-model", "worker stopped")
    result = {
        "readiness_score": 50,
        "summary": "Late result",
        "document_inventory": [],
        "timeline": [],
        "key_evidence": [],
        "contradictions": [],
        "missing_evidence": [],
        "risk_flags": [],
        "recommended_next_steps": [],
        "human_review_note": "Human verification required.",
    }
    assert save_document_analysis(case["id"], result, "test-model", "obsolete-run") is None



def test_admin_state_changes_require_csrf_token():
    import re

    created = client.post(
        "/api/applications",
        json=valid_payload(email="admin-csrf@example.com"),
        headers={"x-forwarded-for": "198.51.100.66"},
    ).json()
    login = client.post(
        "/admin/login",
        data={"token": "test-admin-token-abcdefghijklmnopqrstuvwxyz"},
        follow_redirects=False,
        headers={"x-forwarded-for": "198.51.100.66"},
    )
    assert login.status_code == 303
    dashboard = client.get("/admin")
    case_match = re.search(r'href="/admin/case/(\d+)">' + re.escape(created["case_reference"]), dashboard.text)
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', dashboard.text)
    assert case_match and csrf_match
    case_id = int(case_match.group(1))

    missing = client.post(
        f"/admin/case/{case_id}/status",
        data={"status": "closed", "note": "should fail"},
        follow_redirects=False,
    )
    assert missing.status_code == 422
    wrong = client.post(
        f"/admin/case/{case_id}/status",
        data={"status": "closed", "note": "should fail", "csrf_token": "wrong"},
        follow_redirects=False,
    )
    assert wrong.status_code == 403
    valid = client.post(
        f"/admin/case/{case_id}/status",
        data={"status": "closed", "note": "approved", "csrf_token": csrf_match.group(1)},
        follow_redirects=False,
    )
    assert valid.status_code == 303



def test_pdf_validation_rejects_encryption_and_obfuscated_active_content():
    import asyncio
    import pytest
    from starlette.datastructures import UploadFile
    from io import BytesIO
    from app.documents import DocumentValidationError, prepare_upload

    encrypted = b"%PDF-1.4\n1 0 obj<< /Encrypt 2 0 R >>endobj\n%%EOF"
    with pytest.raises(DocumentValidationError, match="Password-protected"):
        asyncio.run(prepare_upload(UploadFile(BytesIO(encrypted), filename="encrypted.pdf")))

    obfuscated = b"%PDF-1.4\n1 0 obj<< /Java#53cript 2 0 R >>endobj\n%%EOF"
    with pytest.raises(DocumentValidationError, match="active or embedded"):
        asyncio.run(prepare_upload(UploadFile(BytesIO(obfuscated), filename="active.pdf")))



def test_application_ai_triage_has_short_response_budget(monkeypatch):
    import asyncio
    import time
    import app.main as module

    async def slow_triage(_payload):
        await asyncio.sleep(0.2)
        raise AssertionError("slow triage should be cancelled by the response budget")

    monkeypatch.setattr(module, "ai_triage", slow_triage)
    original = module.settings.application_triage_timeout_seconds
    object.__setattr__(module.settings, "application_triage_timeout_seconds", 0.01)
    try:
        started = time.monotonic()
        response = client.post(
            "/api/applications",
            json=valid_payload(email="bounded-triage@example.com"),
            headers={"x-forwarded-for": "198.51.100.81"},
        )
        elapsed = time.monotonic() - started
    finally:
        object.__setattr__(module.settings, "application_triage_timeout_seconds", original)
    assert response.status_code == 201
    assert elapsed < 0.15
    reference, token = response.json()["status_url"].rstrip("/").split("/")[-2:]
    from app.db import get_case_by_public
    case = get_case_by_public(reference, token)
    assert case["triage_source"] == "rules"


def test_failed_email_is_rescheduled_and_eventually_stops(monkeypatch):
    import app.notifications as notifications
    from app.db import execute, pending_notifications, queue_notification, transaction

    original_host = notifications.settings.smtp_host
    original_username = notifications.settings.smtp_username
    original_password = notifications.settings.smtp_password
    object.__setattr__(notifications.settings, "smtp_host", "smtp.example.test")
    object.__setattr__(notifications.settings, "smtp_username", None)
    object.__setattr__(notifications.settings, "smtp_password", None)
    monkeypatch.setattr(
        notifications,
        "_deliver_via_smtp",
        lambda _item: (_ for _ in ()).throw(RuntimeError("temporary smtp outage")),
    )
    try:
        with transaction() as conn:
            execute(conn, "UPDATE notification_outbox SET status='sent',sent_at=? WHERE status='pending'", (__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(timespec='seconds'),))
        queue_notification(None, "retry@example.com", "Retry", "Body")
        result = notifications.deliver_pending()
        assert result["pending"] == 1
        with transaction() as conn:
            row = execute(
                conn,
                "SELECT * FROM notification_outbox WHERE recipient=? ORDER BY id DESC LIMIT 1",
                ("retry@example.com",),
            ).fetchone()
            assert row["status"] == "pending"
            assert row["attempts"] == 1
            assert row["next_attempt_at"]
            execute(
                conn,
                "UPDATE notification_outbox SET attempts=4,next_attempt_at=NULL WHERE id=?",
                (row["id"],),
            )
        result = notifications.deliver_pending()
        assert result["failed"] == 1
        with transaction() as conn:
            final = execute(conn, "SELECT * FROM notification_outbox WHERE id=?", (row["id"],)).fetchone()
            assert final["status"] == "failed"
            assert final["attempts"] == 5
        assert all(item["recipient"] != "retry@example.com" for item in pending_notifications())
    finally:
        object.__setattr__(notifications.settings, "smtp_host", original_host)
        object.__setattr__(notifications.settings, "smtp_username", original_username)
        object.__setattr__(notifications.settings, "smtp_password", original_password)


def test_document_analysis_drops_invented_evidence_filenames(monkeypatch):
    import asyncio
    import json
    import app.document_analysis as module

    expected = {
        "readiness_score": 60,
        "summary": "Summary",
        "document_inventory": [
            {"filename": "INVOICE.PDF", "document_type": "Invoice", "language": "English", "date_or_period": "2026", "key_content": "Known", "readability": "clear"},
            {"filename": "invented.pdf", "document_type": "Other", "language": "English", "date_or_period": "2026", "key_content": "Invented", "readability": "clear"},
        ],
        "timeline": [{"date": "2026", "event": "Paid", "source_files": ["invoice.pdf", "invented.pdf", "INVOICE.PDF"], "confidence": "high"}],
        "key_evidence": [], "contradictions": [], "missing_evidence": [], "risk_flags": [],
        "recommended_next_steps": [], "human_review_note": "Human verification required.",
    }

    class FakeResponse:
        status_code = 200
        headers = {}
        def raise_for_status(self): return None
        def json(self): return {"output_text": json.dumps(expected)}

    class FakeClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def post(self, *args, **kwargs): return FakeResponse()

    monkeypatch.setattr(module.httpx, "AsyncClient", FakeClient)
    original_enabled = module.settings.enable_document_analysis
    original_key = module.settings.openai_api_key
    original_model = module.settings.openai_document_model
    object.__setattr__(module.settings, "enable_document_analysis", True)
    object.__setattr__(module.settings, "openai_api_key", "test-key")
    object.__setattr__(module.settings, "openai_document_model", "test-model")
    try:
        result = asyncio.run(module.analyse_case_documents(
            {"case_reference": "CTR-TEST", "preferred_language": "English"},
            [{"original_name": "invoice.pdf", "content_type": "application/pdf", "content_blob": b"%PDF-1.4\n%%EOF"}],
        ))
    finally:
        object.__setattr__(module.settings, "enable_document_analysis", original_enabled)
        object.__setattr__(module.settings, "openai_api_key", original_key)
        object.__setattr__(module.settings, "openai_document_model", original_model)
    assert [item["filename"] for item in result["document_inventory"]] == ["invoice.pdf"]
    assert result["timeline"][0]["source_files"] == ["invoice.pdf"]



def test_retention_starts_when_case_is_closed_not_when_created():
    from app.db import execute, get_case_by_public, soft_delete_expired, transaction, update_status

    created = client.post(
        "/api/applications",
        json=valid_payload(email="old-open-case@example.com"),
        headers={"x-forwarded-for": "198.51.100.170"},
    ).json()
    reference, token = created["status_url"].rstrip("/").split("/")[-2:]
    case = get_case_by_public(reference, token)
    with transaction() as conn:
        execute(
            conn,
            "UPDATE cases SET created_at='2000-01-01T00:00:00+00:00' WHERE id=?",
            (case["id"],),
        )
    update_status(case["id"], "closed", "closed today")

    assert soft_delete_expired(90) == 0
    with transaction() as conn:
        row = execute(conn, "SELECT deleted_at FROM cases WHERE id=?", (case["id"],)).fetchone()
        assert row["deleted_at"] is None


def test_admin_retriage_uses_short_ai_timeout(monkeypatch):
    import asyncio
    import re
    import app.main as module
    from app.db import get_case_by_public

    created = client.post(
        "/api/applications",
        json=valid_payload(email="admin-retriage-timeout@example.com"),
        headers={"x-forwarded-for": "198.51.100.171"},
    ).json()
    reference, token = created["status_url"].rstrip("/").split("/")[-2:]
    case = get_case_by_public(reference, token)

    async def slow_triage(_payload):
        await asyncio.sleep(0.2)
        raise AssertionError("retriage should have been cancelled")

    monkeypatch.setattr(module, "ai_triage", slow_triage)
    monkeypatch.setattr(
        module,
        "settings",
        module.settings.__class__(**{
            **module.settings.__dict__,
            "application_triage_timeout_seconds": 0.01,
        }),
    )
    login = client.post(
        "/admin/login",
        data={"token": "test-admin-token-abcdefghijklmnopqrstuvwxyz"},
        follow_redirects=False,
        headers={"x-forwarded-for": "198.51.100.171"},
    )
    assert login.status_code == 303
    page = client.get(f"/admin/case/{case['id']}")
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
    assert csrf_match
    response = client.post(
        f"/admin/case/{case['id']}/retriage",
        data={"csrf_token": csrf_match.group(1)},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_invalid_numeric_environment_values_use_safe_defaults(monkeypatch):
    from app.config import _env_float, _env_int, configured_public_base_url

    monkeypatch.setenv("BROKEN_INTEGER", "not-a-number")
    monkeypatch.setenv("BROKEN_FLOAT", "")
    assert _env_int("BROKEN_INTEGER", 60, minimum=10, maximum=100) == 60
    assert _env_float("BROKEN_FLOAT", 8.0, minimum=1.0, maximum=30.0) == 8.0
    monkeypatch.setenv("PUBLIC_BASE_URL", "javascript:alert(1)")
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://safe-example.onrender.com")
    assert configured_public_base_url() == "https://safe-example.onrender.com"


def test_document_analysis_drops_timeline_events_without_real_sources(monkeypatch):
    import asyncio
    import json
    import app.document_analysis as module

    payload = {
        "readiness_score": 50,
        "summary": "Summary",
        "document_inventory": [{
            "filename": "invoice.png",
            "document_type": "invoice",
            "language": "English",
            "date_or_period": "2026-01-01",
            "key_content": "Invoice",
            "readability": "clear",
        }],
        "timeline": [
            {"date": "2026-01-01", "event": "Supported", "source_files": ["invoice.png"], "confidence": "high"},
            {"date": "2026-01-02", "event": "Invented", "source_files": ["missing.png"], "confidence": "low"},
        ],
        "key_evidence": [],
        "contradictions": [],
        "missing_evidence": [],
        "risk_flags": [],
        "recommended_next_steps": [],
        "human_review_note": "Human verification required.",
    }

    class FakeResponse:
        status_code = 200
        headers = {}
        def raise_for_status(self):
            return None
        def json(self):
            return {"output_text": json.dumps(payload)}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(module.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(
        module,
        "settings",
        module.settings.__class__(**{
            **module.settings.__dict__,
            "enable_document_analysis": True,
            "openai_api_key": "test-key",
            "openai_document_model": "test-model",
        }),
    )
    result = asyncio.run(module.analyse_case_documents(
        {
            "case_reference": "CTR-TEST",
            "preferred_language": "English",
            "main_problem": "Wrong specification",
            "requested_result": "Refund",
            "amount_in_dispute": "1000",
            "description": "Description",
        },
        [{
            "original_name": "invoice.png",
            "content_type": "image/png",
            "content_blob": b"png",
        }],
    ))
    assert [item["event"] for item in result["timeline"]] == ["Supported"]


def test_late_result_from_previous_run_cannot_overwrite_new_claim():
    from app.db import (
        add_case_document, claim_document_analysis, create_case, get_document_analysis,
        save_document_analysis, set_document_analysis_status,
    )
    import hashlib

    payload = valid_payload(email="run-token-race@example.com")
    triage = {
        "decision": "needs_information", "risk_level": "medium", "priority": 50,
        "confidence": 0.5, "position_strength": "unclear", "in_scope": True,
        "hard_stop": False, "reasons": [], "missing_information": [], "risk_flags": [],
        "recommended_action": "Review", "public_message": "Review", "source": "rules",
    }
    case = create_case(payload, triage, "CTR-2026-RUNTOKEN", "run-token-public")
    content = _make_png_bytes()
    add_case_document(case["id"], {
        "original_name": "evidence.png", "content_type": "image/png",
        "size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
        "content": content,
    })
    first_token = claim_document_analysis(
        case["id"], "test-model", actor="client", document_count=1
    )
    assert first_token
    set_document_analysis_status(case["id"], "failed", "test-model", "stale worker")
    second_token = claim_document_analysis(
        case["id"], "test-model", actor="client", document_count=1, allow_completed=True
    )
    assert second_token and second_token != first_token

    old_result = {
        "readiness_score": 1, "summary": "OLD RUN", "document_inventory": [],
        "timeline": [], "key_evidence": [], "contradictions": [],
        "missing_evidence": [], "risk_flags": [], "recommended_next_steps": [],
        "human_review_note": "Human verification required.",
    }
    assert save_document_analysis(case["id"], old_result, "test-model", first_token) is None
    current = get_document_analysis(case["id"])
    assert current["status"] == "running"
    assert current["result"].get("summary") != "OLD RUN"

    new_result = dict(old_result, readiness_score=80, summary="NEW RUN")
    assert save_document_analysis(case["id"], new_result, "test-model", second_token) is not None
    assert get_document_analysis(case["id"])["result"]["summary"] == "NEW RUN"


def test_overlapping_deploy_does_not_fail_fresh_analysis():
    from app.db import (
        claim_document_analysis, fail_running_document_analyses_on_startup,
        get_case_by_public, get_document_analysis,
    )

    created = client.post(
        "/api/applications",
        json=valid_payload(email="fresh-deploy-analysis@example.com"),
        headers={"x-forwarded-for": "198.51.100.90"},
    ).json()
    client.post(
        created["status_url"] + "/documents",
        data={"document_consent": "true"},
        files=[("files", ("fresh.png", _make_png_bytes(), "image/png"))],
        follow_redirects=False,
        headers={"x-forwarded-for": "198.51.100.90"},
    )
    reference, token = created["status_url"].rstrip("/").split("/")[-2:]
    case = get_case_by_public(reference, token)
    run_token = claim_document_analysis(
        case["id"], "test-model", actor="client", document_count=1
    )
    assert run_token
    assert fail_running_document_analyses_on_startup(stale_seconds=300) == 0
    assert get_document_analysis(case["id"])["status"] == "running"


def test_stale_failure_does_not_overwrite_just_completed_result():
    from app.db import (
        claim_document_analysis, fail_stale_document_analysis, get_case_by_public,
        get_document_analysis, save_document_analysis,
    )

    created = client.post(
        "/api/applications",
        json=valid_payload(email="stale-completion-race@example.com"),
        headers={"x-forwarded-for": "198.51.100.91"},
    ).json()
    client.post(
        created["status_url"] + "/documents",
        data={"document_consent": "true"},
        files=[("files", ("race.png", _make_png_bytes(), "image/png"))],
        follow_redirects=False,
        headers={"x-forwarded-for": "198.51.100.91"},
    )
    reference, token = created["status_url"].rstrip("/").split("/")[-2:]
    case = get_case_by_public(reference, token)
    run_token = claim_document_analysis(
        case["id"], "test-model", actor="client", document_count=1
    )
    result = {
        "readiness_score": 90, "summary": "Completed safely", "document_inventory": [],
        "timeline": [], "key_evidence": [], "contradictions": [],
        "missing_evidence": [], "risk_flags": [], "recommended_next_steps": [],
        "human_review_note": "Human verification required.",
    }
    assert save_document_analysis(case["id"], result, "test-model", run_token) is not None
    assert fail_stale_document_analysis(case["id"], stale_seconds=0) is False
    analysis = get_document_analysis(case["id"])
    assert analysis["status"] == "completed"
    assert analysis["result"]["summary"] == "Completed safely"


def test_existing_document_analysis_table_gets_run_token_migration(tmp_path):
    import sqlite3
    from app.db import _ensure_document_analysis_run_token

    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE document_analyses (
            case_id INTEGER PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            status TEXT NOT NULL,
            model TEXT NOT NULL DEFAULT '',
            result_json TEXT NOT NULL DEFAULT '{}',
            error TEXT NOT NULL DEFAULT ''
        )
        """
    )
    _ensure_document_analysis_run_token(conn)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(document_analyses)")}
    assert "run_token" in columns
    conn.close()


def test_notification_outbox_claim_prevents_cross_process_duplicate_delivery():
    from app.db import (
        claim_pending_notifications,
        execute,
        mark_notification,
        queue_notification,
        transaction,
    )

    with transaction() as conn:
        execute(
            conn,
            "UPDATE notification_outbox SET status='sent',sent_at=? WHERE status IN ('pending','sending')",
            (__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(timespec="seconds"),),
        )
    queue_notification(None, "lease@example.com", "Lease", "Body")

    first = claim_pending_notifications(limit=10)
    assert len(first) == 1
    assert first[0]["recipient"] == "lease@example.com"
    assert first[0]["status"] == "sending"
    assert first[0]["claim_token"]

    # A second process must not see the already leased row.
    assert claim_pending_notifications(limit=10) == []

    # A worker that does not own the lease cannot change its state.
    assert mark_notification(
        first[0]["id"], "sent", expected_claim_token="wrong-token"
    ) is False
    assert mark_notification(
        first[0]["id"], "sent", expected_claim_token=first[0]["claim_token"]
    ) is True



def test_notification_outbox_recovers_abandoned_lease():
    from app.db import (
        claim_pending_notifications,
        execute,
        mark_notification,
        queue_notification,
        transaction,
    )

    with transaction() as conn:
        execute(
            conn,
            "UPDATE notification_outbox SET status='sent',sent_at=? WHERE status IN ('pending','sending')",
            (__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(timespec="seconds"),),
        )
    queue_notification(None, "stale-lease@example.com", "Lease", "Body")
    first = claim_pending_notifications(limit=10, lease_seconds=60)
    assert len(first) == 1

    old = (
        __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        - __import__("datetime").timedelta(minutes=10)
    ).isoformat(timespec="seconds")
    with transaction() as conn:
        execute(
            conn,
            "UPDATE notification_outbox SET claimed_at=? WHERE id=?",
            (old, first[0]["id"]),
        )

    recovered = claim_pending_notifications(limit=10, lease_seconds=60)
    assert len(recovered) == 1
    assert recovered[0]["id"] == first[0]["id"]
    assert recovered[0]["claim_token"] != first[0]["claim_token"]
    assert mark_notification(
        recovered[0]["id"], "sent",
        expected_claim_token=recovered[0]["claim_token"],
    ) is True



def test_fresh_postgres_audit_schema_has_one_created_at_column(monkeypatch):
    from contextlib import contextmanager
    import app.db as db

    statements = []

    class Cursor:
        rowcount = 0
        def fetchall(self):
            return []

    @contextmanager
    def fake_transaction():
        yield object()

    def fake_execute(_conn, query, _params=()):
        statements.append(query)
        return Cursor()

    monkeypatch.setattr(db, "using_postgres", lambda: True)
    monkeypatch.setattr(db, "transaction", fake_transaction)
    monkeypatch.setattr(db, "execute", fake_execute)
    monkeypatch.setattr(db, "_ensure_notification_retry_columns", lambda _conn: None)
    monkeypatch.setattr(db, "_ensure_document_analysis_run_token", lambda _conn: None)

    db.init_db()
    audit_statement = next(
        statement for statement in statements
        if "CREATE TABLE IF NOT EXISTS audit_log" in statement
    )
    assert audit_statement.lower().count("created_at text not null") == 1


def test_existing_sqlite_outbox_migrates_database_lease_columns(tmp_path):
    import sqlite3
    import app.db as db

    old_path = db.settings.database_path
    migrated_path = tmp_path / "old-outbox.db"
    conn = sqlite3.connect(migrated_path)
    conn.execute(
        """
        CREATE TABLE notification_outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            case_id INTEGER,
            recipient TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            error TEXT NOT NULL DEFAULT '',
            sent_at TEXT,
            attempts INTEGER NOT NULL DEFAULT 0,
            next_attempt_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()

    object.__setattr__(db.settings, "database_path", migrated_path)
    try:
        db.init_db()
        check = sqlite3.connect(migrated_path)
        columns = {row[1] for row in check.execute("PRAGMA table_info(notification_outbox)")}
        check.close()
        assert {"claim_token", "claimed_at"}.issubset(columns)
    finally:
        object.__setattr__(db.settings, "database_path", old_path)



def test_application_and_initial_notifications_commit_atomically():
    """A failure while inserting the outbox must roll back the case too."""
    import sqlite3
    from app.db import create_case, get_case_by_public
    from app.triage import rules_triage
    from app.schemas import ApplicationCreate

    payload = ApplicationCreate(**valid_payload(email="atomic-outbox@example.com"))
    triage = rules_triage(payload).model_dump()
    reference = "CTR-ATOMIC-ROLLBACK"
    token = "atomic-token"
    try:
        create_case(
            payload.model_dump(),
            triage,
            reference,
            token,
            notifications=[{"subject": "Broken", "body": "Broken"}],
        )
    except (sqlite3.IntegrityError, TypeError, KeyError):
        pass
    else:
        raise AssertionError("The invalid outbox row should fail the transaction")
    assert get_case_by_public(reference, token) is None


def test_deliver_pending_claims_each_email_immediately_before_sending(monkeypatch):
    import app.notifications as notifications

    items = [
        {"id": 101, "recipient": "one@example.com", "subject": "One", "body": "Body", "attempts": 0, "claim_token": "a"},
        {"id": 102, "recipient": "two@example.com", "subject": "Two", "body": "Body", "attempts": 0, "claim_token": "b"},
    ]
    claim_limits = []

    def fake_claim(*, limit=100, lease_seconds=300):
        claim_limits.append(limit)
        return [items.pop(0)] if items else []

    monkeypatch.setattr(notifications, "claim_pending_notifications", fake_claim)
    monkeypatch.setattr(notifications, "pending_notifications", lambda: [])
    monkeypatch.setattr(notifications, "mark_notification", lambda *args, **kwargs: True)
    monkeypatch.setattr(notifications, "_deliver_via_smtp", lambda _item: None)
    original_host = notifications.settings.smtp_host
    original_username = notifications.settings.smtp_username
    original_password = notifications.settings.smtp_password
    object.__setattr__(notifications.settings, "smtp_host", "smtp.example.test")
    object.__setattr__(notifications.settings, "smtp_username", None)
    object.__setattr__(notifications.settings, "smtp_password", None)
    try:
        result = notifications.deliver_pending(max_messages=10)
    finally:
        object.__setattr__(notifications.settings, "smtp_host", original_host)
        object.__setattr__(notifications.settings, "smtp_username", original_username)
        object.__setattr__(notifications.settings, "smtp_password", original_password)
    assert result["sent"] == 2
    assert claim_limits == [1, 1, 1]


def test_feedback_is_rejected_before_case_is_closed():
    created = client.post(
        "/api/applications",
        json=valid_payload(email="early-feedback@example.com"),
        headers={"x-forwarded-for": "198.51.100.199"},
    ).json()
    response = client.post(
        created["status_url"] + "/feedback",
        data={"rating": 5, "feedback_text": "This should not be accepted yet.", "display_name": "", "testimonial_consent": "false"},
        follow_redirects=False,
    )
    assert response.status_code == 409


def test_repeated_close_does_not_queue_duplicate_completion_email():
    from app.db import create_case, execute, transaction, update_status
    from app.notifications import build_completion_notifications
    from app.schemas import ApplicationCreate
    from app.triage import rules_triage

    payload = ApplicationCreate(**valid_payload(email="single-close@example.com"))
    triage = rules_triage(payload).model_dump()
    triage["decision"] = "accepted"
    case = create_case(payload.model_dump(), triage, "CTR-SINGLE-CLOSE", "single-close-token")
    messages = build_completion_notifications(case)
    update_status(case["id"], "closed", "done", close_notifications=messages)
    update_status(case["id"], "closed", "done again", close_notifications=messages)
    with transaction() as conn:
        row = execute(
            conn,
            "SELECT COUNT(*) AS n FROM notification_outbox WHERE case_id=? AND recipient=?",
            (case["id"], case["email"]),
        ).fetchone()
    assert int(row["n"]) == 1


def test_close_status_and_completion_notification_commit_atomically():
    from app.db import create_case, get_case, update_status
    from app.schemas import ApplicationCreate
    from app.triage import rules_triage

    payload = ApplicationCreate(**valid_payload(email="atomic-close@example.com"))
    triage = rules_triage(payload).model_dump()
    triage["decision"] = "accepted"
    case = create_case(payload.model_dump(), triage, "CTR-ATOMIC-CLOSE", "atomic-close-token")
    try:
        update_status(
            case["id"],
            "closed",
            "must roll back",
            close_notifications=[{"subject": "Broken", "body": "Broken"}],
        )
    except KeyError:
        pass
    else:
        raise AssertionError("The invalid completion notification should fail the transaction")
    assert get_case(case["id"])["status"] == "accepted"


def test_oversized_json_body_is_rejected_before_validation():
    from app.main import STANDARD_REQUEST_BODY_BYTES

    response = client.post(
        "/api/applications",
        content=b"x" * (STANDARD_REQUEST_BODY_BYTES + 1),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "Request body is too large"


def test_oversized_document_content_length_is_rejected_before_body_read():
    import asyncio
    from app.main import DOCUMENT_UPLOAD_REQUEST_BODY_BYTES, RequestBodyLimitMiddleware

    called = False
    received = False
    messages = []

    async def downstream(scope, receive, send):
        nonlocal called
        called = True

    async def receive():
        nonlocal received
        received = True
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/case/CTR-2026-ABC/token/documents",
        "headers": [
            (b"content-length", str(DOCUMENT_UPLOAD_REQUEST_BODY_BYTES + 1).encode("ascii")),
            (b"content-type", b"multipart/form-data; boundary=test"),
        ],
    }
    asyncio.run(RequestBodyLimitMiddleware(downstream)(scope, receive, send))

    assert called is False
    assert received is False
    assert messages[0]["status"] == 413


def test_chunked_body_is_capped_without_content_length():
    import asyncio
    from app.main import RequestBodyLimitMiddleware, STANDARD_REQUEST_BODY_BYTES

    messages = []
    chunks = iter([
        {"type": "http.request", "body": b"a" * (STANDARD_REQUEST_BODY_BYTES // 2 + 1), "more_body": True},
        {"type": "http.request", "body": b"b" * (STANDARD_REQUEST_BODY_BYTES // 2 + 1), "more_body": False},
    ])

    async def receive():
        return next(chunks)

    async def send(message):
        messages.append(message)

    async def downstream(scope, receive, send):
        while True:
            message = await receive()
            if not message.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/applications",
        "headers": [(b"transfer-encoding", b"chunked")],
    }
    asyncio.run(RequestBodyLimitMiddleware(downstream)(scope, receive, send))

    assert messages[0]["status"] == 413


def test_health_exposes_request_body_limits():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["standard_request_limit_mb"] == 1
    assert response.json()["document_upload_request_limit_mb"] == 50
    assert response.json()["document_processing_workers"] == 2


def test_admin_login_requires_secure_app_secret_even_with_secure_admin_token():
    """A per-process fallback secret must never enable unstable admin sessions."""
    import app.main as main_module

    original_admin = main_module.settings.admin_token
    original_secret = main_module.settings.app_secret
    object.__setattr__(
        main_module.settings,
        "admin_token",
        "secure-admin-token-0123456789-ABCDEFGHIJKL",
    )
    object.__setattr__(main_module.settings, "app_secret", "development-secret-change-me")
    try:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["secure_configuration"] is False

        page = client.get("/admin/login")
        assert page.status_code == 503
        assert "APP_SECRET" in page.text

        login = client.post(
            "/admin/login",
            data={"token": "secure-admin-token-0123456789-ABCDEFGHIJKL"},
            follow_redirects=False,
        )
        assert login.status_code == 503
        assert "APP_SECRET" in login.text
    finally:
        object.__setattr__(main_module.settings, "admin_token", original_admin)
        object.__setattr__(main_module.settings, "app_secret", original_secret)


def test_prepare_upload_offloads_cpu_processing_from_event_loop(monkeypatch):
    """Large-image re-encoding must not freeze unrelated async requests."""
    import asyncio
    import time
    from io import BytesIO
    from starlette.datastructures import UploadFile
    import app.documents as documents

    def slow_processor(raw: bytes, detected: str):
        time.sleep(0.18)
        return raw, detected

    monkeypatch.setattr(documents, "_process_document_bytes", slow_processor)

    async def scenario():
        upload = UploadFile(
            filename="large.png",
            file=BytesIO(b"\x89PNG\r\n\x1a\nplaceholder"),
        )
        task = asyncio.create_task(documents.prepare_upload(upload))
        started = time.perf_counter()
        await asyncio.sleep(0.02)
        heartbeat_elapsed = time.perf_counter() - started
        prepared = await task
        return heartbeat_elapsed, prepared

    heartbeat_elapsed, prepared = asyncio.run(scenario())
    assert heartbeat_elapsed < 0.10
    assert prepared.original_name == "large.png"


def test_document_processing_concurrency_is_bounded(monkeypatch):
    """Concurrent large uploads must not create an unbounded image-decoder spike."""
    import asyncio
    import threading
    import time
    from io import BytesIO
    from starlette.datastructures import UploadFile
    import app.documents as documents

    active = 0
    maximum_active = 0
    state_lock = threading.Lock()

    def slow_unbounded(raw: bytes, detected: str):
        nonlocal active, maximum_active
        with state_lock:
            active += 1
            maximum_active = max(maximum_active, active)
        try:
            time.sleep(0.10)
            return raw, detected
        finally:
            with state_lock:
                active -= 1

    monkeypatch.setattr(documents, "_process_document_bytes_unbounded", slow_unbounded)

    async def scenario():
        uploads = [
            UploadFile(
                filename=f"large-{index}.png",
                file=BytesIO(b"\x89PNG\r\n\x1a\nplaceholder"),
            )
            for index in range(6)
        ]
        return await asyncio.gather(*(documents.prepare_upload(upload) for upload in uploads))

    prepared = asyncio.run(scenario())
    assert len(prepared) == 6
    assert maximum_active <= documents.MAX_CONCURRENT_DOCUMENT_PROCESSORS
    assert maximum_active >= 1


def test_gpt5_document_analysis_uses_low_reasoning_and_sufficient_budget(monkeypatch):
    import asyncio
    import json
    from types import SimpleNamespace
    import app.document_analysis as module

    expected = {
        "readiness_score": 50, "summary": "Summary", "document_inventory": [],
        "timeline": [], "key_evidence": [], "contradictions": [], "missing_evidence": [],
        "risk_flags": [], "recommended_next_steps": [],
        "human_review_note": "Human verification required.",
    }
    captured = {}

    class FakeResponse:
        status_code = 200
        headers = {}
        def raise_for_status(self): return None
        def json(self):
            return {"id": "resp-ok", "status": "completed", "output": [{"content": [{"type": "output_text", "text": json.dumps(expected)}]}]}

    class FakeClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def post(self, url, headers, json):
            captured["body"] = json
            return FakeResponse()

    monkeypatch.setattr(module, "settings", SimpleNamespace(
        enable_document_analysis=True, openai_api_key="test-key",
        openai_document_model="gpt-5-mini", document_analysis_timeout_seconds=30,
        document_analysis_max_output_tokens=3000,
    ))
    monkeypatch.setattr(module.httpx, "AsyncClient", FakeClient)
    case = valid_payload(); case["case_reference"] = "CTR-GPT5"
    result = asyncio.run(module.analyse_case_documents(case, [{
        "original_name": "chat.png", "content_type": "image/png", "content_blob": _make_png_bytes(),
    }]))
    assert result["readiness_score"] == 50
    assert captured["body"]["reasoning"] == {"effort": "low"}
    assert captured["body"]["text"]["verbosity"] == "low"
    assert captured["body"]["max_output_tokens"] >= 6000


def test_document_analysis_retries_incomplete_or_truncated_structured_output(monkeypatch):
    import asyncio
    import json
    from types import SimpleNamespace
    import app.document_analysis as module

    expected = {
        "readiness_score": 61, "summary": "Summary", "document_inventory": [],
        "timeline": [], "key_evidence": [], "contradictions": [], "missing_evidence": [],
        "risk_flags": [], "recommended_next_steps": [],
        "human_review_note": "Human verification required.",
    }
    bodies = []
    calls = {"n": 0}

    class FakeResponse:
        status_code = 200
        headers = {}
        def __init__(self, payload): self.payload = payload
        def raise_for_status(self): return None
        def json(self): return self.payload

    class FakeClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def post(self, url, headers, json):
            bodies.append(json)
            calls["n"] += 1
            if calls["n"] == 1:
                return FakeResponse({
                    "id": "resp-truncated", "status": "incomplete",
                    "incomplete_details": {"reason": "max_output_tokens"},
                    "output": [{"content": [{"type": "output_text", "text": '{"readiness_score": 61'}]}],
                })
            return FakeResponse({
                "id": "resp-complete", "status": "completed",
                "output": [{"content": [{"type": "output_text", "text": json_module.dumps(expected)}]}],
            })

    # Avoid shadowing the imported json module with the FakeClient argument.
    json_module = json
    monkeypatch.setattr(module, "settings", SimpleNamespace(
        enable_document_analysis=True, openai_api_key="test-key",
        openai_document_model="gpt-5-mini", document_analysis_timeout_seconds=30,
        document_analysis_max_output_tokens=3000,
    ))
    monkeypatch.setattr(module.httpx, "AsyncClient", FakeClient)
    case = valid_payload(); case["case_reference"] = "CTR-INCOMPLETE"
    result = asyncio.run(module.analyse_case_documents(case, [{
        "original_name": "chat.png", "content_type": "image/png", "content_blob": _make_png_bytes(),
    }]))
    assert result["readiness_score"] == 61
    assert calls["n"] == 2
    assert bodies[1]["max_output_tokens"] > bodies[0]["max_output_tokens"]


def test_document_analysis_reports_content_filter_and_refusal(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    import pytest
    import app.document_analysis as module

    payloads = [
        {"id": "resp-filter", "status": "incomplete", "incomplete_details": {"reason": "content_filter"}, "output": []},
        {"id": "resp-refusal", "status": "completed", "output": [{"content": [{"type": "refusal", "refusal": "Cannot comply"}]}]},
    ]

    class FakeResponse:
        status_code = 200
        headers = {}
        def __init__(self, payload): self.payload = payload
        def raise_for_status(self): return None
        def json(self): return self.payload

    class FakeClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def post(self, *args, **kwargs): return FakeResponse(payloads.pop(0))

    monkeypatch.setattr(module, "settings", SimpleNamespace(
        enable_document_analysis=True, openai_api_key="test-key",
        openai_document_model="gpt-5-mini", document_analysis_timeout_seconds=30,
        document_analysis_max_output_tokens=6000,
    ))
    monkeypatch.setattr(module.httpx, "AsyncClient", FakeClient)
    case = valid_payload(); case["case_reference"] = "CTR-REFUSAL"
    docs = [{"original_name": "chat.png", "content_type": "image/png", "content_blob": _make_png_bytes()}]
    with pytest.raises(module.DocumentAnalysisProviderError, match="content filter"):
        asyncio.run(module.analyse_case_documents(case, docs))
    with pytest.raises(module.DocumentAnalysisProviderError, match="declined"):
        asyncio.run(module.analyse_case_documents(case, docs))



def test_document_report_postprocessing_sorts_dates_and_explains_score():
    import app.document_analysis as module

    parsed = {
        "readiness_score": 99,
        "readiness_factors": [
            {"factor": "parties", "status": "complete", "explanation": "Стороны видны."},
            {"factor": "transaction", "status": "partial", "explanation": "Заказ указан частично."},
            {"factor": "specification", "status": "complete", "explanation": "Спецификация подтверждена."},
            {"factor": "payment", "status": "missing", "explanation": "Оплата не подтверждена комплектом."},
            {"factor": "communications", "status": "complete", "explanation": "Переписка читается."},
            {"factor": "delivery", "status": "missing", "explanation": "Доставка не подтверждена комплектом."},
            {"factor": "problem_evidence", "status": "partial", "explanation": "Есть часть фотографий."},
        ],
        "summary": "Краткое резюме.",
        "document_inventory": [
            {"filename": "a.png", "document_type": "Переписка", "language": "Russian", "date_or_period": "Date not visible", "key_content": "Текст", "readability": "clear"},
        ],
        "timeline": [
            {"date": "22 марта 2025", "sort_date": "2025-03-22", "event": "Позднее событие", "source_files": ["a.png"], "confidence": "high"},
            {"date": "19 марта 2025", "sort_date": "2025-03-19", "event": "Раннее событие", "source_files": ["a.png"], "confidence": "high"},
            {"date": "Дата not visible", "sort_date": "", "event": "Без даты", "source_files": ["a.png"], "confidence": "medium"},
        ],
        "key_evidence": ["Факт A", "Факт A"],
        "contradictions": ["Противоречие B"],
        "missing_evidence": ["Документ C"],
        "risk_flags": ["Противоречие B", "Риск мошенничества из-за неподходящего сертификата"],
        "recommended_next_steps": ["Загрузить документ C"],
        "human_review_note": "Важные выводы должен проверить человек.",
    }
    result = module._postprocess_report(parsed, "Russian")
    assert result["readiness_score"] == 55
    assert [item["date"] for item in result["timeline"]] == ["19 марта 2025", "22 марта 2025", "Дата не видна"]
    assert result["document_inventory"][0]["date_or_period"] == "Дата не видна"
    assert len(result["key_evidence"]) == 1
    assert result["risk_flags"] == ["Риск возможного введения в заблуждение или использования несоответствующего документа из-за неподходящего сертификата"]
    assert result["readiness_factors"][0]["weight"] == 10
    assert result["readiness_factors"][0]["earned_points"] == 10


def test_document_report_prompt_requires_cautious_language_and_iso_sort_date():
    import app.document_analysis as module
    prompt = module._developer_prompt("Russian")
    assert "sort_date" in prompt
    assert "not evidenced in the uploaded materials" in prompt
    assert "Never label conduct as fraud" in prompt
    assert "Classify all seven readiness_factors exactly once" in prompt


def test_russian_status_page_localises_fixed_analysis_enums():
    from app.main import DOCUMENT_COPY
    copy = DOCUMENT_COPY["Russian"]
    assert copy["readability_labels"]["clear"] == "Хорошо читается"
    assert copy["confidence_labels"]["high"] == "Высокая уверенность"
    assert copy["readiness_factor_labels"]["payment"] == "Подтверждение оплаты"
