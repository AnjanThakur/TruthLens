# TruthLens backend API contract — Person 1 → Person 2

Base URL for local development: `http://127.0.0.1:8000`. API version: `0.1.0`. [backend-openapi.json](backend-openapi.json) and the generated schema appendix below define exact names, defaults, required fields, constraints and nullable values. Swagger is `/docs`; live OpenAPI is `/openapi.json`. Times are UTC ISO 8601, IDs are UUIDs. All successes and errors carry `X-Request-ID` and `Cache-Control: no-store`.

| Method/path | Request content | Success |
|---|---|---|
| `GET /api/health` | None | `HealthResponse` |
| `POST /api/verify` | JSON `VerifyRequest` | `VerificationResult` |
| `POST /api/extract` | `multipart/form-data`, one `file` part | `ExtractionResult` |
| `POST /api/extract/url` | JSON `URLRequest` | `ExtractionResult` |
| `POST /api/explain` | JSON `ExplainRequest` | `VerificationResult` |

No `/api/history`, `/api/tracker`, `/api/radar`, Supabase operations or WhatsApp endpoints are provided. Person 2 owns persistence and the frontend. Backend models reject unknown request fields. CORS permits only the origins configured in `CORS_ORIGINS`; no credentials/cookies are required.

## Verify request and response

```json
{"text":"From Monday all ₹500 notes are invalid. Forward to everyone!","input_language":"auto","response_language":"hi","audience":"adult","jurisdiction":"IN","input_type":"text"}
```

This is a **demo test prompt**, not a checked claim. Do not preselect its verdict in the UI. Exact repeated input can reuse a successful result for up to 120 seconds; display its original `checked_at`.

| Request field | Values/default |
|---|---|
| `text` | Required nonblank string; API schema max 50,000, configured runtime default max 24,000 normalized characters |
| `input_language` | `auto` (default), `en`, `hi`, `mr` |
| `response_language` | `en` (default), `hi`, `mr` |
| `audience` | `child`, `teen`, `adult` (default), `senior` |
| `jurisdiction` | Two uppercase letters, default `IN`; search prioritizes reviewed Indian institutions for relevant claims |
| `input_type` | `text` (default), `image`, `audio`, `pdf`, `url`; use the extraction's type when submitting extracted text |

`VerificationResult` fields:

| Field | Meaning |
|---|---|
| `verification_id` | UUID for this check; no server-side history is saved |
| `status` | `completed`, `partial`, `no_checkable_claims` |
| `input` | Common `ExtractionResult` with normalized submitted text and detected language |
| `claims` | Zero or more independent `ClaimResult` objects |
| `summary` | Concise localized combined summaries; useful for speech synthesis |
| `checked_at` | As-of-check UTC timestamp; retained by re-explanation |
| `warnings` | Machine-readable codes and readable messages for omitted claims and failed dependencies |
| `response_language`, `audience` | Applied presentation settings |

`ClaimResult` fields:

| Field | Meaning |
|---|---|
| `claim_id`, `claim_text` | Exact classified statement and stable UUID within this result |
| `original_span` | Exact substring of normalized input used to extract the claim |
| `entities`, `dates`, `qualifiers` | Preserved checkability details; do not silently remove qualifiers |
| `normalized_claim`, `lexical_hash` | Case/NFC/whitespace normalized lexical lookup hooks; hash is SHA-256, not semantic similarity |
| `verdict` | `verified`, `false`, `partially_true`, `outdated`, `misleading_context`, `unconfirmed` |
| `grounded_explanation` | Immutable English evidence-grounded reasoning; translation always starts here |
| `explanation`, `short_summary`, `key_points`, `next_step` | Localized plain wording/read-aloud fields |
| `evidence` | Per-claim `Evidence[]`; may be empty; keep conflicting stances visible |
| `risk` | Weighted forwarding caution heuristic for the original input; separate from factual verdict |
| `temporal_context` | `claim_date`, `relevant_source_dates`, `notes`; do not equate publication date and event date |
| `original_context` | `status` (`not_checked`, `inconclusive`, `found`), `notes`, actual `source_urls` |
| `limitations` | Immutable English metadata explaining what was not established |
| `checked_at` | Claim's as-of timestamp |

`Evidence` fields:

