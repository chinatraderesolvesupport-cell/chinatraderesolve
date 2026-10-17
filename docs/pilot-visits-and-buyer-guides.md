# Pilot visits, usage and buyer guides

Scope: `feature/sourcing-pilot`, staged deployment only. Production integration remains separate.

## Buyer guidance

`/sourcing/help` links four practical guide groups, each available in ru/en/de/fr/es/sr. Individual topic titles describe actual buyer questions. The pages cover supplier identity and role, sample versus bulk specifications, total cost and documents, and photos/alternatives. Existing dispute guide hubs remain linked. No country-specific rates or platform refund deadlines are invented. All pilot pages remain noindex/noarchive; public indexing, canonical/hreflang, sitemap inclusion and production redirects must be handled together during integration, without indexing private requests.

Optional `platform` and `purchase_purpose` enums are saved in schema-version 3 briefs. Old briefs remain readable. Unknown enum values are rejected. Language and destination remain distinct.

## Admin statistics

`/admin/sourcing-statistics` requires the existing administrator session and is linked from the main admin page and sourcing queue while the pilot is enabled. UTC windows include today, the last 7 calendar days and the last 30 calendar days. No public numbers are displayed.

* Page views: successfully rendered allowlisted public pilot pages and valid help topics.
* Approximate visits: first counted view per signed browser session per UTC day. This is a browser-day estimate, not a person count or a 30-minute visit definition. Cookie resets, parallel initial requests and multiple browsers can inflate it; shared browsers can reduce it.
* New requests: records created during the period. Idempotent submission replay does not create another record.
* Requests receiving reports: distinct request IDs with a report publication during the period; multiple revisions count once within each window. Reports may refer to older requests, so do not calculate a funnel conversion from these period totals. Deletion removes requests/reports from these operational counts.

Daily view aggregates persist in PostgreSQL (`sourcing_daily_stats`: day, pageviews, sessions), not process memory. Only an updated day marker is added to the existing signed session. No IP, browser ID, referrer, URL/query, request identifier, email, photo or access code is stored in that table. Existing rate-limiter IP-derived keys remain memory-only. Admin sessions, DNT=1, Sec-GPC=1, empty agents and common bots are excluded. This is heuristic filtering, not bot-proof audience measurement. Counter write errors fail open for the public page.

The counter is deliberately called only by the enabled pilot renderer. `/health`, static files, admin/private pages and production public routes do not cause analytics writes. Integrating analytics into production needs an explicit decision about traffic scope, cookie/privacy text and database-wakeup costs; do not install a global per-request database middleware. Historic visits cannot be reconstructed. The first stored view day is shown; no fabricated backfill. The public footer explains counting and DNT/GPC.

The existing admin “traffic sources” block counts submitted dispute cases by attribution; it must not be presented as website visitor statistics.

## Validation

Server tests cover six-language pages and context fields, access restrictions, session-day deduplication, filtering, private-route exclusion, persistence shape, 1/7/30-day windows, report revision deduplication, deletion behavior and fail-open writes. The existing isolated CI browser flow exercises the mobile form, selected context, operator statistics and six-language help pages, with synthetic data only. Browser bots are intentionally excluded from audience counts.
