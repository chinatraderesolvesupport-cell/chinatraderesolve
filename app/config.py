from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_ADMIN_TOKEN = "change-me-before-deployment"
DEFAULT_APP_SECRET = "development-secret-change-me"

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


def _valid_base_url(raw: str | None) -> str | None:
    value = (raw or "").strip().rstrip("/")
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
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
    enable_ai_triage: bool = _env_bool("ENABLE_AI_TRIAGE")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str | None = os.getenv("OPENAI_MODEL")
    enable_ai_assistant: bool = _env_bool("ENABLE_AI_ASSISTANT")
    openai_assistant_model: str | None = os.getenv("OPENAI_ASSISTANT_MODEL") or os.getenv("OPENAI_MODEL")
    enable_document_analysis: bool = _env_bool("ENABLE_DOCUMENT_ANALYSIS")
    openai_document_model: str | None = os.getenv("OPENAI_DOCUMENT_MODEL") or os.getenv("OPENAI_MODEL")
    document_analysis_max_output_tokens: int = _env_int("DOCUMENT_ANALYSIS_MAX_OUTPUT_TOKENS", 6000, minimum=1000, maximum=12000)
    document_analysis_timeout_seconds: float = _env_float("DOCUMENT_ANALYSIS_TIMEOUT_SECONDS", 90, minimum=10, maximum=300)
    openai_moderation_model: str | None = os.getenv("OPENAI_MODERATION_MODEL", "omni-moderation-latest")
    ai_assistant_max_output_tokens: int = _env_int("AI_ASSISTANT_MAX_OUTPUT_TOKENS", 500, minimum=100, maximum=5000)
    ai_assistant_history_messages: int = _env_int("AI_ASSISTANT_HISTORY_MESSAGES", 8, minimum=1, maximum=10)
    openai_timeout_seconds: float = _env_float("OPENAI_TIMEOUT_SECONDS", 20, minimum=2, maximum=120)
    application_triage_timeout_seconds: float = _env_float("APPLICATION_TRIAGE_TIMEOUT_SECONDS", 8, minimum=1, maximum=30)
    maintenance_interval_seconds: int = _env_int("MAINTENANCE_INTERVAL_SECONDS", 60, minimum=60, maximum=3600)
    retention_check_interval_seconds: int = _env_int("RETENTION_CHECK_INTERVAL_SECONDS", 86400, minimum=3600, maximum=604800)
    retention_days: int = _env_int("RETENTION_DAYS", 90, minimum=1, maximum=3650)
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
    enable_voluntary_support: bool = _env_bool("ENABLE_VOLUNTARY_SUPPORT")
    support_url: str | None = os.getenv("SUPPORT_URL")
    support_project_name: str = os.getenv("SUPPORT_PROJECT_NAME", "ChinaTradeResolve")
    btc_address: str | None = os.getenv("BTC_ADDRESS")
    eth_address: str | None = os.getenv("ETH_ADDRESS")
    usdt_trc20_address: str | None = os.getenv("USDT_TRC20_ADDRESS")
    sol_address: str | None = os.getenv("SOL_ADDRESS")


settings = Settings()
