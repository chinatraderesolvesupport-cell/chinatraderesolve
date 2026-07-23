from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


# Deliberately insecure sentinels: production checks recognize them and fail closed.
DEFAULT_ADMIN_TOKEN = "change-me-before-deployment"  # nosec B105
DEFAULT_APP_SECRET = "development-secret-change-me"  # nosec B105

# Public receiving addresses for voluntary project support. These are safe to
# display and may be overridden with the corresponding Render variables.
DEFAULT_BTC_ADDRESS = "1KPw94sUBeJH3noxdgQWrVMQf3sAebmeN4"
DEFAULT_ETH_ADDRESS = "0x2F8a2773F8254d061ef286Bac8BF922344a2A494"
DEFAULT_USDT_TRC20_ADDRESS = "TEJaGC38ZV8UirP7zkfPRiqHRi73wTWX5R"
DEFAULT_SOL_ADDRESS = "AEZsJ2921CR7qD7kRQRS7BiaxneeaFyKMhwDmyjCS6Zm"

INSECURE_ADMIN_TOKENS = frozenset({
    "",
    DEFAULT_ADMIN_TOKEN,
    "replace-with-a-long-random-token",
    "replace-me",
    "admin",
})
INSECURE_APP_SECRETS = frozenset({
    "",
    DEFAULT_APP_SECRET,
    "replace-with-a-long-random-secret",
    "replace-me",
    "secret",
})


MIN_ADMIN_TOKEN_LENGTH = 32
MIN_APP_SECRET_LENGTH = 32


def admin_token_is_secure(value: str | None) -> bool:
    candidate = (value or "").strip()
    return (
        candidate not in INSECURE_ADMIN_TOKENS
        and len(candidate) >= MIN_ADMIN_TOKEN_LENGTH
        and len(set(candidate)) >= 8
    )