| Field | Meaning |
|---|---|
| `evidence_id` | UUID identifying a retrieved source assessment |
| `title`, `url`, `publisher` | Retrieved title, validated/canonical source link, publisher from reviewed domain identity or unreviewed hostname |
| `source_type` | `primary`, `secondary`, `fact_check`, `other` |
| `published_at`, `updated_at` | Nullable explicit publisher meta/JSON-LD dates, kept separate; neither establishes the event/effective date. Search-only dates retain their search provenance |
| `retrieved_at` | Actual UTC retrieval time |
| `stance` | `supports`, `contradicts`, `context`, `neutral`, `unclear` |
| `excerpt` | Exact contiguous extract, never a model-created quotation |
| `excerpt_provenance` | `fetched_page`, `search_excerpt`, reserved `fact_check_api` |
| `what_source_says` | Exact source-specific extract; the main explanation supplies the plain-language paraphrase |
| `authority_basis` | Reviewed domain match or explicit unestablished-authority note |
| `relevance_score` | Search provider ranking hint, **not truth confidence** |
| `directly_relevant` | Model assessment against this atomic claim; conservative verdict gate requires it |

`Risk` is `{score: 0..100, level: low|medium|high, factors: [{rule, weight, description}], is_probability: false, label}`. Rules and weights are OTP request 35, payment demand 25, identity collection 20, urgency 15, mass forwarding 10, authority appeal 10; sum capped at 100. Low is below 25, medium 25–59, high 60+. It cannot establish fraud or falsity. Render the accompanying label.

## Extraction

`POST /api/extract` accepts exactly a file upload, not JSON/base64. Byte signatures determine format; the filename and supplied MIME type are not trusted. PNG/JPEG, PDF, WAV, MP3 and OGG/Opus-in-OGG are accepted. OGG conversion needs FFmpeg. Current size default: 10 MiB. Read `/api/health` for actual limits.

`POST /api/extract/url` accepts `{"url":"https://public-publisher/article"}`. URL fetching rejects private network addresses, unsafe schemes, credentials and invalid redirects. Every redirect is DNS-validated and IP-pinned. Only bounded HTML/text/PDF is fetched; paywalls and JavaScript pages may be unreadable. A JS-only shell returns existing `422 url_no_text` with a useful message, without script execution. Semantic article/main HTML fallback runs locally. PDF signatures use existing PDF validation even for octet-stream/mislabeled HTML; unsupported binary content remains rejected. Article URLs and linked PDFs share the same extraction services. Details preserve submitted `source_url` and final validated `url` after redirects.

Every modality returns:

```json
{"text":"actual extracted content","detected_language":"en","input_type":"image","warnings":[],"extraction_details":{"ocr_confidence":93.5,"ocr_languages":["eng"],"width":1200,"height":600}}
```

The above illustrates field types only. Confidence and text must come from the actual extractor. `detected_language` may be `und`, a metadata language, or a best-effort `en`/`hi`/`mr`. `extraction_details` is intentionally extensible: image dimensions/confidence/languages; audio model, nullable duration; PDF `pages` with page number/text/method, total/processed pages; URL title, URL, publisher, author, publication date and date-provenance note. An unreadable image may return empty text plus readability warnings; `/api/verify` rejects blank text. A wholly unreadable PDF produces an error; a mixed PDF can return usable pages plus explicit OCR-unavailable warnings. Scanned/page-limited/truncated content must be surfaced by the UI before checking. Preserve extraction metadata locally when posting its text for verification; `/api/verify` does not reconstruct page coordinates or duration from text.

PDF details now include `chunks: [{chunk_id, page_number, text, page_start, page_end, boundary_split}]`, `full_text_chars`, `text_is_preview` and `coverage`. Offsets address that page's normalized text. Top-level `text` remains a compatible bounded preview: when `text_is_preview` is true, review and check **every chunk**, retaining its page number locally. Chunks prefer sentence/paragraph boundaries and overlap at hard cuts; deduplicate repeated anchored claims in presentation. Documents beyond the configured character/chunk budget return `413 document_too_large` before model calls. Pages beyond `MAX_PDF_PAGES` remain explicitly unprocessed; split the original document to check those pages. A full-page OCR failure is visible in `pages[].method` and warnings.

