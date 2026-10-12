# Evidence assessment failure — 12 October 2026

## Confirmed historical diagnosis

The sanitized runtime log for backend instance
`03d8aed1-ba5d-4337-aef7-50fa2a79ba9d` records request
`4a7f2c77-a551-48d3-a69c-a547f7f2b345` failing at:

```json
{"stage":"evidence_assessment","category":"timeout","code":"llm_timeout"}
```

The file's last-write time was 07:11:20 UTC / 12:41:20 IST, consistent with the
reported approximately 12:40 check. Old events did not contain timestamps,
elapsed times or sizes. There is no recorded provider HTTP status, retry,
quota error or response-validation error for this assessment. This establishes
a timeout while waiting for assessment; it does not establish why the remote
response was slow or distinguish the SDK transport timeout from the outer
application attempt deadline. Increasing the timeout again is not justified.

The historical assessment payload is unavailable. No matching saved JSON was
found in the main checkout or feature worktree's demo-output, temporary-artifact
and docs locations. Partial reports are deliberately not kept in the successful
verification cache. The connected browser had no tabs. The report was not saved
to history, and no database access was attempted.

The owner's three reported sources were AP, The Hindu and TOI. These are owner
observations, not fresh fetch results in this investigation. No new source,
Gemini or Tavily request was made to reconstruct their missing historical text.

## Why copied excerpts were blank

The copy summary previously used only `what_source_says`. That field is filled
only after the assessment and quotation guards accept a result. The independent
`excerpt` field carries fetched page content and is included by the Gemini
request-building code; the page
rendered it inside a collapsed details element, but the copy summary omitted it.
Thus blank copied notes do not demonstrate blank Gemini input. Conversely, the
old "complete reviewed" label did not explicitly reject an empty excerpt, so
the historical label alone cannot prove that the three input excerpts were
nonempty or relevant. The actual historical text cannot be recovered or invented.

## Smallest justified changes

- Keep the model timeout at 45 seconds and total request deadline at 180 seconds.
- Stop asking Gemini to generate a second source paraphrase that the server
  always discarded. The internal provider schema now requests the verbatim
  quotation and factual assessment fields only; legacy paraphrases remain
  accepted but unused. All ID, quotation, relevance, contradiction, source,
  temporal and verdict guards remain.
- Remove search queries and default unassessed stance/relevance fields
  from the model input. Retain every supplied excerpt unchanged, its evidence
  ID, publisher, source type, publication/modified dates and provenance, plus
  completeness/subject/syndication flags. Original URLs stay in both the input
  and result ledger to preserve publisher and provenance context.
- Count instructions and response schema as well as data against the existing
  65,000-character prompt limit before reserving a model attempt. Current fixed
  decision instructions use 4,214 characters and schema uses 2,493 characters;
  the historical dynamic input/output size is unknown. The 16,384-token output
  ceiling is unchanged.
- Require nonempty text in the eligible-source gate and completeness flag;
  never label an empty fetched excerpt as complete in the UI.
- Log UTC timestamps, stage, safe error category, elapsed time, configured
  timeout, attempt/budget counts, evidence/eligible counts and input/schema/output
  character counts. Distinguish transport timeout from application deadline.
  Never log prompts, source text, URLs, credentials or full provider responses.
- Explain that evidence was retrieved but assessment failed, rather than
  describing unassessed evidence as weak. The UI no longer says it is awaiting
  assessment after terminal failure. Copying includes the fetched excerpt with
  its unassessed status, rather than a blank source note.

These changes remove confirmed unnecessary work and reporting defects. They
are not proof that the provider timeout has been eliminated.

## Offline evidence and controlled live capture

PASS: 429 backend tests and 65 frontend tests. Ruff (`app tests scripts`),
application mypy (48 files), frontend TypeScript and frontend lint all pass.
The backend run used the existing local eng/hin/mar Tesseract data. Tests use
mocked provider responses; no Gemini, Tavily or Twilio requests were made.

