# Gemini 503 diagnosis and client recovery — 12 October 2026

## Confirmed cause and limits

The approved five-format report records three upstream Gemini HTTP 503 responses
at claim extraction (12,025 ms for text, 4,424 ms after audio transcription and
1,771 ms after URL extraction). The earlier approved assessment test also got
503 after 1,768 ms. The same configured `gemini-3.8-flash` model successfully
transcribed audio and completed two assessments within the five-format suite.
These events establish intermittent upstream server unavailability. They do
not establish a bad key, daily quota exhaustion, malformed model JSON or an
oversized request; failing claim-extraction prompts were small. Historical raw
provider messages were deliberately not retained, so the precise Google-side
capacity or infrastructure problem cannot be identified locally.

[Google's error reference](https://ai.google.dev/gemini-api/docs/api-errors)
defines 503 as temporary overload or downtime. Its
[retry guidance](https://ai.google.dev/gemini-api/docs/troubleshooting)
recommends bounded exponential backoff with jitter. The live suite intentionally
disabled retries according to the owner's approved budget, which explains why
an individual 503 ended each affected operation. Production already allowed two
attempts; retries alone are not a guarantee of recovery.

## Implemented changes

- Explicit stable `v1` Interactions routing instead of the SDK's implicit
  `v1beta`. [Google documents core Interactions as generally available in v1](https://ai.google.dev/gemini-api/docs/api-versions).
  Verified locally that pinned SDK 2.29 forwards HttpOptions.api_version into
  actual request routing. The configured model and schema are unchanged; beta
  routing remains an explicit compatibility option. This removes unnecessary
  reliance on the beta route; it does not prove beta caused the captured 503s.
- Bounded exponential retry waits (1/2 seconds plus 0–250 ms jitter); explicit
  Retry-After takes precedence. Existing maximum attempts, wait cap, 45-second
  per-attempt deadline and total request budget remain. An exhausted model
  attempt budget prevents both the next call and a pointless backoff wait.
- Per-model 15-second local cooldown after server-error attempts fail, respecting
  longer Retry-After. Follow-up text, assessment and audio calls fail locally
  with the existing sanitized error/status/header instead of repeatedly hitting
  the unavailable model. Expiry permits recovery; other models are unaffected.
  Cooldown is in process memory, not a distributed availability guarantee, and
  does not cancel requests already in flight.
- Keep daily quota fail-fast separate and highest priority. Recognize stable
  Interactions `quota_exceeded` as daily exhaustion even with generic wording.
- Safe diagnostics now include allow-listed API version, retry wait and
  Retry-After duration. No prompt, speech, keys or raw provider body is logged.

No model fallback, account upgrade, key replacement, larger timeout or relaxed
evidence guard was introduced. Private configuration, database and WhatsApp
state were preserved. Public endpoint schemas and error codes are unchanged.

## Validation

PASS: mocked real-SDK regressions cover v1 and explicitly selected v1beta
request URLs, Unicode input, structured response schema and store=False;
503 recovery, persistent 5xx cooldown/expiry, long Retry-After, model isolation,
daily quota priority, quota_exceeded without daily wording and attempt-budget
exhaustion without a retry wait. Existing audio, quote/provenance, invalid-output,
timeout and OpenAPI-contract regressions remain in the full suite.

PASS: **440 offline backend tests**, Ruff (`app tests scripts`) and application
mypy (48 files). No frontend or database files were changed for this repair.
PASS: owned backend restarted with effective `v1`, two maximum attempts,
15-second server cooldown and unchanged 45-second deadline. Backend and preview
health checks returned HTTP 200. These checks make no generation requests.

No Gemini/Tavily/Twilio calls were made during diagnosis or offline
implementation. The owner then approved one recovery smoke test with ceilings
of two Gemini attempts, zero Tavily calls and zero Twilio sends.

## Approved live recovery

PASS at **20:28:00–20:28:05 IST**, 12 October 2026, request ID
`077b0df1-eaea-450d-aea1-4c1cf7079361`: stable `v1` returned HTTP **200** on
the first attempt in approximately **5.8 seconds**. The response passed the
full ClaimBatch schema, extracted one WHO establishment-date proposition,
and preserved its exact original input span. Actual usage was **1 Gemini
attempt, 0 Tavily calls and 0 Twilio sends**, with no retry. No factual verdict
was generated or accepted by this provider smoke test.

Private Git-ignored capture:
`backend/demo-output/provider-recovery-20261012T145800133235Z.json`.
It includes actual output and safe route/status diagnostics. This confirms
the revised client works live now. It does not isolate whether stable routing
or a change in provider load caused recovery, promise continuous availability,
or relabel the earlier five-format failures as passing.