URL details include explicit `published_at`, `updated_at`, nullable `event_date` (never inferred), `date_provenance`, `content_complete`, `full_text_chars`, `coverage` and returned-text chunks (`start`, `end`). Truncated pages use `coverage: extracted_text_only`; the missing article body is not recoverable from the returned preview. `content_complete` means no known restriction/truncation was detected; it cannot prove all content was present on a dynamic site. Restricted or unreadable article content and low-readability source PDFs cannot establish decisive verdicts. Keep `article_content_incomplete`, truncation and source-page warnings visible.

Verification details can include `verification_cache: hit|miss` and `cache_age_seconds`. The cache is bounded, in memory per worker, cleared on restart and disabled with `VERIFICATION_CACHE_TTL_SECONDS=0`. Keys include exact normalized full text, language, audience, jurisdiction, UTC day, model and processing limits; input format alone can differ. IDs, evidence and original timestamps are retained. Partial/failed/discarded-assessment results are never cached. A cache hit may serve a recent as-of result during quota exhaustion; it is not a new search.

## Explain without reclassification

Verdict guards require complete reviewed directly relevant fetched support for verified and explicit contradiction for false. Weak, snippet-only, incomplete or irrelevant opposition stays visible but cannot alone negate decisive support. Partially_true requires separate exact claim components with attributed supported and contradicted/not-established assessments; misleading_context requires decisive context evidence. Outdated retains historical/current event-date witnesses rather than inferred publication dates. Model/search failures are explicit HTTP errors or `status: partial` plus warning codes, never a completed technical failure disguised as factual uncertainty. Components are internal model-validation details; public response schemas are unchanged.

For adult English, validated `grounded_explanation` is reused directly, reducing decisive single-claim text verification to two Gemini attempts and audio to three before retries. Hindi/Marathi and other audiences retain the existing wording provider. Each live attempt, including retries and failures, counts against the acceptance budget; cache hits use the original result/source timestamps and must not be described as fresh retrieval.

URL metadata also includes `text_encoding`. Unicode BOMs and declared HTTP/HTML charsets are decoded consistently; strictly valid UTF-8 is preferred over stale legacy declarations. `text_encoding_loss` signals undecodable bytes and `content_complete=false`; such source content cannot establish a decisive verdict. Audio errors preserve safe internal provider category/status and expose Retry-After where supplied without changing the public error JSON. Error messages distinguish transient provider unavailability from timeout.

Final acceptance consumed one Gemini attempt and zero Tavily searches: audio failed with upstream HTTP 503 at transcription; the factual counterclaim was SKIPPED after the provider failure. All six category fixtures and their immutable English/Hindi/Marathi fields passed offline. Backend integration is READY WITH BLOCKERS; live audio reliability and decisive-verdict accuracy remain unvalidated. Person 2 should check extraction HTTP status before posting text, retain extraction warnings/metadata, display partial-provider warnings, and never show a failed extraction as successful verification.

`ExplainRequest` is `{result: <complete VerificationResult>, language: "en"|"hi"|"mr", audience: "child"|"teen"|"adult"|"senior"}`. Audience defaults to adult. Return type is the same `VerificationResult`.

Only the wording fields `explanation`, `short_summary`, `key_points`, `next_step` inside each claim and top-level `response_language`, `audience`, `summary` may change. Everything else—including claim/evidence IDs, verdict, stances, URLs, excerpts, dates, original statements, grounded explanation, risk, warnings and limitations—is copied unchanged. Translation uses no search and does not create a new verification timestamp. This stateless API trusts the supplied result's provenance; Person 2 should use the actual server result/persisted trusted record. A translation provider failure returns a structured error, so retain the prior wording. Verification itself can return localized conservative fallback wording with `status: partial`.

## Empty, missing evidence and errors

