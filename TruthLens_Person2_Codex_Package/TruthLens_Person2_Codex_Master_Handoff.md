# TruthLens AI — COMPLETE CODEX HANDOFF FOR PERSON 2

> **Purpose:** This file is a self-contained instruction and context package. Give this entire file to Codex inside the TruthLens repository and ask it to implement Person 2's work. It incorporates (a) the supplied five-page document **TruthLens_PS_Aligned_Two_Developer_Plan.docx** and (b) earlier product conversations. The document's agreed division of responsibility and official problem statement **override optional ideas from brainstorming**.
>
> **Developer assigned:** PERSON 2 — Frontend / Data / Meta Platform Engineer. **Do not silently take ownership of Person 1's AI verification backend.**
>
> **Project name:** TruthLens AI. Earlier names (ForwardDNA, TruthOS, ProofGap, ClaimLab) were exploratory concepts, **not** decided product names.

---

## 0. FIRST INSTRUCTION TO CODEX — EXECUTE, NOT JUST PLAN

You are the engineering agent assigned to implement **Person 2's scope** of TruthLens AI in the repository that is currently open in your workspace.

1. Inspect the actual repository, installed frameworks, and existing code before making changes. Read the README, package manifests, environment examples and any shared API schemas. **Preserve existing code and conventions** where practical; do not overwrite working Person 1 endpoints.
2. Summarize what already exists and how you will satisfy the Person 2 deliverables. Then **start implementation**; do not stop after writing a plan.
3. If the frontend is absent, scaffold a production-ready **Next.js + TypeScript** application (App Router recommended) with a clean, responsive design. Choose Tailwind CSS or adapt the existing styling setup; avoid over-engineered UI dependencies.
4. **Work contract-first:** Person 1 develops the FastAPI multimodal verification engine separately. Implement an isolated typed API client + adapter layer and high-quality, clearly labeled local mock fixtures so the frontend works without backend API keys or server availability. When the real backend is ready, only API adapter configuration and any explicitly negotiated schema differences should change.
5. Implement in gates G0–G4; only start G5 optional differentiators after the five input formats, claim-by-claim sourced results, accessibility, and honest uncertainty work.
6. Create/update code, tests, `.env.example`, and setup/deployment documents. Run available lint/typecheck/test/build checks and fix any errors. Report what was truly implemented versus what is blocked by missing credentials, Person 1 services or approvals. Never claim a feature works when it only has a mock demonstration.
7. Ask for input only when absolutely blocked by a missing decision or credential; document reasonable reversible assumptions instead of waiting. **Never invent provider secrets or source citations.**

---

## 1. PRODUCT CONTEXT AND WHY WE ARE BUILDING IT

### Hackathon problem statement (PS3, GenAI, “Is This Forward True?”)

Build an AI system to check factual claims from **WhatsApp messages, screenshots, voice notes, PDFs, and public URLs** against reliable sources. It should provide **individual claim verdicts**, real evidence, plain-language explanations, and explicitly distinguish **verified, false, outdated, partially true, misleading context, and unable to confirm**. People uncomfortable with English should be able to understand the result.

This is **not** a generic text chatbot, a single “fake/real” classifier, or a convincing static demo with hard-coded answers. Important audiences include Indian WhatsApp users and less tech-savvy people receiving government scheme forwards, health claims, dated announcements, breaking news, and other potentially misleading messages.

### Key discussions leading to the current plan

We repeatedly explored novelty. Initially discussed: Claim Mutation X-Ray, Minimum Truth Repair, Truth Conditions Engine, historical/time-based evidence, multilingual duplicate-claim recognition, adversarial verification, claim-to-code tests, living verdict recalls, safe link/action investigation, and active proof gathering. **These were brainstorms, not approved mandatory requirements.** We concluded that simply adding agents/OCR/RAG/WhatsApp is not defensible originality; the differentiator must not compromise a robust judge-ready core.

The definitive supplied implementation brief names the project **TruthLens AI** and sets the official priorities: **full multimodal input support, independently checkable atomic claims, attributable evidence per claim, honest verdicts, understandable explanations, a working accessible web demo**, and a strict two-developer split. Optional frontend-led differentiators named in that document are **truth cards, related-forward clustering, claim evolution tracking, and aggregated misinformation radar**. WhatsApp is an optional channel; the web application must work even without Meta approval.

**Product principle:** “Show WHO said WHAT, WHEN, with a real link; distinguish absence of evidence from evidence of falsehood.” Never treat a pretty interface as a substitute for this.

