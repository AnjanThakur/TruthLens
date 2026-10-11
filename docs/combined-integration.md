# Person 2 + scam intelligence — combined integration

Combined locally on 2026-10-11 in `integration/person2-scam-intelligence`. No GitHub push, main merge, account changes, live provider calls, live WhatsApp sends or production release was performed.

## What was combined

1. Checked the staged Person 2 files for excluded paths, known local secret values and common credential patterns, including Word document contents. No private environment files, account screenshots or chat databases were committed.
2. Saved Person 2 work as `c88900c` on `feature/person2-whatsapp`, preserving its earlier `0e813a2` commit.
3. Created `integration/person2-scam-intelligence` from that saved state.
4. Merged `origin/feature/scam-alert-intelligence` (`50350b4`) without conflicts. Both histories remain in a merge commit. Main and the scam feature were not modified.
5. Confirmed the existing verification API/routes/schemas/OpenAPI snapshot are unchanged from Person 2, and alert implementation/tests/schema are unchanged from the fetched scam branch.

This is a tested **source integration**, not a claim that scam alerts are already available in the website or chatbot. The two services intentionally remain separate. The existing website and WhatsApp verification paths continue using the original backend.

## Validation on this laptop after merging

| Check | Result |
| --- | --- |
| Full backend offline suite | 291 passed, three failed, two skipped |
| Alert regressions within that suite | All 101 passed; live HTTP transports blocked by their fixture |
| Website unit/component/contract/history/RLS suite | 40 passed |
| WhatsApp adapter offline suite | 92 passed |
| Backend Ruff, mypy (44 files) and dependency check | Passed |

The three backend failures match the previously documented local blockers: legacy OpenAPI response-description wording differs under the installed dependencies, and Hindi/Marathi native OCR lacks language support on this laptop. The two skips are native audio checks because FFmpeg/FFprobe are absent. No assertions, golden schema or backend code were weakened to hide these results. The other branch's report of 296 passing tests refers to its separate development machine, not this merged checkout's local result.

The dedicated `pytest tests/test_alerts.py` CI command was also run separately: 101 passed. No paid provider or message delivery tests were run.

The prior 22 website browser/accessibility and six production-proxy browser passes are recorded in `person2-local-acceptance.md`; they were not rerun for this backend-only merge. The prepared CI now also covers the integration branch and a dedicated offline alert regression job; hosted CI execution remains pending after push. The dedicated job does not claim that all native/legacy backend tests pass.

## How the combined system fits together

```text
Website / WhatsApp private chat
          |
          v
Existing verification backend :8000
  extract -> verify -> grounded explanation
          |
          | future trusted, explicit-consent ingestion
          v
Separate scam-alert service :8001
  minimize -> cluster -> draft -> human review -> manual export
```

Scam intelligence consumes existing verification results; it does not invoke another AI engine. A partial/unconfirmed check is not automatically a publishable warning. The alert evidence gates defer incomplete results. Nothing is ingested from website history or WhatsApp automatically, and no Channel auto-publishing is implemented.

## Run the separate alert service

Use the existing backend Python environment; the scam feature adds no dependencies. From the repository root in PowerShell:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.alerts_app:app --host 127.0.0.1 --port 8001 --workers 1 --no-access-log
```

Keep the original verification backend on port 8000, adapter on 8100 and website on 3000. Port 8001 must be free. The alert repository is currently in memory: one worker only; restart loses its records. Do not treat it as durable production storage.

Health: `http://127.0.0.1:8001/health`; Swagger: `http://127.0.0.1:8001/docs`. Unconfigured protected routes return a sanitized 503. For authenticated local fixture work, configure three **distinct random server-only secrets**, each at least 32 characters, privately in `backend/.env`:

- `ALERTS_INGEST_TOKEN`: producer credential for ingest/withdraw.
- `ALERTS_ADMIN_TOKEN`: trusted review server credential.
- `ALERTS_PSEUDONYM_SECRET`: pseudonym/guard key.

