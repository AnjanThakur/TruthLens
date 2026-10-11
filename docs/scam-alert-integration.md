# Scam Alert Intelligence: Person 2 handoff

## Current integrated implementation (11 October 2026)

The website now provides explicit signed-report contribution consent, withdrawal and authenticated role-gated `/alerts` review with manual draft creation/edit/submit/approve/reject. Role identity and stable source/submission pseudonyms are derived server-side, not accepted from the browser. Configure server-only `ALERTS_BASE_URL`, `ALERTS_INGEST_TOKEN`, `ALERTS_ADMIN_TOKEN`, and stable `ALERTS_SOURCE_SECRET`, alongside existing Supabase/history settings. The Windows runner shares these privately between the website and isolated alert service.

New additive migration `supabase/migrations/202610110003_alert_reviewers.sql` creates only a reviewer role allowlist; existing Person 2 report tables are untouched. A project administrator must apply it and grant selected existing auth users. The hosted read-only preflight returned **404/PGRST205**; authenticated review is blocked until that action and a real session check. Ordinary authenticated users have read-own-role only and cannot self-grant roles.

Set paired `ALERTS_DATABASE_PATH` and `ALERTS_ENCRYPTION_KEY` for the new encrypted SQLite repository; preserve the original key across restarts/backups. Memory remains the unconfigured/default test implementation. Local durable storage is separate from WhatsApp and Supabase history. BEGIN IMMEDIATE transactions serialize repository instances; ciphertext stores minimized redacted observations, drafts and receipts. New persistence regressions cover restart/withdrawal, rollback, wrong keys and concurrent instances.

The single-process website serializes contribution/withdrawal per authenticated principal with bounded waiting. Multi-replica integration requires distributed serialization/tombstones before deployment. Cross-language matching remains conservative for the existing supported narrative catalogue and optional local embedder. Alerts are never automatically published or sent; approval only retains a reviewed candidate. This functionality is source/offline/local PASS, not a claim of hosted authenticated acceptance. See [full-system acceptance](final-full-system-acceptance.md) and [Windows startup](windows-startup.md).

The earlier service-only handoff below is historical where it describes missing website integration or memory-only operation.


This feature consumes **already fact-checked, explicitly consented claim records** and prepares reviewable alert drafts. It observes this retained submission sample only. It neither monitors WhatsApp globally nor publishes messages. No Gemini, Tavily, Meta or Supabase calls are made by the default alert engine.

## Isolation and compatibility

Feature branch: `feature/scam-alert-intelligence`. Development worktree: `D:\HackOnTrack-TruthLens\.worktrees\scam-alert-intelligence`. Base commit: `153af610d9ccb9a761eca6bdb6361da5791358d4`.

The original `app.main:app`, verification endpoints, schemas, public OpenAPI snapshot, frontend, Person 2 database and Meta configuration are unchanged. The new `app.alerts_app:app` runs on a separate port. Its separate OpenAPI snapshot is [scam-alert-openapi.json](scam-alert-openapi.json); it does not replace `backend-openapi.json`. Person 2 can proxy `/api/alerts/*` through a trusted server after integrating the feature. Do not expose the service bearer tokens to browsers or chat users.

## Architecture and reuse

| Component | Responsibility |
| --- | --- |
| `backend/app/services/alerts/models.py` | Strict additive Pydantic ingestion, cluster, draft, review and export schemas |
| `settings.py` | Authentication, retention, capacity, evidence age and heuristic settings |
| `privacy.py` | Claim/excerpt redaction, HMAC source pseudonyms and protected numeric/entity anchors |
| `clustering.py` | Conservative EN/HI/MR lexicon matching; optional injected local multilingual embedder |
| `evidence.py` | Existing evidence ledger publisher identity and URL validation; freshness/provenance/stance gates |
| `content.py` | Authored EN/HI/MR safety wording, fingerprints and manual Channel text |
| `engine.py` | Atomic deduplication, clustering, trend detection, draft lifecycle and source withdrawal |
| `repository.py` | Repository protocol, transaction rollback and isolated in-memory implementation |
| `backend/app/alerts_app.py` | Dedicated service authentication, role separation, bounded request bodies, sanitized errors and retention sweep |
| `backend/scripts/demo_alerts.py` | Fictional offline three-language demonstration; simulated approval; no publishing |

