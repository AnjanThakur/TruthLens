# TruthLens full-system acceptance - 11 October 2026

**Latest, 12 October:** [final integration and teammate handoff](final-integration-20261012.md)
and [actual status JSON](final-integration-20261012.json) supersede current-origin
and test counts below: backend 350, adapter 140, frontend 59 offline tests PASS.
Current preview is localhost:3001. No new provider calls or WhatsApp sends.
Dynamic delivery and hosted authenticated acceptance remain BLOCKED; no public
production deployment exists. Earlier live results below remain historical.

## Latest provider-free integration follow-up

See [actual hosted follow-up statuses](hosted-integration-acceptance-20261011.json)
and [changes, verification and owner steps](hosted-integration-followup.md).
The port-3001 preview reuses the original project/private signing key and now
prevents caching auth callback redirects. The WHO optional-source status rule is
corrected with warnings and evidence guards retained. Targeted offline checks:
192 backend tests, 24 frontend tests, Ruff, mypy, lint, typecheck and build PASS.
No new provider calls or remote writes. Hosted authenticated history/reviewer/
retention/alert mutations remain BLOCKED by the documented prerequisites; an
anonymous reviewer 404 does not prove the table is missing. The original live WHO
result below remains unchanged. The following full-system baseline predates this
follow-up and is retained as historical evidence.

Branch: `feature/scam-alert-intelligence`. Tested implementation commit: `9f16d4c4e70f2da218ec82b6def200cf29108a0f`.
Worktree: `D:\HackOnTrack-TruthLens\.worktrees\scam-alert-intelligence`.
The final documentation commit is additional; use `git rev-parse HEAD` for the delivered tip.
Main and the owner's uncommitted changes/private configuration were preserved. No reset, main merge or force push was performed.

## Actual component status

| Component | Offline/local result | Fresh live acceptance |
|---|---|---|
| Backend extraction, investigation and guards | **PASS** - 334 tests; Ruff; mypy 47 files; pip compatibility; exact existing OpenAPI contract | **PASS** for one grounded live text decision; strict pipeline **FAIL** (partial DNS limitation); other formats **NOT TESTED** |
| Website | **PASS** - 53 unit/contract/RLS tests, 24 desktop/mobile/accessibility checks, six production-proxy browser checks; lint/typecheck/format/build | **PASS** for actual local HTTP/proxy health and honest provider-disabled errors; one grounded factual result **PASS**; strict pipeline **FAIL** (partial) |
| Supabase private history | **PASS** for isolated actual SQL ownership/RLS tests and local configuration presence; hosted anonymous read rejected 401/42501 | Authenticated sign-in/save/list/delete **NOT TESTED**; no email sent or existing table modified |
| Hosted alert reviewer authorization | **PASS** for additive SQL RLS and server role tests | **BLOCKED** - anonymous REST returned 404/PGRST205; authenticated/administrator inspection needed before inferring table absence or changing grants |
| Scam alerts | **PASS** - encrypted isolated persistence/restart/withdrawal; evidence-gated recurrence/drafts/review; website consent and authenticated server proxies | Authenticated hosted contribution/review **BLOCKED** pending legitimate session, reviewer authorization and genuine consented records |
| WhatsApp inbound | **PASS**, previously proven signed webhook HTTP 200 and durable queue; all offline signature/state/command regressions pass | New inbound **NOT TESTED** this phase |
| WhatsApp development template | **PASS**, prior HTTP 201 + actual delivered state + signed callback + owner phone receipt | No new outbound attempt this phase |
| WhatsApp dynamic fact-check report | Formatter/backend integration **PASS** offline | **BLOCKED** by confirmed trial ContentSid restriction; fixed template is not a dynamic report |
| Meta alternate transport | Existing implementation preserved | **BLOCKED** by prior account restriction; no account action or send attempted |
| Windows startup | **PASS** - preflight, occupied-port detection, owned-process graceful restart, backend/alerts/website health and paused worker standby | Public deployment/ngrok reconfiguration **NOT TESTED**; existing tunnel/adapter preserved |

Current local feature services: backend `127.0.0.1:8000`, alerts `127.0.0.1:8001`, website `127.0.0.1:3001`. Gemini/Tavily are disabled in those backend child processes. The owner's port-3000 website and port-8100 adapter remain untouched. The worker standby was started, confirmed paused, then cleanly stopped; no job was claimed or outbox retried.

