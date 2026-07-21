from __future__ import annotations

import hashlib
import json
import re
import secrets
from datetime import datetime, timezone
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import qrcode
from qrcode.constants import ERROR_CORRECT_H

from .ai_triage import ai_triage
from .ai_assistant import (
    AssistantConfigurationError,
    AssistantProviderError,
    assistant_is_enabled,
    assistant_reply,
    localized_error,
)
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
from .schemas import ApplicationCreate, AssistantChatRequest, AssistantChatResponse, FeedbackCreate
from .security import SlidingWindowRateLimiter, client_key
from .triage import merge_triage, rules_triage


BASE = Path(__file__).resolve().parent
app = FastAPI(title="ChinaTradeResolve Free Access", version="3.1.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.app_secret,
    same_site="lax",
    https_only=settings.public_base_url.startswith("https://"),
    max_age=3600,
)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")
limiter = SlidingWindowRateLimiter()
admin_login_limiter = SlidingWindowRateLimiter(limit=5, window_seconds=900)
assistant_limiter = SlidingWindowRateLimiter(limit=18, window_seconds=600)
init_db()


def is_admin(request: Request) -> bool:
    return bool(request.session.get("admin"))


def require_admin(request: Request) -> None:
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Admin authentication required")


def make_reference() -> str:
    year = datetime.now(timezone.utc).year
    return f"CTR-{year}-{secrets.token_hex(5).upper()}"


def safe_support_url() -> str | None:
    raw = (settings.support_url or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        return None
    return raw


_BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _base58check_payload(address: str) -> bytes | None:
    try:
        number = 0
        for char in address:
            number = number * 58 + _BASE58_ALPHABET.index(char)
        decoded = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
        decoded = b"\x00" * (len(address) - len(address.lstrip("1"))) + decoded
    except (ValueError, OverflowError):
        return None
    if len(decoded) < 5:
        return None
    payload, checksum = decoded[:-4], decoded[-4:]
    expected = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return payload if secrets.compare_digest(checksum, expected) else None


def _valid_btc(address: str) -> bool:
    if address.startswith(("1", "3")):
        payload = _base58check_payload(address)
        return bool(payload and payload[0] in {0x00, 0x05})
    # Bech32 addresses are accepted by strict shape here; the configured legacy address
    # receives full Base58Check validation above.
    return bool(re.fullmatch(r"bc1[ac-hj-np-z02-9]{11,71}", address))


def _valid_tron(address: str) -> bool:
    payload = _base58check_payload(address)
    return bool(payload and len(payload) == 21 and payload[0] == 0x41)


def _valid_eth(address: str) -> bool:
    return bool(re.fullmatch(r"0x[a-fA-F0-9]{40}", address))


def _valid_solana(address: str) -> bool:
    """Validate a Solana public key as a 32-byte Base58 value."""
    if not re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", address):
        return False
    try:
        number = 0
        for char in address:
            number = number * 58 + _BASE58_ALPHABET.index(char)
        decoded = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
        decoded = b"\x00" * (len(address) - len(address.lstrip("1"))) + decoded
    except (ValueError, OverflowError):
        return False
    return len(decoded) == 32


def crypto_wallets() -> list[dict[str, str]]:
    """Return only public wallet addresses that pass network-specific validation."""
    configured = [
        ("btc", "Bitcoin", "BTC", "Bitcoin", settings.btc_address, _valid_btc),
        ("eth", "Ethereum", "ETH", "Ethereum Mainnet", settings.eth_address, _valid_eth),
        ("usdt-trc20", "Tether", "USDT", "TRON (TRC20)", settings.usdt_trc20_address, _valid_tron),
        ("sol", "Solana", "SOL", "Solana", settings.sol_address, _valid_solana),
    ]
    wallets: list[dict[str, str]] = []
    for wallet_id, name, asset, network, raw_address, validator in configured:
        address = (raw_address or "").strip()
        if not address or not validator(address):
            continue
        wallets.append({
            "id": wallet_id,
            "name": name,
            "asset": asset,
            "network": network,
            "address": address,
            "qr_url": f"/support/qr/{wallet_id}.png",
        })
    return wallets


def support_is_available() -> bool:
    return bool(safe_support_url() or crypto_wallets())


@lru_cache(maxsize=16)
def _qr_png(payload: str) -> bytes:
    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_H, box_size=12, border=4)
    qr.add_data(payload)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'",
    )
    if settings.public_base_url.startswith("https://"):
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if request.url.path.startswith(("/admin", "/case/")):
        response.headers.setdefault("Cache-Control", "no-store")
    return response



