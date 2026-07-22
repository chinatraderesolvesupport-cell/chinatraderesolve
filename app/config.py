from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    base_dir: Path = Path(__file__).resolve().parent.parent
    database_url: str | None = os.getenv("DATABASE_URL")
    database_path: Path = Path(os.getenv("DATABASE_PATH", str(Path(__file__).resolve().parent.parent / "data" / "ctr.db")))
    admin_token: str = os.getenv("ADMIN_TOKEN", "change-me-before-deployment")
    app_secret: str = os.getenv("APP_SECRET", "development-secret-change-me")
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000")
    enable_ai_triage: bool = os.getenv("ENABLE_AI_TRIAGE", "false").lower() == "true"
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str | None = os.getenv("OPENAI_MODEL")
    enable_ai_assistant: bool = os.getenv("ENABLE_AI_ASSISTANT", "false").lower() == "true"
    openai_assistant_model: str | None = os.getenv("OPENAI_ASSISTANT_MODEL") or os.getenv("OPENAI_MODEL")
    openai_moderation_model: str | None = os.getenv("OPENAI_MODERATION_MODEL", "omni-moderation-latest")
    ai_assistant_max_output_tokens: int = int(os.getenv("AI_ASSISTANT_MAX_OUTPUT_TOKENS", "500"))
    ai_assistant_history_messages: int = int(os.getenv("AI_ASSISTANT_HISTORY_MESSAGES", "8"))
    openai_timeout_seconds: float = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "20"))
    retention_days: int = int(os.getenv("RETENTION_DAYS", "90"))
    contact_email: str = os.getenv("CONTACT_EMAIL", "chinatraderesolve.support@gmail.com")
    smtp_host: str | None = os.getenv("SMTP_HOST")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str | None = os.getenv("SMTP_USERNAME")
    smtp_password: str | None = os.getenv("SMTP_PASSWORD")
    smtp_from: str = os.getenv("SMTP_FROM", "ChinaTradeResolve <chinatraderesolve.support@gmail.com>")
    admin_email: str | None = os.getenv("ADMIN_EMAIL", "chinatraderesolve.support@gmail.com")
    email_bridge_url: str | None = os.getenv("EMAIL_BRIDGE_URL")
    email_bridge_secret: str | None = os.getenv("EMAIL_BRIDGE_SECRET")
    email_bridge_timeout_seconds: float = float(os.getenv("EMAIL_BRIDGE_TIMEOUT_SECONDS", "20"))
    free_access_mode: bool = os.getenv("FREE_ACCESS_MODE", "true").lower() == "true"
    enable_voluntary_support: bool = os.getenv("ENABLE_VOLUNTARY_SUPPORT", "false").lower() == "true"
    support_url: str | None = os.getenv("SUPPORT_URL")
    support_project_name: str = os.getenv("SUPPORT_PROJECT_NAME", "ChinaTradeResolve")
    btc_address: str | None = os.getenv("BTC_ADDRESS")
    eth_address: str | None = os.getenv("ETH_ADDRESS")
    usdt_trc20_address: str | None = os.getenv("USDT_TRC20_ADDRESS")
    sol_address: str | None = os.getenv("SOL_ADDRESS")


settings = Settings()
