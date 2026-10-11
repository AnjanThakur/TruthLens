# TruthLens collaborator handoff — 2026-10-11

Repository: https://github.com/AnjanThakur/TruthLens

**Combined integration update:** Person 2 was saved as local commit `c88900c`, then combined with scam-alert commit `50350b4` on `integration/person2-scam-intelligence` without conflicts. At the owner's request, the existing `feature/scam-alert-intelligence` was then fast-forwarded to contain both features and is now the delivery branch. Main remains unchanged. See [combined integration](combined-integration.md) for tests, setup and remaining alert UI/chat work. Older Person 2-specific branch references below are historical; use the existing scam branch for sharing both features.

Working branch: `feature/person2-whatsapp`. The shareable ZIP contains the current working files, including changes not yet committed; its `HANDOFF-MANIFEST.json` records the base commit and file hashes. Your friend can extract it without waiting for a push. Cloning from GitHub requires these latest changes to be committed and pushed first. Preserve the website, Person 1 backend and shared main history; work through feature branches and reviewed pull requests.

Primary requirements: `TruthLens_Person2_Codex_Package/TruthLens_PS_Aligned_Two_Developer_Plan.docx`. Later owner instructions make WhatsApp a required deliverable. Also read the root WhatsApp integration guide and Codex prompt. This file contains no credentials.

Latest update: [Person 2 local acceptance](person2-local-acceptance.md) records completed timeout/upload alignment, production proxy browser tests, controlled single-message testing, history route tests and CI preparation. These reduce the remaining implementation work but do not replace live/hosted acceptance.

## What works, and what is not finished

- Person 1 owns FastAPI extraction, search, verification and explanation. Person 2 owns the Next.js website, private history and independent WhatsApp integration service. Do not duplicate the AI engine. Coordinate before editing Person 1 backend source.
- Website server routes and the WhatsApp adapter target the same actual backend API contract. Live website UI acceptance has not yet been demonstrated.
- One fresh real Twilio Sandbox message passed through Person 1's backend; the reply reached a signature-validated `read` callback and the owner confirmed receipt on the phone.
- The actual verification was `partial` / `unconfirmed`, with three neutral evidence entries and `source_page_unavailable:url_fetch_error`. Delivery passed; complete evidence quality did not pass. Do not describe this as a fully accepted production fact-checking bot.
- That approved round trip used two Gemini requests, one Tavily search and one Twilio reply attempt. Its temporary worker and bounded backend runtime exited. Continuous paid processing is disabled in the saved adapter configuration.
- The existing Meta transport is preserved. The owner's Meta test WhatsApp Business Account remains restricted with error 131031; Twilio Sandbox testing does not remove that restriction. This is private WhatsApp chat, not a Channel.
- Latest Person 2 checks: 92 adapter tests, 40 website tests (including isolated RLS), 22 existing browser/accessibility checks and six production-proxy browser checks passed, plus lint/format/build. These use mocked services. Backend's earlier checks remain 190 passed, three failed, two skipped; no backend source was edited or paid test rerun in this pass.

## Remaining work, in priority order

### 1. Person 1 — reliable evidence and backend acceptance

1. Diagnose source-download failures. Distinguish upstream HTTP rejection, network/TLS and timeouts without logging credentials or submitted private content. `url_fetch_error` currently does not identify the precise cause. Preserve SSRF protection, IP checks and safe redirect handling.
2. Improve directly relevant, current evidence retrieval and assessment. Resolve relative dates such as “next Monday”; preserve dates, amounts and qualifiers in atomic claims. Check source relevance, fetch availability and contradictory evidence. Keep snippet-only evidence clearly limited. Never force false/verified when evidence is insufficient.
3. Validate multi-claim reports and all six verdict values using controlled fixtures. Verify that translated explanations preserve verdicts, evidence links, dates and uncertainty.
4. Install/verify native extraction dependencies on the actual deployment machine: Tesseract with English, Hindi and Marathi language data; FFmpeg and FFprobe for audio. This laptop currently has only `eng`/`osd` Tesseract data and no FFmpeg/FFprobe. Test screenshots, scanned/text PDFs, supported voice notes and public URLs.
5. Resolve the three backend test failures: one OpenAPI snapshot differs in HTTP description wording (413/422), and two Hindi/Marathi OCR checks fail. Investigate dependencies/native capabilities rather than weakening factual or security checks. API field names, endpoints and verdict values must not change silently.
6. Agree request timeouts, concurrency, retry and model/search budgets with Person 2. Keep live provider tests explicitly approved and bounded.