STATUS_LABELS = {
    "submitted": "Получено", "needs_information": "Нужна информация",
    "pilot_candidate": "Кандидат на бесплатную помощь", "human_review": "Ручная проверка",
    "declined": "Отклонено", "accepted": "Принято", "closed": "Закрыто",
}
RISK_LABELS = {"critical": "Критический", "high": "Высокий", "medium": "Средний", "low": "Низкий"}
LANGUAGE_LABELS = {"English": "Английский", "French": "Французский", "German": "Немецкий", "Spanish": "Испанский", "Russian": "Русский", "Serbian": "Сербский"}
ACTOR_LABELS = {"system": "система", "triage": "автопроверка", "admin": "администратор", "client": "клиент"}
EVENT_LABELS = {"application_created": "заявка создана", "triage_completed": "автопроверка завершена", "status_updated": "статус изменён", "feedback_submitted": "отзыв отправлен", "triage_recomputed": "автопроверка повторена"}
PROBLEM_LABELS = {
    "Goods not delivered": "Товар не доставлен",
    "Poor quality or defects": "Низкое качество или дефекты",
    "Wrong material or specification": "Неверный материал или спецификация",
    "Questionable documents": "Сомнительные документы",
    "Supplier refuses refund": "Поставщик отказывается возвращать деньги",
    "Marketplace rejected the claim": "Площадка отклонила претензию",
}
RESULT_LABELS = {
    "Full refund": "Полный возврат", "Partial refund": "Частичный возврат", "Replacement": "Замена",
    "Completion of order": "Завершение исполнения заказа", "Negotiated settlement": "Согласованное урегулирование",
    "Not sure": "Пока не определено",
}
CHANNEL_LABELS = {"Direct supplier contract": "Прямой договор с поставщиком", "Other": "Другое"}
PUBLIC_STATUS_LABELS = {
    "English": {"submitted":"Received","needs_information":"Information needed","pilot_candidate":"Free-review candidate","human_review":"Human review","declined":"Declined","accepted":"Accepted","closed":"Closed"},
    "French": {"submitted":"Reçue","needs_information":"Informations nécessaires","pilot_candidate":"Candidate à l’analyse gratuite","human_review":"Vérification humaine","declined":"Refusée","accepted":"Acceptée","closed":"Clôturée"},
    "German": {"submitted":"Eingegangen","needs_information":"Informationen erforderlich","pilot_candidate":"Kandidat für kostenlose Prüfung","human_review":"Menschliche Prüfung","declined":"Abgelehnt","accepted":"Angenommen","closed":"Abgeschlossen"},
    "Spanish": {"submitted":"Recibida","needs_information":"Se necesita información","pilot_candidate":"Candidato a revisión gratuita","human_review":"Revisión humana","declined":"Rechazada","accepted":"Aceptada","closed":"Cerrada"},
    "Russian": STATUS_LABELS,
    "Serbian": {"submitted":"Primljeno","needs_information":"Potrebne informacije","pilot_candidate":"Kandidat za besplatni pregled","human_review":"Ljudski pregled","declined":"Odbijeno","accepted":"Prihvaćeno","closed":"Zatvoreno"},
}
PUBLIC_RISK_LABELS = {
    "English": {"critical":"Critical","high":"High","medium":"Medium","low":"Low"},
    "French": {"critical":"Critique","high":"Élevé","medium":"Moyen","low":"Faible"},
    "German": {"critical":"Kritisch","high":"Hoch","medium":"Mittel","low":"Niedrig"},
    "Spanish": {"critical":"Crítico","high":"Alto","medium":"Medio","low":"Bajo"},
    "Russian": RISK_LABELS,
    "Serbian": {"critical":"Kritičan","high":"Visok","medium":"Srednji","low":"Nizak"},
}

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
    "French": {
        "title": "Statut du dossier",
        "info_heading": "Informations susceptibles d’être demandées",
        "return": "Retour au site",
        "notice": "Aucun paiement ni téléchargement de fichier n’est requis au stade de la demande. Cette page contient une classification préliminaire automatisée, et non un conseil juridique ou une prévision du résultat.",
        "feedback_heading": "Aidez-nous à améliorer le service gratuit",
        "feedback_intro": "Laissez un avis sincère après avoir reçu de l’aide. N’indiquez pas le nom du fournisseur, le numéro de commande ni d’autres informations confidentielles.",
        "rating": "Note",
        "feedback": "Votre avis",
        "display_name": "Nom à afficher avec un éventuel témoignage (facultatif)",
        "testimonial": "Vous pouvez publier un extrait anonymisé de cet avis. La publication n’est jamais automatique.",
        "submit_feedback": "Envoyer l’avis",
        "thanks": "Merci. Votre avis a été enregistré.",
        "support_heading": "Soutenir volontairement le projet",
        "support_text": "ChinaTradeResolve est actuellement gratuit. Une contribution volontaire n’est pas le paiement d’un service et n’influence ni l’acceptation, ni la priorité, ni l’analyse, ni le résultat.",
        "support_button": "Soutenir le projet",
        "not_ready": "Le soutien volontaire n’est pas encore activé.",
    },
    "German": {
        "title": "Fallstatus",
        "info_heading": "Möglicherweise benötigte Informationen",
        "return": "Zur Website zurückkehren",
        "notice": "Bei der Antragstellung sind weder Zahlung noch Datei-Upload erforderlich. Diese Seite enthält eine automatisierte vorläufige Einstufung, keine Rechtsberatung und keine Prognose des Ergebnisses.",
        "feedback_heading": "Helfen Sie uns, den kostenlosen Dienst zu verbessern",
        "feedback_intro": "Geben Sie nach erhaltener Unterstützung eine ehrliche Rückmeldung. Nennen Sie keine Lieferantennamen, Bestellnummern oder andere vertrauliche Angaben.",
        "rating": "Bewertung",
        "feedback": "Ihre Rückmeldung",
        "display_name": "Name für eine mögliche Veröffentlichung (optional)",
        "testimonial": "Ein anonymisierter Auszug dieser Rückmeldung darf veröffentlicht werden. Eine Veröffentlichung erfolgt nie automatisch.",
        "submit_feedback": "Rückmeldung senden",
        "thanks": "Vielen Dank. Ihre Rückmeldung wurde gespeichert.",
        "support_heading": "Projekt freiwillig unterstützen",
        "support_text": "ChinaTradeResolve ist derzeit kostenlos. Eine freiwillige Unterstützung ist keine Bezahlung für eine Leistung und beeinflusst weder Annahme, Priorität, Prüfung noch Ergebnis.",
        "support_button": "Projekt unterstützen",
        "not_ready": "Freiwillige Unterstützung ist noch nicht eingerichtet.",
    },
    "Spanish": {
        "title": "Estado del caso",
        "info_heading": "Información que puede solicitarse",
        "return": "Volver al sitio web",
        "notice": "En la fase de solicitud no se requiere pago ni carga de archivos. Esta página contiene una clasificación preliminar automatizada, no asesoramiento jurídico ni una predicción del resultado.",
        "feedback_heading": "Ayúdenos a mejorar el servicio gratuito",
        "feedback_intro": "Comparta una opinión sincera después de recibir ayuda. No incluya nombres de proveedores, números de pedido ni otros datos confidenciales.",
        "rating": "Valoración",
        "feedback": "Su opinión",
        "display_name": "Nombre para un posible testimonio (opcional)",
        "testimonial": "Puede publicarse un extracto anonimizado de esta opinión. La publicación nunca es automática.",
        "submit_feedback": "Enviar opinión",
        "thanks": "Gracias. Su opinión ha sido registrada.",
        "support_heading": "Apoyar voluntariamente el proyecto",
        "support_text": "ChinaTradeResolve es actualmente gratuito. Una contribución voluntaria no es el pago de un servicio y no afecta la aceptación, prioridad, revisión ni resultado.",
        "support_button": "Apoyar el proyecto",
        "not_ready": "El apoyo voluntario aún no está habilitado.",
    },
}


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "support_enabled": support_is_available(),
            "contact_email": settings.contact_email,
            "ai_assistant_enabled": assistant_is_enabled(),
        },
    )


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "free_access_mode": settings.free_access_mode,
        "support_enabled": support_is_available(),
        "ai_triage_enabled": settings.enable_ai_triage and bool(settings.openai_api_key and settings.openai_model),
        "ai_assistant_enabled": assistant_is_enabled(),
        "email_delivery_configured": bool(
            (settings.email_bridge_url and settings.email_bridge_secret)
            or (
                settings.smtp_host
                and settings.smtp_username
                and settings.smtp_password
                and settings.admin_email
            )
        ),
    }


