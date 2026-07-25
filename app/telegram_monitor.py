from __future__ import annotations

import asyncio
import logging
import os
import random
import re
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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
    heartbeat_seconds: int = 45
    max_retry_seconds: int = 120


class _RuntimeState:
    def __init__(self) -> None:
        self.configured = False
        self.connected = False
        self.connection_state = "starting"
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
        self.connection_attempts = 0
        self.successful_connections = 0
        self.disconnects = 0
        self.consecutive_failures = 0
        self.connected_since_monotonic: float | None = None
        self.last_event_at: str | None = None
        self.last_alert_at: str | None = None
        self.last_connected_at: str | None = None
        self.last_disconnected_at: str | None = None
        self.last_heartbeat_at: str | None = None
        self.next_retry_at: str | None = None
        self.retry_delay_seconds: float | None = None
        self.last_connection_duration_seconds: float | None = None
        self.last_error: str | None = None
        self.last_error_type: str | None = None
        self.last_error_detail: str | None = None
        self.last_disconnect_reason: str | None = None
        self.last_disconnect_type: str | None = None
        self.last_disconnect_detail: str | None = None


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


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = (os.getenv(name) or "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _safe_error_detail(exc: BaseException) -> str:
    """Return useful diagnostics without exposing credentials, URLs or session strings."""
    exception_type = type(exc).__name__
    message = str(exc).strip() or "No additional message"
    message = re.sub(r"https?://\S+", "[url]", message, flags=re.IGNORECASE)
    message = re.sub(r"\b\d{5,}:[A-Za-z0-9_-]{10,}\b", "[bot-token]", message)
    message = re.sub(r"(?<![A-Za-z0-9])[A-Za-z0-9_-]{40,}(?![A-Za-z0-9])", "[secret]", message)
    message = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[ip]", message)
    message = re.sub(r"\s+", " ", message).strip()
    return f"{exception_type}: {message}"[:240]


def _connection_error_code(exc: BaseException) -> str:
    """Map Telethon/network exceptions to stable, non-secret diagnostic codes."""
    name = type(exc).__name__.casefold()
    message = str(exc).casefold()

    if "authkeyduplicated" in name or "auth key is used under two different ip" in message:
        return "session_used_from_multiple_locations"
    if any(token in name for token in (
        "sessionrevoked", "authkeyunregistered", "authkeynotfound",
        "userdeactivated", "unauthorized",
    )) or "no longer authorized" in message:
        return "session_unauthorized"
    if "apiidinvalid" in name or "api_id" in message and "invalid" in message:
        return "api_credentials_invalid"
    if "floodwait" in name:
        return "telegram_flood_wait"
    if "connectionreset" in name or "connection reset" in message:
        return "network_connection_reset"
    if "connectionrefused" in name or "connection refused" in message:
        return "network_connection_refused"
    if "brokenpipe" in name or "broken pipe" in message:
        return "network_broken_pipe"
    if "gaierror" in name or any(token in message for token in (
        "name or service not known", "temporary failure in name resolution", "nodename nor servname",
    )):
        return "dns_resolution_failed"
    if "timeout" in name or "timed out" in message or "timeout" in message:
        return "network_timeout"
    if any(token in name for token in ("servererror", "rpccallfail", "interdcerror")):
        return "telegram_server_error"
    if "telethon is not installed" in message:
        return "dependency_missing"
    if "closed" in message or "disconnected" in message or "not connected" in message:
        return "telegram_connection_closed"
    if isinstance(exc, OSError):
        return "network_os_error"
    return "unexpected_connection_error"


def _flood_wait_seconds(exc: BaseException) -> int | None:
    raw = getattr(exc, "seconds", None)
    try:
        return max(1, min(900, int(raw))) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _retry_delay_for_error(exc: BaseException, current_delay: int, maximum: int) -> float:
    code = _connection_error_code(exc)
    flood_wait = _flood_wait_seconds(exc)
    if flood_wait is not None:
        return float(flood_wait)
    if code in {
        "session_used_from_multiple_locations",
        "session_unauthorized",
        "api_credentials_invalid",
        "dependency_missing",
    }:
        return float(max(300, maximum))
    base = float(max(5, min(maximum, current_delay)))
    return round(base + random.uniform(0.0, min(3.0, base * 0.2)), 2)


def _mark_disconnected() -> None:
    if _runtime.connected_since_monotonic is not None:
        _runtime.last_connection_duration_seconds = round(
            max(0.0, time.monotonic() - _runtime.connected_since_monotonic), 2
        )
    if _runtime.connected:
        _runtime.disconnects += 1
    _runtime.connected = False
    _runtime.account_id = None
    _runtime.connected_since_monotonic = None
    _runtime.last_disconnected_at = _now_iso()


def _record_connection_error(exc: BaseException, retry_delay: float) -> None:
    code = _connection_error_code(exc)
    detail = _safe_error_detail(exc)
    _runtime.connected = False
    _runtime.connection_state = "retry_wait"
    _runtime.consecutive_failures += 1
    _runtime.last_error = code
    _runtime.last_error_type = type(exc).__name__
    _runtime.last_error_detail = detail
    _runtime.last_disconnect_reason = code
    _runtime.last_disconnect_type = type(exc).__name__
    _runtime.last_disconnect_detail = detail
    _runtime.retry_delay_seconds = retry_delay
    _runtime.next_retry_at = (_now() + timedelta(seconds=retry_delay)).isoformat()


def load_telegram_monitor_settings() -> TelegramMonitorSettings:
    enabled = _env_bool("TELEGRAM_MONITOR_ENABLED", False)
    if not enabled:
        _runtime.configured = False
        _runtime.connection_state = "disabled"
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
        heartbeat_seconds=_env_int("TELEGRAM_MONITOR_HEARTBEAT_SECONDS", 45, 20, 300),
        max_retry_seconds=_env_int("TELEGRAM_MONITOR_MAX_RETRY_SECONDS", 120, 30, 600),
    )


