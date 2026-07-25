import asyncio
import pytest

from app.telegram_monitor_core import (
    classify_message,
    compact_excerpt,
    format_alert,
    message_fingerprint,
    parse_csv,
    public_message_link,
)


def test_alibaba_refund_is_relevant():
    result = classify_message("Alibaba supplier refuses to issue a refund after the dispute")
    assert result.relevant
    assert "alibaba" in result.source_hits


def test_russian_non_shipment_is_relevant():
    result = classify_message("Китайский поставщик не отправил товар и отказывается вернуть деньги")
    assert result.relevant


def test_supplier_without_problem_is_not_relevant():
    result = classify_message("We found a Chinese supplier for a new product line")
    assert not result.relevant


def test_unrelated_message_is_not_relevant():
    result = classify_message("Прогноз биткоина и криптовалютные сигналы на сегодня")
    assert not result.relevant


def test_exclusion_wins():
    result = classify_message("Alibaba dispute webinar and course training")
    assert not result.relevant
    assert result.excluded_hits


def test_extra_phrase_can_match():
    result = classify_message("Factory inspection failed again", extra_phrases=("factory inspection failed",))
    assert result.relevant


def test_public_link():
    assert public_message_link("@example", 42) == "https://t.me/example/42"
    assert public_message_link(None, 42) is None


def test_alert_is_bounded():
    alert = format_alert(
        chat_title="Example",
        username="example",
        text="x" * 5000,
        labels=("alibaba", "refund"),
        link="https://t.me/example/1",
    )
    assert len(alert) <= 3900
    assert "https://t.me/example/1" in alert


def test_helpers_are_stable():
    assert parse_csv(" a, b ,,c ") == ("a", "b", "c")
    assert compact_excerpt("a   b", 10) == "a b"
    assert message_fingerprint(1, 2) == message_fingerprint("1", "2")