### 2. Person 2 — website and WhatsApp integration acceptance

1. Configure the website against the actual running backend with both mock flags false. Demonstrate text, image, audio, PDF and URL through the UI. Timeout/upload alignment and full proxy tests now pass offline: proxy default 195 seconds, browser 330 seconds, shared upload cap. Real extraction/provider acceptance remains pending.
2. Recheck responsive/accessibility behavior, English/Hindi/Marathi explanations and browser speech where supported. Run the existing frontend checks and demonstrate a live UI result; mocks alone do not prove live integration.
3. Test real WhatsApp attachments and languages after approving a small test budget. Twilio media retrieval currently refuses redirects and accepts account/message-scoped authenticated API resource URLs. Real CDN redirects remain an acceptance gap: review official host/authentication behavior before implementing any change, and never forward Twilio credentials to arbitrary hosts.
4. Verify text/URL, image, voice and PDF replies; concise verdict/explanation/source formatting; HELP, SOURCES, language changes, STOP/START; deduplication; expired reply windows; signed callbacks; error handling and pacing. Normal source URLs are now preserved across reply parts in offline tests; URLs longer than a whole part produce an explicit omission notice. A public full-report design remains a separate decision if those links must be delivered. Do not label untested media paths live-ready.
5. Use the new controlled single-message tool for separately approved acceptance; see `person2-local-acceptance.md`. Set an agreed usage budget before continuous processing. The normal worker has no global model/search spending cap, and controlled backend-request limits do not bound provider calls inside P1. Preserve stable encryption and identity keys; do not casually regenerate them or copy real chat databases to GitHub.
6. Complete hosted private history: configure Supabase/email sign-in and callback, apply both SQL migrations, verify opt-in save/deletion, two real users' isolation, expiry and scheduled cleanup. Configure the hourly retention job described in the setup docs. WhatsApp messages must not silently become website history.

### 3. Shared — deployment and final demonstration

1. Prepare hosting for the website, private backend, adapter web process and separate worker. Provide durable encrypted state, HTTPS callbacks, request/upload limits, monitoring, restart behavior, backup/restore and retention cleanup. A laptop/ngrok session is temporary testing, not deployment.
2. The backend currently has no built-in bearer-token authentication. Use a coordinated authenticated gateway/private network before exposing it; merely setting a client token does not secure the backend.
3. Twilio integration is deliberately Sandbox/test-only; its production mode is rejected. A supported production sender/transport and account eligibility need separate work and approval. Meta account restriction must be addressed with Meta if choosing direct Cloud API. Do not buy senders, upgrade accounts, submit verification or publish without the owner's approval.
4. Demonstrate the website and WhatsApp using the same backend. Include multi-claim, uncertainty/conflicts and languages; show at least three real modalities and finish the remaining modality checks. Record actual delivery and evidence quality separately.
5. Confirm provider credential revocation/replacement before production. The owner waived waiting for old-key revocation for local tests only; revocation remains unconfirmed. Do not claim it has happened.

Deferred supplementary features: tracker/radar, clustering, truth cards/public sharing and other optional differentiators. Finish the approved core requirements first.

## APIs your friend must use

Backend local base: `http://127.0.0.1:8000`.