Names/defaults are included in the merged `backend/.env.example`; do not copy the template over an existing private env file. No real secrets were generated or enabled by this merge. Static service tokens are not per-user reviewer authentication. Never expose them in browser variables, chat replies, screenshots or commits. The verification backend's separate gateway/authentication requirement is unchanged.

API contract: [scam-alert-openapi.json](scam-alert-openapi.json). Full ownership, payloads, lifecycle and privacy notes: [scam-alert-integration.md](scam-alert-integration.md). This additive schema does not replace `backend-openapi.json`.

| Endpoint | Role / purpose |
| --- | --- |
| `POST /api/alerts/ingest` | Ingest role; explicit consent + stable per-principal UUIDv4 source + per-delivery submission UUID + existing verification result |
| `POST /api/alerts/withdraw` | Ingest role; withdraw that source and related retained data |
| `GET /api/alerts/clusters`, `GET /api/alerts/drafts` | Admin role; retained sample and review drafts |
| `POST /api/alerts/clusters/{cluster_id}/drafts` | Admin role; prepare EN/HI/MR draft |
| `PATCH /api/alerts/{alert_id}` | Admin role; versioned edits/translation review |
| `POST /api/alerts/{alert_id}/submit`, `/approve`, `/reject` | Admin role; human review lifecycle |
| `GET /api/alerts/{alert_id}/export` | Admin role; currently approved manual-copy text only |
| `POST /api/alerts/purge` | Admin role; retention sweep |

## Remaining Person 2 work to expose alerts to users

This was not implemented by the branch merge:

1. An explicit, informed alert-contribution opt-in separate from private history and normal fact-checking; a withdrawal flow and retained-source deletion. Do not infer consent from sending a WhatsApp message, saving history or pressing Check.
2. A trusted server integration that forwards authentic completed verification records, checks consent and assigns a stable random UUIDv4 per consenting principal plus idempotent UUID per submission. Do not use phone numbers, phone hashes or WhatsApp message IDs as source/submission identities. Counts must not inflate by inventing a new principal for each message.
3. An authenticated reviewer dashboard with server-enforced roles. Derive reviewer UUID from the trusted session; never trust an arbitrary browser-supplied reviewer identity or expose the admin credential to users.
4. Durable repository/storage, scoped access, retention and withdrawal cascades, capacity/pagination and restart/restore acceptance. Coordinate Supabase schema with existing private history rather than changing it silently.
5. Versioned review, source/evidence/privacy/translation checks and approved-only manual export. Re-fetch immediately before copying; edits, evidence/sample changes and expiry revoke approval. Channel posting remains a deliberate manual operation.
6. Mocked end-to-end UI/chat tests for opt-in/withdrawal, deduplication, reviewer authorization and blocked unapproved/stale/partial export. Real provider/message/deployment tests require a separately agreed budget and owner approval.

The original handoff's evidence-quality, live-media/language, website, hosted-history and production tasks still apply. Do not change a verdict or manufacture evidence to activate an alert.

## Publish both features together, when ready

Review `git status` and current commit first. The local integration is already committed; no additional merge command is required. To publish this combined branch:

```powershell
git switch integration/person2-scam-intelligence
git push -u origin integration/person2-scam-intelligence
```

Then create a reviewed pull request to main. Do not force-push or overwrite either feature branch. Pushing requires contributor permission on the repository. If rejected, stop and inspect the error rather than resetting/rebasing shared history blindly.

Your friend should clone the combined branch after that push:

```powershell
git clone --branch integration/person2-scam-intelligence https://github.com/AnjanThakur/TruthLens.git
```

The rebuilt `dist/handoff/TruthLens-Friend-Handoff.zip` also includes both features, the separate alert API schema and this document. Its manifest records the snapshot; private files and Git history remain excluded.
