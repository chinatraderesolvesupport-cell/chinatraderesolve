# ChinaTradeResolve Document AI v3.4.5

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

## Private document analysis in v3.4.5

After an application is submitted, the private case page accepts up to twenty key files in PDF, JPG, PNG or WebP format. Each file is limited to 8 MB and each case to 45 MB total.

Security and privacy controls:

- files are stored in PostgreSQL/SQLite with the case, not on Render's ephemeral filesystem;
- file signatures are checked instead of trusting the browser MIME type;
- images are decoded and re-encoded to remove EXIF and other embedded metadata;
- obvious PDF active-content markers are rejected;
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
DOCUMENT_ANALYSIS_MAX_OUTPUT_TOKENS=3000
DOCUMENT_ANALYSIS_TIMEOUT_SECONDS=90
```

See `DOCUMENT_AI_SETUP_RU.md` for the Render checklist.

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

Voluntary support is **disabled by default**. Keep it disabled until the service operator has confirmed the legal, tax, accounting and refund handling requirements for receiving contributions.

To enable it deliberately, set `ENABLE_VOLUNTARY_SUPPORT=true` and configure either a verified external support URL or one or more public wallet addresses:

```env
ENABLE_VOLUNTARY_SUPPORT=false
SUPPORT_URL=
BTC_ADDRESS=
ETH_ADDRESS=
USDT_TRC20_ADDRESS=
SOL_ADDRESS=
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
cd ChinaTradeResolve_Document_AI_v3.4.5
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

## Enable AI triage

```env
ENABLE_AI_TRIAGE=true
OPENAI_API_KEY=...
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

The application is preconfigured for Gmail SMTP in `.env.example`, but the secret is intentionally empty.

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
- Set `APP_SECRET` and `ADMIN_TOKEN` to separate long random secrets.


## HTTPS email bridge for Render Free

Render Free cannot use outbound SMTP ports. Configure the Google Apps Script web-app endpoint instead:

```env
EMAIL_BRIDGE_URL=https://script.google.com/macros/s/.../exec
EMAIL_BRIDGE_SECRET=the-same-secret-stored-in-Apps-Script
```

When both variables are present, queued confirmation and admin-alert emails are delivered through the HTTPS bridge. SMTP remains available as a local or non-Render fallback.
