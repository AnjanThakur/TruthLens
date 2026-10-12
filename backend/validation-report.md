# Backend implementation and validation record

## Final provider-free regression — 12 October 2026

**PASS:** full backend pytest **350 tests**, Ruff, mypy **47 source files**;
frontend **59 offline tests**, lint and TypeScript; adapter **140 offline tests**
and Ruff. Existing OpenAPI compatibility regressions pass. Native OCR/media tests
run locally; provider responses are fixtures. The runtime test harness now uses
an isolated environment mapping, preventing newly introduced runtime secrets and
test storage paths from leaking into subsequent alert tests. Windows sandbox
event-loop hangs were resolved by rerunning offline tests in the approved host
context, without relaxing application safeguards.

The canonical preview is now `http://localhost:3001`. The WHO optional-source fix,
callback no-cache handling and encrypted retention regression are implemented.
No new live factual result was generated. Real hosted history/reviewer/isolation/
cleanup/review/withdrawal checks remain **BLOCKED**; owner-reported sign-in is not
an independently validated session. See [final integration handoff](../docs/final-integration-20261012.md).

This phase: **0 Gemini, 0 Tavily, 0 WhatsApp sends**, four read-only Twilio GETs,
zero hosted writes. The account is active Trial, current sender differs from the
documented legacy Sandbox, and the existing Body-only failure remains 400/21654.
The old dynamic-send artifacts are absent; an account/sender transition cannot
be proven. Dynamic WhatsApp remains **BLOCKED** and is handed to the teammate.

## Provider-free hosted integration follow-up — 11 October 2026

Continued from feature commit `f0b0fce`; actual statuses and blockers are recorded
in [the hosted follow-up](../docs/hosted-integration-followup.md) and
[its acceptance JSON](../docs/hosted-integration-acceptance-20261011.json).

The WHO partial-status cause was a blanket source-page warning rule. Retrieval
failure provenance now distinguishes optional unreviewed snippet sources from
required/incomplete investigation. A guarded decisive verdict can complete with
an optional source warning still visible; trusted-source failure, missing excerpts,
SSRF rejection, interrupted search and model errors remain partial. Existing
citation/verdict/date guards, warning-free cache eligibility and alert ingestion
gates are unchanged. Eight offline retrieval regressions and a durable encrypted
retention regression cover the changes; no live verification was rerun.

Targeted backend pytest: **192 PASS**. Frontend targeted authentication/history/RLS/
consent tests: **24 PASS**. Ruff, mypy, frontend lint/typecheck/build: **PASS**.
Preview 3001, existing site 3000, provider-disabled backend and publishing-disabled
alert health: **PASS**. Callback redirects now explicitly prevent caching.
Hosted signed-in callback, owner reviewer authorization, real history mutations,
two-user isolation, cron execution and authenticated alert review/withdrawal:
**BLOCKED** pending legitimate browser sessions, authentic unexpired receipts,
administrator inspection and explicitly confirmed mutations. Anonymous access
denial is verified; 404/PGRST205 on an anonymous reviewer probe is inconclusive
about table existence. No hosted grants or writes were made. Gemini/Tavily/Twilio
requests: **0/0/0**; WhatsApp worker paused and dynamic delivery **BLOCKED**.

## Latest full-system implementation (11 October 2026)

**New approved live result:** one WHO text check through the actual website used **2 Gemini / 2 Tavily / 0 Twilio**. Grounded `verified` from two fetched WHO sources and website rendering **PASS**; strict complete-pipeline **FAIL** because a non-decisive Wikipedia page failed DNS resolution, leaving `status=partial`. No retry or second submission was made; controlled instances were stopped. See [actual result](../docs/live-website-acceptance-20261011.json). The pre-approval baseline and earlier records below are retained as history.


**PASS:** 334 backend tests, Ruff (app/tests/scripts), mypy 47 files and pip check. Reviewed institution and contradiction investigation, safe page caching with original retrieval timestamps, original-message date context, quota/attempt ceilings and isolated encrypted alert persistence are implemented. Four deterministic before/after avoidable-abstention scenarios now resolve; guard decision remains mandatory. All six labels pass the independent 14-case fictional policy set (50% abstention), not a real-model accuracy benchmark. Exact original OpenAPI schemas/endpoints remain unchanged.

