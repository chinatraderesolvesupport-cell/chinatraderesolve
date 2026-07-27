from pathlib import Path
import json
import os
import tempfile

_tmp = tempfile.TemporaryDirectory()
os.environ["DATABASE_PATH"] = str(Path(_tmp.name) / "test.db")
os.environ["ADMIN_TOKEN"] = "test-admin-token-abcdefghijklmnopqrstuvwxyz"
os.environ["APP_SECRET"] = "test-app-secret-abcdefghijklmnopqrstuvwxyz-0123456789"
os.environ["OPENAI_BILLING_READY"] = "false"
os.environ["ENABLE_AI_TRIAGE"] = "false"
os.environ["FREE_ACCESS_MODE"] = "true"
os.environ["RENDER"] = "true"
os.environ["ENABLE_VOLUNTARY_SUPPORT"] = "true"
os.environ["PAYPAL_SUPPORT_URL"] = "https://www.paypal.com/ncp/payment/THKQMZDRRNHQ8"
os.environ["SUPPORT_URL"] = "https://example.com/support"
os.environ["BTC_ADDRESS"] = "1BafLn5NLdKwyv8rvuPJVZUKwQnHyuMej9"
os.environ["ETH_ADDRESS"] = "0x69ACE684f28B0A66157aB62aD06e93761a713c6b"
os.environ["USDT_TRC20_ADDRESS"] = "TV3CgZaUqRqQSAYnzyGaMH3M27AwZwGJNp"
os.environ["SOL_ADDRESS"] = "Er2tJEVwokTtCBroUi9eAbCRnYCxwVaBqbPDiNaQtMYg"
os.environ["INDEXNOW_KEY"] = "a0d2be8a24fd4d8798f0af9d9a8e2a72"

from fastapi.testclient import TestClient
from app.main import app
from app.config import settings


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


READINESS_FACTOR_NAMES = [
    "parties",
    "transaction",
    "specification",
    "payment",
    "communications",
    "delivery",
    "problem_evidence",
]


def readiness_factors(*statuses):
    assert len(statuses) == len(READINESS_FACTOR_NAMES)
    return [
        {
            "factor": factor,
            "status": status,
            "explanation": f"{factor}: {status}",
        }
        for factor, status in zip(READINESS_FACTOR_NAMES, statuses)
    ]


def _make_pdf_bytes(page_count: int = 1) -> bytes:
    from io import BytesIO
    import pikepdf

    output = BytesIO()
    with pikepdf.Pdf.new() as pdf:
        for _ in range(page_count):
            pdf.add_blank_page(page_size=(595, 842))
        pdf.save(output)
    return output.getvalue()


def _make_unsafe_pdf_bytes(kind: str) -> bytes:
    from io import BytesIO
    import pikepdf

    output = BytesIO()
    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page(page_size=(595, 842))
        if kind == "javascript":
            action = pikepdf.Dictionary(
                S=pikepdf.Name.JavaScript,
                JS=pikepdf.String("app.alert('unsafe')"),
            )
            pdf.Root.OpenAction = pdf.make_indirect(action)
        elif kind == "attachment":
            pdf.attachments["payload.txt"] = b"embedded payload"
        else:
            raise ValueError(kind)
        pdf.save(output, object_stream_mode=pikepdf.ObjectStreamMode.generate)
    return output.getvalue()


def test_health_and_home_free_access():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["free_access_mode"] is True
    assert health.json()["support_enabled"] is True
    assert health.json()["paypal_support_enabled"] is True
    assert health.json()["openai_billing_ready"] is False
    assert health.json()["ai_assistant_enabled"] is False
    assert health.json()["voice_input_enabled"] is False
    assert health.json()["document_analysis_enabled"] is False
    home = client.get("/")
    assert home.status_code == 200
    assert "Ограниченный бесплатный доступ" in home.text
    assert "Добровольная поддержка" in home.text
    assert "chinatraderesolve.support@gmail.com" in home.text
    assert "Платные услуги пока не предоставляются. Документы загружаются только на закрытой странице дела." in home.text
    assert "Через этот прототип не принимаются платежи и документы" not in home.text
    assert "Статус прототипа" not in home.text
    assert health.json()["email_delivery_configured"] is False
    assert health.json()["secure_configuration"] is True



def test_legacy_operator_profile_cannot_reappear_on_home():
    import app.main as main_module

    original = main_module.settings.operator_profile
    object.__setattr__(
        main_module.settings,
        "operator_profile",
        "Статус прототипа: Через этот прототип не принимаются платежи и документы.",
    )
    try:
        home = client.get("/")
    finally:
        object.__setattr__(main_module.settings, "operator_profile", original)
    assert home.status_code == 200
    assert "Статус прототипа" not in home.text
    assert "Через этот прототип не принимаются платежи и документы" not in home.text


def test_client_confirmation_email_matches_current_service_policy():
    from app.notifications import build_case_notifications

    base_case = {
        "id": 1,
        "full_name": "Test Buyer",
        "email": "buyer@example.com",
        "case_reference": "CTR-TEST-3726",
        "public_token": "private-token",
        "status": "pilot_candidate",
        "risk_level": "low",
        "priority": 10,
        "main_problem": "Goods not delivered",
    }
    expectations = {
        "Russian": ("Оплата услуг сейчас не принимается", "Ключевые документы запрашиваются только после предварительного отбора заявки", "Добровольная поддержка проекта не является оплатой услуг"),
        "English": ("Payment for services is not currently accepted", "Key documents are requested only after the application has passed preliminary screening", "Voluntary support for the project is not payment for services"),
        "French": ("Le paiement des services n’est pas accepté actuellement", "Les documents essentiels ne sont demandés qu’après la présélection", "Le soutien volontaire au projet ne constitue pas un paiement"),
        "German": ("Eine Bezahlung von Dienstleistungen wird derzeit nicht angenommen", "Wichtige Dokumente werden erst nach der Vorprüfung", "Freiwillige Unterstützung des Projekts ist keine Bezahlung"),
        "Spanish": ("Actualmente no se acepta el pago de servicios", "Los documentos esenciales solo se solicitan después de la evaluación preliminar", "El apoyo voluntario al proyecto no constituye el pago"),
        "Serbian": ("Plaćanje usluga se trenutno ne prihvata", "Ključni dokumenti se traže tek nakon preliminarnog pregleda", "Dobrovoljna podrška projektu nije plaćanje usluge"),
    }
    obsolete = (
        "На этом этапе оплата и загрузка документов не требуются",
        "No service fee or document upload is required at this stage",
        "Aucun paiement ni téléchargement de document n’est requis à ce stade",
        "In dieser Phase sind weder Zahlung noch Dokumenten-Upload erforderlich",
        "En esta fase no se requiere pago ni carga de documentos",
        "U ovoj fazi nisu potrebni plaćanje ni otpremanje dokumenata",
    )
    for language, fragments in expectations.items():
        case = {**base_case, "preferred_language": language}
        client_message = build_case_notifications(case)[0]
        body = client_message["body"]
        assert f"/case/{case['case_reference']}/{case['public_token']}" in body
        for fragment in fragments:
            assert fragment in body
        for stale in obsolete:
            assert stale not in body

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
    assert "https://www.paypal.com/ncp/payment/THKQMZDRRNHQ8" in page.text
    assert "Поддержать через PayPal" in page.text
    assert "Continue to PayPal" in page.text
    assert "https://example.com/support" in page.text
    assert 'class="coin-icon btc"' in page.text
    assert 'class="coin-icon eth"' in page.text
    assert 'class="coin-icon usdt"' in page.text
    assert 'class="coin-icon sol"' in page.text
    assert page.text.count('class="network-alert"') == 4
    assert 'id="cryptoToggle"' in page.text
    assert 'aria-expanded="false"' in page.text
    assert 'aria-controls="cryptoOptions"' in page.text
    assert 'id="cryptoOptions" hidden' in page.text
    assert "grid-template-columns:repeat(2,minmax(0,1fr))" in page.text
    assert "id.startsWith('wallet-')" in page.text
    assert "Обязательная сеть:" in page.text
    assert "Do not use ERC20, BEP20 or any other network." in page.text
    assert 'language_label:"Language"' in page.text
    assert 'paypal_qr_label:"Open PayPal payment page"' in page.text


def test_home_shows_configured_voluntary_payment_methods():
    page = client.get("/")
    assert page.status_code == 200
    assert 'href="/support#paypal"' in page.text
    assert 'href="/support#crypto"' in page.text
    assert 'href="/support#wallet-btc"' not in page.text
    assert 'data-i18n="support_crypto_method"' in page.text
    assert "PayPal" in page.text
    assert "Криптовалюта" in page.text


def test_mobile_menu_accessible_name_is_localized():
    page = client.get("/")
    translations = client.get("/static/translations-v2.js")
    assert page.status_code == 200
    assert translations.status_code == 200
    assert 'data-i18n-aria-label="mobile_menu_open"' in page.text
    assert '"mobile_menu_open":"Open menu"' in translations.text


def test_legal_language_accessible_names_are_localized():
    legal_script = client.get("/static/legal-i18n-v2.js")
    assert legal_script.status_code == 200
    for expected in (
        "en:'Language'",
        "fr:'Langue'",
        "de:'Sprache'",
        "es:'Idioma'",
        "ru:'Язык'",
        "sr:'Jezik'",
    ):
        assert expected in legal_script.text
    assert "setAttribute('aria-label',languageLabels[l]" in legal_script.text


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
    assert 'id="client-feedback"' in admin_case.text

    dashboard_with_feedback = client.get("/admin")
    assert "Открыть и проанализировать" in dashboard_with_feedback.text
    assert f'href="/admin/case/{case_id}#client-feedback"' in dashboard_with_feedback.text
    assert "> 5/5</a>" in dashboard_with_feedback.text

    feedback_centre = client.get("/admin/feedback")
    assert feedback_centre.status_code == 200
    assert "Отзывы клиентов" in feedback_centre.text
    assert "Средняя оценка" in feedback_centre.text
    assert "5.0/5" in feedback_centre.text
    assert "The chronology and next-step checklist" in feedback_centre.text
    assert "Можно рассмотреть для публикации" in feedback_centre.text

    filtered_feedback = client.get("/admin/feedback?rating=4")
    assert "По выбранным фильтрам отзывов нет." in filtered_feedback.text


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
    assert home.headers["permissions-policy"] == "camera=(), microphone=(self), geolocation=()"
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