def app_secret_is_secure(value: str | None) -> bool:
    candidate = (value or "").strip()
    return (
        candidate not in INSECURE_APP_SECRETS
        and len(candidate) >= MIN_APP_SECRET_LENGTH
        and len(set(candidate)) >= 8
    )


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(
    name: str,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    raw = os.getenv(name)
    try:
        value = int(raw.strip()) if raw is not None and raw.strip() else int(default)
    except (TypeError, ValueError):
        value = int(default)
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _env_float(
    name: str,
    default: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    raw = os.getenv(name)
    try:
        value = float(raw.strip()) if raw is not None and raw.strip() else float(default)
    except (TypeError, ValueError):
        value = float(default)
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _env_choice(name: str, default: str, allowed: set[str]) -> str:
    value = (os.getenv(name) or default).strip().lower()
    return value if value in allowed else default


def _valid_base_url(raw: str | None) -> str | None:
    value = (raw or "").strip().rstrip("/")
    if not value or any(ord(char) < 33 for char in value):
        return None
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname or ""
        parsed.port
        hostname.encode("idna")
    except (UnicodeError, ValueError):
        return None
    hostname_key = hostname.casefold()
    if not parsed.netloc:
        return None
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and hostname_key in {"localhost", "127.0.0.1", "::1"}
    ):
        return None
    if not hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        return None
    return value


def configured_public_base_url() -> str:
    # Render exposes the production HTTPS URL automatically. An explicit valid
    # PUBLIC_BASE_URL still takes precedence for a custom domain.
    return (
        _valid_base_url(os.getenv("PUBLIC_BASE_URL"))
        or _valid_base_url(os.getenv("RENDER_EXTERNAL_URL"))
        or "http://127.0.0.1:8000"
    )


@dataclass(frozen=True)
class Settings:
    base_dir: Path = Path(__file__).resolve().parent.parent
    database_url: str | None = os.getenv("DATABASE_URL")
    database_path: Path = Path(os.getenv("DATABASE_PATH", str(Path(__file__).resolve().parent.parent / "data" / "ctr.db")))
    admin_token: str = os.getenv("ADMIN_TOKEN", DEFAULT_ADMIN_TOKEN)
    app_secret: str = os.getenv("APP_SECRET", DEFAULT_APP_SECRET)
    public_base_url: str = configured_public_base_url()
    public_launch_mode: bool = _env_bool("PUBLIC_LAUNCH_MODE")
    openai_billing_ready: bool = _env_bool("OPENAI_BILLING_READY")
    enable_ai_triage: bool = _env_bool("ENABLE_AI_TRIAGE")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str | None = os.getenv("OPENAI_MODEL")
    enable_ai_assistant: bool = _env_bool("ENABLE_AI_ASSISTANT")
    openai_assistant_model: str | None = os.getenv("OPENAI_ASSISTANT_MODEL") or os.getenv("OPENAI_MODEL")
    enable_document_analysis: bool = _env_bool("ENABLE_DOCUMENT_ANALYSIS")
    openai_document_model: str | None = os.getenv("OPENAI_DOCUMENT_MODEL") or os.getenv("OPENAI_MODEL")
    document_analysis_max_output_tokens: int = _env_int("DOCUMENT_ANALYSIS_MAX_OUTPUT_TOKENS", 6000, minimum=1000, maximum=12000)
    document_analysis_timeout_seconds: float = _env_float("DOCUMENT_ANALYSIS_TIMEOUT_SECONDS", 90, minimum=10, maximum=300)
    document_pdf_detail: str = _env_choice("DOCUMENT_PDF_DETAIL", "low", {"low", "high", "auto"})
    max_daily_document_analyses: int = _env_int("MAX_DAILY_DOCUMENT_ANALYSES", 20, minimum=1, maximum=1000)
    openai_moderation_model: str | None = os.getenv("OPENAI_MODERATION_MODEL", "omni-moderation-latest")
    ai_assistant_max_output_tokens: int = _env_int("AI_ASSISTANT_MAX_OUTPUT_TOKENS", 500, minimum=100, maximum=5000)
    ai_assistant_history_messages: int = _env_int("AI_ASSISTANT_HISTORY_MESSAGES", 8, minimum=1, maximum=10)
    max_daily_ai_assistant_requests: int = _env_int("MAX_DAILY_AI_ASSISTANT_REQUESTS", 40, minimum=1, maximum=10000)
    enable_voice_input: bool = _env_bool("ENABLE_VOICE_INPUT", True)
    openai_transcription_model: str | None = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe")
    voice_max_seconds: int = _env_int("VOICE_MAX_SECONDS", 120, minimum=15, maximum=300)
    max_daily_voice_transcriptions: int = _env_int("MAX_DAILY_VOICE_TRANSCRIPTIONS", 20, minimum=1, maximum=1000)
    openai_timeout_seconds: float = _env_float("OPENAI_TIMEOUT_SECONDS", 20, minimum=2, maximum=120)
    application_triage_timeout_seconds: float = _env_float("APPLICATION_TRIAGE_TIMEOUT_SECONDS", 8, minimum=1, maximum=30)
    maintenance_interval_seconds: int = _env_int("MAINTENANCE_INTERVAL_SECONDS", 60, minimum=60, maximum=3600)
    retention_check_interval_seconds: int = _env_int("RETENTION_CHECK_INTERVAL_SECONDS", 86400, minimum=3600, maximum=604800)
    retention_days: int = _env_int("RETENTION_DAYS", 90, minimum=1, maximum=3650)
    inactive_retention_days: int = _env_int("INACTIVE_RETENTION_DAYS", 365, minimum=30, maximum=3650)
    contact_email: str = os.getenv("CONTACT_EMAIL", "chinatraderesolve.support@gmail.com")
    smtp_host: str | None = os.getenv("SMTP_HOST")
    smtp_port: int = _env_int("SMTP_PORT", 587, minimum=1, maximum=65535)
    smtp_username: str | None = os.getenv("SMTP_USERNAME")
    smtp_password: str | None = os.getenv("SMTP_PASSWORD")
    smtp_from: str = os.getenv("SMTP_FROM", "ChinaTradeResolve <chinatraderesolve.support@gmail.com>")
    admin_email: str | None = os.getenv("ADMIN_EMAIL", "chinatraderesolve.support@gmail.com")
    email_bridge_url: str | None = os.getenv("EMAIL_BRIDGE_URL")
    email_bridge_secret: str | None = os.getenv("EMAIL_BRIDGE_SECRET")
    email_bridge_timeout_seconds: float = _env_float("EMAIL_BRIDGE_TIMEOUT_SECONDS", 20, minimum=2, maximum=120)
    free_access_mode: bool = _env_bool("FREE_ACCESS_MODE", True)
    enable_voluntary_support: bool = _env_bool("ENABLE_VOLUNTARY_SUPPORT", True)
    paypal_support_url: str | None = os.getenv(
        "PAYPAL_SUPPORT_URL",
        "https://www.paypal.com/ncp/payment/THKQMZDRRNHQ8",
    )
    support_url: str | None = os.getenv("SUPPORT_URL")
    support_project_name: str = os.getenv("SUPPORT_PROJECT_NAME", "ChinaTradeResolve")
    btc_address: str | None = os.getenv("BTC_ADDRESS", DEFAULT_BTC_ADDRESS)
    eth_address: str | None = os.getenv("ETH_ADDRESS", DEFAULT_ETH_ADDRESS)
    usdt_trc20_address: str | None = os.getenv(
        "USDT_TRC20_ADDRESS",
        DEFAULT_USDT_TRC20_ADDRESS,
    )
    sol_address: str | None = os.getenv("SOL_ADDRESS", DEFAULT_SOL_ADDRESS)
    turnstile_site_key: str | None = os.getenv("TURNSTILE_SITE_KEY")
    turnstile_secret_key: str | None = os.getenv("TURNSTILE_SECRET_KEY")
    data_controller_name: str | None = os.getenv("DATA_CONTROLLER_NAME")
    data_controller_address: str | None = os.getenv("DATA_CONTROLLER_ADDRESS")
    data_controller_registration: str | None = os.getenv("DATA_CONTROLLER_REGISTRATION")
    operator_profile: str | None = os.getenv("OPERATOR_PROFILE")
    operator_credentials: str | None = os.getenv("OPERATOR_CREDENTIALS")


settings = Settings()