@app.post("/api/assistant", response_model=AssistantChatResponse)
async def public_ai_assistant(payload: AssistantChatRequest, request: Request) -> AssistantChatResponse:
    key = f"assistant:{client_key(request)}"
    if not assistant_limiter.allow(key):
        raise HTTPException(status_code=429, detail=localized_error(payload.language, "rate"))
    if not assistant_is_enabled():
        raise HTTPException(status_code=503, detail=localized_error(payload.language, "unavailable"))
    try:
        reply = await assistant_reply(payload)
    except AssistantConfigurationError:
        raise HTTPException(status_code=503, detail=localized_error(payload.language, "unavailable"))
    except AssistantProviderError:
        raise HTTPException(status_code=502, detail=localized_error(payload.language, "unavailable"))
    return AssistantChatResponse(reply=reply)


@app.get("/support", response_class=HTMLResponse)
def support_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="support.html",
        context={
            "support_url": safe_support_url(),
            "wallets": crypto_wallets(),
            "project_name": settings.support_project_name,
        },
    )


@app.get("/support/qr/{wallet_id}.png")
def support_qr(wallet_id: str) -> Response:
    wallet = next((item for item in crypto_wallets() if item["id"] == wallet_id), None)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return Response(
        content=_qr_png(wallet["address"]),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600", "X-Content-Type-Options": "nosniff"},
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
            "support_available": support_is_available(),
            "status_label": PUBLIC_STATUS_LABELS.get(language, PUBLIC_STATUS_LABELS["English"]).get(case["status"], case["status"]),
            "risk_label": PUBLIC_RISK_LABELS.get(language, PUBLIC_RISK_LABELS["English"]).get(case["risk_level"], case["risk_level"]),
            "page_language": {"English": "en", "French": "fr", "German": "de", "Spanish": "es", "Russian": "ru", "Serbian": "sr"}.get(language, "en"),
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
    key = f"admin-login:{client_key(request)}"
    if not admin_login_limiter.allow(key):
        return templates.TemplateResponse(
            request=request,
            name="admin_login.html",
            context={"error": "Слишком много попыток входа. Повторите позже."},
            status_code=429,
        )
    if not secrets.compare_digest(token, settings.admin_token):
        return templates.TemplateResponse(request=request, name="admin_login.html", context={"error": "Неверный токен администратора"}, status_code=401)
    request.session.clear()
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
        context={
            "cases": cases,
            "counts": dashboard_counts(),
            "status_filter": status or "",
            "risk_filter": risk or "",
            "status_labels": STATUS_LABELS,
            "risk_labels": RISK_LABELS,
            "problem_labels": PROBLEM_LABELS,
        },
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
            "status_labels": STATUS_LABELS,
            "risk_labels": RISK_LABELS,
            "language_labels": LANGUAGE_LABELS,
            "actor_labels": ACTOR_LABELS,
            "event_labels": EVENT_LABELS,
            "problem_labels": PROBLEM_LABELS,
            "result_labels": RESULT_LABELS,
            "channel_labels": CHANNEL_LABELS,
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
