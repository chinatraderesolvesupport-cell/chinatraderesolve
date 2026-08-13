# ChinaTradeResolve: бесплатный пакет запуска трафика

Актуально на 14 августа 2026 года. Основной домен: `https://chinatraderesolve.com`.

## 1. Что установлено аудитом

- Сайт уже обнаруживается поиском, а отдельные русские и английские руководства про возврат, закрытый спор Alibaba, повреждение, таможню и систематизацию доказательств проиндексированы.
- В проекте опубликовано 72 индексируемые страницы: 12 руководств на шести языках. Настроены canonical, hreflang, sitemap, Open Graph и структурированные данные.
- Заявка сохраняет UTM-метки, первую страницу входа и домен источника. Это позволяет связать обращение с конкретной публикацией.
- Нулевой или почти нулевой трафик на новом домене без ссылок и внешних публикаций не означает техническую поломку. Индексация даёт право участвовать в поиске, но не гарантирует показы и позиции: https://developers.google.com/search/docs/fundamentals/how-search-works
- Главный дефицит сейчас — не количество текстов, а дистрибуция, упоминания и первые реальные сигналы полезности.

## 2. Цель первого бесплатного цикла

Не гнаться за «массовым трафиком». За первые 30 дней получить:

1. не менее 300 релевантных посещений;
2. не менее 30 переходов из руководств к заявке;
3. не менее 10 начатых заявок;
4. 2–5 реальных обращений, подходящих по профилю;
5. первые поисковые запросы с позицией 8–30, которые можно улучшать адресно.

## 3. Измерение без платных сервисов

После установки v3.7.56 Яндекс Метрика получает следующие цели:

| Цель | Что означает |
| --- | --- |
| `guide_open` | переход к конкретному руководству |
| `guide_share` | нажатие «Поделиться руководством» |
| `application_cta_click` | переход к форме заявки |
| `application_start` | первое взаимодействие с формой |
| `application_submitted` | успешная отправка заявки |
| `ai_chat_open` | открытие ИИ-чата |
| `support_open` | переход к добровольной поддержке |

Основная воронка: `посещение → guide_open → application_cta_click → application_start → application_submitted`.

Раз в неделю фиксировать в одной строке: посетители, источники, пять главных страниц входа, цели, обращения и подходящие обращения. Не считать собственные проверки и роботов реальными людьми. Метрика автоматически исключает известных роботов, но блокировщики рекламы могут уменьшать видимые цифры: https://yandex.com/support/metrica/en/general/robots и https://yandex.com/support/metrica/ru/technologies/adblocks

## 4. Единые UTM-метки

Формат:

```text
https://chinatraderesolve.com/en/guides/SLUG?utm_source=SOURCE&utm_medium=MEDIUM&utm_campaign=pilot_2026_08&utm_content=CONTENT
```

Использовать только нижний регистр и подчёркивания.

| Канал | `utm_source` | `utm_medium` | Пример `utm_content` |
| --- | --- | --- | --- |
| Reddit | `reddit` | `community` | `alibaba_weekly` |
| LinkedIn | `linkedin` | `social` | `evidence_index_post` |
| Facebook-группа | `facebook` | `community` | `china_sourcing_group` |
| Quora | `quora` | `answer` | `supplier_refund_answer` |
| Форум | имя домена без точки | `community` | `case_specific_reply` |
| Письмо партнёру | `partner_name` | `outreach` | `evidence_checklist` |

Нельзя публиковать одну и ту же ссылку с разными написаниями источника (`LinkedIn`, `linkedin.com`, `li`). Иначе статистика раздробится.

## 5. Приоритет площадок

### A. Reddit r/Alibaba — только по правилам

Страница и правила: https://www.reddit.com/r/Alibaba/

На площадке действует ограничение самопродвижения до 10% истории, запрещены призывы «напишите мне в личку», типовые ИИ-тексты для лидогенерации и реклама вне еженедельной промо-темы. Поэтому:

- сначала публично помогать фактами без ссылки;
- ссылку давать только по прямому запросу или в еженедельной промо-теме;
- никогда не обещать возврат денег;
- не копировать одинаковый ответ в несколько тем.

Готовый текст для еженедельной промо-темы:

