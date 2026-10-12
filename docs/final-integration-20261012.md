# Final integration and teammate handoff — 12 October 2026

Continued from `f0b0fce` on `feature/scam-alert-intelligence`. The owner asked to
commit and push the tested work and hand the WhatsApp account portion to their
teammate. Main, private environment files, keys and the original encrypted chat
database were preserved. No queue item was retried or consumed. No hosting
account, sender, role or subscription was created.

## Actual results

| Check | Result | Evidence / remaining prerequisite |
|---|---|---|
| Backend offline | PASS | 350 tests, including native extraction, quota/503, six verdict guards and exact OpenAPI compatibility; Ruff; mypy 47 files |
| Adapter offline | PASS | 140 tests; mocked Meta/Twilio/backend; signature, deduplication, error sanitization, template gates and acknowledgement modes; Ruff |
| Website offline | PASS | 59 tests including isolated local PostgreSQL RLS, receipt/consent/owner/reviewer routes and callback/Origin checks; lint; TypeScript |
| Preview | PASS local | localhost:3001 restored with the original Supabase project and stable signing key; providers disabled; publishing false; worker not started |
| Hosted sign-in / history list | BLOCKED | Owner reported sign-in; connected browser's actual Load reports action still requires sign-in |
| Hosted save/delete/isolation | BLOCKED | Need valid user session, genuine unexpired receipt and confirmed disposable row; second legitimate user for isolation |
| Hosted reviewer / cleanup / alert withdrawal | BLOCKED | Administrator read-only migration/grant/cron check and genuine consented eligible records; no hosted writes authorized or performed |
| WHO optional retrieval correction | PASS offline / SKIPPED live | Two decisive fetched primary pages can establish a verdict while retaining an optional-source failure warning; required-source/SSRF/model/incomplete guards remain partial |
| Dynamic WhatsApp | BLOCKED | Existing Body-only send failed HTTP 400 / code 21654; account is active Trial; current sender is different from documented legacy Sandbox |
| Template delivery | PASS historical | Previously accepted, signed delivered/read callback and owner phone confirmation; no new send |
| Meta alternate | BLOCKED | Prior restriction 131031; no fresh account action or automatic fallback |
| Public production deployment | NOT IMPLEMENTED | No approved host/domain/eligible sender; backend currently needs private networking or an authenticated gateway |

Latest full frontend production build was successful in the preceding integration
pass. No new frontend source change followed that build; this pass reran the full
unit suite, lint and typecheck. Existing browser/proxy tests are earlier PASS,
not a fresh hosted run. Deprecation warnings remain in Starlette/httpx and Gemini
SDK dependencies. Offline PASS does not establish model accuracy or delivery.

## Bugs fixed

1. The verifier previously made any unavailable source force partial status.
   Ledger provenance now identifies safe optional snippet fallbacks separately
   from required failures. Only a guard-established decisive verdict can complete
   despite optional failure. Warnings remain visible; warning-bearing results
   still cannot enter the verification cache or scam-alert ingestion.
2. Preview hostname and port were inconsistent with the owner's localhost
   sign-in. The launcher accepts an explicit validated local origin and injects
   APP_ORIGIN only into its website child. Callback redirects are private/no-store.
   CSRF still rejects port 3000 and alternate host origins for port 3001 mutations.
3. Runtime tests leaked newly added environment values into following tests.
   They now isolate the entire environment mapping. Production configuration
   behavior remains unchanged.
4. Trial webhook XML incompatibility has a small opt-in acknowledgement mode.
   Empty-mode signed requests queue exactly once and return HTTP 200 without
   TwiML instructions; legacy XML remains the default. Invalid signatures still
   reject, invalid modes fail configuration, and no synchronous send occurs.
   Historical error 12300 is real; its specific old response body is unavailable.
   This compatibility option has not been enabled or proven live.
5. An added encrypted retention test proves expired observations, receipts,
   clusters and drafts stay deleted across restart in an isolated database.
   This does not prove the hosted Supabase cron job has executed.

## WhatsApp comparison for the teammate

The earlier gate record says one genuine backend round trip used 2 Gemini,
1 Tavily and 1 Twilio attempt and reached signed read status and the phone.
Its result was partial/unconfirmed. The two named private transaction summaries
are not present here, so original account/sender/window cannot be compared.