| Case | Result |
|---|---|
| Blank text / invalid language or audience / missing file | `422 validation_error`; no raw forwarded text in error details |
| Greetings/opinions only | `200`, `status: no_checkable_claims`, `claims: []`, localized summary |
| Search returns no usable results | `200`, claim verdict `unconfirmed`, `evidence: []`, warning `no_usable_evidence_retrieved`; never false merely for absence |
| Some search/source/assessment/explanation operations fail | `200`, `status: partial`, warning codes and limitations; unsupported conclusions remain unconfirmed |
| No Gemini key for claim extraction | `503 llm_unavailable`; service still boots |
| Gemini quota/authentication/model access | `503 llm_quota_exhausted`, `llm_rate_limited`, `llm_auth_error`, `llm_model_unavailable`; retain prior results |
| Gemini operation timeout | `504 llm_timeout`; downstream assessment failures can instead appear in `200 partial` |
| No search key after extraction | `200 partial`, per-claim unconfirmed, `search_unavailable`; no fake ledger |
| Missing OCR/transcription/FFmpeg runtime | `503 ocr_unavailable`, `transcription_unavailable`, `ffmpeg_unavailable` or language-capability error |
| Claim extraction provider fails/invalid output | `502 llm_provider_error`, `llm_output_invalid` or `claim_span_invalid` |
| Private URL / credentials / disallowed scheme | `400 unsafe_url` |
| Oversized upload/body/page/document | `413 upload_too_large`, `request_too_large`, `url_too_large`, `document_too_large` or dimension error |
| Wrong format | `415 unsupported_media` / `url_content_unsupported` |
| Corrupt/unreadable input or too many redirects | `422` with format-specific error |
| Public download failure / DNS failure | `502 url_fetch_error` / `url_dns_error` |
| External public-page/request deadline | `504 url_timeout` / `request_timeout` |
| Unexpected server error | `500 internal_error`, sanitized message |

Unified error shape:

```json
{"error":{"code":"llm_unavailable","message":"Set GEMINI_API_KEY to extract or check claims.","request_id":"17c1c65c-47f4-4f82-9329-5d5df8b511c4"}}
```

Validation errors can additionally contain `details: [{location: ["body", "response_language"], type: "literal_error"}]`. `details` may be absent or null. UI handling must check HTTP status and `error`, preserve prior results on failure, and show qualified unconfirmed results distinctly from false results. Health reports configured capabilities and installed dependencies, not proof of key validity or provider uptime.

Quota/rate-limit errors expose integer seconds in the HTTP `Retry-After` header, allowed through CORS; the JSON error shape is unchanged. Disable automatic immediate resubmission. Daily `RESOURCE_EXHAUSTED`/429 responses are not retried. Short transient guidance is honored within `PROVIDER_MAX_RETRY_WAIT_SECONDS`; longer guidance returns immediately and blocks further model calls locally until the advised cooldown. Without provider guidance, daily errors use a conservative one-hour local cooldown, not a promised reset time. Audio and verification share the gate for the same model. Downstream quota failures remain `200 partial` with warning codes; subsequent claims preserve uncertainty and skip further searches. Gate/cache state is process-local and does not survive restart.

Invalid model JSON/local schema validation and malformed provider envelopes use existing `llm_output_invalid`; connections/request rejections/transient server failures remain `llm_provider_error` with distinct sanitized messages. Backend diagnostics correlate failure stage and provider HTTP status with `X-Request-ID`, including failures inside `200 partial`. These internal diagnostics do not alter the public response schema. The selective acceptance report captures them without keys, prompts, offending values, provider bodies or raw exception text. An unreadable social source warning does not imply that the input article failed; retain per-source provenance and limitations.

## HTTP and PowerShell examples

From the repository root; no API key goes in these browser-facing requests:

```powershell
$base = 'http://127.0.0.1:8000'
Invoke-RestMethod "$base/api/health"
$payload = @{text='From Monday all ₹500 notes are invalid.'; input_language='auto'; response_language='hi'; audience='adult'; jurisdiction='IN'} | ConvertTo-Json
$result = Invoke-RestMethod "$base/api/verify" -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($payload))
$urlBody = @{url='https://www.rbi.org.in/scripts/FS_FAQs.aspx?Id=136&fn=2753'} | ConvertTo-Json
$extracted = Invoke-RestMethod "$base/api/extract/url" -Method Post -ContentType 'application/json' -Body $urlBody
$mediaPayload = @{text=$extracted.text; input_type=$extracted.input_type; response_language='mr'} | ConvertTo-Json
# Check $extracted.warnings and let the user review extracted text first.
Invoke-RestMethod "$base/api/verify" -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($mediaPayload))
$explainBody = @{result=$result; language='mr'; audience='senior'} | ConvertTo-Json -Depth 30
Invoke-RestMethod "$base/api/explain" -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($explainBody))
curl.exe -X POST "$base/api/extract" -F 'file=@backend/demo-output/fixtures/forward.png'
curl.exe -X POST "$base/api/extract" -F 'file=@backend/demo-output/fixtures/forward.pdf'
curl.exe -X POST "$base/api/extract" -F 'file=@backend/demo-output/fixtures/voice-hi.wav'
```

