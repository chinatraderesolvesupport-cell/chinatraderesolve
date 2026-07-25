# Telegram Monitor ChinaTradeResolve v3.7.39

## Назначение

Монитор пассивно получает новые сообщения из **публичных каналов и групп, уже доступных авторизованному Telegram-аккаунту**, и отправляет владельцу только релевантные сообщения о спорах с китайскими поставщиками.

Он не пишет авторам, не отвечает, не реагирует, не вступает в группы и не создаёт массовый архив Telegram-контента.

## Обязательные переменные Render

```text
TELEGRAM_MONITOR_ENABLED=true
TELEGRAM_API_ID=<числовой App api_id>
TELEGRAM_API_HASH=<секретный App api_hash>
TELEGRAM_SESSION_STRING=<секретная Telethon StringSession>
TELEGRAM_BOT_TOKEN=<токен уведомляющего бота>
TELEGRAM_CHAT_ID=<личный chat id владельца>
```

`TELEGRAM_API_HASH`, `TELEGRAM_SESSION_STRING` и `TELEGRAM_BOT_TOKEN` нельзя публиковать, показывать на скриншотах или хранить в GitHub.

## Необязательные переменные

```text
TELEGRAM_MONITOR_CHATS=
TELEGRAM_MONITOR_KEYWORDS=
TELEGRAM_MONITOR_EXCLUDE_KEYWORDS=
TELEGRAM_MONITOR_STARTUP_NOTICE=false
```

- Пустой `TELEGRAM_MONITOR_CHATS` означает: отслеживать все публичные каналы и группы, уже доступные аккаунту.
- Для ограничения укажите публичные usernames через запятую без `@`, например `alibaba_reviews,importers_chat`.
- `TELEGRAM_MONITOR_KEYWORDS` добавляет точные фразы, которые считаются релевантными.
- `TELEGRAM_MONITOR_EXCLUDE_KEYWORDS` исключает нежелательные темы.
- `TELEGRAM_MONITOR_STARTUP_NOTICE=false` не отправляет сообщение при каждом deploy.

## Проверка

После deploy откройте:

```text
https://chinatraderesolve.com/health
```

Ожидаемый фрагмент:

```json
"telegram_monitor": {
  "enabled": true,
  "configured": true,
  "connected": true,
  "alerts_sent_since_start": 0,
  "last_error": null
}
```

Если `connected=false`, откройте Render Logs. Секреты в лог не выводятся.

## Безопасность

После добавления StringSession в Render удалите локальный файл:

```powershell
Remove-Item "$HOME\Downloads\telegram_session_secret.txt" -Force
```

Если StringSession раскрыта, завершите соответствующий сеанс в Telegram: **Настройки → Конфиденциальность и безопасность → Устройства**, затем создайте новую сессию.
