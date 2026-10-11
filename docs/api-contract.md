> Historical provisional contract. Superseded for HTTP schemas by backend-api-contract.md, backend-openapi.json and person2-contract-reconciliation.md.

# TruthLens shared API contract

Version: 0.1 PROVISIONAL — awaiting Person 1 confirmation. Primary authority: `TruthLens_PS_Aligned_Two_Developer_Plan.docx`. The supplementary handoff clarifies implementation, but does not override the Word plan. No Person 1 code is included here.

## Change agreement

Document-defined field names, endpoint names, verdicts and stances are fixed. Request bodies, extraction metadata, errors, health capabilities, explanation shape and transport statuses below are proposals. Person 1 must confirm them against their OpenAPI specification before live sign-off. Schema changes require a recorded agreement, adapter change and updated fixtures/tests. Never quietly rename agreed fields.

| Item | Status | Decision needed |
| --- | --- | --- |
| Verification, claim, evidence minimum fields | Word-plan required | Confirm OpenAPI matches |
| Verdict and stance values | Word-plan fixed | No unilateral changes |
| Extract upload field `file`, MIME support, 10 MiB cap | Provisional | Confirm P1 and hosting limits |
| Verify and URL request bodies | Provisional | Confirm exact names and limits |
| Top-level `status=completed` | Provisional | Confirm values; add polling only if negotiated |
| Explain display-only projection | Provisional | Confirm shape and grounding behavior |
| Health capability response | Provisional | Confirm feature availability schema |
| Error codes, bearer authentication, timeouts | Provisional | Confirm upstream conventions |

Confirmation record: P1 name/date/OpenAPI revision: **pending**. No message has been sent to Person 1; this document is the reviewable handoff.

## P1 services through fixed-origin Next.js proxies

- `GET /api/health` → `{status: string, capabilities?: {extract: InputType[], verify: boolean, explain: boolean}}`.
- `POST /api/extract`: multipart `file` → `{text, detected_language, input_type, metadata?, warnings: string[]}`.
- `POST /api/extract/url`: `{url}` → same extraction object, input_type `url`. Only P1 fetches the supplied URL and owns SSRF protection.
- `POST /api/verify`: `{text, input_type, detected_language?, source_metadata?}` → VerificationResult.
- `POST /api/explain`: `{verification: VerificationResult, language: en|hi|mr, audience: standard|easy}` → `{verification_id, language, audience, summary, claims: [{claim_id, explanation, short_summary, next_step}]}`. The UI only applies these display strings. It cannot replace factual fields, verdicts, evidence or dates.

InputType: `text | image | audio | pdf | url`. Text limit provisionally 10–30,000 characters. Multipart total is bounded before parsing. Uploads provisionally accept JPEG/PNG/WebP, MP3/M4A/OGG/WAV/WebM/AAC, PDF. Browser MIME is preliminary validation; P1 must inspect actual file content and reject corrupt or spoofed media.

VerificationResult minimum: `verification_id`, `status`, `input{text, detected_language, input_type}`, `claims[]`, `summary`, `checked_at`, `warnings[]`.

Claim minimum: `claim_id`, `claim_text`, `verdict`, `explanation`, `short_summary`, `evidence[]`, `limitations[]`, `next_step`, nullable `temporal_context`, nullable `original_context`, optional `forwarding_risk`.

Evidence minimum: `title`, `url`, `publisher`, nullable `published_at`, nullable `retrieved_at`, `source_type`, `stance`, `excerpt`, `what_source_says`.

Verdict: `verified | false | partially_true | outdated | misleading_context | unconfirmed`.

Stance: `supports | contradicts | context | neutral | unclear`.

Unknown fields are stripped at the adapter; malformed required fields are rejected. Nullable dates are accepted and displayed as unavailable. Empty evidence and claim arrays are valid. Until P1 confirms job states, a non-`completed` result is visibly unsupported rather than displayed as a finished verification.

## P2 routes

- `GET /api/history?cursor=<last uuid>`: authenticated `{reports: ReportRow[], next_cursor: uuid|null}`. 20 records/page, stable UUID cursor order. Expired rows excluded. Full original result is retained in `report_json`.
- `POST /api/history`: `{report, receipt, consent_to_store: true, retention_days: 7|30|90}`. Validated user identity supplies owner_id. Receipt is a one-hour HMAC issued only for live upstream responses. No client identity is trusted; synthetic reports are rejected.
- `DELETE /api/history`: `{id: uuid}`. Owner-scoped hard deletion.
- `POST /api/auth/email`: `{email}`. Supabase PKCE email sign-in link; verify in the same browser.
- `GET /auth/callback?code=...`: exchange PKCE code and redirect only to fixed `/history`.
- `POST /api/auth/signout`: destroy session.
- `/api/tracker`, `/api/radar`: deferred to G5; not implemented as fake endpoints.

All mutation routes require matching Origin. Responses use `Cache-Control: no-store, private`. Backend keys and report-signing keys are server-only. History errors do not expose private backend details.

## Fixtures and failures

The six supplied fixtures are UI-only, include fictional publishers and `example.org` links, and cover all verdicts and stances. `dev:mock` explicitly enables both fixture flags. Production ignores those flags. Arbitrary text or edited samples cannot receive a canned fact-check. Mock explanations are deliberately unavailable rather than invented translations.

Frontend errors: `{error:{code,message}}`, e.g. `BACKEND_OFFLINE`, `TIMEOUT`, `RATE_LIMIT`, `BAD_RESPONSE`, `BAD_INPUT`, `EXTRACTION_EMPTY`, `UNAUTHENTICATED`. Unknown upstream messages and stack traces are not shown. Production never falls back to fixtures.

## Integration sign-off

Before connecting production, obtain P1 OpenAPI and real samples, reconcile all provisional rows, validate two different text claims plus one real file, then run all five modalities. Verify unknown dates, no evidence, conflicting sources, provider failures and translation invariants. Record exact API revision and successful modalities in `gate-status.md`.
