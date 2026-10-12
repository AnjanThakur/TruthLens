# TruthLens AI — evidence-based hackathon submission content

Audit date: 12 October 2026. Scope: main checkout and the newer feature worktree, README/handoffs, source, dependency manifests/locks, safe configuration examples, migrations, Dockerfile, fixtures, tests, acceptance artifacts and Git history. No notebooks were found. Private credentials were excluded. No new provider calls or database writes were made.

Use the feature worktree for the current implementation. At the initial audit, its pushed HEAD was `b5d42d9` and newer assessment, extraction and Gemini recovery changes were uncommitted. See subsequent Git history for their publication. Earlier README counts and pending-feature statements are historical. Sources S1–S21 below identify the evidence for this deck. Reported tests were inspected during the audit; the subsequent commit-readiness checks below were rerun offline.

Commit-readiness validation, 12 October 2026: 440 backend tests passed; Ruff passed; mypy passed across 48 source files. All 65 frontend tests, ESLint, TypeScript and the production build passed. The targeted evidence-status browser regression passed on desktop and mobile. The slide structure, bullet lengths and local source links were checked. No new Gemini, Tavily or Twilio requests were made. Hosted acceptance and dynamic WhatsApp blockers remain unchanged.

## Slide 1 — TruthLens AI

- Check forwarded claims against fetched evidence before sharing. [S1, S6]
- PS3: “Is This Forward True?”; documented technical area: GenAI. [S1]
- Official theme/category and team name/ID: [NOT FOUND]; add submission details.
- Member names: [NOT FOUND]; documented roles: Person 1 backend/AI, Person 2 frontend/data/integration. [S1]
- College and mentor: [NOT FOUND]; add verified institutional details.

Visual: Project name beside the actual home screen; reserve space for verified team details.

## Slide 2 — Problem and Solution

- Indian forward recipients face unsupported health, scheme and dated-news claims; impact figure: [NOT FOUND]. [S1]
- Solution: extract claims, retrieve original pages, assess evidence, then explain uncertainty. [S6, S12]
- USP: evidence IDs and verbatim-quote checks constrain decisive verdicts. [S6]
- USP: publication, modification and event dates remain distinct. [S12, S13]
- USP: English, Hindi and Marathi presentation preserves factual verdicts. [S1, S11]

Existing approach means the preserved repository baseline, not an independently evaluated competitor:

| Existing way | Flaw | Our fix |
| --- | --- | --- |
| Discard low-ranked official results | Relevant primary evidence can be missed | Reviewed authority considered alongside relevance |
| Stop after an empty initial query | Discoverable evidence remains missing | Bounded alternative investigation queries |
| Rely on publication dates | Event changes remain unresolved | Distinct event-date evidence and temporal guards |

Source: identical fictional baseline comparisons in S9. The solution does not infer truth from search titles or snippets. Add a cited impact statistic before submission; none is established by this repository.

Visual: Forward → atomic claim → fetched source → guarded verdict, beside the baseline comparison.

## Slide 3 — Technical Approach

- Gemini produces structured claims, transcriptions and evidence assessments; local validation constrains acceptance. [S4, S6]
- Tesseract and PyMuPDF extract image/scanned-PDF text; Trafilatura extracts webpage content. [S4, S13]
- Evidence logic checks subject, dates, quotations, publisher identity and independent corroboration. [S6, S12]
- Alert clustering preserves entities, numbers and negation; lexical matching works without downloaded embeddings. [S18]

| Layer | Libraries and versions declared by the project |
| --- | --- |
| Frontend | Next.js 16.4.0; React/React DOM 19.3.0; TypeScript 6.0.3; Zod 4.6.5; Lucide React 1.55.0. [S3] |
| Backend | Python >=3.11; FastAPI >=0.115,<1; Pydantic >=2.10,<3; Uvicorn >=0.34,<1; HTTPX >=0.28,<1. [S4] |
| AI/extraction | google-genai 2.29.0; configured gemini-3.8-flash; PyMuPDF >=1.25,<2; pytesseract >=0.3.13,<1; Pillow >=11,<13; Trafilatura >=2,<3. Tavily through HTTPX. [S4, S10, S13] |
| Data | @supabase/supabase-js 2.117.3; @supabase/ssr 0.12.7; Supabase PostgreSQL; Python sqlite3. Adapter psycopg 3.3.6; cryptography 50.0.0. [S3, S5, S15, S18] |
| Infra/testing | Adapter Python 3.12-slim Docker image; PowerShell/Uvicorn/Node startup; GitHub Actions. Vitest 5.0.3; Playwright 1.64.0; axe-core/playwright 4.13.0. [S3, S5, S20] |

