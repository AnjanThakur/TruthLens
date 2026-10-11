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

## Required WhatsApp service

WhatsApp is a required deliverable under the owner's revised roadmap. Person 2's separate adapter calls Person 1's existing engine; the website remains independently usable. See `twilio-sandbox-setup.md` for the current test transport and `whatsapp-deployment.md` for deployment preparation. Twilio Sandbox is test-only; production transport/account acceptance and owner publication approval remain pending. No Channel integration is provided.

The website proxy now defaults to 195 seconds to outlive P1's 180-second default deadline. `BACKEND_TIMEOUT_MS` supports 1–300 seconds; the browser allows 330 seconds. Configure the host accordingly. Setting a longer application timeout does not extend a hosting platform's invocation limit. `MAX_UPLOAD_BYTES` is shared by the server and browser UI and can be reduced below 10 MiB for the selected host; leave allowance for multipart overhead.

`.github/workflows/person2-offline.yml` prepares separate website and adapter checks without provider/account secrets. It has not been executed on GitHub yet. Local browser integration uses a loopback-only fake P1 service and explicitly labeled fictional responses, not real evidence acceptance.
