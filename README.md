# ChinaTradeResolve Document AI v3.7.8

Version 3.7.8 adds the verified public BTC, ETH, USDT TRC20 and SOL receiving addresses, generates matching QR codes, and displays a prominent required-network warning on every cryptocurrency card. The icons and linked support methods from v3.7.7 remain in place.

Runnable free-access implementation for ChinaTradeResolve. The service is free with no fixed end date until the operator decides to introduce a different model and announces it in advance.

## Included

- six-language public application form (English, French, German, Spanish, Russian and Serbian);
- SQLite case database and audit log;
- deterministic safety-first triage;
- optional multilingual public AI assistant;
- optional OpenAI structured triage;
- exception-driven admin queue;
- private case-status page;
- private upload of up to twenty PDF/image documents per case;
- optional multimodal AI document analysis with evidence inventory, chronology and contradiction detection;
- optional feedback/testimonial collection after a case is closed;
- optional voluntary project-support page;
- SMTP notification outbox;
- retention/anonymisation script;
- automated tests and Docker packaging.

## Security, privacy and cost hardening in v3.6.8

- PDF files are parsed with pikepdf, including compressed object streams; malformed, encrypted, active-content and embedded-file PDFs are rejected. Limits are 100 PDF pages per file and 200 per case.
- Document analysis has an atomic database-backed daily budget (`MAX_DAILY_DOCUMENT_ANALYSES`), records provider token usage and sends PDFs with `detail=low` by default.
- Triage never automatically declines a person because of an evidence-handling keyword, and monetary escalation is currency-aware for USD, EUR, GBP, CNY and RSD.
- Cloudflare Turnstile can protect the public application form when both keys are configured.
- The private case link supports withdrawal of future AI consent, removal of the stored AI report and immediate permanent case deletion.
- Closed and inactive cases have separate retention periods. The dynamic privacy page exposes operator details from `DATA_CONTROLLER_NAME` and `DATA_CONTROLLER_ADDRESS`.
- Bitcoin Bech32/Bech32m and Ethereum EIP-55 checksums are validated; non-local support URLs must use HTTPS.
- Dependencies and the Python base image are pinned. The container runs as an unprivileged user and includes a health check.

## Pre-launch readiness and user clarity in v3.7.0

Version 3.7.0 adds a fail-closed public launch mode, a machine-readable `/ready` gate, explicit manual/automatic document-review availability, a stronger private-link confirmation, a four-stage case progress view, accessibility improvements, and basic canonical/social structured metadata. Set `PUBLIC_LAUNCH_MODE=true` only after `/ready` returns HTTP 200.

## URL and test-environment hardening in v3.6.9

- The HTTPS email bridge now rejects non-HTTP schemes, remote plain HTTP, embedded credentials and control characters before any network access.
- External support links reject embedded credentials and malformed whitespace; plain HTTP remains limited to loopback development addresses.
- Notification SQL uses static statements for both SQLite and PostgreSQL lease paths.
- The development test client uses the pinned `httpx2` compatibility package required by the current Starlette release.



## Embedded-PDF attachment blocking in v3.6.7

- PDF validation now rejects the standard `/EmbeddedFiles` name tree used for attachments;
- file-specification and associated-file structures (`/Filespec`, `/EF`, `/AF`, `/AFRelationship`) are rejected before storage;
- portfolio and embedded-file navigation markers (`/Collection`, `/GoToE`) are also blocked;
- PDF name escapes are decoded first, so obfuscated forms such as `/Embedded#46iles` cannot bypass the check.


## Partial-date preservation in v3.6.6

- visible month-and-year values such as `March 2025` are retained even when the exact day is unavailable;
- a visible year such as `2025` is retained instead of being replaced by a generic unknown-date label;
- partial dates receive an internal earliest-possible sorting key while the original wording remains visible;
- month-and-year parsing supports the same six interface languages as full-date chronology parsing.


## Cautious authenticity and legality wording in v3.6.5

