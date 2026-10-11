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

## Twilio Sandbox testing transport - PASS offline; live delivery BLOCKED

Added a separate, test-only Twilio transport after the owner's Meta test WABA was restricted with error 131031. The existing Meta adapter, website and Person 1 backend remain preserved. Both transports use the same worker and Person 1 API client; no alternate verification engine was introduced.

Implemented: official SDK signature validation against a configured HTTPS origin, bounded form parsing, account/sender/media checks, transport-isolated encrypted state, duplicate protection, signed status callbacks, authenticated receipt-time validation before processing, conservative send handling, and a private configuration wizard that leaves all live flags disabled. Development replies explicitly say no fact-check was performed. Twilio production mode is rejected.

Validation: **81 adapter tests pass (52 existing plus 29 Twilio tests)**, with mocked messaging and backend services. The Twilio dependency lock passes pip-audit with no known vulnerabilities; pip dependency consistency passes. No live Twilio requests, paid AI/search calls, account changes or public tunnel were performed.

Blocked: ngrok is not available on PATH, private `.env.twilio` is not configured, and live-message/tunnel approval is pending. The owner reports joining the legacy Sandbox, but actual signed receipt and phone delivery have not been demonstrated. Real media downloads, CDN redirect compatibility and long source-link usability remain acceptance checks. Provider credential rotation and separately approved backend testing are still required before real verdicts.

Follow [the Sandbox setup guide](twilio-sandbox-setup.md). This transport does not remove Meta's restriction or establish production eligibility. Website checks were not repeated for this adapter-only addition; the prior website results above remain the last recorded results.

### Owner-approved first live development attempt (2026-10-11) - FAIL: authentication

The owner configured private credentials, started ngrok, and approved saving the Sandbox webhook plus one development reply using trial allowance, with zero AI/search calls. The webhook URL and POST method were saved and verified after reload. A temporary worker was limited to one send attempt; persisted outbound flags remain false.

The actual inbound POST reached the local app but returned **403 Invalid signature**. Local inspection of the existing ngrok capture confirmed matching account, target number and public host, and a present signature. The saved token did not match the expected Auth Token format; offline signature verification failed. No job was accepted, no outbound reply was attempted, and no backend client was instantiated. The test worker was stopped. Real message receipt at ngrok is established; authenticated acceptance and delivery remain blocked pending private token correction and restart.

Added `configure_twilio --update-token` to repair only the private token while preserving encryption/identity keys and disabled flags. Three focused configuration tests pass, including invalid-token refusal and preservation of existing settings; Ruff passes. The original 81-test result above predates this small fix. Signature validation remains enabled.

### Token correction and one development reply (2026-10-11) - PASS delivery after controlled replay

The owner privately corrected the token. Offline validation of the original captured inbound message then passed with matching account, recipient and public origin. The local webhook server was restarted to load the corrected token. The same original signed `Hi` capture was reprocessed locally, preserving its signature and form body; it returned **200** and created one completed job. This was a controlled replay after the initial live request failed authentication, not a second fresh inbound message from Twilio.

A temporary test worker used Twilio's actual canonical message API and attempted exactly one development reply. No backend client was instantiated, and AI/search remained disabled. Twilio accepted the reply; subsequent signature-validated status callbacks returned **204** and advanced the outbox to **read**, with **one attempt**. Delivery and read confirmation are established for the development response. The temporary worker exited; persisted sending flags remain false, so additional messages will not automatically receive replies.

Still pending: a fresh direct authenticated inbound test, individual media acceptance, real Person 1 backend checks, provider-key rotation confirmation and explicit AI/search budget approval. No real factual verdict, production deployment or permanent bot operation has been demonstrated.

### Local backend preparation (2026-10-11) - offline checks; live AI blocked

Created an ignored backend virtual environment and installed Person 1's declared dependencies without changing backend source. Both provider settings are present in the ignored private `.env`; their values were not displayed. The owner generated new keys, but revocation of previously exposed keys remains unconfirmed. No real provider test or AI/search credit use was performed.

