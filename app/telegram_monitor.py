from __future__ import annotations

import asyncio
import logging
import os
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

import httpx

from .telegram_monitor_core import (
    classify_message,
    format_alert,
    message_fingerprint,
    parse_csv,
    public_message_link,
)

logger = logging.getLogger("chinatraderesolve.telegram_monitor")


@dataclass(frozen=True)
class TelegramMonitorSettings:
    enabled: bool
    api_id: int
    api_hash: str
    session_string: str
    bot_token: str
    chat_id: str
    allowed_chats: tuple[str, ...]
    extra_phrases: tuple[str, ...]
    exclude_phrases: tuple[str, ...]
    startup_notice: bool


class _RuntimeState:
    def __init__(self) -> None:
        self.configured = False
        self.connected = False
        self.account_id: int | None = None
        self.alerts_sent = 0
        self.last_error: str | None = None


_runtime = _RuntimeState()


class _RecentMessages:
    def __init__(self, max_items: int = 5000) -> None:
        self.max_items = max(100, max_items)
        self._items: OrderedDict[str, None] = OrderedDict()

    def add_if_new(self, value: str) -> bool:
        if value in self._items:
            self._items.move_to_end(value)
            return False
        self._items[value] = None
        while len(self._items) > self.max_items:
            self._items.popitem(last=False)
        return True


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_telegram_monitor_settings() -> TelegramMonitorSettings:
    enabled = _env_bool("TELEGRAM_MONITOR_ENABLED", False)
    if not enabled:
        _runtime.configured = False
        return TelegramMonitorSettings(False, 0, "", "", "", "", (), (), (), False)

    raw_api_id = os.getenv("TELEGRAM_API_ID", "").strip()
    try:
        api_id = int(raw_api_id)
    except ValueError as exc:
        raise RuntimeError("TELEGRAM_API_ID must be a number") from exc

    values = {
        "TELEGRAM_API_HASH": os.getenv("TELEGRAM_API_HASH", "").strip(),
        "TELEGRAM_SESSION_STRING": os.getenv("TELEGRAM_SESSION_STRING", "").strip(),
        "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID", "").strip(),
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RuntimeError("Missing Telegram monitor settings: " + ", ".join(missing))

    allowed = tuple(
        item.casefold().lstrip("@")
        for item in parse_csv(os.getenv("TELEGRAM_MONITOR_CHATS"))
    )
    _runtime.configured = True
    return TelegramMonitorSettings(
        enabled=True,
        api_id=api_id,
        api_hash=values["TELEGRAM_API_HASH"],
        session_string=values["TELEGRAM_SESSION_STRING"],
        bot_token=values["TELEGRAM_BOT_TOKEN"],
        chat_id=values["TELEGRAM_CHAT_ID"],
        allowed_chats=allowed,
        extra_phrases=parse_csv(os.getenv("TELEGRAM_MONITOR_KEYWORDS")),
        exclude_phrases=parse_csv(os.getenv("TELEGRAM_MONITOR_EXCLUDE_KEYWORDS")),
        startup_notice=_env_bool("TELEGRAM_MONITOR_STARTUP_NOTICE", False),
    )


def telegram_monitor_health() -> dict[str, Any]:
    enabled = _env_bool("TELEGRAM_MONITOR_ENABLED", False)
    return {
        "enabled": enabled,
        "configured": bool(_runtime.configured),
        "connected": bool(_runtime.connected),
        "alerts_sent_since_start": int(_runtime.alerts_sent),
        "last_error": _runtime.last_error,
    }


async def _send_bot_message(settings: TelegramMonitorSettings, text: str) -> None:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
            json={
                "chat_id": settings.chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
        )
        response.raise_for_status()


async def _connected_monitor(settings: TelegramMonitorSettings) -> None:
    try:
        from telethon import TelegramClient, events
        from telethon.errors import FloodWaitError
        from telethon.sessions import StringSession
    except ImportError as exc:
        raise RuntimeError("Telethon is not installed") from exc

    recent = _RecentMessages()
    client = TelegramClient(
        StringSession(settings.session_string),
        settings.api_id,
        settings.api_hash,
    )

    @client.on(events.NewMessage(incoming=True))
    async def on_message(event) -> None:
        try:
            text = (event.raw_text or "").strip()
            if not text:
                return

            if not getattr(event, "is_channel", False):
                # Ignore direct messages and legacy private groups. Public channels
                # and public discussion groups are represented as channels/megagroups.
                return

            chat = await event.get_chat()
            username = (getattr(chat, "username", None) or "").strip()
            if not username:
                # A channel/group without a public username is private.
                return

            username_key = username.casefold().lstrip("@")
            if settings.allowed_chats and username_key not in settings.allowed_chats:
                return

            result = classify_message(
                text,
                extra_phrases=settings.extra_phrases,
                exclude_phrases=settings.exclude_phrases,
            )
            if not result.relevant:
                return

            chat_id = getattr(event, "chat_id", "unknown")
            fingerprint = message_fingerprint(chat_id, event.id)
            if not recent.add_if_new(fingerprint):
                return

            title = (
                getattr(chat, "title", None)
                or getattr(chat, "first_name", None)
                or username
            )
            alert = format_alert(
                chat_title=str(title),
                username=username,
                text=text,
                labels=result.labels,
                link=public_message_link(username, event.id),
            )
            await _send_bot_message(settings, alert)
            _runtime.alerts_sent += 1
            logger.info("Sent Telegram monitor alert for @%s message %s", username, event.id)
        except FloodWaitError as exc:
            logger.warning("Telegram rate limit: sleeping %s seconds", exc.seconds)
            await asyncio.sleep(exc.seconds)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Failed to process Telegram monitor message")

    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        raise RuntimeError("TELEGRAM_SESSION_STRING is no longer authorized")

    me = await client.get_me()
    _runtime.connected = True
    _runtime.account_id = getattr(me, "id", None)
    _runtime.last_error = None
    logger.info(
        "Telegram monitor connected; public chats only; auto-replies disabled; account_id=%s",
        _runtime.account_id,
    )

    if settings.startup_notice:
        await _send_bot_message(
            settings,
            "✅ Telegram Monitor запущен. Отслеживаются только доступные аккаунту публичные каналы и группы; автоматические ответы отключены.",
        )

    try:
        await client.run_until_disconnected()
    finally:
        _runtime.connected = False
        await client.disconnect()


async def run_telegram_monitor() -> None:
    try:
        settings = load_telegram_monitor_settings()
    except Exception:
        _runtime.last_error = "configuration_error"
        logger.exception("Telegram monitor configuration error")
        return

    if not settings.enabled:
        logger.info("Telegram monitor is disabled")
        return

    delay = 5
    while True:
        try:
            await _connected_monitor(settings)
            delay = 5
        except asyncio.CancelledError:
            _runtime.connected = False
            raise
        except Exception:
            _runtime.connected = False
            _runtime.last_error = "connection_error"
            logger.exception("Telegram monitor disconnected; retrying in %s seconds", delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 300)