def test_large_html_responses_are_compressed_when_supported():
    response = client.get("/", headers={"accept-encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"


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
        "0x69ACE684f28B0A66157aB62aD06e93761a713c6b": "Ethereum Mainnet",
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


def test_public_default_wallet_addresses_match_verified_qr_codes():
    from app.config import (
        DEFAULT_BTC_ADDRESS,
        DEFAULT_ETH_ADDRESS,
        DEFAULT_SOL_ADDRESS,
        DEFAULT_USDT_TRC20_ADDRESS,
    )
    from app.main import _valid_btc, _valid_eth, _valid_solana, _valid_tron

    assert DEFAULT_BTC_ADDRESS == "1KPw94sUBeJH3noxdgQWrVMQf3sAebmeN4"
    assert DEFAULT_ETH_ADDRESS == "0x2F8a2773F8254d061ef286Bac8BF922344a2A494"
    assert DEFAULT_USDT_TRC20_ADDRESS == "TEJaGC38ZV8UirP7zkfPRiqHRi73wTWX5R"
    assert DEFAULT_SOL_ADDRESS == "AEZsJ2921CR7qD7kRQRS7BiaxneeaFyKMhwDmyjCS6Zm"
    assert _valid_btc(DEFAULT_BTC_ADDRESS)
    assert _valid_eth(DEFAULT_ETH_ADDRESS)
    assert _valid_tron(DEFAULT_USDT_TRC20_ADDRESS)
    assert _valid_solana(DEFAULT_SOL_ADDRESS)


def test_crypto_qr_assets_are_served_as_png():
    for asset in ("btc", "eth", "usdt-trc20", "sol"):
        response = client.get(f"/support/qr/{asset}.png")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(response.content) > 500


def test_paypal_qr_is_served_as_png():
    response = client.get("/support/paypal-qr.png")
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


def test_ai_assistant_frontend_and_disabled_endpoint(monkeypatch):
    import json
    import app.main as main_module

    monkeypatch.setattr(main_module, "voice_input_is_enabled", lambda: True)
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
    assert 'data-enabled="false"' in home.text
    assert 'id="aiChatRoot"' in home.text and ' hidden' in home.text
    assert "fetch('/api/assistant/transcribe'" in home.text
    assert "navigator.mediaDevices.getUserMedia" in home.text
    assert "window.MediaRecorder" in home.text
    assert "speechSynthesis" not in home.text
    assert "turnstile_token:turnstileToken" in home.text
    assert "aiChatBusy||aiVoiceBusy||!aiChatInput.value.trim()" in home.text
    assert 'id="aiChatTurnstileWidget"' in home.text or 'data-turnstile-required="false"' in home.text
    assert "ensureAiTurnstile" in home.text
    assert "widgetSize=aiTurnstileMount.clientWidth<300?'compact':'flexible'" in home.text
    assert "preferredSpeechVoice" not in home.text
    assert 'id="descriptionVoiceButton"' in home.text
    assert 'id="descriptionVoicePanel"' in home.text
    assert 'id="descriptionVoiceTurnstileWidget"' in home.text or 'data-turnstile-required="false"' in home.text
    assert "uploadDescriptionVoice" in home.text
    assert "data.append('purpose','description')" in home.text
    assert "data.append('purpose','assistant')" in home.text
    assert "descriptionField.dispatchEvent(new Event('input'" in home.text
    assert "window.webkitSpeechRecognition" in home.text
    assert 'id="descriptionVoiceLive"' in home.text
    assert 'id="aiVoiceLive"' in home.text
    assert '.ai-chat-voice.recording{position:sticky;top:0' in home.text
    assert '.description-voice-button.recording{position:fixed' in home.text
    assert 'bottom:calc(12px + env(safe-area-inset-bottom))' in home.text
    assert 'id="aiVoiceButtonText"' in home.text
    assert 'id="descriptionVoiceButtonText"' in home.text
    assert 'setAiVoiceButtonState(true)' in home.text
    assert "descriptionVoiceButtonHint.hidden=Boolean(recording)" in home.text
    assert "let recognition=null,active=false,finalText='',restartTimer=null,hasText=false" in home.text
    assert "function disableLivePreview(){active=false;if(!hasText)onUnavailable()}" in home.text
    assert "aiTurnstileSessionVerified" in home.text
    assert "aiTurnstileSatisfied()" in home.text
    assert "aiVoiceStartPending" in home.text
    assert "descriptionVoiceStartPending" in home.text
    assert "drawFormReadinessAttention" in home.text
    assert "form-readiness-attention" in home.text
    assert "if(preview){hasText=true;onText(preview)}" in home.text
    assert '.description-voice-turnstile.is-verified{display:none}' in home.text
    assert '.description-voice-turnstile.is-verified .description-voice-turnstile-widget{display:none}' in home.text
    assert '.description-voice-panel.is-ready .description-voice-help' in home.text
    assert '.description-voice-turnstile-widget{width:100%;min-width:0;min-height:65px' not in home.text

    translations = json.loads(client.get("/static/translations-v2.json").text)
    for language in ("en", "fr", "de", "es", "ru", "sr"):
        assert translations[language]["ai_chat_button"].strip()
        assert translations[language]["ai_chat_notice"].strip()
        assert translations[language]["ai_chat_welcome"].strip()
        assert translations[language]["ai_voice_consent"].strip()
        assert translations[language]["ai_voice_review"].strip()
        assert translations[language]["ai_voice_cta_hint"].strip()
        assert translations[language]["ai_turnstile_title"].strip()
        assert translations[language]["ai_turnstile_required"].strip()
        assert translations[language]["description_voice_help"].strip()
        assert translations[language]["description_voice_consent"].strip()
        assert translations[language]["description_voice_review"].strip()
        assert translations[language]["description_voice_verification_required"].strip()
        assert translations[language]["voice_live_privacy"].strip()
        assert translations[language]["voice_live_title"].strip()
        assert translations[language]["voice_live_unavailable"].strip()

    unavailable = client.post(
        "/api/assistant",
        json={
            "language": "ru",
            "messages": [{"role": "user", "content": "Как подготовить доказательства?"}],
        },
    )
    assert unavailable.status_code == 503
    assert "временно недоступен" in unavailable.json()["detail"]

    voice_unavailable = client.post(
        "/api/assistant/transcribe",
        data={"language": "ru", "voice_consent": "true"},
        files={"audio": ("voice.webm", b"test-audio", "audio/webm")},
    )
    assert voice_unavailable.status_code == 503


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



def test_ai_assistant_scope_guard_blocks_general_chat_and_specific_vendor_requests():
    from app.ai_assistant import assistant_scope_reply
    from app.schemas import AssistantChatRequest

    off_topic = AssistantChatRequest.model_validate(
        {
            "language": "ru",
            "messages": [
                {
                    "role": "user",
                    "content": "Как починить Toyota Corolla, если стучат амортизаторы?",
                }
            ],
        }
    )
    assert "только по вопросам споров" in assistant_scope_reply(off_topic)

    vendor_request = AssistantChatRequest.model_validate(
        {
            "language": "ru",
            "messages": [
                {
                    "role": "user",
                    "content": "Порекомендуйте конкретного надёжного поставщика из Китая и дайте его контакты.",
                }
            ],
        }
    )
    vendor_reply = assistant_scope_reply(vendor_request)
    assert "не рекомендую" in vendor_reply
    assert "критерии проверки" in vendor_reply


def test_ai_assistant_scope_guard_allows_relevant_questions_and_contextual_followups():
    from app.ai_assistant import assistant_scope_reply
    from app.schemas import AssistantChatRequest

    evidence = AssistantChatRequest.model_validate(
        {
            "language": "ru",
            "messages": [
                {
                    "role": "user",
                    "content": "Какие доказательства готовить для спора с китайским поставщиком?",
                }
            ],
        }
    )
    assert assistant_scope_reply(evidence) is None

    for quick_question in (
        "Подходит ли сервис для моей ситуации?",
        "Как проходит бесплатная проверка?",
        "Is this service suitable for my situation?",
        "How does the free review work?",
    ):
        quick = AssistantChatRequest.model_validate(
            {
                "language": "ru" if quick_question[0] > "z" else "en",
                "messages": [{"role": "user", "content": quick_question}],
            }
        )
        assert assistant_scope_reply(quick) is None

    due_diligence = AssistantChatRequest.model_validate(
        {
            "language": "en",
            "messages": [
                {
                    "role": "user",
                    "content": "How can I verify a Chinese supplier and compare neutral red flags?",
                }
            ],
        }
    )
    assert assistant_scope_reply(due_diligence) is None

    followup = AssistantChatRequest.model_validate(
        {
            "language": "en",
            "messages": [
                {
                    "role": "user",
                    "content": "My supplier delivered goods that differ from the written specification.",
                },
                {"role": "assistant", "content": "Please preserve the written order."},
                {"role": "user", "content": "What should I do next?"},
            ],
        }
    )
    assert assistant_scope_reply(followup) is None

    for short_reply in (
        "да",
        "Да, пожалуйста",
        "составь",
        "продолжай",
        "yes",
        "please do",
        "draft it",
    ):
        contextual = AssistantChatRequest.model_validate(
            {
                "language": "ru" if any("а" <= char.lower() <= "я" for char in short_reply) else "en",
                "messages": [
                    {
                        "role": "user",
                        "content": "Поставщик Alibaba прислал товар с дефектами и отказывается вернуть деньги.",
                    },
                    {
                        "role": "assistant",
                        "content": "Хотите, я составлю письменную претензию поставщику?",
                    },
                    {"role": "user", "content": short_reply},
                ],
            }
        )
        assert assistant_scope_reply(contextual) is None, short_reply

    upload_question = AssistantChatRequest.model_validate(
        {
            "language": "ru",
            "messages": [
                {"role": "user", "content": "Поставщик не отправил товар."},
                {"role": "assistant", "content": "Соберите документы."},
                {"role": "user", "content": "Ну а куда мне это всё отправлять? Я до сих пор не понял."},
            ],
        }
    )
    upload_reply = assistant_scope_reply(upload_question)
    assert "приватную ссылку" in upload_reply
    assert "до 20" in upload_reply

    for natural_upload_question in (
        "Куда мне отправлять документы по спору с поставщиком?",
        "Где загрузить материалы по делу?",
        "Как прикрепить файлы с доказательствами?",
        "Куда направить PDF по моей заявке?",
    ):
        natural_payload = AssistantChatRequest.model_validate(
            {
                "language": "ru",
                "messages": [{"role": "user", "content": natural_upload_question}],
            }
        )
        natural_reply = assistant_scope_reply(natural_payload)
        assert "приватную ссылку" in natural_reply, natural_upload_question
        assert "до 20" in natural_reply, natural_upload_question

    from app.ai_assistant import UPLOAD_DESTINATION_COPY
    multilingual_upload_questions = {
        "en": "Where can I attach the evidence files for my supplier case?",
        "fr": "Où joindre les documents de mon dossier fournisseur ?",
        "de": "Wo kann ich die Unterlagen für meinen Lieferantenfall anhängen?",
        "es": "¿Dónde adjuntar los documentos de mi caso con el proveedor?",
        "sr": "Gde da priložim dokumenta za slučaj sa dobavljačem?",
    }
    for language, question in multilingual_upload_questions.items():
        multilingual_payload = AssistantChatRequest.model_validate(
            {"language": language, "messages": [{"role": "user", "content": question}]}
        )
        assert assistant_scope_reply(multilingual_payload) == UPLOAD_DESTINATION_COPY[language], question

    isolated_yes = AssistantChatRequest.model_validate(
        {"language": "ru", "messages": [{"role": "user", "content": "да"}]}
    )
    assert assistant_scope_reply(isolated_yes) is not None


def test_ai_assistant_removes_isolated_english_tail_from_russian_output():
    from app.ai_assistant import _strip_unexpected_foreign_tail

    assert _strip_unexpected_foreign_tail(
        "Не размещайте здесь номера заказов или конфиденциальные данные. crescent", "ru"
    ) == "Не размещайте здесь номера заказов или конфиденциальные данные."
    assert _strip_unexpected_foreign_tail(
        "Материал был заявлен как Nappa.", "ru"
    ) == "Материал был заявлен как Nappa."


def test_ai_assistant_scope_guard_allows_car_part_supplier_disputes_but_not_repairs():
    from app.ai_assistant import assistant_scope_reply
    from app.schemas import AssistantChatRequest

    relevant = AssistantChatRequest.model_validate(
        {
            "language": "ru",
            "messages": [
                {
                    "role": "user",
                    "content": "Китайский поставщик прислал бракованный двигатель и не возвращает деньги.",
                }
            ],
        }
    )
    assert assistant_scope_reply(relevant) is None

    selection = AssistantChatRequest.model_validate(
        {
            "language": "ru",
            "messages": [
                {
                    "role": "user",
                    "content": "Как проверить поставщика автомобильных амортизаторов перед оплатой?",
                }
            ],
        }
    )
    assert assistant_scope_reply(selection) is None

    repair = AssistantChatRequest.model_validate(
        {
            "language": "ru",
            "messages": [
                {
                    "role": "user",
                    "content": "Как починить двигатель Toyota Corolla?",
                }
            ],
        }
    )
    assert "только по вопросам споров" in assistant_scope_reply(repair)


def test_ai_assistant_scope_guard_rechecks_each_turn_and_blocks_topic_hopping():
    from app.ai_assistant import assistant_scope_reply
    from app.schemas import AssistantChatRequest

    unrelated_followups = (
        "Расскажи анекдот",
        "Кто такой Наполеон?",
        "Объясни квантовую механику",
        "Составь мне резюме",
        "Сколько будет дважды два?",
        "Tell me a joke",
    )
    for latest in unrelated_followups:
        payload = AssistantChatRequest.model_validate(
            {
                "language": "en" if latest.startswith("Tell") else "ru",
                "messages": [
                    {
                        "role": "user",
                        "content": "Поставщик из Китая прислал товар с браком. Что делать?",
                    },
                    {"role": "assistant", "content": "Сохраните договор и фотографии."},
                    {"role": "user", "content": latest},
                ],
            }
        )
        assert assistant_scope_reply(payload) is not None


def test_ai_assistant_scope_guard_blocks_unrelated_code_and_vendor_rankings():
    from app.ai_assistant import assistant_scope_reply
    from app.schemas import AssistantChatRequest

    code_request = AssistantChatRequest.model_validate(
        {
            "language": "ru",
            "messages": [
                {"role": "user", "content": "Напиши Python-код для проверки поставщиков."}
            ],
        }
    )
    assert "только по вопросам споров" in assistant_scope_reply(code_request)

    for request in (
        "Какой маркетплейс лучше для покупки в Китае?",
        "Назови лучшую инспекционную компанию в Китае.",
    ):
        payload = AssistantChatRequest.model_validate(
            {"language": "ru", "messages": [{"role": "user", "content": request}]}
        )
        assert "не рекомендую" in assistant_scope_reply(payload)


def test_ai_assistant_scope_guard_allows_neutral_vendor_checklists_not_endorsements():
    from app.ai_assistant import assistant_scope_reply
    from app.schemas import AssistantChatRequest

    for request in (
        "Назовите признаки мошенничества поставщика.",
        "Назовите документы, которые нужно запросить у поставщика.",
        "Какой поставщик считается надёжным по объективным признакам?",
        "Name the red flags when checking a supplier.",
        "Which supplier documents should I verify?",
    ):
        payload = AssistantChatRequest.model_validate(
            {
                "language": "en" if request[0].isascii() else "ru",
                "messages": [{"role": "user", "content": request}],
            }
        )
        assert assistant_scope_reply(payload) is None, request

    for request in (
        "Какой маркетплейс лучше защищает покупателя?",
        "Какая инспекционная компания подходит для проверки качества?",
        "Which supplier should I choose?",
    ):
        payload = AssistantChatRequest.model_validate(
            {
                "language": "en" if request[0].isascii() else "ru",
                "messages": [{"role": "user", "content": request}],
            }
        )
        reply = assistant_scope_reply(payload)
        assert reply is not None
        assert "recommend" in reply.lower() or "не рекомендую" in reply.lower()


def test_ai_assistant_scope_guard_allows_plain_language_quality_disputes():
    from app.ai_assistant import assistant_scope_reply
    from app.schemas import AssistantChatRequest

    for request in (
        "Я заказал двигатель, но он не соответствует спецификации.",
        "Мне прислали не тот цвет.",
        "Оплатил товар, но его не прислали. Что делать?",
        "Мне не возвращают деньги.",
        "Как проверить компанию перед оплатой?",
        "Я купил на Алибабе товары, оплатил их, но они так и не пришли.",
    ):
        payload = AssistantChatRequest.model_validate(
            {"language": "ru", "messages": [{"role": "user", "content": request}]}
        )
        assert assistant_scope_reply(payload) is None, request


def test_ai_assistant_scope_guard_does_not_consume_daily_quota(monkeypatch):
    import app.main as main_module

    calls = {"usage": 0, "provider": 0}

    async def passed_verification(_token, _request):
        return True

    async def unexpected_provider(_payload):
        calls["provider"] += 1
        return "unexpected"

    def unexpected_usage(*_args, **_kwargs):
        calls["usage"] += 1
        return 1

    monkeypatch.setattr(main_module, "assistant_is_enabled", lambda: True)
    monkeypatch.setattr(main_module, "verify_turnstile", passed_verification)
    monkeypatch.setattr(main_module, "assistant_reply", unexpected_provider)
    monkeypatch.setattr(main_module, "claim_daily_usage_for_subject", unexpected_usage)

    response = client.post(
        "/api/assistant",
        json={
            "language": "en",
            "messages": [{"role": "user", "content": "How do I repair a Toyota engine?"}],
            "turnstile_token": "test-token",
        },
        headers={"x-forwarded-for": "198.51.100.247"},
    )
    assert response.status_code == 200
    assert "only covers disputes" in response.json()["reply"]
    assert calls == {"usage": 0, "provider": 0}


def test_ai_assistant_scope_guard_accepts_implicit_transaction_language_and_rechecks_latest_message():
    from app.ai_assistant import assistant_scope_reply
    from app.schemas import AssistantChatRequest

    for text in (
        "Оплатил товар, но его не прислали. Что делать?",
        "Мне не возвращают деньги.",
        "Как проверить компанию перед оплатой?",
        "Я купил на Алибабе товары, оплатил их, но они так и не пришли.",
    ):
        payload = AssistantChatRequest.model_validate({
            "language": "ru",
            "messages": [{"role": "user", "content": text}],
        })
        assert assistant_scope_reply(payload) is None

    bypass = AssistantChatRequest.model_validate({
        "language": "ru",
        "messages": [
            {"role": "user", "content": "Поставщик прислал товар не по спецификации."},
            {"role": "assistant", "content": "Сохраните договор и переписку."},
            {"role": "user", "content": "А теперь напиши стих про лето."},
        ],
    })
    assert "только по вопросам споров" in assistant_scope_reply(bypass)


def test_ai_assistant_output_removes_unicode_noncharacters():
    from app.ai_assistant import _clean_output_text

    assert _clean_output_text("Bonjour.\U0008ffff") == "Bonjour."
    assert _clean_output_text("Line one\n\n\nLine two") == "Line one\n\nLine two"
    assert _clean_output_text("Normal français, Deutsch, русский, srpski.") == "Normal français, Deutsch, русский, srpski."


def test_ai_assistant_short_limit_is_per_browser_session_not_shared_ip(monkeypatch):
    import app.main as main_module
    from app.security import SlidingWindowRateLimiter
    from fastapi.testclient import TestClient

    async def passed_verification(_token, _request):
        return True

    async def fake_reply(_payload):
        return "Keep the written order and payment proof."

    monkeypatch.setattr(main_module, "assistant_is_enabled", lambda: True)
    monkeypatch.setattr(main_module, "verify_turnstile", passed_verification)
    monkeypatch.setattr(main_module, "assistant_reply", fake_reply)
    monkeypatch.setattr(main_module, "claim_daily_usage_for_subject", lambda *_args, **_kwargs: (1, 1))
    monkeypatch.setattr(main_module, "assistant_limiter", SlidingWindowRateLimiter(limit=1, window_seconds=600))
    monkeypatch.setattr(main_module, "assistant_ip_flood_limiter", SlidingWindowRateLimiter(limit=20, window_seconds=600))

    first_client = TestClient(main_module.app)
    second_client = TestClient(main_module.app)
    payload = {
        "language": "en",
        "messages": [{"role": "user", "content": "The supplier did not deliver my paid order."}],
        "turnstile_token": "test-token",
    }
    headers = {"x-forwarded-for": "198.51.100.249"}
    assert first_client.post("/api/assistant", json=payload, headers=headers).status_code == 200
    assert second_client.post("/api/assistant", json=payload, headers=headers).status_code == 200
    assert first_client.post("/api/assistant", json=payload, headers=headers).status_code == 429


def test_voice_transcription_api_mock(monkeypatch):
    import app.main as main_module

    captured = {}

    async def fake_transcribe(audio_bytes, content_type, language, safety_identifier):
        captured.update(
            audio=audio_bytes,
            content_type=content_type,
            language=language,
            safety_identifier=safety_identifier,
        )
        return "The supplier delivered a different material."

    monkeypatch.setattr(main_module, "voice_input_is_enabled", lambda: True)
    monkeypatch.setattr(main_module, "transcribe_audio", fake_transcribe)
    monkeypatch.setattr(main_module, "claim_daily_usage_for_subject", lambda *_args, **_kwargs: (1, 1))
    no_consent = client.post(
        "/api/assistant/transcribe",
        data={"language": "en"},
        files={"audio": ("voice.webm", b"test-audio", "audio/webm")},
        headers={"x-forwarded-for": "198.51.100.244"},
    )
    assert no_consent.status_code == 422
    assert "consent" in no_consent.json()["detail"].lower()
    response = client.post(
        "/api/assistant/transcribe",
        data={"language": "en", "voice_consent": "true", "purpose": "description"},
        files={"audio": ("voice.webm", b"test-audio", "audio/webm")},
        headers={"x-forwarded-for": "198.51.100.245"},
    )
    assert response.status_code == 200
    assert response.json()["transcript"].startswith("The supplier")
    assert captured["audio"] == b"test-audio"
    assert captured["content_type"] == "audio/webm"
    assert captured["language"] == "en"
    assert len(captured["safety_identifier"]) == 64



def test_voice_rate_limit_is_separate_for_assistant_and_description(monkeypatch):
    import app.main as main_module
    from app.security import SlidingWindowRateLimiter

    async def fake_transcribe(*_args, **_kwargs):
        return "Transcribed text."

    monkeypatch.setattr(main_module, "voice_input_is_enabled", lambda: True)
    monkeypatch.setattr(main_module, "transcribe_audio", fake_transcribe)
    monkeypatch.setattr(main_module, "claim_daily_usage_for_subject", lambda *_args, **_kwargs: (1, 1))
    monkeypatch.setattr(main_module, "voice_attempt_limiter", SlidingWindowRateLimiter(limit=20, window_seconds=600))
    monkeypatch.setattr(main_module, "voice_limiter", SlidingWindowRateLimiter(limit=1, window_seconds=1800))

    headers = {"x-forwarded-for": "198.51.100.246"}
    assistant = client.post(
        "/api/assistant/transcribe",
        data={"language": "ru", "voice_consent": "true", "purpose": "assistant"},
        files={"audio": ("voice.webm", b"test-audio", "audio/webm")},
        headers=headers,
    )
    description = client.post(
        "/api/assistant/transcribe",
        data={"language": "ru", "voice_consent": "true", "purpose": "description"},
        files={"audio": ("voice.webm", b"test-audio", "audio/webm")},
        headers=headers,
    )
    description_again = client.post(
        "/api/assistant/transcribe",
        data={"language": "ru", "voice_consent": "true", "purpose": "description"},
        files={"audio": ("voice.webm", b"test-audio", "audio/webm")},
        headers=headers,
    )

    assert assistant.status_code == 200
    assert description.status_code == 200
    assert description_again.status_code == 429
    assert "голосовых записей" in description_again.json()["detail"]


def test_voice_transcription_provider_request_and_validation(monkeypatch):
    import asyncio
    from types import SimpleNamespace

    import pytest
    import app.voice_transcription as module

    captured = {}

    class FakeResponse:
        headers = {"x-request-id": "req-voice-test"}

        def raise_for_status(self):
            return None

        def json(self):
            return {"text": "  A clear spoken description.  "}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers, data, files):
            captured.update(url=url, headers=headers, data=data, files=files)
            return FakeResponse()

    monkeypatch.setattr(module, "assistant_is_enabled", lambda: True)
    monkeypatch.setattr(
        module,
        "settings",
        SimpleNamespace(
            enable_voice_input=True,
            openai_api_key="test-key",
            openai_transcription_model="gpt-4o-mini-transcribe",
            openai_timeout_seconds=7,
        ),
    )
    monkeypatch.setattr(module.httpx, "AsyncClient", FakeClient)
    transcript = asyncio.run(
        module.transcribe_audio(b"voice-bytes", "audio/webm;codecs=opus", "en", "safe-id")
    )
    assert transcript == "A clear spoken description."
    assert captured["url"].endswith("/v1/audio/transcriptions")
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["headers"]["OpenAI-Safety-Identifier"] == "safe-id"
    assert captured["data"]["model"] == "gpt-4o-mini-transcribe"
    assert captured["files"]["file"][1] == b"voice-bytes"
    with pytest.raises(module.VoiceValidationError, match="invalid"):
        module.validate_voice_audio(b"not-audio", "application/octet-stream")
    with pytest.raises(module.VoiceValidationError, match="too_large"):
        module.validate_voice_audio(b"x" * (module.MAX_VOICE_AUDIO_BYTES + 1), "audio/webm")


def test_ai_turnstile_session_reuses_one_successful_challenge(monkeypatch):
    import app.main as main_module

    calls = {"count": 0}

    async def passed_verification(_token, _request):
        calls["count"] += 1
        return True

    async def assistant_answer(_payload):
        return "Preserve the order, payment proof and supplier messages."

    monkeypatch.setattr(main_module, "turnstile_is_enabled", lambda: True)
    monkeypatch.setattr(main_module, "verify_turnstile", passed_verification)
    monkeypatch.setattr(main_module, "assistant_is_enabled", lambda: True)
    monkeypatch.setattr(main_module, "assistant_reply", assistant_answer)
    with TestClient(main_module.app) as session_client:
        first = session_client.get("/")
        assert 'data-turnstile-session-verified="false"' in first.text
        first_response = session_client.post(
            "/api/assistant",
            json={
                "language": "en",
                "messages": [{"role": "user", "content": "How should I organise evidence for a supplier dispute?"}],
                "turnstile_token": "one-valid-token",
            },
        )
        assert first_response.status_code == 200
        assert calls["count"] == 1

        second_response = session_client.post(
            "/api/assistant",
            json={
                "language": "en",
                "messages": [{"role": "user", "content": "What should I do next?"}],
                "turnstile_token": "",
            },
        )
        assert second_response.status_code == 200
        assert calls["count"] == 1
        second_home = session_client.get("/")
        assert 'data-turnstile-session-verified="true"' in second_home.text


def test_ai_assistant_requires_turnstile_when_configured(monkeypatch):
    import app.main as main_module

    async def failed_verification(_token, _request):
        return False

    monkeypatch.setattr(main_module, "assistant_is_enabled", lambda: True)
    monkeypatch.setattr(main_module, "verify_ai_turnstile", failed_verification)
    response = client.post(
        "/api/assistant",
        json={
            "language": "en",
            "messages": [{"role": "user", "content": "How should I organise evidence?"}],
            "turnstile_token": "",
        },
        headers={"x-forwarded-for": "198.51.100.246"},
    )
    assert response.status_code == 400
    assert "bot-protection" in response.json()["detail"]


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
            openai_assistant_model="gpt-5.6-luna",
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
                {"role": "user", "content": "My supplier sent defective goods."},
                {"role": "assistant", "content": "Preserve the written specification and photos."},
                {"role": "user", "content": "What documents should I prepare?"},
            ],
        }
    )
    reply = asyncio.run(module.assistant_reply(payload))
    assert "written order" in reply
    assert captured["url"].endswith("/v1/responses")
    assert captured["body"]["store"] is False
    assert captured["body"]["model"] == "gpt-5.6-luna"
    assert captured["body"]["max_output_tokens"] == 500
    assert captured["body"]["reasoning"] == {"effort": "none"}
    assert captured["body"]["text"] == {"verbosity": "low"}
    assert captured["body"]["input"][0]["role"] == "developer"
    assert captured["body"]["input"][1] == {
        "role": "user",
        "content": [{"type": "input_text", "text": "My supplier sent defective goods."}],
    }
    assert captured["body"]["input"][2] == {
        "role": "assistant",
        "content": [{"type": "output_text", "text": "Preserve the written specification and photos."}],
    }
    assert captured["body"]["input"][3] == {
        "role": "user",
        "content": [{"type": "input_text", "text": "What documents should I prepare?"}],
    }
    assert "not legal advice" in captured["body"]["input"][0]["content"][0]["text"]
    assert "Answer only about commercial disputes" in captured["body"]["input"][0]["content"][0]["text"]
    assert "Never name, rank, advertise, endorse" in captured["body"]["input"][0]["content"][0]["text"]
    assert captured["headers"]["Authorization"] == "Bearer test-key"