Backend dependency consistency passes. Offline tests, with real credentials excluded from the test process, report **190 passed, 3 failed, 2 skipped**. An initial missing temporary-directory issue was corrected locally. The remaining schema snapshot failure consists only of HTTP 413/422 description wording differences; schema fields, verdicts and endpoint contracts are unchanged. Two native Hindi/Marathi OCR tests fail on this machine and remain unresolved; two other native-media tests skip. These results do not establish full media readiness or live verification readiness.

Live AI/search stays disabled until exposed-key revocation is clarified and the owner approves a bounded provider test. The previously successful WhatsApp development reply does not establish a real fact-checking result.

### Owner waiver and first new-key backend check (2026-10-11) - FAIL: provider unavailable

The owner explicitly waived waiting for old-key revocation and authorized proceeding with the new keys. Added a test-only `PROVIDER_KEY_REVOCATION_WAIVED` setting; rotation remains unconfirmed and is not falsely marked complete. Backend use still requires separate consumption enablement. The waiver cannot authorize production. Both Settings validation and the API client enforce this distinction. **85 offline adapter tests pass**, and Ruff check/format pass. Person 1 backend source remains unchanged.

Ran one English text check through Person 1's real FastAPI verification route using the private new keys. The call budget was three Gemini attempts and one Tavily search, with provider retries disabled. Actual usage: **one Gemini request, zero Tavily requests**. Gemini returned **503**, classified as `transient_server` during `claim_extraction`; the backend returned a safe `llm_provider_error` response (HTTP 502). Stopped without retries or further live tests. No factual verdict or WhatsApp send occurred, and credential validity is not established by this error. The private report is ignored at `backend/.tmp/new-keys-text-check.json`.

Recorded only the owner waiver in private adapter settings; persisted backend consumption and messaging remain disabled. A further live attempt needs approval; real sourced verification and its WhatsApp delivery remain unproven.

### Replacement-key test and local startup (2026-10-11) - FAIL: model timeout; services running

The owner supplied a replacement Gemini key privately to the backend configuration and explicitly requested testing/running the project. The first launch was denied by an automatic permission-review timeout before execution; the permitted single launch retry succeeded. The actual text check was capped at three Gemini attempts and one Tavily search with retries disabled. It stopped at `llm_timeout` during verification: **one Gemini attempt, zero Tavily searches**. No factual verdict, further provider attempt or WhatsApp send occurred. The ignored local report is `backend/.tmp/replacement-key-text-check.json`; credential validity remains unproven.

Started the local backend on `127.0.0.1:8000`, with one claim/search per claim and one provider attempt configured. Its `/api/health` returns 200. The existing adapter on `127.0.0.1:8100` returns 200 in Twilio development mode with both outbound flags false; a duplicate server launch was stopped by the OS because that port was already occupied. The existing HTTPS ngrok tunnel still targets port 8100. No worker is processing/sending messages for this run. Health proves local readiness only, not provider availability or a functional live fact-checking bot.

Local dependency inspection confirms only English/OSD Tesseract data and no FFmpeg/FFprobe on the backend PATH, explaining remaining language/media readiness gaps. No Person 1 source was modified. The configured Gemini model exists in Google's official model documentation; no model substitution or fabricated result was used to hide the timeout.

### Minimal Gemini diagnostic (2026-10-11) - PASS basic access

The owner approved one minimal diagnostic after the full verification timeout. Using the current private key, the official SDK and the same `gemini-3.8-flash` Interactions endpoint returned completed text exactly `Hello`. Actual usage: **one Gemini attempt, zero Tavily searches, zero WhatsApp sends**; generated-client retries were disabled. This proves current key/basic model access for that request, not full structured verification or stable availability. No backend source was changed. The ignored local result is `backend/.tmp/gemini-hello-result.json`.

The earlier full-check failure remains unresolved: intermittent availability, latency and structured-request behavior still require isolation. A further real verification attempt requires approval under the owner's live-testing instruction. No fabricated verdict or automatic retry was used.

### Approved full text-check retry (2026-10-11) - PASS backend and offline reply formatting

The owner approved one full text-check retry capped at three Gemini attempts and one Tavily search. Actual usage: **two Gemini attempts and one Tavily search**, with automatic retries disabled. The existing Person 1 FastAPI verification route returned `completed` without warnings. For the test claim about all Rs 500 notes becoming invalid next Monday, the actual verdict was **`unconfirmed`**, with three evidence entries. Limitations explicitly state that no current announcement or directly assessed trusted fetched source establishes the claim. This is an actual uncertainty result, not proof the claim is false; the verdict was not forced.