| Method and path | Request / purpose |
| --- | --- |
| `GET /api/health` | Local service/capability health; not proof of provider authentication or quota |
| `POST /api/verify` | JSON claim input; returns the actual VerificationResult |
| `POST /api/extract` | Multipart upload with field name **file**; image, audio or PDF |
| `POST /api/extract/url` | JSON `{"url":"https://public-article"}` |
| `POST /api/explain` | JSON containing full **result**, **language**, **audience**; grounded explanation |
| `GET /docs` and `GET /openapi.json` | Running backend documentation and schema |

Example verification request (fictional input, no promised verdict):

```json
{"text":"A factual claim to check.","input_type":"text","input_language":"auto","response_language":"en","audience":"adult","jurisdiction":"IN"}
```

Verdicts: `verified`, `false`, `partially_true`, `outdated`, `misleading_context`, `unconfirmed`. Result statuses: `completed`, `partial`, `no_checkable_claims`. Coordinate changes explicitly. The authoritative integration references are [backend contract](backend-api-contract.md), [OpenAPI snapshot](backend-openapi.json), and [reconciliation](person2-contract-reconciliation.md). The older `api-contract.md` is superseded provisional material.

Adapter local base: `http://127.0.0.1:8100`; health: `GET /health`.

- Twilio inbound callback: `POST https://YOUR-CURRENT-TUNNEL-HOST/webhook/twilio/whatsapp`.
- Signed per-message status callback: `/webhook/twilio/status/{outbox_id}`, set automatically by the adapter. No generic Sandbox status callback is required.
- Alternative Meta instance uses `GET/POST /webhook/whatsapp`. Do not configure that path for Twilio.
- Website `/api/history` routes are Person 2's authenticated website routes, not Person 1's FastAPI endpoints.

## Private configuration and account access

Use your friend's own credentials/projects where possible, or a deliberate collaborator invitation/secure private transfer. Never commit `.env` files, Notepad secrets, account screenshots, ngrok tokens, virtual environments or real message databases.

| Service | Where to configure | Values/access needed |
| --- | --- | --- |
| Gemini + Tavily | `backend/.env`, using `backend/.env.example` names | Gemini API key, Tavily API key, approved usage budget |
| Website backend | `frontend/.env.local` | `BACKEND_BASE_URL`, timeout/upload limits; `BACKEND_API_TOKEN` only if a real authenticated gateway is added |
| Website history | `frontend/.env.local` + Supabase dashboard | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, server-only `HISTORY_SIGNING_SECRET` (at least 32 characters), `APP_ORIGIN`, SQL/email/callback configuration; no service-role key needed |
| Twilio Sandbox | `whatsapp-adapter/.env.twilio`, created by wizard | Account SID starting `AC`, primary Auth Token, exact Sandbox sender, account-specific join code, approved console access |
| Adapter/backend | Same private adapter file | `TRUTHLENS_BACKEND_URL`, optional coordinated gateway token, generated `STATE_ENCRYPTION_KEY` and `IDENTITY_HASH_SECRET`, durable private database path |
| ngrok | Friend's own ngrok configuration | Own ngrok authtoken, current HTTPS origin; match `TWILIO_PUBLIC_BASE_URL` and the Twilio inbound callback |
| Production | Approved hosting secret store/accounts | Coordinated deployment access, domains, transport eligibility and separately approved release/budget |

Provider credentials belong only on the backend, never in `NEXT_PUBLIC_*` variables or the adapter's source. Supabase's publishable key is intentionally public; provider secrets and history signing/encryption keys are not.

Your friend's `localhost` is their computer. The owner's current tunnel points to the owner's laptop and must not be reused as if it hosted your friend's server. Each new tunnel origin must be updated in both the private adapter configuration and Twilio console, then the server/worker restarted.

## Fresh setup for your friend (PowerShell)

Use Python 3.12 (tested) and Node.js 22.12+ within 22.x, or Node.js 24. Clone after the owner pushes:

```powershell
git clone --branch feature/person2-whatsapp https://github.com/AnjanThakur/TruthLens.git
cd TruthLens
```

Backend, first setup only (do not overwrite existing private env files):

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
Copy-Item .env.example .env
```

Enter credentials privately in `.env`, install native extraction dependencies, then start in this terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Website, separate terminal from repository root:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
```