def test_ai_assistant_incomplete_response_is_logged_without_message_content(monkeypatch, caplog):
    import asyncio
    import logging
    from types import SimpleNamespace

    import pytest
    import app.ai_assistant as module
    from app.schemas import AssistantChatRequest

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "status": "incomplete",
                "incomplete_details": {"reason": "max_output_tokens"},
                "usage": {
                    "input_tokens": 250,
                    "output_tokens": 500,
                    "output_tokens_details": {"reasoning_tokens": 500},
                },
                "output": [],
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers, json):
            return FakeResponse()

    monkeypatch.setattr(
        module,
        "settings",
        SimpleNamespace(
            enable_ai_assistant=True,
            openai_api_key="sk-test-secret-value",
            openai_assistant_model="gpt-5.6-luna",
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
            "messages": [{"role": "user", "content": "PRIVATE TEST MESSAGE"}],
        }
    )
    with caplog.at_level(logging.WARNING, logger="chinatraderesolve.ai_assistant"):
        with pytest.raises(module.AssistantProviderError, match="incomplete"):
            asyncio.run(module.assistant_reply(payload))
    log_text = caplog.text
    assert "reason=max_output_tokens" in log_text
    assert "reasoning_tokens=500" in log_text
    assert "PRIVATE TEST MESSAGE" not in log_text
    assert "sk-test-secret-value" not in log_text


