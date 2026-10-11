# TruthLens — start here, collaborator

This package contains the current website, Person 1 FastAPI backend and independent WhatsApp adapter. Start with this file, then [the completion handoff](docs/current-integration-handoff.md). You do not need the owner's laptop, Notepad files or private API keys to review the code and run the mocked tests.

## Current status and ownership

- Person 1: extraction, claims, search, evidence assessment, verification and grounded explanation. Start with the numbered Person 1 tasks in the completion handoff. Preserve existing contracts; coordinate any field/verdict changes.
- Person 2: website, private history, WhatsApp transport, account setup and deployment integration. Keep both clients calling the same backend. Do not create another verification engine.
- One real Twilio Sandbox text reply was received and read. Its report was **partial/unconfirmed**, with incomplete source retrieval. Delivery succeeded; evidence quality and production acceptance remain unfinished.
- Latest offline checks passed: 40 website tests, 22 browser/accessibility checks, six production-proxy browser checks and 92 adapter tests, plus build/lint/format. Earlier backend results were 190 passed, three failed and two skipped; see the handoff for those failures.
- Still pending: reliable live evidence/extraction, real attachments/languages, live website acceptance, hosted Supabase history and production deployment/transport. Meta's test account is restricted. Twilio Sandbox is a test chatbot in private chat, not a WhatsApp Channel.

Primary requirements: [original two-developer plan](TruthLens_Person2_Codex_Package/TruthLens_PS_Aligned_Two_Developer_Plan.docx). Read the root WhatsApp guide/prompt as well; later owner instructions make WhatsApp required.

## What is included

| Folder/file | Purpose |
| --- | --- |
| `backend/` | Actual Person 1 FastAPI implementation, tests, scripts and environment template |
| `frontend/` | Next.js website, API proxies, private history, unit/browser/integration tests and locked npm dependencies |
| `whatsapp-adapter/` | Separate Meta/Twilio service, durable queue/worker, signatures, deduplication, encrypted state, tests and dependency locks |
| `supabase/migrations/` | Private report ownership/RLS and retention migrations |
| `docs/` | Remaining tasks, API contract/OpenAPI, setup, deployment preparation and gate evidence |
| `TruthLens_Person2_Codex_Package/` | Original requirements and synthetic fixtures |
| `.github/workflows/person2-offline.yml` | Prepared offline CI checks; hosted execution still needs confirmation |
| `HANDOFF-MANIFEST.json` | ZIP snapshot metadata and SHA-256 hashes; base commit is not a claim that all included work was pushed |

Dependencies, caches, test screenshots, private `.env` files, actual chat state and Git history are excluded. Install dependencies on your machine. Do not copy this ZIP over an existing checkout with private files; extract into a new folder. If you already collaborate through Git, use the pushed feature branch instead and compare changes before applying anything.

## Run without keys first

Use Python 3.12 and Node.js 24 (or supported Node 22.12+). From the extracted `TruthLens` folder, PowerShell:

```powershell
cd frontend
npm ci
npm run dev:mock
```

Open `http://localhost:3000`. This is a **synthetic UI demonstration**, not a real fact-check. Stop with Ctrl+C before browser testing. After dependency installation, website unit and complete browser/proxy checks are listed in [local acceptance](docs/person2-local-acceptance.md). For browsers, install Chromium first and select it if Microsoft Edge is not installed:

```powershell
npx playwright install chromium
$env:PLAYWRIGHT_CHANNEL = 'chromium'
npm test
npm run test:e2e
npm run build
npm run test:integration
```

Run build after the first browser suite; do not run browser suites concurrently. The production-proxy suite starts a loopback fake backend itself and uses no provider keys. It does not test real AI, OCR or source quality.

For adapter tests, in another terminal from the extracted root:

```powershell
cd whatsapp-adapter
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-twilio-lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m pip install 'pytest==9.1.1' 'pytest-asyncio==1.4.0' 'ruff==0.17.0'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

These adapter tests mock external services. Do not run backend live/preflight/source scripts or enable a live worker just to check installation: those can consume credits. Backend setup and native extraction requirements are in `backend/README.md` and the completion handoff; backend tests are separate from the passing Person 2 tests.

## API information — already included

Backend local base: `http://127.0.0.1:8000`. Exact schemas: [backend-openapi.json](docs/backend-openapi.json). Human-readable contract: [backend-api-contract.md](docs/backend-api-contract.md). Actual example result: [Person 1 response fixture](frontend/tests/fixtures/person1-response.json). Reconciliation: [person2-contract-reconciliation.md](docs/person2-contract-reconciliation.md). The older `api-contract.md` is provisional and superseded.