---

## 2. EXACT OWNERSHIP: PERSON 2 VS PERSON 1

### Person 2 — you must own

- **Website:** Responsive Next.js interface with paste text, screenshot/image upload, audio/voice-note upload, PDF upload, and a public news/article URL field; visible extraction preview; progress and failure states; readable per-claim evidence cards. Large type, easy steps, mobile-first accessibility, optional read-aloud controls.
- **Evidence presentation:** For each independent claim, show verdict and plain explanation, each source's **publisher, actual URL, title, publish/verification and retrieval dates, stance, attributed excerpt, and “what this source says”**. Explicitly show contradictions, limitations, next steps, uncertainty.
- **Localization and reading mode:** English, Hindi, Marathi language selection; normal vs easy-to-read/senior-friendly controls. This is **display/explanation**, and must **never rewrite the factual verdict or claim meaning**. Real LLM explanation transformation is provided by Person 1's `/api/explain`; UI translations belong to Person 2.
- **Supabase/data:** Opt-in report persistence, secure per-user history, access controls, retention/deletion, typed schema/migrations, APIs for `/api/history`, `/api/tracker`, `/api/radar` when corresponding phases are reached.
- **Extra frontend features, only after core works:** citation-backed shareable truth cards, conservative similar-forward grouping, observed claim timeline, privacy-respecting aggregate misinformation radar.
- **Meta configuration/release:** Create/configure WhatsApp developer/business/WABA **test** assets and relevant webhook subscriptions if credentials/access exist, phone number ID and environment configuration, demo link/QR, deployment and handoff guide. **Person 1 writes the actual WhatsApp webhook implementation.**
- **Deployment and integration:** Publish accessible web app over HTTPS, connect to Person 1 FastAPI when available, maintain fixtures and a working zero-secret demo fallback.

### Person 1 — DO NOT BUILD THESE UNLESS YOU EXPLICITLY AGREE ON A REASSIGNMENT

- FastAPI backend, typed request/response schemas, health/capability checks, validations.
- Actual OCR, audio transcription, PDF/scanned-PDF extraction and safe remote URL extraction.
- Atomic factual claim detection, normalization, multilingual search and live source retrieval/fact-check APIs.
- Evidence-grounded verdict decision logic and its explanations (English/Hindi/Marathi).
- Stale news / scam and scheme / original-context / risk analysis (secondary optional AI features).
- Meta signed webhook verification, inbound events, media IDs, message deduplication and outgoing replies (Person 1 code).

You **may build proxy route handlers, mocks and API adapters** to consume Person 1 routes. They are integration infrastructure, not a replacement AI backend. Do not label frontend heuristic guessing as actual verification.

---

## 3. THE FIVE CORE USER JOURNEYS (ALL ARE MANDATORY)

1. **Text:** User pastes WhatsApp forward (possibly long and containing multiple factual claims). Click Verify. Frontend calls `/api/verify` and shows a **separate card for each factual assertion**, source list and independent verdict.
2. **Screenshot/image:** Accept common image formats; preview file name/thumbnail; POST to `/api/extract`; display actual OCR text; allow user to correct OCR mistakes **before** sending text to `/api/verify`; disclose when text is edited.
3. **Voice note/audio:** Accept browser-supported audio upload including formats compatible with Person 1 extractor; display file name/size and optional playback; show transcript and language; let user review/correct transcript, then verify.
4. **PDF notice:** Upload PDF; show extracted text, pages/page reference if backend supplies it; scanned PDF goes through Person 1 OCR fallback; review then verify.
5. **Public URL:** Accept HTTP(S) news/article links; POST to `/api/extract/url` (backend handles SSRF safety); display article title/metadata if available plus extracted content; review then verify. Never rely on a frontend proxy that blindly fetches arbitrary user URLs.

For all five: show states **idle → validating → uploading/extracting → review extracted text → verifying → results**. Include accessible progress messaging, cancellation/reset as feasible, clear error messages, retry, and no fabricated results. Avoid duplicate submissions. Extraction is not verification; make this visually clear.

**Explicitly handle:** unconfirmed when evidence is missing; conflicting sources; multiple claims with different verdicts; partial success; empty/too-short extraction; unsupported/corrupt file; link extraction unavailable; backend offline; rate limits/timeouts; unavailable optional provider.

---

## 4. CORE PAGE STRUCTURE AND UX REQUIREMENTS

