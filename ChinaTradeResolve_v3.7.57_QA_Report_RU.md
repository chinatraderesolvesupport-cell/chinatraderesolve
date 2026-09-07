# ChinaTradeResolve v3.7.57 — локальный QA после назначения контролёра пилота

Дата: 7 сентября 2026
База: `ChinaTradeResolve_Document_AI_v3.7.56.zip`

## Решение

Для текущей бесплатной пилотной стадии в сборке указан реальный контролёр данных: **Эдуард Цаголов**.
Публичный контакт: `chinatraderesolve.support@gmail.com`.
Почтовый адрес не выдумывается и не публикуется, пока он отдельно не подтверждён владельцем.

Технический privacy/readiness gate изменён так, чтобы для пилота требовались:

- осмысленная идентичность контролёра;
- корректный публичный контактный email.

`DATA_CONTROLLER_ADDRESS` остаётся необязательным и показывается только при явной настройке осмысленным значением. Старые hash/opaque значения адреса или имени игнорируются и не выводятся пользователю.

Это техническая конфигурация пилотной стадии, а не заключение о полном юридическом соответствии. Перед коммерциализацией/регистрацией бизнеса Privacy и Terms целесообразно отдельно проверить у специалиста по праву Сербии и применимым правилам защиты данных.

## Изменения v3.7.57

- Добавлен безопасный fallback контролёра пилота `Эдуард Цаголов`.
- Старые opaque/hash значения `DATA_CONTROLLER_NAME` и `DATA_CONTROLLER_ADDRESS` не могут вытеснить реальную пилотную идентичность или попасть на публичную страницу.
- Privacy показывает имя контролёра + рабочий email; пустая строка адреса не создаёт лишний визуальный блок.
- Блок доверия на главной обновлён во всех 6 языках.
- `.env.example` содержит реальное имя контролёра пилота и оставляет адрес пустым.
- Версия приложения, SEO smoke, IndexNow User-Agent, документация и deployment-маркеры синхронизированы на `3.7.57`.
- Production, Render, DNS, домен, Cloudflare, секреты и внешние сервисы не изменялись.

## Автоматические проверки

- Регрессионный pytest: **330 passed, 5 deselected**.
- `python -m compileall -q app scripts tests` — PASS.
- `node --check app/static/translations-v2.js` — PASS.
- `node --check app/static/launch-i18n-v3.js` — PASS.
- `node --check app/static/legal-i18n-v2.js` — PASS.
- `translations-v2.json` ↔ `translations-v2.js` parity — PASS.
- HTTP smoke с намеренно оставленными старыми hash-значениями в environment:
  - `/health` — HTTP 200, версия `3.7.57`, `privacy_configuration_complete=true`;
  - `/privacy?lang=ru` — HTTP 200, показывает `Эдуард Цаголов`;
  - старые hash-значения на Privacy не выводятся;
  - главная RU — HTTP 200 и показывает имя контролёра.

## Пять dependency-specific тестов

В текущем контейнере отсутствуют реальные `pikepdf` и `eth-utils`, поэтому для импорта и остальных регрессий использовался временный QA compatibility layer **вне release-каталога**, а пять тестов, смысл которых зависит именно от реальных этих библиотек, были исключены:

1. `test_pdf_document_analysis_uses_low_detail_data_url`
2. `test_public_pdf_download_is_attachment_and_image_is_inline`
3. `test_pdf_validation_rejects_encryption_and_obfuscated_active_content`
4. `test_document_analysis_drops_invented_evidence_filenames`
5. `test_wallet_checksum_validation_rejects_shape_only_addresses`

Compatibility layer в ZIP не включён. Эти пять тестов должны пройти в CI/Render-окружении с полным `requirements-dev.txt`, как и раньше.

## Перед установкой в production

После установки проверить `/health`, затем `/ready` и выполнить предусмотренный проектом production smoke test. Остальные readiness-компоненты (PostgreSQL, email, Turnstile, PDF security, admin security и т. д.) по-прежнему должны быть реально настроены; изменение Privacy gate их не обходит.