**PASS:** actual safe WHO constitution URL extraction, HTTP 200 / 2,330 characters / explicit original date / no warnings; this spends no Gemini/Tavily credit and is not a factual verdict. **NOT TESTED:** fresh provider-backed five-format or website factual acceptance. Latest earlier audio record remains **FAIL**, transient-server transcription error; mocked 503 recovery and daily-quota fail-fast regressions pass. New phase usage **0 Gemini / 0 Tavily / 0 Twilio**.

See [actual full-system report](../docs/final-full-system-acceptance.md), [startup and selective acceptance](../docs/windows-startup.md), and [avoidable comparison](evaluation/avoidable-results.json). Hosted reviewer table is **BLOCKED** (404/PGRST205); authenticated Supabase history/alerts are not claimed live PASS. The sections below retain earlier run evidence and counts for historical context.


Repair runs: **11 October 2026**, Windows PowerShell, Python **3.14.7**. Only `backend/` and `docs/` are in scope. Frontend, Person 2's database and WhatsApp were not changed.

**Final Person 1 status: READY WITH BLOCKERS.** Code and offline quality gates pass. Existing text/image/PDF/URL workflow acceptance is preserved. Final live audio failed with Gemini HTTP 503, so live audio recovery and decisive-verdict accuracy remain unvalidated. Final-pass consumption: **one Gemini attempt, zero Tavily searches**, within the hard five/two ceilings. Remaining live work stopped immediately; no extra credits were requested.

## Current status

| Check | Status | Evidence |
|---|---|---|
| Automated regressions | PASS | 195 tests, zero skipped; all previous 172 retained and 23 final-pass cases added. Cloud HTTP responses are mocked; native OCR/PDF/audio and article parsing execute locally |
| Ruff lint and formatting | PASS | `ruff check app tests scripts`; `ruff format --check app tests scripts` |
| mypy | PASS | 34 application files, no issues |
| Public OpenAPI compatibility | PASS | Regression compares the exact exported bytes, including Windows line endings; endpoint/request/response schemas unchanged |
| Screenshot repair | PASS | Native OCR → partial-search/page fixtures → exact ledger and conservative uncertainty |
| Scanned-PDF repair | PASS | Native scanned OCR, bounded chunks/page offsets, oversize rejection, incomplete Gemini fixture rejection |
| URL/backend follow-up | PASS | Reproduced latest assessment failures offline; semantic HTML fallback, JS-only detection, PDF responses, safe redirects, source/date metadata and provider diagnostics. This does not establish new live acceptance |
| Independent runner reporting | PASS | URL HTTP verification failure and non-JSON response both allow subsequent audio PASS in offline fixtures; selected inputs are recorded before interruption; quota/budget stop tests remain intact |
| Quota/retry/cache behavior | PASS | Daily 429 single attempt, shared cooldown, transient retry guidance, expiry, no secret leakage, TTL/concurrent/cache isolation and failed-result exclusions |
| Six verdict evidence guards | PASS | Fictional retrieved HTTP fixtures cover all six categories; absent/weak/incomplete sources cannot establish decisive verdicts. This is not broad real-world accuracy validation |
| Final audio live check | FAIL | 05:49 UTC, upstream Gemini HTTP 503 at transcription; exact result below |
| Final live verified/false acceptance | SKIPPED | No actual claim/evidence could be obtained for audio; counterclaim stopped after provider failure |
| Earlier full live acceptance | FAIL | Screenshot, scanned PDF and URL produced partial results; original ignored artifact retained |
| WhatsApp, Google Fact Check API, durable jobs/persistence | NOT IMPLEMENTED | Outside Person 1 repair scope |

## Final pass: implementation, verdict audit and actual live result

The final request authorized at most five Gemini attempts and two Tavily searches after offline checks, followed by a scoped Git commit/push. All live cloud calls in this final pass are recorded in ignored `demo-output/final-person1-20261011.json`, started **2026-10-11 05:49:34 UTC**. No provider preflight or five-format rerun was performed.

| Final acceptance input | Extraction | Actual claim / evidence / verdict | Status / consumption |
|---|---|---|---|
| English WAV `final-issuer.wav`, locally generated Windows speech: “One rupee notes in India are issued by the Government of India.” | **FAIL**, `/api/extract` returns existing `502 transcription_provider_error`; sanitized diagnostic `transcription / transient_server / llm_provider_error / provider_http_status=503`, request ID `8f1d041e-b2ff-4fb7-b555-f8968fe7b989` | No transcript or claim accepted, no evidence retrieval, no verdict. This is a synthetic spoken fixture, not human/private audio or a mocked live transcript | **FAIL**, one Gemini attempt, zero Tavily searches |
| Text counterclaim: “One rupee notes in India are issued by the Reserve Bank of India.” | Not needed; verification was never attempted | No claim extraction, sources, verdict or rationale fabricated | **SKIPPED** after provider failure, zero requests |

