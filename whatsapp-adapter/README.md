# TruthLens WhatsApp adapter

Person 2's isolated Meta Cloud API transport. Person 1's FastAPI remains the only extractor and verifier. The existing Next.js website remains independently usable. No backend code is changed.

**Current status: implemented and tested offline; actual Meta delivery and live backend fact-checking are not yet demonstrated.** Account actions, real WhatsApp sends, provider credits and production publication require the owner's approval. All automated tests use mocked HTTP. Do not interpret a mocked verdict as a factual finding.

An additional **Twilio Sandbox test connector** is available while the owner's Meta test WABA is restricted. It preserves this Meta adapter and reuses the same queue and Person 1 API client. See [Twilio setup](../docs/twilio-sandbox-setup.md) for the separate private configuration, signatures, trial limits and explicit live-test gates. It is not a Channel integration; real Twilio delivery is not yet demonstrated. Install optional `.[twilio]` dependencies when using it.

## Install and run offline

From this repository (PowerShell):

```powershell
Set-Location 'C:\Users\Gaurav Choithramani\Desktop\hackOnTrack\whatsapp-adapter'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev,qr]'
New-Item -ItemType Directory .tmp -Force | Out-Null
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.tmp/pytest
.\.venv\Scripts\python.exe -m ruff check truthlens_whatsapp tests
.\.venv\Scripts\python.exe -m ruff format --check truthlens_whatsapp tests
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m truthlens_whatsapp.offline_demo
```

The demo signs a local webhook, submits it twice, processes one durable job and intercepts the outgoing Graph request in memory. It prints the development response. It never sends a WhatsApp message or contacts Gemini/Tavily. Its invented IDs and token cannot be used with Meta. The test suite blocks the real HTTP transport.

The Python environment in this workspace uses the bundled Python 3.12 runtime because the system Python's virtualenv creation failed. A fresh installation can use Python 3.11+. `requirements-lock.txt` records the tested full dependency set; `requirements-runtime-lock.txt` pins the container runtime; the project manifest pins direct dependencies. Optional QR generation uses qrcode 8.2.

## Configuration

Copy `.env.example` to `.env` only when it does not already exist. Edit secrets privately. Do not print `.env` or paste tokens into chat. Generate the state key with `cryptography.fernet.Fernet.generate_key()` and an independent random hashing secret/verify token with `secrets.token_urlsafe(32)`; save directly into the private file or secret manager. `STATE_ENCRYPTION_KEY` and `IDENTITY_HASH_SECRET` must stay stable across webhook/worker restarts and replicas. Losing either breaks recovery; changing the identity key loses deduplication. Back up/rotate keys through an explicit maintenance procedure.

| Setting | Purpose |
|---|---|
| `WHATSAPP_ACCESS_TOKEN` | Temporary Meta test token; later an authorized system-user token |
| `WHATSAPP_PHONE_NUMBER_ID` | Intended receiving/sending Phone Number ID, not the displayed number |
| `WHATSAPP_WABA_ID` | Intended WhatsApp Business Account ID |
| `WHATSAPP_VERIFY_TOKEN` | Locally generated token matching Meta's webhook configuration |
| `META_APP_SECRET` | Meta app secret used for raw-body HMAC verification |
| `GRAPH_API_VERSION` | Version confirmed in current Meta documentation/dashboard; no guessed production default |
| `TRUTHLENS_BACKEND_URL` | Fixed internal origin, default `http://127.0.0.1:8000` |
| `TRUTHLENS_BACKEND_TOKEN` | Optional bearer token for an authenticated gateway; P1 currently implements no bearer authentication |
| `DATABASE_URL` | Local SQLite or hosted `postgresql://...` with appropriate TLS parameters |
| `STATE_ENCRYPTION_KEY` | Fernet encryption of submitted content, reports and reply bodies |
| `IDENTITY_HASH_SECRET` | HMAC key for sender/message identifiers |
| `SUPPORT_URL` | Actual support webpage; required HTTPS in production |
| `META_OUTBOUND_ENABLED` | Defaults false; enable only after owner approves real sends |
| `BACKEND_ENABLED` | Defaults false; enable only after owner approves provider consumption |
| `PROVIDER_CREDENTIALS_ROTATED` | Defaults false; owner must confirm rotation before real backend access |
| `RESPONSE_MODE` | `development` by default; `backend` requires both backend gates |

Never set Meta/provider secrets as `NEXT_PUBLIC_*`. `BOT_ENV=test` does not make arbitrary real Graph calls safe: the outbound flag is a deliberate gate, not account approval enforcement. Only the owner may authorize enabling it with real credentials.