The service reuses `VerificationResult` / `ClaimResult` / `Evidence`, existing Unicode normalization, `risk_for()` rule identifiers, `canonical_url()` and the reviewed ledger domain registry. Claim extraction, searches and fact-checking happen upstream through the existing backend; ingestion never re-verifies claims or spends provider credits. The transient request may contain the existing verification record, but the repository keeps only minimized individual claims and evidence snapshots, not the entire input, original spans, model explanations or raw source token.

An independent source means an independently authenticated consenting submitter in the upstream integration. Person 2 must assign a stable random UUIDv4 **per principal**, retained only as needed to support deduplication and withdrawal. A new random source per message would falsely inflate independence. A random submission UUID is per delivery and provides idempotency. Never pass a phone number, WhatsApp chat ID, hash of a phone number, or Meta message ID as either field.

## Configuration and startup

Put alerts configuration in the isolated backend `.env` or server environment. No Gemini/Tavily credentials are required. All three secrets must be different and at least 32 characters. Generate strong random secrets in your server's secret manager; never print or commit them. An entirely unconfigured service starts but protected routes return `503 alerts_not_configured`. Partial/invalid configuration aborts startup with a sanitized message.

| Environment variable | Default | Meaning |
| --- | --- | --- |
| `ALERTS_INGEST_TOKEN` | empty | Producer service credential: ingest and withdraw only |
| `ALERTS_ADMIN_TOKEN` | empty | Trusted dashboard server credential: review, list and export |
| `ALERTS_PSEUDONYM_SECRET` | empty | HMAC-SHA256 key for source/numeric/entity guards |
| `ALERTS_MIN_INDEPENDENT_SUBMISSIONS` | 3 | Recurrence threshold; range 2–100 |
| `ALERTS_TREND_WINDOW_HOURS` | 24 | Counting window; range 1–168 |
| `ALERTS_BASELINE_DAYS` | 7 | Previous baseline period; range 1–30 |
| `ALERTS_GROWTH_RATIO` | 2 | Increasing if window count exceeds scaled prior daily baseline by this ratio |
| `ALERTS_EVIDENCE_MAX_AGE_HOURS` | 48 | Maximum evidence/check age; range 1–168 |
| `ALERTS_DRAFT_TTL_HOURS` | 12 | Draft validity, capped by oldest usable check/evidence expiry; range 1–48 |
| `ALERTS_RETENTION_DAYS` | 14 | Original first-seen retention, never extended by repeat submissions; range 2–90 |
| `ALERTS_PURGE_INTERVAL_SECONDS` | 60 | Standalone app retention/expiry sweep; range 1–3600 |
| `ALERTS_MAX_OBSERVATIONS` | 5000 | Local retained observation cap; idempotency receipt cap is twice this |
| `ALERTS_MAX_CLUSTERS` | 1000 | Local cluster cap |
| `ALERTS_MAX_DRAFTS` | 2000 | Local draft cap |
| `ALERTS_EMBEDDING_SIMILARITY` | 0.93 | Optional local embedding cosine threshold |

Retention must cover the baseline plus the counting window. Growth comparison scales baseline counts to the configured window duration; a zero baseline does not establish growth. Financial, identity and OTP warning rules are reported independently of verdict. Defaults are initial heuristics, not scientifically validated outbreak statistics.

Run the existing verification backend on port 8000 as before. Start alerts separately with **one worker** while using the memory adapter:

```powershell
Set-Location D:\HackOnTrack-TruthLens\.worktrees\scam-alert-intelligence\backend
& D:\HackOnTrack-TruthLens\backend\.venv\Scripts\python.exe -m uvicorn app.alerts_app:app --host 127.0.0.1 --port 8001 --workers 1 --no-access-log
```

Swagger: `http://127.0.0.1:8001/docs`. Health: `GET /health`, unauthenticated; reports configuration and `publishing: false`, not provider quota. Keep the service on a private interface, use TLS and rate limits at the trusted gateway, disable request/body/query/header logging there too. The app limits actual bodies to 256 KiB with a ten-second receive deadline, redacts validation diagnostics, sends `Cache-Control: no-store`, and logs only exception class for unexpected errors. CORS is intentionally absent; browser traffic goes through Person 2's authenticated server.

## API contracts

All protected requests use `Authorization: Bearer <server-held credential>`. Missing/invalid credentials return 401; a credential for the wrong role returns 403. Authentication and schema errors never echo private request values. Domain errors have `{"error":{"code":"...","message":"...","request_id":"<uuid>"}}`; unexpected failures return a sanitized 500.

| Method/path | Role | Payload / result |
| --- | --- | --- |
| `POST /api/alerts/ingest` | ingest | `IngestRequest` → `IngestResponse` |
| `POST /api/alerts/withdraw` | ingest | `{"source_token":"<UUIDv4>"}` → deleted observation count |
| `GET /api/alerts/clusters` | admin | Cluster list, evidence including contrary/ineligible findings, sample trend |
| `GET /api/alerts/drafts` | admin | Draft list including pending language and review history |
| `POST /api/alerts/clusters/{cluster_id}/drafts` | admin | `{"language":"en"}` (`hi` / `mr` supported) → draft or 409 deferred |
| `PATCH /api/alerts/{alert_id}` | admin | Expected version, title, claim summary, explanation and optional `translation_reviewed` |
| `POST /api/alerts/{alert_id}/submit` | admin | `{"expected_version":1}` → pending review |
| `POST /api/alerts/{alert_id}/approve` | admin | Expected version, reviewer UUID, literal boolean `evidence_reviewed:true` |
| `POST /api/alerts/{alert_id}/reject` | admin | Expected version, reviewer UUID, structured rejection reason |
| `GET /api/alerts/{alert_id}/export` | admin | Current approved text only; otherwise 409 |
| `POST /api/alerts/purge` | admin | Immediate retention/expiry sweep → deleted observation count |

`reviewer_id` is an assertion by the **trusted dashboard server**, not per-user authentication in this local adapter. The server must authenticate the reviewer with Supabase/session auth, authorize their reviewer role, and derive their UUID from that session. Never forward a browser-supplied identity unchecked. Static tokens authenticate services only; deployment-grade per-user role enforcement belongs in that trusted server/adapter.

Ingestion example using an actual result already returned by `/api/verify`:

```python
payload = {
    "consent": True,  # literal boolean; capture informed opt-in upstream
    "submission_id": str(uuid4()),
    "source_token": stable_random_source_uuid_for_this_consenting_principal,
    "verification": existing_verification_result.model_dump(mode="json"),
}
```

Example response (illustrative IDs):

```json
{
  "submission_id": "164e2ad8-5099-48ce-b127-d969f55f28a8",
  "duplicate": false,
  "cluster_ids": ["a77b3a87-7318-48ed-9b9c-685b1115fdac"],
  "draft_ids": [],
  "deferred_reasons": ["trend_threshold_not_met"]
}
```

One source's repeated deliveries do not increase counts. Identical submission-ID replay is acknowledged; a changed minimized record/source under that ID returns 409. A new delivery can refresh an existing source's evidence without adding independence. Older checks cannot replace newer observations. The first observation time stays fixed and controls counting/retention.

Approval example:

```json
{
  "expected_version": 1,
  "reviewer_id": "818f7217-7684-43dd-a495-6bc3d1e85a14",
  "evidence_reviewed": true
}
```

