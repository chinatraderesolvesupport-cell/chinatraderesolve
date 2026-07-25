from __future__ import annotations

import asyncio
import logging
import os
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
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
    test_own_messages: bool = False
    self_test_on_startup: bool = False


class _RuntimeState:
    def __init__(self) -> None:
        self.configured = False
        self.connected = False
        self.account_id: int | None = None
        self.events_seen = 0
        self.relevant_matches = 0
        self.alerts_sent = 0
        self.self_tests_sent = 0
        self.ignored_empty = 0
        self.ignored_own = 0
        self.ignored_non_channel = 0
        self.ignored_private = 0
        self.ignored_not_allowed = 0
        self.ignored_irrelevant = 0
        self.ignored_duplicate = 0
        self.last_event_at: str | None = None
        self.last_alert_at: str | None = None
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
        test_own_messages=_env_bool("TELEGRAM_MONITOR_TEST_OWN_MESSAGES", False),
        self_test_on_startup=_env_bool("TELEGRAM_MONITOR_SELF_TEST_ON_STARTUP", False),
    )


def telegram_monitor_health() -> dict[str, Any]:
    enabled = _env_bool("TELEGRAM_MONITOR_ENABLED", False)
    return {
        "enabled": enabled,
        "configured": bool(_runtime.configured),
        "connected": bool(_runtime.connected),
        "test_own_messages": _env_bool("TELEGRAM_MONITOR_TEST_OWN_MESSAGES", False),
        "events_seen_since_start": int(_runtime.events_seen),
        "relevant_matches_since_start": int(_runtime.relevant_matches),
        "alerts_sent_since_start": int(_runtime.alerts_sent),
        "self_tests_sent_since_start": int(_runtime.self_tests_sent),
        "ignored_since_start": {
            "empty": int(_runtime.ignored_empty),
            "own": int(_runtime.ignored_own),
            "non_channel": int(_runtime.ignored_non_channel),
            "private": int(_runtime.ignored_private),
            "not_allowed": int(_runtime.ignored_not_allowed),
            "irrelevant": int(_runtime.ignored_irrelevant),
            "duplicate": int(_runtime.ignored_duplicate),
        },
        "last_event_at": _runtime.last_event_at,
        "last_alert_at": _runtime.last_alert_at,
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

    @client.on(events.NewMessage())
    async def on_message(event) -> None:
        try:
            _runtime.events_seen += 1
            _runtime.last_event_at = datetime.now(timezone.utc).isoformat()

            text = (event.raw_text or "").strip()
            if not text:
                _runtime.ignored_empty += 1
                return

            sender_id = getattr(event, "sender_id", None)
            is_own = bool(getattr(event, "out", False)) or (
                _runtime.account_id is not None and sender_id == _runtime.account_id
            )
            if is_own and not settings.test_own_messages:
                _runtime.ignored_own += 1
                return

            if not getattr(event, "is_channel", False):
                # Ignore direct messages and legacy private groups. Public channels
                # and public discussion groups are represented as channels/megagroups.
                _runtime.ignored_non_channel += 1
                return

            chat = await event.get_chat()
            username = (getattr(chat, "username", None) or "").strip()
            if not username:
                # A channel/group without a public username is private.
                _runtime.ignored_private += 1
                return

            username_key = username.casefold().lstrip("@")
            if settings.allowed_chats and username_key not in settings.allowed_chats:
                _runtime.ignored_not_allowed += 1
                return

            result = classify_message(
                text,
                extra_phrases=settings.extra_phrases,
                exclude_phrases=settings.exclude_phrases,
            )
            if not result.relevant:
                _runtime.ignored_irrelevant += 1
                return

            _runtime.relevant_matches += 1

            chat_id = getattr(event, "chat_id", "unknown")
            fingerprint = message_fingerprint(chat_id, event.id)
            if not recent.add_if_new(fingerprint):
                _runtime.ignored_duplicate += 1
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
            _runtime.last_alert_at = datetime.now(timezone.utc).isoformat()
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

    if settings.self_test_on_startup:
        sample = "Alibaba supplier has not shipped the order and refuses a refund."
        result = classify_message(sample)
        alert = format_alert(
            chat_title="ChinaTradeResolve — системный тест",
            username=None,
            text=sample,
            labels=result.labels,
            link=None,
        )
        await _send_bot_message(settings, "🧪 ТЕСТ МОНИТОРА\n\n" + alert)
        _runtime.self_tests_sent += 1
        _runtime.alerts_sent += 1
        _runtime.last_alert_at = datetime.now(timezone.utc).isoformat()
        logger.info("Telegram monitor self-test alert sent")

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