## Meta account steps and shortest live test

These steps are **prepared, not performed**. Obtain approval before using the owner's account, sending a live test or publishing anything.

1. Register at Meta Developers; select an authorized Business Portfolio. Create/select an app with the WhatsApp use case and provision its test WABA/test number through the current wizard. Use truthful ownership details.
2. Record App ID (handoff inventory), WABA ID, Phone Number ID and the displayed test number. Securely provision the temporary access token, App Secret and a unique verify token. Confirm the Graph version.
3. Add and verify the owner's WhatsApp number as a permitted test recipient. Token permissions must cover `whatsapp_business_messaging` and the required `whatsapp_business_management` operations. `business_management` is conditional on business-management operations, not universally required.
4. Keep `RESPONSE_MODE=development`, `BACKEND_ENABLED=false` and `PROVIDER_CREDENTIALS_ROTATED=false`. After specific approval for live sending, enable `META_OUTBOUND_ENABLED=true` and supply real Meta credentials. No provider keys are needed for this first messaging test.
5. Start the two adapter processes in separate PowerShell terminals:

```powershell
# Both terminals start in whatsapp-adapter with the same .env and database.
.\.venv\Scripts\python.exe -m uvicorn truthlens_whatsapp.main:app --host 127.0.0.1 --port 8100 --no-access-log
.\.venv\Scripts\python.exe -m truthlens_whatsapp.worker
```

6. After account/tunnel approval, expose only port 8100 through an HTTPS tunnel such as `ngrok http 8100`. Never expose an unauthenticated P1 backend. Register `https://<host>/webhook/whatsapp` and the private verify token. Confirm challenge verification, enable `messages`, and confirm the app's subscription to the correct WABA. Disable query-string access logging at the proxy too; verification tokens arrive in a GET query.
7. With approval to send, use the official dashboard-provided test template/message to your verified recipient. This establishes initial test messaging. Then send a user-initiated message from your approved phone to Meta's test number.
8. Confirm the incoming signed event produces one job and one development reply. Check the actual phone and signed delivery status. An HTTP success or Meta message ID alone is not delivery proof.
9. Record the result without phone numbers, tokens or raw private messages. Tunnel hostname changes require updating the registered callback.

The development reply explicitly says no verdict/evidence was generated. No fabricated fact-check substitutes for a missing backend.

## Enable real verification separately

Person 1's code exists here, but its former local runtime paths in their README refer to another checkout. Install/run their service according to their instructions without editing it. Confirm `/api/health` using only local capability information; it does not establish key validity. The adapter uses these exact APIs:

| Content/action | Backend request |
|---|---|
| Text | `POST /api/verify` with `text,input_type,input_language,response_language,audience,jurisdiction` |
| Image/audio/PDF | `POST /api/extract`, multipart `file`; submit actual extracted text to verify |
| One URL | `POST /api/extract/url`, JSON `{url}`; submit actual extracted text to verify |
| Re-explanation | `POST /api/explain`, `{result,language,audience}`; validate unchanged factual fields |

Exact backend OpenAPI is copied into the installed package and tested against `docs/backend-openapi.json`. Changes require explicit contract review, not silent field renaming. No extractor, model SDK, search client or classification logic is duplicated here.

Before enabling backend mode, the owner must rotate previously exposed Gemini/Tavily keys in the providers' consoles, revoke old keys, privately configure replacement keys on Person 1's service, and confirm completion without sharing values. Rotation has **not** been verified by this adapter. Obtain explicit approval for the bounded live provider test, then set `BACKEND_ENABLED=true`, `PROVIDER_CREDENTIALS_ROTATED=true`, `RESPONSE_MODE=backend`. Both clients use fixed origins, timeouts and no automatic provider retry. Each backend verification may itself consume multiple paid calls: this flag is not a spending budget. Coordinate a narrow backend/provider budget before running.

Start with one short English text check and compare its actual sources/result to the website or Swagger. Additional live text/media/language tests require separate approval. Gemini/Tavily failures are real failures, never canned `unconfirmed` results. Partial results retain warnings and limitations.

## Formats and coverage

Supported binary inputs match P1: PNG/JPEG, PDF, WAV/MP3 and OGG/Opus. Cloud API media availability and supported encodings still constrain inputs; AAC/M4A/video/other documents receive a clear unsupported-format response. Media lookup and download use bearer authentication, a fixed Graph origin and the expected Meta download host `lookaside.fbsbx.com`; redirects to other hosts are rejected. New official hosts require reviewed configuration/code updates. Downloads enforce MIME, magic bytes, checksum when supplied, streaming size limits and timeouts. Downloaded content exists only in bounded process memory and encrypted job/report storage, never in public files.

