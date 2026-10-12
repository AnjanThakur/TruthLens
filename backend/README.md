# TruthLens AI — Person 1 backend

FastAPI implements extraction → atomic claims → Tavily evidence → per-source assessment → English/Hindi/Marathi explanations. Person 2 owns frontend, Supabase, history, tracker, radar and Meta setup. The Gemini migration preserves endpoint names and the exact public OpenAPI schema.

See [API contract](../docs/backend-api-contract.md), [OpenAPI](../docs/backend-openapi.json), and [validation report](validation-report.md). **READY WITH BLOCKERS:** 195 offline tests, Ruff, mypy, dependency/startup/security and exact OpenAPI checks pass. Final live audio failed at transcription with Gemini HTTP 503; counterclaim skipped immediately. Final-pass usage: one Gemini attempt, zero Tavily searches. Prior text/image/PDF/URL workflow PASS does not establish general fact-check accuracy.

## Independent scam alert engine

The optional `app.alerts_app:app` service consumes consented verified claim records, clusters EN/HI/MR variants, detects sample recurrence, and prepares evidence-gated drafts with human review and manual export. It makes no provider calls by default and uses a transactional local memory repository. Run separately on port 8001; the existing verification app and OpenAPI remain unchanged. See [Person 2 integration and demo](../docs/scam-alert-integration.md), [alerts OpenAPI](../docs/scam-alert-openapi.json), and [feature validation](alerts-validation-report.md). No Supabase changes or WhatsApp publishing are included.

## Run on this machine

The existing virtualenv, ignored `.env`, installed native runtimes and local OCR language data are ready:

```powershell
Set-Location D:\HackOnTrack-TruthLens\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Swagger: `http://127.0.0.1:8000/docs`; health: `http://127.0.0.1:8000/api/health`. Health reports configuration/local dependencies, not provider authentication or remaining quota.

A fresh checkout requires Python 3.11+ (validated here on 3.14.7):

```powershell
Set-Location D:\HackOnTrack-TruthLens\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
if (-not (Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }
# Edit .env locally: GEMINI_API_KEY, TAVILY_API_KEY, CORS_ORIGINS.
```

Keep secrets only in `.env` or server environment variables, never `.env.example`, browser code or `NEXT_PUBLIC_*`. Rotate the existing keys because an earlier template read exposed them in tool output. The template is now clean and `.env` is ignored.

## Gemini and Tavily

All model functionality uses Google's official **google-genai 2.29.0** SDK and **Interactions API**: claim extraction, evidence assessment, wording and transcription. Default `GEMINI_MODEL=gemini-3.8-flash`; blank `GEMINI_AUDIO_MODEL` uses the same model. The SDK is pinned because its Interactions errors/retries differ from the legacy generation client.

