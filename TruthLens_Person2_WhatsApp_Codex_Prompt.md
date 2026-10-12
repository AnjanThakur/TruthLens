# TruthLens AI — Person 2 WhatsApp Bot Implementation (Codex Prompt)

You are the Person 2 integration engineer for **TruthLens AI — Verify Before You Forward**.

## Workspace

Windows project root: `D:\HackOnTrack-TruthLens`.

**Goal:** Implement a real Meta WhatsApp Cloud API chatbot as a **core TruthLens deliverable** and connect it to Person 1's **existing** FastAPI fact-checking backend. Users should voluntarily forward **text, screenshots, voice notes, PDFs or URLs** to a TruthLens WhatsApp number and receive an accessible **claim-by-claim, source-linked fact-check**. Do not build a second AI verifier.

**Current backend context (reported by Person 1):** Gemini + Tavily verification and evidence ledger implemented; previously 195 tests passed offline; several input formats have passed prior live testing, while real audio suffered Gemini HTTP 503 / timeout. Provider failures must not be passed off as factual verdicts. Do not assume that passing unit tests proves real-world accuracy.

## Required discovery before coding

1. Inspect repository tree, `docs/backend-api-contract.md`, `backend/README.md`, backend OpenAPI (if available), and `backend/validation-report.md`. Determine the *actual* request schema and response fields for `POST /api/extract`, `POST /api/verify` and explanation functionality. Do not guess from this prompt.
2. Inspect Git status, branch, existing tracked changes and ownership before editing. Preserve Person 1 changes. Do not modify `backend/` or its public API without explicit coordination.
3. Check for an existing WhatsApp adapter or Meta config to avoid duplicate implementation.
4. Inspect relevant current Meta API documentation, local SDKs and project deployment configuration; use the Graph version configured in the Meta console rather than guessing a fixed version.
5. **Policy gate:** Meta's current WhatsApp Business Platform terms restrict some services whose primary offering is AI. Do not claim that public deployment of a standalone fact-checking AI bot is permitted merely because the test API works. Document the eligibility uncertainty, prioritize the official test environment and provide the existing web application as a fallback for public demos.

## Ownership boundary

**Person 2 owns:** Meta Developer/Business portfolio setup instructions, WABA/test-number configuration, WhatsApp connector, webhook, message routing, media download, formatting, frontend link/QR, HTTPS host, bot test harness and integration docs. Person 2 may add a standalone `whatsapp-adapter/` with its own configuration, tests and README.

**Person 1 owns:** Gemini/Tavily, OCR, PDF, URL, audio transcription, source ranking, claim extraction, verdicts and explanation logic. Do not reimplement these modules.

## Implementation phases

### Phase A — Isolated WhatsApp adapter

Create a clean, runnable service, preferably Python FastAPI, at:

```
whatsapp-adapter/
  app/main.py
  app/config.py
  app/meta_client.py
  app/truthlens_client.py
  app/message_handler.py
  app/formatter.py
  app/worker.py
  tests/
  .env.example
  requirements.txt (or pyproject.toml)
  README.md
```

Implementation details:

- `GET /webhook/whatsapp`: verify Meta `hub.mode`, `hub.verify_token` and return `hub.challenge` plain text, otherwise 403.
- `POST /webhook/whatsapp`: verify raw-body HMAC-SHA256 using `META_APP_SECRET` and the `X-Hub-Signature-256` header; use constant-time comparison; reject invalid payloads before processing.
- Parse `entry[].changes[].value.messages[]`; ignore status-only updates and unsupported event fields.
- Use WhatsApp `message.id` as durable deduplication key, with delivery state `received`, `processing`, `completed`, `failed` and guarded resends; avoid double AI calls and duplicate replies from Meta retries.
- Acknowledge webhook quickly after reliable enqueue; process potentially slow Gemini/Tavily requests outside the webhook request path. For local test, provide a light queue; document a durable worker solution for hosted deployment.
- Use strict timeouts, size limits, concurrency control, bounded retries, rate limits, sanitized logs and clear errors.
- Outgoing messages: call `POST https://graph.facebook.com/{GRAPH_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages` with the correct authorization and actual documented Cloud API schema. Respect user-initiated messaging and the 24-hour customer-service window; never send unsolicited promotions.

### Phase B — All forwarded content types

- **Text:** read `message.text.body`; detect explicit URL input; call the existing verification/extraction API according to the actual contract.
- **Image:** obtain `image.id`; use Graph Media API to get metadata/temporary URL; fetch bytes with bearer token; validate content type and size; send to Person 1's extraction endpoint; verify extracted claims.
- **Voice/audio:** process audio message media ID (OGG/Opus when available); send to backend extraction/transcription; handle Gemini 503/timeout as a service failure, not a false/unconfirmed fact-check. Never silently claim transcription worked.
- **PDF/document:** validate supported PDF MIME/media; download and forward binary using exactly the backend's documented multipart schema; use scanned-PDF OCR through existing backend.
- **URL:** pass to the backend's SSRF-protected safe URL extractor; do not independently fetch potentially unsafe user-supplied URLs from the adapter.
- **Other:** return a short, polite supported-format message without attempting Gemini/Tavily calls.