- unverified conclusions such as “forged certificate”, “illegal document” or “criminal conduct” are no longer displayed as established facts;
- the same deterministic protection is applied in English, Russian, Serbian, French, German and Spanish;
- the protection covers the summary, chronology, evidence lists, risk sections, next steps and document-inventory descriptions;
- exact quotations inside `«…»`, `“…”` and `"…"` remain unchanged so the visible evidence is not silently rewritten;
- the existing prompt-level caution remains, while application post-processing now enforces the boundary if a model disregards it.


## Deterministic readiness breakdown in v3.6.4

- Structured Outputs now requires exactly seven readiness-factor entries.
- The application defensively fills any missing or duplicated factor as `missing`.
- The displayed percentage is always recalculated from the seven factors and can no longer remain an unexplained model-provided number.
- A report with no applicable evidence factors receives a score of 0 instead of retaining an arbitrary percentage.

## Localised date formats in v3.6.3

- German dates with an ordinal dot, such as `22. März 2025`, are recognised.
- Spanish dates with `de`, such as `22 de mayo de 2025`, are recognised.
- Serbian Latin and Cyrillic month inflections, such as `22 maja 2025` and `22. маја 2025.`, are recognised.
- Localised date ranges use their earliest visible date for sorting.

## Multilingual chronology fixes in v3.6.2

- a visible date is preserved when another detail is unavailable, for example “26 May 2026, time not visible”;
- visible month names are parsed in English, Russian, French, German, Spanish and Serbian;
- chronology ordering no longer has to rely on the model-provided ISO helper for these interface languages.


## Public-site redesign retained from v3.3

- shortened the public page by merging repeated free-access and service-result sections;
- made the first screen more specific about the review result and next steps;
- replaced the inconsistent pre-payment card with an active refund-dispute scenario;
- reduced the workflow to four steps that match the actual free-review scope;
- consolidated trust, operator information, AI boundaries and the sample report;
- displays a verifiable contact email, Serbia operation location, working hours and response target;
- states clearly that the service is not a law firm and does not send documents to third parties without an agreed action;
- improved light-background contrast and shortened desktop navigation labels;
- added a description character counter, keyboard progression and accessible success focus;
- added a privacy FAQ explaining who may see case materials;
- keeps voluntary support disabled by default and preserves the existing case-management and AI-assistant workflow.




## Upload responsiveness and bounded image processing in v3.6.1

- image/PDF validation and image re-encoding run outside the main ASGI event loop, so large screenshots do not pause unrelated requests;
- document processing is globally limited to two concurrent CPU-heavy jobs per web process, preventing several 30-megapixel images from exhausting a small Render instance;
- files within one upload remain sequential to keep peak memory predictable;
- `.env.example` is included again with secrets and external integrations disabled by default.

## Administrator-session safety fix in v3.5.7

Administrator login now requires both `ADMIN_TOKEN` and `APP_SECRET` to pass the production safety checks. Previously, a secure admin token could still enable login while an insecure app secret caused each process to generate its own temporary session key. On overlapping Render deploys or restarts, that made administrator sessions unstable. Public case submission remains available when these secrets are incomplete, but the administrator login is intentionally disabled until both are configured.

## Transactional notification and workflow fixes in v3.5.6

- initial applicant and administrator notifications are inserted in the same database transaction as the new case, so a process interruption cannot save the case while losing its outbox messages;
- the completion notification is inserted in the same locked transaction as the transition to `closed`;
- repeated or concurrent close requests cannot create duplicate completion-email rows;
- the mail worker claims one message immediately before sending instead of leasing a large batch whose later leases could expire;
- public feedback is accepted only after the case is actually closed;
- administrator notes are capped at the documented 1,000-character limit.

## PostgreSQL and notification reliability fixes in v3.5.4

- fixed the fresh PostgreSQL schema for `audit_log`: the previous SQL declared `created_at` twice and could fail on a brand-new database;
- email outbox rows are now claimed with a database-backed lease before delivery;
- overlapping old and new Render instances cannot concurrently send the same pending message;
- abandoned email leases are automatically recovered after a bounded timeout;
- notification lease columns are added automatically to existing PostgreSQL and SQLite databases;
- all document-analysis run-token protections from v3.5.3 remain in place.

## Reliability, concurrency and security fixes in v3.5.3