Core requests now explicitly use Google's stable `v1` route. `GEMINI_API_VERSION=v1beta` is an optional compatibility setting; it is not an automatic fallback. The model and private credentials are unchanged. Stable routing is supported by [Google's API version reference](https://ai.google.dev/gemini-api/docs/api-versions); it is not a guarantee against model overload.

The adapter expands schema references and sends a supported JSON subset, with omitted length/item bounds expressed as instructions. Every response still passes full Pydantic validation, including bounds and rejection of extra fields. Incomplete output, invented evidence references, untraceable dates and non-verbatim quotes are rejected. Requests use `store=False`; provider processing/retention policies still apply. References: [Google structured outputs](https://ai.google.dev/gemini-api/docs/structured-output), [audio](https://ai.google.dev/gemini-api/docs/audio), [Interactions](https://ai.google.dev/gemini-api/docs/interactions-overview).

Malformed envelopes/model JSON and local schema failures use `llm_output_invalid`. Sanitized `truthlens.diagnostics` events distinguish quota, timeout, authentication, connection, request rejection, transient server failure and validation. Events include stage/request ID/numeric HTTP status when known; validation reports issue types only. Raw exceptions, provider bodies, prompts, headers, URL queries and keys are excluded. Audio errors retain internal provider classification/status and HTTP Retry-After, with specific temporary-server/timeout advice. The selective runner captures these events in its ignored timestamped report so future partial HTTP 200 failures can be diagnosed.

Server errors (including 503) honor short Retry-After guidance within the configured wait cap; longer guidance returns without an early retry and preserves the Retry-After header. Production defaults to two attempts, while the live runner intentionally uses one to limit credits. Downloaded webpage content is decoded consistently before primary extraction, semantic fallback and metadata parsing, preserving ₹, Hindi and Marathi. Existing extraction metadata records `text_encoding`; undecodable bytes produce `text_encoding_loss` and incomplete content, which cannot support a decisive verdict.

Without explicit provider guidance, transient retries use 1/2-second exponential delays plus up to 250 ms jitter, within the existing wait/attempt/request-budget caps. After bounded server-error retries fail, the shared model client locally stops follow-up calls for `PROVIDER_SERVER_COOLDOWN_SECONDS` (default 15), or longer when Retry-After requires it. Errors retain `llm_provider_error`, HTTP 502, the sanitized upstream status and Retry-After. Cooldown expires automatically and does not fabricate a successful response. It applies across transcription and verification for the affected model only; it is separate from the daily quota gate. Stable Interactions `quota_exceeded` is recognized as daily exhaustion without requiring the word “daily” in the provider message.

Daily `RESOURCE_EXHAUSTED`/429 errors never retry. The shared model quota gate returns `503 llm_quota_exhausted` with HTTP `Retry-After` and stops verification/audio calls locally until cooldown expiry. A missing provider reset hint uses a one-hour local cooldown, not a promised reset. Transient rate-limit guidance is respected within `PROVIDER_MAX_RETRY_WAIT_SECONDS` (default 3); longer guidance returns immediately with `llm_rate_limited`. Other transient failures are bounded by `PROVIDER_MAX_ATTEMPTS` (default 2, maximum 3). Generated SDK retries are disabled. Timeouts/incomplete/invalid output are not retried. Initial extraction failures return structured HTTP errors; downstream failures preserve partial unconfirmed results, skip subsequent searches after quota errors, and never invent citations.

Tavily defaults to **basic search, one query per claim**, no answer/raw-content generation. Successful queries, including empty results, have a bounded 900-second/128-entry memory cache; concurrent identical requests share results. Failures are not cached. Cache is per worker, cleared on restart; different model queries may miss it. `/api/explain` uses no search. Monthly account balance was not measured. See [Tavily search reference](https://docs.tavily.com/documentation/api-reference/search).

Successful verification also has a bounded 120-second/32-entry per-worker cache, keyed by exact normalized full input, language/audience/jurisdiction, UTC day, model and processing limits. Format alone may differ. Concurrent identical checks share a success. Failed/partial/discarded-assessment results are not cached; cache hits retain original IDs, evidence and `checked_at`, with age/hit metadata. Disable with `VERIFICATION_CACHE_TTL_SECONDS=0`. Model assessment is skipped when only snippets, unreviewed or known incomplete sources exist; deterministic unconfirmed wording requires no model call.

[.env.example](.env.example) lists all settings: keys/models, CORS, timeouts, text/upload/page/claim/source caps, query/cache limits, executable paths and OCR languages. Environment variables override `.env`.

## Media and runtimes

Adult English uses the already-validated grounded assessment explanation directly, avoiding an additional model call. Hindi/Marathi and other audiences keep the wording adapter; verdict, evidence, dates and limitations remain immutable. The first Indian-currency search targets the actual RBI domain to avoid unrelated acronym results. Partially-true verdicts require anchored attributed components, misleading-context verdicts require actual context evidence, and weak/irrelevant opposition cannot erase directly assessed support. See the validation report for the six-category offline audit and live limitations.

| Input | Actual extraction | Requirements |
|---|---|---|
| Text | NFC/whitespace normalization; exact original spans | Gemini + Tavily for checking |
| PNG/JPEG | Tesseract OCR with confidence/readability warnings | Tesseract + eng/hin/mar data |
| WAV | PCM validation, original-language Gemini transcription | Gemini |
| MP3 | FFprobe validation, Gemini transcription | FFprobe + Gemini |
| OGG/Opus in OGG | FFmpeg to mono 16 kHz WAV, then same transcriber | FFmpeg + Gemini |
| PDF | PyMuPDF embedded text, per-page OCR fallback, bounded page-context chunks | Tesseract for scanned pages |
| Public HTML/text/PDF URL | IP-pinned safe fetch, article/PDF extraction | Public network access |

Audio duration cap is 300 seconds; OGG processes only the first 300 seconds with a visible warning. Converted/inline audio is capped at 14 MiB to fit the provider's encoded request budget. M4A/MP4/FLAC/WebM and raw Opus outside OGG are unsupported. Native conversion success does not establish live transcription success.

Discovery checks PATH, standard Windows Tesseract and WinGet FFmpeg locations. Set `TESSERACT_CMD`, `FFMPEG_CMD`, `FFPROBE_CMD` for other installations. Invalid explicit paths do not fall back. `TESSDATA_DIR` overrides `backend/.runtime/tessdata`. Current machine supports **eng, hin, mar**; all were exercised with real OCR. Extraction language detection uses a script/word heuristic, model identification is best-effort. Marathi OCR had minor character errors despite high confidence; users must review extracted text.

PDF `text` stays a compatible preview capped by `MAX_TEXT_CHARS`. `extraction_details.chunks` retains text and offsets for every processed page within a bounded budget (default eight chunks of at most 6,000 characters). Prefer sentence boundaries; hard cuts overlap to retain nearby context. Oversized documents fail with `413 document_too_large`; pages beyond the page cap remain visibly unprocessed. Review OCR warnings and verify every chunk when the top-level preview is truncated, preserving page numbers locally. `/api/verify` automatically chunks submitted long text, anchors claims to the current chunk, deduplicates and reports claim-cap omissions. No endpoint automatically verifies omitted pages.

Ignored runtime data does not travel with a checkout. Install native executables on each deployment; provision OCR data from `backend/`:

```powershell
New-Item -ItemType Directory .runtime\tessdata -Force | Out-Null
Copy-Item -LiteralPath 'C:\Program Files\Tesseract-OCR\tessdata\eng.traineddata' -Destination .runtime\tessdata\eng.traineddata
Invoke-WebRequest 'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/hin.traineddata' -OutFile .runtime\tessdata\hin.traineddata
Invoke-WebRequest 'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/mar.traineddata' -OutFile .runtime\tessdata\mar.traineddata
```

Language data comes from the [official Tesseract repository](https://github.com/tesseract-ocr/tessdata_fast).

## Evidence and preserved behavior

Each claim has an independent ledger of retrieved URLs, reviewed publisher identities, nullable dates, exact excerpts, provenance and stance. Partial malformed Tavily responses preserve valid hits with warnings; primary publishers rank ahead of unreviewed hits within the relevance threshold. Unreviewed domains/search-only snippets and known incomplete or low-readability source content cannot establish decisive truth. Missing evidence never implies false. Conflicting sources remain visible. Evidence windows are bounded to reduce model input, and accepted quotes/dates must trace to the original retrieved window.

HTML parsing validates readable article content, permits local recall and semantic article/main DOM fallback, detects JS-only shells and rejects short access/captcha pages. Scripts are never executed. Empty layout-table rows are removed without losing cell text. PDF byte signatures use the existing PDF parser even for octet-stream/mislabeled HTML; other binary content is rejected. Original `source_url` and final `url` are retained through validated redirects. HTTP read/connect timeouts return `504 url_timeout`; separate optional URL/model timeouts fall back to the existing external deadline. Dates use explicit publisher meta/JSON-LD only: published and modified remain separate, event dates are never inferred. Restriction/truncation warnings are visible. Dynamic article completeness cannot be guaranteed; SSRF/IP pinning defenses remain intact.

Six verdicts remain `verified`, `false`, `partially_true`, `outdated`, `misleading_context`, `unconfirmed`. Outdated requires two distinct fetched historical/current sources with literal ISO event-date excerpts. This conservative requirement can leave historical claims unconfirmed.

`/api/explain` changes only presentation fields; IDs, verdicts, evidence, dates, limitations, risk and grounded English explanation remain exact. Unconfirmed wording is deterministic in all three languages to preserve uncertainty without another model call. Live generated translations of decisive verdicts and human language review remain unvalidated.

OTP/payment/identity/urgency/forwarding rules remain caution heuristics, not probabilities of fraud or falsity. Earlier-text lookup returns inconclusive unless dated retrieved text establishes a match; it does not prove first authorship or perform reverse-image forensics. SHA-256 lexical hooks do not provide semantic/cross-language clustering.

## Local and deliberate live checks

Local checks spend no Gemini/Tavily credits:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check app tests scripts
.\.venv\Scripts\python.exe -m ruff format --check app tests scripts
.\.venv\Scripts\python.exe -m mypy app --no-incremental
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m scripts.export_openapi
```

For managed Windows temporary-file restrictions:

```powershell
New-Item -ItemType Directory .tmp -Force | Out-Null
$env:TEMP = (Resolve-Path .tmp).Path
$env:TMP = $env:TEMP
```

Tests replace cloud providers only inside `tests/`; native OCR/PDF/audio and article parsing run for real when installed. They do not establish general fact-check accuracy.

After independently confirming quota availability and rotating the previously exposed keys, run the selective suite deliberately. It performs no availability probe first:

```powershell
.\.venv\Scripts\python.exe -m scripts.make_demo_fixtures
.\.venv\Scripts\python.exe -m scripts.validate_live --live --quota-available --formats audio --model-budget 4 --search-budget 1
```

The runner covers text, screenshot, WAV, scanned PDF and URL by default, English only, one claim/three sources, one model attempt per operation, and one disclosed literal sentence of the RBI FAQ. Default ceilings are **12 Gemini HTTP requests and 5 Tavily searches**, with explicit budget flags. It stops after quota/rate/budget errors, marking remaining inputs SKIPPED; `partial` is FAIL for complete acceptance. Exact repeated successful text can reuse the short cache, recorded with original timestamps. Actual request counts/results are saved to unique ignored `demo-output/acceptance-<UTC timestamp>.json` files, preserving earlier reports. Exit codes: 0 PASS, 1 any FAIL, 2 SKIPPED without FAIL. No fixed currency verdict is assumed.

For the remaining live failure, rerun only audio when quota is available using the command above. URL has a later saved PASS. The runner retains one attempt per model operation; offline regressions verify production's two-attempt 503 recovery. Ordinary HTTP/local input failures do not stop later selected formats; quota/budget stops still do. All selected formats exist in the report before operations begin, including unattempted SKIPPED entries on interruption. Stage, HTTP status, request IDs and sanitized provider diagnostics are recorded. Optional individual URL/audio commands remain in the validation report; a five-format rerun is unnecessary.

Required fixtures include `voice-en.wav` (existing actual audible Windows-generated speech), `banknote.png` and `banknote-scanned.pdf`. Missing fixtures are SKIPPED. Optional `--formats image,pdf,url` limits a rerun; `--languages en,hi,mr` adds wording checks and consumes extra calls for decisive verdicts. Corrected Hindi/Marathi screenshots are optional formats. Human speech and language review remain pending. The older `scripts.live_e2e` supplied-recording runner has no account-wide call budget; use the selective runner for this acceptance task.

## Limits and operational boundaries

Defaults: upload 10 MiB, URL 2 MiB, text 24,000 characters, eight PDF pages/claims/chunks, six evidence items, 20-second external operations, 180-second request deadline. Template suggests 30-second external calls; selective live runner uses model 60 seconds, URL 15 seconds, request 180 seconds and lower claim/source caps. Multipart bodies are bounded before parsing; JSON is 256 KiB, `/api/explain` 2 MiB. Truncation and failed pages are visible. Two checks run concurrently, claims sequentially. Long forwards can hit deadlines or quotas.

Public fetching validates every DNS answer/redirect, rejects private/reserved/multicast/loopback/link-local destinations, unsafe schemes, credentials and custom ports, and pins connections to validated public IPs while preserving Host/TLS checks and disabling ambient proxies. Uploaded names are never paths. Encrypted/attachment PDFs are rejected. Native parser threads need resource-limited workers for public deployment; also add authentication, gateway rate/cost limits and patched dependencies. There is no malware scanner.

Logs omit submitted content, keys and URL queries; keep `--no-access-log`. No content history is written to disk; cached queries/results remain briefly in memory. Explicit demo scripts save local results. Text/audio/evidence goes to Gemini, queries to Tavily, and publishers see public fetches.

WhatsApp, Google Fact Check Tools API, persistence, authentication gateway and durable jobs are **NOT IMPLEMENTED**. No Person 2 file or Meta account was changed.