PowerShell 7 additionally supports `Invoke-RestMethod "$base/api/extract" -Method Post -Form @{file=(Get-Item '.\backend\demo-output\fixtures\forward.png')}`. Windows PowerShell 5.1 users should use `curl.exe` for multipart; do not use the `curl` alias. With browser `FormData`, omit a manual Content-Type header so the browser supplies the multipart boundary.

```http
POST /api/verify HTTP/1.1
Content-Type: application/json

{"text":"A factual forward to check","response_language":"en"}
```

Regenerate schemas after backend model changes with `Set-Location backend; .\.venv\Scripts\python.exe -m scripts.export_openapi`.

## Next.js handoff

For local direct browser requests, set `NEXT_PUBLIC_TRUTHLENS_API_URL=http://127.0.0.1:8000` in Person 2's app and allow its exact origin in backend `CORS_ORIGINS` (default includes `http://localhost:3000`). API keys remain exclusively in backend `.env`. The base URL is public; the provider keys are secrets. The following is an integration example, not a frontend file modification:

```typescript
const base = process.env.NEXT_PUBLIC_TRUTHLENS_API_URL ?? "http://127.0.0.1:8000";
async function api(path: string, init: RequestInit = {}) {
  const response = await fetch(`${base}${path}`, { ...init, cache: "no-store" });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error?.message ?? "Request failed");
  return body;
}
const form = new FormData();
form.append("file", selectedFile);
const extracted = await api("/api/extract", { method: "POST", body: form });
// Show extracted.text and warnings for review/editing before checking.
const result = await api("/api/verify", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ text: extracted.text, input_type: extracted.input_type,
    input_language: "auto", response_language: "hi", audience: "adult" }),
});
const marathi = await api("/api/explain", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ result, language: "mr", audience: "senior" }),
});
```

For pasted text, call `/api/verify` directly; for URLs, first call `/api/extract/url` with `{url}`. Allow enough browser/proxy time for the backend's 180-second request deadline. Render `partial` results and warning/limitation fields visibly. Retain prior results on an error, including provider quota errors. Do not automatically loop failed requests or rerun verification just to switch languages; use `/api/explain`. Handle HTTP 503, 504 and `200 partial` separately. CORS disallows credentials and wildcard origins; cross-machine deployment needs reachable base URLs, exact origins and HTTPS.

The backend now uses official Gemini Interactions structured output and audio transcription, with `store=False` and full local Pydantic validation. WAV/MP3 duration defaults to 300 seconds; OGG conversion processes at most the first 300 seconds and warns. MP3 validation requires FFprobe; OGG requires FFmpeg. Inline audio is additionally capped at 14 MiB after conversion. Audio metadata includes actual validated duration, Gemini model, and best-effort language identification. Image confidence is not a guarantee of correct recognition. Extraction and immutable evidence metadata should remain stored alongside any user edits by Person 2.

Tavily defaults to one basic query per claim with a short-lived bounded cache. Health flags indicate configured keys and local runtimes; they do not establish current service availability. Unconfirmed explanations are deterministic in en/hi/mr; live generated translation of decisive verdicts remains pending validation. See [validation report](../backend/validation-report.md) for actual acceptance status and the daily Gemini quota blocker. The exact OpenAPI artifact remained byte-for-byte unchanged through this migration; health's extensible capabilities/dependencies gained Gemini/FFprobe details.

<!-- GENERATED SCHEMAS -->

## Generated exact schemas

References resolve against `components.schemas` in backend-openapi.json. This appendix is generated from the application, not handwritten.

### Body_extract_api_extract_post

```json
{
  "properties": {
    "file": {
      "type": "string",
      "contentMediaType": "application/octet-stream",
      "title": "File",
      "description": "PNG/JPEG, PDF, WAV, MP3 or OGG/Opus. Format is detected from bytes, not the filename."
    }
  },
  "type": "object",
  "required": [
    "file"
  ],
  "title": "Body_extract_api_extract_post"
}
```

### ClaimResult