> **Free preliminary evidence review for buyers in disputes with Chinese suppliers**
>
> ChinaTradeResolve helps buyers organize order terms, payment records, supplier messages and defect or non-delivery evidence before continuing a platform or payment dispute. The pilot review is currently free, is checked by a person and does not guarantee recovery or replace legal advice. Twelve practical checklists are also available in English, French, German, Spanish, Russian and Serbian.
>
> https://chinatraderesolve.com/en/guides?utm_source=reddit&utm_medium=community&utm_campaign=pilot_2026_08&utm_content=alibaba_weekly

### B. LinkedIn — основной бесплатный канал доверия

Публиковать с личного профиля основателя, а не с пустой страницы бренда. Частота: три полезных публикации в неделю. В первых двух абзацах — самостоятельная ценность; ссылка в конце. Не использовать формулировки «вернём деньги», «выиграем спор» или «юридическая помощь», если это не соответствует услуге.

### C. Тематические форумы и вопросы

Использовать только действующие обсуждения, где можно дать точный ответ: MoneySavingExpert, профильные форумы импортёров, Quora и локальные предпринимательские сообщества. Сначала прочитать правила конкретного раздела. Если самопродвижение запрещено — отвечать без ссылки. Старые обсуждения не поднимать рекламным сообщением.

### D. Партнёрские упоминания

Наиболее релевантные партнёры: инспекционные компании, независимые специалисты по контролю качества, экспедиторы, таможенные брокеры, консультанты по закупкам и отраслевые сообщества импортёров. Им предлагать не обмен случайными ссылками, а полезный чек-лист, который дополняет их услугу.

## 6. Готовые ответы на реальные вопросы

Ссылку добавлять только если правила разрешают. Если добавляется ссылка, вести на соответствующее руководство, а не всегда на главную.

### Поставщик обещает возврат, но деньги не пришли

> Separate the promise from the payment trail. Save the original order and payment record, the exact message where the supplier accepted a refund, the promised date and a statement showing that no credit arrived. Keep every amount consistent and do not close an active platform or card dispute merely because the supplier says a refund is “processing”. Check the platform and payment deadlines before continuing informal negotiations.

Руководство: `/en/guides/supplier-not-refunding`.

### Alibaba закрыла спор

> Preserve the complete dispute page before doing anything else: your claim, the supplier response, evidence requests, status changes and the exact reason for closure. Then compare every claim with the evidence actually submitted. A closed platform dispute is not necessarily a finding that the supplier was right, but other routes and deadlines depend on the payment method, contract and jurisdiction.

Руководство: `/en/guides/alibaba-dispute-closed-no-refund`.

### Товар бракованный

> Evidence is stronger when it shows the agreed specification, a repeatable inspection method, the number checked, the number affected and the commercial consequence. Keep packaging and originals, record dates and batch or carton numbers, and avoid claiming the entire shipment is defective if only an unexplained sample was inspected.

Руководство: `/en/guides/product-quality-dispute`.

### Недостача или повреждение

> Document the unopened condition first: seals, labels, pallet or carton damage and the delivery receipt. Use a count sheet linked to carton and SKU numbers. Separate a supplier packaging issue from a carrier loss by checking the Incoterm and the point where risk passed.

Руководство: `/en/guides/damaged-or-short-shipment`.

### Поставщик пропал после оплаты

> Preserve volatile evidence now: supplier profile, company identity, recipient bank or wallet details, order terms, all messages and any changed or deleted pages. Contact the platform and payment provider promptly because reporting and dispute deadlines can run while you wait for the seller to reply.

Руководство: `/en/guides/supplier-disappeared-after-payment`.

### Таможня остановила груз

> Start from the written customs, broker or carrier notice. Identify the importer of record, the Incoterm and the exact document or compliance issue. A customs hold is not automatically a supplier breach; responsibility depends on the official reason and the written allocation of duties.

Руководство: `/en/guides/customs-clearance-problem`.

## 7. Календарь LinkedIn на четыре недели

Каждая публикация должна быть 500–1 000 знаков, с одним выводом и одной ссылкой. Изображение необязательно; полезная схема или обезличенный фрагмент чек-листа предпочтительнее стоковой картинки.

### Неделя 1 — доказательства