Design a coherent professional Trust/Verification UI, not a generic chatbot layout.

### Public/home verification flow

- TruthLens AI heading, concise statement of purpose, noticeable **“Verify a forward”** action and compact input selector: **Text | Screenshot | Voice | PDF | URL**.
- Clear text box and drag-and-drop/select-file affordance; appropriately labeled controls; source and privacy notice; never auto-save submissions.
- A small **“How it works”** explainer: submit → extract → inspect claims/evidence → understand the result.
- Extraction preview/editor with format metadata, confidence or warnings only **if actually supplied** by the extractor; user edits must be preserved through verification.
- Results summary: verification time, high-level summary, number of factual claims, clear indication when any claim remains unconfirmed; DO NOT collapse all claims into one green/red badge.
- Claim cards, numbered and navigable. Each: claim text; verdict; short/plain explanation; exact reason; original/temporal context if returned; limitations; recommended next step; evidence list with stance and dated attribution. Provide “view original source” links (safe anchors, `rel="noopener noreferrer"`).
- Evidence ledger: one actual backend source per record. Show the published date when known, retrieved date when available, source type and exactly what it supports/contradicts. If date unknown, display “Date not provided”, not an invented date.
- “Explain simply / Change language” control, powered by `/api/explain`, that preserves original facts/verdicts/evidence. Show the source-backed original result if rephrasing fails.
- Clearly distinguish **Verified**, **False**, **Partially true**, **Outdated**, **Misleading context**, **Unconfirmed** with text + distinct icons; do not rely solely on color. Use a neutral/warning presentation for uncertainty.
- Clear controls: Verify another, retry, copy textual evidence summary, opt-in Save to history (if Supabase configured), optional share card after core.

### Other frontend pages

- `/history`: private authenticated user report history (opt-in only); saved timestamp, abbreviated text, verdict summary; report detail; deletion; empty state; must never display another user's content.
- `/tracker`: optional, after core: related claims, observed timestamps, evidence/version notes; show **observed submissions**, not claim origins or private WhatsApp diffusion.
- `/radar`: optional, after core: **aggregated consented submissions only**, clearly labeled sample scope and measurement limitations. Do not infer city-wide or national prevalence from our tiny sample.
- `/privacy` and/or accessible inline privacy information: what is sent for AI verification, what's saved only with consent, how to delete, handling of sensitive forwarded content.
- Mobile layout should be fully usable on a typical narrow handset. Ensure large click targets, keyboard navigation, visible focus, screen-reader labels, semantic status announcements and readable contrast.

### Suggested visual direction (not a fixed brand specification)

Trustworthy investigative interface; airy, contemporary and readable. Avoid giant gradients and endless cards, crowded dashboards and fake “AI confidence 97%” numbers. Evidence has priority over decoration. A source-versus-claim comparison, readable typography and an at-a-glance verdict are key. Provide a senior-friendly large-text toggle and reduce animation for users who request reduced motion.

---

## 5. CONTRACT-FIRST INTEGRATION — THIS IS CRITICAL

The document requires the two developers to agree on HTTP schemas **on Day 1**. Person 2 builds against fixed fixture responses, and Person 1 later delivers live data without changing field names or verdict values.

### APIs and ownership (exact route names from document)

| Route | Owner | Purpose |
|---|---|---|
| `GET /api/health` | P1 | Backend health and configured capabilities |
| `POST /api/extract` | P1 | Multipart image/audio/PDF → text and metadata |
| `POST /api/extract/url` | P1 | Public URL → safely extracted content |
| `POST /api/verify` | P1 | Input text → atomic claims, sources, verdicts and explanations |
| `POST /api/explain` | P1 | Rephrase an already verified response; never modify verdict/evidence |
| `GET /api/history` | P2 | Authenticated opt-in saved reports |
| `GET /api/tracker` | P2 | Related consented claims and appearance timeline |
| `GET /api/radar` | P2 | Aggregated, privacy-safe consented claim statistics |
| `GET/POST /webhook/whatsapp` | P1 code / P2 setup | Meta webhook handshake, events and replies (OPTIONAL) |

### Shared response types — document-defined minimum

`VerificationResult`:
- `verification_id`
- `status` (document includes this field but DOES NOT define its allowed values: agree with P1; do not conflate it with per-claim `verdict`)
- `input`: `{ text, detected_language, input_type }`
- `claims`: array
- `summary`
- `checked_at`
- `warnings`: string array

