# Restart and approved five-format acceptance — 12 October 2026

The owner requested a restart, all-format testing and a saved image result,
then explicitly approved one suite capped at 12 Gemini attempts, 5 Tavily
attempts and 0 Twilio sends, without retries or extra languages.

## Service and offline checks

PASS: restarted only the owned feature backend (8000) and website (3001).
Backend health, website health and homepage returned HTTP 200. Existing private
configuration was preserved; WhatsApp worker and outbound remain paused.
PASS: 67 targeted offline extraction, audio, URL, acceptance-runner and assessment
regression tests. Actual screenshot and scanned-PDF extraction through the
restarted HTTP service also returned 200 and 49 characters each, without warnings.

## Approved live suite

Ran from 14:41:44 to approximately 14:43:11 UTC (20:11:44–20:13:11 IST).
The existing acceptance runner exercised actual FastAPI routes in an isolated
ASGI application using production Gemini/Tavily providers, not browser clicks.
The current 45-second model deadline was retained; no settings file was edited.
The local demo fixtures contain the test assertion that all Rs 500 notes become
invalid next Monday. They are input prompts, not established facts. Audio uses
the existing locally generated spoken WAV fixture, not a human recording.

| Format | Extraction | Full live acceptance | Actual result | Gemini / Tavily attempts |
| --- | --- | --- | --- | --- |
| Text | Not a separate extraction operation | FAIL | Claim extraction returned API 502, upstream Gemini HTTP 503 / transient_server / llm_provider_error | 1 / 0 |
| Image, banknote.png | PASS: 49 characters, no warnings | FAIL | API 200, Unconfirmed / Partial; assessment completed but fetched evidence did not establish the exact claim. Source retrieval included HTTP 403 / access_denied / url_fetch_error | 2 / 2 |
| WAV, voice-en.wav | PASS: real Gemini transcript, 52 characters, no warnings | FAIL | Subsequent claim extraction returned API 502, upstream Gemini HTTP 503 / transient_server / llm_provider_error | 2 / 0 |
| Scanned PDF, banknote-scanned.pdf | PASS: 49 characters, no warnings | FAIL | API 200, Unconfirmed / Partial; assessment completed but evidence was insufficient. url_no_text and source_content_incomplete warnings retained | 2 / 2 |
| Public RBI FAQ URL | PASS: 24,000 characters, extraction_text_truncated warning | FAIL | The literal extracted sentence “₹1 notes issued by Government of India are also Legal Tender.” was submitted; claim extraction returned API 502, upstream Gemini HTTP 503 / transient_server / llm_provider_error | 1 / 0 |

PASS: all five selected formats were attempted independently. None was skipped.
PASS: actual total **8 Gemini attempts, 4 Tavily attempts, 0 Twilio sends**;
no retries. No quota exhaustion was observed. Failed acceptance is not proof
that the input claim is false. Unconfirmed/Partial reports preserve uncertainty
and warnings; no successful full verification is claimed.

## Stored actual results

Private Git-ignored artifacts in the feature backend:

- `demo-output/formats-restart-20261012T144144365527Z.json`: all five actual
  results, extraction text, source ledgers, request IDs, safe diagnostics and
  per-format/total provider counts.
- `demo-output/image-result-20261012T144144365527Z.json`: separate image result,
  including successful OCR, the actual partial verification and source ledger.
  JSON parsed successfully after writing (17,038 bytes).
- `demo-output/image-extraction-restart-20261012T144007391444Z.json`: actual
  screenshot extraction from the restarted HTTP service, before live approval.

BLOCKED: a fully successful live verification remains dependent on provider
availability and adequate retrieved source evidence. Further provider testing
requires fresh approval; the approved suite is finished. No database or
WhatsApp operations were performed.