## Implemented fixes and evidence

| Root cause | Exact change | Regression result |
|---|---|---|
| A single initial query could miss relevant evidence | Deterministic primary-authority, independent corroboration, explicit contradiction and conditional alternate/PDF stages; deduplicate queries/URLs; actual attempt budgets | **PASS** - delayed source recovery, mandatory contradiction, bounded fallback/search errors |
| Low Tavily score could promote an unreviewed page above an official source | Reviewed institution identity ranks before search score; expand explicit ECI/court/tax/scheme registry; lookalikes and arbitrary government-looking domains remain untrusted | **PASS** - low-score official and missing-institution cases; fake/snippet-only evidence rejected |
| Any rupee price could trigger an RBI banknote search | Currency authority selection requires banknote/legal-tender scope; choose relevant UIDAI/ECI/court/health authority and preserve jurisdiction | **PASS** - price false positive, banknotes, HI/MR authorities, non-India and WHO regressions |
| Natural calendar event dates failed an ISO-only witness check | Only explicit ISO or unambiguous full English calendar dates in a verbatim quoted passage can validate an ISO temporal witness; publication dates never become event dates | **PASS** - genuine chronological fixture becomes outdated; impossible/ambiguous dates rejected |
| Relative dates lost the original message time and cache date context | Optional validated original timestamp header, website local-time input, signed adapter timestamp forwarding; IST resolution for India; cache includes timestamp and local day | **PASS** - next Monday across dates, EN/HI/MR, ambiguous Hindi kal retained unresolved, IST midnight and body-contract preservation |
| Repeated pages could be fetched repeatedly or appear newly retrieved | Cache only readable complete safe pages, retain original retrieval time and isolate per-claim assessments; mark identical syndicated passages as one origin | **PASS** - cache-hit fetch count, immutable timestamp, independent assessment and duplicate-passages tests |
| Tavily exhausted limits were classified too generally | Recognize 402/432/433 quota versus 429 transient rate limit, cooldown repeated queries, retain bounded transient retries and count actual attempts including retries | **PASS** - mocked statuses produce one HTTP attempt, cache hits cost zero; Gemini daily fail-fast/503 recovery remain passing |
| Unconfirmed and technical failures looked alike or repeated generic warnings | Keep completed/partial/error contract; claim-specific unresolved reasoning, human warnings, readable checked dates; concise eligible sources and full detailed ledger | **PASS** - six categories, complete/partial/error UI, irrelevant/neutral/unreviewed sources, EN/HI/MR immutable verdict tests |
| Alerts existed only as an unconnected memory service | Optional separate Fernet-encrypted SQLite repository; signed-report opt-in, stable authenticated source/submission IDs, withdrawal, role-gated draft dashboard | **PASS** - atomic rollback, wrong-key fail closed, restart, concurrent instances, RLS, trust/role/consent/version gates |
| Windows generated env escaping could corrupt a database path | Escape local env strings correctly; preserve stable encryption/pseudonym secrets; refuse key/path mismatch and shared WhatsApp database | **PASS** - startup/restart reopened isolated alert state; original WhatsApp paths/keys unchanged |

`guard_decision()` remains mandatory. No publisher/domain identity alone proves a claim, no missing evidence proves falsity, no snippet-only decisive verdict is accepted, and scam-risk heuristics do not determine factual truth. Source-specific stance, direct relevance, exact excerpts, context and temporal witnesses remain validated.

The default settings now allow four stage queries, at most eight actual search attempts and twelve model attempts per verification, with existing bounded concurrency, fetch caps/timeouts and safe redirect/DNS validation. An explicit legacy private `MAX_SEARCH_QUERIES_PER_CLAIM=1` still selects one-query cost mode; update that setting deliberately to enable fuller ordinary investigation. The controlled acceptance runner explicitly uses primary + contradiction within its two-search lifetime ceiling.

## Avoidable abstention comparison and evaluation

`backend/evaluation/avoidable-results.json` records identical fictional evidence run against actual preserved main code and new feature code. **Four avoidable cases fixed**: official score ranking, initial empty query, missing reviewed institution and explicit natural event dates. These are software regressions, not four real-world forwards or a population accuracy improvement.

