# Продвижение ChinaTradeResolve — порядок запуска

## Что даёт версия 3.7.39

Сайт получает отдельные полезные руководства на шести языках, корректные языковые ссылки для поисковиков, карту сайта, структурированные данные и учёт источника каждой новой заявки. В админ-панели видно, пришёл человек напрямую, из Google, Reddit, Facebook или другой кампании.

Это техническая основа продвижения. Она не покупает рекламу и не гарантирует позиции в поиске автоматически.

## 1. Сначала разрешите индексацию

1. После развёртывания откройте `/health` и проверьте версию `3.7.39`.
2. Откройте `/ready`. Он должен вернуть HTTP 200 и `"status": "ready"`.
3. Откройте `/robots.txt`. При готовом запуске там должны быть `Allow: /` и ссылка на `/sitemap.xml`.
4. Если robots показывает `Disallow: /`, откройте админ-панель: новый блок индексации покажет, что сайт ещё не прошёл проверки запуска. Не рекламируйте сайт до устранения причин в `/ready`. Для Render обязательно должна быть настроена постоянная PostgreSQL-база через `DATABASE_URL`; локальный SQLite намеренно не проходит проверку готовности.

## 2. Подключите поисковые системы

1. Добавьте сайт в Google Search Console и внесите полученное значение в `GOOGLE_SITE_VERIFICATION` на Render.
2. Добавьте сайт в Bing Webmaster Tools и внесите значение в `BING_SITE_VERIFICATION`.
3. Передайте в обе системы адрес `https://chinatraderesolve.com/sitemap.xml`.
4. Создайте собственный ключ IndexNow:

```bash
python -c "import secrets; print(secrets.token_hex(16))"
```

5. Сохраните его как `INDEXNOW_KEY` в Render. После крупного обновления страниц выполните в Render Shell:

```bash
python scripts/submit_indexnow.py
```

## 3. Отмечайте рекламные ссылки

Пример:

```text
https://chinatraderesolve.com/?lang=en&utm_source=reddit&utm_medium=community&utm_campaign=launch
```

Источник, канал и кампания появятся в админ-панели рядом с заявкой. Сайт сохраняет только очищенные метки, первую страницу входа и origin сайта-источника без его пути и параметров.

## 4. Публикуйте полезно, а не массово

Не размещайте одинаковую рекламу во множестве групп. Сначала отвечайте по существу, а ссылку оставляйте только там, где правила разрешают самопродвижение. Лучше вести человека на конкретное руководство, соответствующее его проблеме.

### Английский текст для разрешённой промо-темы

**Free preliminary review for buyers in disputes with Chinese suppliers**

I am testing ChinaTradeResolve, a multilingual service that helps buyers organize order terms, messages, payment records and defect evidence before they submit or continue a supplier dispute. The current review stage is free and does not promise a refund or replace legal advice. Feedback from real cases is welcome: [SITE_URL]/?lang=en&utm_source=community&utm_medium=post&utm_campaign=launch

### Русский текст

**Бесплатная предварительная оценка спора с китайским поставщиком**

Запустил ChinaTradeResolve — сервис, который помогает систематизировать заказ, переписку, оплату и доказательства брака или непоставки. Сейчас предварительная оценка бесплатная, без обещаний возврата и без подмены юридической помощи. Буду благодарен за обратную связь: [SITE_URL]/?lang=ru&utm_source=community&utm_medium=post&utm_campaign=launch