- rate limiting now uses Render’s documented first `X-Forwarded-For` address only when proxy headers are trusted; local/direct deployments ignore caller-supplied forwarding headers by default;
- closed-case retention begins from the latest case update/closure time, so an old case closed today is not anonymised immediately;
- administrator re-triage uses the same bounded AI response budget as the public application and safely falls back to rules;
- malformed or blank numeric environment variables no longer crash a Render deploy and are clamped to safe ranges;
- invalid `PUBLIC_BASE_URL` values are rejected, with a valid `RENDER_EXTERNAL_URL` used as fallback;
- unsupported AI-generated timeline events are removed unless they cite at least one real uploaded filename;
- all reliability, concurrency and security controls introduced through v3.5.1 remain in place.

## Private document analysis in v3.5.3

Reliability hardening in this release:

- Unique per-run claim tokens prevent stale workers from saving results or errors into a newer analysis.
- Stale recovery uses conditional database updates and does not invalidate fresh work during an overlapping Render deploy.
- Existing PostgreSQL and SQLite databases receive the new `run_token` column automatically at startup.


After an application is submitted, the private case page accepts up to twenty key files in PDF, JPG, PNG or WebP format. Each file is limited to 8 MB and each case to 45 MB total. The HTTP upload request itself is capped at 50 MB including multipart overhead, before Starlette parses or spools the files. Other POST, PUT and PATCH requests are capped at 1 MB.

Security and privacy controls:

- files are stored in PostgreSQL/SQLite with the case, not on Render's ephemeral filesystem;
- file signatures are checked instead of trusting the browser MIME type;
- images are decoded and re-encoded to remove EXIF and other embedded metadata;
- encrypted PDFs and PDFs with JavaScript, launch actions, embedded files, rich media or other active-content markers are rejected;
- downloads require the private case token or an authenticated admin session;
- adding or deleting a file invalidates the previous AI report;
- retention cleanup deletes file blobs and analysis reports with the closed case;
- AI requests use the Responses API, Structured Outputs and `store: false`;
- document content is treated as untrusted and cannot override system instructions;
- the readiness score measures evidence organisation, not legal merit or probability of success.

The report includes document inventory, chronology with source filenames, key evidence, possible contradictions, missing evidence, risk flags and recommended next steps. Important conclusions still require human verification.

Enable it with:

```env
ENABLE_DOCUMENT_ANALYSIS=true
OPENAI_API_KEY=...
OPENAI_DOCUMENT_MODEL=<vision and PDF capable model>
DOCUMENT_ANALYSIS_MAX_OUTPUT_TOKENS=6000
DOCUMENT_ANALYSIS_TIMEOUT_SECONDS=90
```

See `DOCUMENT_AI_SETUP_RU.md` for the Render checklist.

### Analysis execution model

The private page responds immediately after an analysis is claimed and the provider call continues in the web process. Each run receives a unique database claim token, so a late response from an older run cannot overwrite a newer retry. Fresh work is not invalidated during Render's overlapping zero-downtime deploy; only jobs that remain running beyond the bounded stale threshold are marked failed and can be retried. This is suitable for the current low-volume deployment; sustained production load should move analysis to a durable queue and separate worker.

## Public AI assistant

The main page now contains a multilingual AI information assistant for English, French, German, Spanish, Russian and Serbian. The widget remains hidden until the server is configured with an API key and model.

The assistant can:

- explain the ChinaTradeResolve process and free-access limits;
- help a visitor identify useful evidence and organise a dispute description;
- explain which matters are outside scope or require urgent human professional help;
- answer in the language currently selected on the site.

Safety and privacy controls:

- the API key stays on the server and is never sent to browser JavaScript;
- the browser sends only the recent chat history to the site’s own `/api/assistant` endpoint;
- chat messages are not written to the ChinaTradeResolve case database;
- OpenAI Responses requests use `store: false`;
- input length, output length and request frequency are limited;
- the assistant is explicitly forbidden from promising outcomes, giving binding legal advice, requesting passwords/private keys or claiming access to private case data;
- a narrow moderation check blocks the most sensitive prohibited category while allowing legitimate dispute descriptions to receive safe guidance.

The public chat assistant cannot read case records, status links, email, uploaded documents or the admin database. The separate document-analysis component runs only from the private case page when enabled and consented to.