Rejection reasons: `insufficient_evidence`, `translation_needed`, `incorrect_content`, `other`. Rejection is terminal for that draft ID, with reason retained; a fresh draft may be explicitly prepared from newer evidence. Edit requests include all three text fields, reject recognized PII/URLs/blank text, increment the version and revoke approval. `translation_reviewed:true` permits a human-written pending translation to become ready. These endpoints do not let editors change the evidence-based status or source links.

Export has `alert_id`, `content_version`, `language`, `channel_text`, `approved_at`, `reviewer_id`, `expires_at`, and `mode: "manual_copy_only"`. Re-fetch immediately before copying. Exporting is not publishing and cannot recall text already copied externally.

## Evidence and lifecycle

Require threshold activation and fresh reviewed-domain HTTPS evidence from the existing trusted verifier pipeline, `excerpt_provenance: fetched_page`, direct relevance and relevance score at least 0.5. Reject unsafe/credential-bearing/private-identifier URLs; do not fetch any supplied URL here. Existing SSRF/network protections stay in the upstream fetcher. Registry identity establishes publisher identity, not factual truth; a valid URL alone cannot prove a submitted excerpt was fetched. Only the trusted backend may assert verification provenance.

| Retained verdicts / relevant evidence | Result |
| --- | --- |
| False claims with contradictory evidence | `claim_contradicted`; explicitly does not establish criminal fraud |
| Partially true / misleading context with context evidence | `claim_needs_context` |
| Outdated with context evidence | Needs two distinct source URLs and two quoted source event dates; publication dates alone do not suffice |
| Unconfirmed with relevant context and known warning rules | `suspicious_indicators`; underlying claim stays unconfirmed |
| Verified, conflicting decisive support/opposition, stale/incomplete/insufficient evidence | Defer public draft |
| Partial result or any verification warning, including provider errors | Defer public draft conservatively |

Supporting and contradicting snapshots remain visible even if they share an evidence ID; a conflict cannot disappear through ID-based deduplication. Published/modified date metadata remains separate from retrieved/check dates and quoted event dates. Evidence eligibility is recorded at ingestion; re-evaluate freshness by timestamp during review. Historical samples inform the baseline; today's evidence gate uses the current counting cohort. Any stale/failed member in that cohort suppresses a warning.

States: `draft` → `pending_review` → `approved` or `rejected`; stale/threshold-invalid content becomes `expired`. Unknown/missing target-language claim text yields `language_content_status: pending_translation` and a null summary, with approval/export blocked. Static safety/status wording is authored in EN/HI/MR. An observed same-language variant supplies the claim summary; the engine does not invent its translation.

Approval binds reviewer, UTC time, content version/hash and evidence/sample fingerprint. Edits, refreshed evidence, new independent sources and changed counting-window membership revoke approval. Refresh the draft and re-review the current version. A stale browser version returns 409. The fingerprint excludes last-seen refresh time and source pseudonym; identical evidence replay does not require pointless review. Expiry is checked on every service operation and by the standalone sweep. The local review history is capped at 32 records per retained draft.

No status here is `confirmed_fraud`. A false message or a high heuristic risk score is not proof of a criminal scam. That stronger claim would require an explicit independently reviewed institutional finding and a separate approved policy/contract; this feature intentionally does not infer it.

## Supabase storage integration contract (Person 2 to implement)

No existing database/schema/migration was modified. Implement `AlertRepository.transaction() -> AbstractContextManager[AlertState]`. It must atomically load/commit the minimized state, roll back exceptions and return isolated values. The local reference uses an `RLock` and deep copies; it is **ephemeral, single-process, not production persistence**. A Supabase adapter needs server-side transactional RPC/locking or equivalent serializable transactions, not independent REST writes that can race between count/approval/export. Start with a small isolated alert schema; scale by implementing equivalent row-level transactions/indexes and pagination behind the repository boundary.