PASS: frontend production build. Reloaded only the owned feature website and
backend. Backend `/api/health` on port 8000, preview `/api/health` and homepage
on localhost:3001 each returned HTTP 200. Private configuration was preserved;
the existing provider keys remain enabled for user testing. The WhatsApp worker
and outbound delivery remain paused. Health checks do not verify live assessment.

New mocked SDK tests use three explicitly fictional source bodies. They assert
the exact nonempty excerpts, IDs, publication and modified dates inside the SDK's
actual HTTP request envelope. Cases include valid assessment, malformed JSON,
missing required fields, timeout, outer deadline, HTTP 503, 503 recovery, daily
quota and invented evidence IDs. Failed responses preserve source bodies and
remain Unconfirmed / Partial. No failure manufactures a verdict or quotation.

`backend/scripts/validate_assessment.py` was prepared before approval.
With explicit owner approval, it performs one English text verification of the
reported claim with enforced ceilings of **1 Gemini attempt, 2 Tavily attempts,
0 Twilio sends**, including retries. The isolated run disables retries and uses
the existing 45-second model deadline. It saves the prepared evidence payload,
actual result, safe diagnostics and actual attempt counts to a new private JSON
artifact, even when assessment fails. It never overwrites an existing report.
This provides the missing per-source audit data without placing article text in
routine application logs. A payload-ready event alone is not proof of a model
request; pair it with the request-started event and actual attempt count.

Example command, **only after approval**, from the feature backend directory:

```powershell
D:\HackOnTrack-TruthLens\backend\.venv\Scripts\python.exe -m scripts.validate_assessment --live --env-file D:\HackOnTrack-TruthLens\backend\.env --output demo-output/assessment-approved-20261012.json
```

## Approved live acceptance result

The owner approved one bounded test. It ran on 12 October 2026 from
14:19:53 to 14:20:23 UTC (19:49:53 to 19:50:23 IST), request ID
`92d03b7b-59b4-4322-8045-f2aed3667949`.

- PASS: actual usage **1 Gemini attempt, 2 Tavily attempts, 0 Twilio sends**;
  no retry. End-to-end duration approximately 30 seconds.
- PASS: six prepared evidence entries, three eligible fetched sources: AP
  (1,698 excerpt characters), TOI (3,000) and BBC (3,000). This fresh result
  differs from the historical AP/The Hindu/TOI set. Each eligible excerpt
  contains article-body discussion of the exact subject and event, not just a
  search title. Their IDs, URLs, dates and `fetched_page` provenance are present
  in the captured input. All six input excerpts and IDs match the output ledger.
  TOI/BBC are bounded excerpts, not a claim that their whole articles fit in the
  prompt. BBC has no publication date; its modified date remains distinct.
- PASS: request-started diagnostic confirms the assessment attempt with 19,169
  input characters, 4,214 instruction characters and 2,493 schema characters
  (25,876 total, below 65,000). The timeout remained 45 seconds.
- FAIL: Gemini returned **HTTP 503**, category **`transient_server`**, code
  **`llm_provider_error`**, elapsed **1,768 ms**. No response was available for
  structured validation. This is a new server failure, not the historical
  timeout and not evidence of malformed JSON, quota exhaustion or empty input.
- PASS: HTTP 200 partial report retained sources and warnings, with
  Unconfirmed verdict and explicit wording that evidence was retrieved but AI
  assessment failed. No definitive verdict or quotation was manufactured.
  Source extraction warnings (`url_no_text`, `source_content_incomplete`)
  remained visible and were not confused with the assessment failure.
- BLOCKED: successful real model assessment remains unverified because the
  approved attempt received a provider 503. The one-test budget is consumed;
  any further provider attempt requires fresh approval.

The private, Git-ignored artifact is
`backend/demo-output/assessment-approved-20261012-controlled.json`. It contains
the prepared source excerpts, result and sanitized diagnostics; no credentials
or signed receipt. Ordinary logs continue to exclude article text. No private
configuration, database or WhatsApp state was changed by this run.