The assistant also resets the active chat whenever the visitor changes the site language, aborts any in-flight request from the previous language, and removes invalid Unicode/noncharacter artefacts from provider output before displaying it.

## Multilingual foundation

- detects the visitor’s browser language on the first visit;
- provides desktop and mobile language selectors;
- remembers the manual selection locally;
- localizes the main site, intake validation, case status, support page, legal pages and sample assessment;
- synchronizes the selected interface language with the application’s preferred-language field;
- localizes deterministic triage output and applicant emails;
- keeps the v1.8 form-error fix and never renders validation objects as `[object Object]`;
- does not include Telegram or WhatsApp integrations.

The main public page is indexable. The optional support page remains `noindex,nofollow`, and it is unavailable unless voluntary support is deliberately enabled.

## Financial model

- No service fee is charged during the free-access phase.
- There is no automatic expiry date.
- Individual cases may still be declined because of scope, urgency, evidence or available capacity.
- A future paid model may be introduced only after advance notice.
- A case already accepted as free is not converted to paid work without the user’s explicit agreement.
- Voluntary support is separate from the service and never affects acceptance, priority, review or outcome.

## Voluntary support

Voluntary support is enabled for the verified ChinaTradeResolve PayPal payment link. It remains separate from the free service and never affects acceptance, priority, review, communication or outcome.

The included PayPal link can be replaced through `PAYPAL_SUPPORT_URL`. Optional cryptocurrency addresses and another verified external provider can also be configured:

```env
ENABLE_VOLUNTARY_SUPPORT=true
PAYPAL_SUPPORT_URL=https://www.paypal.com/ncp/payment/THKQMZDRRNHQ8
SUPPORT_URL=
BTC_ADDRESS=1KPw94sUBeJH3noxdgQWrVMQf3sAebmeN4
ETH_ADDRESS=0x2F8a2773F8254d061ef286Bac8BF922344a2A494
USDT_TRC20_ADDRESS=TEJaGC38ZV8UirP7zkfPRiqHRi73wTWX5R
SOL_ADDRESS=AEZsJ2921CR7qD7kRQRS7BiaxneeaFyKMhwDmyjCS6Zm
```

When disabled, the support section, navigation link, public page and QR routes are unavailable. Public wallet addresses are not secrets, but private keys, recovery phrases and passwords must never be placed in the project or environment file.

## Feedback and testimonials

When a case is marked `closed`, the private status page displays:

- a 1–5 rating;
- a written feedback field;
- optional display name;
- separate permission for an anonymised testimonial excerpt.

Feedback is stored in SQLite and shown in the admin case view. Nothing is published automatically. Users are warned not to include supplier names, order numbers or confidential details.

## What is automated

1. Application validation and request rate limiting.
2. Scope, urgency, risk and missing-information triage.
3. Case reference and private status-link generation.
4. Routing into `pilot_candidate` (internal legacy status name), `needs_information`, `human_review` or `declined`.
5. Applicant/admin notification queue.
6. Admin exception queue ordered by risk and priority.
7. Completion email asking for optional feedback and voluntary support.
8. Audit trail for creation, triage, decisions and feedback.

## Safety boundaries

- No mandatory payment or file upload before the application is submitted; private upload is optional afterward.
- No automated supplier contact.
- No court, arbitration or authority representation.
- Deterministic hard stops cannot be overruled by AI.
- AI failure never blocks intake.
- API keys stay server-side.
- OpenAI calls use `store: false`.

## Run locally

```bash
cd ChinaTradeResolve_Document_AI_v3.7.8
cp .env.example .env
# Edit ADMIN_TOKEN and APP_SECRET.
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

- public site: `http://127.0.0.1:8000`
- admin: `http://127.0.0.1:8000/admin/login`
- support page, only when explicitly enabled: `http://127.0.0.1:8000/support`
- health: `http://127.0.0.1:8000/health`

## Enable the public AI assistant

Set these variables in Render (or in a local `.env` file):

```env
ENABLE_AI_ASSISTANT=true
OPENAI_API_KEY=...
OPENAI_MODEL=<model available in your OpenAI project>
# Optional: use a different model for the assistant.
OPENAI_ASSISTANT_MODEL=
OPENAI_MODERATION_MODEL=omni-moderation-latest
```

