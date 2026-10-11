# TruthLens required WhatsApp milestone report

Date: 2026-10-11. Branch: `feature/person2-whatsapp`. Person 1 backend code and schemas are unchanged. Existing Next.js code is preserved and its API consumer corrected. No Meta account action, real WhatsApp send, paid Gemini/Tavily request, push or public deployment was performed.

## W0 contract and configuration - PASS locally

Implemented: canonical website verify/extract/explain contracts, complete result preservation, structured context, partial/no-checkable-claims support, actual supported MIME list, explicit adult/senior mapping, page-chunk review and source priority/ownership documentation. Exact backend OpenAPI is packaged in the separate adapter and checked for drift. Original fictional fixture JSON is unchanged; development-only conversion preserves the demo.

Validation: website contract and proxy regressions pass; the shared full-result fixture validates against P1's exact exported schema; adapter pin compares to the original OpenAPI. Git diff confirms no `backend/`, backend contract or original OpenAPI edits. Person 1 review/live origin confirmation remains pending; no messages were sent on the owner's behalf.

## W1 signed messaging - PASS offline; live delivery BLOCKED

Implemented: webhook challenge, raw-body HMAC with constant-time comparison, phone/WABA filtering, bounded event parsing, encrypted durable SQLite jobs, keyed identifier hashes, atomic admission, duplicate suppression, separate worker and development reply. Production PostgreSQL implementation is prepared. Defaults disable actual Graph sends.

Validation: valid/tampered signatures, token rejection, malformed/batched events, wrong account, status-only events, size/rate limits and encrypted restart-persistent dedup tests pass. The offline demo submits a signed event twice and produces exactly one intercepted Meta send. No message was delivered through actual Meta infrastructure.

Blockers: owner-authorized account setup, actual Meta credentials/test recipient, HTTPS callback/subscription and specific live-send approval.

## W2 shared text backend - PASS offline; live factual acceptance BLOCKED

Implemented: fixed-origin P1 client, exact request fields, response JSON Schema validation, provider approval/rotation gates, concise per-claim verdict/source replies, partial warnings and neutral technical errors. No alternate AI verifier or provider SDK is added.

Validation: signed webhook through actual adapter clients/worker to HTTP-mocked P1 and HTTP-mocked Graph, duplicate replay and signed delivery-status reconciliation pass. Invalid contract, provider 429/503/504, bounded requests and no automatic paid retry are tested. All six verdicts retain their exact meaning.

Blockers: provider-key rotation is unverified; explicit paid-test approval/budget and running reachable P1 runtime are needed. A real sourced check delivered to WhatsApp has not occurred.

## W3 formats - PASS offline; individual live tests BLOCKED

Implemented/tested: text; URL through P1 SSRF-safe extraction; authenticated Meta image/audio/PDF media lookup/download; streaming size, MIME/signature/checksum/host restrictions; multipart `file`; extracted type checks; extraction warnings. Unsupported encodings/documents receive truthful errors. Large preview PDFs request splitting or website review, never a whole-document verdict.

Every required route has deterministic tests. No actual Meta media was downloaded. Live screenshot, voice note, PDF and URL WhatsApp flows are untested. P1's earlier audio 503 and broader accuracy limitations remain unresolved. Additional live provider tests require separate approval; these formats are not labeled live complete.

## W4 accessibility and frontend - PASS automated; real number pending

Implemented: actual P1-compatible website requests/results/re-explanation, partial-warning UI, selected-page-chunk review, localized verdicts and existing en/hi/mr interface, HELP/SOURCES/language/STOP/START, hidden-until-configured click-to-chat and guarded QR generation utility. No fabricated number/link/QR was published. WhatsApp framing/help copy uses English; native-speaker and manual screen-reader reviews remain release tasks.

Validation: 30 website unit/component/contract/crypto/database tests and 22 desktop/mobile browser checks pass. Browser suite includes automated WCAG checks, actual backend-shaped partial response/context and PDF preview chunk selection. Existing five-format synthetic demonstration remains usable.

## W5 reliability/deployment - local PASS; hosted acceptance BLOCKED

Implemented: encrypted persisted job/outbox state, per-sender processing serialization, crash-safe refusal to replay possibly paid calls, bounded definite-429 retries, uncertain-send reconciliation, service-window suppression, opt-out even at queue capacity, one-minute content cleanup and hashed dedup tombstones. Runtime/development dependency locks, non-root Docker image and separate-worker/private-backend deployment guide prepared.

Validation: 52 adapter tests pass. Ruff lint/format, pip dependency consistency and pip-audit pass. Initial cryptography advisory was fixed by upgrading to 50.0.0; final adapter lock and npm audit show no known vulnerabilities. Website typecheck, ESLint, formatting and production build pass. Local production smoke passes nonce CSP/no eval, no fictional fallback, honest outage behavior and no hydration/runtime errors.

Limitations: hosted PostgreSQL locking/multi-host recovery, Docker image execution, TLS/hosting, operational monitoring/backups, Supabase email/cron and real Meta delivery were not exercised. Docker/PostgreSQL services are not available in this workspace. A third-party Starlette/httpx test-client deprecation warning is non-fatal. Audit databases cannot establish absence of unknown vulnerabilities.

## W6 acceptance/handoff - package ready; final acceptance BLOCKED

Delivered: adapter source/tests, offline demonstration, configuration template, exact contract mapping, dependency locks, QR utility, test-number instructions, deployment/rollback guide and this gate report. User-provided instruction documents remain preserved. No shared-main history was rewritten and no branch was pushed.

Current proof: **52 adapter + 30 website + 22 browser tests pass**, with only mocked external services. Offline signature/routing success is not a live bot claim.

Required next human steps, in order:

1. Approve Meta account setup and privately configure assets, secrets, approved recipient and HTTPS callback. Specific approval to send a live development reply is required; this test needs no model/search credits.
2. Demonstrate actual signed receipt and delivered development reply. Record safe IDs/status evidence, without private phone numbers or message dumps.
3. Rotate/revoke exposed provider keys privately, confirm rotation and approve a narrowly budgeted live backend test. Each check may consume several provider calls/retries. Stop on failure; no extra test credits are authorized.
4. Demonstrate an actual P1-backed sourced text result delivered through Meta. Obtain further approval for live media/language tests.
5. Confirm current Meta eligibility/app/business/number requirements before public launch. Obtain production publication approval and test the selected host/database/worker.

No claim of fully functional, publicly approved or production-ready fact-checking is made before these steps pass. Actual acceptance must be recorded separately as PASS/FAIL/SKIPPED/BLOCKED; failures must not be replaced with fixtures.