```json
{
  "properties": {
    "claim_id": {
      "type": "string",
      "format": "uuid",
      "title": "Claim Id"
    },
    "claim_text": {
      "type": "string",
      "maxLength": 1200,
      "title": "Claim Text"
    },
    "original_span": {
      "type": "string",
      "maxLength": 3000,
      "title": "Original Span"
    },
    "entities": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "title": "Entities"
    },
    "dates": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "title": "Dates"
    },
    "qualifiers": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "title": "Qualifiers"
    },
    "normalized_claim": {
      "type": "string",
      "title": "Normalized Claim"
    },
    "lexical_hash": {
      "type": "string",
      "title": "Lexical Hash"
    },
    "verdict": {
      "type": "string",
      "enum": [
        "verified",
        "false",
        "partially_true",
        "outdated",
        "misleading_context",
        "unconfirmed"
      ],
      "title": "Verdict"
    },
    "grounded_explanation": {
      "type": "string",
      "maxLength": 1800,
      "title": "Grounded Explanation"
    },
    "explanation": {
      "type": "string",
      "maxLength": 2500,
      "title": "Explanation"
    },
    "short_summary": {
      "type": "string",
      "maxLength": 350,
      "title": "Short Summary"
    },
    "key_points": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "title": "Key Points"
    },
    "evidence": {
      "items": {
        "$ref": "#/components/schemas/Evidence"
      },
      "type": "array",
      "maxItems": 10,
      "title": "Evidence"
    },
    "risk": {
      "$ref": "#/components/schemas/Risk"
    },
    "temporal_context": {
      "$ref": "#/components/schemas/TemporalContext"
    },
    "original_context": {
      "$ref": "#/components/schemas/OriginalContext"
    },
    "limitations": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "title": "Limitations"
    },
    "next_step": {
      "type": "string",
      "title": "Next Step"
    },
    "checked_at": {
      "type": "string",
      "format": "date-time",
      "title": "Checked At"
    }
  },
  "additionalProperties": false,
  "type": "object",
  "required": [
    "claim_text",
    "original_span",
    "entities",
    "dates",
    "qualifiers",
    "normalized_claim",
    "lexical_hash",
    "verdict",
    "grounded_explanation",
    "explanation",
    "short_summary",
    "evidence",
    "risk",
    "temporal_context",
    "original_context",
    "limitations",
    "next_step",
    "checked_at"
  ],
  "title": "ClaimResult"
}
```

### ErrorBody

```json
{
  "properties": {
    "code": {
      "type": "string",
      "title": "Code"
    },
    "message": {
      "type": "string",
      "title": "Message"
    },
    "request_id": {
      "type": "string",
      "format": "uuid",
      "title": "Request Id"
    },
    "details": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/components/schemas/ErrorDetail"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "title": "Details"
    }
  },
  "additionalProperties": false,
  "type": "object",
  "required": [
    "code",
    "message",
    "request_id"
  ],
  "title": "ErrorBody"
}
```

### ErrorDetail

```json
{
  "properties": {
    "location": {
      "items": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "integer"
          }
        ]
      },
      "type": "array",
      "title": "Location"
    },
    "type": {
      "type": "string",
      "title": "Type"
    }
  },
  "additionalProperties": false,
  "type": "object",
  "required": [
    "location",
    "type"
  ],
  "title": "ErrorDetail"
}
```

### ErrorResponse

```json
{
  "properties": {
    "error": {
      "$ref": "#/components/schemas/ErrorBody"
    }
  },
  "additionalProperties": false,
  "type": "object",
  "required": [
    "error"
  ],
  "title": "ErrorResponse"
}
```

### Evidence

