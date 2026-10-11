# TruthLens AI

Person 2's Next.js application for reviewing forwarded claims, original evidence and honest uncertainty. The original Word execution plan in `TruthLens_Person2_Codex_Package` is the primary authority. Person 1's AI/backend code is intentionally a separate service.

Current collaborator handoff: [remaining work, APIs, private configuration and startup](docs/current-integration-handoff.md). Read it before older gate reports, which include historical blockers.

Combined branch: `integration/person2-scam-intelligence` now contains the saved Person 2 work and the scam-alert feature. See [merge validation and what remains to connect](docs/combined-integration.md). The alert service is separate; merging source does not automatically add a dashboard or chatbot consent/alert commands.

For a single-file collaborator package, read [START-HERE](START-HERE.md). Run `py -3.12 scripts/build_handoff.py` to build `dist/handoff/TruthLens-Friend-Handoff.zip` from current working files. It includes code, requirements, API schemas and setup templates; private configuration, chat state, screenshots, dependencies and Git history are excluded. This does not commit or push changes.

Latest Person 2 work: [local acceptance results and controlled test commands](docs/person2-local-acceptance.md). Both the production website proxy and adapter can be tested locally with mocked services while Person 1 finishes evidence quality.

## Start the local synthetic demo

Use Node.js 22.12+ or Node.js 24 LTS. This checkout's SDK and test-tool requirements are stricter than Next.js's own minimum.

```powershell
cd frontend
npm ci
npm run dev:mock
```

Open http://localhost:3000. Select **Use this example**, then **Check the facts**. All six examples are explicitly fictional. In synthetic mode uploaded files are not actually extracted, translations are unavailable, and arbitrary or edited messages cannot be assigned canned verdicts. No Supabase or AI secrets are needed.

## Connect Person 1 and optional history

Copy `frontend/.env.example` to `frontend/.env.local`. Set `BACKEND_BASE_URL` and negotiated authentication if needed. Keep both mock flags false. Start with `npm run dev`. Review `docs/backend-api-contract.md`, `docs/backend-openapi.json` and `docs/person2-contract-reconciliation.md` with Person 1 before live sign-off. The earlier `docs/api-contract.md` is a superseded provisional contract.

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

Person 1's backend code is present and the website contract is reconciled with its actual APIs. WhatsApp is a required deliverable implemented as the separate `whatsapp-adapter/` service. One fresh Twilio Sandbox message passed through the backend and its reply reached signed `read` status, confirmed on the owner's phone. Its verification was partial/unconfirmed because source retrieval was incomplete. Continuous replies remain disabled; live website acceptance, full media/language checks, hosted history and production deployment remain pending. See `docs/current-integration-handoff.md`, `docs/whatsapp-gates.md` and `docs/twilio-sandbox-setup.md`. The earlier `docs/gate-status.md` records historical website checks. Tracker/radar/public sharing remain deferred.

## Required WhatsApp connector

The adapter validates signed webhooks, durably deduplicates/encrypts jobs, retrieves Meta media, calls the existing P1 APIs and formats source-linked replies. Its defaults disable live Meta sending and provider calls. Run `python -m truthlens_whatsapp.offline_demo` from its installed environment for a network-free routing demonstration. This does not prove actual WhatsApp delivery. See its README for setup, approval boundaries and commands.