Exact resolved backend versions, native Tesseract/FFmpeg versions and hosted PostgreSQL version: [NOT FOUND] in dependency locks. Backend declarations above are ranges, not exact pins. Add a reproducible backend lock and native-tool inventory.

Flow: Input → extraction/review → atomic claims → Tavily discovery → guarded page fetch → evidence ledger → Gemini assessment → deterministic acceptance guards → readable report.

Rationale inferred from implementation: structured output supports typed validation; OCR supports image forwards; fetched-page guards prevent snippet-only decisions; conservative clustering reduces accidental merging. No model-selection benchmark establishes these as optimal choices.

Visual: Layered architecture with the evidence ledger and local acceptance guards highlighted.

## Slide 4 — Data and Validation

- Public publisher pages provide live evidence; corpus size and redistribution licenses: [NOT FOUND]. [S12]
- Synthetic validation includes 14 policy cases and six fictional interface examples. [S7, S8]
- Preprocessing includes Unicode normalization, OCR/transcription, bounded chunks, date extraction and source deduplication. [S12, S13]
- No local model training; train/test split, real-world accuracy and representative benchmark: [NOT FOUND].
- Policy cases passed 14/14; four baseline regressions improved, using fictional deterministic records. [S8, S9]

| Data source | Type, size and format | License/limitation |
| --- | --- | --- |
| Tavily-discovered source pages | Public, changing HTML/PDF articles; no fixed corpus count | Public accessibility does not establish redistribution permission |
| Policy cases and proposals | Synthetic JSON; 14 labeled cases; adversarial model proposals | Project license [NOT FOUND]; tests evaluate guard behavior |
| Interface fixtures | Synthetic JSON; six fictional examples | Not genuine verification or a held-out test set |
| Demo media | Generated PNG/JPG, text, PDF and spoken WAV fixtures | WAV is generated speech; not representative human voice data |
| OCR language assets | Public Tesseract eng/hin/mar trained-data files | Project license inventory/revisions [NOT FOUND]; record upstream assets |

Sources: S7, S8, S13 and the fixture generator linked in the source ledger.

| Recorded measurement | Actual result | Interpretation and source |
| --- | --- | --- |
| Deterministic policy conformance | 14/14; category precision/recall 1.0 | Tiny fictional guard test, not factual accuracy. S8 |
| Policy abstention | 50% = 7 unconfirmed / 14 cases | Fixture distribution, not population failure rate. S8 |
| Baseline regression comparison | Four scenarios corrected | Preserved backend versus feature backend; fictional evidence. S9 |
| Backend automated checks | 440 tests PASS; Ruff and mypy PASS | Software regression coverage, not ML accuracy. S10 |
| Frontend automated checks | 65 tests PASS; production build PASS | Last recorded frontend suite, not hosted acceptance. S11 |

Limitations: small handcrafted fixtures, changing source accessibility, incomplete articles, synthetic speech, no representative user study. Add independently labeled real claims, source snapshots with permissions, and language/media-specific evaluation. R² is inapplicable to this classification workflow; no R² result exists.

Visual: Separate panels for synthetic guard tests and actual live acceptance; never label tests “accuracy.”

## Slide 5 — Prototype and Demo

- Implemented: text, image, audio, PDF and public-URL extraction with editable review. [S6, S13]
- Implemented: claim-level reports, source states, uncertainty and multilingual reading modes. [S6, S11]
- Implemented/offline-tested: private history, consented alerts, reviewer checks and withdrawal. [S15–S18]
- Latest live suite: extraction worked; full acceptance failed through provider errors or insufficient evidence. [S14]
- Later Gemini recovery passed claim extraction; full verification remained unproven by that smoke test. [S10]

