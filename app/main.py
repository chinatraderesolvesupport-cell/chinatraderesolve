from __future__ import annotations

import asyncio
import hashlib
import logging
from contextlib import asynccontextmanager
import json
import re
import secrets
import time
import tempfile
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse
from xml.sax.saxutils import escape as xml_escape

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.gzip import GZipMiddleware

import qrcode
import httpx
from eth_utils import is_checksum_address
from qrcode.constants import ERROR_CORRECT_H

from .ai_triage import ai_triage
from .ai_assistant import (
    AssistantConfigurationError,
    AssistantProviderError,
    assistant_is_enabled,
    assistant_reply,
    assistant_scope_reply,
    localized_error,
)
from .config import admin_token_is_secure, app_secret_is_secure, settings
from .db import (
    add_case_documents,
    claim_document_analysis,
    connect,
    create_case,
    dashboard_counts,
    DailyAnalysisLimitError,
    DailyUsageLimitError,
    delete_case_now,
    delete_case_document,
    DocumentAnalysisInProgressError,
    DocumentLimitError,
    get_audit,
    get_case,
    get_case_by_public,
    get_case_document,
    get_document_analysis,
    fail_running_document_analyses_on_startup,
    fail_stale_document_analysis,
    get_feedback,
    grant_ai_consent,
    init_db,
    list_case_documents,
    list_cases,
    claim_daily_usage_for_subject,
    replace_triage,
    record_audit,
    revoke_ai_consent,
    save_document_analysis,
    save_feedback,
    set_document_analysis_status,
    soft_delete_expired,
    update_status,
)
from .document_analysis import (
    DocumentAnalysisConfigurationError,
    DocumentAnalysisProviderError,
    analyse_case_documents,
    document_analysis_is_enabled,
)
from .documents import (
    MAX_CONCURRENT_DOCUMENT_PROCESSORS,
    MAX_DOCUMENTS_PER_CASE,
    MAX_PDF_PAGES_PER_DOCUMENT,
    MAX_TOTAL_PDF_PAGES_PER_CASE,
    MAX_TOTAL_BYTES,
    DocumentValidationError,
    prepare_upload,
)
from .notifications import (
    build_case_notifications,
    build_completion_notifications,
    deliver_pending,
    email_delivery_is_configured,
)
from .schemas import (
    ApplicationCreate,
    AssistantChatRequest,
    AssistantChatResponse,
    FeedbackCreate,
    VoiceTranscriptionResponse,
)
from .security import SlidingWindowRateLimiter, client_key
from .triage import merge_triage, rules_triage
from .voice_transcription import (
    LANGUAGE_CODES,
    MAX_VOICE_AUDIO_BYTES,
    VoiceConfigurationError,
    VoiceProviderError,
    VoiceValidationError,
    transcribe_audio,
    validate_voice_audio,
    voice_input_is_enabled,
)


BASE = Path(__file__).resolve().parent
APP_VERSION = "3.7.20"
logger = logging.getLogger("chinatraderesolve")


STANDARD_REQUEST_BODY_BYTES = 1 * 1024 * 1024
DOCUMENT_UPLOAD_REQUEST_BODY_BYTES = 50 * 1024 * 1024
VOICE_UPLOAD_REQUEST_BODY_BYTES = 5 * 1024 * 1024


class RequestBodyLimitMiddleware:
    """Reject oversized HTTP bodies before Starlette parses JSON or multipart.

    The body is copied into a bounded spooled temporary file and then replayed
    to FastAPI. Small forms stay in memory; larger document uploads spill to
    temporary disk. This also enforces the limit for chunked requests that do
    not provide Content-Length.
    """

    def __init__(self, app):
        self.app = app

    @staticmethod
    def _limit(scope: dict[str, Any]) -> int | None:
        if scope.get("type") != "http":
            return None
        method = str(scope.get("method") or "GET").upper()
        if method not in {"POST", "PUT", "PATCH"}:
            return None
        path = str(scope.get("path") or "")
        if path.startswith("/case/") and path.endswith("/documents"):
            return DOCUMENT_UPLOAD_REQUEST_BODY_BYTES
        if path == "/api/assistant/transcribe":
            return VOICE_UPLOAD_REQUEST_BODY_BYTES
        return STANDARD_REQUEST_BODY_BYTES

    async def __call__(self, scope, receive, send) -> None:
        limit = self._limit(scope)
        if limit is None:
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        raw_length = headers.get(b"content-length", b"").decode("ascii", errors="ignore").strip()
        if raw_length:
            try:
                if int(raw_length) > limit:
                    await self._reject(scope, receive, send)
                    return
            except ValueError:
                # The bounded read below still protects malformed or absent lengths.
                pass

        spool = tempfile.SpooledTemporaryFile(max_size=1 * 1024 * 1024, mode="w+b")
        total = 0
        disconnected = False
        try:
            while True:
                message = await receive()
                message_type = message.get("type")
                if message_type == "http.disconnect":
                    disconnected = True
                    break
                if message_type != "http.request":
                    continue
                chunk = message.get("body", b"")
                total += len(chunk)
                if total > limit:
                    await self._reject(scope, receive, send)
                    return
                if chunk:
                    spool.write(chunk)
                if not message.get("more_body", False):
                    break

            spool.seek(0)
            finished = False

            async def replay_receive():
                nonlocal finished
                if disconnected:
                    return {"type": "http.disconnect"}
                if finished:
                    return {"type": "http.request", "body": b"", "more_body": False}
                chunk = spool.read(64 * 1024)
                if chunk:
                    more = spool.tell() < total
                    if not more:
                        finished = True
                    return {"type": "http.request", "body": chunk, "more_body": more}
                finished = True
                return {"type": "http.request", "body": b"", "more_body": False}

            await self.app(scope, replay_receive, send)
        finally:
            spool.close()

    @staticmethod
    async def _reject(scope, receive, send) -> None:
        response = JSONResponse(
            {"detail": "Request body is too large"},
            status_code=413,
            headers={"Connection": "close"},
        )
        await response(scope, receive, send)


def _document_analysis_stale_seconds() -> int:
    return max(300, int(settings.document_analysis_timeout_seconds * 3 + 60))