Current read-only observations used four Twilio GET requests across two bounded
passes: account endpoint HTTP 200, active Trial, credential Account SID matches;
one complete page contains ten records, seven inbound and three outbound. All
match the configured account/sender. Three existing outbound records are read;
none has a TruthLens report marker. Seven inbound records carry 12300. There is
no further page in this result. No SIDs, numbers, bodies or full API responses
were published. Absence here does not invalidate earlier owner-confirmed receipt.

The rejected send used the canonical Messages endpoint, Account SID/primary
token Basic auth, configured From/To/StatusCallback and Body. It did **not** send
ContentVariables. The recorded inbound check established the fresh reply window.
The subsequent approved template used ContentSid without Body or variables and
was delivered. This rules out broken credentials/connectivity as the cause of
that particular Body rejection. It does not prove the previous working account
was migrated; ask the teammate for the old private configuration and transaction
SID locally, never in public chat.

[Twilio's current trial](https://www.twilio.com/docs/usage/trials/try-out-whatsapp)
requires provided templates and does not support direct TwiML XML.
[Legacy Sandbox](https://www.twilio.com/docs/whatsapp/sandbox) permits freeform
replies in the user-initiated 24-hour window, but is testing-only. Generic
[21654 documentation](https://www.twilio.com/docs/api/errors/21654) describes
ContentVariables without ContentSid; that generic explanation alone cannot
explain this Body-only request. Obtain account-specific support confirmation.

Prefer the original legitimately enabled legacy account for a demo. If it is
unavailable, dynamic production requires an approved sender/account. Direct Meta
remains restricted and must not be used as an automatic fallback. Do not put an
AI report into unrelated template variables or purchase an upgrade as a shortcut.
Current [WhatsApp terms](https://www.whatsapp.com/legal/business-solution-terms)
also require an eligibility review for AI-primary functionality; do not presume
this fact-checking service is exempt or that a transport switch changes the terms.

For a confirmed legacy configuration, retain default XML acknowledgements,
remove the development-only ContentSid from **that isolated configuration**,
verify account/sender/recipient and fresh inbound window read-only, and validate
backend-mode settings offline. Keep the current original database/key intact.
For the current trial, empty acknowledgement addresses XML compatibility only;
dynamic text remains blocked. Obtain fresh approval before one development send;
then separately approve bounded AI/search usage before a genuine round trip.
Do not retry existing failed entries or start a continuous worker.

## Owner steps and demonstration

Use `http://localhost:3001/history` consistently. Retain the port-3000 Supabase
redirect entry and allow the additional exact localhost:3001 callback if needed.
Sign in in the browser being tested; only a successful Load reports establishes
authenticated list access. Use the read-only SQL in `supabase/checks/` to inspect
reviewer RLS/grants and cron. Confirm any specific migration, selected-user grant
or disposable report mutation before executing it. A saved WHO JSON without a
receipt cannot be re-signed to fabricate a valid save test.

For judges, show the existing real WHO result with its original warning/status,
explain the tested correction, and show the five-format UI plus explicit offline
fixtures separately. Show the historical delivered template as connectivity
evidence only. Do not demonstrate a synthetic result as a fresh live verdict.
Real verified/false/unconfirmed, image, voice, Hindi/Marathi and reliability
WhatsApp scenarios remain NOT TESTED in this phase until transport eligibility
and separate bounded provider/send approvals exist.

Production preparation remains in `deployment.md` and `whatsapp-deployment.md`:
HTTPS website/webhook, private backend, separate worker, durable PostgreSQL queue,
encrypted secrets/state, independent retention scheduler, count-only monitoring,
bounded replica/provider admission, backups with a tested restore, and owner-
approved release/rollback. No laptop/ngrok process counts as that deployment.
[Twilio pricing](https://www.twilio.com/en-us/whatsapp/pricing) is $0.005 per
inbound or outbound message plus applicable Meta template fees. For 1,000
one-input/one-reply interactions that is $10 in Twilio handling fees before
additional parts/templates/provider calls. Hosting, durable database, backups,
domain and AI/search budgets need a selected provider and approved quote; no
purchase was made and no unverified fixed total is promised.

This phase consumed **0 Gemini / 0 Tavily / 0 WhatsApp sends**, with four read-only
Twilio GETs and zero hosted mutations. Commit/push status is reported separately
with the actual resulting hash after Git succeeds.
