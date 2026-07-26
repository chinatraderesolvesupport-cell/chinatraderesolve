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



def test_connection_error_codes_are_specific():
    from app import telegram_monitor

    duplicated = type("AuthKeyDuplicatedError", (Exception,), {})
    reset = ConnectionResetError("Connection reset by peer")
    timeout = TimeoutError("Telegram heartbeat timed out")

    assert telegram_monitor._connection_error_code(duplicated("duplicate")) == "session_used_from_multiple_locations"
    assert telegram_monitor._connection_error_code(reset) == "network_connection_reset"
    assert telegram_monitor._connection_error_code(timeout) == "network_timeout"


def test_connection_error_detail_redacts_secrets():
    from app import telegram_monitor

    secret = "A" * 80
    detail = telegram_monitor._safe_error_detail(
        RuntimeError(f"failed at https://example.com/path token 123456:abcdefghijklmno session {secret} from 203.0.113.8")
    )
    assert "example.com" not in detail
    assert "abcdefghijklmno" not in detail
    assert secret not in detail
    assert "203.0.113.8" not in detail
    assert "[url]" in detail
    assert "[bot-token]" in detail
    assert "[secret]" in detail
    assert "[ip]" in detail


def test_health_exposes_reconnect_state_without_credentials(monkeypatch):
    from app import telegram_monitor

    monkeypatch.setenv("TELEGRAM_MONITOR_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_MONITOR_HEARTBEAT_SECONDS", "50")
    monkeypatch.setenv("TELEGRAM_MONITOR_MAX_RETRY_SECONDS", "150")
    runtime = telegram_monitor._runtime
    runtime.connection_state = "retry_wait"
    runtime.connection_attempts = 4
    runtime.successful_connections = 2
    runtime.disconnects = 2
    runtime.consecutive_failures = 1
    runtime.last_error = "network_timeout"
    runtime.last_error_type = "TimeoutError"
    runtime.last_error_detail = "TimeoutError: Telegram heartbeat timed out"
    runtime.next_retry_at = "2026-07-25T22:00:00+00:00"
    runtime.retry_delay_seconds = 10.0

    health = telegram_monitor.telegram_monitor_health()
    assert health["connection_state"] == "retry_wait"
    assert health["connection_attempts_since_start"] == 4
    assert health["reconnect_attempts_since_start"] == 3
    assert health["successful_connections_since_start"] == 2
    assert health["heartbeat_interval_seconds"] == 50
    assert health["max_retry_delay_seconds"] == 150
    assert health["last_error"] == "network_timeout"
    assert health["last_error_type"] == "TimeoutError"
    assert health["retry_delay_seconds"] == 10.0
    rendered = repr(health)
    assert "TELEGRAM_API_HASH" not in rendered
    assert "TELEGRAM_SESSION_STRING" not in rendered


def test_retry_delay_is_slow_for_unrecoverable_session_error(monkeypatch):
    from app import telegram_monitor

    monkeypatch.setattr(telegram_monitor.random, "uniform", lambda _a, _b: 0.0)
    session_error = type("SessionRevokedError", (Exception,), {})
    network_error = ConnectionResetError("reset")
    assert telegram_monitor._retry_delay_for_error(session_error("revoked"), 5, 120) == 300.0
    assert telegram_monitor._retry_delay_for_error(network_error, 5, 120) == 5.0


def test_connected_monitor_passes_resilient_telethon_options(monkeypatch):
    import sys
    import types
    from app import telegram_monitor

    captured = {}

    class FakeClient:
        def __init__(self, *_args, **kwargs):
            captured.update(kwargs)
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
            return None

        async def disconnect(self):
            pass

        def is_connected(self):
            return True

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

    settings = telegram_monitor.TelegramMonitorSettings(
        True, 123, "hash", "session", "token", "chat", (), (), (), False,
        heartbeat_seconds=45,
        max_retry_seconds=120,
    )
    asyncio.run(telegram_monitor._connected_monitor(settings))

    assert captured["connection_retries"] == 10
    assert captured["request_retries"] == 5
    assert captured["retry_delay"] == 2
    assert captured["auto_reconnect"] is True
    assert captured["timeout"] == 15
    assert captured["sequential_updates"] is True


def test_connection_watchdog_detects_disconnected_client(monkeypatch):
    from app import telegram_monitor

    class FakeClient:
        def is_connected(self):
            return False

        async def get_me(self):
            raise AssertionError("get_me must not run after disconnected state")

    async def no_wait(_seconds):
        return None

    monkeypatch.setattr(telegram_monitor.asyncio, "sleep", no_wait)
    with pytest.raises(ConnectionError, match="not connected"):
        asyncio.run(telegram_monitor._connection_watchdog(FakeClient(), 45))


