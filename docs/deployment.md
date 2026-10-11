# Deployment and release

The web app is prepared for a Node.js Next.js host. No deployment account, production backend, Supabase project or domain is configured. Local development and all offline checks remain independent of Meta.

## Next.js host

Use Vercel or a suitable Node.js HTTPS host with `frontend` as project root. Install with `npm ci`, build with `npm run build`, and start with `npm start` for a Node server. This application needs server routes and cannot use static export. Do not upload `.env.local` or the instruction package as public assets.

Set server-side `BACKEND_BASE_URL`, optional `BACKEND_API_TOKEN`, `BACKEND_TIMEOUT_MS`, `APP_ORIGIN` and optional history signing secret. Set public Supabase URL/key only if private history is configured. Both mock flags must be false. Production code independently refuses fixture API mode. Use HTTPS for production backend and app; do not expose backend credentials in public variables.

Confirm platform upload/time limits before accepting media. The app provisionally supports 10 MiB, but serverless providers may impose smaller body limits or invocation durations. For a constrained host, align both UI/server caps to the actual limit, or negotiate an upload architecture with Person 1 before release. Do not implement a blind URL-fetching workaround.

## Release requirements

- Confirm the P1 contract and real-provider health/capabilities. Run all five real inputs where possible; minimum live demo is three inputs with documented tests for the remaining two.
- Configure authentication callbacks and hosted database migrations; verify owner isolation with two real accounts, session refresh, deletion and scheduled expiry purge.
- Configure hosting/WAF or shared gateway limits for anonymous verification, media uploads and email sign-in. The app intentionally does not claim that per-process memory is a distributed rate limiter. P1 must enforce quotas/limits on its service too.
- Confirm provider processing/retention and populate the deployment-specific privacy disclosures. Disable sensitive request-body logging at the host, backend and telemetry layers.
- Verify HTTPS and response security headers. Page scripts use per-request CSP nonces; development eval allowance is absent in production. No auth/history responses may be cached by a CDN.
- Run the build, lint, tests, browser accessibility and live QA checklist. Confirm runtime browser errors are absent and no fictional sources appear in live results.
- Verify costs, quotas, monitoring, rollback version and error handling. No Meta account status is required for website release.

## Staging versus production

Development synthetic demo: `npm run dev:mock`, prominent fixture warnings, no real extraction, no real translation and no live saving. Normal dev/staging: both flags off and configured P1 origin. A hosted production build requires the live upstream; it never substitutes demo results during an outage.

## Optional WhatsApp

Follow `meta-setup.md` after the core is ready. P1 deploys signed webhook code separately. A public demo QR or test bot is a G5 milestone, not a prerequisite for web verification.
