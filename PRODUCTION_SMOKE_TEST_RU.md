# Глубокая production-проверка ChinaTradeResolve v3.7.39

Версия 3.7.39 содержит администраторский сценарий `scripts/production_smoke_test.py`. Он запускается из **Render Shell** после успешного deploy и выполняет реальные проверки с действующими переменными среды.

## Что проверяется

1. Публичные адреса `/health`, `/ready` и `/robots.txt` через HTTPS-домен.
2. Создание настоящего тестового дела в настроенной production-базе.
3. Открытие приватной страницы дела.
4. Загрузка безопасного PDF и PNG.
5. Формирование и фактическая передача почтовому провайдеру двух уведомлений: клиентского и административного.
6. Наличие домена `chinatraderesolve.com` в клиентской ссылке.
7. Настоящий ответ OpenAI через модель ИИ-помощника.
8. Настоящая расшифровка встроенной тестовой WAV-записи.
9. Автоматическое обезличивание тестового дела и удаление его документов после проверки.
10. Создание JSON-отчёта `production_smoke_report.json`.

Временный обход Turnstile существует только внутри отдельного процесса Render Shell. Публичные маршруты сайта не получают скрытого обхода и продолжают требовать Cloudflare Turnstile.

## Обязательные переменные Render

Перед запуском должны быть корректно настроены:

```env
PUBLIC_BASE_URL=https://chinatraderesolve.com
DATABASE_URL=...
ADMIN_TOKEN=...
APP_SECRET=...
TURNSTILE_SITE_KEY=...
TURNSTILE_SECRET_KEY=...
DATA_CONTROLLER_NAME=...
DATA_CONTROLLER_ADDRESS=...
SMTP_HOST=...
SMTP_USERNAME=...
SMTP_PASSWORD=...
SMTP_FROM=ChinaTradeResolve <chinatraderesolve.support@gmail.com>
ADMIN_EMAIL=chinatraderesolve.support@gmail.com
OPENAI_BILLING_READY=true
OPENAI_API_KEY=...
ENABLE_AI_ASSISTANT=true
OPENAI_ASSISTANT_MODEL=...
ENABLE_VOICE_INPUT=true
OPENAI_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
```

Вместо SMTP допускается уже настроенный `EMAIL_BRIDGE_URL` вместе с `EMAIL_BRIDGE_SECRET`.

## Запуск

В Render откройте **Shell** и выполните:

```bash
python scripts/production_smoke_test.py \
  --confirm-live \
  --base-url https://chinatraderesolve.com \
  --email info.praim@list.ru
```

Команда намеренно требует `--confirm-live`, поскольку она отправляет настоящие письма и выполняет платные вызовы OpenAI.

При полном успехе команда завершится с кодом `0`, в отчёте будет:

```json
"ok": true,
"failures": []
```

Проверка `public_ready` должна содержать HTTP 200 и `"status": "ready"`. Проверка `email_delivery` должна показать два сообщения со статусом `sent`. Проверки `openai_assistant` и `voice_transcription` должны содержать непустые результаты.

Статус `sent` означает, что SMTP-сервер или почтовый bridge принял письмо. После команды дополнительно откройте указанный почтовый ящик и убедитесь, что оба письма не попали в спам.

## Сохранение тестового дела

По умолчанию тестовое дело удаляется и обезличивается после проверки. Только для диагностики можно временно добавить:

```bash
--keep-test-case
```

Не оставляйте тестовое дело в production после окончания диагностики.