def test_ai_assistant_http_error_logs_safe_provider_fields(monkeypatch, caplog):
    import asyncio
    import logging
    from types import SimpleNamespace

    import httpx
    import pytest
    import app.ai_assistant as module
    from app.schemas import AssistantChatRequest

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers, json):
            request = httpx.Request("POST", url)
            return httpx.Response(
                401,
                request=request,
                headers={"x-request-id": "req-safe-test"},
                json={
                    "error": {
                        "type": "invalid_request_error",
                        "code": "invalid_api_key",
                        "param": None,
                        "message": "Incorrect API key provided: sk-test-secret-value",
                    }
                },
            )

    monkeypatch.setattr(
        module,
        "settings",
        SimpleNamespace(
            enable_ai_assistant=True,
            openai_api_key="sk-test-secret-value",
            openai_assistant_model="gpt-5.6-luna",
            openai_moderation_model=None,
            ai_assistant_history_messages=8,
            ai_assistant_max_output_tokens=500,
            openai_timeout_seconds=7,
        ),
    )
    monkeypatch.setattr(module.httpx, "AsyncClient", FakeClient)
    payload = AssistantChatRequest.model_validate(
        {
            "language": "ru",
            "messages": [{"role": "user", "content": "CONFIDENTIAL USER TEXT"}],
        }
    )
    with caplog.at_level(logging.ERROR, logger="chinatraderesolve.ai_assistant"):
        with pytest.raises(module.AssistantProviderError, match="HTTP error"):
            asyncio.run(module.assistant_reply(payload))
    log_text = caplog.text
    assert "status=401" in log_text
    assert "code=invalid_api_key" in log_text
    assert "request_id=req-safe-test" in log_text
    assert "sk-[redacted]" in log_text
    assert "sk-test-secret-value" not in log_text
    assert "CONFIDENTIAL USER TEXT" not in log_text


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
    assert 'data-i18n-aria-label="language_label"' in home.text
    assert 'data-i18n-aria-label="ai_chat_message_label"' in home.text

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
        json=valid_payload(email="unsafe-docs@example.com", preferred_language="Russian"),
        headers={"x-forwarded-for": "198.51.100.202"},
    ).json()
    status_url = created["status_url"]
    unsafe = client.post(
        status_url + "/documents",
        files=[("files", ("payload.html", b"<script>alert(1)</script>", "text/html"))],
        data={"document_consent": "true"},
        follow_redirects=False,
    )
    assert unsafe.status_code == 303
    assert "upload_issue=unsupported_type" in unsafe.headers["location"]
    unsafe_page = client.get(unsafe.headers["location"])
    assert "Выберите только файлы PDF, JPG, PNG или WebP" in unsafe_page.text
    assert 'id="documentUploadForm"' in unsafe_page.text

    oversized = client.post(
        status_url + "/documents",
        files=[("files", ("large.png", b"\x89PNG\r\n\x1a\n" + b"x" * (8 * 1024 * 1024), "image/png"))],
        data={"document_consent": "true"},
        follow_redirects=False,
    )
    assert oversized.status_code == 303
    assert "upload_issue=too_large" in oversized.headers["location"]
    oversized_page = client.get(oversized.headers["location"])
    assert "8 МБ" in oversized_page.text


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
        "readiness_factors": readiness_factors(
            "missing", "missing", "missing", "complete",
            "complete", "complete", "complete",
        ),
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


def test_application_response_exposes_canonical_absolute_status_url():
    created = client.post(
        "/api/applications",
        json=valid_payload(email="canonical-link@example.com"),
        headers={"x-forwarded-for": "198.51.100.241"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status_url"].startswith("/case/")
    assert body["absolute_status_url"] == settings.public_base_url.rstrip("/") + body["status_url"]

    index_page = client.get("/")
    assert "result.absolute_status_url||new URL(result.status_url,window.location.origin).href" in index_page.text
    assert "link.href=absoluteStatusUrl" in index_page.text


def test_release_metadata_and_twenty_file_copy_are_consistent():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["version"] == "3.7.50"
    assert health.json()["document_limit"] == 20
    assert health.headers["x-app-version"] == "3.7.50"
    assert health.json()["voice_max_seconds"] == 120
    assert health.json()["email_link_base_url"] == health.json()["public_base_url"]
    assert "voice_transcriptions_daily_limit" not in health.json()
    assert "voice_transcriptions_used_today" not in health.json()
    assert "ai_assistant_daily_limit" not in health.json()
    assert "ai_assistant_used_today" not in health.json()
    assert health.json()["openai_billing_ready"] is False

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

    privacy_ru = client.get("/privacy?lang=ru")
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


def test_pdf_document_analysis_uses_low_detail_data_url(monkeypatch):
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
        document_analysis_max_output_tokens=3000, document_pdf_detail="low",
    ))
    monkeypatch.setattr(module.httpx, "AsyncClient", FakeClient)
    case = valid_payload(); case["case_reference"] = "CTR-PDF"
    pdf = _make_pdf_bytes()
    asyncio.run(module.analyse_case_documents(case, [{
        "original_name": "invoice.pdf", "content_type": "application/pdf", "content_blob": pdf,
    }]))
    file_part = captured["body"]["input"][1]["content"][1]
    assert file_part["type"] == "input_file"
    assert file_part["file_data"].startswith("data:application/pdf;base64,")
    assert file_part["detail"] == "low"


