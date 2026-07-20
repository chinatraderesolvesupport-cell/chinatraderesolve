from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .ai_triage import ai_triage
from .config import settings
from .db import (
    create_case,
    dashboard_counts,
    get_audit,
    get_case,
    get_case_by_public,
    get_feedback,
    init_db,
    list_cases,
    replace_triage,
    save_feedback,
    update_status,
)
from .notifications import (
    deliver_pending,
    queue_case_notifications,
    queue_completion_notification,
)
from .schemas import ApplicationCreate, FeedbackCreate
from .security import SlidingWindowRateLimiter, client_key
from .triage import merge_triage, rules_triage


BASE = Path(__file__).resolve().parent
app = FastAPI(title="ChinaTradeResolve Free Access", version="1.1.0")
app.add_middleware(SessionMiddleware, secret_key=settings.app_secret, same_site="lax", https_only=False)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")
limiter = SlidingWindowRateLimiter()
init_db()


def is_admin(request: Request) -> bool:
    return bool(request.session.get("admin"))


def require_admin(request: Request) -> None:
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Admin authentication required")


def make_reference() -> str:
    year = datetime.now(timezone.utc).year
    return f"CTR-{year}-{secrets.token_hex(3).upper()}"


def safe_support_url() -> str | None:
    raw = (settings.support_url or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        return None
    return raw


STATUS_COPY = {
    "English": {
        "title": "Case status",
        "info_heading": "Information that may be requested",
        "return": "Return to website",
        "notice": "No service fee or file upload is required at the application stage. This page contains an automated preliminary classification, not legal advice or a prediction of outcome.",
        "feedback_heading": "Help us improve the free service",
        "feedback_intro": "Share honest feedback after the service has helped you. Do not include supplier names, order numbers or other confidential details.",
        "rating": "Rating",
        "feedback": "Your feedback",
        "display_name": "Name shown with a possible testimonial (optional)",
        "testimonial": "You may publish an anonymised excerpt of this feedback. Publication is never automatic.",
        "submit_feedback": "Send feedback",
        "thanks": "Thank you. Your feedback has been recorded.",
        "support_heading": "Support the project voluntarily",
        "support_text": "ChinaTradeResolve is currently free. A voluntary contribution is not payment for a service and does not affect acceptance, priority, review or outcome.",
        "support_button": "Support the project",
        "not_ready": "Voluntary support has not been connected yet.",
    },
    "Russian": {
        "title": "Статус дела",
        "info_heading": "Информация, которая может потребоваться",
        "return": "Вернуться на сайт",
        "notice": "На этапе заявки оплата и загрузка файлов не требуются. Эта страница содержит автоматическую предварительную классификацию, а не юридическую консультацию или прогноз результата.",
        "feedback_heading": "Помогите улучшить бесплатный сервис",
        "feedback_intro": "Оставьте честный отзыв после получения помощи. Не указывайте имена поставщиков, номера заказов и другие конфиденциальные сведения.",
        "rating": "Оценка",
        "feedback": "Ваш отзыв",
        "display_name": "Имя для возможной публикации отзыва (необязательно)",
        "testimonial": "Разрешаю опубликовать обезличенный фрагмент отзыва. Публикация не происходит автоматически.",
        "submit_feedback": "Отправить отзыв",
        "thanks": "Спасибо. Ваш отзыв сохранён.",
        "support_heading": "Добровольно поддержать проект",
        "support_text": "ChinaTradeResolve сейчас работает бесплатно. Добровольная поддержка не является оплатой услуги и не влияет на принятие дела, приоритет, проверку или результат.",
        "support_button": "Поддержать проект",
        "not_ready": "Добровольная поддержка пока не подключена.",
    },
    "Serbian": {
        "title": "Status slučaja",
        "info_heading": "Informacije koje mogu biti zatražene",
        "return": "Povratak na sajt",
        "notice": "U fazi prijave se ne traži plaćanje niti otpremanje fajlova. Ova stranica sadrži automatsku preliminarnu klasifikaciju, a ne pravni savet ili prognozu ishoda.",
        "feedback_heading": "Pomozite nam da unapredimo besplatnu uslugu",
        "feedback_intro": "Pošaljite iskrene povratne informacije nakon pomoći. Ne unosite imena dobavljača, brojeve porudžbina ili poverljive podatke.",
        "rating": "Ocena",
        "feedback": "Vaša povratna informacija",
        "display_name": "Ime za moguću objavu izjave (opciono)",
        "testimonial": "Dozvoljavam objavu anonimizovanog izvoda. Objavljivanje nikada nije automatsko.",
        "submit_feedback": "Pošaljite povratnu informaciju",
        "thanks": "Hvala. Vaša povratna informacija je sačuvana.",
        "support_heading": "Dobrovoljno podržite projekat",
        "support_text": "ChinaTradeResolve je trenutno besplatan. Dobrovoljna podrška nije plaćanje usluge i ne utiče na prihvatanje, prioritet, pregled ili ishod.",
        "support_button": "Podržite projekat",
        "not_ready": "Dobrovoljna podrška još nije povezana.",
    },
}


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "support_enabled": bool(safe_support_url()),
            "contact_email": settings.contact_email,
        },
    )


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "free_access_mode": settings.free_access_mode,
        "support_enabled": bool(safe_support_url()),
        "ai_triage_enabled": settings.enable_ai_triage and bool(settings.openai_api_key and settings.openai_model),
        "email_delivery_configured": bool(
            settings.smtp_host
            and settings.smtp_username
            and settings.smtp_password
            and settings.admin_email
        ),
    }