def test_record_connection_error_sets_retry_metadata():
    from app import telegram_monitor

    runtime = telegram_monitor._runtime
    runtime.connected = False
    runtime.consecutive_failures = 0
    telegram_monitor._record_connection_error(
        ConnectionResetError("Connection reset by peer"),
        12.5,
    )
    assert runtime.connection_state == "retry_wait"
    assert runtime.last_error == "network_connection_reset"
    assert runtime.last_error_type == "ConnectionResetError"
    assert runtime.retry_delay_seconds == 12.5
    assert runtime.next_retry_at is not None
    assert runtime.consecutive_failures == 1


@pytest.mark.parametrize(
    ("text", "context"),
    [
        # Russian — natural wording and common commercial problems.
        ("Из Китая пришли бракованные товары, половину невозможно продать.", None),
        ("Заказал партию у китайской фабрики, часть товара повреждена.", None),
        ("На Alibaba оплатил заказ, но продавец не отправил товар.", None),
        ("На 1688 прислали другой материал, не тот, который был в образце.", None),
        ("Китайский поставщик прислал меньше товара, чем было оплачено.", None),
        ("Товар из Китая не совпадает с образцом и имеет дефекты.", None),
        ("Alibaba закрыла спор, а деньги так и не вернули.", None),
        ("Перечислил предоплату китайскому продавцу, после этого он пропал.", None),
        ("Мне не вернули деньги, что делать?", "Закупки из Китая @china_sourcing"),
        ("Продавец перестал отвечать и заблокировал меня.", "Поставщики из Китая"),
        ("Пришла партия с ужасным качеством, куда жаловаться?", "Бизнес с Китаем"),
        ("Не тот цвет и размер, поставщик игнорирует претензию.", "Китайские поставщики"),
        ("Сертификат оказался недействительным, товар застрял на таможне.", "Импорт из Китая"),
        ("Алибаба отказала в возврате после закрытия спора.", None),
        ("Заказ с Алиэкспресс не доставлен, продавец не отвечает.", None),
        ("На Taobao оплатил товар, но посылка так и не пришла.", None),
        ("Поставщик из Китая недоложил часть комплектующих.", None),
        ("Китайский производитель сделал товар из другого материала.", None),
        ("Взяли депозит за заказ в Китае и исчезли.", None),
        ("Кто сталкивался: Alibaba спор закрыт в пользу продавца, возврата нет?", None),
        # English.
        ("The goods from China arrived defective and cannot be sold.", None),
        ("A Chinese supplier sent the wrong material and stopped replying.", None),
        ("Alibaba closed my dispute and I received no refund.", None),
        ("I paid a factory in China but the order was never shipped.", None),
        ("The shipment from China contains missing items and damaged products.", None),
        ("The product does not match the sample. What should I do?", "China sourcing group"),
        ("The seller kept my deposit and blocked me.", "Chinese suppliers and factories"),
        ("1688 delivered poor quality goods and refuses to refund.", None),
        ("Trade Assurance rejected my claim after the supplier disappeared.", None),
        ("The fake certificate caused a customs problem.", "Importing goods from China"),
        # Serbian.
        ("Roba iz Kine je stigla neispravna i lošeg kvaliteta.", None),
        ("Kineski dobavljač nije poslao porudžbinu i ne vraća novac.", None),
        ("Prodavac na Alibaba ne odgovara, a spor je zatvoren.", None),
        ("Platio sam depozit fabrici u Kini, ali je prodavac nestao.", None),
        ("Stiglo je manje robe nego što je plaćeno. Šta da radim?", "Nabavka iz Kine"),
        ("Materijal ne odgovara uzorku i roba je oštećena.", "Kineski dobavljači"),
        ("Lažni sertifikat je napravio problem na carini.", "Uvoz iz Kine"),
        ("1688 nije isporučio robu i odbijen je povraćaj.", None),
        # French.
        ("La marchandise de Chine est arrivée défectueuse et endommagée.", None),
        ("Le fournisseur chinois n'a pas expédié la commande.", None),
        ("Alibaba a rejeté le litige et aucun remboursement n'a été reçu.", None),
        ("J'ai payé un acompte à une usine en Chine, puis le vendeur a disparu.", None),
        ("Le produit ne correspond pas à l'échantillon. Que faire ?", "Achats en Chine"),
        ("Il manque des articles et le vendeur ne répond pas.", "Fournisseurs chinois"),
        ("Le faux certificat a bloqué la marchandise à la douane.", "Import de Chine"),
        ("1688 a livré un mauvais matériau et refuse le remboursement.", None),
        # German.
        ("Die Ware aus China ist mangelhaft und beschädigt angekommen.", None),
        ("Der chinesische Lieferant hat die Bestellung nicht versendet.", None),
        ("Alibaba hat den Streitfall abgelehnt und das Geld nicht zurückgezahlt.", None),
        ("Ich habe eine Anzahlung an eine Fabrik in China geleistet, dann war der Verkäufer verschwunden.", None),
        ("Das Produkt entspricht nicht dem Muster. Was soll ich tun?", "Einkauf aus China"),
        ("Es fehlt Ware und der Lieferant antwortet nicht.", "Chinesische Lieferanten"),
        ("Ein ungültiges Zertifikat führte zu Problemen beim Zoll.", "Import aus China"),
        ("1688 lieferte falsches Material und verweigert die Rückerstattung.", None),
        # Spanish.
        ("La mercancía de China llegó defectuosa y dañada.", None),
        ("El proveedor chino no envió el pedido.", None),
        ("Alibaba cerró la disputa y no devolvió el dinero.", None),
        ("Pagué un depósito a una fábrica en China y el vendedor desapareció.", None),
        ("El producto no coincide con la muestra. ¿Qué puedo hacer?", "Compras en China"),
        ("Faltan productos y el proveedor no responde.", "Proveedores chinos"),
        ("El certificado falso causó un problema en la aduana.", "Importación de China"),
        ("1688 entregó material equivocado y rechazó el reembolso.", None),
    ],
)
def test_broad_multilingual_supplier_dispute_phrasing_is_relevant(text, context):
    result = classify_message(text, context_text=context)
    assert result.relevant, (text, context, result)
    assert result.reason in {
        "direct_china_supplier_phrase",
        "source_and_problem",
        "chat_context_and_specific_problem",
        "source_help_and_transaction",
    }