`backend/evaluation/cases.json` has 14 independently labeled fictional cases with source-level justifications. Predictions are separately supplied adversarial proposals; the prediction function never reads expected labels. Actual guard evaluation: **14/14 PASS**. Supports: verified 2, false 2, partially_true 1, outdated 1, misleading_context 1, unconfirmed 7. Each fixture-category precision/recall is 1.0; confusion matrix is diagonal with those counts; abstention rate is **50%**. Full matrix is in `policy-results.json`.

Seven cases remain correctly unresolved: unknown facts, credible unresolved conflict, fake/unreviewed support, inaccessible snippet-only support, wrong-subject evidence, duplicated unreviewed support and an unsupported claim qualification. This tiny deterministic policy set does **not** evaluate Gemini prediction accuracy or live search factual accuracy.

## Five formats and three languages

| Input | Current deterministic/native/proxy checks | Earlier real provider report | Fresh full live check |
|---|---|---|---|
| Text | **PASS** | **PASS**, recorded 04:43 acceptance | Grounded verdict/rendering **PASS**; strict pipeline **FAIL** (partial) |
| Screenshot/image | **PASS** - native OCR plus mocked verification | **PASS**, recorded 04:43 acceptance | **NOT TESTED** |
| WAV/audio | **PASS** - native media validation and mocked transcription/503 recovery | Latest **FAIL** at transcription: `llm_provider_error`, `transient_server`; earlier real WAV transcription had passed | **NOT TESTED** |
| Scanned PDF | **PASS** - bounded OCR/page/chunk context and structured-response checks | **PASS**, recorded 04:43 acceptance | **NOT TESTED** |
| Public URL | **PASS** - safe redirects/HTML/JS-only/PDF/Unicode/date regressions | **PASS**, selective 05:24 report after earlier failure | **PASS** for extraction only: actual WHO constitution page returned HTTP 200, 2,330 characters, original event date present, no warnings; full factual check **NOT TESTED** |

Earlier records are private existing main `backend/demo-output/acceptance-20261011T044352197204Z.json`, `acceptance-20261011T052429704146Z.json` and `final-person1-20261011.json`. They were inspected read-only and were not copied into this source commit or relabeled as new results. Their earlier provider counts are not charged to this phase.

English, Hindi and Marathi: **PASS** for deterministic explanations, UI/formatter invariants and installed native OCR languages. Fresh end-to-end model translation and multilingual voice transcription: **NOT TESTED**. No unsupported format is claimed live PASS.

## WhatsApp limits and commands

The confirmed free-form path returned HTTP 400 / numeric Twilio code **21654** (`ContentSid Required`). HTTP status/numeric code alone are safely logged; credentials, phone numbers, message bodies and full API responses are excluded. Malformed/success-uncertain responses are not blindly retried. The exact development connectivity response may use the configured ContentSid only in test/development mode with backend consumption disabled; no Body or ContentVariables is sent. HELP, SOURCES, language selection, STOP, START and factual/error reports cannot silently become that template.

The prior separately approved template was actually delivered and received. That approval is exhausted. Commands HELP/SOURCES/HINDI/MARATHI/ENGLISH/STOP/START pass offline; dynamic command replies on this account remain blocked like other free-form replies. No existing failed item was retried.