Each `Claim` MUST have:
- `claim_id`, `claim_text`, `verdict`, `explanation`, `short_summary`
- `evidence`: array of separately attributable evidence records
- `limitations`: array
- `next_step`, `temporal_context`, `original_context`
- optional `forwarding_risk`

Each `Evidence` MUST have:
- `title`, `url`, `publisher`, `published_at`, `retrieved_at`
- `source_type`
- `stance`: **`supports | contradicts | context | neutral | unclear`**
- `excerpt` (actual source passage; never an invented quote)
- `what_source_says` (attributed paraphrase)

**Per-claim verdict values MUST remain exactly:**

```
verified | false | partially_true | outdated | misleading_context | unconfirmed
```

No renaming to `true`, `fake`, `suspicious`, `misleading`, etc. A forwarding/scam risk indicator is **NOT** a falsehood probability and must not be confused with factual verdict.

### Proposed request/extraction/error shapes — NOT YET APPROVED BY PERSON 1

The supplied document specifies output minimums and route names, not exact request bodies or error shapes. Treat the following as a **draft adapter contract**, write it down in `docs/api-contract.md` and reconcile with P1 before wiring production.

- `POST /api/extract`: multipart/form-data with `file`. Proposed response: `{ text, detected_language, input_type, metadata?, warnings[] }`.
- `POST /api/extract/url`: `{ url: string }`. Proposed response: `{ text, detected_language, input_type: 'url', metadata?: {title?, url?, published_at?}, warnings: [] }`.
- `POST /api/verify`: `{ text: string, input_type: 'text'|'image'|'audio'|'pdf'|'url', detected_language?: string, source_metadata?: object }`, yielding `VerificationResult`.
- `POST /api/explain`: `{ verification: VerificationResult, language: 'en'|'hi'|'mr', audience: 'standard'|'easy' }`, returning either a language-specific explanation payload or a non-mutating copy of the verification; **the actual shape is to be agreed**.
- Proposed error: `{ error: { code, message, details? } }` with HTTP status; Person 2 should write one centralized translator for display errors and never show raw stack traces.

For backend status, progress and health capabilities, use defensive decoding: optional metadata is optional, empty evidence arrays are valid for unconfirmed results, nullable dates are accepted, unrecognized fields are ignored, and a malformed required field produces a visible error instead of fake success.

### Recommended Next.js API integration pattern

- In Next.js, write a **typed `lib/api` client** and a few same-origin BFF proxy route handlers (`/api/extract`, `/api/extract/url`, `/api/verify`, `/api/explain`, `/api/health`) that forward to a separate configured FastAPI origin via server-only `BACKEND_BASE_URL` when possible. These are **proxy routes, not P1 replacement endpoints**.
- The Next.js-owned `/api/history`, `/api/tracker`, `/api/radar` routes read from your own Supabase data.
- Avoid route collisions and circular calls. Do not expose service-role keys, Meta tokens or P1 private API keys in `NEXT_PUBLIC_*` variables.
- If the existing repo has a different working architecture, adapt to it, but keep the same central typed adapter boundary.
- Provide a **clearly labeled development fixture mode** (e.g. `NEXT_PUBLIC_USE_MOCK_API=true`) containing at least six realistic UI test responses. Never silently fall back to fixtures in a production verification request: show an explicit disabled/error status if backend is unavailable.
- Support loading, request cancellation, sane timeouts, bad payload and rate-limit errors, and transparent user retry.

### Example minimal response (SYNTHETIC MOCK, NOT A REAL FACT-CHECK)

```json
{
  "verification_id": "mock-verification-001",
  "status": "completed",
  "input": {
    "text": "Every student in India will receive Rs 20,000 tomorrow.",
    "detected_language": "en",
    "input_type": "text"
  },
  "claims": [
    {
      "claim_id": "claim-001",
      "claim_text": "Every student in India will receive Rs 20,000 tomorrow.",
      "verdict": "unconfirmed",
      "explanation": "There is not enough independently verifiable evidence to confirm this specific announcement.",
      "short_summary": "No sufficient supporting evidence found.",
      "evidence": [],
      "limitations": ["Available sources may be incomplete or delayed."],
      "next_step": "Check the relevant ministry's official announcements.",
      "temporal_context": null,
      "original_context": null
    }
  ],
  "summary": "One claim could not be confirmed from the available evidence.",
  "checked_at": "2026-10-11T09:00:00Z",
  "warnings": ["UI FIXTURE ONLY — NOT A REAL FACT-CHECK"]
}
```