The runner's expected verified/false categories are test assertions only, never inputs forcing the classifier. They were not established live. Four Gemini attempts/two searches remained unused because repeated calls after this 503 would waste the limited budget. No quota error occurred in this final attempt; actual remaining daily quota was not queried.

### Corrections and offline evidence

- **PASS — retry-aware budgets:** Gemini and Tavily reserve each individual HTTP attempt before sending it, including failed attempts and retries. Exhausted budgets reject the next call locally. Mocked three-attempt providers with a budget of one prove no second HTTP request occurs. Final-mode validation rejects ceilings above five/two before provider initialization. Ordinary runner errors still allow independent inputs outside final mode; final mode stops on transient server/timeout/authentication/connection errors.
- **PASS — complete audio pipeline:** production Gemini adapter/actual FastAPI routes plus deterministic mocked HTTP cover WAV → Unicode transcript → anchored claims → attributed source retrieval → verified result → English/Hindi/Marathi wording. Actual FFmpeg/FFprobe WAV/MP3/OGG-Opus conversion, PCM validation and duration tests pass. Existing invalid-audio, unavailable-provider, 503 recovery/backoff/Retry-After, timeout, daily quota, authentication, invalid-envelope/JSON and sanitization regressions remain green.
- **PASS — query specificity:** prior URL workflow PASS meant the pipeline completed, not that its factual claim was verified. Saved evidence was general Wikipedia, the RBI homepage's exchange-rate table and `rbi.com` Restaurant Brands International. None directly established ₹1 legal tender, so unconfirmed was correct for that ledger. For Indian rupee/banknote claims the first bounded query now targets `site:rbi.org.in`, expanding bare RBI to Reserve Bank of India; other cross-check queries remain. No topic-specific verdict is hardcoded.
- **PASS — conflict guard:** unreviewed, irrelevant, snippet-only or incomplete opposing sources no longer erase direct complete reviewed support merely by having a contradictory stance. Their attributed excerpts and stances remain visible. A genuine conflict among complete, directly relevant reviewed sources still yields unconfirmed.
- **PASS — qualified verdict guards:** partially_true now requires separate non-overlapping exact claim spans with supported and contradicted/not-established component assessments. Established components need decisive trusted source attribution; invented spans/references are rejected with explicit technical warnings. Genuine component qualification is not mistaken for whole-claim disagreement. Misleading_context requires a decisive context stance. Existing outdated chronology/source-date guards remain conservative: two actual source event-date witnesses, current assertion, no publication-date substitution.
- **PASS — fewer model calls:** for adult English the already-validated grounded Decision explanation is reused directly, with immutable verdict and evidence, instead of generating it again. Typical decisive text check uses two Gemini attempts, audio three; retries still count against ceilings. Other audiences and Hindi/Marathi keep the existing wording adapter. URLs in explanation/key points outside the ledger are rejected. Technical failures remain explicit HTTP errors or `status: partial` with warning codes, never a completed factual success.

| Deterministic source-attributed scenario | Offline result | Scope |
|---|---|---|
| Direct support | **PASS — verified** | Relevant complete fetched fixture, exact source quote/URL/timestamp retained |
| Direct contradiction | **PASS — false** | Explicit contrary fetched statement, not absence of an announcement |
| Supported fact plus false/unsupported qualification | **PASS — partially_true** | Anchored components and attributed decisive sources; missing/overlapping/unattributed/invented components rejected |
| Previously valid but obsolete | **PASS — outdated** | Historical/current dated excerpts from distinct trusted sources; publication dates alone rejected |
| Material omitted context | **PASS — misleading_context** | Decisive context evidence; support-only proposal rejected |
| Insufficient evidence | **PASS — unconfirmed** | Empty/weak/irrelevant sources do not imply false |
| Gemini/Tavily failure | **PASS — explicit technical error** | HTTP error or partial result with provider warning; no completed uncertainty concealing a dependency failure |

All six verdict fixtures additionally verify English/Hindi/Marathi re-explanation preserves every immutable field, including verdict, evidence IDs/URLs/excerpts/stances, dates, checked_at, risk and limitations. These are fictional offline fixtures, not six real-world live accuracy validations. The older next-Monday ₹500 forward remained correctly unconfirmed because retrieved 2016–2017 material did not establish a current future announcement.