When `OPENAI_ASSISTANT_MODEL` is empty, the assistant uses `OPENAI_MODEL`. After deployment, `/health` must report `"ai_assistant_enabled": true`. Never place the API key in HTML, JavaScript, GitHub or screenshots.

For GPT-5.6 models, the public assistant explicitly sends `reasoning.effort=none` and low verbosity. This preserves a fast, concise informational chat and prevents hidden reasoning tokens from consuming the short response budget. Provider failures are logged with the HTTP status, safe error fields and request ID; the log never includes the API key or the user's chat text.

## Enable AI triage

```env
ENABLE_AI_TRIAGE=true
OPENAI_API_KEY=...
APPLICATION_TRIAGE_TIMEOUT_SECONDS=8
OPENAI_MODEL=<model available in your OpenAI project>
```

Application triage sends only structured intake fields, not files. Document analysis is a separate consented action from the private case page. Deterministic triage runs first; AI can add nuance but cannot lower hard-stop safety decisions.

A step-by-step Render guide in Russian is included in `AI_ASSISTANT_SETUP_RU.md`.

## Email

Configure SMTP in `.env`. Without SMTP, confirmations remain in the SQLite `notification_outbox` table.

```bash
python scripts/send_notifications.py
```

## Retention

```bash
python scripts/purge_closed_cases.py
```

## Tests

```bash
python -m pip install -r requirements-dev.txt
pytest -q
```

## Before public deployment

- replace operator/contact placeholders;
- obtain legal review for Privacy, Terms, AI Notice, Support wording and Disclaimer;
- use HTTPS and secure cookies;
- configure a real email provider;
- verify the voluntary-support wording, public wallet ownership, legal/tax treatment and accounting process;
- add managed backups, monitoring, rate limits and incident logging;
- perform privacy and security review.


## Project email configured

The public contact and operator notification address is:

```text
chinatraderesolve.support@gmail.com
```

The `.env.example` template leaves SMTP disabled by default. Use `EMAIL_SETUP.md` to add Gmail SMTP settings explicitly; passwords remain intentionally absent from the repository.

### Connect Gmail safely

1. Turn on 2-Step Verification for the Google Account.
2. Create a dedicated App Password for the website/server.
3. Copy `.env.example` to `.env`.
4. Put the App Password only in:

```env
SMTP_PASSWORD=your-16-character-app-password
```

Do not enter or share the normal Google Account password.

### Test the email connection

```bash
python scripts/test_email.py
```

A successful test sends one message to `chinatraderesolve.support@gmail.com`.

### Automatic messages after connection

- confirmation to the applicant;
- new-case alert to `chinatraderesolve.support@gmail.com`;
- optional completion/feedback request after a case is closed.

If SMTP is unavailable, the application still accepts cases and keeps messages in the SQLite `notification_outbox`.


## Persistent database for free hosting

Free Render web services have an ephemeral filesystem. Do not use the local SQLite file for public applications because it can disappear after a restart, redeploy, or idle spin-down.

For deployment, create a persistent Neon PostgreSQL database and set:

```env
DATABASE_URL=postgresql://...
```

When `DATABASE_URL` is present, the app automatically creates and uses PostgreSQL tables. When it is absent, local development and tests continue to use SQLite.

## Render deployment notes

- Docker runtime is supported.
- The Docker command binds to Render's `PORT` variable.
- Keep SMTP variables empty on a Free Render web service because outbound SMTP ports are blocked. Connect an HTTPS email provider later.
- Set `APP_SECRET` and `ADMIN_TOKEN` to separate random secrets of at least 32 characters each.


## HTTPS email bridge for Render Free

Render Free cannot use outbound SMTP ports. Configure the Google Apps Script web-app endpoint instead:

```env
EMAIL_BRIDGE_URL=https://script.google.com/macros/s/.../exec
EMAIL_BRIDGE_SECRET=the-same-secret-stored-in-Apps-Script
```

When both variables are present, queued confirmation and admin-alert emails are delivered through the HTTPS bridge. SMTP remains available as a local or non-Render fallback.