Suggested new tables, without altering Person 2's existing tables:

| Proposed table | Columns / invariants |
| --- | --- |
| `alert_clusters` | UUID PK; canonical redacted claim, first/last time, cached sample counts/trend/status; counts always recomputed from retained observations |
| `alert_observations` | UUID PK; cluster FK, source HMAC, redacted claim/language/verdict, first/last/check times, quality flag, recognized rule IDs, HMAC numeric/entity guards, ISO event dates; UNIQUE(cluster_id, source_hash) |
| `alert_evidence_snapshots` | Observation FK; evidence UUID, canonical URL, reviewed publisher, redacted excerpt, stance, retrieved/published/updated times, initial eligibility/issues; preserve conflicting snapshots |
| `alert_submission_receipts` | Submission UUID PK, source HMAC, minimized payload digest, cluster UUIDs, server receipt time; supports conflict checks and withdrawal |
| `alert_drafts` | Draft UUID PK, cluster FK, all `AlertDraft` fields, version, evidence fingerprint and language state; at most one active draft per cluster/language |
| `alert_reviews` | Draft FK, reviewer UUID, UTC time, version/hash/fingerprint, reviewed flag, approved/rejected action and optional rejection reason; capped/retained as local contract |

Use server-only RLS/service access for observations, HMAC anchors and receipts; dashboards read minimized public models through their server. Service-role credentials never belong in `NEXT_PUBLIC_*`. Encrypt storage/backups, apply retention to evidence and derivative drafts too, and schedule purge at least as often as configured. Withdrawal must delete that source's observations/receipts and **all related drafts/reviews** that could carry its wording, then recompute remaining clusters atomically. Retention expiry also deletes derivative drafts in affected clusters. Rebuild new drafts from the remaining consenting cohort when appropriate. Do not orphan evidence/reviews in backup/export paths.

Pseudonyms and protected anchors are linkable **pseudonymization, not anonymization**. Keep the HMAC secret and upstream consent/source mapping access-restricted; do not expose pseudonyms in API responses. Purge/migrate atomically when rotating the HMAC key to avoid double-counting a source under two secrets. UUID reviewer identifiers can themselves be personal data and require access/retention controls.

## WhatsApp chatbot, dashboard and Channel workflow

1. Person 2's chatbot explains optional retained trend analysis and obtains explicit opt-in; verification still works without consent. Confirm withdrawal by the authenticated user's stable source mapping. Do not ingest nonconsented records.
2. Reuse the existing verifier result, authenticated on the trusted server. Do not accept client-authored evidence/verdicts as trusted records. Ingest only the necessary result; avoid logging bodies or storing a second raw conversation copy.
3. Dashboard cluster screen: canonical/observed language variants, sample scope, independent window count, baseline, heuristic severity, evidence stances/timestamps and deferral status. Do not display a global infection/outbreak metric.
4. Draft queue: language, pending translation, lifecycle, version, expiry, source links; editor screen must show conflicting findings and PII checks. Authenticate actual reviewer identity on the server.
5. Reviewer opens the actual institutional pages, checks relevance/quotes/dates, wording/translation/privacy and uncertainty, submits and explicitly approves current evidence/content. A generic checkbox without actual review is insufficient operationally.
6. Approved preview/copy screen calls export immediately before copying. A human Channel administrator pastes the concise text into the official WhatsApp Channel interface. Show expiry and reviewer/version. No automated sender or unofficial interface is implemented.
7. Later source changes revoke export eligibility, but cannot recall externally pasted posts. Person 2 needs a manual correction/withdrawal process for copied posts and appropriate privacy handling of any downstream copies.

## Complete offline demonstration and validation

From this feature worktree's `backend`, using the existing shared virtualenv:

```powershell
New-Item -ItemType Directory -Path .tmp -Force | Out-Null
& D:\HackOnTrack-TruthLens\backend\.venv\Scripts\python.exe -m scripts.demo_alerts --output .tmp/alerts-demo.json
& D:\HackOnTrack-TruthLens\backend\.venv\Scripts\python.exe -m pytest tests/test_alerts.py -q -p no:cacheprovider
$env:TEMP=(Resolve-Path .tmp).Path
$env:TMP=$env:TEMP
$env:TESSDATA_DIR='D:\HackOnTrack-TruthLens\backend\.runtime\tessdata'
& D:\HackOnTrack-TruthLens\backend\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
& D:\HackOnTrack-TruthLens\backend\.venv\Scripts\python.exe -m ruff check app tests scripts
& D:\HackOnTrack-TruthLens\backend\.venv\Scripts\python.exe -m mypy app
& D:\HackOnTrack-TruthLens\backend\.venv\Scripts\python.exe -m pip check
```

The demo creates three independent random sources, clusters English/Hindi/Marathi variants, prepares each language, **simulates** reviewer approval, generates manual-only export, and withdraws one source to delete all related drafts. Source URLs/content are labeled fictional test fixtures, not actual institutional findings. Never publish the demo text. Inspect `.tmp/alerts-demo.json` for complete sample records and structured draft/export output. The integration tests exercise the HTTP review/authorization flows without starting a network server or calling providers.

For a local HTTP fixture exercise, use `fixture_record()` from `scripts.demo_alerts` and POST three `IngestRequest` bodies with different stable fixture source UUIDs to the local alerts server. `SecretStr.model_dump()` masks source tokens by design: the trusted outbound sender must explicitly set `payload["source_token"] = request.source_token.get_secret_value()` before sending. List drafts with the admin server credential, submit the current version, approve with a reviewer UUID and actual evidence-review assertion, then request export. Repeating one source should leave the count unchanged; requesting export before approval should return 409. This remains fictional/offline acceptance, not real-world claim validation.

## Limits and remaining work

- Lexicon matching covers selected common EN/HI/MR scam vocabulary, not general multilingual semantic equivalence. Numeric/entity/negation/topic guards prioritize preventing unrelated merges and can split valid paraphrases. Proper names/amounts may be over-redacted. Unknown private details cannot be exhaustively recognized by regex; require upstream minimization and human privacy review before public copying. Avoid storing free conversation prose as a claim.
- Optional `Embedder.encode()` and `ClaimTranslator.translate()` protocols accept a preloaded local adapter. No model is bundled, downloaded or invoked by default. Adapter implementations must stay local; missing/failed embeddings preserve deterministic fallback, while unavailable translation stays pending. Tests use injected fixtures.
- Local lists are capped by storage capacities and observed-variant samples show at most 50 entries; they are not a scalable dashboard API. Person 2 should add server-side pagination when integrating durable storage. Capacity exhaustion returns 503 and rolls back the whole ingest, never silently evicts active evidence.
- No Supabase adapter, frontend dashboard, chatbot consent integration, individual session authentication, confirmed-fraud policy, Meta setup or Channel publishing is implemented here. These are Person 2 integration tasks; existing modules are untouched.
- No new real-world accuracy or live-provider acceptance claim is made. Tests establish deterministic safety/contract behavior. Existing Gemini audio HTTP 503 live blocker remains outside this independent feature.

## Safe Git handoff

The feature is committed only on its isolated branch, with no push or main merge. Find its commit using `git log -1 feature/scam-alert-intelligence`. Review `git diff main...feature/scam-alert-intelligence -- backend docs/scam-alert*` before integration. Person 2 should finish/stash their own work themselves, review the isolated commit, then integrate from a clean chosen branch:

```powershell
git cherry-pick <feature-commit-hash>
```

Do not cherry-pick into an active dirty tree. Resolve overlaps in backend README/environment template deliberately, rerun offline checks and exact legacy OpenAPI comparison, then configure the private alert service. Only Person 2 should add their Supabase tables, server proxy/auth mapping, consent workflow and dashboard. Keep Channel posting manual.