Set `BACKEND_BASE_URL=http://127.0.0.1:8000`, `USE_MOCK_API=false` and `NEXT_PUBLIC_USE_MOCK_API=false`. Run `npm run dev`, then open `http://localhost:3000`. Configure Supabase separately using [Person 2 setup](person2-setup.md); callback is the exact website origin plus `/auth/callback`.

Adapter, separate terminal from repository root:

```powershell
cd whatsapp-adapter
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-twilio-lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
```

After approval for account/tunnel testing, configure your own ngrok, run `ngrok http 8100` in a separate terminal and run the private wizard:

```powershell
.\.venv\Scripts\python.exe -m truthlens_whatsapp.configure_twilio
$env:TRUTHLENS_ENV_FILE = '.env.twilio'
.\.venv\Scripts\python.exe -m uvicorn truthlens_whatsapp.main:app --host 127.0.0.1 --port 8100 --no-access-log --no-proxy-headers
```

The wizard disables sends and AI by default. Join the Sandbox from the test phone and configure its incoming webhook to your current tunnel's Twilio path, method POST. Read [Twilio setup](twilio-sandbox-setup.md) before enabling anything.

For approved real fact-check testing only: privately set `RESPONSE_MODE=backend`, `BACKEND_ENABLED=true`, `TWILIO_OUTBOUND_ENABLED=true`, and the correct backend origin. Set `PROVIDER_CREDENTIALS_ROTATED=true` only when actually confirmed. An explicit owner waiver for local testing can instead use `PROVIDER_KEY_REVOCATION_WAIVED=true` with rotation false; it does not authorize production. Restart the web process after changes.

In another adapter terminal, only once a continuous-use budget is approved:

```powershell
$env:TRUTHLENS_ENV_FILE = '.env.twilio'
.\.venv\Scripts\python.exe -m truthlens_whatsapp.worker
```

That normal worker is continuous, not the previous one-message bounded test helper. Do not start it with paid flags enabled on the assumption that the old one-test approval covers unlimited new requests. Stop with Ctrl+C and disable outbound/backend flags when finished. No temporary helper or real database is required in the Git handoff.

## What the owner should send

Send the generated `dist/handoff/TruthLens-Friend-Handoff.zip` as one file. It contains the latest code, `START-HERE.md`, `FRIEND-MESSAGE.txt`, all documents listed above, configuration templates, API schemas, fixtures, tests and SQL migrations. No manual copying of code or API documentation is needed. Rebuild it with `py -3.12 scripts/build_handoff.py` after further changes. The archive intentionally excludes Git history, private configuration, chat databases, account screenshots, dependencies and generated artifacts.

`FRIEND-MESSAGE.txt` is ready-to-copy context for the friend. Live access cannot be provisioned by an archive: your friend must use their own keys/projects or receive an authorized account invitation/private secret transfer. Offline work requires no provider or Twilio keys. If also sharing GitHub access, push first and send the resulting commit hash; do not identify the archive's base commit as the final pushed state.

## Safe publishing from the owner's current checkout

Four root `.tmp` account screenshots are already staged. The new ignore rule does not remove already staged files. Unstage them while retaining the local copies, then stage the project changes:

```powershell
cd "C:\Users\Gaurav Choithramani\Desktop\hackOnTrack"
git switch feature/scam-alert-intelligence
git restore --staged -- .tmp
git add .
git status --short
git diff --cached --stat
```

Review the staged list: no `.env`, `.tmp`, Notepad secrets, screenshots of credentials or message databases. Do not paste a full sensitive diff into chat. Then:

```powershell
git commit -m "Add Twilio WhatsApp integration and project handoff"
git push -u origin feature/scam-alert-intelligence
git rev-parse --short HEAD
```

Share that commit hash and branch. Do not force-push or overwrite main. If GitHub denies access, ask the repository owner to grant contributor permission or use an authorized fork; do not change shared history. Open a pull request for review when ready.