Important: `"status":"completed"` is an **illustrative proposed transport status, not an approved enum**, and this sample must be marked **MOCK** prominently in the UI. Never insert made-up government evidence or URLs that users could mistake for real citations. Provide additional **synthetic fixture variants** for all verdicts and stance values solely to test UI components.

---

## 6. SUPABASE DATA DESIGN, PRIVACY, HISTORY

Use Supabase for optional **consented verification history**, not as the source of factual truth. Start with minimal tables; expand only if needed.

Recommended schema (you may adapt to the actual repo and product constraints):

- `verification_reports`: `id` (UUID), `owner_id` (Supabase auth user ID), `verification_id` (external result ID), `input_type`, `input_excerpt`, `report_json` (JSONB immutable backend result snapshot), `consent_to_store` (true), `created_at`, `retention_expires_at` (optional), `deleted_at` (optional).
- `claim_observations` (G5 only): `id`, `owner_id`, `verification_report_id`, normalized/hashed claim representation, verdict, observed_at, `consent_to_aggregate` flag. **Do not assume a hash is fully anonymous for short/sensitive claims**.
- Optional `shared_truth_cards` (G5 only): opt-in public sharing with high-entropy unguessable ID, configurable expiry/revocation, explicit warning before making the content link-accessible.

Security and product policies:

1. By default, run verification **without storing the message in our database**; network transmission to P1 for verification is necessary and must be disclosed.
2. Save only after explicit, informed user consent, ideally backed by authenticated user identity. If authentication or Supabase is unavailable, keep verification functional but disable server history safely. Do not create an unprotected anonymous shared table.
3. Enable **Row Level Security** on all user-owned tables. Users can select/insert/delete only their own rows. Never rely on a client-supplied `user_id` for authorization. Use server-side verification or user-scoped tokens where needed.
4. Deleting saved reports works; optionally offer retention settings. Avoid logging complete messages/media and minimize sensitive data in telemetry.
5. Never expose Supabase service-role keys in browser code. If backend storage is unavailable, UI must show honest messages without dropping or pretending to save data.
6. Aggregation/tracker must only use reports whose owners explicitly permitted reuse, hide tiny/sensitive groups, and say the counts reflect **TruthLens users' opted-in submissions**, not the prevalence of misinformation among all WhatsApp users.
7. **Mock reports must never go to live persistent storage by default**; keep development/test data separate from real user records.

Create SQL migrations, row-level security policies, storage/data access tests, and documented env setup. You may add magic-link auth for history, but **never require sign-in to fact-check**. Avoid implementing unneeded image/audio persistence; transient upload to P1 extractor suffices.

---

## 7. ACCESSIBILITY, LOCALIZATION AND TRUST RULES

- Language selector: English (`en`), Hindi (`hi`), Marathi (`mr`). Translate static UI labels locally; obtain claim-level explanation rewriting from Person 1's `/api/explain`. If rewrite fails, retain original cited explanation with an honest notice; **never fabricate a local-language fact-check**.
- Easy-reading mode: larger fonts, expanded spacing, simpler UI labels, optional collapse of lengthy technical detail while keeping sources one click away. An optional Web Speech API “listen” feature can read the **already displayed, verified text**; if unsupported, hide or disable politely. Never imply client speech synthesis is the P1 audio-transcription engine.
- Support screen readers, keyboard navigation, visible focus, high contrast, semantic form fields, text alternatives to icons and status/error announcements (`aria-live`), and meaningful source-link labels.
- Make verdict distinctions clear without green/red-only signifiers. Every claim needs a readable textual verdict and uncertainty limitations.
- Evidence source display is literal: do not invent article publication dates, citation passages, publisher names, original image provenance, or confidence percentages.
- Original evidence absence is not disproof. If the P1 response is `unconfirmed`, render “Not enough evidence to confirm” rather than “False.”
- Handle multi-claim messages without implicitly assigning all claims the same verdict.
- Risk warnings are heuristics; never present them as proof of scams, guilt or probability of falsehood.

---

## 8. OPTIONAL NOVELTY FEATURES — STRICTLY AFTER CORE G0–G4

Earlier conversations were intentionally ambitious, but the working document requires delivering the official PS first. P2-owned features permitted **in G5**:

### A. Shareable Truth Card

