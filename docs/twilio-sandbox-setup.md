# Satyavaani / TruthLens: Twilio WhatsApp Sandbox

**Current account follow-up, 12 October:** the configured sender differs from
Twilio's documented legacy Sandbox sender. Read-only account/message API calls
succeeded; the account is active Trial. The latest Body-only POST failed
400/21654 and the selected ContentSid template reached the phone. Earlier dynamic
delivery is recorded below, but its private transaction/configuration artifacts
are absent from this checkout, so continuity with this account is unproven.
See [teammate handoff](final-integration-20261012.md). Keep the consuming worker
paused. Never copy a legacy sender into configuration without account eligibility
and participation checks.

Existing inbound message records also carry error 12300 (unsupported content
type). The new trial explicitly forbids direct TwiML XML. After confirming that
flow, `TWILIO_WEBHOOK_ACK_MODE=empty` selects an empty text/plain HTTP 200 instead
of XML. The default `twiml` preserves legacy behavior; signed admission and
durable deduplication are unchanged. This option passed offline tests only and
has not been enabled in the private file or verified on a fresh live webhook.
It does not unlock Body sends or generate a reply. The exact historical response
that produced 12300 was not available from the message metadata.

This is an additional **test-only transport**, preserving the existing Meta Cloud API adapter, Next.js website and Person 1 backend. It is not a WhatsApp Channel integration. A Channel publishes updates; this adapter receives private WhatsApp messages and replies in that chat.

Status: **one fresh real Twilio delivery round trip through Person 1's backend passed**, reaching a signature-validated `read` callback and owner phone confirmation. The actual verification was **partial**, with an `unconfirmed` verdict, three neutral evidence entries and a source-page retrieval failure; full evidence/accuracy acceptance is still pending. The one-message worker stopped after one send attempt; automatic messaging remains disabled. Media, language and production acceptance also remain pending. The owner's existing Meta test WABA is restricted (131031, dashboard requests business verification). See [the gate record](whatsapp-gates.md) for actual test results.

## 1. Account and permission boundary

The legacy Twilio Sandbox supports a preconfigured sender without registering the owner's own WABA. The newer trial flow has different limitations; do not assume custom reply capabilities based on having trial credit. The owner is currently using the legacy Sandbox screen with `Sandbox settings` available. Sandbox participants must join with the account-specific join message. Joining expires after three days. Test-only use, at most one message every three seconds; the worker waits 3.1 seconds between attempts.

Sandbox messages can consume trial allowance and are billed according to Twilio's applicable pricing. Do not upgrade, buy a sender or spend paid balance without the owner's approval. Gemini/Tavily approval is separate. A Twilio Sandbox is not evidence of production eligibility and does not unlock the restricted Meta WABA.

