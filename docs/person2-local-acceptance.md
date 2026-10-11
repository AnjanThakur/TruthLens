# Person 2 local acceptance — 2026-10-11

This pass completes additional integration work while Person 1 improves evidence quality. It does not modify Person 1 backend source, enable provider/messaging flags, access accounts, publish, or spend Gemini/Tavily/Twilio credits.

## Implemented

- Website deadlines: the server proxy defaults to 195 seconds, outliving P1's default 180-second request deadline. Valid overrides are 1–300 seconds. The browser waits up to 330 seconds and distinguishes timeout, unavailable service and user cancellation. Invalid backend URLs/deadlines fail before a fetch. Hosting must support the selected duration.
- Shared upload limit: `MAX_UPLOAD_BYTES` controls the server cap, browser validation and localized size display. The maximum remains 10 MiB; reduce it for the selected host, allowing multipart overhead. Invalid values fail closed.
- Real proxy acceptance: a production Next.js instance uses both mock flags false and calls a separate loopback-only fake P1 HTTP server. Desktop/mobile tests cover all five inputs, extraction review, contract fields, source identity, English/Hindi/Marathi explanation requests, partial/unconfirmed presentation, upstream failure, actual timeout and client/server upload rejection. Test responses explicitly say offline/fictional. No OCR, public article fetching, translation quality or real model accuracy is claimed.
- Controlled WhatsApp testing: `truthlens_whatsapp.controlled_test` scopes claims and replies to one selected inbound message. It caps backend requests and reply/outbox steps, waits a bounded period for that message, never processes unrelated entries and refuses replay of a completed/failed job. It never enables disabled flags. Zero backend requests is the default. Attempt counts and job failure are reported separately from delivery.
- Reply URLs: normal URLs stay intact across Twilio message parts. A URL exceeding a whole part is replaced with an explicit omission notice, not a broken/shortened URL or an invented public report link. The source title/publisher remains. Full long-link delivery still needs a reviewed public-report design if required.
- History API acceptance: mocked SDK tests cover explicit consent, authentic unmodified report receipts, owner assignment, deletion scoping, cross-origin rejection and sanitized storage failures. Existing isolated PostgreSQL RLS tests remain part of `npm test`. Hosted email/session/retention acceptance is separate.
- CI preparation: `.github/workflows/person2-offline.yml` runs website and adapter checks without provider/account secrets. It is prepared, not yet proven by a GitHub run. Deployment docs now reflect required WhatsApp ownership and distinguish Sandbox from production.

## Local results

| Check | Result |
| --- | --- |
| Website unit/component/contract/security/history/RLS | 40 passed |
| Existing desktop/mobile browser and accessibility | 22 passed |
| New production proxy integration, desktop/mobile | 6 passed |
| Adapter offline suite, including bounded selection and source links | 92 passed |
| Website lint, format, TypeScript/build | Passed |
| Adapter Ruff check/format and dependency check | Passed |

Windows sandbox initially prevented Python event-loop creation and Next.js path resolution; those checks were rerun successfully outside the restricted sandbox, still with mocked services. Vitest used a workspace-local temporary directory. One added multi-part test fixture initially exceeded P1's explanation schema limit; the fixture was corrected without relaxing the contract.

## Repeat website checks without Person 1 or provider keys

From `frontend`, with the locked dependencies installed:

```powershell
npm ci
npm run typecheck
npm run lint
npm test
npm run test:e2e
npm run build
npm run test:integration
```

Run the build after `test:e2e`: Next.js development and production use the same `.next` directory. Do not run the two browser suites concurrently. The integration suite starts/stops its own production website on loopback port 3101 and fake upstream on 18101, so those ports must be available. It overwrites transport/account settings for the test process only and never edits private env files. Its 1.5-second upstream timeout and 1 MiB cap are deliberate test overrides, not production defaults.

For sandbox-related Vitest temp-file errors on Windows, set workspace-local temporary paths before `npm test`:

```powershell
$env:TEMP = Join-Path $PWD '.tmp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Path $env:TEMP -Force | Out-Null
npm test
```

## Controlled real WhatsApp test — only after separate approval

Do not run a normal continuous worker alongside this command. Keep the web process and approved tunnel running; select one fresh inbound SID from the account's private logs. Configure `.env.twilio` privately according to `twilio-sandbox-setup.md`, then, from the adapter environment:

```powershell
$env:TRUTHLENS_ENV_FILE = '.env.twilio'
.\.venv\Scripts\python.exe -m truthlens_whatsapp.controlled_test --message-id SM_REPLACE_WITH_REAL_INBOUND_SID --max-backend-requests 0 --max-send-attempts 1 --wait-seconds 30
```

The placeholder SID is intentionally invalid; replace it privately. Use development response mode for a zero-AI delivery check. Backend mode additionally requires the existing explicit provider approval/credential flags and an approved backend request allowance. Text normally needs one `/api/verify` call; image/audio/PDF/URL generally need extraction plus verification. A language change for a saved report can need explanation calls. If the cap is exhausted, no additional backend HTTP request is made and the reply must remain a service-error response without a factual verdict.

**A backend HTTP request can internally consume multiple Gemini/Tavily calls.** This is not a monetary/provider-call cap. Agree P1's internal budgets/retries before live testing. The allowance applies to this invocation; additional invocations/messages need authorization. Reply caps may leave parts pending; the tool reports this and will not replay them on rerun. Do not start a continuous worker just to flush leftovers without reviewing them and obtaining approval.

Receipt/media/status requests can consume transport allowance separately. Successful processing or an API-accepted send does not establish physical delivery, source quality or accuracy. Inspect signed delivered/read state and the phone; assess `partial`/`unconfirmed` honestly.

## Still external or blocked

- Person 1: source-fetch diagnostics, relevant evidence and actual extraction/language/provider quality; the three previously recorded backend test failures remain outside this pass.
- Person 2: real Twilio attachments/languages and command acceptance with an approved budget; actual media redirects remain refused until the official host/auth behavior can be safely confirmed. The authenticated scoped media resource follows [Twilio's media API](https://www.twilio.com/docs/messaging/api/media-resource); arbitrary redirect hosts are not authorized by that contract.
- Supabase: a real project, email callbacks, two users, scheduled purge and hosted session/retention checks.
- Production: approved host/domain, persistent database, private/authenticated backend, monitoring/restore, supported production WhatsApp sender/transport and account eligibility. Twilio Sandbox remains test-only and Meta restriction is unresolved.
- No actual secret revocation has been confirmed. The owner's earlier local waiver is not production credential approval.
