from pathlib import Path
import os
import tempfile

_tmp = tempfile.TemporaryDirectory()
os.environ["DATABASE_PATH"] = str(Path(_tmp.name) / "test.db")
os.environ["ADMIN_TOKEN"] = "test-token"
os.environ["APP_SECRET"] = "test-secret"
os.environ["ENABLE_AI_TRIAGE"] = "false"
os.environ["FREE_ACCESS_MODE"] = "true"
os.environ["SUPPORT_URL"] = "https://example.com/support"

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
    assert "Этап бесплатного доступа" in home.text
    assert "Добровольная поддержка" in home.text
    assert "chinatraderesolve.support@gmail.com" in home.text
    assert health.json()["email_delivery_configured"] is False


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
    login = client.post("/admin/login", data={"token": "test-token"}, follow_redirects=False)
    assert login.status_code == 303
    dashboard = client.get("/admin")
    assert dashboard.status_code == 200
    assert "Очередь дел, требующих внимания" in dashboard.text

    # Find the case id from the queue link.
    import re
    match = re.search(r'href="/admin/case/(\d+)">' + re.escape(created["case_reference"]), dashboard.text)
    assert match
    case_id = int(match.group(1))
    close = client.post(f"/admin/case/{case_id}/status", data={"status": "closed", "note": "Review completed"}, follow_redirects=False)
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
    assert "Команда по разбору дел ChinaTradeResolve" in home.text
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
        execute(conn, "UPDATE cases SET created_at='2000-01-01T00:00:00+00:00' WHERE id=?", (case_id,))

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