Official references checked 2026-10-11: [Sandbox](https://www.twilio.com/docs/whatsapp/sandbox), [current trial differences](https://www.twilio.com/docs/usage/trials/try-out-whatsapp), [request signatures](https://www.twilio.com/docs/usage/security), [inbound parameters](https://www.twilio.com/docs/messaging/guides/webhook-request), [message API/status callbacks](https://www.twilio.com/docs/messaging/api/message-resource).

## 2. Install (already installed in this checkout)

From PowerShell:

```powershell
Set-Location 'C:\Users\Gaurav Choithramani\Desktop\hackOnTrack\whatsapp-adapter'
.\.venv\Scripts\python.exe -m pip install -r requirements-twilio-lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
```

Twilio's official Python SDK 9.11.2 validates signatures; HTTPX performs explicit bounded transport requests. No Twilio SDK retry policy is used for sending.

## 3. Prepare the private settings

Install/configure [ngrok](https://ngrok.com/docs/start) yourself. Creating the account, accepting terms and authenticating must be completed by the owner. Do not post ngrok tokens in chat. Do not open a public tunnel until the owner approves it. A prepared server cannot receive real Twilio messages before a reachable HTTPS callback is configured.

After tunnel approval, start `ngrok http 8100` and leave that window open. Copy the HTTPS origin (no trailing path). Then run:

```powershell
.\.venv\Scripts\python.exe -m truthlens_whatsapp.configure_twilio
```

Enter the Twilio **Account SID** and **primary Auth Token** from the Account Dashboard privately. Token input is hidden. Enter the exact Sandbox sender as `whatsapp:+...` (including `whatsapp:` and country code). Enter the HTTPS ngrok origin.

The wizard creates ignored `.env.twilio`, generates encryption/identity keys, uses a separate `state/twilio-sandbox.sqlite3`, and refuses to overwrite an existing file. It preserves Meta's `.env`. Do not commit or share either private file. Restrict access to the workspace and private files to the owner; Python file permissions alone do not configure Windows ACLs.

If the wrong Auth Token was copied, run `python -m truthlens_whatsapp.configure_twilio --update-token` using the adapter's virtual environment. The hidden prompt replaces only `TWILIO_AUTH_TOKEN`, checks its expected 32-character hexadecimal format, and preserves the encryption/identity keys and disabled flags. Format validation does not prove that a token belongs to the intended account. Restart the server and worker after updating it; never disable signature validation to fix a 403.

All live flags remain false. The webhook can acknowledge a correctly signed event, but the worker will not process or send Twilio jobs until `TWILIO_OUTBOUND_ENABLED=true` is explicitly authorized. This gate covers the authenticated Twilio receipt lookup, media requests and sends, which may consume allowance.

Keep these settings for the first test:

```dotenv
MESSAGING_PROVIDER=twilio
BOT_ENV=test
RESPONSE_MODE=development
TWILIO_OUTBOUND_ENABLED=false
META_OUTBOUND_ENABLED=false
BACKEND_ENABLED=false
PROVIDER_CREDENTIALS_ROTATED=false
```

## 4. Start two processes

Open two PowerShell terminals in `whatsapp-adapter`. In **each** set:

```powershell
$env:TRUTHLENS_ENV_FILE = '.env.twilio'
```

First terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn truthlens_whatsapp.main:app --host 127.0.0.1 --port 8100 --no-access-log --no-proxy-headers
```

Second terminal:

```powershell
.\.venv\Scripts\python.exe -m truthlens_whatsapp.worker
```

`http://127.0.0.1:8100/health` should report `messaging_provider: twilio`, `response_mode: development` and both outbound flags false. Health is configuration information, not delivery proof. Use a single Sandbox worker; multi-worker Sandbox pacing is not implemented. The Meta endpoint is disabled on a Twilio instance, and vice versa. The database binds to its transport and refuses cross-provider reuse.

## 5. Set Twilio's inbound webhook manually

In Twilio **Sandbox settings**:

* **When a message comes in:** `https://<your-ngrok-host>/webhook/twilio/whatsapp`
* **Method:** `POST`

Save only after owner approval for account configuration. The adapter sets a per-message status callback automatically on outgoing API requests; no generic Sandbox status URL is required. Do not paste the Meta `/webhook/whatsapp` endpoint into Twilio. Do not expose Person 1's backend. Leave Twilio's signature and TLS verification enabled. The configured `TWILIO_PUBLIC_BASE_URL` must match the exact tunnel origin; proxy headers/Host headers are not trusted for signatures. Update the private setting and Twilio webhook together if ngrok's hostname changes, then restart both processes.

## 6. One controlled messaging acceptance test

Before sending, obtain explicit approval for the public tunnel/account setup and **one live development round trip**, covering Twilio trial usage but **zero Gemini/Tavily calls**. With approval, privately edit `.env.twilio` to set `TWILIO_OUTBOUND_ENABLED=true`, restart both processes, and send `Hi` from the joined phone to the Sandbox number.

Expected actual reply:

> TruthLens DEVELOPMENT TEST: your message was received. Fact-checking is not enabled for this test. No verdict or evidence has been generated.

Check the physical phone and the signed `delivered`/`read` callback or Twilio logs. An HTTP 200 or API message SID alone does not prove delivery. Save only redacted evidence. A duplicate inbound MessageSid must produce no second job or reply. The worker first checks Twilio's canonical message resource to confirm account, sender, recipient, received state and original creation time; old/replayed events cannot reset the 24-hour reply window.

Failure guide: 403 means signature/account/origin mismatch; 400 means invalid form/target; 503 means queue capacity. The worker's safe error codes exclude token/phone/raw message content. Twilio API 401 may indicate wrong credentials; 63015 may mean the phone has not joined/rejoined. Check Twilio logs privately for the exact error; never paste credentials. Ambiguous timeout/5xx sends are not retried. Definite 429 rejection has a bounded retry. To stop local processes, use Ctrl+C; set sending false afterward and restart to disable it. The OS/ngrok may retain independent logs; review their privacy/access controls.

## 7. Real fact-checking is a separate gate

After owner-confirmed provider credential rotation and explicit approval/budget for actual AI/search calls, configure the existing Person 1 backend and set `BACKEND_ENABLED=true`, `PROVIDER_CREDENTIALS_ROTATED=true`, `RESPONSE_MODE=backend`. The same exact verify/extract/explain API client is reused. No AI engine or model SDK is duplicated.

For local testing only, the owner may explicitly waive waiting for old-key revocation. Record that as `PROVIDER_KEY_REVOCATION_WAIVED=true`, leaving `PROVIDER_CREDENTIALS_ROTATED=false` while revocation is unconfirmed. This waiver is separate from `BACKEND_ENABLED` consumption approval, does not revoke any keys and cannot authorize production. On 2026-10-11 the owner explicitly authorized using new keys without waiting; the first bounded text check stopped after Gemini returned HTTP 503 (one Gemini attempt, zero Tavily searches). No real verdict or WhatsApp fact-check reply was generated. Messaging remains disabled pending successful backend acceptance and messaging approval.

Subsequent owner-approved checks established basic Gemini access, then one full backend text response, then one fresh WhatsApp text round trip. The round trip used two Gemini requests, one Tavily search and one Twilio reply attempt, reaching signed `read` status. The verdict stayed `unconfirmed`; it was not forced to `false`. The temporary worker and bounded backend test runtime exited afterward. Starting a normal continuous worker with sending enabled would consume additional credits and requires approval beyond that one-message test.

Local tests cover text, a standalone URL, PNG/JPEG, supported audio and PDF routing. Twilio media retrieval currently accepts only authenticated, account/message-scoped `api.twilio.com` resource URLs. It **refuses redirects** so credentials cannot leak to a CDN. If real Twilio media redirects, attachment checks are blocked pending review of the official storage host/authentication requirements; do not call media live-ready. Media count >1/unsupported formats produce a neutral format prompt. MIME, magic bytes and streaming size limits apply. Twilio replies are split conservatively to 1500 UTF-16 units while preserving complete source URLs. A URL exceeding a whole part is replaced with an explicit omission notice, preserving the title/publisher; full long-link delivery needs a reviewed public-report design. No automatic publication to a Channel occurs.

For future separately approved local acceptance, prefer the committed single-message `truthlens_whatsapp.controlled_test` tool over a continuous worker. It targets one fresh inbound SID, defaults to zero backend requests, enforces explicit per-invocation limits and refuses replay of completed/failed jobs. See [Person 2 local acceptance](person2-local-acceptance.md) for commands and limitations. Backend HTTP request limits do not cap provider calls inside P1; no new live test is authorized merely by having this tool.

Privacy: encrypted payload/report/outbox bodies expire within 24 hours plus cleanup interval; hashed sender preferences persist to honor STOP. Because Twilio form signatures have no timestamp, minimal content-free hashed MessageSid/job tombstones persist indefinitely to suppress captured-event replays. These keyed identifiers are pseudonymous, not anonymous. Never rotate encryption/identity keys casually. Hosted privacy/retention requirements must be reviewed before any production proposal. Twilio production mode is intentionally rejected in this test connector.

## 8. Offline verification

```powershell
New-Item -ItemType Directory .tmp -Force | Out-Null
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.tmp/pytest
.\.venv\Scripts\python.exe -m ruff check truthlens_whatsapp tests
.\.venv\Scripts\python.exe -m ruff format --check truthlens_whatsapp tests
.\.venv\Scripts\python.exe -m pip check
```

The Twilio tests use signed fictional forms, a temporary encrypted SQLite queue and mocked HTTP. They do not contact the user's account, send actual messages or invoke AI/search. Existing Meta tests must remain green.
