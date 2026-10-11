# TruthLens AI

Person 2's Next.js application for reviewing forwarded claims, original evidence and honest uncertainty. The original Word execution plan in `TruthLens_Person2_Codex_Package` is the primary authority. Person 1's AI/backend code is intentionally a separate service.

## Start the local synthetic demo

Use Node.js 22.12+ or Node.js 24 LTS. This checkout's SDK and test-tool requirements are stricter than Next.js's own minimum.

```powershell
cd frontend
npm ci
npm run dev:mock
```

Open http://localhost:3000. Select **Use this example**, then **Check the facts**. All six examples are explicitly fictional. In synthetic mode uploaded files are not actually extracted, translations are unavailable, and arbitrary or edited messages cannot be assigned canned verdicts. No Supabase or AI secrets are needed.

## Connect Person 1 and optional history

Copy `frontend/.env.example` to `frontend/.env.local`. Set `BACKEND_BASE_URL` and negotiated authentication if needed. Keep both mock flags false. Start with `npm run dev`. Review `docs/api-contract.md` with Person 1 before live sign-off.

For private history, configure the Supabase URL and publishable key, a random server-only `HISTORY_SIGNING_SECRET` (at least 32 characters), and `APP_ORIGIN`. Apply the SQL migrations in `supabase/migrations` to your own project, enable email sign-in and allow the callback URL. No service-role key is needed. Detailed setup: `docs/person2-setup.md`.

## Included

- Text, screenshot, voice-note, PDF and public URL entry paths; editable extraction review.
- Independent claim cards, all six verdicts and five evidence stances; dated source attribution, contradictions, limitations, next steps and no-evidence handling.
- English/Hindi/Marathi interface, easy reading, optional browser speech, grounded explanation adapter with immutable factual fields.
- Typed/runtime-validated server proxy, cancellation, timeout/error handling, bounded requests and uploads, no silent fixture fallback.
- Optional email sign-in and explicitly saved private history, owner-only database policies, retention, deletion, server-issued report receipts and no mock persistence.
- Privacy page, security headers, automated tests, integration/deployment/Meta requirements and gate reports.

## Check the project

```powershell
cd frontend
npm run typecheck
npm run lint
npm test
npm run test:rls
npm run test:e2e
npm run build
```

Browser tests use installed Microsoft Edge by default. For other systems set `PLAYWRIGHT_CHANNEL=chromium` and install Playwright Chromium: `npx playwright install chromium`. The runner starts its own clearly labeled mock development server when no preview is already running. Run against a clean environment without live credentials. `node scripts/qa-screenshots.mjs` captures local QA views while the demo is running.

Database security tests execute the actual base migration in isolated PostgreSQL (PGlite), checking owners, cross-user access, anonymous denial, consent, immutability, expiry and deletion. They do not create or modify a hosted database. They do not validate Supabase email delivery or pg_cron deployment; those require a configured project.

## Production and status

`npm run build` then `npm start` serves the production application. Fixture APIs are disabled under production even if mock flags were mistakenly enabled. A live FastAPI service is required for real verification; synthetic examples are never evidence of live accuracy.

The current live integration and HTTPS deployment remain pending: the user confirmed that Person 1's backend and Supabase are not yet available. See `docs/gate-status.md` for exact tested scope and `docs/deployment.md` for deployment and release gates. G5 tracker, radar, public sharing and WhatsApp integration are deferred.