| Request | Purpose / body |
| --- | --- |
| `GET /api/health` | Capabilities; not proof of provider credentials/quota |
| `POST /api/verify` | JSON text, input type/language, response language, audience and jurisdiction |
| `POST /api/extract` | Multipart **file**, for image/audio/PDF |
| `POST /api/extract/url` | JSON `url`, for a public article |
| `POST /api/explain` | Full **result**, **language**, **audience**; preserve factual verdict/evidence |
| `GET /docs`, `GET /openapi.json` | Running FastAPI docs/schema |

Verification example:

```json
{"text":"A factual claim to check.","input_type":"text","input_language":"auto","response_language":"en","audience":"adult","jurisdiction":"IN"}
```

Verdicts: `verified`, `false`, `partially_true`, `outdated`, `misleading_context`, `unconfirmed`. Statuses: `completed`, `partial`, `no_checkable_claims`. Do not silently rename them.

Adapter base: `http://127.0.0.1:8100`; `GET /health`. Twilio inbound: `POST https://YOUR-TUNNEL/webhook/twilio/whatsapp`. Signed per-message status callbacks are generated by the adapter. Alternative Meta webhook: `GET/POST /webhook/whatsapp`. These are different transport paths. See [Twilio setup](docs/twilio-sandbox-setup.md).

## Credentials and access for live work

No real credentials are included. Use your own projects or an authorized collaborator invitation and private secret transfer. The following is the complete configuration inventory; you do not need to ask the owner to manually assemble API files.

| Need | Configuration location / how to obtain it |
| --- | --- |
| Gemini API key and Tavily API key | Copy `backend/.env.example` to `backend/.env`, fill `GEMINI_API_KEY` and `TAVILY_API_KEY` privately; choose an accessible model and approved budget with Person 1 |
| Website backend address | Copy `frontend/.env.example` to `frontend/.env.local`; set `BACKEND_BASE_URL`, both mock flags false for actual backend use; configured default deadline 195 seconds and cap 10 MiB |
| Twilio Account SID, primary Auth Token, Sandbox sender and join code | Your Twilio console/account, not ngrok credentials. Run `truthlens_whatsapp.configure_twilio` after adapter install; it securely prompts and generates `.env.twilio`, encryption/identity keys and a separate database path with sends/AI disabled |
| Adapter backend address | Private `.env.twilio`: `TRUTHLENS_BACKEND_URL=http://127.0.0.1:8000`; see setup docs for approved response/enable flags |
| ngrok authtoken and HTTPS origin | Your ngrok account/config; tunnel port 8100. Put your current origin in `TWILIO_PUBLIC_BASE_URL` and its full inbound path in Twilio. The owner's old tunnel points to the owner's laptop |
| Optional Supabase history | Your project URL and publishable key in website env, plus a new server-only `HISTORY_SIGNING_SECRET` of at least 32 characters and exact `APP_ORIGIN`. Apply both included migrations and configure email/auth callbacks/retention. No service-role key is needed |
| Backend gateway credentials, if deployed | Coordinate an actual private network/authenticated gateway. Setting `BACKEND_API_TOKEN` / `TRUTHLENS_BACKEND_TOKEN` alone does not add authentication to FastAPI |
| Direct Meta, only if chosen later | Your eligible Meta business/app/WABA/phone IDs, app secret, verification token and access token; see `docs/meta-setup.md`. The current restriction is unresolved; these are not needed for offline or Twilio Sandbox tests |
| Production release | Hosting/domain access, durable encrypted state, supported sender/transport and explicit owner release approval |

Only copy templates on first setup; never overwrite existing private files. Never put Gemini/Tavily keys in frontend public variables. Keep stable adapter encryption/identity keys. Do not send the owner your `.env` or real message database as a code change.

Before consuming credits, sending live WhatsApp messages, changing accounts or publishing, agree scope/budget and obtain the owner's approval. The controlled single-message tool is documented in local acceptance. It caps backend HTTP requests, **not Gemini/Tavily calls nested inside the backend**. Do not start continuous paid processing under an old one-message approval. Old-key revocation remains unconfirmed; any earlier local waiver does not authorize production.

## Working together

Repository: https://github.com/AnjanThakur/TruthLens — branch `feature/person2-whatsapp`. The ZIP has no `.git` history and includes current uncommitted work. Do not initialize it and replace shared `main`; coordinate with the owner to push the feature branch, then clone that branch for normal collaboration. Instructions for the owner are in the completion handoff.

Send back a feature branch/PR, the tests you actually ran, and separate results for delivery, evidence quality and modality coverage. Keep API names stable and record any coordinated changes. Do not call an incomplete evidence result verified or false merely to make the demo look complete.