```json
{
  "properties": {
    "evidence_id": {
      "type": "string",
      "format": "uuid",
      "title": "Evidence Id"
    },
    "title": {
      "type": "string",
      "maxLength": 500,
      "title": "Title"
    },
    "url": {
      "type": "string",
      "maxLength": 2048,
      "title": "Url"
    },
    "publisher": {
      "type": "string",
      "maxLength": 300,
      "title": "Publisher"
    },
    "source_type": {
      "type": "string",
      "enum": [
        "primary",
        "secondary",
        "fact_check",
        "other"
      ],
      "title": "Source Type"
    },
    "published_at": {
      "anyOf": [
        {
          "type": "string",
          "maxLength": 100
        },
        {
          "type": "null"
        }
      ],
      "title": "Published At"
    },
    "updated_at": {
      "anyOf": [
        {
          "type": "string",
          "maxLength": 100
        },
        {
          "type": "null"
        }
      ],
      "title": "Updated At"
    },
    "retrieved_at": {
      "type": "string",
      "format": "date-time",
      "title": "Retrieved At"
    },
    "stance": {
      "type": "string",
      "enum": [
        "supports",
        "contradicts",
        "context",
        "neutral",
        "unclear"
      ],
      "title": "Stance",
      "default": "unclear"
    },
    "excerpt": {
      "type": "string",
      "maxLength": 5000,
      "title": "Excerpt"
    },
    "excerpt_provenance": {
      "type": "string",
      "enum": [
        "fetched_page",
        "search_excerpt",
        "fact_check_api"
      ],
      "title": "Excerpt Provenance"
    },
    "what_source_says": {
      "type": "string",
      "title": "What Source Says",
      "default": ""
    },
    "authority_basis": {
      "type": "string",
      "title": "Authority Basis"
    },
    "relevance_score": {
      "type": "number",
      "title": "Relevance Score",
      "default": 0
    },
    "directly_relevant": {
      "type": "boolean",
      "title": "Directly Relevant",
      "default": false
    }
  },
  "additionalProperties": false,
  "type": "object",
  "required": [
    "title",
    "url",
    "publisher",
    "source_type",
    "retrieved_at",
    "excerpt",
    "excerpt_provenance",
    "authority_basis"
  ],
  "title": "Evidence"
}
```

### ExplainRequest

```json
{
  "properties": {
    "result": {
      "$ref": "#/components/schemas/VerificationResult"
    },
    "language": {
      "type": "string",
      "enum": [
        "en",
        "hi",
        "mr"
      ],
      "title": "Language"
    },
    "audience": {
      "type": "string",
      "enum": [
        "child",
        "teen",
        "adult",
        "senior"
      ],
      "title": "Audience",
      "default": "adult"
    }
  },
  "additionalProperties": false,
  "type": "object",
  "required": [
    "result",
    "language"
  ],
  "title": "ExplainRequest"
}
```

### ExtractionResult

```json
{
  "properties": {
    "text": {
      "type": "string",
      "title": "Text"
    },
    "detected_language": {
      "type": "string",
      "title": "Detected Language"
    },
    "input_type": {
      "type": "string",
      "enum": [
        "text",
        "image",
        "audio",
        "pdf",
        "url"
      ],
      "title": "Input Type"
    },
    "warnings": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "title": "Warnings"
    },
    "extraction_details": {
      "additionalProperties": true,
      "type": "object",
      "title": "Extraction Details"
    }
  },
  "additionalProperties": false,
  "type": "object",
  "required": [
    "text",
    "detected_language",
    "input_type"
  ],
  "title": "ExtractionResult"
}
```

### HealthResponse

```json
{
  "properties": {
    "status": {
      "type": "string",
      "const": "ok",
      "title": "Status"
    },
    "capabilities": {
      "additionalProperties": true,
      "type": "object",
      "title": "Capabilities"
    },
    "dependencies": {
      "additionalProperties": {
        "type": "boolean"
      },
      "type": "object",
      "title": "Dependencies"
    },
    "limits": {
      "additionalProperties": {
        "type": "integer"
      },
      "type": "object",
      "title": "Limits"
    },
    "notes": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "title": "Notes"
    }
  },
  "additionalProperties": false,
  "type": "object",
  "required": [
    "status",
    "capabilities",
    "dependencies",
    "limits",
    "notes"
  ],
  "title": "HealthResponse"
}
```

### OriginalContext

```json
{
  "properties": {
    "status": {
      "type": "string",
      "enum": [
        "not_checked",
        "inconclusive",
        "found"
      ],
      "title": "Status",
      "default": "not_checked"
    },
    "notes": {
      "type": "string",
      "title": "Notes",
      "default": ""
    },
    "source_urls": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "title": "Source Urls"
    }
  },
  "additionalProperties": false,
  "type": "object",
  "title": "OriginalContext"
}
```

### Risk

