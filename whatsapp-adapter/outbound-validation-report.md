# Twilio outbound diagnostics — 11 October 2026

Scope: `D:\HackOnTrack-TruthLens\whatsapp-adapter`. No frontend, backend verification
engine, public API, Meta transport, database schema, encryption key or identity secret
changed. Only the supplied development ContentSid was added to private settings;
all other settings were preserved. The adapter web process remains running; the worker was
paused to prevent unapproved sends during debugging.

## Findings and fixes

The previous implementation discarded Twilio error responses in `TwilioClient.send()`
and raised only `twilio_rejected`. `Worker.send_one()` caught this and marked the
outbox failed without recording a reason. Consequently the old send's HTTP status
and numeric error code cannot be recovered from its outbox record. The actual
Twilio-side cause of that historical attempt cannot be recovered. A new approved
attempt below establishes the currently reproducible failure as missing ContentSid.

`TwilioSendError` and `TwilioUncertainSend` now carry strictly validated HTTP status
and numeric error-code fields. They do not store provider messages, phone numbers,
credentials or response bodies. Worker warning logs record those two fields and
attempt logs report the resulting state. Malformed or oversized JSON supplies no
error code. Timeouts, 5xx and malformed successful responses remain uncertain and
are not automatically resent. Definite 400/401/403 rejections remain failed; only
429 retains the existing bounded retry policy. Invalid callback UUIDs now fail
locally without a request. A response explicitly reporting `failed`/`undelivered`
is no longer treated as an accepted message solely because it contains a SID.

## Actual non-sending checks

| Check | Result |
|---|---|
| Private settings | PASS: Twilio, development, outbound enabled, backend disabled; token has expected format |
| Account GET | PASS: HTTP 200, matching account, active, Trial |
| Existing inbound Message GET | PASS: HTTP 200; account, configured Sandbox sender and recipient match; received within the reply window |
| Latest outbox, read-only SQLite | CONFIRMED FAILURE: failed, attempts 1, no Twilio ID; not changed or retried |
| Monitor Alerts GET | BLOCKED: HTTP 401, numeric code 20003; did not recover the send error. This is a separate read endpoint failure, not evidence that the send failed with 20003 |
| Account settings correction | None justified by the above checks |
| Initial approved development send | FAIL: HTTP 400, numeric error 21654, no message SID |
| Separately approved template send | PASS: HTTP 201; one send attempt, actual message SID returned |
| Template delivery | PASS: Twilio message GET and signed callback both delivered; owner confirmed receipt on their phone |
| Gemini / Tavily calls | Zero / zero |

Current [trial documentation](https://www.twilio.com/docs/usage/trials/try-out-whatsapp)
requires verified recipients and Twilio-provided `ContentSid` templates. The
[Sandbox guide](https://www.twilio.com/docs/whatsapp/sandbox?save_locale=en-us)
describes participant expiry after three days and a 24-hour free-form reply window.
The approved send provided account-specific confirmation: **21654 — ContentSid
Required**. See [Twilio's error definition](https://www.twilio.com/docs/api/errors/21654).
The adapter's actual request contained `Body` and did not contain `ContentVariables`;
the current trial API requires a supplied ContentSid. No account upgrade was made.

## Approved live attempt and smallest compatibility fix

After explicit owner approval and a freshly submitted HI, the selected-message
runner performed exactly one receipt GET and one send POST. A local exclusive-create
attempt marker prevents that approval from authorizing another POST on rerun. The
unrestricted worker stayed paused, backend requests were zero, and old failed outbox
rows were compared before/after and remained identical. The new outbox is failed,
attempts 1, no Twilio ID. Actual diagnostic: `http_status=400 twilio_error_code=21654`.

Added optional `TWILIO_DEVELOPMENT_CONTENT_SID` (HX plus 32 hex characters). When
configured, only the fixed development connectivity reply uses `ContentSid` instead
of `Body`, with no `ContentVariables`. Configuration and runtime gates require test
environment, development mode and disabled backend. This cannot replace a factual
result, command acknowledgement or provider-error reply. Authentication, sender,
recipient, status callback, signature validation, queue and database remain intact.
The delivered content would be Twilio's supplied trial template, not custom TruthLens
text. This proves connectivity only and does not enable arbitrary sourced replies
under trial restrictions.

The Content API's non-sending template-list GET returned HTTP 401/code 20003; no HX
SID was configured in the private file at that point. No suitable existing Twilio browser window
was visible. Owner action is required to copy the actual Twilio-provided ContentSid
from Console → Try out WhatsApp. No example SID, template creation, purchase,
automatic fallback, old-item retry or second live send was used.

The owner subsequently supplied the HX ContentSid. It was saved only to the ignored
private `.env.twilio`, preserving all other settings, including state encryption and
identity secrets. Its format and test/development/backend-disabled gates passed.
A MockTransport dry run using the actual private configuration confirmed the
ContentSid field, absence of Body/ContentVariables, authentication and status
callback, with zero live requests and no database access. This establishes request
construction only, not template authorization, acceptance or delivery. The worker
remained paused. At that point, no second send had been authorized or attempted.

## Separately approved live template acceptance

The owner explicitly approved one further template test and submitted fresh HI
messages. The initial preflight found two fresh inputs and stopped before any POST;
the attempt marker was absent and no outbox had changed. The subsequent run selected
only the newest HI and left the other input unprocessed. Its own exclusive-create
attempt marker limited the new approval to one POST.

**Actual result: PASS.** The ContentSid request returned HTTP **201**, and the
outbox received an actual Twilio message SID. A read-only Message API GET returned
HTTP 200/status **delivered**, with no numeric error code. The signature-validated
callback independently moved the outbox to **delivered**. The owner then confirmed
the selected template appeared on their WhatsApp phone.

Consumption for this template test: **one outbound attempt, zero backend requests,
zero Gemini requests, zero Tavily searches**. Total debugging consumption across
the two separately approved tests: two outbound attempts, zero AI calls. Both old
failed outbox rows remained unchanged. The worker stays paused; no unrestricted
processing or further sends were enabled. The delivered message is the supplied
Twilio trial template. This acceptance establishes development connectivity;
custom factual replies remain subject to the trial's content restrictions.

## Offline validation

- PASS: **132 adapter tests**, including 40 new send-diagnostic/template regressions.
- PASS: Ruff over `truthlens_whatsapp` and `tests`; formatting check on changed Python files.
- PASS: `pip check` reports no broken requirements.
- PASS: existing Meta, signed-webhook, queue, encryption, opt-out, deduplication and backend-contract regressions.
- PASS: selected fresh Twilio fixture makes exactly one GET and one POST, zero backend requests; rerunning it does nothing and preserves every column of the old failed outbox row.
- One existing Starlette/httpx deprecation warning remains; no test failures.

Tests use MockTransport and the suite's network-blocking fixture. Initial sandboxed
attempts could not access pytest temporary directories; the final complete run used
an isolated workspace temporary directory with filesystem permission escalation.
Private operational state was read only.

## Further live work

The actual `TWILIO_DEVELOPMENT_CONTENT_SID` is saved privately and the development
template path has passed offline and live delivery validation. Both single-send
approvals are exhausted. Any further outbound test needs new approval and one
selected fresh input, with the unrestricted worker paused. Do not reset/retry old
failed rows, consume the unselected queued HI or automatically fall back to another
send. No upgrade was purchased, and provider-backed fact-checking remains disabled.
