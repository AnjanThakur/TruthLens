# Scam Alert Intelligence validation

Validated offline on 2026-10-11 in `feature/scam-alert-intelligence`, isolated worktree `D:\HackOnTrack-TruthLens\.worktrees\scam-alert-intelligence`, based on `153af610d9ccb9a761eca6bdb6361da5791358d4`. No frontend, Person 2 database, Meta configuration, existing verification endpoint/schema or existing public OpenAPI changes.

## Actual results

| Check | Result | Evidence |
| --- | --- | --- |
| Complete backend pytest | **PASS** | 296 passed, zero failed/skipped, 16.05 seconds in the final full run |
| New alert regressions | **PASS** | 101 cases in `tests/test_alerts.py`, including parametrized cases |
| Existing backend regressions | **PASS** | All 195 pre-existing cases still pass, including media extraction, quota/503 handling and exact legacy OpenAPI comparison |
| Ruff | **PASS** | `ruff check app tests scripts`: all checks passed |
| mypy | **PASS** | `mypy app`: no issues in 44 source files |
| Dependencies | **PASS** | `pip check`: no broken requirements; no dependencies added |
| Separate alert OpenAPI | **PASS** | New golden snapshot regression matches generated schema; legacy snapshot unchanged |
| API startup/lifespan/auth/error controls | **PASS** | TestClient covers startup, dedicated bearer roles, review/export, request limits, withdrawal/purge, fail-closed configuration and sanitized errors |
| Offline three-language demonstration | **PASS** | Fictional EN/HI/MR claims form one cluster of three independent sources; simulated approval/export for each language; source withdrawal removes drafts |
| Live Gemini/Tavily | **SKIPPED** | User prohibited live requests; actual usage: zero Gemini and zero Tavily calls |
| Supabase adapter, dashboard/chatbot wiring, Channel publishing | **NOT IMPLEMENTED** | Deliberately reserved for Person 2; repository contract and full handoff documented |
| New real-world alert accuracy / confirmed fraud assessment | **NOT VALIDATED** | Offline fixtures do not establish real-world factual accuracy or criminal fraud |

Two existing dependency deprecation warnings remain: Starlette TestClient/httpx and google-genai `_UnionGenericAlias` on Python 3.14. They do not fail tests. Existing Gemini live audio HTTP 503 issue remains outside this feature; no live retest was attempted.

## Behavior verified

- EN/HI/MR common scam variants cluster, including Hindi sentence punctuation. Topic, negation/contraction, numeric-HMAC and entity-HMAC guards prevent the tested unrelated merges. Optional mocked local embeddings preserve these guards; no default model download or translation call exists.
- Stable source pseudonyms count once per cluster. UUID aliases canonicalize before HMAC; idempotent delivery replay stays stable as evidence ages. Changed source, verdict, quality or minimized record under the same submission ID conflicts. Older evidence cannot replace fresher evidence or reset first-seen retention.
- Three independent sources activate the configurable recurrence heuristic; scaled baseline growth is reported only with an established nonzero baseline. Historic stale samples do not replace the current cohort's evidence. Counts always describe this consented sample.
- Reviewed publisher identity, HTTPS URL/privacy checks, fetched provenance, direct relevance, finite relevance bounds and UTC freshness are required. Search snippets, unsafe/private URLs, incomplete/stale/future/unreviewed evidence and provider/quality warnings suppress drafting. High risk alone cannot establish falsehood or fraud.
- All six upstream verdicts have evidence gates. False is described as contradicted, not confirmed fraud. Partial/misleading/outdated claims require relevant context; outdated requires two quoted event dates and distinct source URLs. Unconfirmed remains suspicious/unconfirmed. Verified or decisive contradictory support/opposition suppresses the warning. Opposing snapshots survive shared evidence IDs.
- Pending language generation is explicit, with null summary and blocked approval/export. Available observed target-language variants use authored safety wording; human translation review can resolve a pending draft.
- Approval records reviewer/time/version/content hash/evidence review. Unsubmitted, unapproved, rejected, stale, changed-version and changed-sample drafts cannot export. Edits, fresh evidence and counting-window changes revoke approval; unchanged replay does not. Export is manual-copy-only and never sends a message.
- Phone/PAN/Aadhaar/OTP/password/account/card/UPI/IFSC/email/recognized personal attributes/message URLs are redacted in the tested formats. Whole input, original spans, raw tokens and arbitrary language metadata are not stored. Unknown PII still requires upstream minimization and human privacy review; pseudonyms are not anonymous.
- Withdrawal and retention delete observations, receipts and affected derivative drafts/reviews. Explicit purge, operation-time checks and periodic app sweep enforce expiry/retention. Repository copy isolation and transaction rollback prevent partial capacity/failed writes.
- Ingest/admin roles are separate; service tokens must not reach browsers. Unauthorized requests, validation failures, unknown errors and invalid configuration do not echo private input or secrets. Unknown route exceptions are handled inside the ASGI boundary so the server does not rethrow/log their raw text. Actual streamed byte limits, incomplete bodies and receive timeout are exercised offline.

## Reproduce

```powershell
Set-Location D:\HackOnTrack-TruthLens\.worktrees\scam-alert-intelligence\backend
New-Item -ItemType Directory -Path .tmp -Force | Out-Null
$env:TEMP=(Resolve-Path .tmp).Path
$env:TMP=$env:TEMP
$env:TESSDATA_DIR='D:\HackOnTrack-TruthLens\backend\.runtime\tessdata'
& D:\HackOnTrack-TruthLens\backend\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
& D:\HackOnTrack-TruthLens\backend\.venv\Scripts\python.exe -m ruff check app tests scripts
& D:\HackOnTrack-TruthLens\backend\.venv\Scripts\python.exe -m mypy app
& D:\HackOnTrack-TruthLens\backend\.venv\Scripts\python.exe -m pip check
& D:\HackOnTrack-TruthLens\backend\.venv\Scripts\python.exe -m scripts.demo_alerts --output .tmp/alerts-demo.json
```

Alert tests explicitly block real httpx HTTP transports. Existing backend tests use fixture/provider transports. The demo has no cloud provider implementation. No live acceptance result has been fabricated. Demo fixtures cite clearly fictional institution paths/content and must not be published.

For integration prerequisites, endpoints, JSON schemas/examples, proposed Supabase tables, dashboard/chatbot/Channel workflow, privacy limitations and safe Git handoff see `docs/scam-alert-integration.md`.