def telegram_monitor_health() -> dict[str, Any]:
    enabled = _env_bool("TELEGRAM_MONITOR_ENABLED", False)
    heartbeat_seconds = _env_int("TELEGRAM_MONITOR_HEARTBEAT_SECONDS", 45, 20, 300)
    maximum_retry = _env_int("TELEGRAM_MONITOR_MAX_RETRY_SECONDS", 120, 30, 600)
    return {
        "enabled": enabled,
        "configured": bool(_runtime.configured),
        "connected": bool(_runtime.connected),
        "connection_state": _runtime.connection_state,
        "test_own_messages": _env_bool("TELEGRAM_MONITOR_TEST_OWN_MESSAGES", False),
        "heartbeat_interval_seconds": heartbeat_seconds,
        "max_retry_delay_seconds": maximum_retry,
        "connection_attempts_since_start": int(_runtime.connection_attempts),
        "successful_connections_since_start": int(_runtime.successful_connections),
        "reconnect_attempts_since_start": max(0, int(_runtime.connection_attempts) - 1),
        "disconnects_since_start": int(_runtime.disconnects),
        "consecutive_failures": int(_runtime.consecutive_failures),
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
        "last_connected_at": _runtime.last_connected_at,
        "last_disconnected_at": _runtime.last_disconnected_at,
        "last_heartbeat_at": _runtime.last_heartbeat_at,
        "last_connection_duration_seconds": _runtime.last_connection_duration_seconds,
        "next_retry_at": _runtime.next_retry_at,
        "retry_delay_seconds": _runtime.retry_delay_seconds,
        "last_error": _runtime.last_error,
        "last_error_type": _runtime.last_error_type,
        "last_error_detail": _runtime.last_error_detail,
        "last_disconnect_reason": _runtime.last_disconnect_reason,
        "last_disconnect_type": _runtime.last_disconnect_type,
        "last_disconnect_detail": _runtime.last_disconnect_detail,
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


async def _connection_watchdog(client: Any, heartbeat_seconds: int) -> None:
    """Detect a stale TCP/MTProto connection even when no channel events arrive."""
    while True:
        await asyncio.sleep(heartbeat_seconds)
        is_connected = getattr(client, "is_connected", None)
        if callable(is_connected) and not is_connected():
            raise ConnectionError("Telethon client reports that it is not connected")
        try:
            await asyncio.wait_for(client.get_me(), timeout=15.0)
        except asyncio.TimeoutError as exc:
            raise TimeoutError("Telegram heartbeat timed out") from exc
        _runtime.last_heartbeat_at = _now_iso()


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
        connection_retries=10,
        request_retries=5,
        retry_delay=2,
        auto_reconnect=True,
        timeout=15,
        flood_sleep_threshold=60,
        sequential_updates=True,
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
    _runtime.connection_state = "connected"
    _runtime.account_id = getattr(me, "id", None)
    _runtime.successful_connections += 1
    _runtime.consecutive_failures = 0
    _runtime.connected_since_monotonic = time.monotonic()
    _runtime.last_connected_at = _now_iso()
    _runtime.last_heartbeat_at = _runtime.last_connected_at
    _runtime.next_retry_at = None
    _runtime.retry_delay_seconds = None
    _runtime.last_error = None
    _runtime.last_error_type = None
    _runtime.last_error_detail = None
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
        _runtime.last_alert_at = _now_iso()
        logger.info("Telegram monitor self-test alert sent")

    disconnected_task = asyncio.create_task(client.run_until_disconnected())
    watchdog_task = asyncio.create_task(
        _connection_watchdog(client, settings.heartbeat_seconds)
    )
    try:
        done, pending = await asyncio.wait(
            {disconnected_task, watchdog_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        for task in pending:
            try:
                await task
            except asyncio.CancelledError:
                pass
        if watchdog_task in done:
            watchdog_error = watchdog_task.exception()
            if watchdog_error is not None:
                raise watchdog_error
        if disconnected_task in done:
            await disconnected_task
    finally:
        for task in (disconnected_task, watchdog_task):
            if not task.done():
                task.cancel()
        for task in (disconnected_task, watchdog_task):
            if not task.done():
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        _mark_disconnected()
        await client.disconnect()


async def run_telegram_monitor() -> None:
    try:
        settings = load_telegram_monitor_settings()
    except Exception as exc:
        _runtime.connection_state = "configuration_error"
        _runtime.last_error = "configuration_error"
        _runtime.last_error_type = type(exc).__name__
        _runtime.last_error_detail = _safe_error_detail(exc)
        logger.exception("Telegram monitor configuration error")
        return

    if not settings.enabled:
        logger.info("Telegram monitor is disabled")
        return

    delay = 5
    while True:
        _runtime.connection_attempts += 1
        _runtime.connection_state = "connecting"
        _runtime.next_retry_at = None
        _runtime.retry_delay_seconds = None
        successful_before = _runtime.successful_connections
        try:
            await _connected_monitor(settings)
            exc: BaseException = ConnectionError(
                "Telegram connection closed without an exception"
            )
        except asyncio.CancelledError:
            _mark_disconnected()
            _runtime.connection_state = "stopped"
            raise
        except Exception as caught:
            exc = caught

        if _runtime.successful_connections > successful_before:
            delay = 5
        retry_delay = _retry_delay_for_error(exc, delay, settings.max_retry_seconds)
        _record_connection_error(exc, retry_delay)
        logger.exception(
            "Telegram monitor disconnected (%s); retrying in %.2f seconds",
            _runtime.last_error,
            retry_delay,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        await asyncio.sleep(retry_delay)
        delay = min(max(10, delay * 2), settings.max_retry_seconds)