1. «Обещание возврата — ещё не возврат»: пять документов, связывающих обещание с движением денег.
2. «Почему 200 скриншотов слабее одного индекса доказательств»: структура пяти папок.
3. «Один факт — один источник»: мини-пример таблицы `утверждение → файл → дата → что доказывает`.

### Неделя 2 — ошибки спора

4. Четыре действия, которые нельзя делать сразу после закрытия спора Alibaba.
5. Почему нельзя закрывать спор до фактического зачисления денег.
6. Как сформулировать требование: точная сумма, основание, срок и подтверждение.

### Неделя 3 — качество и доставка

7. Как документировать повреждение до распаковки и распределения товара.
8. Почему фотография цвета на экране не доказывает неверный оттенок.
9. Как отличить ответственность поставщика от ответственности перевозчика.

### Неделя 4 — прозрачность сервиса

10. Что входит и не входит в бесплатную предварительную оценку ChinaTradeResolve.
11. Как безопасно подготовить документы: убрать лишние персональные данные, сохранить оригиналы, загрузить только ключевые файлы.
12. Открытый запрос обратной связи: какие элементы спора покупателю труднее всего систематизировать.

Готовый завершающий абзац:

> ChinaTradeResolve is running a free pilot for buyers who need to organise a dispute with a Chinese supplier. It does not promise recovery and does not replace legal advice. Practical guides: https://chinatraderesolve.com/en/guides?utm_source=linkedin&utm_medium=social&utm_campaign=pilot_2026_08&utm_content=TOPIC

## 8. Письмо потенциальному партнёру

Тема: `Free evidence checklist for your clients importing from China`

> Hello,
>
> I run ChinaTradeResolve, a small multilingual pilot that helps buyers organise order terms, payment records, supplier messages and problem evidence before continuing a dispute. I noticed that your clients may face the same documentation gap after inspection, shipping or sourcing work is complete.
>
> We have a free, non-promissory checklist on [specific topic]. If it would genuinely help your audience, you are welcome to reference it. I would also value one factual correction from your area of expertise. There is no request for a paid placement or a reciprocal link.
>
> [specific guide URL with outreach UTM]
>
> Best regards,
> ChinaTradeResolve

Отправлять только персонализированные письма, максимум 5–8 в неделю. Перед отправкой указать конкретный материал партнёра и объяснить, почему выбран именно он.

## 9. Что не делать

- Не покупать пакеты ссылок, отзывы, лайки, подписчиков или «гарантированный трафик».
- Не рассылать одинаковый текст десяткам форумов и групп.
- Не маскировать связь с ChinaTradeResolve.
- Не отвечать вымышленными историями клиентов и не публиковать конфиденциальные дела.
- Не создавать ещё десятки почти одинаковых SEO-страниц до появления данных по запросам.
- Не запускать широкую рекламу на главную до измерения конверсии органических переходов.

## 10. Платный тест — только после бесплатного цикла

Если бесплатный цикл покажет, что `application_start → application_submitted` работает, запускать только поисковую рекламу с намерением решить конкретный спор. Начальный предел: 5 евро в день, общий стоп 50 евро. Отдельные группы: `supplier refund`, `Alibaba dispute closed`, `defective goods`, `supplier disappeared`. Исключить слова: `job`, `wholesale products`, `supplier list`, `tracking number`, `Alibaba customer service`, `free money`, `crypto recovery`.

Реклама должна вести на конкретное руководство, а не на общий рекламный экран. До запуска проверить правила Google Ads о вводящих в заблуждение заявлениях: https://support.google.com/adspolicy/answer/6020955

## 11. Что требует владельца аккаунта

Всё ниже невозможно выполнить корректно и безопасно без человека, от имени которого публикуется материал:

1. выбрать личный LinkedIn/Reddit/форумный профиль;
2. подтвердить биографию и допустимую степень публичности;
3. публиковать ответы и вступать в диалог;
4. отправить IndexNow из Render Shell, если настроен `INDEXNOW_KEY`;
5. просмотреть реальные запросы и показы в Google Search Console и Яндекс Вебмастере;
6. одобрить любой рекламный бюджет.

До этого момента техническая база, тексты, ссылки, ограничения и измерение подготовлены.
