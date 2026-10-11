# Development gate report

Date: 2026-10-11. User confirmed Person 1 backend and Supabase project are not yet available; finish and test locally. Primary authority: original Word execution plan. Person 1 responsibilities have not been implemented. No production service or external account was created.

## G0 — foundation complete locally; P1 confirmation pending

Files created/modified: `frontend/package.json`, lockfile and configuration; `src/lib/api/*`, `src/lib/fixtures/*`, `.env.example`; `docs/api-contract.md`, `meta-setup.md`, `source-priority.md`; Supabase migrations.

What works with REAL backend: typed fixed-origin proxy implementation is ready, but no P1 service was available to test. No live functionality is claimed.

What works in MOCK mode ONLY: explicit synthetic UI/response examples, no actual OCR/transcription/retrieval. Production ignores fixture flags.

Tests run and results: schema/file tests pass; TypeScript/build checks pass; dependency audit has zero known vulnerabilities. Fixtures cover six verdicts and five stances.

Credentials/integration blockers: P1 origin/OpenAPI/auth; optional Supabase project; deployment account/domain. Meta requirements are prepared independently; no Meta assets configured.

Contract questions needing Person 1 confirmation: request/error/explain/health shapes, statuses/polling, upload limits/MIMEs, timeout/auth rules. Required field names/verdicts/stances remain unchanged.

Next smallest step: review provisional contract with Person 1 when their service is available.

## G1 — text/evidence flow complete locally

Files created/modified: verification workspace, results, `/api/verify`, client/server transport and schema validators.

What works with REAL backend: connection and validation paths implemented; real source retrieval/accuracy not tested.

What works in MOCK mode ONLY: supplied multi-claim example and other fixed verification responses. Arbitrary or edited input cannot be assigned a canned result.

Tests run and results: component and browser checks prove separate verdicts, source attribution, contradictory/no evidence, nullable dates and empty claims. Upstream outage/429/5xx/timeout/malformed-response tests pass without fixture fallback.

Credentials/integration blockers: P1 verification service and actual evidence.

Contract questions: verify request and completed-status semantics.

Next smallest step: run two real text claims and the RBI currency demo with P1-retrieved sources.

## G2 — multimodal UX complete locally

Files created/modified: image/audio/PDF/URL inputs and preview, editable extraction review, file validators, `/api/extract`, `/api/extract/url`.

What works with REAL backend: proxy routes and all client paths implemented; no real media processing was run. P1 still owns actual extraction and SSRF safety.

What works in MOCK mode ONLY: simulated extraction for selected files/links and supplied fixtures, visibly disclosed.

Tests run and results: all five input paths pass desktop/mobile UI tests; upload controls, extraction edits, warnings, metadata, limits and corrected-text preservation tested. User URLs are forwarded as data to a fixed P1 origin, never fetched by this website.

Credentials/integration blockers: P1 extractors, representative live files and host-compatible upload/time limits.

Contract questions: multipart field/MIMEs, extraction metadata/page references, URL response.

Next smallest step: validate one real file, then all five modalities against P1.

## G3 — accessible interface complete locally; grounded rewrites pending P1

Files created/modified: local en/hi/mr UI/privacy/error copy, preference controls, easy-reading CSS, optional speech, display-only `/api/explain` adapter and identity validation.

What works with REAL backend: explanation adapter is ready; no live translation quality or factual-grounding validation is claimed.

What works in MOCK mode ONLY: language labels and reading mode work with synthetic results. Mock mode refuses to invent translated fact-checks; original cited result remains visible with a localized notice.

Tests run and results: language/reading controls preserve claim identity/verdicts/source URLs; malformed rewrite identities rejected; desktop/mobile axe WCAG A/AA scans pass. Manual screen-reader/device listening and native-speaker review remain recommended before public release.

Credentials/integration blockers: P1 `/api/explain`.

Contract questions: display-only projection versus P1's final response, grounded rewrite behavior.

Next smallest step: validate real Hindi and Marathi explanations while preserving the underlying report.

## Secure history — implementation and isolated database verification complete

Files created/modified: `/api/history`, auth routes/callback, history view, server-only Supabase client, signed receipts, migrations, history/receipt/database tests.

What works with REAL backend: Supabase paths are implemented but no hosted project/email session was available. No live report is saved.

What works in MOCK mode ONLY: safely disabled history and explicit refusal of mock persistence. Actual database policies are independently tested in isolated PostgreSQL; that is not a simulated RLS check.

Tests run and results: actual migration proves owner read/insert/delete, cross-owner read/write/delete denial, anonymous denial, no-consent/synthetic rejection, snapshot immutability, expiry visibility and hard purge. Receipt tests reject altered reports, expired signatures and missing signing configuration. API test rejects unauthenticated history.

Credentials/integration blockers: Supabase URL/publishable key, configured email/callback, signing secret and scheduled purge. No service-role key is used.

Contract questions: none for P1 beyond retaining verifiable result identity; history is P2-owned.

Next smallest step: deploy migrations and prove email sign-in, refresh and isolation with two real users. Verify pg_cron job; do not claim deployed retention before it runs.

## G4 — local quality checks complete; live release acceptance pending

Files created/modified: tests and browser QA, security headers/CSP, setup/deployment/QA guides, README, screenshots and production smoke script.

What works with REAL backend: no live verification modalities yet. Production serves the application and reports missing backend honestly.

What works in MOCK mode ONLY: full local five-format judge walkthrough. All fictional data is labeled.

Tests run and results: 26 automated unit/component/adapter/crypto/database tests and 18 desktop/mobile/browser/accessibility checks passed, including duplicate-submission and cancellation checks. TypeScript, ESLint, formatting and production build passed. Production smoke verified nonce CSP without eval, no fixture picker/fallback, honest unavailable service and no hydration/runtime errors. Final dependency audit: zero vulnerabilities.

Credentials/integration blockers: user-confirmed absent P1 and Supabase, hosted deployment and live provider access.

Contract questions: provisional API decisions listed in `api-contract.md` remain outstanding.

Next smallest step: connect services, run at least three live modalities with tests for the other two, verify hosted history/retention, configure privacy/quotas/logging and publish HTTPS. Until then, G4's real-demo/deployment acceptance is not complete.

## G5

Deferred as approved: tracker, radar, public truth cards and full WhatsApp integration. Meta platform requirements were prepared in G0; no webhook, messaging, account configuration or external publication occurred.