Exact screens to capture: `/` input selection; `/` extracted-text review; `/` results/source cards; `/` Marathi easy-reading mode; `/history` authenticated private history; `/alerts` consent/reviewer dashboard. History and reviewer screenshots require genuinely authenticated sessions. Existing `docs/qa` screenshots are earlier UI examples, not fresh live acceptance proof.

Actual live evidence: image OCR and scanned-PDF OCR passed; WAV transcription passed; URL extraction passed with truncation warning. Subsequent text/audio/URL claim extraction encountered Gemini 503; image/PDF reports remained Unconfirmed/Partial. No complete five-format PASS is claimed. The separate actual image result is saved at the private artifact linked under S14.

Links: [repository](https://github.com/AnjanThakur/TruthLens/tree/feature/scam-alert-intelligence); local preview `http://localhost:3001`; public live app [NOT FOUND]; demo video [NOT FOUND]. Publish an approved deployment and record an honest demo.

Three commands for the documented **synthetic frontend demo**, requiring the declared Node version:

```powershell
cd D:\HackOnTrack-TruthLens\.worktrees\scam-alert-intelligence\frontend
npm ci
npm run dev:mock -- --port 3002
```

Use `http://localhost:3002`; the explicit port avoids replacing existing previews. Select “Use this example,” then “Check the facts.” Synthetic mode does not actually extract uploads, translate through Gemini or verify arbitrary edited claims. Real backend/native tools and private configuration require the separate Windows startup guide, S20. These commands were inspected, not launched during this audit.

Visual: Actual home/results screenshots plus a clearly labeled status strip: offline PASS, live partial/FAIL, hosted BLOCKED.

## Slide 6 — Feasibility and Risks

- Technical: modular services support local testing; provider availability limits live reliability. [S10, S20]
- Operational: reviewer permissions and consent exist; hosted acceptance and channel eligibility remain blocked. [S19]
- Financial: usage budgets and caches exist; rupee costs and monthly balances: [NOT FOUND]. [S10, S12]
- Deployment: local services and adapter Docker are supported; public production deployment remains unverified. [S5, S20]

Severity below is an analyst assessment, not a measured risk score.

| Risk | Severity | Implemented mitigation | Remaining limit |
| --- | --- | --- | --- |
| Provider overload/quota | High | Bounded retries, Retry-After, cooldown, daily-quota fail-fast | Availability remains external |
| Unsupported or malicious evidence | High | Fetched-page, relevance, quotation, schema and temporal guards; abstention | Retrieval quality is not guaranteed |
| Private content exposure | High | Owner RLS, signed receipts, consent, redaction, encrypted local state, retention | Hosted lifecycle acceptance is blocked |
| WhatsApp account restrictions | High | Numeric sanitized diagnostics, paused worker, outbound gates, no automatic fallback | Dynamic delivery blocked; template connectivity passed historically |

Sources: S6, S10, S15–S19, S21.

Supported deployment scope: Windows local startup; separately hosted Node/FastAPI services described in deployment handoffs; adapter container usable on a suitable local/cloud host. Backend/frontend Dockerfiles, Compose, Kubernetes and deployed public URLs: [NOT FOUND]. On-premises service hosting still depends on external Gemini/Tavily and optionally Supabase/WhatsApp; an air-gapped system is not implemented.

Cost basis: hosting + Gemini billable usage + Tavily searches + applicable messaging charges. Account tariffs, token billing and hosting bills are [NOT FOUND], so no rupee estimate is defensible. Recorded five-format usage was 8 Gemini attempts, 4 Tavily attempts, 0 Twilio sends; recovery used 1/0/0. These are request counts, not monetary savings. [S10, S14]

Visual: Risk/mitigation table beside local-service and external-provider boundaries.

## Slide 7 — Impact and Benefits

- Recipients — Projected: cited verdicts support checking before forwarding; behavioral improvement is unmeasured. [S1, S6]
- Language users — Projected: English/Hindi/Marathi reading options broaden access; comprehension improvement is unmeasured. [S1, S11]
- Reviewers — Projected: consented clusters and reviewed drafts support triage; productivity improvement is unmeasured. [S18]
- Measured: four fictional baseline regressions corrected; basis is identical before/after inputs. [S9]
- SDG mapping and population benefit figures: [NOT FOUND]; add supported targets and user-study measurements.

Calculation basis: four corrected scenarios are counted in the comparison artifact; this is software behavior, not prevented scams. Projected benefits follow implemented user actions, not a quantified outcome model. No cost-saving, accuracy-improvement or harm-reduction percentage is established. SDGs are deliberately unassigned because the repository provides no mapping; select up to three only after verifying target relevance.

Visual: Recipient, language-user and reviewer icons linked to observable product actions; no invented impact graph.

## Slide 8 — Roadmap and Future Scope

- Built: investigation, alert persistence and multilingual web reports; commits ca46666 and b8a0cd6. [S2]
- Built: controlled acceptance/startup and retrieval/auth fixes; commits 231ac1a and b5d42d9. [S2]
- Next: complete full live acceptance after provider availability and approved testing budgets. [S19, S20]
- Next: validate hosted history/reviewer/retention, then dynamic WhatsApp after account eligibility. [S19]
- Scaling work: shared coordination and load testing; tracker/radar/public sharing remain deferred. [S1, S19]

| Next milestone | Dependency-based timeline | Evidence needed |
| --- | --- | --- |
| Reliable provider-backed demo | Before claiming complete live acceptance | All input outcomes recorded; available providers; approved budget |
| Hosted privacy/alert lifecycle | Before releasing authenticated storage/review | Real sessions, owner isolation, reviewer grant, cleanup and withdrawal |
| Dynamic WhatsApp replies | After account permits actual report delivery | Approved outbound attempt and real phone confirmation |

Calendar dates and effort estimates: [NOT FOUND]; add owners, available engineering capacity and deadlines. These are existing release gates, not invented delivery promises. Recent local Gemini/relevance/assessment fixes were implemented but uncommitted at the initial audit; use subsequent Git history to confirm their publication.

Scaling: adapter supports SQLite/PostgreSQL; alert state supports encrypted local SQLite. Distributed consent locks, shared rate controls, independent retention scheduling and representative load tests remain follow-up work. No capacity or users-per-second claim exists. Out of scope now: global WhatsApp monitoring, automatic public alert publishing, local model training and full browser rendering of JavaScript-only articles. [S18–S21]

Visual: Built commits → provider acceptance gate → hosted lifecycle gate → account-eligible channel gate.

## Slide 9 — References

- Cite actual APIs, extraction tools and framework documentation; no research-paper benchmark is documented.
- Use repository fixtures as validation evidence, not real-world datasets. [S7–S9]
- Repository exists; public live application and demo video: [NOT FOUND]. [S2]

Reference format: author, year, title, link. `n.d.` denotes living documentation without a fixed publication year established here; no year is invented.

| Author | Year | Title and verified link | Project use |
| --- | --- | --- | --- |
| Google | n.d. | [Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output) | Structured extraction/assessment |
| Google | n.d. | [Gemini API versions](https://ai.google.dev/gemini-api/docs/api-versions) | Stable provider routing |
| Tavily | n.d. | [Tavily Search API](https://docs.tavily.com/documentation/api-reference/endpoint/search) | Evidence discovery |
| Tesseract OCR contributors | n.d. | [tessdata_fast](https://github.com/tesseract-ocr/tessdata_fast) | OCR language assets |
| PyMuPDF contributors | n.d. | [PyMuPDF documentation](https://pymupdf.readthedocs.io/en/latest/) | PDF extraction/rendering |
| FFmpeg contributors | n.d. | [FFmpeg documentation](https://ffmpeg.org/documentation.html) | Audio inspection/conversion |
| Vercel/Next.js contributors | n.d. | [Next.js documentation](https://nextjs.org/docs) | Web application |
| FastAPI contributors | n.d. | [FastAPI documentation](https://fastapi.tiangolo.com/) | Verification/adapter APIs |
| Supabase | n.d. | [Supabase documentation](https://supabase.com/docs) | Authentication and private history |
| Twilio | n.d. | [Try out WhatsApp](https://www.twilio.com/docs/usage/trials/try-out-whatsapp) | Sandbox integration |

Repository: https://github.com/AnjanThakur/TruthLens/tree/feature/scam-alert-intelligence. Public app: [NOT FOUND]. Demo video: [NOT FOUND]. No unverified paper citation has been added; no `[VERIFY]` citation is necessary for the links checked. Dataset/repository licensing remains missing from the project inventory.

Visual: Compact API/tool references with a repository QR code; omit nonexistent app/video QR codes.

## A. Gap report — ranked by judge impact

| Priority | Gap | What to add or measure |
| --- | --- | --- |
| Critical | Complete live acceptance still fails/is unproven | Approved controlled verification; preserve actual results and limitations |
| Critical | [NOT FOUND] real-world accuracy and representative benchmark | Independently label real claims; evaluate correctness, abstention, languages and media |
| High | Hosted history/reviewer/cleanup acceptance BLOCKED | Authenticated lifecycle tests, legitimate second user, confirmed reviewer/cron configuration |
| High | [NOT FOUND] public live link and demo video | Approved hosting and a recorded reproducible demonstration |
| High | [NOT FOUND] team name/ID, member names, college, mentor, official theme/category | Copy verified submission metadata; keep PS3/GenAI distinct from unknown official fields |
| High | [NOT FOUND] cited impact figure and measured beneficiary outcomes | Add authoritative impact source; run usability/comprehension/forwarding studies |
| High | [NOT FOUND] source/data licensing inventory and repository license | Document rights, upstream versions and permissible snapshot use |
| Medium | Dynamic WhatsApp BLOCKED | Account eligibility plus one approved genuine dynamic reply; templates prove connectivity only |
| Medium | [NOT FOUND] cost model, tariffs, hosting bills and monthly balance | Record billable tokens/searches/messages and compute cost per completed check |
| Medium | [NOT FOUND] backend dependency lock/native versions/database version | Capture resolved dependencies and installed native-tool/server versions |
| Medium | [NOT FOUND] fixed real corpus size, real baseline and evaluation split | Publish dataset manifest and independent evaluation protocol; local training is unnecessary |
| Medium | [NOT FOUND] scaling/load evidence and calendar roadmap | Measure concurrent workload; assign milestone owners and deadlines |
| Lower | [NOT FOUND] SDG mapping | Select supported targets and justify their connection without claiming measured SDG impact |
| Lower | [NOT FOUND] backend/frontend containers or orchestration | Add only if required for the chosen deployment; do not imply existing full-stack Docker support |

No numerical performance claim lacking a source is presented as a result. Any proposed accuracy, savings or harm-reduction number would be `[UNVERIFIED]` until measured. No notebook, training split or research-paper citation was found; these are not automatically requirements for an inference-only prototype.

## B. Five likely judge questions

1. **How accurate is it?** No real-world accuracy is established. The fictional policy cases test evidence safeguards. The recorded backend suite tests software behavior. Neither substitutes for a representative independent benchmark. [S8, S10]
2. **What prevents hallucinated citations?** The ledger assigns evidence IDs to fetched sources. Assessment output must pass structured validation, reference real ledger entries and use traceable verbatim quotations. Missing, irrelevant or snippet-only evidence cannot establish a decisive verdict. [S6, S12]
3. **What is different from asking a chatbot?** This implementation separates claim extraction, discovery, page retrieval and guarded acceptance. It retains source provenance and dates, exposes uncertainty and preserves verdicts across language presentation. No market superiority study is claimed. [S6, S11–S13]
4. **Is private content protected?** History requires consent, a genuine signed receipt and owner RLS. Alerts minimize/redact inputs and support withdrawal/retention; local alert/channel state is encrypted. Hosted lifecycle acceptance is still blocked, and external provider processing remains part of the trust boundary. [S15–S19]
5. **Can we see a reliable demo, and will it scale?** The synthetic interface runs without provider credits. Recorded live extraction works across media, but full acceptance remains limited by provider/evidence availability. Later provider recovery passed extraction only. Dynamic WhatsApp is blocked; no production capacity or cost claim is available. [S10, S14, S19–S21]

## C. One-minute pitch

TruthLens AI helps people check forwarded claims before sharing them. Users submit text, a screenshot, audio, a PDF or a public link, then review the extracted text. The backend separates atomic claims, discovers sources and retrieves their actual pages. Gemini assesses the evidence, while local rules check quotations, relevance, dates and provenance before accepting a verdict. When evidence is insufficient, the report says Unconfirmed. English, Hindi and Marathi presentation improves access without changing the verdict. Private history and consented alert review are implemented with ownership and privacy controls. Our tests validate safeguards, not real-world accuracy. Live media extraction has worked, but provider failures still limit complete acceptance. The next gates are reliable live verification, hosted privacy checks and account-eligible WhatsApp delivery.

## Diagram prompts

### 1. User flow diagram

Create a TruthLens AI swimlane flowchart, left-to-right, clean flat style, white background, large slide-legible labels. Lanes: visitor, signed-in user, authorized alert reviewer, and optional WhatsApp participant. Visitor enters the Next.js `/` page, selects text/image/audio/PDF/public URL, reviews extracted text, then requests verification. Decision diamonds: extraction succeeds? fetched evidence eligible? Gemini assessment succeeds? local guards accept? Outcomes: cited report, explicit partial/error, or Unconfirmed. Show English/Hindi/Marathi and easy-reading controls. Signed-in users can explicitly save only a completed genuine report with a valid receipt, then list/delete their own history at `/history`. Add optional consent contribution, withdrawal, and `/alerts`. Reviewer access requires an `alert_reviewers` grant; review draft, approve/reject/edit, then manual export only. WhatsApp lane: signed webhook → encrypted queue → paused worker; mark dynamic delivery BLOCKED and historical template connectivity separate. Never imply automatic alert publishing or working dynamic replies.

### 2. System architecture diagram

Create a layered TruthLens AI architecture diagram, left-to-right, clean flat style, white background. Browser layer: Next.js pages `/`, `/history`, `/alerts`; components VerificationWorkspace, Results, AlertsWorkspace. Server layer: Next.js `/api/extract`, `/api/verify`, `/api/explain`, `/api/history`, `/api/alerts/*` proxies, Origin/auth checks and receipt verification. Verification layer: FastAPI `app.main:app`, extract modules, claims.parser, search.investigation, search.relevance, search.ledger, verify.engine, explain.engine, providers and quota. Connect providers to Gemini and search.client to Tavily; connect URL fetcher directly to public source pages through SSRF protections. Separate alert service `app.alerts_app:app` connects to consented completed reports and encrypted SQLiteAlertRepository. Supabase Auth/PostgreSQL supports owner-only reports and reviewer allowlist. Separate `truthlens_whatsapp.main:app` connects signed Meta/Twilio webhooks to encrypted Store and paused worker. Use solid implemented connections and dashed blocked outbound delivery. Draw external-provider and private-state trust boundaries; secrets stay server-side.

### 3. Technology stack diagram

Create a TruthLens AI stack diagram, top-to-bottom, grouped layers, clean flat style, white background. Use recognizable official logos where available and readable text labels. Frontend: Next.js 16.4.0, React 19.3.0, TypeScript 6.0.3, Zod 4.6.5, Lucide React 1.55.0, custom CSS. Backend: Python >=3.11, FastAPI >=0.115,<1, Pydantic >=2.10,<3, HTTPX >=0.28,<1, Uvicorn >=0.34,<1. AI/extraction: configured gemini-3.8-flash, google-genai 2.29.0, Tavily HTTP API, Tesseract/pytesseract, PyMuPDF, Pillow, Trafilatura, FFmpeg/FFprobe. Data: Supabase Auth/PostgreSQL, supabase-js 2.117.3, supabase/ssr 0.12.7, encrypted SQLite; optional adapter PostgreSQL via psycopg 3.3.6. Infra/tests: adapter Python 3.12-slim Docker, PowerShell startup, GitHub Actions, Vitest 5.0.3, Playwright 1.64.0, pytest/Ruff/mypy. Add footer: backend ranges are declarations; native-tool/server versions were not pinned. Do not add TensorFlow, PyTorch, vector databases, Tailwind or Kubernetes.

### 4. Data flow diagram

Create a TruthLens AI data flow diagram, left-to-right, clean flat style, white background. Sources: user text/image/audio/PDF/public URL and Tavily search results. Processing: extract.media, extract.url/encoding/article_content/metadata → reviewed text → claims.parser → search.investigation/relevance → SSRF-guarded article fetch → search.ledger. Annotate ledger records with evidence ID, original/final URL, publisher, fetched excerpt, provenance, publication/modified/event dates and completeness. Pass prepared records to Gemini via providers; verify.engine validates schema, verbatim quotes and evidence IDs before producing the report. Output: Results source cards, report status and multilingual explanation. Optional explicit-consent branches: signed receipt → verification_reports; eligible warning-free completed report → alerts privacy/clustering/engine → encrypted alert_state → reviewed draft/manual export. Show withdrawal/retention deleting eligible stored and derived records. No automatic storage of every input, search snippet as proof, or unconsented WhatsApp ingestion.

### 5. ML/AI pipeline diagram

Create a TruthLens AI inference-and-validation pipeline, left-to-right, clean flat style, white background. Label it “Pretrained model inference; no local training.” Input preprocessing: Unicode normalization, OCR/PDF parsing, audio transcription and article extraction. Claim representation: exact original span, entities, temporal context and atomic propositions. Retrieval: primary/corroboration/contrary query planning, Tavily, full-page fetch, relevance/independence checks. Model: configured gemini-3.8-flash returns structured evidence assessments using ledger IDs, excerpts and dates. Acceptance layer: full Pydantic validation, source eligibility, exact quotation, component support, contradiction and temporal guards. Outputs: verified, false, partially_true, outdated, misleading_context, unconfirmed; do not merge verdict with processing status. Explainability: source excerpts, dates, provenance, warnings and plain-language reasons. Evaluation side branch: fictional cases.json plus adversarial proposals → evaluate_policy.py → policy-results.json; label “guard conformance, not factual accuracy.” Separate Gemini availability tests from correctness evaluation. Alert side branch uses conservative lexical/Jaccard clustering with optional injected embeddings; no default embedding model or trained classifier.

### 6. Deployment diagram

Create a TruthLens AI deployment diagram, left-to-right, clean flat style, white background. Draw a local Windows host boundary containing Node/Next.js preview on 3001, Uvicorn verification on 8000, separate alerts service on 8001, and optional adapter on 8100. Label `scripts/Manage-TruthLens.ps1` as startup/readiness/owned-process control. Show encrypted alert SQLite and private configuration as host-side assets without values or filesystem secrets. Outside the boundary: Gemini, Tavily, public article sites, Supabase Auth/PostgreSQL, Twilio/Meta. Optional ngrok connects public signed webhooks to adapter only. Worker remains paused; outbound dynamic delivery BLOCKED. Add separate supported packaging inset: only the adapter has a Python 3.12-slim, non-root Dockerfile exposing 8100. Add “cloud HTTPS deployment documented; public hosted app not verified.” Do not depict full-stack Compose, Kubernetes, deployed cloud instances or an air-gapped AI service.

### 7. Database/ER diagram

Create a TruthLens AI database diagram, left-to-right, clean flat style, white background, with three distinct storage boundaries. Supabase relational ER: auth.users(id) connects by actual foreign keys to verification_reports(owner_id) and alert_reviewers(owner_id). verification_reports fields: id, owner_id, verification_id, input_type, input_excerpt, report_json, consent_to_store, created_at, retention_expires_at; annotate unique(owner_id, verification_id), owner-only RLS, completed genuine reports, no UPDATE grant, expired rows hidden and scheduled purge. alert_reviewers: owner_id primary key, granted_at; only own grant readable, administrator-managed assignment. Alert SQLite: one physical table alert_state(id primary key, payload encrypted BLOB); show observations/clusters/drafts/receipts as logical JSON collections inside payload, never as physical tables. Adapter SQLite/PostgreSQL: transport_config(id,provider), jobs(id,sender,payload,state,created,lease,report,error,language), preferences(sender,language,stopped,updated), outbox(id,job_id,part,body,state,meta_id,attempts,due,created). Show jobs.id → outbox.job_id as dashed logical relationship, not declared foreign key; annotate unique(job_id,part), hashed sender and encrypted payload/report/body. Do not connect isolated adapter data to Supabase users.

### 8. Before-versus-after comparison infographic

Create a TruthLens AI comparison infographic, left-to-right, clean flat style, white background, two columns “Preserved repository baseline” and “Feature implementation.” Use three matched rows: low-ranked official evidence discarded → reviewed authority plus relevance; initial empty query stops discovery → bounded alternative queries; publication date treated without event witnesses → separate event-date evidence and temporal guards. Show identical fictional inputs on both sides and label “Deterministic regression comparison; not a market study.” Add small footer: avoidable-results.json records four corrected scenarios; no real-world accuracy, monetary savings or prevented-scam percentage is established. Include an uncertainty badge on both sides to emphasize unavailable/unsupported evidence remains Unconfirmed. Do not portray WhatsApp users, competing products or manual checking as measured inferior baselines.

## Source ledger

All local paths below refer to the scanned feature worktree unless noted. They are the numerical and implementation provenance for this document.

| ID | Primary source |
| --- | --- |
| S1 | [Problem statement and roles](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/TruthLens_Person2_Codex_Package/TruthLens_Person2_Codex_Master_Handoff.md) |
| S2 | [Feature Git history](https://github.com/AnjanThakur/TruthLens/commits/feature/scam-alert-intelligence/) — additionally inspected local `git log`; current HEAD b5d42d9467f30edf027700ad0cc0a4897d3c2079 |
| S3 | [Frontend exact dependency versions](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/frontend/package.json) |
| S4 | [Backend dependency declarations](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/backend/pyproject.toml) |
| S5 | [Adapter dependency lock](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/whatsapp-adapter/requirements-runtime-lock.txt), [Dockerfile](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/whatsapp-adapter/Dockerfile) |
| S6 | [Evidence acceptance engine](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/backend/app/services/verify/engine.py), [public schemas](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/backend/app/schemas/models.py) |
| S7 | [Fictional UI fixture set](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/frontend/src/lib/fixtures/synthetic.json) |
| S8 | [Policy results and limitations](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/backend/evaluation/policy-results.json), [cases](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/backend/evaluation/cases.json) |
| S9 | [Actual fictional before/after results](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/backend/evaluation/avoidable-results.json) |
| S10 | [Latest 440-test and live recovery record](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/docs/gemini-503-recovery-20261012.md), [actual recovery JSON](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/backend/demo-output/provider-recovery-20261012T145800133235Z.json), [availability tests](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/backend/tests/test_gemini_availability.py) |
| S11 | [Assessment validation, 65 frontend tests and live failure](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/docs/assessment-failure-20261012.md), [results rendering](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/frontend/src/components/results.tsx) |
| S12 | [Evidence ledger and source eligibility](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/backend/app/services/search/ledger.py), [investigation](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/backend/app/services/search/investigation.py) |
| S13 | [URL extraction](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/backend/app/services/extract/url.py), [fixture generator](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/backend/scripts/make_demo_fixtures.py), [native tool setup](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/backend/README.md) |
| S14 | [Five-format actual acceptance](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/docs/formats-restart-acceptance-20261012.md), [private saved image result](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/backend/demo-output/image-result-20261012T144144365527Z.json) |
| S15 | [Private report schema/RLS](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/supabase/migrations/202610110001_private_reports.sql), [receipt validation](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/frontend/src/lib/history/receipt.ts) |
| S16 | [Retention scheduler migration](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/supabase/migrations/202610110002_retention.sql) |
| S17 | [Reviewer allowlist migration](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/supabase/migrations/202610110003_alert_reviewers.sql) |
| S18 | [Alert engine](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/backend/app/services/alerts/engine.py), [clustering](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/backend/app/services/alerts/clustering.py), [encrypted SQLite repository](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/backend/app/services/alerts/sqlite_repository.py) |
| S19 | [Actual integration gates and remaining steps](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/docs/final-integration-20261012.md), [hosted acceptance](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/docs/hosted-integration-acceptance-20261011.json) |
| S20 | [Windows startup/deployment scope](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/docs/windows-startup.md), [offline CI](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/.github/workflows/person2-offline.yml), [mock runner](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/frontend/scripts/dev-mock.mjs) |
| S21 | [Adapter database definitions](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/whatsapp-adapter/truthlens_whatsapp/store.py), [outbound validation](D:/HackOnTrack-TruthLens/.worktrees/scam-alert-intelligence/whatsapp-adapter/outbound-validation-report.md) |