**Crucial:** Inspect real backend API models/OpenAPI before writing `truthlens_client.py`; implement response mapping against exact field names. Add contract tests that detect schema drift. Never hardcode example or invented source links as real responses.

### Phase C — WhatsApp reply experience

Create concise, readable replies containing:

1. Claim being checked (bounded length).
2. Actual verdict from backend: `verified`, `false`, `partially_true`, `outdated`, `misleading_context`, `unconfirmed`.
3. A short evidence-grounded explanation that says what is known, what is wrong or missing.
4. At least one real source title + link when returned by the backend (up to a safe concise number); no invented citations.
5. Actual check timestamp and optional follow-up controls: `HINDI`, `MARATHI`, `SOURCES`, `HELP`, `STOP`.

Language and age-friendly rewriting must **not change claim IDs, evidence or verdict**; reuse backend explanations when available. If provider error occurs, send a clear temporary-unavailability reply with no factual verdict. Handle multiline / too-long messages by splitting or linking to an authorized web report.

### Phase D — Meta account and deployment handoff

Create a step-by-step README covering:

1. Meta Developer registration and Business Portfolio / WABA setup; never invent organization credentials.
2. Temporary test number, Phone Number ID, WABA ID and allowlisted recipients.
3. Creating a unique verify token; finding Meta App Secret; separating that from access token.
4. `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_WABA_ID`, `WHATSAPP_VERIFY_TOKEN`, `META_APP_SECRET`, `GRAPH_API_VERSION`, `TRUTHLENS_BACKEND_URL` in `.env.example` only as dummy placeholders.
5. Starting Person 1 backend on 127.0.0.1:8000 and adapter on 127.0.0.1:8100.
6. Exposing adapter with an HTTPS tunnel (for example ngrok) and setting callback `https://<host>/webhook/whatsapp`.
7. Completing Meta webhook verification and subscribing to `messages` for the correct WABA.
8. Sending a sanctioned test message with approved sender and seeing automated reply.
9. Production token, approved phone, support contact, privacy policy, access controls and messaging window caveats.
10. Website button and QR code opening a `wa.me` link **only after** a real approved number exists. Do not embed secrets in links.

### Phase E — Testing; conserve external quotas

Most tests MUST be offline and deterministic. Mock Meta webhook, Media API, Person 1 FastAPI, Graph replies and provider errors. Test:

- GET verification succeeds with correct token and fails with incorrect token.
- POST signature verification accepts valid raw-body digest and rejects tampered payloads.
- Text/Image/Audio/PDF/URL messages map to correct Person 1 calls and truthful output.
- Correct MIME and length limits; malicious URLs handled by backend SSRF rules.
- Message status webhooks ignored; duplicate message IDs processed only once.
- Gemini 429, 503, timeout; Tavily failure; unreadable attachment; missing evidence.
- `verified`, `false`, `partially_true`, `outdated`, `misleading_context`, `unconfirmed` mapped faithfully, no forced labels.
- Hindi and Marathi retain original verdict/evidence.
- `STOP`, `HELP`, service window and no unauthorized outbound campaigns.
- No PII or secrets in logs, fixtures, commits, screenshots or documentation.

**Live budget:** Default **ZERO real Gemini/Tavily requests** during implementation; use mocked Person 1 responses. When the real WhatsApp integration works, if credentials/eligibility allow, perform **one minimal live text-to-evidence WhatsApp test**; request explicit approval before using further model/search credits. Provider failures should be recorded honestly. Never fake a successful fact-check.

Run the project's relevant unit tests, lint/type checks and adapter integration tests. Do not modify Person 1 baseline or public API schemas.

### Phase F — Git and final handoff

- Protect all `.env` files and test user content from Git.
- Work in a Person 2 feature branch (e.g. `feature/whatsapp-adapter`) unless project owner explicitly instructs otherwise.
- Stage only Person 2 changes and relevant non-breaking integration documentation; never stage unrelated Person 1 files.
- Produce complete demo commands, API mapping, issue list, Meta setup steps, test results, and a simple hackathon demo script.
- Commit implementation after checks pass. Do not force-push or overwrite shared `main`. Push only to an approved feature branch with user authorization / tooling permissions; otherwise report exact manual command.

## Acceptance criteria

- A message forwarded by an approved test sender reaches the signed WhatsApp webhook and results in exactly one outbound message.
- At least one full text example is verified through **actual Person 1 API**, returns a real retrieved citation and an uncertainty-appropriate verdict.
- All five formats have working routes or clearly documented, nonfabricated provider/API blockers.
- No new AI verifier, no changed Person 1 contract, no leaked keys, no unsanctioned WhatsApp sends.
- A demo can run from VS Code, with Meta sandbox and local HTTPS tunnel, and the project web app remains usable independently.

**Finish the complete implementation rather than stopping at a plan.** If Meta setup requires interactive account ownership or production policy approval, clearly identify the exact human actions needed and continue implementing everything testable with mocked payloads. Give an accurate PASS / FAIL / SKIPPED / BLOCKED report and exact next steps.