@app.get("/support", response_class=HTMLResponse)
def support_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="support.html",
        context={
            "support_url": safe_support_url(),
            "project_name": settings.support_project_name,
        },
    )


@app.post("/api/applications")
async def submit_application(payload: ApplicationCreate, request: Request) -> JSONResponse:
    if payload.company_website:
        return JSONResponse({"case_reference": "received", "public_message": "Application received."}, status_code=201)
    if not limiter.allow(client_key(request)):
        raise HTTPException(status_code=429, detail="Too many applications from this connection. Please try later.")

    rule_result = rules_triage(payload)
    ai_result = None
    if payload.ai_consent:
        try:
            ai_result = await ai_triage(payload)
        except Exception:
            ai_result = None
    triage = merge_triage(rule_result, ai_result)

    reference = make_reference()
    public_token = secrets.token_urlsafe(24)
    case = create_case(payload.model_dump(), triage.model_dump(), reference, public_token)
    queue_case_notifications(case)
    deliver_pending()
    status_url = f"/case/{reference}/{public_token}"
    return JSONResponse(
        {
            "case_reference": reference,
            "status": case["status"],
            "public_message": case["public_message"],
            "status_url": status_url,
        },
        status_code=201,
    )


@app.get("/case/{reference}/{token}", response_class=HTMLResponse)
def public_case_status(reference: str, token: str, request: Request, feedback_saved: int = 0) -> HTMLResponse:
    case = get_case_by_public(reference, token)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    triage = json.loads(case["triage_json"])
    language = case.get("preferred_language") or "English"
    copy = STATUS_COPY.get(language, STATUS_COPY["English"])
    feedback = get_feedback(case["id"])
    return templates.TemplateResponse(
        request=request,
        name="public_status.html",
        context={
            "case": case,
            "triage": triage,
            "copy": copy,
            "feedback": feedback,
            "feedback_saved": bool(feedback_saved),
            "support_url": safe_support_url(),
        },
    )


@app.post("/case/{reference}/{token}/feedback")
def public_case_feedback(
    reference: str,
    token: str,
    request: Request,
    rating: int = Form(...),
    feedback_text: str = Form(...),
    display_name: str = Form(""),
    testimonial_consent: bool = Form(False),
    company_website: str = Form(""),
) -> RedirectResponse:
    case = get_case_by_public(reference, token)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if company_website:
        return RedirectResponse(f"/case/{reference}/{token}?feedback_saved=1", status_code=303)
    if not limiter.allow(f"feedback:{client_key(request)}"):
        raise HTTPException(status_code=429, detail="Too many feedback submissions. Please try later.")
    payload = FeedbackCreate(
        rating=rating,
        feedback_text=feedback_text,
        display_name=display_name,
        testimonial_consent=testimonial_consent,
        company_website=company_website,
    )
    save_feedback(case["id"], payload.model_dump())
    return RedirectResponse(f"/case/{reference}/{token}?feedback_saved=1", status_code=303)


@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="admin_login.html", context={"error": None})


@app.post("/admin/login", response_class=HTMLResponse)
def admin_login(request: Request, token: str = Form(...)) -> HTMLResponse:
    if not secrets.compare_digest(token, settings.admin_token):
        return templates.TemplateResponse(request=request, name="admin_login.html", context={"error": "Invalid admin token"}, status_code=401)
    request.session["admin"] = True
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/logout")
def admin_logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=303)


@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, status: str | None = None, risk: str | None = None) -> HTMLResponse:
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)
    cases = list_cases(status=status, risk=risk)
    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={"cases": cases, "counts": dashboard_counts(), "status_filter": status or "", "risk_filter": risk or ""},
    )


@app.get("/admin/case/{case_id}", response_class=HTMLResponse)
def admin_case_detail(case_id: int, request: Request) -> HTMLResponse:
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return templates.TemplateResponse(
        request=request,
        name="admin_case.html",
        context={
            "case": case,
            "triage": json.loads(case["triage_json"]),
            "audit": get_audit(case_id),
            "feedback": get_feedback(case_id),
        },
    )


@app.post("/admin/case/{case_id}/status")
def admin_update_status(case_id: int, request: Request, status: str = Form(...), note: str = Form("")) -> RedirectResponse:
    require_admin(request)
    try:
        old_case = get_case(case_id)
        updated = update_status(case_id, status, note)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if old_case and old_case["status"] != "closed" and updated["status"] == "closed":
        queue_completion_notification(updated)
        deliver_pending()
    return RedirectResponse(f"/admin/case/{case_id}", status_code=303)


@app.post("/admin/case/{case_id}/retriage")
async def admin_retriage(case_id: int, request: Request) -> RedirectResponse:
    require_admin(request)
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    payload = ApplicationCreate(
        full_name=case["full_name"],
        email=case["email"],
        country=case["country"],
        preferred_language=case["preferred_language"],
        purchasing_channel=case["purchasing_channel"],
        amount_in_dispute=case["amount_in_dispute"],
        main_problem=case["main_problem"],
        supplier_name=case["supplier_name"],
        order_number=case["order_number"],
        order_value=case["order_value"],
        requested_result=case["requested_result"],
        description=case["description"],
        company_website="",
        free_access_terms=True,
        sharing_authority=True,
        ai_consent=bool(case["ai_consent"]),
        no_guarantee=True,
    )
    rules = rules_triage(payload)
    ai = None
    if payload.ai_consent:
        try:
            ai = await ai_triage(payload)
        except Exception:
            ai = None
    replace_triage(case_id, merge_triage(rules, ai).model_dump())
    return RedirectResponse(f"/admin/case/{case_id}", status_code=303)