Generate a clean card/share text for an existing **real** verification: exact claim, verdict, shortened reason, publisher/source links, checked timestamp, “may change” caveat and TruthLens report link where permitted. Add copy/share and optional client-side image export only when the underlying result is sourced. No “verified” claim if the backend says `unconfirmed`; no source cropping that changes the meaning.

### B. Similar-Forward Grouping

Cluster **opted-in recorded claims** as “possibly related”, with provenance of the match and the ability to inspect differences. Do not call this the original forwarding chain; WhatsApp private message histories are inaccessible. Start with a simple transparent text comparison; avoid claiming multilingual semantic equivalence unless a reliable service exists and validation is done.

### C. Claim Evolution Tracker

Show **timestamps of observed user-submitted variants and separately verified evidence updates**. Explicitly distinguish **when TruthLens observed the submission** from when a claim first appeared publicly. Do not invent an origin date or sender graph. If P1 lacks source version data, show only observations.

### D. Community Misinformation Radar

Only privacy-safe counts from explicitly opted-in submissions, with timestamps, filtering if sample size allows, a small-sample caveat, and meaningful aggregation. Do not display private message text publicly or mislabel it as global trend data.

### Ideas discussed previously but **NOT IN THE APPROVED PERSON 2 SCOPE**

Minimum Truth Repair, Claim Mutation X-Ray, claim-to-code experiments, living automated recall alerts, proactive proof solicitation, consequence/link-action sandbox and broader agentic architectures. These might become future product/research tracks; **do not implement them in this assignment** unless separately requested and reviewed with Person 1.

---

## 9. META / WHATSAPP — RESPONSIBILITY AND LIMITS

User previously asked to deploy a WhatsApp bot. We decided WhatsApp is a **useful access channel**, not the novel verification algorithm. The official brief marks it OPTIONAL and assigns code to Person 1 and setup to Person 2.

**Person 2 handles:**
- Document creating a Meta Developer app and WhatsApp Business Platform test setup (business/WABA test assets where eligible), phone number ID, app secret / access-token names and scopes, callback HTTPS URL, verification token handoff to P1, webhook subscription events, and QR/link for the demo.
- Configure Meta assets only when legitimate access and approval are present; never place tokens in source control or in frontend env variables. Maintain `.env.example` placeholders only.
- Coordinate webhook route and HTTPS deployment with P1, verify test messaging and media delivery with P1's signed webhook implementation.
- Create a web-based end-to-end demo path independent of WhatsApp activation or policy approval.

**Person 1 handles:** `GET/POST /webhook/whatsapp`, signed challenge/webhook events, message processing, inbound/outbound messaging, media IDs, signature verification, deduplication.

**Privacy/realism:** The bot cannot read private WhatsApp chats or enumerate a forwarded message's recipients. Users must submit messages voluntarily. Review current Meta rules, account and template requirements before production; do not assume broad public chatbot access is approved. A webhook test and public production service are different milestones.

---

## 10. SUGGESTED FILE / MODULE ARCHITECTURE

Use the repo's current layout if already established. For a clean Next.js App Router frontend, a reasonable design is:

```
frontend/
  app/
    page.tsx                     # submission + review + verified results
    history/page.tsx             # opt-in authenticated history
    tracker/page.tsx             # optional G5
    radar/page.tsx               # optional G5
    privacy/page.tsx
    api/
      health/route.ts           # server-side proxy to P1
      extract/route.ts          # server-side multipart proxy to P1
      extract/url/route.ts      # server-side JSON proxy to P1
      verify/route.ts           # server-side proxy to P1
      explain/route.ts          # server-side proxy to P1
      history/route.ts          # P2-owned persistence endpoints
      tracker/route.ts          # P2-owned optional endpoint
      radar/route.ts            # P2-owned optional endpoint
  components/
    input/                       # Text / Screenshot / Audio / PDF / URL
    verification/                # claim cards, evidence ledger, summary
    accessibility/               # reading mode, language, speech
    layout/
  lib/
    api/                         # endpoint adapter, schemas, transport
    i18n/                        # UI labels en/hi/mr
    supabase/                    # browser/server scoped clients and RLS-safe data helpers
    fixtures/                    # explicitly mocked, never prod fallback
    formatters/                  # dates, stance/verdict labels
  types/
    verification.ts              # backend-owned shape mirrored/validated
  tests/
  .env.example
  README.md
supabase/migrations/             # if Supabase integration exists
 docs/
   api-contract.md
   person2-setup.md
   deployment.md
   meta-setup.md
   qa-demo-checklist.md
```