```json
{
  "properties": {
    "score": {
      "type": "integer",
      "maximum": 100.0,
      "minimum": 0.0,
      "title": "Score"
    },
    "level": {
      "type": "string",
      "enum": [
        "low",
        "medium",
        "high"
      ],
      "title": "Level"
    },
    "factors": {
      "items": {
        "$ref": "#/components/schemas/RiskFactor"
      },
      "type": "array",
      "title": "Factors"
    },
    "is_probability": {
      "type": "boolean",
      "const": false,
      "title": "Is Probability",
      "default": false
    },
    "label": {
      "type": "string",
      "title": "Label",
      "default": "Forwarding caution heuristic; not a probability that a claim is false."
    }
  },
  "additionalProperties": false,
  "type": "object",
  "required": [
    "score",
    "level",
    "factors"
  ],
  "title": "Risk"
}
```

### RiskFactor

```json
{
  "properties": {
    "rule": {
      "type": "string",
      "title": "Rule"
    },
    "weight": {
      "type": "integer",
      "title": "Weight"
    },
    "description": {
      "type": "string",
      "title": "Description"
    }
  },
  "additionalProperties": false,
  "type": "object",
  "required": [
    "rule",
    "weight",
    "description"
  ],
  "title": "RiskFactor"
}
```

### TemporalContext

```json
{
  "properties": {
    "claim_date": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Claim Date"
    },
    "relevant_source_dates": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "title": "Relevant Source Dates"
    },
    "notes": {
      "type": "string",
      "title": "Notes",
      "default": ""
    }
  },
  "additionalProperties": false,
  "type": "object",
  "title": "TemporalContext"
}
```

### URLRequest

```json
{
  "properties": {
    "url": {
      "type": "string",
      "maxLength": 2048,
      "minLength": 1,
      "title": "Url"
    }
  },
  "additionalProperties": false,
  "type": "object",
  "required": [
    "url"
  ],
  "title": "URLRequest"
}
```

### VerificationResult

```json
{
  "properties": {
    "verification_id": {
      "type": "string",
      "format": "uuid",
      "title": "Verification Id"
    },
    "status": {
      "type": "string",
      "enum": [
        "completed",
        "partial",
        "no_checkable_claims"
      ],
      "title": "Status"
    },
    "input": {
      "$ref": "#/components/schemas/ExtractionResult"
    },
    "claims": {
      "items": {
        "$ref": "#/components/schemas/ClaimResult"
      },
      "type": "array",
      "maxItems": 12,
      "title": "Claims"
    },
    "summary": {
      "type": "string",
      "title": "Summary"
    },
    "checked_at": {
      "type": "string",
      "format": "date-time",
      "title": "Checked At"
    },
    "warnings": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "title": "Warnings"
    },
    "response_language": {
      "type": "string",
      "enum": [
        "en",
        "hi",
        "mr"
      ],
      "title": "Response Language"
    },
    "audience": {
      "type": "string",
      "enum": [
        "child",
        "teen",
        "adult",
        "senior"
      ],
      "title": "Audience"
    }
  },
  "additionalProperties": false,
  "type": "object",
  "required": [
    "status",
    "input",
    "claims",
    "summary",
    "checked_at",
    "response_language",
    "audience"
  ],
  "title": "VerificationResult"
}
```

### VerifyRequest

```json
{
  "properties": {
    "text": {
      "type": "string",
      "maxLength": 50000,
      "minLength": 1,
      "title": "Text"
    },
    "input_language": {
      "type": "string",
      "enum": [
        "auto",
        "en",
        "hi",
        "mr"
      ],
      "title": "Input Language",
      "default": "auto"
    },
    "response_language": {
      "type": "string",
      "enum": [
        "en",
        "hi",
        "mr"
      ],
      "title": "Response Language",
      "default": "en"
    },
    "audience": {
      "type": "string",
      "enum": [
        "child",
        "teen",
        "adult",
        "senior"
      ],
      "title": "Audience",
      "default": "adult"
    },
    "jurisdiction": {
      "type": "string",
      "pattern": "^[A-Z]{2}$",
      "title": "Jurisdiction",
      "default": "IN"
    },
    "input_type": {
      "type": "string",
      "enum": [
        "text",
        "image",
        "audio",
        "pdf",
        "url"
      ],
      "title": "Input Type",
      "default": "text"
    }
  },
  "additionalProperties": false,
  "type": "object",
  "required": [
    "text"
  ],
  "title": "VerifyRequest"
}
```