@pytest.mark.parametrize(
    ("text", "context"),
    [
        ("Мне не вернули деньги за аренду квартиры.", None),
        ("Продавец автомобиля не отвечает.", None),
        ("Сегодня обсуждаем Китай и его историю.", None),
        ("Китайская кухня была отличной.", None),
        ("Нашли хорошего китайского поставщика для новой коллекции.", None),
        ("Alibaba stock rose after the earnings report.", None),
        ("Акции Alibaba сегодня выросли на бирже.", None),
        ("Webinar: how to open an Alibaba dispute.", None),
        ("Ищем сотрудника по закупкам из Китая.", None),
        ("Курс обучения работе с поставщиками Китая.", None),
        ("The seller of my used car blocked me.", None),
        ("I need a refund for a hotel booking.", None),
        ("Chinese factory tour starts tomorrow.", None),
        ("We found a reliable supplier in China.", None),
        ("Roba je stigla na vreme i odličnog je kvaliteta.", "Nabavka iz Kine"),
        ("Treba mi savet za putovanje u Kinu.", None),
        ("Le vendeur de ma voiture ne répond pas.", None),
        ("La Chine a annoncé de nouvelles règles commerciales.", None),
        ("Wir suchen einen Lieferanten in China.", None),
        ("Alibaba Aktie Analyse und Prognose.", None),
        ("El vendedor de mi coche no responde.", None),
        ("Busco un proveedor chino confiable.", None),
        ("Мне нужен юрист по спору с арендодателем.", None),
        ("Поставщик прислал каталог и цены.", "Бизнес с Китаем"),
        ("Кто был в Китае и что посмотреть?", None),
        ("Нужен возврат билета на поезд.", "Закупки из Китая"),
    ],
)
def test_broad_filter_rejects_unrelated_or_positive_messages(text, context):
    result = classify_message(text, context_text=context)
    assert not result.relevant, (text, context, result)


def test_real_alert_explains_source_author_time_and_action():
    from datetime import datetime, timezone

    alert = format_alert(
        chat_title="China Importers",
        username="china_importers",
        text="Alibaba closed my dispute and did not refund the order.",
        labels=("alibaba", "dispute", "did not refund"),
        link="https://t.me/china_importers/99",
        author_name="Anna Buyer",
        author_username="anna_buyer",
        source_type="публичная группа",
        message_time=datetime(2026, 7, 26, 8, 30, tzinfo=timezone.utc),
        match_reason="source_and_problem",
    )
    assert "РЕАЛЬНАЯ НАХОДКА" in alert
    assert "Anna Buyer (@anna_buyer)" in alert
    assert "публичная группа" in alert
    assert "26.07.2026 08:30 UTC" in alert
    assert "https://t.me/china_importers/99" in alert