Quality gates: **195 pytest PASS / zero skipped**, Ruff lint and formatting **PASS** (57 files), mypy **PASS** (34 app files), `pip check` **PASS**, FastAPI health/Swagger/OpenAPI startup **PASS**, exact exported OpenAPI bytes **PASS**, security/SSRF/source-grounding tests **PASS**. Configured-secret scan finds no credential value in intended unignored backend/docs files; `.env`, local native runtimes, environments, generated reports and all audio fixtures are ignored. No frontend/Person 2/Supabase/tracker/radar/Meta files were edited. Non-fatal Starlette/httpx and Google SDK typing deprecations remain.

Handoff is ready for backend integration with blockers explicitly visible: live Gemini audio availability; live decisive-verdict acceptance/accuracy; human review of multilingual wording. Provider failures cannot be fixed by pretending transcription succeeded, forcing a verdict or using new keys to evade project quota. Git target: existing `main` → `origin/main` at the existing TruthLens repository; only Person 1 backend/tests/docs are intended for staging. Final commit and verified push outcome are reported separately after Git review.

## Earlier audio and Unicode follow-up: actual evidence

Inspected saved `demo-output/acceptance-20261011T052429704146Z.json` and `demo-output/acceptance-20261011T052710644997Z.json`. Sanitized captured diagnostics establish these outcomes:

| Workflow | Actual root cause | Fix / regression result |
|---|---|---|
| URL at 05:24 UTC | **PASS** extraction and verification. Combined URL/audio run: three Gemini HTTP requests, one Tavily request | Supersedes the earlier URL failure below. No new URL live rerun during this repair |
| Audio at 05:24 UTC | **FAIL** at transcription: upstream HTTP **503**, `transient_server`, request ID `210feaa9-277a-4489-beac-e204da46f750`; API returns existing `502 transcription_provider_error`. Live runner allows only one attempt | Production already defaults to two attempts (maximum three), 0.5/1-second bounded backoff, SDK retries disabled. Confirmed mocked 503 recovery with identical WAV resubmission through production adapter. Fixed ignored server Retry-After: short guidance honored within wait cap; long guidance returns immediately with Retry-After without an early retry. **PASS offline** |
| Audio-only at 05:27 UTC | **FAIL** at transcription: `llm_timeout`, HTTP **504**, request ID `eef65503-94da-42a5-bf28-a0f54a0f2842`; one Gemini request, zero Tavily requests | Separate from the 503. Timeout remains one bounded attempt to avoid repeating potentially completed work. Audio messages now distinguish temporary server unavailability from timeouts. **PASS offline**; provider recovery **SKIPPED live** |
| Audio wrapper | Dropped `category`, `provider_status`, `retry_after_seconds`; advised shorter WAV even for temporary server failure | Preserve internal diagnostics and Retry-After, existing public code/status/error shape. Request-linked logs contain stage/category/numeric upstream status, never keys/raw provider messages/speech. **PASS offline**, including FastAPI error/header contract |
| Unicode HTML fallback | lxml parsed undeclared UTF-8 bytes using a legacy fallback, corrupting ₹/Devanagari text and titles even when primary trafilatura extraction worked | Decode once before primary/fallback/metadata parsing; honor Unicode BOMs, prefer strictly valid UTF-8 over stale legacy declarations, otherwise honor HTTP/HTML charsets. Preserve charset in safe fetcher and use same decoding for plain-text URL and evidence ledger. **PASS offline**: Hindi/Marathi/₹, precision/fallback, missing/stale charset, UTF-8/16/32 BOMs, Windows-1252 |
| Unrecoverable encoding | Invalid bytes could silently be replaced without incomplete-content warning | Return `text_encoding_loss`; record `text_encoding` and `content_complete=false` in existing extensible metadata. Ledger treats affected sources as incomplete, preventing decisive verdicts. **PASS offline** |

Focused coverage: `tests/test_audio_unicode_repairs.py`, **23 cases**. Full offline results: **172 passed, zero skipped**, Ruff lint/format **PASS** (56 files), mypy **PASS** (34 application files). Exact exported OpenAPI bytes are unchanged. Existing SSRF, source grounding, quota and runner isolation tests remain green. Repair usage: **zero live Gemini / zero live Tavily requests**. Frontend, database, Person 2 files and Meta integration were not edited.

