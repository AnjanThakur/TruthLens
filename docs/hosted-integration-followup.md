# Hosted integration follow-up — 11 October 2026

This continues the feature branch from `f0b0fce`. The actual follow-up results
are in `hosted-integration-acceptance-20261011.json`. No Gemini, Tavily or Twilio
request was made. No remote database write, reviewer grant, auth redirect setting
change, or existing history deletion was performed.

**12 October update:** the current preview uses `http://localhost:3001`, including
APP_ORIGIN and `/auth/callback`. The launcher now validates the selected local
host/port without editing port-3000 configuration. The owner reported signing in;
the currently connected browser's Load reports action still returns the sign-in
requirement. This is not authenticated history acceptance. The earlier approval
review usage-limit interruption has cleared; browser access was rechecked.
Current full offline results and the read-only WhatsApp account comparison are
recorded in [the final follow-up](final-integration-20261012.md). Historical
127.0.0.1 observations below describe the earlier run, not the current origin.

## Implemented and verified

- **PASS:** feature website on port 3001 and existing website on port 3000 both
  return HTTP 200. The runner reuses the owner's original Supabase project,
  publishable key and history signing key; private files were not edited.
- **PASS:** preview `APP_ORIGIN` and callback redirects use
  `http://127.0.0.1:3001`. Callback success and failure redirects now explicitly
  set `Cache-Control: no-store, private`; the deployed missing-code callback was
  checked (307 to the same preview's history page). Successful hosted token
  exchange and browser cookie roundtrip are **BLOCKED**, not inferred from this.
- **PASS:** anonymous website history/review requests return 401; the hosted
  history table denies anonymous access with 401 / 42501. Secure, HttpOnly,
  SameSite=Lax host-scoped cookie configuration and server-validated identity
  remain unchanged and are covered by offline tests.
- **PASS (offline):** reviewer migration allows only reading one's own grant;
  authenticated users cannot self-grant, alter, delete or read another grant.
  The migration was not reapplied remotely.
- **PASS:** local alert service is healthy and publishing is false. Authenticated
  service reads return zero clusters and zero drafts; anonymous reads return 401.
  These service-token reads do not establish the owner's reviewer authorization.
- **PASS (offline):** history ownership/consent/receipt boundaries, reviewer RLS,
  alert consent/review/withdrawal and retention safeguards. A new encrypted
  repository test verifies expired observations, receipts, clusters and drafts
  remain removed after a restart, using an isolated test database.

## WHO partial-status correction

The earlier real WHO result remains recorded as **verified / partial**, with
strict full-pipeline acceptance **FAIL**. Its two decisive sources were fetched
WHO pages. A non-decisive Wikipedia page failed DNS resolution. The old engine
unconditionally set `partial` for any `source_page_unavailable` warning.

The ledger now records the failure code in the affected evidence's provenance
notes. Only failures belonging to retained, unreviewed, snippet-only sources may
be treated as optional, and only after the existing evidence guard establishes a
decisive verdict. The original warning remains present and the claim explicitly
explains that the unavailable optional source did not establish the verdict.
Failed trusted sources, unsafe URLs, absent fallback excerpts, incomplete source
content, interrupted search stages, unconfirmed assessments and model failures
still preserve partial status. Citation, conflict, date and verdict guards are
unchanged. Reports with warnings remain excluded from caching and alert ingestion.

**PASS (offline):** the reproduced non-decisive DNS case is completed with the
verified verdict and original warning; the negative cases remain partial.
**SKIPPED:** a new live WHO check, because providers must stay disabled. The old
live artifact was not rewritten or re-signed.

## Hosted blockers and owner steps

1. Sign in in the connected port-3001 preview browser. The earlier port-3000
   browser/session is not connected to this task. Cookies share a hostname across
   ports, but `localhost` and `127.0.0.1` are different hosts. Use the preview's
   canonical origin consistently. If Supabase redirects the sign-in back to port
   3000, add the exact preview callback
   `http://127.0.0.1:3001/auth/callback` to the project's allowed redirect URLs,
   retaining the existing port-3000 entries. No token, key or auth code needs to
   be shared in chat.
2. Run `supabase/checks/integration-readonly.sql` in the project's SQL editor to
   inspect tables, RLS, grants and (when installed) the named retention job and its
   recent runs. The anonymous `alert_reviewers` probe returned 404 / PGRST205;
   this alone cannot distinguish a missing table from role/schema-cache visibility.
   If missing, applying `202610110003_alert_reviewers.sql` and granting only the
   explicitly selected owner's existing Auth UUID require separate confirmation.
   No grant to all users is appropriate.
3. Real history **save/list/delete** remains **BLOCKED** until authentication and
   an unexpired genuine signed verification result are available. Website receipts
   expire after one hour. The recorded WHO JSON contains no receipt; a new receipt
   was not manufactured. The original partial WHO report also does not satisfy
   the database's completed-report constraint. Do not enable providers simply to
   unblock this test. An existing genuine unexpired completed result can be used
   with explicit confirmation to save one disposable report, list it, and delete
   only that newly saved report. Existing owner reports remain untouched.
4. Hosted user-isolation verification requires a second legitimate signed-in user
   and a confirmed disposable report. Local PostgreSQL isolation tests pass but
   do not substitute for two hosted sessions.
5. Hosted cron hard-deletion and authenticated alert review/withdrawal remain
   **BLOCKED**. Cron needs an administrator read-only check; a destructive cleanup
   test needs confirmation. Alert review additionally needs an authorized reviewer
   and genuine eligible consented scam submissions. No fake contributors or drafts
   were inserted into the running dashboard to claim success. Withdrawal must be
   limited to confirmed consented test contributions.

The WhatsApp worker remains paused and dynamic delivery remains **BLOCKED** by the
account's existing restrictions. Prior template connectivity success does not
authorize or prove dynamic report delivery.

## Targeted validation

- Backend: **192 tests PASS** across optional retrieval, URL workflow, pipeline,
  six verdict grounding, quota/cache, final guard, alert and persistence suites.
- Frontend: **24 tests PASS** across preview authentication, receipts, history,
  reviewer/owner RLS and alert consent/review/withdrawal routes.
- Ruff, mypy (47 source files), frontend lint, TypeScript and production build:
  **PASS**. Deprecation warnings from existing Starlette/httpx and Gemini SDK
  dependencies remain; no new runtime provider requests were needed.

All changes are confined to the feature worktree. No Person 2/main configuration,
frontend private keys, hosted schema, WhatsApp outbox or original encrypted adapter
database was changed.