The real response passes the adapter's pinned `VerificationResult` schema and its WhatsApp formatter/splitter offline, yielding one reply part within the 1500 UTF-16-unit limit. No additional provider requests were made for formatting/contract verification. The ignored report is `backend/.tmp/full-text-check-success.json`. No Person 1 backend source was changed.

This establishes one real sourced backend text response and compatible reply formatting, not stable provider availability, broad fact-check accuracy or WhatsApp delivery of a real verdict. Automatic outbound flags remain false. Next acceptance requires owner approval for a bounded live WhatsApp text round trip (Twilio usage plus a new bounded AI/search check).

### Fresh WhatsApp text round trip (2026-10-11) - PASS received, checked and read

The owner approved one real round trip with up to three Gemini attempts, one Tavily search and Twilio trial usage, then sent the claim from the joined phone. The existing signed Twilio webhook accepted the fresh inbound message into the encrypted queue. A strict temporary test guard initially stopped before network use because punctuation differed from the supplied example; offline review established identical words and amount. The same queued message was resumed without asking the owner to resend or replaying a captured webhook.

The one-message worker performed Twilio's canonical inbound-message check and called Person 1's actual verification route on a temporary loopback test runtime. That runtime reused the existing backend app/provider code unchanged and enforced a total budget of three Gemini attempts and one Tavily search. Actual usage: **two Gemini attempts, one Tavily search, one Twilio reply attempt**, no automatic provider or send retries. The transport job completed, but the verification result was **`partial`**, returning **`unconfirmed` with three evidence entries** and `source_page_unavailable:url_fetch_error`. This distinction was verified against the stored report after the owner shared the received reply. Transport completion is not full verification acceptance.

The worker formatted one reply part and Twilio accepted it. A subsequent signature-validated callback advanced that specific outbox entry to **`read`**, with **one attempt**; the job completed without error. This establishes one real fresh inbound-to-backend-to-WhatsApp text path and read confirmation. It does not establish broad accuracy, media compatibility, uninterrupted availability or production eligibility.

The one-message worker exited and the temporary bounded backend runtime was stopped after the test. Persisted messaging/backend flags remain disabled; the normal local backend and queue-only webhook service remain available. Private test summaries are ignored at `whatsapp-adapter/.tmp/twilio-backend-once-result.json` and `.tmp/twilio-backend-delivery.json`. Person 1 source, website code and shared main history were not modified. Further live tests or continuous credit-consuming operation require approval.

Owner phone confirmation matches the stored report: all three source stances were neutral; at least one evidence item was snippet-only; no directly assessed trusted fetched source established the exact relative-date claim. The delivered `PARTIAL CHECK` label and `unconfirmed` verdict correctly preserve those limitations. The generic `url_fetch_error` collapses HTTP/network failures, so its specific upstream cause is not established by the saved report. Source retrieval and adequate relevant evidence remain Person 1 backend integration issues requiring coordination; no verdict guard was weakened and no further paid test was made during this inspection.

## Person 2 work while awaiting Person 1 — 2026-10-11

Completed website timeout/upload alignment, production-proxy browser acceptance with a loopback fake backend, private-history API security checks, controlled single-message WhatsApp test tooling and URL-preserving reply splitting. Added offline GitHub Actions preparation and reconciled deployment/handoff documentation. Person 1 backend source and private configuration are preserved; no provider/messaging flags were enabled, paid requests sent, account settings changed or production deployment made.

Local results: 92 adapter tests, 40 website tests (including isolated PostgreSQL RLS), 22 existing browser/accessibility checks, six production proxy browser checks; website lint/format/build and adapter Ruff/dependency checks pass. The Windows sandbox initially blocked compiler/event-loop operations; offline checks passed after rerunning with appropriate local execution permissions. Hosted CI has not run yet. See `person2-local-acceptance.md` for commands and limitations.

Remaining: Person 1 evidence/native extraction quality; approved real WhatsApp media/language checks and safe CDN behavior; actual website/provider acceptance; hosted Supabase email/isolation/retention; production hosting/transport/account eligibility and release approval. Offline fixture checks are not real fact-check or message-delivery acceptance.