The selective live runner retains its one-attempt credit ceiling; offline audio regressions exercise production retry policy. No timeout, authentication or invalid-output retry was added. Repeated daily quota errors still fail before new model work. Invalid/unsupported encodings are flagged rather than guessed; already-corrupted publisher content cannot be restored reliably.

## Earlier supplied live acceptance: exact diagnosis

Inspected `demo-output/acceptance-20261011T044352197204Z.json` (started **2026-10-11 04:43:52 UTC**), plus its two preceding acceptance reports. Its actual totals are **six Gemini HTTP requests and two Tavily HTTP requests**. Text, image and PDF are PASS; image/PDF reused the recent successful text verification cache. **Audio was reached and is explicitly FAIL**, rather than absent: its actual Gemini transcription succeeded, then `/api/verify` failed. Later PDF and URL were still attempted. The runner already continued after ordinary HTTP errors; it previously lacked protection against unexpected local exceptions/malformed responses.

| Stage | Actual observed result | Root cause / evidence limit |
|---|---|---|
| Submitted URL extraction | PASS: `https://www.rbi.org.in/scripts/FS_FAQs.aspx?Id=136&fn=2753`, title `ISSUER OF CURRENCY`, 39,502 extracted characters; compatible 24,000-character preview with `extraction_text_truncated` | Valid readable RBI HTML was returned. Preview truncation was visible; it did not prevent selection of the literal test sentence. No publication/modified/event date was explicitly established, so dates remained null |
| URL claim extraction | PASS: `₹1 notes issued by Government of India are also Legal Tender.` was extracted and anchored | The failed URL verification was not an initial article or claim-extraction failure |
| Retrieved source extraction | Primary RBI FAQ `https://www.rbi.org.in/Commonperson/english/Scripts/FAQs.aspx?Id=3158` and Wikipedia `https://en.wikipedia.org/wiki/Indian_rupee` supplied fetched excerpts. Instagram `https://www.instagram.com/reel/DVsU6Ilkj-K?hl=en` retained a search snippet | `source_page_unavailable:url_no_text` refers to the Instagram evidence page, **not the submitted RBI URL**. Its original raw HTML was not saved, so JavaScript-only behavior cannot be proven retrospectively. JS-only shells are now explicitly detected and covered by a fixture; no browser execution or access-control bypass was added |
| URL evidence assessment | FAIL: `llm_provider_error`, limitations explicitly say assessment failed, final `partial/unconfirmed` | The Decision generation/validation stage failed after evidence retrieval. Old handling conflated HTTP provider rejection/server errors, connections and invalid JSON/schema output. The report stores only the warning code, not the underlying provider HTTP status/body, so its exact upstream subcause cannot be recovered |
| Audio extraction | PASS: actual transcription `All 500-rupee notes will become invalid next Monday.`, duration 4.254 seconds | Audio decoding/transcription was not the failed stage |
| Audio verification | FAIL: `/api/verify` error request ID `58a8d5ba-ff52-4a45-a8e5-a43c0ca9b2b7`, `llm_provider_error`, message `Gemini could not complete this request. Check provider configuration and retry.` | That exact old message comes from the SDK API-error branch during initial claim extraction, which also included SDK response-envelope validation errors. It is distinct from old quota, authentication, timeout and local model-JSON validation messages. The original status was discarded, so client rejection, transient server failure or an invalid SDK envelope remains unknown; no claim/search result was produced |

No retained backend `.log`/stdout/stderr files were found in the workspace, backend, demo-output or temporary-file locations inspected. Existing request logging recorded only request ID/method/status/duration, and downstream assessment failures could be hidden behind HTTP 200. No missing historical exception/status has been invented.

### Implemented follow-up fixes and relevant tests

