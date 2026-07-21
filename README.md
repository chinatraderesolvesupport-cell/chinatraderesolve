# ChinaTradeResolve Multilingual v2.0

Runnable free-access implementation for ChinaTradeResolve. The service is free with no fixed end date until the operator decides to introduce a different model and announces it in advance.

## Included

- six-language public application form (English, French, German, Spanish, Russian and Serbian);
- SQLite case database and audit log;
- deterministic safety-first triage;
- optional OpenAI structured triage;
- exception-driven admin queue;
- private case-status page;
- optional feedback/testimonial collection after a case is closed;
- optional voluntary project-support page;
- SMTP notification outbox;
- retention/anonymisation script;
- automated tests and Docker packaging.

## Multilingual v2.0

- detects the visitor’s browser language on the first visit;
- provides desktop and mobile language selectors;
- remembers the manual selection locally;
- localizes the main site, intake validation, case status, support page, legal pages and sample assessment;
- synchronizes the selected interface language with the application’s preferred-language field;
- localizes deterministic triage output and applicant emails;
- keeps the v1.8 form-error fix and never renders validation objects as `[object Object]`;
- does not include Telegram or WhatsApp integrations.

The public staging pages retain `noindex` until the operator is ready for search-engine indexing.

## Financial model

- No service fee is charged during the free-access phase.
- There is no automatic expiry date.
- Individual cases may still be declined because of scope, urgency, evidence or available capacity.
- A future paid model may be introduced only after advance notice.
- A case already accepted as free is not converted to paid work without the user’s explicit agreement.
- Voluntary support is separate from the service and never affects acceptance, priority, review or outcome.

## Voluntary support

The support button is provider-agnostic. Configure one server variable when a payment/support account is ready:

```env
SUPPORT_URL=https://your-support-provider.example/your-project
```

When `SUPPORT_URL` is empty, the support page clearly states that financial support is not yet connected. No code change is required later.

Before enabling support publicly, confirm the legal operator, provider terms, tax treatment, refund/error process and final wording with a qualified adviser.

## Feedback and testimonials

When a case is marked `closed`, the private status page displays:

- a 1–5 rating;
- a written feedback field;
- optional display name;
- separate permission for an anonymised testimonial excerpt.

Feedback is stored in SQLite and shown in the admin case view. Nothing is published automatically. Users are warned not to include supplier names, order numbers or confidential details.

## What is automated

1. Application validation and spam honeypot.
2. Scope, urgency, risk and missing-information triage.
3. Case reference and private status-link generation.
4. Routing into `pilot_candidate` (internal legacy status name), `needs_information`, `human_review` or `declined`.
5. Applicant/admin notification queue.
6. Admin exception queue ordered by risk and priority.
7. Completion email asking for optional feedback and voluntary support.
8. Audit trail for creation, triage, decisions and feedback.

## Safety boundaries

- No mandatory payment or file upload at application stage.
- No automated supplier contact.
- No court, arbitration or authority representation.
- Deterministic hard stops cannot be overruled by AI.
- AI failure never blocks intake.
- API keys stay server-side.
- OpenAI calls use `store: false`.

## Run locally

```bash
cd ChinaTradeResolve_Multilingual_v2.0
cp .env.example .env
# Edit ADMIN_TOKEN and APP_SECRET.
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

- public site: `http://127.0.0.1:8000`
- admin: `http://127.0.0.1:8000/admin/login`
- support page: `http://127.0.0.1:8000/support`
- health: `http://127.0.0.1:8000/health`

## Enable AI triage

```env
ENABLE_AI_TRIAGE=true
OPENAI_API_KEY=...
OPENAI_MODEL=<model available in your OpenAI project>
```

The application sends only structured intake fields, not files. Deterministic triage runs first; AI can add nuance but cannot lower hard-stop safety decisions.

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
- choose and configure a voluntary-support provider only after legal/tax review;
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
