# WhatsApp deployment preparation

Prepared only. No host, tunnel, Meta asset, phone number or public deployment has been created. Owner approval is required before account actions, live sends, provider tests or publishing.

## Topology

Deploy the adapter web process and a separate worker from `whatsapp-adapter/`. Use the supplied Dockerfile for the web process and override the worker command with `python -m truthlens_whatsapp.worker`. Keep Next.js as its existing separate application. Both call the same private Person 1 origin. Native OCR/FFmpeg/provider dependencies remain on P1's service, not in this adapter image.

Use managed PostgreSQL with a restricted application role, encrypted transport and backups. Configure `DATABASE_URL=postgresql://...` with `sslmode=verify-full` and the provider's CA where supported. The web and worker share identical encryption/hash keys. The role needs schema/table creation for initial startup, then only the required data operations after a reviewed migration. Never use the website's Supabase service-role key. The generic queue tables are internal, not public REST tables.

For a hosted local-mode demonstration, SQLite needs a persistent volume and a single machine; production configuration deliberately rejects SQLite. PostgreSQL SQL/locking paths still require an actual hosted/isolated-server acceptance test before release. No hosted database has been provisioned or claimed tested here.

## Host configuration

- Public route: HTTPS `GET/POST /webhook/whatsapp`; health exposes only configuration state. No admin, report or queue inspection endpoint is public.
- Preserve raw request bytes for HMAC. Disable request-body and query-string logging, including challenge tokens. Apply edge request-size/connection limits. Never cache webhook responses.
- Run a worker continuously, with graceful shutdown and restart policy. Its default 30-minute processing lease exceeds bounded request deadlines; an expired lease marks a job failed without repeating paid calls.
- Limit worker replicas according to provider budget; start with one. Database admission and per-sender serialization protect duplicate work, but multi-host failure recovery must be acceptance-tested before scaling.
- Backend network access must be private or protected by an authenticated gateway. Setting `TRUTHLENS_BACKEND_TOKEN` alone does not add authentication to P1. Do not expose their unauthenticated endpoints publicly.
- Configure encrypted secrets privately. Production requires backend mode, PostgreSQL and actual HTTPS support contact. Meta access tokens must be rotated/reissued according to the chosen authorized flow.
- Add host resource limits, database connection limits and edge abuse protection. Rate-limit web verification separately; CORS is not authentication.

## Monitoring and retention

Alert on webhook failures, pending-job age, failed/interrupted jobs, failed/uncertain outgoing sends, missing workers, database errors and token expiry. Metrics must contain counts/stages, not submitted text, phone numbers, source URLs with private queries or credentials. Logs contain hashed/truncated job references and sanitized codes. Access to logs and database is restricted to maintainers.

The worker purges encrypted content after configured retention (maximum 24 hours plus one-minute sweep); run an independent scheduled cleanup if the worker is unavailable. Backups have their own bounded retention/deletion policy: application deletion does not erase an existing backup. Verify cleanup behavior and restore procedures on the selected host. Minimal hashed opt-out state is retained to honor STOP; it must not become an analytics identity graph.

## Release sequence

1. Obtain current account/AI-service eligibility confirmation and applicable app/business/number approvals.
2. Confirm provider-key rotation and explicit provider test budget separately.
3. Build/test locally; deploy web, worker and database only after production publication approval.
4. Confirm TLS, raw-body signatures, callback challenge, correct app/WABA `messages` subscription and test recipient.
5. Demonstrate a development reply first, recording actual delivery. Then enable real backend mode only with provider approval.
6. Perform one bounded text check, record real citation/timestamp and actual delivered result; stop on provider failure.
7. Seek approval for additional media/provider acceptance. Do not label partial or failed formats complete.
8. Verify STOP/window suppression, duplicate replay, worker restart, database purge and no raw PII logs. Publish the website number/QR only after the relevant number and audience are approved.

Rollback: disable outbound sending first, stop intake or route to a maintenance response, preserve encrypted state for investigation, and roll back application images without resetting identifiers/keys. Reconcile uncertain sends from status records; do not mass replay them. Re-enabling backend work or public messaging requires the relevant owner authorization.