- **PASS — provider classification and observability:** invalid model JSON/local Pydantic validation and malformed provider envelopes now use existing `llm_output_invalid`, rather than generic `llm_provider_error`. Connection failures, upstream request rejection and transient server failures have distinct sanitized messages/diagnostic categories. Existing quota/auth/model/timeout codes and retry limits remain. Allow-listed diagnostics identify claim extraction, evidence assessment, wording or transcription, with request ID, numeric provider HTTP status when known, and safe validation issue types. No raw exception strings, payloads, URLs, headers, keys or offending values are logged. Local validation failures are never retried.
- **PASS — faithful latest-workflow reproduction:** actual FastAPI extraction/verification routes plus real local HTML parsing and mocked cloud/public HTTP reproduce readable RBI input, an unreadable social source and an assessment HTTP 503 or invalid JSON. Both remain conservative partial/unconfirmed; diagnostics distinguish the assessment failures. A separate valid-assessment test preserves a grounded primary-source verdict despite the social-page failure, while retaining `partial` and its warning. These are offline reconstructions, not new live RBI/Instagram observations.
- **PASS — bounded article handling:** precision and recall extraction remain; an additional local semantic `<article>`/`<main>`/`articleBody` DOM fallback excludes scripts, menus, hidden content and forms. No JS is executed and no extra network resource is fetched. Empty layout-table rows are removed without dropping cell text. Explicit dates and source links remain. The parser is not passed the request URL, preventing third-party extraction warnings from logging URL queries; actual URLs remain in response metadata.
- **PASS — URL safety/PDF behavior:** each public redirect still re-resolves and validates every DNS answer, pins the validated IP and preserves Host/TLS. Tests verify final/original URL and explicit publication-date preservation. Supported PDF signatures are routed through existing PDF validation even when served as octet-stream or mislabeled HTML; other binary content is rejected. Existing private/mixed-IP/redirect/size/deadline regressions still pass.
- **PASS — independent runner results:** comma-separated CLI order is preserved; all selected entries are saved before any operation. Ordinary HTTP failures, non-JSON responses and unexpected per-input exceptions produce FAIL for that input and allow the next input. An interruption leaves remaining inputs explicitly SKIPPED. Quota/rate/budget exhaustion still stops further paid calls and marks remaining inputs SKIPPED. Each report now includes stage, request IDs, HTTP statuses and bounded sanitized diagnostic events. Reports remain unique and earlier artifacts are preserved.

That earlier follow-up added `tests/test_url_acceptance_repairs.py` (15 cases) and `tests/test_provider_diagnostics.py` (nine cases): **149 passed, zero skipped; Ruff lint/format PASS; mypy PASS, 33 files; exact public OpenAPI bytes unchanged.** Its repair-time live testing was **SKIPPED**. The later saved report at 05:24 UTC establishes URL **PASS**; historical failures remain here for traceability.

### Minimal selective live commands, only when quota is available

From `D:\HackOnTrack-TruthLens\backend`, select just the needed format:

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_live --live --quota-available --formats url --model-budget 3 --search-budget 1
.\.venv\Scripts\python.exe -m scripts.validate_live --live --quota-available --formats audio --model-budget 4 --search-budget 1
```

Or test both independently in one bounded process, URL first:

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_live --live --quota-available --formats url,audio --model-budget 7 --search-budget 2
```

An ordinary URL failure will not suppress audio. A global quota/budget stop will deliberately SKIP it. No full five-format rerun or extra preflight is necessary. Audio requires `demo-output/fixtures/voice-en.wav`; missing input is reported SKIPPED. Unique `acceptance-<UTC timestamp>.json` files record actual outcomes/counters and sanitized stage diagnostics. The URL still checks only the literal disclosed FAQ sentence, not every claim in the whole article. An unreadable evidence page can correctly keep full acceptance FAIL even if another source establishes a claim.

## Three earlier failures: prior repair history

The table below preserves the original repair observations before the latest supplied acceptance. Its SKIPPED live statuses describe that earlier repair run, not the newer text/image/PDF PASS results above.