Do not introduce duplicate component libraries or services just to satisfy the example tree. Prefer simple, typed, testable modules.

---

## 11. BUILD GATES AND ORDER — REQUIRED

### G0 — Shared setup and scaffold

- Inspect repository; initialize/adapt Next.js.
- Create design tokens, types, response validators and API client, and document proposed/requested API shapes.
- Load 6+ labeled synthetic fixtures, env toggles, error handling, frontend routing and baseline tests.
- Set up Supabase schema and optional auth without blocking anonymous fact-checking; write no real data until consent.
- Prepare Meta test setup documentation independently; do **not** block G1–G4 on Meta.

**Checkpoint:** UI starts locally with clearly labeled fixtures; TypeScript builds; P1 contract questions documented.

### G1 — Core text verification flow

- Text input and accessible progress, verifying state and extraction-bypass path.
- Multiple independent claim result cards; evidence ledger per claim including stance, dates, publication and actual source URL; verdict enum mapping; limitations and next steps.
- Empty evidence/unconfirmed state, API unavailability state and cross-language labels.

**Checkpoint:** At least two claims show different valid verdicts and individually traceable evidence; when live backend exists, no fixture data leaks into responses.

### G2 — Multimodal UX

- Image screenshot with preview, audio with transcript preview, PDF with extracted text, URL with fetched content; all through P1 extractors.
- Review/edit extracted text before verification; errors and file validation.
- Metadata if available, and source-specific extraction warnings.

**Checkpoint:** All five supported entry paths end in the same `/api/verify` pipeline.

### G3 — Accessible explanation

- English/Hindi/Marathi selection; call `/api/explain` to rephrase only, keep verdict/evidence intact.
- Senior/easy-reading mode and optional browser speech playback.

**Checkpoint:** Switching language or audience cannot silently change a verdict, claim ID, or evidence URL.

### G4 — Quality, demo and deployment

- Manual/automated end-to-end tests, mobile usability, verified source links and timestamps, accessibility and clear errors.
- Deploy web independently of Meta. README with environment configuration, staging vs production behavior, and brief demo script.
- P1/P2 daily 15-minute integration test with two different claims + at least one file.

**Checkpoint:** Judge-ready end-to-end web demo; actual live evidence from P1 when connected.

### G5 — Extras only if all G0–G4 acceptance conditions pass

- Optional truth cards, opt-in history/polish, related claim tracker, privacy-safe radar, Meta QR/test hookup.

NOTE: **Secure opt-in Supabase history is part of P2 ownership**, so implement its foundation during early gates; richer history/sharing/tracker enhancements can be polished in G5. Do not let dashboards crowd out the core verification flow.

---

## 12. TESTS, FIXTURES AND FAILURE CASES

Add automated tests as practical (Vitest/React Testing Library for components; Playwright for user flows if the setup supports it). Always distinguish **mock UI testing** from **live retrieval**.

**At least six fixtures or test cases:**

1. Long forward with **two or more claims** having different verdicts and different sources.
2. Screenshot OCR text response plus optional extraction warning.
3. Hindi or Marathi voice note transcript, later explained in selected language.
4. PDF extracted text with page info or scanned fallback warning.
5. Valid article URL extraction with document title/date when supplied.
6. A claim with **zero evidence** and verdict `unconfirmed` — never render “false”.

Also test all six **verdict enum** renderings and all five **evidence stance** renderings; missing dates; conflicting evidence; stale source; empty claim list; unsupported file; extraction failure; 429/5xx backend errors; save/delete RLS; refusal of unauthenticated history access; UI translation preserving original verdict/source IDs; saved report opt-in only; mobile layout; full keyboard navigation; no mock mode silently used in production.

**High-priority judge demo from original brief:** a long multi-claim WhatsApp forward; a screenshot; a real audio voice note; PDF notice; public article URL; and a ₹500 currency-related forward checked against actual RBI sources (P1 owns obtaining the RBI evidence; P2 displays only what P1 actually retrieves). Do not hardcode a claim verdict for the RBI demonstration.

---

## 13. ENVIRONMENT, DEPLOYMENT, RELEASE CHECKLIST

Create a working `.env.example` with explanatory placeholders, adapting to the repository. Suggested names:

```
# PRIVATE: consumed only by Next.js server for P1 upstream calls
BACKEND_BASE_URL=http://localhost:8000

# PUBLIC: explicit development-only fixture mode; MUST NOT silently activate in production
NEXT_PUBLIC_USE_MOCK_API=false

# Supabase project browser configuration (public)
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=

# PRIVATE if truly required by server-side tasks; never client-exposed
SUPABASE_SERVICE_ROLE_KEY=

# Meta settings are for controlled setup/P1 webhook, not public frontend
# META_WABA_ID=
# META_PHONE_NUMBER_ID=
# META_ACCESS_TOKEN=
# META_APP_SECRET=
# META_VERIFY_TOKEN=
```

Important: The precise Supabase public key environment convention can vary by client/version. Use the installed SDK's current documented option and explain it. Do not require `SUPABASE_SERVICE_ROLE_KEY` if user-scoped client + RLS can do the job; least privilege wins.

Document local startup instructions for both dev servers, migrations, auth callback URLs, staging vs prod flags, provider timeouts, public HTTPS deployment and where P1 webhook URL is configured. Deploy on a suitable Next.js host (e.g., Vercel) while P1 separately deploys FastAPI. Do not claim production WhatsApp is ready until a real test has passed.

---

## 14. HARD ACCEPTANCE CRITERIA (FROM THE BRIEF)

You are done with **Person 2 core** only when:

- [ ] The working web app accepts **text, screenshot, audio, PDF, public URL** end-to-end via P1 or a visibly marked local **mock test mode**; production does not rely on canned verdicts.
- [ ] Every independently checkable claim gets a separate verdict card with traceable, source-specific evidence. Source publisher, title, URL, relevant excerpt/paraphrase, publication/retrieval date and stance are visible when provided.
- [ ] `unconfirmed` and conflicting evidence are represented cautiously and never mislabeled “false”.
- [ ] English/Hindi/Marathi display and easy-reading mode work; `/api/explain` never changes facts, verdicts or citations.
- [ ] User can inspect/edit extracted text and understand extraction warnings.
- [ ] Website is simple for nontechnical users and works on mobile without WhatsApp access.
- [ ] Opt-in history respects identity, RLS, consent, deletion and no persistent storage by default.
- [ ] API integration contract and fixture payloads are checked with P1, or their remaining differences are explicitly tracked.
- [ ] Core demo runs live for **at least three input types**; remaining two must have documented working tests. Aim for all five live.
- [ ] There is **no invented evidence or unverifiable citation** in a live user result.
- [ ] README, env/config, setup, deployment steps and QA evidence are provided; build/test results are honest.

### When you finish each gate, report using this format

```
Gate: G0 / G1 / G2 / G3 / G4 / G5
Files created/modified:
What works with the REAL backend:
What works in MOCK mode ONLY:
Tests run and results:
Credentials/integration blockers:
Contract questions needing Person 1 confirmation:
Next smallest implementation step:
```

---

## 15. QUESTIONS TO RESOLVE WITH PERSON 1 EARLY (DO NOT BLOCK MOCK UI)

- Exact `/api/extract` multipart field names, accepted MIME types, upload size limit, extraction metadata and transcription language fields.
- Exact request/response of `/api/extract/url`, `/api/verify`, `/api/explain` and error handling. Sync versus long-running verification response; any job polling.
- Meaning and values of top-level `status`, date formats/nullable fields, `input_type` nomenclature (`audio` versus `voice`), and whether claim/evidence arrays may be empty.
- Does backend supply extracted claim spans / PDF page references? Optional rendering only when present.
- How do we rephrase language without changing evidence: full verification object in `/api/explain` or verification ID with P1 storage?
- Any API authentication, request size/time limits, CORS/proxy requirements, and hosted FastAPI base URL.
- What does backend return when a provider is offline or evidence search fails? It must not return a fabricated “false”.

**Do not independently redefine agreed verdict enum, evidence stances, required shared response fields or endpoint names.**

---

## 16. IMMEDIATE FIRST CODING TASK

**Start now with G0 and G1:** inspect existing repo, implement/adapt the responsive five-tab verification entry UI, implement the typed shared result contract, mock API fixtures and switch, and render a multi-claim result with credible component structure for all six verdicts and source evidence records. Make the UI work from local fixtures while preserving a straightforward route to the real P1 FastAPI. Add runtime validation, progress/error/unconfirmed states, tests and setup notes. After G1 is working, proceed to G2–G4 incrementally. **Do not spend the first session on radar, claim clustering, speculative research novelties or a production WhatsApp integration.**

When complete, show me what changed, how to launch it, what is still mocked, and the exact schema/credential details I need from Person 1.