async def _maintenance_loop() -> None:
    """Retry queued mail and enforce retention without relying on a redeploy."""
    next_retention_check = time.monotonic() + settings.retention_check_interval_seconds
    while True:
        try:
            if email_delivery_is_configured():
                await asyncio.to_thread(deliver_pending)
            recovered = await asyncio.to_thread(
                fail_running_document_analyses_on_startup,
                _document_analysis_stale_seconds(),
            )
            if recovered:
                logger.warning("Marked %s stale document analyses as failed", recovered)
            if time.monotonic() >= next_retention_check:
                removed = await asyncio.to_thread(
                    soft_delete_expired,
                    settings.retention_days,
                    settings.inactive_retention_days,
                )
                if removed:
                    logger.info("Anonymised %s expired closed or inactive cases", removed)
                next_retention_check = time.monotonic() + settings.retention_check_interval_seconds
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Periodic maintenance failed")
        await asyncio.sleep(settings.maintenance_interval_seconds)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Apply retention, recover abandoned jobs and start periodic maintenance."""
    soft_delete_expired(settings.retention_days, settings.inactive_retention_days)
    recovered = fail_running_document_analyses_on_startup(_document_analysis_stale_seconds())
    if recovered:
        logger.warning("Marked %s stale document analyses as failed", recovered)
    maintenance_task = asyncio.create_task(_maintenance_loop())
    try:
        yield
    finally:
        maintenance_task.cancel()
        try:
            await maintenance_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="ChinaTradeResolve Free Access",
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
_runtime_session_secret = (
    settings.app_secret
    if app_secret_is_secure(settings.app_secret)
    else secrets.token_urlsafe(48)
)
app.add_middleware(
    SessionMiddleware,
    secret_key=_runtime_session_secret,
    same_site="lax",
    https_only=settings.public_base_url.startswith("https://"),
    max_age=3600,
)
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=6)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")
limiter = SlidingWindowRateLimiter()
admin_login_limiter = SlidingWindowRateLimiter(limit=5, window_seconds=900)
assistant_limiter = SlidingWindowRateLimiter(limit=18, window_seconds=600)
assistant_ip_flood_limiter = SlidingWindowRateLimiter(limit=90, window_seconds=600)
voice_attempt_limiter = SlidingWindowRateLimiter(limit=120, window_seconds=600)
voice_limiter = SlidingWindowRateLimiter(limit=10, window_seconds=1800)
document_upload_limiter = SlidingWindowRateLimiter(limit=12, window_seconds=900)
document_analysis_limiter = SlidingWindowRateLimiter(limit=4, window_seconds=1800)
init_db()


def admin_configuration_is_secure() -> bool:
    """Require both persistent secrets before administrator sessions are enabled."""
    return bool(
        admin_token_is_secure(settings.admin_token)
        and app_secret_is_secure(settings.app_secret)
    )


def privacy_configuration_is_complete() -> bool:
    return bool(
        (settings.data_controller_name or "").strip()
        and (settings.data_controller_address or "").strip()
    )


def database_is_available() -> bool:
    """Return whether the configured database accepts a minimal query.

    Readiness must include the application's persistent store. Configuration-only
    checks can otherwise advertise an instance as ready during a database outage.
    """
    try:
        conn = connect()
        try:
            conn.execute("SELECT 1").fetchone()
        finally:
            conn.close()
        return True
    except Exception:
        logger.exception("Database readiness check failed")
        return False


def launch_readiness_checks() -> dict[str, bool]:
    """Expose non-secret pre-launch requirements in one auditable place."""
    return {
        "administrator_security": admin_configuration_is_secure(),
        "privacy_identity": privacy_configuration_is_complete(),
        "https_public_url": settings.public_base_url.startswith("https://"),
        "email_delivery": email_delivery_is_configured(),
        "bot_protection": turnstile_is_enabled(),
        "database_storage": database_is_available(),
    }


def public_launch_is_ready() -> bool:
    return all(launch_readiness_checks().values())


def public_launch_is_blocked() -> bool:
    return bool(settings.public_launch_mode and not public_launch_is_ready())


def unavailable_until_configured(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="service_unavailable.html",
        context={"contact_email": settings.contact_email},
        status_code=503,
    )


def is_admin(request: Request) -> bool:
    return bool(admin_configuration_is_secure() and request.session.get("admin"))


def require_admin(request: Request) -> None:
    if not admin_configuration_is_secure():
        raise HTTPException(status_code=503, detail="Administrator security settings are incomplete")
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Admin authentication required")


def admin_csrf_token(request: Request) -> str:
    token = str(request.session.get("csrf_token") or "")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def require_admin_csrf(request: Request, provided: str) -> None:
    require_admin(request)
    expected = str(request.session.get("csrf_token") or "")
    if not expected or not secrets.compare_digest(provided or "", expected):
        raise HTTPException(status_code=403, detail="Invalid administrator form token")


def public_rate_session_key(request: Request) -> str:
    """Return a stable browser-session bucket without storing a raw IP address."""
    token = str(request.session.get("public_rate_id") or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{20,80}", token):
        token = secrets.token_urlsafe(24)
        request.session["public_rate_id"] = token
    return token


def usage_subject(request: Request, purpose: str) -> str:
    token = public_rate_session_key(request)
    return hashlib.sha256(
        f"{_runtime_session_secret}:{purpose}:{token}".encode("utf-8")
    ).hexdigest()[:32]


def voice_rate_session_key(request: Request) -> str:
    """Backward-compatible alias used by voice short-window buckets."""
    return public_rate_session_key(request)


def make_reference() -> str:
    year = datetime.now(timezone.utc).year
    return f"CTR-{year}-{secrets.token_hex(5).upper()}"


def safe_support_url() -> str | None:
    raw = (settings.support_url or "").strip()
    if not raw or any(ord(char) < 33 for char in raw):
        return None
    try:
        parsed = urlparse(raw)
        hostname = (parsed.hostname or "").casefold()
        parsed.port
        hostname.encode("idna")
    except (UnicodeError, ValueError):
        return None
    if not parsed.netloc or not hostname or parsed.username or parsed.password:
        return None
    if parsed.scheme != "https" and hostname not in {"localhost", "127.0.0.1", "::1"}:
        return None
    return raw


def safe_paypal_support_url() -> str | None:
    """Return only a PayPal-hosted voluntary-support payment link."""
    raw = (settings.paypal_support_url or "").strip()
    if not raw or any(ord(char) < 33 for char in raw):
        return None
    try:
        parsed = urlparse(raw)
        hostname = (parsed.hostname or "").casefold()
        parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme != "https"
        or hostname != "www.paypal.com"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or not re.fullmatch(r"/ncp/payment/[A-Za-z0-9]+", parsed.path)
    ):
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
    return _valid_bitcoin_bech32(address)


_BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _bech32_polymod(values: list[int]) -> int:
    checksum = 1
    generators = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)
    for value in values:
        top = checksum >> 25
        checksum = ((checksum & 0x1FFFFFF) << 5) ^ value
        for index, generator in enumerate(generators):
            if (top >> index) & 1:
                checksum ^= generator
    return checksum


def _convert_bits(values: list[int], from_bits: int, to_bits: int) -> bytes | None:
    accumulator = 0
    bit_count = 0
    output = bytearray()
    for value in values:
        if value < 0 or value >> from_bits:
            return None
        accumulator = (accumulator << from_bits) | value
        bit_count += from_bits
        while bit_count >= to_bits:
            bit_count -= to_bits
            output.append((accumulator >> bit_count) & ((1 << to_bits) - 1))
    if bit_count >= from_bits or ((accumulator << (to_bits - bit_count)) & ((1 << to_bits) - 1)):
        return None
    return bytes(output)


def _valid_bitcoin_bech32(address: str) -> bool:
    """Validate a mainnet SegWit Bech32/Bech32m address and its checksum."""
    if not (14 <= len(address) <= 90) or (address.lower() != address and address.upper() != address):
        return False
    normalized = address.lower()
    separator = normalized.rfind("1")
    if separator != 2 or normalized[:separator] != "bc" or len(normalized) - separator < 7:
        return False
    try:
        values = [_BECH32_CHARSET.index(char) for char in normalized[separator + 1:]]
    except ValueError:
        return False
    # HRP expansion for "bc": high bits, separator zero, then low bits.
    checksum_kind = _bech32_polymod([3, 3, 0, 2, 3] + values)
    if checksum_kind not in {1, 0x2BC830A3}:
        return False
    payload = values[:-6]
    if not payload or payload[0] > 16:
        return False
    witness_program = _convert_bits(payload[1:], 5, 8)
    if witness_program is None or not 2 <= len(witness_program) <= 40:
        return False
    if payload[0] == 0:
        return checksum_kind == 1 and len(witness_program) in {20, 32}
    return checksum_kind == 0x2BC830A3


def _valid_tron(address: str) -> bool:
    payload = _base58check_payload(address)
    return bool(payload and len(payload) == 21 and payload[0] == 0x41)


def _valid_eth(address: str) -> bool:
    return bool(re.fullmatch(r"0x[a-fA-F0-9]{40}", address) and is_checksum_address(address))


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
    return bool(
        settings.enable_voluntary_support
        and (safe_paypal_support_url() or safe_support_url() or crypto_wallets())
    )


def turnstile_is_enabled() -> bool:
    return bool(settings.turnstile_site_key and settings.turnstile_secret_key)


async def verify_turnstile(token: str, request: Request) -> bool:
    if not turnstile_is_enabled():
        return True
    if not token.strip():
        return False
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={
                    "secret": settings.turnstile_secret_key,
                    "response": token,
                    "remoteip": client_key(request),
                },
            )
            response.raise_for_status()
            result = response.json()
            return bool(isinstance(result, dict) and result.get("success") is True)
    except (httpx.HTTPError, ValueError, TypeError):
        logger.exception("Turnstile verification failed")
        raise HTTPException(status_code=503, detail="Bot protection is temporarily unavailable")


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
    response.headers.setdefault("X-App-Version", APP_VERSION)
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(self), geolocation=()")
    turnstile_sources = " https://challenges.cloudflare.com" if turnstile_is_enabled() else ""
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; style-src 'self' 'unsafe-inline'; "
        f"script-src 'self' 'unsafe-inline'{turnstile_sources}; "
        "img-src 'self' data:; "
        f"connect-src 'self'{turnstile_sources}; frame-src 'self'{turnstile_sources}; "
        "form-action 'self'; frame-ancestors 'none'; base-uri 'self'",
    )
    if settings.public_base_url.startswith("https://"):
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if request.url.path.startswith(("/admin", "/case/")):
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("X-Robots-Tag", "noindex, nofollow, noarchive")
    return response



STATUS_LABELS = {
    "submitted": "Получено", "needs_information": "Нужна информация",
    "pilot_candidate": "Кандидат на бесплатную помощь", "human_review": "Ручная проверка",
    "declined": "Отклонено", "accepted": "Принято", "closed": "Закрыто",
}
RISK_LABELS = {"critical": "Критический", "high": "Высокий", "medium": "Средний", "low": "Низкий"}
LANGUAGE_LABELS = {"English": "Английский", "French": "Французский", "German": "Немецкий", "Spanish": "Испанский", "Russian": "Русский", "Serbian": "Сербский"}
ACTOR_LABELS = {"system": "система", "triage": "автопроверка", "document_ai": "ИИ-анализ", "admin": "администратор", "client": "клиент"}
EVENT_LABELS = {"application_created": "заявка создана", "triage_completed": "автопроверка завершена", "status_updated": "статус изменён", "feedback_submitted": "отзыв отправлен", "triage_recomputed": "автопроверка повторена", "document_uploaded": "документ загружен", "document_deleted": "документ удалён", "ai_consent_granted": "согласие на ИИ-анализ подтверждено", "document_analysis_started": "ИИ-анализ документов запущен", "document_analysis_unavailable": "ИИ-анализ документов недоступен", "document_analysis_failed": "ИИ-анализ документов завершился ошибкой", "documents_analysed": "документы проанализированы"}
EVENT_LABELS["ai_consent_revoked"] = "согласие на будущую ИИ-обработку отозвано"
PROBLEM_LABELS = {
    "Goods not delivered": "Товар не доставлен",
    "Poor quality or defects": "Низкое качество или дефекты",
    "Wrong material or specification": "Неверный материал или спецификация",
    "Questionable documents": "Сомнительные документы",
    "Supplier refuses refund": "Поставщик отказывается возвращать деньги",
    "Marketplace rejected the claim": "Площадка отклонила претензию",
    "Other or multiple issues": "Другая или несколько проблем",
}
RESULT_LABELS = {
    "Full refund": "Полный возврат", "Partial refund": "Частичный возврат", "Replacement": "Замена",
    "Completion of order": "Завершение исполнения заказа", "Negotiated settlement": "Согласованное урегулирование",
    "Not sure": "Пока не определено",
}
CHANNEL_LABELS = {"Direct supplier contract": "Прямой договор с поставщиком", "Other": "Другое"}
PUBLIC_STATUS_LABELS = {
    "English": {"submitted":"Received","needs_information":"Information needed","pilot_candidate":"Eligible for preliminary review","human_review":"Human review","declined":"Declined","accepted":"Accepted","closed":"Closed"},
    "French": {"submitted":"Reçue","needs_information":"Informations nécessaires","pilot_candidate":"Éligible à l’examen préliminaire","human_review":"Vérification humaine","declined":"Refusée","accepted":"Acceptée","closed":"Clôturée"},
    "German": {"submitted":"Eingegangen","needs_information":"Informationen erforderlich","pilot_candidate":"Für die Vorprüfung geeignet","human_review":"Menschliche Prüfung","declined":"Abgelehnt","accepted":"Angenommen","closed":"Abgeschlossen"},
    "Spanish": {"submitted":"Recibida","needs_information":"Se necesita información","pilot_candidate":"Apta para revisión preliminar","human_review":"Revisión humana","declined":"Rechazada","accepted":"Aceptada","closed":"Cerrada"},
    "Russian": {**STATUS_LABELS, "pilot_candidate": "Предварительно подходит для рассмотрения"},
    "Serbian": {"submitted":"Primljeno","needs_information":"Potrebne informacije","pilot_candidate":"Pogodno za preliminarni pregled","human_review":"Ljudski pregled","declined":"Odbijeno","accepted":"Prihvaćeno","closed":"Zatvoreno"},
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
        "notice": "No service fee is required. You may add up to twenty key files below. The classification and document analysis are preliminary evidence organisation, not legal advice or a prediction of outcome.",
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
        "notice": "Оплата не требуется. Ниже можно добавить до двадцати ключевых файлов. Предварительная классификация и анализ документов систематизируют доказательства, но не являются юридической консультацией или прогнозом результата.",
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
        "notice": "Plaćanje nije potrebno. Ispod možete dodati do dvadeset ključnih fajlova. Preliminarna klasifikacija i analiza organizuju dokaze, ali nisu pravni savet niti prognoza ishoda.",
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
        "notice": "Aucun paiement n’est requis. Vous pouvez ajouter jusqu’à vingt fichiers clés ci-dessous. La classification et l’analyse sont une organisation préliminaire des preuves, pas un conseil juridique ni une prévision du résultat.",
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
        "notice": "Es ist keine Zahlung erforderlich. Unten können Sie bis zu zwanzig wichtige Dateien hinzufügen. Einstufung und Dokumentenanalyse sind eine vorläufige Beweisorganisation, keine Rechtsberatung oder Erfolgsprognose.",
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
        "notice": "No se requiere pago. A continuación puede añadir hasta veinte archivos clave. La clasificación y el análisis son una organización preliminar de pruebas, no asesoramiento jurídico ni una predicción del resultado.",
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


DOCUMENT_COPY = {
    "English": {
        "heading": "Add key documents",
        "intro": "Upload up to twenty key PDF or image files: specifications, invoice or payment proof, supplier messages, delivery evidence, or a marketplace decision.",
        "privacy": "Remove passwords, private keys, full card numbers and unnecessary identity documents. Images are re-encoded to remove embedded metadata.",
        "select": "Choose files",
        "consent": "I have the right to share these files and understand they may be processed by AI when AI consent was provided.",
        "upload": "Upload documents",
        "uploaded": "Documents uploaded successfully.",
        "limit": "PDF, JPG, PNG or WebP; maximum 8 MB each and 45 MB total.",
        "none": "No documents uploaded yet.",
        "delete": "Delete",
        "analyse": "Analyse documents with AI",
        "analysing": "The analysis has started. This page updates automatically, and you may return later.",
        "analysis_not_configured": "Automatic document analysis is temporarily unavailable. The uploaded files remain available for human review.",
        "analysis_consent_required": "To analyse these files, confirm the voluntary AI-processing consent below.",
        "analysis_consent": "I voluntarily allow these uploaded files to be processed by AI with mandatory human verification of important conclusions.",
        "analysis_error": "The automated analysis could not be completed. The files remain available for human review.",
        "analysis_title": "Preliminary document analysis",
        "analysis_notice": "This is evidence organisation, not legal advice, authentication or a prediction of success. Important conclusions require human verification.",
        "readiness": "Evidence readiness",
        "inventory": "Document inventory",
        "timeline": "Chronology",
        "evidence": "Key evidence",
        "contradictions": "Possible contradictions",
        "missing": "Missing evidence",
        "risks": "Risk flags",
        "steps": "Recommended next steps",
        "download": "Open",
        "table_file": "File", "table_type": "Type", "table_date": "Date", "table_readability": "Readability",
        "readiness_breakdown": "How this score is calculated",
        "readiness_explanation": "The percentage measures completeness of the uploaded evidence set, not legal strength or probability of success.",
        "points": "points",
        "readability_labels": {"clear": "Clear", "partial": "Partly readable", "unreadable": "Unreadable"},
        "confidence_labels": {"high": "High confidence", "medium": "Medium confidence", "low": "Low confidence"},
        "readiness_status_labels": {"complete": "Complete", "partial": "Partial", "missing": "Missing", "not_applicable": "Not applicable"},
        "readiness_factor_labels": {"parties": "Parties and supplier", "transaction": "Order and transaction", "specification": "Agreed specification", "payment": "Payment evidence", "communications": "Written communications", "delivery": "Shipment or delivery", "problem_evidence": "Evidence of the reported problem"},
    },
    "Russian": {
        "heading": "Добавьте ключевые документы",
        "intro": "Загрузите до двадцати ключевых PDF или изображений: спецификацию, инвойс или подтверждение оплаты, переписку, доказательства доставки либо решение площадки.",
        "privacy": "Удалите пароли, приватные ключи, полные номера карт и ненужные документы личности. Изображения перекодируются, чтобы удалить встроенные метаданные.",
        "select": "Выберите файлы",
        "consent": "Я имею право передавать эти файлы и понимаю, что при ранее данном согласии они могут обрабатываться ИИ.",
        "upload": "Загрузить документы",
        "uploaded": "Документы успешно загружены.",
        "limit": "PDF, JPG, PNG или WebP; не более 8 МБ каждый и 45 МБ суммарно.",
        "none": "Документы пока не загружены.",
        "delete": "Удалить",
        "analyse": "Проанализировать документы с помощью ИИ",
        "analysing": "Анализ запущен. Страница обновится автоматически; к ней также можно вернуться позже.",
        "analysis_not_configured": "Автоматический анализ документов временно недоступен. Загруженные файлы остаются доступными для ручной проверки.",
        "analysis_consent_required": "Чтобы проанализировать эти файлы, подтвердите добровольное согласие на обработку ИИ ниже.",
        "analysis_consent": "Я добровольно разрешаю обработку загруженных файлов с помощью ИИ при обязательной проверке важных выводов человеком.",
        "analysis_error": "Автоматический анализ завершить не удалось. Файлы остаются доступными для ручной проверки.",
        "analysis_title": "Предварительный анализ документов",
        "analysis_notice": "Это систематизация доказательств, а не юридическая консультация, проверка подлинности или прогноз успеха. Важные выводы должен проверить человек.",
        "readiness": "Готовность доказательств",
        "inventory": "Состав документов",
        "timeline": "Хронология",
        "evidence": "Ключевые доказательства",
        "contradictions": "Возможные противоречия",
        "missing": "Недостающие доказательства",
        "risks": "Факторы риска",
        "steps": "Рекомендуемые следующие шаги",
        "download": "Открыть",
        "table_file": "Файл", "table_type": "Тип", "table_date": "Дата", "table_readability": "Читаемость",
        "readiness_breakdown": "Из чего складывается оценка",
        "readiness_explanation": "Процент показывает полноту загруженного комплекта доказательств, а не юридическую силу дела и не вероятность успеха.",
        "points": "баллов",
        "readability_labels": {"clear": "Хорошо читается", "partial": "Читается частично", "unreadable": "Не читается"},
        "confidence_labels": {"high": "Высокая уверенность", "medium": "Средняя уверенность", "low": "Низкая уверенность"},
        "readiness_status_labels": {"complete": "Есть", "partial": "Частично", "missing": "Отсутствует", "not_applicable": "Не применимо"},
        "readiness_factor_labels": {"parties": "Стороны и поставщик", "transaction": "Заказ и сделка", "specification": "Согласованная спецификация", "payment": "Подтверждение оплаты", "communications": "Письменная переписка", "delivery": "Отгрузка или доставка", "problem_evidence": "Доказательства заявленной проблемы"},
    },
    "Serbian": {
        "heading": "Dodajte ključne dokumente", "intro": "Otpremite do dvadeset ključnih PDF ili slikovnih fajlova: specifikaciju, račun ili dokaz o uplati, poruke dobavljača, dokaz o isporuci ili odluku platforme.",
        "privacy": "Uklonite lozinke, privatne ključeve, pune brojeve kartica i nepotrebna lična dokumenta. Slike se ponovo kodiraju radi uklanjanja metapodataka.",
        "select": "Izaberite fajlove", "consent": "Imam pravo da podelim ove fajlove i razumem da mogu biti obrađeni AI-jem ako sam prethodno dao saglasnost.",
        "upload": "Otpremi dokumente", "uploaded": "Dokumenti su uspešno otpremljeni.", "limit": "PDF, JPG, PNG ili WebP; najviše 8 MB po fajlu i 45 MB ukupno.",
        "none": "Dokumenti još nisu otpremljeni.", "delete": "Obriši", "analyse": "Analiziraj dokumente pomoću AI-ja", "analysing": "Analiza je pokrenuta. Stranica se automatski osvežava, a možete se vratiti i kasnije.",
        "analysis_not_configured": "Automatska analiza dokumenata trenutno nije dostupna. Fajlovi ostaju dostupni za ljudski pregled.", "analysis_consent_required": "Za analizu ovih fajlova potvrdite dobrovoljnu saglasnost za AI obradu ispod.", "analysis_consent": "Dobrovoljno dozvoljavam AI obradu otpremljenih fajlova uz obaveznu ljudsku proveru važnih zaključaka.", "analysis_error": "Automatska analiza nije završena. Fajlovi ostaju dostupni za ljudski pregled.",
        "analysis_title": "Preliminarna analiza dokumenata", "analysis_notice": "Ovo je organizovanje dokaza, a ne pravni savet, potvrda autentičnosti ili prognoza uspeha. Važne zaključke mora proveriti čovek.",
        "readiness": "Spremnost dokaza", "inventory": "Pregled dokumenata", "timeline": "Hronologija", "evidence": "Ključni dokazi", "contradictions": "Moguće protivrečnosti", "missing": "Nedostajući dokazi", "risks": "Faktori rizika", "steps": "Preporučeni sledeći koraci", "download": "Otvori", "table_file": "Fajl", "table_type": "Vrsta", "table_date": "Datum", "table_readability": "Čitljivost",
        "readiness_breakdown": "Kako je ocena izračunata", "readiness_explanation": "Procenat meri potpunost otpremljenih dokaza, a ne pravnu snagu ili verovatnoću uspeha.", "points": "poena",
        "readability_labels": {"clear": "Jasno", "partial": "Delimično čitljivo", "unreadable": "Nečitljivo"}, "confidence_labels": {"high": "Visoka pouzdanost", "medium": "Srednja pouzdanost", "low": "Niska pouzdanost"},
        "readiness_status_labels": {"complete": "Potpuno", "partial": "Delimično", "missing": "Nedostaje", "not_applicable": "Nije primenljivo"},
        "readiness_factor_labels": {"parties": "Strane i dobavljač", "transaction": "Porudžbina i transakcija", "specification": "Dogovorena specifikacija", "payment": "Dokaz o uplati", "communications": "Pisana komunikacija", "delivery": "Otprema ili isporuka", "problem_evidence": "Dokazi prijavljenog problema"},
    },
    "French": {
        "heading": "Ajouter les documents clés", "intro": "Téléversez jusqu’à vingt fichiers PDF ou images essentiels : spécifications, facture ou preuve de paiement, messages du fournisseur, preuve de livraison ou décision de la plateforme.",
        "privacy": "Supprimez les mots de passe, clés privées, numéros de carte complets et pièces d’identité inutiles. Les images sont réencodées pour supprimer les métadonnées.",
        "select": "Choisir les fichiers", "consent": "J’ai le droit de partager ces fichiers et je comprends qu’ils peuvent être traités par l’IA si j’ai déjà donné mon consentement.",
        "upload": "Téléverser les documents", "uploaded": "Documents téléversés avec succès.", "limit": "PDF, JPG, PNG ou WebP ; 8 Mo maximum par fichier et 45 Mo au total.",
        "none": "Aucun document téléversé.", "delete": "Supprimer", "analyse": "Analyser les documents avec l’IA", "analysing": "L’analyse a démarré. La page se met à jour automatiquement et vous pouvez revenir plus tard.",
        "analysis_not_configured": "L’analyse automatique des documents est temporairement indisponible. Les fichiers restent accessibles pour une vérification humaine.", "analysis_consent_required": "Pour analyser ces fichiers, confirmez ci-dessous votre consentement volontaire au traitement par l’IA.", "analysis_consent": "J’autorise volontairement le traitement de ces fichiers par l’IA, avec vérification humaine obligatoire des conclusions importantes.", "analysis_error": "L’analyse automatique n’a pas pu être terminée. Les fichiers restent disponibles pour une vérification humaine.",
        "analysis_title": "Analyse préliminaire des documents", "analysis_notice": "Il s’agit d’une organisation des preuves, pas d’un conseil juridique, d’une authentification ou d’une prévision de succès. Les conclusions importantes doivent être vérifiées par une personne.",
        "readiness": "Préparation des preuves", "inventory": "Inventaire des documents", "timeline": "Chronologie", "evidence": "Éléments de preuve clés", "contradictions": "Contradictions possibles", "missing": "Preuves manquantes", "risks": "Signaux de risque", "steps": "Prochaines étapes recommandées", "download": "Ouvrir", "table_file": "Fichier", "table_type": "Type", "table_date": "Date", "table_readability": "Lisibilité",
        "readiness_breakdown": "Calcul de cette note", "readiness_explanation": "Le pourcentage mesure la complétude des preuves téléversées, et non la solidité juridique ni la probabilité de succès.", "points": "points",
        "readability_labels": {"clear": "Lisible", "partial": "Partiellement lisible", "unreadable": "Illisible"}, "confidence_labels": {"high": "Confiance élevée", "medium": "Confiance moyenne", "low": "Confiance faible"},
        "readiness_status_labels": {"complete": "Complet", "partial": "Partiel", "missing": "Manquant", "not_applicable": "Non applicable"},
        "readiness_factor_labels": {"parties": "Parties et fournisseur", "transaction": "Commande et transaction", "specification": "Spécification convenue", "payment": "Preuve de paiement", "communications": "Communications écrites", "delivery": "Expédition ou livraison", "problem_evidence": "Preuves du problème signalé"},
    },
    "German": {
        "heading": "Wichtige Dokumente hinzufügen", "intro": "Laden Sie bis zu zwanzig wichtige PDF- oder Bilddateien hoch: Spezifikation, Rechnung oder Zahlungsnachweis, Lieferantennachrichten, Liefernachweis oder Plattformentscheidung.",
        "privacy": "Entfernen Sie Passwörter, private Schlüssel, vollständige Kartennummern und unnötige Ausweisdokumente. Bilder werden neu kodiert, um Metadaten zu entfernen.",
        "select": "Dateien auswählen", "consent": "Ich darf diese Dateien weitergeben und verstehe, dass sie bei zuvor erteilter Zustimmung durch KI verarbeitet werden können.",
        "upload": "Dokumente hochladen", "uploaded": "Dokumente erfolgreich hochgeladen.", "limit": "PDF, JPG, PNG oder WebP; höchstens 8 MB je Datei und 45 MB insgesamt.",
        "none": "Noch keine Dokumente hochgeladen.", "delete": "Löschen", "analyse": "Dokumente mit KI analysieren", "analysing": "Die Analyse wurde gestartet. Die Seite aktualisiert sich automatisch; Sie können auch später zurückkehren.",
        "analysis_not_configured": "Die automatische Dokumentenanalyse ist vorübergehend nicht verfügbar. Die Dateien bleiben für eine menschliche Prüfung verfügbar.", "analysis_consent_required": "Bestätigen Sie unten Ihre freiwillige Einwilligung zur KI-Verarbeitung, um diese Dateien zu analysieren.", "analysis_consent": "Ich willige freiwillig in die KI-Verarbeitung dieser Dateien ein; wichtige Schlussfolgerungen müssen von einem Menschen geprüft werden.", "analysis_error": "Die automatische Analyse konnte nicht abgeschlossen werden. Die Dateien bleiben für eine menschliche Prüfung verfügbar.",
        "analysis_title": "Vorläufige Dokumentenanalyse", "analysis_notice": "Dies ist eine Beweisorganisation, keine Rechtsberatung, Echtheitsprüfung oder Erfolgsprognose. Wichtige Schlussfolgerungen müssen menschlich geprüft werden.",
        "readiness": "Beweisbereitschaft", "inventory": "Dokumentenübersicht", "timeline": "Chronologie", "evidence": "Wichtige Belege", "contradictions": "Mögliche Widersprüche", "missing": "Fehlende Belege", "risks": "Risikohinweise", "steps": "Empfohlene nächste Schritte", "download": "Öffnen", "table_file": "Datei", "table_type": "Typ", "table_date": "Datum", "table_readability": "Lesbarkeit",
        "readiness_breakdown": "Berechnung der Bewertung", "readiness_explanation": "Der Prozentsatz misst die Vollständigkeit der hochgeladenen Belege, nicht die rechtliche Stärke oder Erfolgswahrscheinlichkeit.", "points": "Punkte",
        "readability_labels": {"clear": "Gut lesbar", "partial": "Teilweise lesbar", "unreadable": "Unlesbar"}, "confidence_labels": {"high": "Hohe Sicherheit", "medium": "Mittlere Sicherheit", "low": "Geringe Sicherheit"},
        "readiness_status_labels": {"complete": "Vollständig", "partial": "Teilweise", "missing": "Fehlt", "not_applicable": "Nicht anwendbar"},
        "readiness_factor_labels": {"parties": "Parteien und Lieferant", "transaction": "Bestellung und Transaktion", "specification": "Vereinbarte Spezifikation", "payment": "Zahlungsnachweis", "communications": "Schriftliche Kommunikation", "delivery": "Versand oder Lieferung", "problem_evidence": "Nachweise des gemeldeten Problems"},
    },
    "Spanish": {
        "heading": "Añadir documentos clave", "intro": "Suba hasta veinte archivos PDF o imágenes clave: especificaciones, factura o comprobante de pago, mensajes del proveedor, prueba de entrega o decisión de la plataforma.",
        "privacy": "Elimine contraseñas, claves privadas, números completos de tarjeta y documentos de identidad innecesarios. Las imágenes se recodifican para eliminar metadatos.",
        "select": "Elegir archivos", "consent": "Tengo derecho a compartir estos archivos y entiendo que pueden ser procesados por IA si ya di mi consentimiento.",
        "upload": "Subir documentos", "uploaded": "Documentos subidos correctamente.", "limit": "PDF, JPG, PNG o WebP; máximo 8 MB por archivo y 45 MB en total.",
        "none": "Todavía no se han subido documentos.", "delete": "Eliminar", "analyse": "Analizar documentos con IA", "analysing": "El análisis ha comenzado. La página se actualiza automáticamente y puede volver más tarde.",
        "analysis_not_configured": "El análisis automático de documentos no está disponible temporalmente. Los archivos siguen disponibles para revisión humana.", "analysis_consent_required": "Para analizar estos archivos, confirme abajo su consentimiento voluntario para el tratamiento con IA.", "analysis_consent": "Autorizo voluntariamente el tratamiento de estos archivos con IA, con verificación humana obligatoria de las conclusiones importantes.", "analysis_error": "No se pudo completar el análisis automático. Los archivos siguen disponibles para revisión humana.",
        "analysis_title": "Análisis preliminar de documentos", "analysis_notice": "Esto organiza pruebas; no es asesoramiento jurídico, autenticación ni una predicción de éxito. Las conclusiones importantes requieren verificación humana.",
        "readiness": "Preparación de las pruebas", "inventory": "Inventario de documentos", "timeline": "Cronología", "evidence": "Pruebas clave", "contradictions": "Posibles contradicciones", "missing": "Pruebas faltantes", "risks": "Señales de riesgo", "steps": "Próximos pasos recomendados", "download": "Abrir", "table_file": "Archivo", "table_type": "Tipo", "table_date": "Fecha", "table_readability": "Legibilidad",
        "readiness_breakdown": "Cómo se calcula la puntuación", "readiness_explanation": "El porcentaje mide la integridad del conjunto de pruebas subido, no la fuerza jurídica ni la probabilidad de éxito.", "points": "puntos",
        "readability_labels": {"clear": "Legible", "partial": "Parcialmente legible", "unreadable": "Ilegible"}, "confidence_labels": {"high": "Confianza alta", "medium": "Confianza media", "low": "Confianza baja"},
        "readiness_status_labels": {"complete": "Completo", "partial": "Parcial", "missing": "Falta", "not_applicable": "No aplicable"},
        "readiness_factor_labels": {"parties": "Partes y proveedor", "transaction": "Pedido y transacción", "specification": "Especificación acordada", "payment": "Prueba de pago", "communications": "Comunicaciones escritas", "delivery": "Envío o entrega", "problem_evidence": "Pruebas del problema comunicado"},
    },
}

_ANALYSIS_BUDGET_COPY = {
    "English": "The daily automatic-analysis budget has been reached. The files remain available for human review; please try again tomorrow.",
    "Russian": "Дневной лимит автоматического анализа исчерпан. Файлы доступны для ручной проверки; попробуйте снова завтра.",
    "Serbian": "Dnevni limit automatske analize je dostignut. Fajlovi ostaju dostupni za ljudski pregled; pokušajte ponovo sutra.",
    "French": "Le budget quotidien d’analyse automatique est épuisé. Les fichiers restent disponibles pour une vérification humaine ; réessayez demain.",
    "German": "Das tägliche Budget für automatische Analysen ist erreicht. Die Dateien bleiben für die menschliche Prüfung verfügbar; versuchen Sie es morgen erneut.",
    "Spanish": "Se alcanzó el límite diario de análisis automático. Los archivos siguen disponibles para revisión humana; inténtelo mañana.",
}
for _language, _message in _ANALYSIS_BUDGET_COPY.items():
    DOCUMENT_COPY[_language]["analysis_budget"] = _message

_PDF_PAGE_LIMIT_COPY = {
    "English": "Each PDF may contain up to 100 pages; one case may contain up to 200 PDF pages.",
    "Russian": "В одном PDF допускается до 100 страниц, в одном деле — до 200 PDF-страниц.",
    "Serbian": "Jedan PDF može imati do 100 strana, a jedan slučaj ukupno do 200 PDF strana.",
    "French": "Chaque PDF peut contenir jusqu’à 100 pages, et un dossier jusqu’à 200 pages PDF au total.",
    "German": "Eine PDF-Datei darf bis zu 100 Seiten enthalten, ein Fall insgesamt bis zu 200 PDF-Seiten.",
    "Spanish": "Cada PDF puede contener hasta 100 páginas y un caso hasta 200 páginas PDF en total.",
}
for _language, _message in _PDF_PAGE_LIMIT_COPY.items():
    DOCUMENT_COPY[_language]["limit"] += " " + _message

PRIVACY_ACTION_COPY = {
    "English": {"title":"Privacy controls","revoke":"Withdraw AI consent","revoke_note":"This prevents future AI processing and removes the stored AI report. Uploaded files remain available for human review.","revoke_confirm":"I confirm that I withdraw consent for future AI processing.","delete":"Permanently delete this case","delete_note":"This immediately removes the case details, uploaded documents, report, feedback and notification records. This cannot be undone.","delete_confirm":"I understand that this deletion is permanent.","submit_revoke":"Withdraw consent","submit_delete":"Delete case permanently"},
    "Russian": {"title":"Управление данными","revoke":"Отозвать согласие на ИИ","revoke_note":"Будущая ИИ-обработка прекратится, сохранённый ИИ-отчёт будет удалён. Файлы останутся для ручной проверки.","revoke_confirm":"Я подтверждаю отзыв согласия на будущую ИИ-обработку.","delete":"Безвозвратно удалить дело","delete_note":"Будут немедленно удалены сведения дела, документы, отчёт, отзыв и записи уведомлений. Отменить это действие нельзя.","delete_confirm":"Я понимаю, что удаление является безвозвратным.","submit_revoke":"Отозвать согласие","submit_delete":"Удалить дело навсегда"},
    "Serbian": {"title":"Upravljanje podacima","revoke":"Povuci AI saglasnost","revoke_note":"Buduća AI obrada se zaustavlja i sačuvani AI izveštaj se briše. Fajlovi ostaju za ljudski pregled.","revoke_confirm":"Potvrđujem povlačenje saglasnosti za buduću AI obradu.","delete":"Trajno obriši slučaj","delete_note":"Podaci slučaja, dokumenti, izveštaj, povratne informacije i zapisi obaveštenja biće odmah obrisani. Radnja se ne može opozvati.","delete_confirm":"Razumem da je brisanje trajno.","submit_revoke":"Povuci saglasnost","submit_delete":"Trajno obriši slučaj"},
    "French": {"title":"Gestion des données","revoke":"Retirer le consentement à l’IA","revoke_note":"Le traitement futur par l’IA cesse et le rapport IA enregistré est supprimé. Les fichiers restent disponibles pour la vérification humaine.","revoke_confirm":"Je confirme le retrait de mon consentement au traitement futur par l’IA.","delete":"Supprimer définitivement ce dossier","delete_note":"Les données, documents, rapport, avis et notifications seront supprimés immédiatement. Cette action est irréversible.","delete_confirm":"Je comprends que la suppression est définitive.","submit_revoke":"Retirer le consentement","submit_delete":"Supprimer définitivement"},
    "German": {"title":"Datenverwaltung","revoke":"KI-Einwilligung widerrufen","revoke_note":"Künftige KI-Verarbeitung endet und der gespeicherte KI-Bericht wird gelöscht. Dateien bleiben für die menschliche Prüfung verfügbar.","revoke_confirm":"Ich widerrufe meine Einwilligung zur künftigen KI-Verarbeitung.","delete":"Fall dauerhaft löschen","delete_note":"Falldaten, Dokumente, Bericht, Rückmeldung und Benachrichtigungen werden sofort gelöscht. Dies kann nicht rückgängig gemacht werden.","delete_confirm":"Ich verstehe, dass die Löschung dauerhaft ist.","submit_revoke":"Einwilligung widerrufen","submit_delete":"Fall dauerhaft löschen"},
    "Spanish": {"title":"Control de datos","revoke":"Retirar el consentimiento de IA","revoke_note":"Se detiene el tratamiento futuro con IA y se elimina el informe de IA guardado. Los archivos siguen disponibles para revisión humana.","revoke_confirm":"Confirmo que retiro el consentimiento para el tratamiento futuro con IA.","delete":"Eliminar el caso permanentemente","delete_note":"Los datos, documentos, informe, opinión y notificaciones se eliminarán de inmediato. La acción no se puede deshacer.","delete_confirm":"Entiendo que la eliminación es permanente.","submit_revoke":"Retirar consentimiento","submit_delete":"Eliminar permanentemente"},
}


CASE_PROGRESS_COPY = {
    "English": {"progress":"Case progress","received":"Application received","screening":"Preliminary screening","evidence":"Documents and review","outcome":"Outcome","done":"Completed","current":"Current","pending":"Pending","last_updated":"Last updated","response_target":"Initial human response target: within 2 business days.","next_action":"Your next step","next_upload":"Add only the key documents that support the order, payment, supplier promises and reported problem.","next_information":"Review the requested information above and add the relevant details or documents.","next_analysis":"You may start automatic document organisation below, or wait for human review.","next_wait":"Analysis is running. You may safely return later using this private link.","next_human":"No further action is required now. Keep this private link and wait for the human review.","next_terminal":"No further documents are required for this case.","attention_level":"Attention level","attention_note":"This reflects urgency and review routing, not the chance of success.","private_link":"Private case link","private_warning":"Anyone with this link can open the case. Keep it private.","copy_link":"Copy link","copied":"Link copied.","download_access":"Download access note"},
    "Russian": {"progress":"Ход рассмотрения","received":"Заявка получена","screening":"Предварительная проверка","evidence":"Документы и проверка","outcome":"Результат","done":"Завершено","current":"Текущий этап","pending":"Ожидает","last_updated":"Последнее обновление","response_target":"Ориентир первого ответа человека: в течение 2 рабочих дней.","next_action":"Ваш следующий шаг","next_upload":"Добавьте только ключевые документы, подтверждающие заказ, оплату, обещания поставщика и заявленную проблему.","next_information":"Проверьте запрошенную выше информацию и добавьте относящиеся к ней сведения или документы.","next_analysis":"Ниже можно запустить автоматическую систематизацию документов либо дождаться ручной проверки.","next_wait":"Анализ выполняется. Вы можете безопасно вернуться позже по этой приватной ссылке.","next_human":"Сейчас дополнительных действий не требуется. Сохраните приватную ссылку и дождитесь ручной проверки.","next_terminal":"Дополнительные документы по этому делу сейчас не требуются.","attention_level":"Уровень внимания","attention_note":"Показатель отражает срочность и порядок проверки, а не вероятность успеха.","private_link":"Приватная ссылка дела","private_warning":"Любой человек с этой ссылкой сможет открыть дело. Храните её в тайне.","copy_link":"Скопировать ссылку","copied":"Ссылка скопирована.","download_access":"Скачать памятку доступа"},
    "Serbian": {"progress":"Tok slučaja","received":"Prijava primljena","screening":"Preliminarni pregled","evidence":"Dokumenti i pregled","outcome":"Ishod","done":"Završeno","current":"Trenutno","pending":"Na čekanju","last_updated":"Poslednje ažuriranje","response_target":"Cilj prvog ljudskog odgovora: u roku od 2 radna dana.","next_action":"Vaš sledeći korak","next_upload":"Dodajte samo ključne dokumente koji potvrđuju porudžbinu, plaćanje, obećanja dobavljača i prijavljeni problem.","next_information":"Pregledajte tražene informacije iznad i dodajte odgovarajuće podatke ili dokumente.","next_analysis":"Možete pokrenuti automatsko organizovanje dokumenata ispod ili sačekati ljudski pregled.","next_wait":"Analiza je u toku. Možete se kasnije vratiti pomoću privatnog linka.","next_human":"Sada nije potrebna dodatna radnja. Sačuvajte privatni link i sačekajte ljudski pregled.","next_terminal":"Dodatni dokumenti trenutno nisu potrebni.","attention_level":"Nivo pažnje","attention_note":"Ovo pokazuje hitnost i usmeravanje pregleda, a ne verovatnoću uspeha.","private_link":"Privatni link slučaja","private_warning":"Svako sa ovim linkom može otvoriti slučaj. Čuvajte ga privatno.","copy_link":"Kopiraj link","copied":"Link je kopiran.","download_access":"Preuzmi belešku za pristup"},
    "French": {"progress":"Avancement du dossier","received":"Demande reçue","screening":"Examen préliminaire","evidence":"Documents et vérification","outcome":"Résultat","done":"Terminé","current":"Étape actuelle","pending":"En attente","last_updated":"Dernière mise à jour","response_target":"Objectif de première réponse humaine : sous 2 jours ouvrés.","next_action":"Votre prochaine étape","next_upload":"Ajoutez uniquement les documents essentiels concernant la commande, le paiement, les promesses du fournisseur et le problème signalé.","next_information":"Consultez les informations demandées ci-dessus et ajoutez les éléments ou documents correspondants.","next_analysis":"Vous pouvez lancer l’organisation automatique des documents ci-dessous ou attendre la vérification humaine.","next_wait":"L’analyse est en cours. Vous pouvez revenir plus tard avec ce lien privé.","next_human":"Aucune action supplémentaire n’est requise. Conservez ce lien et attendez la vérification humaine.","next_terminal":"Aucun document supplémentaire n’est requis actuellement.","attention_level":"Niveau d’attention","attention_note":"Il reflète l’urgence et l’orientation du dossier, pas les chances de succès.","private_link":"Lien privé du dossier","private_warning":"Toute personne possédant ce lien peut ouvrir le dossier. Gardez-le confidentiel.","copy_link":"Copier le lien","copied":"Lien copié.","download_access":"Télécharger la note d’accès"},
    "German": {"progress":"Fallfortschritt","received":"Antrag eingegangen","screening":"Vorprüfung","evidence":"Dokumente und Prüfung","outcome":"Ergebnis","done":"Abgeschlossen","current":"Aktuell","pending":"Ausstehend","last_updated":"Zuletzt aktualisiert","response_target":"Ziel für die erste menschliche Antwort: innerhalb von 2 Werktagen.","next_action":"Ihr nächster Schritt","next_upload":"Fügen Sie nur wichtige Dokumente zu Bestellung, Zahlung, Lieferantenzusagen und gemeldetem Problem hinzu.","next_information":"Prüfen Sie die oben angeforderten Informationen und ergänzen Sie die passenden Angaben oder Dokumente.","next_analysis":"Sie können unten die automatische Dokumentenorganisation starten oder auf die menschliche Prüfung warten.","next_wait":"Die Analyse läuft. Mit diesem privaten Link können Sie später zurückkehren.","next_human":"Derzeit ist keine weitere Aktion erforderlich. Speichern Sie den privaten Link und warten Sie auf die menschliche Prüfung.","next_terminal":"Derzeit sind keine weiteren Dokumente erforderlich.","attention_level":"Aufmerksamkeitsstufe","attention_note":"Sie zeigt Dringlichkeit und Prüfungsweg, nicht die Erfolgswahrscheinlichkeit.","private_link":"Privater Falllink","private_warning":"Jeder mit diesem Link kann den Fall öffnen. Bewahren Sie ihn vertraulich auf.","copy_link":"Link kopieren","copied":"Link kopiert.","download_access":"Zugangsnotiz herunterladen"},
    "Spanish": {"progress":"Progreso del caso","received":"Solicitud recibida","screening":"Revisión preliminar","evidence":"Documentos y revisión","outcome":"Resultado","done":"Completado","current":"Etapa actual","pending":"Pendiente","last_updated":"Última actualización","response_target":"Objetivo de primera respuesta humana: dentro de 2 días laborables.","next_action":"Su siguiente paso","next_upload":"Añada solo documentos clave sobre el pedido, el pago, las promesas del proveedor y el problema comunicado.","next_information":"Revise la información solicitada arriba y añada los datos o documentos correspondientes.","next_analysis":"Puede iniciar la organización automática de documentos o esperar la revisión humana.","next_wait":"El análisis está en curso. Puede volver más tarde mediante este enlace privado.","next_human":"Ahora no se requiere ninguna acción adicional. Guarde el enlace privado y espere la revisión humana.","next_terminal":"Actualmente no se necesitan más documentos.","attention_level":"Nivel de atención","attention_note":"Refleja la urgencia y el enrutamiento de la revisión, no la probabilidad de éxito.","private_link":"Enlace privado del caso","private_warning":"Cualquier persona con este enlace puede abrir el caso. Manténgalo privado.","copy_link":"Copiar enlace","copied":"Enlace copiado.","download_access":"Descargar nota de acceso"},
}


def public_case_progress(
    case: dict[str, Any],
    documents: list[dict[str, Any]],
    analysis: dict[str, Any] | None,
    copy: dict[str, str],
) -> tuple[list[dict[str, str]], str]:
    status = str(case.get("status") or "submitted")
    analysis_status = str((analysis or {}).get("status") or "")
    terminal = status in {"declined", "closed"}
    outcome_complete = status in {"accepted", "declined", "closed"}
    screening_state = "current" if status == "submitted" else "done"
    evidence_state = "pending"
    if terminal or analysis_status == "completed":
        evidence_state = "done"
    elif documents or status in {"needs_information", "human_review", "pilot_candidate"}:
        evidence_state = "current"
    outcome_state = "done" if outcome_complete else "pending"
    stages = [
        {"label": copy["received"], "state": "done"},
        {"label": copy["screening"], "state": screening_state},
        {"label": copy["evidence"], "state": evidence_state},
        {"label": copy["outcome"], "state": outcome_state},
    ]
    if terminal:
        next_step = copy["next_terminal"]
    elif status == "needs_information":
        next_step = copy["next_information"]
    elif not documents:
        next_step = copy["next_upload"]
    elif analysis_status == "running":
        next_step = copy["next_wait"]
    elif document_analysis_is_enabled() and analysis_status != "completed":
        next_step = copy["next_analysis"]
    else:
        next_step = copy["next_human"]
    return stages, next_step


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    if public_launch_is_blocked():
        return unavailable_until_configured(request)
    wallets = crypto_wallets()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "support_enabled": support_is_available(),
            "paypal_support_enabled": bool(
                settings.enable_voluntary_support and safe_paypal_support_url()
            ),
            "crypto_wallets": wallets,
            "contact_email": settings.contact_email,
            "ai_assistant_enabled": assistant_is_enabled(),
            "voice_input_enabled": voice_input_is_enabled(),
            "voice_max_seconds": settings.voice_max_seconds,
            "document_analysis_enabled": document_analysis_is_enabled(),
            "email_delivery_configured": email_delivery_is_configured(),
            "turnstile_site_key": settings.turnstile_site_key if turnstile_is_enabled() else "",
            "canonical_url": settings.public_base_url + "/",
            "operator_profile": (settings.operator_profile or "").strip(),
            "operator_credentials": (settings.operator_credentials or "").strip(),
            "operator_registration": (settings.data_controller_registration or "").strip(),
        },
    )


@app.get("/health")
def health() -> dict[str, Any]:
    """Lightweight liveness information without exposing usage budgets."""
    readiness = launch_readiness_checks()
    return {
        "status": "ok",
        "version": APP_VERSION,
        "document_limit": MAX_DOCUMENTS_PER_CASE,
        "document_processing_workers": MAX_CONCURRENT_DOCUMENT_PROCESSORS,
        "max_pdf_pages_per_document": MAX_PDF_PAGES_PER_DOCUMENT,
        "max_pdf_pages_per_case": MAX_TOTAL_PDF_PAGES_PER_CASE,
        "standard_request_limit_mb": STANDARD_REQUEST_BODY_BYTES // (1024 * 1024),
        "document_upload_request_limit_mb": DOCUMENT_UPLOAD_REQUEST_BODY_BYTES // (1024 * 1024),
        "voice_upload_request_limit_mb": VOICE_UPLOAD_REQUEST_BODY_BYTES // (1024 * 1024),
        "voice_input_enabled": voice_input_is_enabled(),
        "voice_max_seconds": settings.voice_max_seconds,
        "ai_assistant_enabled": assistant_is_enabled(),
        "document_analysis_enabled": document_analysis_is_enabled(),
        "free_access_mode": settings.free_access_mode,
        "support_enabled": support_is_available(),
        "paypal_support_enabled": bool(
            settings.enable_voluntary_support and safe_paypal_support_url()
        ),
        "openai_billing_ready": settings.openai_billing_ready,
        "secure_configuration": admin_configuration_is_secure(),
        "public_url_https": settings.public_base_url.startswith("https://"),
        "email_delivery_configured": email_delivery_is_configured(),
        "privacy_configuration_complete": privacy_configuration_is_complete(),
        "bot_protection_enabled": turnstile_is_enabled(),
        "public_launch_mode": settings.public_launch_mode,
        "public_launch_ready": all(readiness.values()),
        "readiness_checks": readiness,
    }


@app.get("/ready")
def readiness() -> JSONResponse:
    checks = launch_readiness_checks()
    ready = all(checks.values())
    return JSONResponse(
        {"status": "ready" if ready else "not_ready", "version": APP_VERSION, "checks": checks},
        status_code=200 if ready else 503,
    )


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots() -> PlainTextResponse:
    if not public_launch_is_ready():
        return PlainTextResponse(
            "User-agent: *\nDisallow: /\n",
            headers={"Cache-Control": "public, max-age=300"},
        )
    base_url = settings.public_base_url.rstrip("/")
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /api/\n"
        "Disallow: /case/\n"
        f"Sitemap: {base_url}/sitemap.xml\n"
    )
    return PlainTextResponse(body, headers={"Cache-Control": "public, max-age=3600"})


@app.get("/sitemap.xml")
def sitemap() -> Response:
    base_url = xml_escape(settings.public_base_url.rstrip("/"))
    public_paths = (
        "/",
        "/privacy",
        "/static/terms.html",
        "/static/refund.html",
        "/static/ai-notice.html",
        "/static/disclaimer.html",
    )
    urls = "".join(
        f"<url><loc>{base_url}{path}</loc></url>" for path in public_paths
    )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{urls}</urlset>"
    )
    return Response(
        body,
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request) -> HTMLResponse:
    if public_launch_is_blocked():
        return unavailable_until_configured(request)
    return templates.TemplateResponse(
        request=request,
        name="privacy.html",
        context={
            "controller_name": (settings.data_controller_name or "ChinaTradeResolve").strip(),
            "controller_address": (settings.data_controller_address or "").strip(),
            "controller_registration": (settings.data_controller_registration or "").strip(),
            "privacy_configuration_complete": privacy_configuration_is_complete(),
            "contact_email": settings.contact_email,
            "retention_days": settings.retention_days,
            "inactive_retention_days": settings.inactive_retention_days,
        },
    )


@app.post("/api/assistant", response_model=AssistantChatResponse)
async def public_ai_assistant(payload: AssistantChatRequest, request: Request) -> AssistantChatResponse:
    if not assistant_is_enabled():
        raise HTTPException(status_code=503, detail=localized_error(payload.language, "unavailable"))

    # Scope is checked before any user budget or provider call.  Explicitly
    # unrelated messages therefore cannot waste the visitor's quota.
    local_scope_reply = assistant_scope_reply(payload)
    if local_scope_reply is not None:
        return AssistantChatResponse(reply=local_scope_reply)

    session_key = public_rate_session_key(request)
    if not assistant_limiter.allow(f"assistant-session:{session_key}"):
        raise HTTPException(status_code=429, detail=localized_error(payload.language, "rate"))
    # A deliberately generous IP bucket remains only as an emergency flood
    # guard; normal visitors behind one office or mobile carrier use independent
    # session buckets above.
    if not assistant_ip_flood_limiter.allow(f"assistant-ip:{client_key(request)}"):
        raise HTTPException(status_code=429, detail=localized_error(payload.language, "rate"))
    if not await verify_turnstile(payload.turnstile_token, request):
        raise HTTPException(status_code=400, detail=localized_error(payload.language, "bot"))
    try:
        claim_daily_usage_for_subject(
            "ai_assistant",
            usage_subject(request, "ai_assistant"),
            settings.max_daily_ai_assistant_requests_per_session,
            settings.max_daily_ai_assistant_global_requests,
        )
    except DailyUsageLimitError:
        raise HTTPException(status_code=429, detail=localized_error(payload.language, "daily"))
    try:
        reply = await assistant_reply(payload)
    except AssistantConfigurationError:
        raise HTTPException(status_code=503, detail=localized_error(payload.language, "unavailable"))
    except AssistantProviderError:
        raise HTTPException(status_code=502, detail=localized_error(payload.language, "unavailable"))
    return AssistantChatResponse(reply=reply)


@app.post("/api/assistant/transcribe", response_model=VoiceTranscriptionResponse)
async def public_voice_transcription(
    request: Request,
    audio: UploadFile = File(...),
    language: str = Form("en"),
    voice_consent: bool = Form(False),
    turnstile_token: str = Form(""),
    purpose: str = Form("assistant"),
) -> VoiceTranscriptionResponse:
    language_code = language if language in LANGUAGE_CODES else "en"
    client = client_key(request)
    session_key = voice_rate_session_key(request)
    voice_purpose = purpose if purpose in {"assistant", "description"} else "assistant"
    if not voice_attempt_limiter.allow(f"voice-attempt:{client}"):
        raise HTTPException(status_code=429, detail=localized_error(language_code, "voice_rate"))
    if not voice_input_is_enabled():
        raise HTTPException(status_code=503, detail=localized_error(language_code, "unavailable"))
    if not voice_consent:
        raise HTTPException(status_code=422, detail=localized_error(language_code, "voice_consent"))
    try:
        audio_bytes = await audio.read(MAX_VOICE_AUDIO_BYTES + 1)
    finally:
        await audio.close()
    try:
        validate_voice_audio(audio_bytes, audio.content_type)
    except VoiceValidationError as exc:
        status_code = 413 if exc.kind == "too_large" else 415
        raise HTTPException(status_code=status_code, detail=localized_error(language_code, "voice_invalid"))
    if not await verify_turnstile(turnstile_token, request):
        raise HTTPException(status_code=400, detail=localized_error(language_code, "bot"))
    if not voice_limiter.allow(f"voice:{voice_purpose}:{session_key}"):
        raise HTTPException(status_code=429, detail=localized_error(language_code, "voice_rate"))
    try:
        claim_daily_usage_for_subject(
            f"voice_{voice_purpose}",
            usage_subject(request, f"voice_{voice_purpose}"),
            settings.max_daily_voice_transcriptions_per_session,
            settings.max_daily_voice_transcriptions_global,
        )
    except DailyUsageLimitError:
        raise HTTPException(status_code=429, detail=localized_error(language_code, "voice_daily"))
    safety_identifier = hashlib.sha256(
        f"{_runtime_session_secret}:{client_key(request)}".encode("utf-8")
    ).hexdigest()
    try:
        transcript = await transcribe_audio(
            audio_bytes,
            audio.content_type,
            language_code,
            safety_identifier,
        )
    except VoiceConfigurationError:
        raise HTTPException(status_code=503, detail=localized_error(language_code, "unavailable"))
    except VoiceProviderError:
        raise HTTPException(status_code=502, detail=localized_error(language_code, "unavailable"))
    finally:
        audio_bytes = b""
    return VoiceTranscriptionResponse(transcript=transcript)


@app.get("/support", response_class=HTMLResponse)
def support_page(request: Request) -> HTMLResponse:
    if not support_is_available():
        raise HTTPException(status_code=404, detail="Voluntary support is not currently available")
    return templates.TemplateResponse(
        request=request,
        name="support.html",
        context={
            "paypal_support_url": safe_paypal_support_url(),
            "support_url": safe_support_url(),
            "wallets": crypto_wallets(),
            "project_name": settings.support_project_name,
        },
    )


@app.get("/support/paypal-qr.png")
def paypal_support_qr() -> Response:
    paypal_url = safe_paypal_support_url()
    if not settings.enable_voluntary_support or not paypal_url:
        raise HTTPException(status_code=404, detail="PayPal support is disabled")
    return Response(
        content=_qr_png(paypal_url),
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.get("/support/qr/{wallet_id}.png")
def support_qr(wallet_id: str) -> Response:
    if not settings.enable_voluntary_support:
        raise HTTPException(status_code=404, detail="Support is disabled")
    wallet = next((item for item in crypto_wallets() if item["id"] == wallet_id), None)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return Response(
        content=_qr_png(wallet["address"]),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600", "X-Content-Type-Options": "nosniff"},
    )


def _fresh_document_analysis(case_id: int) -> dict[str, Any] | None:
    """Convert only genuinely stale running jobs into a visible failed state."""
    analysis = get_document_analysis(case_id)
    if not analysis or analysis.get("status") != "running":
        return analysis
    if fail_stale_document_analysis(case_id, _document_analysis_stale_seconds()):
        return get_document_analysis(case_id)
    return analysis


async def _run_document_analysis_task(case_id: int, actor: str, run_token: str) -> None:
    """Run provider work after the HTTP response and persist a terminal status."""
    case = get_case(case_id)
    if not case:
        return
    documents = list_case_documents(case_id, include_content=True)
    if not documents:
        set_document_analysis_status(
            case_id, "failed", settings.openai_document_model or "",
            "No documents were available when analysis started", actor="document_ai", document_count=0,
            expected_run_token=run_token,
        )
        return
    try:
        result = await analyse_case_documents(case, documents)
        saved = save_document_analysis(case_id, result, settings.openai_document_model or "", run_token)
        if saved is None:
            logger.warning("Discarded document-analysis result after its claim expired for case_id=%s", case_id)
    except (DocumentAnalysisConfigurationError, DocumentAnalysisProviderError) as exc:
        set_document_analysis_status(
            case_id, "failed", settings.openai_document_model or "", str(exc),
            actor="document_ai", document_count=len(documents), expected_run_token=run_token,
        )
    except Exception:
        logger.exception("Unexpected document-analysis failure for case_id=%s", case_id)
        # Keep unexpected provider/runtime details out of the public page and audit log.
        set_document_analysis_status(
            case_id, "failed", settings.openai_document_model or "",
            "Unexpected document-analysis failure", actor="document_ai", document_count=len(documents), expected_run_token=run_token,
        )


@app.post("/api/applications")
async def submit_application(
    payload: ApplicationCreate,
    request: Request,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    if public_launch_is_blocked():
        raise HTTPException(status_code=503, detail="The public service is not ready to accept applications")
    if not limiter.allow(client_key(request)):
        raise HTTPException(status_code=429, detail="Too many applications from this connection. Please try later.")
    if not await verify_turnstile(payload.turnstile_token, request):
        raise HTTPException(status_code=400, detail="Bot-protection verification is required")

    rule_result = rules_triage(payload)
    ai_result = None
    if payload.ai_consent:
        try:
            # The application must remain responsive even if the AI provider is slow.
            # Rules-only triage is always available as the safe fallback.
            ai_result = await asyncio.wait_for(
                ai_triage(payload),
                timeout=settings.application_triage_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning("AI triage exceeded the application response budget; using rules-only triage")
            ai_result = None
        except Exception:
            logger.exception("AI triage failed; falling back to rules-only triage")
            ai_result = None
    triage = merge_triage(rule_result, ai_result)

    reference = make_reference()
    public_token = secrets.token_urlsafe(24)
    notification_case = {
        **payload.model_dump(),
        **triage.model_dump(),
        "case_reference": reference,
        "public_token": public_token,
        "status": triage.decision,
    }
    case = create_case(
        payload.model_dump(),
        triage.model_dump(),
        reference,
        public_token,
        notifications=build_case_notifications(notification_case),
    )
    background_tasks.add_task(deliver_pending)
    status_url = f"/case/{reference}/{public_token}"
    return JSONResponse(
        {
            "case_reference": reference,
            "status": case["status"],
            "public_message": case["public_message"],
            "status_url": status_url,
            "email_delivery_configured": email_delivery_is_configured(),
        },
        status_code=201,
    )


@app.get("/case/{reference}/{token}/access.txt", response_class=PlainTextResponse)
def download_case_access_note(reference: str, token: str) -> PlainTextResponse:
    case = get_case_by_public(reference, token)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    language = case.get("preferred_language") or "English"
    progress_copy = CASE_PROGRESS_COPY.get(language, CASE_PROGRESS_COPY["English"])
    private_url = f"{settings.public_base_url}/case/{reference}/{token}"
    body = (
        f"ChinaTradeResolve\n{progress_copy['private_link']}:\n{private_url}\n\n"
        f"{progress_copy['private_warning']}\n"
    )
    return PlainTextResponse(
        body,
        headers={"Content-Disposition": f'attachment; filename="{reference}-access.txt"'},
    )


@app.get("/case/{reference}/{token}", response_class=HTMLResponse)
def public_case_status(reference: str, token: str, request: Request, feedback_saved: int = 0, documents_uploaded: int = 0, analysis_error: int = 0, analysis_unavailable: int = 0, analysis_started: int = 0, analysis_issue: str = "") -> HTMLResponse:
    case = get_case_by_public(reference, token)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    triage = json.loads(case["triage_json"])
    language = case.get("preferred_language") or "English"
    copy = STATUS_COPY.get(language, STATUS_COPY["English"])
    feedback = get_feedback(case["id"])
    documents = list_case_documents(case["id"])
    document_analysis = _fresh_document_analysis(case["id"])
    progress_copy = CASE_PROGRESS_COPY.get(language, CASE_PROGRESS_COPY["English"])
    progress_stages, next_step = public_case_progress(case, documents, document_analysis, progress_copy)
    private_status_url = f"{settings.public_base_url}/case/{reference}/{token}"
    last_updated = str(case.get("updated_at") or case.get("created_at") or "").replace("T", " ").replace("+00:00", " UTC")
    return templates.TemplateResponse(
        request=request,
        name="public_status.html",
        context={
            "case": case,
            "triage": triage,
            "copy": copy,
            "feedback": feedback,
            "feedback_saved": bool(feedback_saved),
            "documents_uploaded": bool(documents_uploaded),
            "analysis_error": bool(analysis_error),
            "analysis_started": bool(
                analysis_started
                and document_analysis
                and document_analysis.get("status") == "running"
            ),
            "analysis_not_configured": bool(analysis_unavailable) or analysis_issue == "configuration",
            "analysis_consent_required": analysis_issue == "consent",
            "analysis_budget_reached": analysis_issue == "budget",
            "support_url": safe_support_url(),
            "support_available": support_is_available(),
            "documents": documents,
            "document_analysis": document_analysis,
            "document_changes_locked": bool(document_analysis and document_analysis.get("status") == "running"),
            "document_analysis_enabled": document_analysis_is_enabled(),
            "document_copy": DOCUMENT_COPY.get(language, DOCUMENT_COPY["English"]),
            "privacy_actions": PRIVACY_ACTION_COPY.get(language, PRIVACY_ACTION_COPY["English"]),
            "progress_copy": progress_copy,
            "progress_stages": progress_stages,
            "next_step": next_step,
            "private_status_url": private_status_url,
            "last_updated": last_updated,
            "max_documents": MAX_DOCUMENTS_PER_CASE,
            "status_label": PUBLIC_STATUS_LABELS.get(language, PUBLIC_STATUS_LABELS["English"]).get(case["status"], case["status"]),
            "risk_label": PUBLIC_RISK_LABELS.get(language, PUBLIC_RISK_LABELS["English"]).get(case["risk_level"], case["risk_level"]),
            "page_language": {"English": "en", "French": "fr", "German": "de", "Spanish": "es", "Russian": "ru", "Serbian": "sr"}.get(language, "en"),
        },
    )


@app.post("/case/{reference}/{token}/documents")
async def public_upload_documents(
    reference: str,
    token: str,
    request: Request,
    files: list[UploadFile] = File(...),
    document_consent: bool = Form(False),
) -> RedirectResponse:
    case = get_case_by_public(reference, token)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case["status"] in {"declined", "closed"}:
        raise HTTPException(status_code=409, detail="This case is no longer accepting documents")
    if not document_consent:
        raise HTTPException(status_code=400, detail="Document-sharing consent is required")
    if not document_upload_limiter.allow(f"documents:{client_key(request)}"):
        raise HTTPException(status_code=429, detail="Too many document uploads. Please try later.")
    if not files:
        raise HTTPException(status_code=400, detail="No files were selected")

    existing = list_case_documents(case["id"])
    if len(existing) + len(files) > MAX_DOCUMENTS_PER_CASE:
        raise HTTPException(status_code=400, detail=f"A case can contain no more than {MAX_DOCUMENTS_PER_CASE} documents")

    existing_total = sum(int(document["size_bytes"]) for document in existing)
    prepared = []
    prepared_total = 0
    try:
        for upload in files:
            document = await prepare_upload(upload)
            prepared_total += document.size_bytes
            if existing_total + prepared_total > MAX_TOTAL_BYTES:
                raise DocumentValidationError("The total document size for one case cannot exceed 45 MB")
            prepared.append(document)
    except DocumentValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        add_case_documents(
            case["id"],
            [
                {
                    "original_name": document.original_name,
                    "content_type": document.content_type,
                    "size_bytes": document.size_bytes,
                    "page_count": document.page_count,
                    "sha256": document.sha256,
                    "content": document.content,
                }
                for document in prepared
            ],
            max_documents=MAX_DOCUMENTS_PER_CASE,
            max_total_bytes=MAX_TOTAL_BYTES,
            max_total_pdf_pages=MAX_TOTAL_PDF_PAGES_PER_CASE,
            actor="client",
        )
    except DocumentAnalysisInProgressError as exc:
        raise HTTPException(status_code=409, detail="Wait for the current document analysis to finish before changing files") from exc
    except DocumentLimitError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(f"/case/{reference}/{token}?documents_uploaded=1", status_code=303)


@app.get("/case/{reference}/{token}/documents/{document_id}")
def public_download_document(reference: str, token: str, document_id: int) -> Response:
    case = get_case_by_public(reference, token)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    document = get_case_document(document_id, case["id"])
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    filename = quote(document["original_name"], safe="")
    return Response(
        content=bytes(document["content_blob"]),
        media_type=document["content_type"],
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f"{'attachment' if document['content_type'] == 'application/pdf' else 'inline'}; filename*=UTF-8''{filename}",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.post("/case/{reference}/{token}/documents/{document_id}/delete")
def public_delete_document(reference: str, token: str, document_id: int, request: Request) -> RedirectResponse:
    case = get_case_by_public(reference, token)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case["status"] in {"declined", "closed"}:
        raise HTTPException(status_code=409, detail="This case is no longer accepting changes")
    if not document_upload_limiter.allow(f"document-delete:{client_key(request)}"):
        raise HTTPException(status_code=429, detail="Too many document changes. Please try later.")
    try:
        deleted = delete_case_document(case["id"], document_id)
    except DocumentAnalysisInProgressError as exc:
        raise HTTPException(status_code=409, detail="Wait for the current document analysis to finish before changing files") from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return RedirectResponse(f"/case/{reference}/{token}", status_code=303)


@app.post("/case/{reference}/{token}/documents/analyse")
async def public_analyse_documents(
    reference: str,
    token: str,
    request: Request,
    background_tasks: BackgroundTasks,
    analysis_consent: bool = Form(False),
) -> RedirectResponse:
    case = get_case_by_public(reference, token)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case["status"] in {"declined", "closed"}:
        raise HTTPException(status_code=409, detail="This case is no longer accepting analysis requests")
    if not document_analysis_is_enabled():
        record_audit(case["id"], "system", "document_analysis_unavailable", {
            "reason": "configuration",
            "model": settings.openai_document_model or "",
        })
        return RedirectResponse(f"/case/{reference}/{token}?analysis_issue=configuration", status_code=303)
    if not case["ai_consent"]:
        if not analysis_consent:
            return RedirectResponse(f"/case/{reference}/{token}?analysis_issue=consent", status_code=303)
        grant_ai_consent(case["id"], actor="client")
        case = get_case_by_public(reference, token) or case
    if not document_analysis_limiter.allow(f"document-analysis:{case['id']}:{client_key(request)}"):
        raise HTTPException(status_code=429, detail="Document analysis was requested too often. Please try later.")
    documents = list_case_documents(case["id"], include_content=False)
    if not documents:
        raise HTTPException(status_code=400, detail="Upload at least one document first")
    _fresh_document_analysis(case["id"])
    try:
        run_token = claim_document_analysis(
            case["id"],
            settings.openai_document_model or "",
            actor="client",
            document_count=len(documents),
            allow_completed=False,
            max_daily_analyses_per_case=settings.max_daily_document_analyses_per_case,
            max_daily_analyses_global=settings.max_daily_document_analyses_global,
        )
    except DailyAnalysisLimitError:
        return RedirectResponse(
            f"/case/{reference}/{token}?analysis_issue=budget#document-analysis",
            status_code=303,
        )
    if not run_token:
        return RedirectResponse(f"/case/{reference}/{token}#document-analysis", status_code=303)
    background_tasks.add_task(_run_document_analysis_task, case["id"], "client", run_token)
    return RedirectResponse(
        f"/case/{reference}/{token}?analysis_started=1#document-analysis",
        status_code=303,
    )


@app.post("/case/{reference}/{token}/ai-consent/revoke")
def public_revoke_ai_consent(
    reference: str,
    token: str,
    request: Request,
    confirm_revoke: bool = Form(False),
) -> RedirectResponse:
    case = get_case_by_public(reference, token)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not confirm_revoke:
        raise HTTPException(status_code=400, detail="Confirmation is required")
    if not limiter.allow(f"consent-revoke:{case['id']}:{client_key(request)}"):
        raise HTTPException(status_code=429, detail="Too many requests. Please try later.")
    try:
        revoke_ai_consent(case["id"], actor="client")
    except DocumentAnalysisInProgressError as exc:
        raise HTTPException(
            status_code=409,
            detail="Wait for the current analysis to finish before withdrawing consent",
        ) from exc
    return RedirectResponse(f"/case/{reference}/{token}", status_code=303)


@app.post("/case/{reference}/{token}/delete")
def public_delete_case(
    reference: str,
    token: str,
    request: Request,
    confirm_delete: bool = Form(False),
) -> RedirectResponse:
    case = get_case_by_public(reference, token)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not confirm_delete:
        raise HTTPException(status_code=400, detail="Deletion confirmation is required")
    if not limiter.allow(f"case-delete:{case['id']}:{client_key(request)}"):
        raise HTTPException(status_code=429, detail="Too many requests. Please try later.")
    analysis = _fresh_document_analysis(case["id"])
    if analysis and analysis.get("status") == "running":
        raise HTTPException(status_code=409, detail="Wait for the current analysis to finish before deleting the case")
    if not delete_case_now(case["id"]):
        raise HTTPException(status_code=404, detail="Case not found")
    request.session.clear()
    return RedirectResponse("/?case_deleted=1", status_code=303)


@app.post("/case/{reference}/{token}/feedback")
def public_case_feedback(
    reference: str,
    token: str,
    request: Request,
    rating: int = Form(...),
    feedback_text: str = Form(...),
    display_name: str = Form(""),
    testimonial_consent: bool = Form(False),
) -> RedirectResponse:
    case = get_case_by_public(reference, token)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case["status"] != "closed":
        raise HTTPException(status_code=409, detail="Feedback is available only after the case is closed")
    if not limiter.allow(f"feedback:{client_key(request)}"):
        raise HTTPException(status_code=429, detail="Too many feedback submissions. Please try later.")
    payload = FeedbackCreate(
        rating=rating,
        feedback_text=feedback_text,
        display_name=display_name,
        testimonial_consent=testimonial_consent,
    )
    save_feedback(case["id"], payload.model_dump())
    return RedirectResponse(f"/case/{reference}/{token}?feedback_saved=1", status_code=303)


@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request) -> HTMLResponse:
    if not admin_configuration_is_secure():
        return templates.TemplateResponse(
            request=request, name="admin_login.html",
            context={"error": "ADMIN_TOKEN или APP_SECRET не настроены безопасно. Добавьте два разных случайных значения длиной не менее 32 символов в Render Environment."},
            status_code=503,
        )
    return templates.TemplateResponse(request=request, name="admin_login.html", context={"error": None})


@app.post("/admin/login", response_class=HTMLResponse)
def admin_login(request: Request, token: str = Form(...)) -> HTMLResponse:
    if not admin_configuration_is_secure():
        return templates.TemplateResponse(
            request=request, name="admin_login.html",
            context={"error": "ADMIN_TOKEN или APP_SECRET не настроены безопасно. Вход администратора отключён."},
            status_code=503,
        )
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
    request.session["csrf_token"] = secrets.token_urlsafe(32)
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/logout")
def admin_logout(request: Request, csrf_token: str = Form(...)) -> RedirectResponse:
    require_admin_csrf(request, csrf_token)
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
            "csrf_token": admin_csrf_token(request),
        },
    )


@app.get("/admin/case/{case_id}", response_class=HTMLResponse)
def admin_case_detail(case_id: int, request: Request) -> HTMLResponse:
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    document_analysis = _fresh_document_analysis(case_id)
    return templates.TemplateResponse(
        request=request,
        name="admin_case.html",
        context={
            "case": case,
            "triage": json.loads(case["triage_json"]),
            "audit": get_audit(case_id),
            "feedback": get_feedback(case_id),
            "documents": list_case_documents(case_id),
            "document_analysis": document_analysis,
            "document_changes_locked": bool(document_analysis and document_analysis.get("status") == "running"),
            "document_analysis_enabled": document_analysis_is_enabled(),
            "status_labels": STATUS_LABELS,
            "risk_labels": RISK_LABELS,
            "language_labels": LANGUAGE_LABELS,
            "actor_labels": ACTOR_LABELS,
            "event_labels": EVENT_LABELS,
            "problem_labels": PROBLEM_LABELS,
            "result_labels": RESULT_LABELS,
            "channel_labels": CHANNEL_LABELS,
            "csrf_token": admin_csrf_token(request),
        },
    )


@app.get("/admin/case/{case_id}/documents/{document_id}")
def admin_download_document(case_id: int, document_id: int, request: Request) -> Response:
    require_admin(request)
    document = get_case_document(document_id, case_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    filename = quote(document["original_name"], safe="")
    return Response(
        content=bytes(document["content_blob"]),
        media_type=document["content_type"],
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f"{'attachment' if document['content_type'] == 'application/pdf' else 'inline'}; filename*=UTF-8''{filename}",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.post("/admin/case/{case_id}/documents/{document_id}/delete")
def admin_delete_document(
    case_id: int, document_id: int, request: Request, csrf_token: str = Form(...)
) -> RedirectResponse:
    require_admin_csrf(request, csrf_token)
    try:
        deleted = delete_case_document(case_id, document_id, actor="admin")
    except DocumentAnalysisInProgressError as exc:
        raise HTTPException(status_code=409, detail="Wait for the current document analysis to finish before changing files") from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return RedirectResponse(f"/admin/case/{case_id}", status_code=303)


@app.post("/admin/case/{case_id}/documents/analyse")
async def admin_analyse_documents(
    case_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    csrf_token: str = Form(...),
) -> RedirectResponse:
    require_admin_csrf(request, csrf_token)
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not document_analysis_is_enabled():
        raise HTTPException(status_code=503, detail="Document analysis is not configured")
    if not case["ai_consent"]:
        raise HTTPException(status_code=409, detail="The client has not consented to AI document analysis")
    documents = list_case_documents(case_id, include_content=False)
    if not documents:
        raise HTTPException(status_code=400, detail="No documents were uploaded")
    _fresh_document_analysis(case_id)
    try:
        run_token = claim_document_analysis(
            case_id,
            settings.openai_document_model or "",
            actor="admin",
            document_count=len(documents),
            allow_completed=True,
            max_daily_analyses_per_case=settings.max_daily_document_analyses_per_case,
            max_daily_analyses_global=settings.max_daily_document_analyses_global,
        )
    except DailyAnalysisLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    if not run_token:
        return RedirectResponse(f"/admin/case/{case_id}#document-analysis", status_code=303)
    background_tasks.add_task(_run_document_analysis_task, case_id, "admin", run_token)
    return RedirectResponse(f"/admin/case/{case_id}#document-analysis", status_code=303)


@app.post("/admin/case/{case_id}/status")
def admin_update_status(
    case_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    status: str = Form(...),
    note: str = Form(""),
    csrf_token: str = Form(...),
) -> RedirectResponse:
    require_admin_csrf(request, csrf_token)
    try:
        old_case = get_case(case_id)
        close_notifications = (
            build_completion_notifications(old_case)
            if old_case and status == "closed"
            else []
        )
        updated = update_status(
            case_id,
            status,
            note,
            close_notifications=close_notifications,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if old_case and old_case["status"] != "closed" and updated["status"] == "closed":
        background_tasks.add_task(deliver_pending)
    return RedirectResponse(f"/admin/case/{case_id}", status_code=303)


@app.post("/admin/case/{case_id}/retriage")
async def admin_retriage(
    case_id: int, request: Request, csrf_token: str = Form(...)
) -> RedirectResponse:
    require_admin_csrf(request, csrf_token)
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
            ai = await asyncio.wait_for(
                ai_triage(payload),
                timeout=settings.application_triage_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning("AI retriage exceeded the administrator response budget; using rules-only triage")
            ai = None
        except Exception:
            logger.exception("AI retriage failed; using rules-only triage")
            ai = None
    replace_triage(case_id, merge_triage(rules, ai).model_dump())
    return RedirectResponse(f"/admin/case/{case_id}", status_code=303)
# Keep the body-size guard outside FastAPI/Starlette exception handling so
# streamed overflows reliably return HTTP 413 instead of being translated into
# a generic body-parsing error. All route decorators above are already bound.
fastapi_app = app
app = RequestBodyLimitMiddleware(fastapi_app)