| Format | Exact earlier failure and root cause | Implemented repair | Test outcome |
|---|---|---|---|
| Screenshot | OCR was exact (confidence 96.3). Tavily returned RBI, YouTube and Wikipedia; a publisher page was unreadable, resulting in `source_page_unavailable:url_no_text` and `partial`. Search success did not mean all retrieved pages were readable | Keep valid partial search hits and warn on discarded malformed items; validate ledger values/canonical links; prioritize primary publishers within the relevance threshold; preserve exact snippets when public pages fail. Snippets/unreviewed/incomplete content cannot establish decisive verdicts. Skip pointless assessment if no complete reviewed source is available; never synthesize a citation | **PASS offline**: actual screenshot OCR, unreadable pages, partial Tavily response, invalid ledger, source ranking and uncertainty. **SKIPPED new live**; external pages can still fail and correctly produce partial results |
| Scanned PDF | OCR extracted the sentence, but RBI/Facebook/PRS retrieval included an unreadable page and Gemini returned incomplete structured output (`llm_output_invalid`). Larger PDFs also exposed the compatible top-level text cap as an incomplete document preview | Retain normalized per-page OCR/text, confidence/readability warnings and bounded page-context chunks. Top-level preview truncation is explicit; later claims remain available in chunk metadata. Prefer sentence boundaries; overlap hard cuts. Validate byte/character/chunk/page limits before model work. Anchor and deduplicate chunk claims; use compact source windows and full Pydantic validation. Incomplete/malformed answers are rejected without repair retries; unreliable source OCR cannot support decisive verdicts | **PASS offline**: native scanned PDF through production Gemini adapter with mocked incomplete response, later-page retention, overlaps/exact offsets, text/byte/chunk budgets and low-readability evidence. **SKIPPED new live**; no guarantee that a future Gemini response will complete |
| Public URL | RBI FAQ extracted 39,502 characters and was capped to 24,000. Original runner checked a disclosed 1,200-character prefix, yielding two claims/six sources, claim-cap omission, `evidence_date_invalid` and `llm_timeout`. Inferred article dates could incorrectly label historical pages with today's date. Date checking against the subsequently shortened assessment quote could reject a date present elsewhere in the original fetched window. Read/connect timeouts were classified as generic fetch errors | Separate bounded URL/model deadlines, return `504 url_timeout`, validate article text/access shells and permit one local recall fallback. Read explicit published/modified meta/JSON-LD separately; never infer an event date. Flag restricted/truncated content and retain coverage information. Validate model dates/temporal witnesses against the original retrieved evidence before transactionally accepting shortened quotes. The selective runner checks one disclosed literal FAQ sentence. Existing every-hop DNS validation, IP pinning, Host/TLS and proxy defenses remain | **PASS offline**: timeout with pinned Host/IP, metadata separation, ignored inferred date, recall fallback, restricted article guard, truncated URL preview and legitimate date outside a selected quote. Existing SSRF/security tests pass. **SKIPPED new live** |

Regression files: `tests/test_workflow_repairs.py`, `tests/test_quota_cache.py`, `tests/test_verdict_grounding.py` and `tests/test_acceptance_runner.py`, plus all earlier tests. No fixture source is represented as an actual RBI/PIB statement. Production never imports test providers.

## Quota and credit controls

Daily `RESOURCE_EXHAUSTED`/HTTP 429 is recognized without repeated retries. An earlier provider diagnostic reported a 20-request/day free-tier limit and a 5h27m44s retry hint; that is historical guidance, not proof of present availability. The newer supplied acceptance is recorded above. SDK automatic retries remain disabled.

Short transient `Retry-After` or Google `RetryInfo` guidance is honored within the configured wait budget (default three seconds). For 429, longer guidance returns immediately and blocks new calls locally until cooldown expiry. Server errors such as 503 also honor short guidance; long guidance returns without an early retry and preserves Retry-After, without classifying it as daily quota. Missing daily guidance uses a one-hour local cooldown, not a promised provider reset. HTTP errors retain the same JSON schema and expose integer-seconds `Retry-After` through CORS. Same-model audio and verification share the gate. Assessment **or wording** quota errors stop subsequent claim searches while preserving prior grounded results and uncertain remaining claims.

Successful exact-input checks are cached for at most 120 seconds (32 entries, per worker, restart clears memory), keyed by normalized full text, language, audience, jurisdiction, UTC day, model and limits. Different formats can reuse identical text. Original IDs/evidence/check timestamps remain, with hit/age metadata. Partial/failed/discarded-assessment results are not cached; concurrent identical checks share a success. Set TTL to zero to disable. Tavily's existing bounded 900-second query cache remains. No semantic similarity or stale long-term fact cache was added.

Source windows default to 3,000 characters to bound assessment prompts. No cloud assessment occurs for snippets-only, unreviewed or known incomplete ledgers. Unconfirmed wording remains deterministic in English/Hindi/Marathi. Missing evidence never means false; conflicts remain visible. Outdated still requires literal chronological historical/current event-date witnesses from two distinct trusted fetched sources. Guards cannot prove the semantics of every model interpretation.

## Earlier actual live results, preserved

The earlier production-provider run used actual FastAPI ASGI routes, two claims/three sources, a 60-second external and 300-second request deadline. Its report is retained at ignored `demo-output/live-validation.json`; repair tests have not overwritten it.