def test_document_analysis_retries_temporary_provider_errors(monkeypatch):
    import asyncio
    import json
    from types import SimpleNamespace
    import app.document_analysis as module

    expected = {
        "readiness_score": 50, "summary": "Summary", "document_inventory": [],
        "readiness_factors": readiness_factors(
            "partial", "missing", "missing", "missing",
            "complete", "complete", "complete",
        ),
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
    pdf = _make_pdf_bytes()
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


def test_production_render_service_does_not_assume_unconnected_custom_domain(monkeypatch):
    from app.config import configured_public_base_url

    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://chinatraderesolve.onrender.com/")
    assert configured_public_base_url() == "https://chinatraderesolve.onrender.com"


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


def test_identical_document_is_not_added_twice_and_user_is_told():
    from app.db import get_case_by_public, list_case_documents

    created = client.post(
        "/api/applications",
        json=valid_payload(email="duplicate-content@example.com", preferred_language="Russian"),
        headers={"x-forwarded-for": "198.51.100.42"},
    ).json()
    content = _make_png_bytes()
    first = client.post(
        created["status_url"] + "/documents",
        data={"document_consent": "true"},
        files=[("files", ("supplier-chat.png", content, "image/png"))],
        follow_redirects=False,
        headers={"x-forwarded-for": "198.51.100.42"},
    )
    assert first.status_code == 303
    assert "upload_result=uploaded" in first.headers["location"]

    repeated = client.post(
        created["status_url"] + "/documents",
        data={"document_consent": "true"},
        files=[("files", ("supplier-chat-copy.png", content, "image/png"))],
        follow_redirects=False,
        headers={"x-forwarded-for": "198.51.100.42"},
    )
    assert repeated.status_code == 303
    assert "upload_result=duplicate" in repeated.headers["location"]
    page = client.get(repeated.headers["location"])
    assert "уже были загружены" in page.text
    assert "Документы успешно загружены" not in page.text

    reference, token = created["status_url"].rstrip("/").split("/")[-2:]
    case = get_case_by_public(reference, token)
    assert len(list_case_documents(case["id"])) == 1


def test_mixed_document_batch_reports_added_files_and_duplicates():
    from io import BytesIO
    from PIL import Image
    from app.db import get_case_by_public, list_case_documents

    def image_bytes(colour: str) -> bytes:
        output = BytesIO()
        Image.new("RGB", (3, 3), colour).save(output, format="PNG")
        return output.getvalue()

    created = client.post(
        "/api/applications",
        json=valid_payload(email="mixed-documents@example.com", preferred_language="English"),
        headers={"x-forwarded-for": "198.51.100.43"},
    ).json()
    first_content = image_bytes("red")
    client.post(
        created["status_url"] + "/documents",
        data={"document_consent": "true"},
        files=[("files", ("first.png", first_content, "image/png"))],
        follow_redirects=False,
        headers={"x-forwarded-for": "198.51.100.43"},
    )
    mixed = client.post(
        created["status_url"] + "/documents",
        data={"document_consent": "true"},
        files=[
            ("files", ("duplicate.png", first_content, "image/png")),
            ("files", ("second.png", image_bytes("blue"), "image/png")),
        ],
        follow_redirects=False,
        headers={"x-forwarded-for": "198.51.100.43"},
    )
    assert mixed.status_code == 303
    assert "upload_result=mixed" in mixed.headers["location"]
    page = client.get(mixed.headers["location"])
    assert "Documents uploaded successfully" in page.text
    assert "already uploaded" in page.text

    reference, token = created["status_url"].rstrip("/").split("/")[-2:]
    case = get_case_by_public(reference, token)
    assert len(list_case_documents(case["id"])) == 2


def test_document_upload_feedback_copy_is_complete_in_all_languages():
    from app.main import DOCUMENT_COPY, DOCUMENT_UPLOAD_ERROR_COPY

    required_errors = {
        "unsupported_type", "too_large", "empty_file", "invalid_image",
        "invalid_pdf", "encrypted_pdf", "pdf_pages", "total_pdf_pages",
        "max_documents", "consent", "rate_limited", "no_files",
        "analysis_running", "case_closed", "generic",
    }
    assert set(DOCUMENT_UPLOAD_ERROR_COPY) == set(DOCUMENT_COPY)
    for language in DOCUMENT_COPY:
        assert DOCUMENT_COPY[language]["duplicate"].strip()
        assert DOCUMENT_COPY[language]["uploading"].strip()
        assert DOCUMENT_COPY[language]["uploading_note"].strip()
        assert set(DOCUMENT_UPLOAD_ERROR_COPY[language]) == required_errors
        assert all(message.strip() for message in DOCUMENT_UPLOAD_ERROR_COPY[language].values())

    template = (Path(__file__).resolve().parents[1] / "app" / "templates" / "public_status.html").read_text()
    assert 'id="documentUploadClientError"' in template
    assert 'id="documentUploadLoading"' in template
    assert 'id="documentUploadButton"' in template
    assert 'role="status"' in template
    assert "uploadForm.setAttribute('aria-busy', 'true')" in template
    assert "button.disabled = true" in template
    assert "showUploadError" in template
    assert "alert('Maximum" not in template


def test_document_upload_progress_is_rendered_in_selected_language():
    created = client.post(
        "/api/applications",
        json=valid_payload(email="upload-progress@example.com", preferred_language="Russian"),
        headers={"x-forwarded-for": "198.51.100.245"},
    ).json()
    page = client.get(created["status_url"])
    assert page.status_code == 200
    assert 'id="documentUploadLoading"' in page.text
    assert 'id="documentUploadButton"' in page.text
    assert "Загрузка документов…" in page.text
    assert "Не закрывайте страницу" in page.text
    assert 'aria-live="polite"' in page.text


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
    assert blocked_upload.status_code == 303
    assert "upload_issue=analysis_running" in blocked_upload.headers["location"]
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
    assert f"/documents/{documents[0]['id']}/delete" not in page.text
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

    import pikepdf
    encrypted_output = BytesIO()
    with pikepdf.Pdf.new() as encrypted_pdf:
        encrypted_pdf.add_blank_page(page_size=(595, 842))
        encrypted_pdf.save(
            encrypted_output,
            encryption=pikepdf.Encryption(user="secret", owner="owner-secret", R=6),
        )
    encrypted = encrypted_output.getvalue()
    with pytest.raises(DocumentValidationError, match="Password-protected"):
        asyncio.run(prepare_upload(UploadFile(BytesIO(encrypted), filename="encrypted.pdf")))

    unsafe_pdfs = {
        "active.pdf": _make_unsafe_pdf_bytes("javascript"),
        "compressed-attachment.pdf": _make_unsafe_pdf_bytes("attachment"),
    }
    for filename, unsafe_pdf in unsafe_pdfs.items():
        with pytest.raises(DocumentValidationError, match="active or embedded"):
            asyncio.run(prepare_upload(UploadFile(BytesIO(unsafe_pdf), filename=filename)))



def test_application_ai_triage_has_short_response_budget(monkeypatch):
    import asyncio
    import time
    import app.main as module

    async def slow_triage(_payload):
        await asyncio.sleep(1.0)
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
    # Keep a wide margin for loaded CI runners while still proving that the
    # one-second provider call was cancelled promptly.
    assert elapsed < 0.5
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
    original_billing_ready = module.settings.openai_billing_ready
    original_key = module.settings.openai_api_key
    original_model = module.settings.openai_document_model
    object.__setattr__(module.settings, "openai_billing_ready", True)
    object.__setattr__(module.settings, "enable_document_analysis", True)
    object.__setattr__(module.settings, "openai_api_key", "test-key")
    object.__setattr__(module.settings, "openai_document_model", "test-model")
    try:
        result = asyncio.run(module.analyse_case_documents(
            {"case_reference": "CTR-TEST", "preferred_language": "English"},
            [{"original_name": "invoice.pdf", "content_type": "application/pdf", "content_blob": _make_pdf_bytes()}],
        ))
    finally:
        object.__setattr__(module.settings, "openai_billing_ready", original_billing_ready)
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
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://[::1")
    assert configured_public_base_url() == "https://safe-example.onrender.com"
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.com:bad")
    assert configured_public_base_url() == "https://safe-example.onrender.com"
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://remote-example.test")
    assert configured_public_base_url() == "https://safe-example.onrender.com"
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://localhost:8000/")
    assert configured_public_base_url() == "http://localhost:8000"


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
            "openai_billing_ready": True,
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
    assert statements[0] == "SELECT pg_advisory_xact_lock(1129601362)"
    audit_statement = next(
        statement for statement in statements
        if "CREATE TABLE IF NOT EXISTS audit_log" in statement
    )
    assert audit_statement.lower().count("created_at text not null") == 1


def test_postgres_schema_initialization_lock_precedes_all_ddl(monkeypatch):
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
        statements.append(" ".join(query.split()))
        return Cursor()

    monkeypatch.setattr(db, "using_postgres", lambda: True)
    monkeypatch.setattr(db, "transaction", fake_transaction)
    monkeypatch.setattr(db, "execute", fake_execute)
    monkeypatch.setattr(db, "_ensure_notification_retry_columns", lambda _conn: None)
    monkeypatch.setattr(db, "_ensure_document_analysis_run_token", lambda _conn: None)
    monkeypatch.setattr(db, "_ensure_case_document_page_count", lambda _conn: None)

    db.init_db()
    assert statements[0].startswith("SELECT pg_advisory_xact_lock(")
    assert all("CREATE TABLE" not in statement for statement in statements[:1])
    assert any("CREATE TABLE IF NOT EXISTS cases" in statement for statement in statements[1:])


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


def test_email_bridge_accepts_https_and_loopback_http_only():
    import app.notifications as notifications

    original = notifications.settings.email_bridge_url
    try:
        for value in (
            "https://bridge.example.test/send?channel=email",
            "http://localhost:8080/send",
            "http://127.0.0.1:8080/send",
            "http://[::1]:8080/send",
        ):
            object.__setattr__(notifications.settings, "email_bridge_url", value)
            assert notifications.safe_email_bridge_url() == value

        for value in (
            "file:///etc/passwd",
            "http://bridge.example.test/send",
            "https://user:password@bridge.example.test/send",
            "javascript:alert(1)",
            "https://[::1",
            "https://bridge.example.test:bad/send",
            "https://bridge.example.test/send\nX-Test: injected",
        ):
            object.__setattr__(notifications.settings, "email_bridge_url", value)
            assert notifications.safe_email_bridge_url() is None
    finally:
        object.__setattr__(notifications.settings, "email_bridge_url", original)


def test_invalid_email_bridge_is_not_reported_as_configured():
    import app.notifications as notifications

    original_url = notifications.settings.email_bridge_url
    original_secret = notifications.settings.email_bridge_secret
    original_host = notifications.settings.smtp_host
    try:
        object.__setattr__(notifications.settings, "email_bridge_url", "file:///etc/passwd")
        object.__setattr__(notifications.settings, "email_bridge_secret", "configured-secret")
        object.__setattr__(notifications.settings, "smtp_host", None)
        assert notifications.email_delivery_is_configured() is False
    finally:
        object.__setattr__(notifications.settings, "email_bridge_url", original_url)
        object.__setattr__(notifications.settings, "email_bridge_secret", original_secret)
        object.__setattr__(notifications.settings, "smtp_host", original_host)


def test_invalid_email_bridge_is_rejected_before_network_access(monkeypatch):
    import pytest
    import app.notifications as notifications

    original_url = notifications.settings.email_bridge_url
    original_secret = notifications.settings.email_bridge_secret
    called = False

    def unexpected_network_access(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("urlopen must not be called for an unsafe URL")

    monkeypatch.setattr(notifications, "urlopen", unexpected_network_access)
    object.__setattr__(notifications.settings, "email_bridge_url", "file:///etc/passwd")
    object.__setattr__(notifications.settings, "email_bridge_secret", "configured-secret")
    try:
        with pytest.raises(RuntimeError, match="not configured"):
            notifications._deliver_via_bridge(
                {"recipient": "test@example.com", "subject": "Test", "body": "Body"}
            )
    finally:
        object.__setattr__(notifications.settings, "email_bridge_url", original_url)
        object.__setattr__(notifications.settings, "email_bridge_secret", original_secret)
    assert called is False


def test_support_url_rejects_credentials_unsafe_schemes_and_whitespace():
    import app.main as module

    original = module.settings.support_url
    try:
        for value in (
            "https://example.com/support",
            "http://localhost:8000/support",
            "http://127.0.0.1:8000/support",
            "http://[::1]:8000/support",
        ):
            object.__setattr__(module.settings, "support_url", value)
            assert module.safe_support_url() == value

        for value in (
            "http://example.com/support",
            "file:///etc/passwd",
            "https://user:password@example.com/support",
            "https://[::1",
            "https://example.com:bad/support",
            "https://example.com/sup port",
        ):
            object.__setattr__(module.settings, "support_url", value)
            assert module.safe_support_url() is None
    finally:
        object.__setattr__(module.settings, "support_url", original)


def test_paypal_support_url_is_restricted_to_verified_payment_links():
    import app.main as module

    original = module.settings.paypal_support_url
    try:
        object.__setattr__(
            module.settings,
            "paypal_support_url",
            "https://www.paypal.com/ncp/payment/THKQMZDRRNHQ8",
        )
        assert (
            module.safe_paypal_support_url()
            == "https://www.paypal.com/ncp/payment/THKQMZDRRNHQ8"
        )

        for value in (
            "http://www.paypal.com/ncp/payment/THKQMZDRRNHQ8",
            "https://paypal.com/ncp/payment/THKQMZDRRNHQ8",
            "https://www.paypal.com.example/ncp/payment/THKQMZDRRNHQ8",
            "https://www.paypal.com/signin",
            "https://user:password@www.paypal.com/ncp/payment/THKQMZDRRNHQ8",
            "https://www.paypal.com/ncp/payment/THKQMZDRRNHQ8?next=bad",
        ):
            object.__setattr__(module.settings, "paypal_support_url", value)
            assert module.safe_paypal_support_url() is None
    finally:
        object.__setattr__(module.settings, "paypal_support_url", original)


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
    assert messages[0]["status"] == 303
    headers = dict(messages[0]["headers"])
    assert b"upload_issue=too_large" in headers[b"location"]


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
        "readiness_factors": readiness_factors(
            "partial", "missing", "missing", "missing",
            "complete", "complete", "complete",
        ),
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
        "readiness_factors": readiness_factors(
            "partial", "missing", "partial", "complete",
            "complete", "not_applicable", "not_applicable",
        ),
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


def test_document_report_always_explains_score_with_all_seven_factors():
    import app.document_analysis as module

    parsed = {
        "readiness_score": 87,
        "readiness_factors": [],
        "summary": "Резюме.",
        "document_inventory": [],
        "timeline": [],
        "key_evidence": [],
        "contradictions": [],
        "missing_evidence": [],
        "risk_flags": [],
        "recommended_next_steps": [],
        "human_review_note": "Проверка человеком.",
    }

    result = module._postprocess_report(parsed, "Russian")

    assert result["readiness_score"] == 0
    assert len(result["readiness_factors"]) == 7
    assert {item["factor"] for item in result["readiness_factors"]} == set(
        module.READINESS_FACTOR_WEIGHTS
    )
    assert all(item["status"] == "missing" for item in result["readiness_factors"])
    assert module.DOCUMENT_ANALYSIS_SCHEMA["properties"]["readiness_factors"]["minItems"] == 7
    assert module.DOCUMENT_ANALYSIS_SCHEMA["properties"]["readiness_factors"]["maxItems"] == 7


def test_document_report_all_not_applicable_factors_have_zero_score():
    import app.document_analysis as module

    parsed = {
        "readiness_score": 99,
        "readiness_factors": [
            {
                "factor": factor,
                "status": "not_applicable",
                "explanation": "Не применимо.",
            }
            for factor in module.READINESS_FACTOR_WEIGHTS
        ],
        "summary": "Резюме.",
        "document_inventory": [],
        "timeline": [],
        "key_evidence": [],
        "contradictions": [],
        "missing_evidence": [],
        "risk_flags": [],
        "recommended_next_steps": [],
        "human_review_note": "Проверка человеком.",
    }

    result = module._postprocess_report(parsed, "Russian")

    assert result["readiness_score"] == 0
    assert len(result["readiness_factors"]) == 7



def test_document_report_deduplication_preserves_opposite_statements():
    import app.document_analysis as module

    values = [
        "Оплата подтверждена документами.",
        "Оплата не подтверждена документами.",
        "Поставщик подтвердил натуральную кожу.",
        "Поставщик не подтвердил натуральную кожу.",
    ]
    assert module._dedupe_text_items(values, 8) == values


def test_document_report_softens_unverified_authenticity_and_illegality_claims_in_all_languages():
    import app.document_analysis as module

    examples = {
        "Russian": [
            ("Поддельный сертификат", "Документ с неподтверждённой подлинностью"),
            ("Незаконный документ", "Материал или действие, правовой статус которого требует проверки"),
        ],
        "English": [
            ("Forged certificate", "Document of unverified authenticity"),
            ("Illegal document", "Matter whose legal status requires verification"),
        ],
        "French": [
            ("Faux certificat", "Document dont l’authenticité n’est pas vérifiée"),
            ("Document illégal", "Élément dont le statut juridique doit être vérifié"),
        ],
        "German": [
            ("Gefälschtes Zertifikat", "Dokument mit ungeprüfter Echtheit"),
            ("Illegales Dokument", "Sachverhalt, dessen rechtlicher Status geprüft werden muss"),
        ],
        "Spanish": [
            ("Certificado falsificado", "Documento cuya autenticidad no está verificada"),
            ("Documento ilegal", "Asunto cuya situación jurídica requiere verificación"),
        ],
        "Serbian": [
            ("Falsifikovan sertifikat", "Dokument čija autentičnost nije potvrđena"),
            ("Nezakonit dokument", "Pitanje čiji pravni status zahteva proveru"),
        ],
    }
    for language, pairs in examples.items():
        for source, expected in pairs:
            assert module._soften_unverified_claims(source, language) == expected


def test_document_report_softens_inventory_prose_but_preserves_exact_quotations():
    import app.document_analysis as module

    quoted = 'Поставщик написал: «Это поддельный сертификат»; поддельный документ не подтверждён экспертизой.'
    softened = module._soften_unverified_claims(quoted, "Russian")
    assert '«Это поддельный сертификат»' in softened
    assert 'документ с неподтверждённой подлинностью не подтверждён экспертизой' in softened

    parsed = {
        "readiness_score": 0,
        "readiness_factors": [],
        "summary": "Резюме.",
        "document_inventory": [{
            "filename": "certificate.png",
            "document_type": "Поддельный сертификат",
            "language": "Russian",
            "date_or_period": "Дата не видна",
            "key_content": 'Продавец написал: “This is a fake certificate”; поддельный документ не проверен.',
            "readability": "clear",
        }],
        "timeline": [],
        "key_evidence": [],
        "contradictions": [],
        "missing_evidence": [],
        "risk_flags": [],
        "recommended_next_steps": [],
        "human_review_note": "Проверка человеком.",
    }
    result = module._postprocess_report(parsed, "Russian")
    inventory = result["document_inventory"][0]
    assert inventory["document_type"] == "Документ с неподтверждённой подлинностью"
    assert '“This is a fake certificate”' in inventory["key_content"]
    assert "документ с неподтверждённой подлинностью не проверен" in inventory["key_content"]


def test_document_report_date_range_uses_earliest_visible_day_and_not_wrong_model_hint():
    import app.document_analysis as module

    assert module._derive_sort_date("16–17 апреля 2025") == "2025-04-16"
    parsed = {
        "readiness_score": 50,
        "readiness_factors": [],
        "summary": "Резюме.",
        "document_inventory": [],
        "timeline": [
            {
                "date": "16–17 апреля 2025",
                "sort_date": "2025-04-17",
                "event": "Диапазон дат",
                "source_files": ["a.png"],
                "confidence": "high",
            },
            {
                "date": "17 апреля 2025",
                "sort_date": "2025-04-16",
                "event": "Следующее событие",
                "source_files": ["a.png"],
                "confidence": "high",
            },
        ],
        "key_evidence": [],
        "contradictions": [],
        "missing_evidence": [],
        "risk_flags": [],
        "recommended_next_steps": [],
        "human_review_note": "Проверка человеком.",
    }
    result = module._postprocess_report(parsed, "Russian")
    assert [item["event"] for item in result["timeline"]] == ["Диапазон дат", "Следующее событие"]

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


def test_document_date_placeholder_preserves_visible_date_with_other_missing_detail():
    import app.document_analysis as module

    value = "26 May 2026, time not visible"
    assert module._normalise_date_placeholder(value, "English") == value
    assert module._derive_sort_date(value) == "2026-05-26"


def test_document_date_placeholder_preserves_partial_month_or_year():
    import app.document_analysis as module

    examples = [
        ("March 2025, day not visible", "English", "2025-03-01"),
        ("2025, exact date not visible", "English", "2025-01-01"),
        ("март 2025, точная дата не указана", "Russian", "2025-03-01"),
        ("mars 2025", "French", "2025-03-01"),
        ("März 2025", "German", "2025-03-01"),
        ("mayo de 2025", "Spanish", "2025-05-01"),
        ("maj 2025", "Serbian", "2025-05-01"),
        ("мај 2025", "Serbian", "2025-05-01"),
        ("2025-03", "English", "2025-03-01"),
        ("03/2025", "English", "2025-03-01"),
    ]
    for visible, language, expected_sort_date in examples:
        assert module._normalise_date_placeholder(visible, language) == visible
        assert module._derive_sort_date(visible) == expected_sort_date


def test_document_date_parser_supports_real_localised_formats():
    import app.document_analysis as module

    examples = {
        "22. März 2025": "2025-03-22",
        "22 de mayo de 2025": "2025-05-22",
        "22 maja 2025": "2025-05-22",
        "22. маја 2025.": "2025-05-22",
        "16.–17. Mai 2025": "2025-05-16",
        "16–17 de mayo de 2025": "2025-05-16",
    }
    for visible, expected in examples.items():
        assert module._derive_sort_date(visible) == expected

def test_document_date_parser_supports_all_interface_languages():
    import app.document_analysis as module

    examples = {
        "26 mars 2025": "2025-03-26",
        "26 März 2025": "2025-03-26",
        "26 marzo 2025": "2025-03-26",
        "26 mart 2025": "2025-03-26",
        "26 март 2025": "2025-03-26",
    }
    for visible, expected in examples.items():
        assert module._derive_sort_date(visible) == expected


def test_triage_never_auto_declines_reported_evidence_misconduct():
    from app.schemas import ApplicationCreate
    from app.triage import rules_triage

    payload = ApplicationCreate(**valid_payload(
        preferred_language="Russian",
        description=(
            "Я отказался подделывать доказательства. Продавец просил удалить переписку, "
            "но я сохранил оригинальный договор, инвойс, сообщения и фотографии товара."
        ),
    ))
    result = rules_triage(payload)
    assert result.decision == "human_review"
    assert result.decision != "declined"
    assert "автоматически отклонена" in result.public_message


def test_triage_amount_thresholds_are_currency_aware():
    from app.schemas import ApplicationCreate
    from app.triage import rules_triage

    description = (
        "The written order and invoice specify leather. Supplier messages confirm it, "
        "but delivery photographs show another material and we request a partial refund."
    )
    rsd = rules_triage(ApplicationCreate(**valid_payload(
        amount_in_dispute="50,000 RSD", order_value="50,000 RSD", description=description,
    )))
    usd = rules_triage(ApplicationCreate(**valid_payload(
        amount_in_dispute="50,000 USD", order_value="50,000 USD", description=description,
    )))
    assert "high_value_dispute" not in rsd.risk_flags
    assert "high_value_dispute" in usd.risk_flags
    assert usd.decision == "human_review"


def test_wallet_checksum_validation_rejects_shape_only_addresses():
    from app.main import _valid_bitcoin_bech32, _valid_eth

    assert _valid_bitcoin_bech32("bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh") is True
    assert _valid_bitcoin_bech32("bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wla") is False
    assert _valid_eth("0x69ACE684f28B0A66157aB62aD06e93761a713c6b") is True
    assert _valid_eth("0x69ace684f28b0a66157ab62ad06e93761a713c6b") is False


def test_daily_document_analysis_budget_is_database_backed():
    import pytest
    from app.db import (
        DailyAnalysisLimitError,
        claim_document_analysis,
        get_case_by_public,
        get_daily_analysis_usage,
        set_document_analysis_status,
    )

    cases = []
    for index in range(2):
        created = client.post(
            "/api/applications",
            json=valid_payload(email=f"budget-{index}@example.com"),
            headers={"x-forwarded-for": f"203.0.113.{180 + index}"},
        ).json()
        upload = client.post(
            created["status_url"] + "/documents",
            data={"document_consent": "true"},
            files=[("files", (f"evidence-{index}.png", _make_png_bytes(), "image/png"))],
            headers={"x-forwarded-for": f"203.0.113.{180 + index}"},
            follow_redirects=False,
        )
        assert upload.status_code == 303
        reference, token = created["status_url"].rstrip("/").split("/")[-2:]
        cases.append(get_case_by_public(reference, token))

    baseline = get_daily_analysis_usage()
    run_token = claim_document_analysis(
        cases[0]["id"], "test-model", actor="test", document_count=1,
        max_daily_analyses=baseline + 1,
    )
    assert run_token
    set_document_analysis_status(
        cases[0]["id"], "failed", "test-model", "test cleanup",
        expected_run_token=run_token,
    )
    with pytest.raises(DailyAnalysisLimitError):
        claim_document_analysis(
            cases[1]["id"], "test-model", actor="test", document_count=1,
            max_daily_analyses=baseline + 1,
        )


def test_personal_and_global_daily_ai_budgets_are_atomic():
    import pytest
    from app.db import DailyUsageLimitError, claim_daily_usage_for_subject

    name = "assistant_budget_test"
    subject_a = "a" * 32
    subject_b = "b" * 32
    subject_c = "c" * 32

    assert claim_daily_usage_for_subject(name, subject_a, 1, 2) == (1, 1)
    with pytest.raises(DailyUsageLimitError):
        claim_daily_usage_for_subject(name, subject_a, 1, 2)
    # The failed personal claim above must not consume the global counter.
    assert claim_daily_usage_for_subject(name, subject_b, 1, 2) == (1, 2)
    with pytest.raises(DailyUsageLimitError):
        claim_daily_usage_for_subject(name, subject_c, 1, 2)


def test_document_analysis_has_per_case_and_global_budgets():
    import pytest
    from app.db import (
        DailyAnalysisLimitError,
        claim_document_analysis,
        get_case_by_public,
        get_daily_analysis_usage,
        set_document_analysis_status,
    )

    created = client.post(
        "/api/applications",
        json=valid_payload(email="per-case-budget@example.com"),
        headers={"x-forwarded-for": "203.0.113.199"},
    ).json()
    upload = client.post(
        created["status_url"] + "/documents",
        data={"document_consent": "true"},
        files=[("files", ("evidence.png", _make_png_bytes(), "image/png"))],
        follow_redirects=False,
    )
    assert upload.status_code == 303
    reference, token = created["status_url"].rstrip("/").split("/")[-2:]
    case = get_case_by_public(reference, token)
    baseline = get_daily_analysis_usage()

    run_token = claim_document_analysis(
        case["id"], "test-model", actor="test", document_count=1,
        max_daily_analyses_per_case=1,
        max_daily_analyses_global=baseline + 10,
    )
    assert run_token
    set_document_analysis_status(
        case["id"], "failed", "test-model", "test cleanup",
        expected_run_token=run_token,
    )
    with pytest.raises(DailyAnalysisLimitError):
        claim_document_analysis(
            case["id"], "test-model", actor="test", document_count=1,
            allow_completed=True,
            max_daily_analyses_per_case=1,
            max_daily_analyses_global=baseline + 10,
        )


def test_private_link_can_revoke_ai_consent_and_delete_case():
    from app.db import get_case_by_public, list_case_documents

    created = client.post(
        "/api/applications",
        json=valid_payload(email="privacy-controls@example.com"),
        headers={"x-forwarded-for": "203.0.113.190"},
    ).json()
    status_url = created["status_url"]
    upload = client.post(
        status_url + "/documents",
        data={"document_consent": "true"},
        files=[("files", ("privacy.png", _make_png_bytes(), "image/png"))],
        headers={"x-forwarded-for": "203.0.113.190"},
        follow_redirects=False,
    )
    assert upload.status_code == 303
    revoke = client.post(
        status_url + "/ai-consent/revoke",
        data={"confirm_revoke": "true"},
        headers={"x-forwarded-for": "203.0.113.190"},
        follow_redirects=False,
    )
    assert revoke.status_code == 303
    reference, token = status_url.rstrip("/").split("/")[-2:]
    case = get_case_by_public(reference, token)
    assert case["ai_consent"] == 0
    assert len(list_case_documents(case["id"])) == 1

    deleted = client.post(
        status_url + "/delete",
        data={"confirm_delete": "true"},
        headers={"x-forwarded-for": "203.0.113.190"},
        follow_redirects=False,
    )
    assert deleted.status_code == 303
    assert client.get(status_url).status_code == 404
    assert get_case_by_public(reference, token) is None


def test_turnstile_failure_blocks_application_before_storage(monkeypatch):
    import app.main as module

    async def reject(_token, _request):
        return False

    monkeypatch.setattr(module, "verify_turnstile", reject)
    response = client.post(
        "/api/applications",
        json=valid_payload(email="turnstile-blocked@example.com"),
        headers={"x-forwarded-for": "203.0.113.191"},
    )
    assert response.status_code == 400


def test_privacy_route_exposes_configuration_status():
    response = client.get("/privacy?lang=en")
    assert response.status_code == 200
    assert "DATA_CONTROLLER_ADDRESS" not in response.text
    assert "This local preview is not accepting public applications" in response.text
    health = client.get("/health").json()
    assert health["privacy_configuration_complete"] is False


def test_container_healthcheck_uses_liveness_endpoint_not_readiness_gate():
    dockerfile = (Path(__file__).resolve().parent.parent / "Dockerfile").read_text(encoding="utf-8")
    healthcheck_line = next(line for line in dockerfile.splitlines() if line.startswith("HEALTHCHECK "))
    assert "/health" in healthcheck_line
    assert "/ready" not in healthcheck_line
    assert "urlopen('http://127.0.0.1:'" in healthcheck_line


def test_launch_readiness_endpoint_is_fail_closed_by_default():
    response = client.get("/ready")
    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["checks"]["administrator_security"] is True
    assert payload["checks"]["privacy_identity"] is False


def test_launch_readiness_endpoint_returns_200_when_all_checks_pass(monkeypatch):
    import app.main as module

    monkeypatch.setattr(module, "launch_readiness_checks", lambda: {
        "administrator_security": True,
        "privacy_identity": True,
        "https_public_url": True,
        "email_delivery": True,
        "bot_protection": True,
        "database_storage": True,
    })
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_robots_and_sitemap_follow_launch_readiness(monkeypatch):
    import app.main as module

    blocked = client.get("/robots.txt")
    assert blocked.status_code == 200
    assert blocked.text == "User-agent: *\nDisallow: /\n"

    monkeypatch.setattr(module, "search_indexing_is_ready", lambda: True)
    allowed = client.get("/robots.txt")
    assert allowed.status_code == 200
    assert "Allow: /" in allowed.text
    assert "Disallow: /admin" in allowed.text
    assert "Disallow: /api/" in allowed.text
    assert "/sitemap.xml" in allowed.text

    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    assert sitemap.headers["content-type"].startswith("application/xml")
    assert "<loc>http://127.0.0.1:8000/</loc>" in sitemap.text
    assert "<loc>http://127.0.0.1:8000/privacy</loc>" in sitemap.text
    assert "?lang=en" in sitemap.text
    assert 'xmlns:xhtml="http://www.w3.org/1999/xhtml"' in sitemap.text
    assert '<lastmod>2026-07-26</lastmod>' in sitemap.text
    assert "/static/terms.html" not in sitemap.text
    assert "/admin" not in sitemap.text
    assert "/case/" not in sitemap.text


def test_form_engagement_closes_open_ai_chat_without_stealing_focus():
    page = client.get("/")
    assert page.status_code == 200
    assert "new CustomEvent('ctr:form-engaged')" in page.text
    assert "if(!aiChatPanel.hidden)closeAiChat(false)" in page.text


def test_launch_readiness_fails_closed_when_database_is_unavailable(monkeypatch):
    import app.main as module

    def unavailable():
        raise OSError("database unavailable")

    monkeypatch.setattr(module, "connect", unavailable)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["database_storage"] is False


def test_health_remains_live_when_database_is_unavailable(monkeypatch):
    import app.main as module

    monkeypatch.setattr(module, "database_is_available", lambda: False)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["readiness_checks"]["database_storage"] is False
    assert "document_analysis_used_today" not in response.json()


def test_public_launch_mode_blocks_incomplete_site_without_leaking_config(monkeypatch):
    import app.main as module

    original = module.settings.public_launch_mode
    object.__setattr__(module.settings, "public_launch_mode", True)
    monkeypatch.setattr(module, "public_launch_is_ready", lambda: False)
    try:
        home = client.get("/")
        privacy = client.get("/privacy")
        support = client.get("/support")
        paypal_qr = client.get("/support/paypal-qr.png")
        crypto_qr = client.get("/support/qr/btc.png")
        submission = client.post(
            "/api/applications",
            json=valid_payload(email="blocked-launch@example.com"),
            headers={"x-forwarded-for": "192.0.2.240"},
        )
        assert home.status_code == privacy.status_code == support.status_code == 503
        assert paypal_qr.status_code == crypto_qr.status_code == submission.status_code == 503
        for response in (home, privacy, support, paypal_qr, crypto_qr):
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["retry-after"] == "300"
        assert "DATA_CONTROLLER" not in home.text
        assert "TURNSTILE" not in home.text
        assert "paypal.com" not in support.text.lower()
        assert "1BafLn5NLdKwyv8rvuPJVZUKwQnHyuMej9" not in support.text
        assert paypal_qr.headers.get("content-type") != "image/png"
        assert crypto_qr.headers.get("content-type") != "image/png"
    finally:
        object.__setattr__(module.settings, "public_launch_mode", original)


def test_public_launch_mode_exposes_site_and_support_after_readiness(monkeypatch):
    import app.main as module

    original = module.settings.public_launch_mode
    object.__setattr__(module.settings, "public_launch_mode", True)
    monkeypatch.setattr(module, "public_launch_is_ready", lambda: True)
    try:
        for path in ("/", "/privacy", "/support", "/support/paypal-qr.png", "/support/qr/btc.png"):
            response = client.get(path)
            assert response.status_code == 200, path
        assert client.get("/support/paypal-qr.png").headers["content-type"] == "image/png"
        assert client.get("/support/qr/btc.png").headers["content-type"] == "image/png"
    finally:
        object.__setattr__(module.settings, "public_launch_mode", original)


def test_home_exposes_truthful_features_accessibility_and_private_link_ui():
    response = client.get("/")
    assert response.status_code == 200
    for expected in (
        'href="#main-content"',
        '<main id="main-content">',
        'rel="canonical"',
        'rel="icon"',
        'application/ld+json',
        'value="Other or multiple issues"',
        'id="privateStatusUrl"',
        'id="copyStatusLink"',
        'class="btn dark" data-i18n="view_case_status"',
        '.status-link-row .btn{color:#0f172a;background:#fff;border-color:#0f766e}',
        'aria-modal="true"',
    ):
        assert expected in response.text


def test_targeted_landing_copy_is_shorter_precise_and_transparent():
    response = client.get("/")
    assert response.status_code == 200
    assert "Что входит в предварительную оценку материалов" in response.text
    assert "Подайте заявку на предварительную оценку материалов" in response.text
    assert "Что входит в бесплатный анализ" not in response.text
    assert "Отправьте дело на бесплатный анализ" not in response.text
    assert 'class="final-cta"' not in response.text
    assert 'class="grid g3 trust-principles"' not in response.text
    assert 'id="submitSummaryTitle"' in response.text
    assert "Документы на этом шаге не передаются" in response.text
    assert "в течение 2 рабочих дней" in response.text
    assert 'data-i18n="choose_text"' not in response.text
    assert '#faq .wrap{display:grid;grid-template-columns:1fr 1fr' in response.text

    assert 'id="submitBtn" type="submit"' in response.text
    assert 'aria-disabled="true"' in response.text
    assert 'function applicationReady()' in response.text
    assert "field===descriptionField)return field.value.trim().length>=50" in response.text
    assert "requiredConsentInputs.every(input=>input.checked)" in response.text

    assert "aiLauncherButton.classList.toggle('is-compact',formInView)" in response.text
    assert '.ai-chat-launcher.is-compact{width:52px;height:52px' in response.text
    assert '@media(max-width:700px){.ai-chat-launcher{right:14px;bottom:calc(82px + env(safe-area-inset-bottom));width:52px;height:52px' in response.text
    assert '.ai-chat-launcher .launcher-label{position:absolute!important;width:1px!important;height:1px!important' in response.text
    assert '.mobile{display:flex;position:fixed;left:4%;right:auto;bottom:calc(14px + env(safe-area-inset-bottom))' in response.text

    sample = client.get("/static/sample_case_assessment.html")
    assert sample.status_code == 200
    assert 'class="report-head"' in sample.text
    assert 'class="summary-grid"' in sample.text
    assert 'class="table-wrap"' in sample.text


def test_case_status_explains_progress_attention_and_private_access():
    created = client.post(
        "/api/applications",
        json=valid_payload(email="progress-page@example.com", preferred_language="Russian"),
        headers={"x-forwarded-for": "192.0.2.241"},
    ).json()
    page = client.get(created["status_url"])
    assert page.status_code == 200
    for expected in (
        "Ход рассмотрения",
        "Уровень внимания",
        "а не вероятность успеха",
        "Ваш следующий шаг",
        "Последнее обновление",
        "Приватная ссылка дела",
        "Скачать памятку доступа",
        'name="robots" content="noindex,nofollow"',
    ):
        assert expected in page.text

    reference, token = created["status_url"].rstrip("/").split("/")[-2:]
    note = client.get(f"/case/{reference}/{token}/access.txt")
    assert note.status_code == 200
    assert "attachment" in note.headers["content-disposition"]
    assert created["status_url"] in note.text
    assert client.get(f"/case/{reference}/wrong-token/access.txt").status_code == 404


def test_disabled_document_analysis_is_disclosed_before_upload():
    created = client.post(
        "/api/applications",
        json=valid_payload(email="manual-review-disclosure@example.com"),
        headers={"x-forwarded-for": "192.0.2.242"},
    ).json()
    page = client.get(created["status_url"])
    assert "Automatic document analysis is temporarily unavailable" in page.text


def test_application_response_reports_email_delivery_capability():
    response = client.post(
        "/api/applications",
        json=valid_payload(email="email-capability@example.com"),
        headers={"x-forwarded-for": "192.0.2.243"},
    )
    assert response.status_code == 201
    assert response.json()["email_delivery_configured"] is False


def test_seo_home_metadata_and_language_alternates():
    page = client.get("/?lang=en")
    assert page.status_code == 200
    assert '<html lang="en">' in page.text
    assert "help with disputes involving Chinese suppliers" in page.text
    assert 'hreflang="ru"' in page.text
    assert 'twitter:card" content="summary_large_image"' in page.text
    assert 'hreflang="x-default" href="http://127.0.0.1:8000/"' in page.text
    assert "/static/social-preview.png" in page.text
    assert '"logo": "http://127.0.0.1:8000/static/logo-512.png"' in page.text


def test_public_guides_and_sitemap_are_indexable():
    expected = {
        "en": "Practical guides for supplier disputes",
        "ru": "Практические руководства",
        "fr": "Guides pratiques",
        "de": "Praktische Leitfäden",
        "es": "Guías prácticas",
        "sr": "Praktični vodiči",
    }
    related_labels = (
        "Related guides", "Другие руководства", "Guides associés",
        "Weitere Ratgeber", "Guías relacionadas", "Povezani vodiči",
    )
    for language, fragment in expected.items():
        hub = client.get(f"/{language}/guides")
        assert hub.status_code == 200
        assert fragment in hub.text
        guide = client.get(f"/{language}/guides/alibaba-dispute-evidence")
        assert guide.status_code == 200
        assert f'<html lang="{language}">' in guide.text
        assert f'hreflang="{language}"' in guide.text
        assert 'datePublished' in guide.text
        assert '/static/logo-512.png' in guide.text
        assert any(label in guide.text for label in related_labels)
    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    assert "/fr/guides/alibaba-dispute-evidence" in sitemap.text
    assert "/de/guides/organize-dispute-documents" in sitemap.text
    assert "/es/guides/product-quality-dispute" in sitemap.text
    assert "/sr/guides/supplier-not-shipped" in sitemap.text
    assert 'hreflang="x-default"' in sitemap.text

def test_indexnow_key_file():
    response = client.get("/indexnow/a0d2be8a24fd4d8798f0af9d9a8e2a72.txt")
    assert response.status_code == 200
    assert response.text == "a0d2be8a24fd4d8798f0af9d9a8e2a72"


def test_campaign_attribution_is_sanitized_and_visible_to_admin():
    response = client.post(
        "/api/applications",
        json=valid_payload(
            email="campaign@example.com",
            utm_source=" reddit\n ",
            utm_medium="community",
            utm_campaign="launch",
            landing_path="https://evil.example/en/guides?lang=en&utm_source=reddit&secret=drop-me#fragment",
            referrer="https://www.reddit.com/r/Alibaba/?private=query",
        ),
    )
    assert response.status_code == 201

    from app.db import get_audit, get_case_by_public
    reference, token = response.json()["status_url"].rstrip("/").split("/")[-2:]
    case = get_case_by_public(reference, token)
    created_event = next(item for item in get_audit(case["id"]) if item["event_type"] == "application_created")
    details = json.loads(created_event["details_json"])
    assert details["utm_source"] == "reddit"
    assert details["landing_path"] == "/en/guides?lang=en&utm_source=reddit"
    assert details["referrer"] == "https://www.reddit.com"

    client.post("/admin/login", data={"token": "test-admin-token-abcdefghijklmnopqrstuvwxyz"})
    dashboard = client.get("/admin")
    assert "Источники заявок" in dashboard.text
    assert "reddit" in dashboard.text
    detail = client.get(f"/admin/case/{case['id']}")
    assert "Источник обращения" in detail.text
    assert "https://www.reddit.com" in detail.text
    assert "private=query" not in detail.text



def test_tracking_disclosure_and_legal_search_visibility():
    privacy = client.get("/privacy?lang=ru")
    assert privacy.status_code == 200
    assert "метки рекламной кампании" in privacy.text
    assert "какие публикации и каналы" in privacy.text
    for path in ("/static/terms.html", "/static/refund.html", "/static/ai-notice.html", "/static/disclaimer.html"):
        page = client.get(path)
        assert page.status_code == 200
        assert 'name="robots" content="noindex,follow"' in page.text


def test_admin_dashboard_explains_when_search_indexing_is_blocked():
    client.post("/admin/login", data={"token": "test-admin-token-abcdefghijklmnopqrstuvwxyz"})
    page = client.get("/admin")
    assert page.status_code == 200
    assert "Индексация в поисковых системах" in page.text
    assert "Заблокирована" in page.text
    assert "SEARCH_INDEXING_ENABLED" in page.text



def test_guide_hubs_use_truthful_localized_read_labels_and_accessibility():
    expected = {
        "fr": ("Lire le guide", "Langue"),
        "de": ("Leitfaden lesen", "Sprache"),
        "es": ("Leer la guía", "Idioma"),
        "sr": ("Pročitaj vodič", "Jezik"),
    }
    forbidden = ("en anglais", "auf Englisch", "en inglés", "na engleskom")
    for language, (read_label, aria_label) in expected.items():
        page = client.get(f"/{language}/guides")
        assert page.status_code == 200
        assert read_label in page.text
        assert f'aria-label="{aria_label}"' in page.text
        assert not any(value in page.text for value in forbidden)


def test_guide_detail_localizes_navigation_accessibility_and_german_refund_text():
    detail = client.get("/de/guides/supplier-not-shipped")
    assert detail.status_code == 200
    assert 'aria-label="Sprache"' in detail.text
    assert 'aria-label="Brotkrümelnavigation"' in detail.text
    assert "eine versprochene Rückerstattung" in detail.text
    assert "versprochenes Refund" not in detail.text


def test_privacy_is_server_rendered_localized_and_has_search_metadata():
    page = client.get("/privacy?lang=de")
    assert page.status_code == 200
    assert '<html lang="de">' in page.text
    assert "Datenschutzerklärung — ChinaTradeResolve" in page.text
    assert 'name="description"' in page.text
    assert 'rel="canonical" href="http://127.0.0.1:8000/privacy?lang=de"' in page.text
    assert 'hreflang="fr"' in page.text
    assert 'hreflang="x-default" href="http://127.0.0.1:8000/privacy?lang=en"' in page.text
    assert 'aria-label="Sprache"' in page.text
    assert "Wer Daten verarbeitet" in page.text
    assert "CTR_BOOT_LEGAL" not in page.text


def test_privacy_without_query_has_stable_russian_default():
    page = client.get("/privacy", headers={"accept-language": "fr-FR,fr;q=0.9,en;q=0.5"})
    assert page.status_code == 200
    assert '<html lang="ru">' in page.text
    assert "Политика конфиденциальности" in page.text
    assert 'rel="canonical" href="http://127.0.0.1:8000/privacy"' in page.text


def test_launch_readiness_requires_persistent_postgresql(monkeypatch):
    import app.main as module

    monkeypatch.setattr(module, "using_postgres", lambda: False)
    monkeypatch.setattr(module, "database_is_available", lambda: True)
    assert module.persistent_database_is_ready() is False
    assert module.launch_readiness_checks()["database_storage"] is False

    monkeypatch.setattr(module, "using_postgres", lambda: True)
    assert module.persistent_database_is_ready() is True


def test_health_and_admin_expose_database_mode_without_database_url():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["database_backend"] == "sqlite"
    assert health.json()["database_persistent"] is False

    client.post("/admin/login", data={"token": "test-admin-token-abcdefghijklmnopqrstuvwxyz"})
    dashboard = client.get("/admin")
    assert dashboard.status_code == 200
    assert "SQLite" in dashboard.text
    assert "DATABASE_URL" in dashboard.text


def test_privacy_sitemap_contains_language_alternates():
    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    assert "<loc>http://127.0.0.1:8000/privacy?lang=en</loc>" in sitemap.text
    assert "<loc>http://127.0.0.1:8000/privacy</loc>" in sitemap.text
    assert 'hreflang="de" href="http://127.0.0.1:8000/privacy?lang=de"' in sitemap.text


def test_local_run_script_is_executable():
    script = Path(__file__).resolve().parent.parent / "run_local.sh"
    assert script.stat().st_mode & 0o111


def test_gitignore_protects_secrets_and_local_database():
    content = (Path(__file__).resolve().parent.parent / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in content
    assert "data/*.db" in content
    assert ".venv/" in content
    assert "__pycache__/" in content


def test_home_promotes_localized_guides_without_reintroducing_old_copy():
    page = client.get('/?lang=ru')
    assert page.status_code == 200
    assert 'id="guides-preview"' in page.text
    assert 'href="/ru/guides/alibaba-dispute-evidence"' in page.text
    assert 'href="/ru/guides/supplier-not-shipped"' in page.text
    assert 'href="/ru/guides/product-quality-dispute"' in page.text
    assert 'data-i18n="nav_guides"' in page.text
    assert 'Подайте заявку на предварительную оценку материалов' in page.text
    assert 'Платные услуги пока не предоставляются.' in page.text
    assert 'Основная заявка рассматривается без оплаты.' in page.text
    for forbidden in (
        'Отправьте дело на бесплатный анализ',
        'Что входит в бесплатный анализ',
        'Платёжный сервис подключается одной настройкой сервера',
        'Через этот прототип не принимаются платежи и документы',
    ):
        assert forbidden not in page.text


def test_home_guide_links_follow_server_and_client_language():
    german = client.get('/?lang=de')
    assert german.status_code == 200
    assert 'href="/de/guides"' in german.text
    assert 'href="/de/guides/alibaba-dispute-evidence"' in german.text
    assert "document.querySelectorAll('[data-guide-slug]')" in german.text
    assert "`/${lang}/guides/${link.dataset.guideSlug}`" in german.text


def test_guide_cta_targets_real_application_section():
    detail = client.get('/ru/guides/alibaba-dispute-evidence')
    assert detail.status_code == 200
    assert '/?lang=ru#submit' in detail.text
    assert '#apply' not in detail.text


def test_ci_workflow_is_packaged_and_runs_compile_and_tests():
    workflow = Path(__file__).resolve().parent.parent / '.github' / 'workflows' / 'ci.yml'
    assert workflow.exists()
    content = workflow.read_text(encoding='utf-8')
    assert 'actions/checkout@v6' in content
    assert 'actions/setup-python@v6' in content
    assert 'chmod +x run_local.sh scripts/*.py' in content
    assert 'python -m pip install -r requirements-dev.txt' in content
    assert 'python -m compileall -q app scripts tests' in content
    assert 'python -m pytest -q' in content


def test_v3734_application_form_tracks_all_required_states():
    template = (Path(__file__).parents[1] / "app" / "templates" / "index.html").read_text(encoding="utf-8")
    assert 'id="formReadiness"' in template
    assert 'data-callback="ctrApplicationTurnstileSuccess"' in template
    assert 'data-expired-callback="ctrApplicationTurnstileExpired"' in template
    assert 'data-timeout-callback="ctrApplicationTurnstileTimeout"' in template
    assert 'data-unsupported-callback="ctrApplicationTurnstileUnsupported"' in template
    assert "window.turnstile.reset('#applicationTurnstileWidget')" in template
    assert 'data-error-callback="ctrApplicationTurnstileError"' in template
    assert "requiredApplicationFields.every(applicationFieldValid)" in template
    assert "requiredConsentInputs.every(input=>input.checked)" in template
    assert "applicationTurnstileVerified" in template
    assert "let applicationSubmitting=false" in template
    assert "if(applicationSubmitting)return" in template
    translations = json.loads((Path(__file__).parents[1] / "app" / "static" / "translations-v2.json").read_text(encoding="utf-8"))
    for language in ("en", "ru", "sr", "fr", "de", "es"):
        assert translations[language]["form_incomplete_status"].strip()
        assert translations[language]["form_incomplete_status_no_bot"].strip()
        assert translations[language]["form_ready_status"].strip()
        assert translations[language]["application_turnstile_ready"].strip()
        assert translations[language]["ai_chat_timeout"].strip()
        assert translations[language]["voice_timeout"].strip()


def test_v3734_voice_and_chat_requests_have_timeouts_and_release_microphone():
    template = (Path(__file__).parents[1] / "app" / "templates" / "index.html").read_text(encoding="utf-8")
    assert template.count("window.setTimeout(()=>controller.abort(),45000)") >= 2
    assert "requestTimedOut=true;controller.abort()" in template
    assert "window.addEventListener('pagehide',()=>stopDescriptionVoiceRecording(true))" in template
    assert "window.addEventListener('pagehide',()=>{if(aiChatAbortController)aiChatAbortController.abort();stopVoiceRecording(true)})" in template
    assert template.count("document.addEventListener('visibilitychange'") >= 2


def test_v3734_description_normalization_preserves_paragraphs():
    from app.schemas import ApplicationCreate

    payload = valid_payload()
    payload["description"] = " First paragraph with enough detail for validation.  \r\n\r\n  Second   paragraph with more evidence. \x00\x07 "
    application = ApplicationCreate.model_validate(payload)
    assert application.description == "First paragraph with enough detail for validation.\n\nSecond paragraph with more evidence."



def _v3745_redirect_test_app():
    from app.main import CanonicalHostRedirectMiddleware, body_limited_app

    return CanonicalHostRedirectMiddleware(
        body_limited_app,
        canonical_base_url="https://chinatraderesolve.com",
        source_hosts={"chinatraderesolve.onrender.com"},
        enabled=True,
    )


def test_v3745_render_hostname_redirects_to_canonical_origin_and_preserves_url():
    technical_client = TestClient(
        _v3745_redirect_test_app(),
        base_url="https://chinatraderesolve.onrender.com",
    )
    response = technical_client.get(
        "/case/CTR-2026-ABC/private-token?lang=ru&utm_source=old-link",
        follow_redirects=False,
    )
    assert response.status_code == 301
    assert response.headers["location"] == (
        "https://chinatraderesolve.com/case/CTR-2026-ABC/private-token"
        "?lang=ru&utm_source=old-link"
    )
    assert response.headers["vary"] == "Host"
    assert response.headers["x-app-version"] == "3.7.50"


def test_v3750_canonical_post_redirect_preserves_method():
    from app.main import CanonicalHostRedirectMiddleware, body_limited_app

    local_app = CanonicalHostRedirectMiddleware(
        body_limited_app,
        canonical_base_url="https://chinatraderesolve.com",
        source_hosts={"chinatraderesolve.onrender.com"},
        enabled=True,
    )
    local_client = TestClient(local_app, base_url="https://chinatraderesolve.onrender.com")
    response = local_client.post("/application", data={"test": "1"}, follow_redirects=False)
    assert response.status_code == 308
    assert response.headers["location"] == "https://chinatraderesolve.com/application"


def test_v3745_canonical_hostname_is_not_redirected():
    canonical_client = TestClient(
        _v3745_redirect_test_app(),
        base_url="https://chinatraderesolve.com",
    )
    response = canonical_client.get("/health", follow_redirects=False)
    assert response.status_code == 200
    assert response.json()["version"] == "3.7.50"


def test_v3745_unrelated_test_hostname_is_not_redirected():
    unrelated_client = TestClient(
        _v3745_redirect_test_app(),
        base_url="https://example.test",
    )
    response = unrelated_client.get("/health", follow_redirects=False)
    assert response.status_code == 200
    assert "location" not in response.headers


def test_v3745_local_fallback_does_not_redirect_render_host_to_localhost():
    from app.main import CanonicalHostRedirectMiddleware, body_limited_app

    local_app = CanonicalHostRedirectMiddleware(
        body_limited_app,
        canonical_base_url="http://127.0.0.1:8000",
        source_hosts={"chinatraderesolve.onrender.com"},
        enabled=True,
    )
    local_client = TestClient(local_app, base_url="https://chinatraderesolve.onrender.com")
    response = local_client.get("/health", follow_redirects=False)
    assert response.status_code == 200
    assert "location" not in response.headers

def test_v3750_yandex_verification_meta_is_rendered():
    import app.main as module

    original = module.settings.yandex_site_verification
    object.__setattr__(module.settings, "yandex_site_verification", "test-yandex-token")
    try:
        page = client.get("/")
        assert '<meta name="yandex-verification" content="test-yandex-token"' in page.text
    finally:
        object.__setattr__(module.settings, "yandex_site_verification", original)


def test_v3750_canonical_redirect_can_be_disabled():
    from app.main import CanonicalHostRedirectMiddleware, body_limited_app

    local_app = CanonicalHostRedirectMiddleware(
        body_limited_app,
        canonical_base_url="https://chinatraderesolve.com",
        source_hosts={"chinatraderesolve.onrender.com"},
        enabled=False,
    )
    local_client = TestClient(local_app, base_url="https://chinatraderesolve.onrender.com")
    response = local_client.get("/health", follow_redirects=False)
    assert response.status_code == 200
    assert "location" not in response.headers


def test_v3738_version_markers_are_synchronised():
    root = Path(__file__).parents[1]
    assert (root / "VERSION.txt").read_text(encoding="utf-8").strip() == "3.7.50"
    assert "v3.7.50" in (root / "README.md").read_text(encoding="utf-8").splitlines()[0]
    assert "ChinaTradeResolve Document AI v3.7.50" in (root / "CHANGELOG_RU.txt").read_text(encoding="utf-8").splitlines()[0]
    assert "v3.7.50" in (root / "DEPLOY_RU.md").read_text(encoding="utf-8").splitlines()[0]
    assert "3.7.50" in (root / "PROMOTION_RU.md").read_text(encoding="utf-8")[:300]


def test_v3738_ai_chat_stacks_send_button_on_very_narrow_screens():
    page = client.get("/?lang=ru")
    assert page.status_code == 200
    assert "@media(max-width:360px){.ai-chat-form{grid-template-columns:minmax(0,1fr)" in page.text
    assert ".ai-chat-form textarea{width:100%}" in page.text
    assert ".ai-chat-send{grid-column:1/-1;width:100%;min-height:44px}" in page.text


def test_v3735_mobile_layout_table_hint_and_copy_are_present():
    page = client.get("/?lang=en")
    assert page.status_code == 200
    assert ".ai-chat-launcher.is-compact{right:14px;bottom:calc(82px + env(safe-area-inset-bottom));max-width:52px;opacity:0" in page.text
    assert "#situations .g4,#services .compact-grid,.guides-preview-grid{display:flex;max-width:100%;min-width:0;overflow-x:auto" in page.text
    assert 'data-i18n="table_swipe_hint" id="tableSwipeHint"' in page.text
    assert 'data-i18n-aria-label="sample_table_label"' in page.text
    translations = json.loads((Path(__file__).resolve().parent.parent / "app" / "static" / "translations-v2.json").read_text(encoding="utf-8"))
    assert translations["en"]["consent2"] == "I voluntarily allow AI assistance with mandatory human review. Without consent, rules-based review and, where needed, manual review will be used."


def test_csp_uses_per_response_nonce_and_blocks_inline_handlers():
    import re
    first = client.get("/")
    second = client.get("/")
    first_csp = first.headers["content-security-policy"]
    second_csp = second.headers["content-security-policy"]
    assert "script-src 'self' 'unsafe-inline'" not in first_csp
    assert "style-src 'self' 'unsafe-inline'" not in first_csp
    assert "script-src-attr 'none'" in first_csp
    assert "style-src-attr 'none'" in first_csp
    assert "object-src 'none'" in first_csp
    first_nonce = re.search(r"'nonce-([^']+)'", first_csp)
    second_nonce = re.search(r"'nonce-([^']+)'", second_csp)
    assert first_nonce and second_nonce and first_nonce.group(1) != second_nonce.group(1)
    assert f'nonce="{first_nonce.group(1)}"' in first.text
    assert not re.search(r"\son[a-z]+=", first.text)


def test_static_legal_pages_do_not_require_inline_javascript():
    import re
    for path in ["terms.html", "refund.html", "ai-notice.html", "disclaimer.html", "sample_case_assessment.html"]:
        text = (Path(__file__).resolve().parent.parent / "app" / "static" / path).read_text(encoding="utf-8")
        assert "CTR_BOOT_LEGAL(" not in text
        assert not re.search(r"<script(?![^>]*src=)[^>]*>\s*\S", text)
    legal_js = (Path(__file__).resolve().parent.parent / "app" / "static" / "legal-i18n-v2.js").read_text(encoding="utf-8")
    assert "dataset?.legalPage" in legal_js


def test_pdf_security_is_an_explicit_launch_readiness_gate(monkeypatch):
    import app.main as module
    monkeypatch.setattr(module, "pdf_security_self_test", lambda: False)
    assert module.launch_readiness_checks()["pdf_security"] is False
    monkeypatch.setattr(module, "pdf_security_self_test", lambda: True)
    assert module.launch_readiness_checks()["pdf_security"] is True
    script = Path(__file__).resolve().parent.parent / "scripts" / "verify_pdf_security.py"
    assert script.exists()


def test_v3738_production_smoke_assets_are_packaged():
    root = Path(__file__).parents[1]
    script = root / "scripts" / "production_smoke_test.py"
    guide = root / "PRODUCTION_SMOKE_TEST_RU.md"
    voice = root / "tests" / "fixtures" / "production-smoke-voice.wav"
    assert script.exists() and script.stat().st_mode & 0o111
    content = script.read_text(encoding="utf-8")
    assert "--confirm-live" in content
    assert "public_ready" in content
    assert "email_delivery" in content
    assert "openai_assistant" in content
    assert "voice_transcription" in content
    assert guide.exists()
    assert voice.read_bytes().startswith(b"RIFF")


def test_v3738_docker_and_ci_restore_zip_permissions():
    root = Path(__file__).parents[1]
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    workflow = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "chmod +x /app/run_local.sh /app/scripts/*.py" in dockerfile
    assert "chmod +x run_local.sh scripts/*.py" in workflow


def test_v3749_search_intent_guides_are_substantial_and_indexable():
    expected_slugs = {
        "supplier-not-refunding",
        "supplier-disappeared-after-payment",
        "damaged-or-short-shipment",
        "wrong-material-size-color",
        "alibaba-dispute-closed-no-refund",
        "supplier-certificate-problem",
        "customs-clearance-problem",
        "order-not-delivered-tracking-problem",
    }
    for language in ("ru", "en"):
        hub = client.get(f"/{language}/guides")
        assert hub.status_code == 200
        for slug in expected_slugs:
            assert f'/{language}/guides/{slug}' in hub.text
            page = client.get(f"/{language}/guides/{slug}")
            assert page.status_code == 200
            assert 'name="robots" content="index,follow,max-image-preview:large"' in page.text
            assert 'FAQPage' in page.text
            assert 'dateModified' in page.text
            assert page.text.count('<h2>') >= 5
            assert len(page.text) > 7000

    # Do not advertise translations that have not received editorial review.
    assert client.get('/fr/guides/supplier-not-refunding').status_code == 404
    sitemap = client.get('/sitemap.xml')
    assert '/ru/guides/supplier-not-refunding' in sitemap.text
    assert '/en/guides/supplier-not-refunding' in sitemap.text
    assert '/fr/guides/supplier-not-refunding' not in sitemap.text
    assert '<lastmod>2026-07-26</lastmod>' in sitemap.text


def test_v3749_related_guides_are_limited_and_contextual():
    page = client.get('/ru/guides/supplier-not-refunding')
    assert page.status_code == 200
    # One article URL may also occur in metadata; the visible related list must stay compact.
    assert page.text.count('class="related"') == 1
    assert 'Alibaba закрыла спор без возврата денег' in page.text
    assert 'Китайский поставщик пропал после оплаты' in page.text
