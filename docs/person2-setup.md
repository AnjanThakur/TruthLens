# Person 2 setup and handoff

## Project layout

`frontend/src/app`: pages, fixed-origin P1 proxy routes, P2 history/auth routes.
`frontend/src/components`: responsive verification, results, preferences and history views.
`frontend/src/lib/api`: schemas reconciled with Person 1 actual OpenAPI, transport, errors, upload validation and server adapter.
`frontend/src/lib/history`: saved-report schema and HMAC receipt validation.
`frontend/src/lib/i18n`: static UI translations and verdict/stance labels.
`frontend/src/lib/supabase`: server-only, user-scoped cookie client.
`supabase/migrations`: immutable private report table, RLS and hourly expiry purge.

## Backend integration

1. Review `backend-api-contract.md`, `backend-openapi.json` and `person2-contract-reconciliation.md` with Person 1. The earlier `api-contract.md` is historical.
2. Set a fixed FastAPI origin in `BACKEND_BASE_URL`; never point it at the Next.js app or a user-controlled URL. Paths `/api/*` resolve at that origin.
3. Set optional server-only `BACKEND_API_TOKEN` only if P1 confirms bearer auth.
4. Configure timeouts and upload limits to match both P1 and the web host. Proxy default is 195 seconds (P1 default deadline: 180); supported overrides are 1–300 seconds and the browser waits 330 seconds. The host must support the selected duration. `MAX_UPLOAD_BYTES` is shared by the UI and server, defaults to 10 MiB and may be reduced for hosting limits; allow multipart overhead. Do not silently accept files the platform rejects.
5. Keep both mock flags off, restart Next.js, check `/api/health`, then test live flows. Normal operation never fetches user URLs directly in Next.js.

## Supabase

1. Create/select a project you own. Copy its project URL and publishable key into `.env.local` or the hosting secret configuration. Legacy anon JWT keys are supported by the SDK if used in the publishable-key variable; document the actual key convention for your project. Never use a service-role key here.
2. Generate `HISTORY_SIGNING_SECRET` with the command in `.env.example`. Share the same server-only signing secret across application instances. Rotating it invalidates unsaved receipts, not existing reports.
3. Apply `202610110001_private_reports.sql` with the database owner. Inspect grants and RLS before enabling history. Anonymous users have no table privileges; authenticated users can select/insert/delete only their own rows. UPDATE is deliberately not granted.
4. Enable pg_cron in the dashboard, then apply `202610110002_retention.sql` once. Confirm the `truthlens-delete-expired-reports` hourly job exists and succeeds. Expired reports are immediately hidden; the job removes them within an hour. If the job cannot be enabled, do not claim retention is fully deployed. Configure an equivalent controlled scheduled purge before production.
5. Enable email authentication, configure trusted SMTP/email sending as needed, and allow exactly the app's callback URLs, e.g. `http://localhost:3000/auth/callback` locally and `https://your-domain/auth/callback` in production. Set `APP_ORIGIN` to the exact origin used by the browser.
6. Test two separate real users: A cannot read/save as/delete B; anonymous access is refused; signing out removes history from the UI; expired rows cannot be read; hard delete removes the report. Verify email link and refresh behavior in the same browser.

Auth cookies are HttpOnly, same-site lax and secure in production. This application uses route handlers for sign-in, refresh and sign-out; it does not expose an auth session to browser JavaScript. All save/delete actions enforce Origin and validate server-confirmed identity. Save receipts expire after one hour; re-run verification to obtain a fresh one if needed. No report or uploaded file is auto-saved.

## Routine integration checkpoint

Run a short shared check with Person 1 using two different claims and a real file. Record API revision, enabled providers, supported formats, observed errors, quotas/cost limits and deployment origin. P1 owns the real RBI/currency evidence for the judge demo. P2 never scripts the factual verdict.

## Dependencies

Versions are locked in `frontend/package-lock.json`. Use `npm ci`; do not update schemas or dependencies silently. Next.js 16 generates frontend/AGENTS.md and ships local API documentation in `node_modules/next/dist/docs`. The direct ESLint setup uses TypeScript, React Hooks and JSX accessibility rules rather than a Next preset with an unpatched transitive glob advisory. Re-evaluate plugin support before a future ESLint major upgrade.

References: [Next.js installation](https://nextjs.org/docs/app/getting-started/installation), [Supabase server clients](https://supabase.com/docs/guides/auth/server-side/creating-a-client), [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security). Documentation checked 2026-10-11; installed SDK/source and lockfile govern this checkout.

## Required WhatsApp service

See `../whatsapp-adapter/README.md` for the separate service and `whatsapp-gates.md` for tested scope. No account access, live sends, paid provider use or publication without owner approval.

Latest repeatable offline acceptance and bounded single-message commands are in `person2-local-acceptance.md`. The new production proxy browser suite uses a local fake P1 HTTP service; it can run without a working verification engine or provider keys.