| Input | Extraction | Earlier full check | Actual recorded result |
|---|---|---|---|
| Plain ₹500 forward | PASS | PASS | One claim, three retrieved sources, completed **unconfirmed** |
| English screenshot | PASS | FAIL | Exact OCR, one claim/three sources, partial because a source page was unreadable |
| English WAV | PASS | PASS | Actual 4.2536-second Windows TTS speech, transcript “All 500-rupee notes will become invalid next Monday.”; one claim/three sources, completed unconfirmed |
| Scanned PDF | PASS | FAIL | OCR sentence, one claim/three sources, unreadable source and incomplete AI output |
| RBI public FAQ | PASS | FAIL | Actual fetched article with truncation; selected prefix returned claim omission/date/timeout warnings |

Historical 2016 demonetisation sources did not establish the upcoming ₹500 change. The backend retained unconfirmed, never treating absence of proof as falsity or publication dates as event dates. Actual Hindi/Marathi explanations retained uncertainty and immutable evidence. Extra original Hindi/Marathi image fixtures were damaged by PowerShell pipe encoding; corrected native fixtures now pass OCR/language checks, while their corrected Gemini verification remains SKIPPED. Native results remain in ignored `demo-output/native-validation.json`. Earlier Tavily usage was seven basic HTTP requests including preflight; monthly balance/billed credits were not queried. Repair-run live usage is **zero Gemini / zero Tavily**.

## Full suite reference (not needed for this follow-up)

Use the minimal URL/audio commands above for this follow-up. The original five-format defaults remain available for a future full acceptance run; this command is reference only:

```powershell
Set-Location D:\HackOnTrack-TruthLens\backend
.\.venv\Scripts\python.exe -m scripts.validate_live --live --quota-available
```

Defaults cover **plain text, screenshot, WAV, scanned PDF and public URL**, English only, one claim/three sources, one provider attempt per operation, model timeout 60 seconds/URL 15 seconds/request 180 seconds. Maximum **12 Gemini HTTP requests and five Tavily searches**. Exact successful repeated extracted text can reuse its short cache; metadata and original timestamps disclose this. Public URL verifies only a literal FAQ sentence found in the actual extraction, recorded as `verification_scope`; this is not whole-article acceptance.

The runner records actual request counts and results to a unique ignored `demo-output/acceptance-<UTC timestamp>.json` after each input, retaining earlier reports. Quota/rate/budget errors stop the suite and mark remaining cases SKIPPED. Missing fixtures are SKIPPED. A partial pipeline is FAIL for complete acceptance even when its conservative verdict is correct. Exit codes: 0 all PASS; 1 any FAIL; 2 SKIPPED without FAIL. Optional format/model/search/language flags narrow or expand the explicit scope. No actual live rerun followed the latest repair; append the timestamped selective outcome after an authorized available-quota run.

Required local fixtures are `banknote.png`, `banknote-scanned.pdf` and `voice-en.wav`. Existing WAV is audible Windows-generated speech, not a human recording or a mocked transcript. `scripts.make_demo_fixtures` creates images/PDF locally without API calls; real Hindi/Marathi speech still needs samples. Do not run extra provider preflight immediately before this bounded suite.

## Person 2 handoff and limits

Public FastAPI endpoints, Pydantic schemas and exported OpenAPI are unchanged. New information uses existing extensible `extraction_details`, warning strings and response headers. Person 2 should retain extraction/page metadata, review OCR text, verify all page chunks when `text_is_preview` is true, display partial/missing-source warnings, show the original cache timestamp and respect quota cooldown without immediate resubmission. Full details are in [the API contract](../docs/backend-api-contract.md).

Article completeness on dynamic/paywalled sites cannot be proven. OCR confidence is not correctness. Bounded chunks can require manual page splits, and claim caps may omit assertions with visible warnings. The authority registry and literal ISO-date requirement are deliberately conservative. Corrected multilingual screenshot live verification, real multilingual audio, decisive-verdict generated translations, human language review and broad fact-check accuracy remain SKIPPED/unvalidated.

The backend has no durable history, public authentication/rate gateway, worker isolation or WhatsApp integration. Cache/gate memory is per process. Native parser threads need deployment resource limits. No frontend/database changes were made.

Earlier startup/Swagger/CORS/pip checks passed. Current offline endpoint tests cover startup, health, CORS and security behavior; the exact OpenAPI export is rechecked. Third-party Starlette/httpx, typing and tld deprecation warnings remain non-fatal. No actual credential is present in tracked/unignored backend/docs files; `.env` is ignored. The earlier session exposed credentials from a misused `.env.example`, subsequently cleaned; **key rotation remains required and was not verified during this repair run**.