The 10 MiB adapter ceiling matches the current backend default; configure a smaller value if needed. Larger platform uploads do not imply backend support. Metadata lookup failures, URL expiry and transient download errors produce a safe error; a later user submission performs a fresh lookup. No automatic verification retry spends additional credits.

Send one URL alone. Mixed URL/prose submissions request clarification instead of choosing a target. Arbitrary user URLs are fetched only by P1's SSRF-protected extractor. Long PDF previews are refused as whole-document checks: split the file or use website page-chunk review. Short/scanned PDFs use P1's actual extraction; unreadability and incomplete coverage remain visible. Audio 503/timeout never becomes a fabricated transcript.

## Replies, privacy and operational limits

Claim-specific verdicts preserve all six exact backend values. Replies show real returned citations, check timestamps and limitations. First replies show up to three sources per claim, with `SOURCES` for all evidence. English/Hindi/Marathi use backend wording; stable claim/evidence IDs and all factual fields are checked on re-explanation. Framing/help text currently uses English; verdict labels are localized. Native-speaker review remains a release task.

`HELP`, `HINDI`, `MARATHI`, `ENGLISH`, `SOURCES`, `STOP`, `START` are supported. STOP is recorded as soon as the signed event is durably admitted, suppresses pending replies, and persists across restarts. It cannot retract an already in-flight send. START explicitly re-enables requested checks. No campaigns, templates or unsolicited follow-up scheduler are implemented. Free-form replies older than 24 hours are suppressed; a new user message is required. Production would require approved templates for any out-of-window messaging.

Submitted payloads, reports and outbox text expire after at most 24 hours plus the worker's one-minute purge interval. Sender/message identifiers use keyed hashes. Dedup tombstones persist eight days by default, covering the accepted seven-day inbound age; expired events are ignored. Opt-out hashes remain to honor STOP; preferences are minimal and do not contain raw phone numbers. No WhatsApp history is inserted into Supabase. User-initiated checking and opt-in saved website history are separate choices.

SQLite is for local/single-machine use with restrictive filesystem permissions. PostgreSQL supports transactional queue admission, per-sender serialized processing and row claiming. An interrupted worker does not repeat a potentially paid call. Ambiguous sends are marked uncertain and never blindly retried; a signed status event with the opaque callback ID can reconcile them. Only definite rate-limit rejection is retried, at most three attempts, respecting Retry-After. Exactly-once external delivery cannot be guaranteed by the Cloud API after a lost response.

## Website and QR

The website consumes the same P1 APIs and preserves its existing interface/history. `WHATSAPP_LINK_ENABLED=false` keeps click-to-chat hidden. Only after a real number and delivery are verified, set that flag and `WHATSAPP_PUBLIC_NUMBER` (country code, digits only) in `frontend/.env.local`. Test recipients still need Meta approval when using a test number; do not advertise it as a public bot.

After verifying an actual public number, generate a QR locally with the optional dependency:

```powershell
.\.venv\Scripts\python.exe -m truthlens_whatsapp.make_qr --number '<VERIFIED_PUBLIC_NUMBER>' --number-verified --output state/whatsapp-qr.svg
```

This creates no account, sends no message and publishes nothing. Do not generate a QR for an invented or unauthorized number. Review the scanned destination before sharing.

## Deployment and acceptance

See `../docs/whatsapp-deployment.md` and `../docs/whatsapp-gates.md`. Required live proof is distinct from offline completion: actual signed receipt, delivered development reply, then separately an actual P1-backed sourced reply. Each media flow needs its own live record or an honest blocker. Production additionally requires hosted database/worker acceptance and current Meta eligibility/configuration. The two approval gates are independent: Meta sending approval does not authorize paid provider use.

Official references checked during planning: [Meta-maintained collection](https://www.postman.com/meta/whatsapp-business-platform/collection/wlk6lh4/whatsapp-cloud-api), [messaging policy](https://whatsappbusiness.com/policy/), [platform terms](https://www.whatsapp.com/legal/WhatsApp-Terms-for-WhatsApp-Business-Platform). Direct developer documentation was rate-limited. AI-specific eligibility remains unresolved; obtain current Meta confirmation before public launch. Successful sandbox messaging does not establish permission for public deployment.
