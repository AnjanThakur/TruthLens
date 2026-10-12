# Commit and hosted CI audit — 12 October 2026

Audited feature HEAD: `8b094d720a38b7ab0ed2d109889a41f6080fbd6a`.
The remote branch had the same SHA, with no ahead/behind commits.
`origin/main` is an ancestor. The main checkout's separate uncommitted
teammate changes were preserved, not mixed into the feature repair.

## Exact CI failure

| Run | Trigger | Backend | Website | Adapter |
| --- | --- | --- | --- | --- |
| [38276401495](https://github.com/AnjanThakur/TruthLens/actions/runs/38276401495) | Push, 8b094d7 | FAIL: one OpenAPI snapshot test; 437 passed, two skipped | PASS | PASS |
| [38276407725](https://github.com/AnjanThakur/TruthLens/actions/runs/38276407725) | Pull request, 8b094d7 | Same failure | PASS | PASS |
| [38209020098](https://github.com/AnjanThakur/TruthLens/actions/runs/38209020098) | Push, b5d42d9 | Same failure; 347 passed, two skipped | PASS | PASS |
| [38162197061](https://github.com/AnjanThakur/TruthLens/actions/runs/38162197061) | Push, f0b0fce | Same failure; 331 passed, two skipped | PASS | PASS |
| [38148351435](https://github.com/AnjanThakur/TruthLens/actions/runs/38148351435) | Push, b6c973b | Workflow PASS | Workflow PASS | Workflow PASS |

The entire failing OpenAPI diff was reconstructed from the hosted test log
and compared structurally. Only ten fields differ: the 413 and 422 response
descriptions on each of the five existing routes. Python 3.12 uses the older
stdlib reason phrases; Python 3.14 uses the newer wording saved in the
snapshot. Paths, operation IDs, payload schemas, constraints and fields do
not differ. This is an interpreter-dependent documentation test failure,
not missing commits, an upstream Gemini error or a frontend test failure.

Repair: explicitly declare the existing published response descriptions in
`app.api.routes`; compare complete parsed OpenAPI JSON rather than file
bytes; test schema generation with both stdlib reason-phrase variants.
No schema fields, endpoint behavior, source-evidence safeguards or private
configuration were changed.

## History coverage

All 21 commits reachable from the audited HEAD were checked for Git object
integrity, ancestry and tracked file content. `git fsck --no-reflogs` found
no missing/corrupt objects; dangling intermediate objects are harmless and
were not deleted. The content scan inspected 435 unique blobs for copies
of the currently configured private key/token values, private-key blocks
and tracked private environment/database filenames; no matches were found.
This is a targeted current-secret audit, not a guarantee about every unknown
historical credential. No secret values were printed or written to this report.

| Commit | Recorded change | Hosted coverage found in feature workflow |
| --- | --- | --- |
| 8b094d7 | Evidence reliability and submission documentation | Original push/PR fail only snapshot test |
| b5d42d9 | Retrieval completeness and preview authentication | Original push/PR snapshot failure |
| f0b0fce | Actual bounded live verdict/partial DNS record | Original push/PR snapshot failure |
| 9f16d4c | Unavailable search excerpt labels | No separate run found |
| 231ac1a | Full-system acceptance and Windows startup | No separate run found |
| 788361f | WHO authority/pronoun distinction | No separate run found |
| 3754235 | Controlled budgets and offline CI | No separate run found |
| b8a0cd6 | Consented alerts and multilingual reports | No separate run found |
| ca46666 | Bounded investigation and durable alerts | No separate run found |
| a62b6d9 | Twilio diagnostics and ContentSid restrictions | No separate run found |
| b6c973b | Combined delivery branch | Hosted push/PR success |
| 1c082ad | Combined integration documentation | No separate feature run found |
| a31b427 | Person 2/scam integration merge | No separate feature run found |
| c88900c | Person 2 integration tests and handoff | No separate feature run found |
| 50350b4 | Consented scam-alert engine | No separate feature run found |
| 0e813a2 | Isolated WhatsApp adapter/contracts | No separate feature run found |
| 153af61 | Remote-main merge | No separate feature run found |
| 7ddc2fc | Remote-main merge | No separate feature run found |
| 3325381 | Initial project | No separate feature run found |
| 0ac7926 | Audio/evidence-verdict backend | No separate feature run found |
| 1efc29f | Initial commit | No separate feature run found |

Historical commits were audited, not individually rerun. Current offline
checks validate the combined implementation. Old red workflow runs remain
historical; the repair must produce new green hosted runs before a merge.

## Validation and remaining boundaries

PASS locally: 442 backend tests, including both new cross-version regressions;
14 policy cases; Ruff; mypy across 48 files; pip dependency checks.
The unchanged frontend and adapter passed their complete hosted jobs at
the audited commit, including browser/proxy tests and formatting/build.
No paid provider or live database requests were made for this audit.

Two original Linux skips are Hindi/Marathi native OCR fixtures requiring
`C:/Windows/Fonts/Nirmala.ttc`. This repair does not claim they ran on Linux;
both ran in the local full suite. Hosted privacy lifecycle acceptance and
dynamic WhatsApp delivery remain separately BLOCKED as previously recorded.

Check the replacement push and pull-request workflows after publication:
[TruthLens offline acceptance runs](https://github.com/AnjanThakur/TruthLens/actions/workflows/person2-offline.yml).
Do not infer hosted success from local PASS or from successful Git upload.