def test_monitor_settings_and_health_do_not_expose_secrets(monkeypatch):
    from app import telegram_monitor

    values = {
        "TELEGRAM_MONITOR_ENABLED": "true",
        "TELEGRAM_API_ID": "123456",
        "TELEGRAM_API_HASH": "secret-hash",
        "TELEGRAM_SESSION_STRING": "1" * 300,
        "TELEGRAM_BOT_TOKEN": "123:secret-token",
        "TELEGRAM_CHAT_ID": "999",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    settings = telegram_monitor.load_telegram_monitor_settings()
    assert settings.enabled
    health = telegram_monitor.telegram_monitor_health()
    assert health["enabled"] is True
    assert health["configured"] is True
    rendered = repr(health)
    assert "secret-hash" not in rendered
    assert "secret-token" not in rendered
    assert "1" * 50 not in rendered


def test_monitor_rejects_missing_secret(monkeypatch):
    from app import telegram_monitor

    monkeypatch.setenv("TELEGRAM_MONITOR_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_API_ID", "123456")
    for name in (
        "TELEGRAM_API_HASH",
        "TELEGRAM_SESSION_STRING",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
    ):
        monkeypatch.delenv(name, raising=False)

    import pytest

    with pytest.raises(RuntimeError):
        telegram_monitor.load_telegram_monitor_settings()


def test_connected_monitor_sends_relevant_public_channel_alert(monkeypatch):
    import sys
    import types
    from app import telegram_monitor

    sent: list[str] = []

    class FakeEvent:
        raw_text = "Alibaba supplier refuses refund after defective goods"
        is_channel = True
        out = False
        sender_id = 888
        id = 42
        chat_id = -100123

        async def get_chat(self):
            return types.SimpleNamespace(username="public_group", title="Public Group")

    class FakeClient:
        def __init__(self, *_args, **_kwargs):
            self.handler = None

        def on(self, _builder):
            def decorator(func):
                self.handler = func
                return func
            return decorator

        async def connect(self):
            return None

        async def is_user_authorized(self):
            return True

        async def get_me(self):
            return types.SimpleNamespace(id=777)

        async def run_until_disconnected(self):
            await self.handler(FakeEvent())

        async def disconnect(self):
            return None

    class FakeEvents:
        @staticmethod
        def NewMessage(**_kwargs):
            return object()

    class FakeFloodWaitError(Exception):
        seconds = 1

    telethon_module = types.ModuleType("telethon")
    telethon_module.TelegramClient = FakeClient
    telethon_module.events = FakeEvents
    errors_module = types.ModuleType("telethon.errors")
    errors_module.FloodWaitError = FakeFloodWaitError
    sessions_module = types.ModuleType("telethon.sessions")
    sessions_module.StringSession = lambda value: value
    monkeypatch.setitem(sys.modules, "telethon", telethon_module)
    monkeypatch.setitem(sys.modules, "telethon.errors", errors_module)
    monkeypatch.setitem(sys.modules, "telethon.sessions", sessions_module)

    async def fake_send(_settings, text):
        sent.append(text)

    monkeypatch.setattr(telegram_monitor, "_send_bot_message", fake_send)
    telegram_monitor._runtime.alerts_sent = 0

    settings = telegram_monitor.TelegramMonitorSettings(
        enabled=True,
        api_id=123,
        api_hash="hash",
        session_string="session",
        bot_token="token",
        chat_id="chat",
        allowed_chats=(),
        extra_phrases=(),
        exclude_phrases=(),
        startup_notice=False,
    )
    asyncio.run(telegram_monitor._connected_monitor(settings))

    assert len(sent) == 1
    assert "Public Group" in sent[0]
    assert "https://t.me/public_group/42" in sent[0]
    assert telegram_monitor._runtime.alerts_sent == 1


def test_connected_monitor_ignores_direct_message(monkeypatch):
    import sys
    import types
    from app import telegram_monitor

    sent: list[str] = []

    class FakeEvent:
        raw_text = "Alibaba supplier refuses refund"
        is_channel = False
        out = False
        sender_id = 888
        id = 1
        chat_id = 99

        async def get_chat(self):
            raise AssertionError("Direct messages must be ignored before chat lookup")

    class FakeClient:
        def __init__(self, *_args, **_kwargs):
            self.handler = None

        def on(self, _builder):
            def decorator(func):
                self.handler = func
                return func
            return decorator

        async def connect(self):
            pass

        async def is_user_authorized(self):
            return True

        async def get_me(self):
            return types.SimpleNamespace(id=777)

        async def run_until_disconnected(self):
            await self.handler(FakeEvent())

        async def disconnect(self):
            pass

    class FakeEvents:
        @staticmethod
        def NewMessage(**_kwargs):
            return object()

    telethon_module = types.ModuleType("telethon")
    telethon_module.TelegramClient = FakeClient
    telethon_module.events = FakeEvents
    errors_module = types.ModuleType("telethon.errors")
    errors_module.FloodWaitError = type("FakeFloodWaitError", (Exception,), {"seconds": 1})
    sessions_module = types.ModuleType("telethon.sessions")
    sessions_module.StringSession = lambda value: value
    monkeypatch.setitem(sys.modules, "telethon", telethon_module)
    monkeypatch.setitem(sys.modules, "telethon.errors", errors_module)
    monkeypatch.setitem(sys.modules, "telethon.sessions", sessions_module)

    async def fake_send(_settings, text):
        sent.append(text)

    monkeypatch.setattr(telegram_monitor, "_send_bot_message", fake_send)
    settings = telegram_monitor.TelegramMonitorSettings(
        True, 123, "hash", "session", "token", "chat", (), (), (), False
    )
    asyncio.run(telegram_monitor._connected_monitor(settings))
    assert sent == []


def test_connected_monitor_can_temporarily_accept_own_public_message(monkeypatch):
    import sys
    import types
    from app import telegram_monitor

    sent: list[str] = []

    class FakeEvent:
        raw_text = "Alibaba supplier has not shipped my order and refuses a refund"
        is_channel = True
        out = True
        sender_id = 777
        id = 55
        chat_id = -100555

        async def get_chat(self):
            return types.SimpleNamespace(username="public_test", title="Public Test")

    class FakeClient:
        def __init__(self, *_args, **_kwargs):
            self.handler = None

        def on(self, _builder):
            def decorator(func):
                self.handler = func
                return func
            return decorator

        async def connect(self):
            pass

        async def is_user_authorized(self):
            return True

        async def get_me(self):
            return types.SimpleNamespace(id=777)

        async def run_until_disconnected(self):
            await self.handler(FakeEvent())

        async def disconnect(self):
            pass

    class FakeEvents:
        @staticmethod
        def NewMessage(**_kwargs):
            return object()

    telethon_module = types.ModuleType("telethon")
    telethon_module.TelegramClient = FakeClient
    telethon_module.events = FakeEvents
    errors_module = types.ModuleType("telethon.errors")
    errors_module.FloodWaitError = type("FakeFloodWaitError", (Exception,), {"seconds": 1})
    sessions_module = types.ModuleType("telethon.sessions")
    sessions_module.StringSession = lambda value: value
    monkeypatch.setitem(sys.modules, "telethon", telethon_module)
    monkeypatch.setitem(sys.modules, "telethon.errors", errors_module)
    monkeypatch.setitem(sys.modules, "telethon.sessions", sessions_module)

    async def fake_send(_settings, text):
        sent.append(text)

    monkeypatch.setattr(telegram_monitor, "_send_bot_message", fake_send)
    settings = telegram_monitor.TelegramMonitorSettings(
        True, 123, "hash", "session", "token", "chat", (), (), (), False,
        test_own_messages=True,
    )
    asyncio.run(telegram_monitor._connected_monitor(settings))
    assert len(sent) == 1
    assert "Public Test" in sent[0]


def test_connected_monitor_ignores_own_message_by_default(monkeypatch):
    import sys
    import types
    from app import telegram_monitor

    sent: list[str] = []

    class FakeEvent:
        raw_text = "Alibaba supplier refuses refund"
        is_channel = True
        out = True
        sender_id = 777
        id = 56
        chat_id = -100556

        async def get_chat(self):
            raise AssertionError("Own event must be ignored before chat lookup")

    class FakeClient:
        def __init__(self, *_args, **_kwargs):
            self.handler = None

        def on(self, _builder):
            def decorator(func):
                self.handler = func
                return func
            return decorator

        async def connect(self):
            pass

        async def is_user_authorized(self):
            return True

        async def get_me(self):
            return types.SimpleNamespace(id=777)

        async def run_until_disconnected(self):
            await self.handler(FakeEvent())

        async def disconnect(self):
            pass

    class FakeEvents:
        @staticmethod
        def NewMessage(**_kwargs):
            return object()

    telethon_module = types.ModuleType("telethon")
    telethon_module.TelegramClient = FakeClient
    telethon_module.events = FakeEvents
    errors_module = types.ModuleType("telethon.errors")
    errors_module.FloodWaitError = type("FakeFloodWaitError", (Exception,), {"seconds": 1})
    sessions_module = types.ModuleType("telethon.sessions")
    sessions_module.StringSession = lambda value: value
    monkeypatch.setitem(sys.modules, "telethon", telethon_module)
    monkeypatch.setitem(sys.modules, "telethon.errors", errors_module)
    monkeypatch.setitem(sys.modules, "telethon.sessions", sessions_module)

    async def fake_send(_settings, text):
        sent.append(text)

    monkeypatch.setattr(telegram_monitor, "_send_bot_message", fake_send)
    telegram_monitor._runtime.ignored_own = 0
    settings = telegram_monitor.TelegramMonitorSettings(
        True, 123, "hash", "session", "token", "chat", (), (), (), False
    )
    asyncio.run(telegram_monitor._connected_monitor(settings))
    assert sent == []
    assert telegram_monitor._runtime.ignored_own == 1


def test_health_exposes_diagnostics_without_secrets(monkeypatch):
    from app import telegram_monitor

    monkeypatch.setenv("TELEGRAM_MONITOR_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_MONITOR_TEST_OWN_MESSAGES", "true")
    health = telegram_monitor.telegram_monitor_health()
    assert health["test_own_messages"] is True
    assert "ignored_since_start" in health
    rendered = repr(health)
    assert "TELEGRAM_SESSION_STRING" not in rendered