Official current trial guidance: [Try out WhatsApp](https://www.twilio.com/docs/usage/trials/try-out-whatsapp), [Trial account guide](https://www.twilio.com/docs/usage/tutorials/how-to-use-your-free-trial-account). Do not place arbitrary generated reports in template variables. A supported free-form-enabled account/channel and fresh owner authorization are required for real dynamic delivery; no upgrade was purchased and no Meta fallback enabled.

## Hosted integration actions

1. Owner/project administrator applies `supabase/migrations/202610110003_alert_reviewers.sql` to the intended project, then grants only selected existing auth users a reviewer row. Ordinary signed-in users cannot self-grant or alter roles. No existing report table is changed by this migration.
2. Verify the project's allowed callback origin for the feature website, sign in intentionally, and test authentic report save/list/delete and consented alerts. No email/session/remote database write was initiated by this implementation phase.
3. The Windows launcher privately generates/reuses isolated local alert secrets in ignored `.tmp/runtime/secrets.env`, reads main private frontend/backend configuration, and injects matching server-only alert credentials into its website/alert processes. Never share or regenerate these stable keys while retained state exists. Other deployment mechanisms must configure the corresponding documented env variables themselves.
4. Keep one website process for consent/withdrawal serialization. Multi-replica deployment requires distributed per-principal serialization/withdrawal tombstones; not claimed production-ready here.
5. Cross-language recurrence is conservative for the existing supported EN/HI/MR narrative catalogue and optional local embedding adapter, not universal cross-language semantic detection. Counts describe consenting retained submissions, not WhatsApp-wide prevalence.

## Startup and selective acceptance

See [Windows startup](windows-startup.md) for exact preflight, dependency and rollback commands. Default startup disables provider consumption and outbound sending in child processes without rewriting private `.env` files. The paused worker service is a standby, not an unrestricted queue processor. Do not restart a consuming worker until its account configuration and separate approval permit it.

Approved and executed live proposal (approval used once): one English adult text claim, **"The World Health Organization was established on 7 April 1948."** Primary reference: [WHO Constitution](https://www.who.int/about/governance/constitution). Safe real extraction of that page already succeeded without Gemini/Tavily. The normal search still has to retrieve relevant real evidence; the known page is not injected as fabricated search output.

Nominal usage: two Gemini calls (claim extraction and grounded assessment), two Tavily searches (primary and contradiction), zero Twilio sends. Enforced process-wide ceilings **5 Gemini attempts / 2 Tavily attempts / 0 Twilio**, including retries. Use isolated backend 8002 and website 3002; leave existing services running. Stop on daily quota exhaustion and record actual errors/partial results rather than substituting fixtures. Independently record website rendering and factual evidence acceptance. Rollback stops only controlled instances, leaving provider-disabled 8000/3001, the paused worker and existing encrypted WhatsApp state intact.

**Actual new usage: Gemini 2 / Tavily 2 / Twilio 0.** Public source research, one safe primary-page download, anonymous non-writing Supabase checks and local mocked HTTP are outside those paid-provider counts. The approved single-text phase has now run; actual results are recorded below. Other fresh live formats remain **NOT TESTED**. Hosted CI is prepared but execution after push is **NOT TESTED**.

## Actual newly approved one-claim acceptance

The owner approved exactly one WHO text test after offline validation. Executed through the actual browser on isolated website 3002 and controlled backend 8002. Actual use: **2 Gemini attempts / 2 Tavily attempts / 0 Twilio sends**, with no second submission, translation or fallback. See [sanitized actual result](live-website-acceptance-20261011.json). Private full API result and actual screenshot remain ignored in `.tmp/live-who-website.json` / `.tmp/live-who-website.png`.

- **PASS: website rendering and grounded factual verdict.** HTTP 200, one anchored claim, `verified`, visible explanation and two eligible fetched WHO primary sources: `https://www.who.int/hongkongchina/about-us` and `https://www.who.int/about/governance/constitution`. Their actual passages establish 7 April 1948. No publication date was invented for either undated page.
- **FAIL: strict complete-pipeline acceptance.** Status was `partial`, warning `source_page_unavailable:url_dns_error`. A contradiction-search Wikipedia result could not resolve through the local DNS path and was retained only as unreviewed `search_excerpt`. It was not eligible to establish the verdict and was excluded from concise verdict sources. This external fetch limitation is not proof the claim is false or an established backend extraction defect.
- **PASS: rollback.** Only controlled 8002/3002 instances stopped. Ordinary provider-disabled 8000/3001 and isolated alerts 8001 continue; the owner's existing website, adapter, tunnel and encrypted WhatsApp state were preserved. Consuming worker remains paused.
- **PASS offline: post-live presentation regression.** The detailed ledger explicitly labels unavailable search excerpts as non-decisive in EN/HI/MR. This corrects a presentation gap seen in the real result; no additional provider request was made to retest it.

This newly approved result establishes only fresh text/website acceptance: factual verdict/rendering PASS, strict full pipeline FAIL (partial). Image, audio, PDF, URL full verification, translations and dynamic WhatsApp remain NOT TESTED or BLOCKED as documented. No ongoing blanket approval remains; further paid tests need new approval.
