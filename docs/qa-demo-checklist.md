# QA and judge demonstration

`npm test` covers contracts, all verdicts/stances, safe URLs, missing dates, empty evidence/claims, explanation identity, file limits, production fixture exclusion, upstream 429/5xx/offline/timeout behavior, origin checks, signed-receipt tampering and actual PostgreSQL owner isolation.

`npm run test:e2e` covers desktop and narrow mobile flows, all five synthetic paths, real upload controls with simulated extraction, extraction edits, uncertainty, language/easy-reading controls, rewrite failure, outages, keyboard skip navigation and safely disabled history. Automated axe checks cover WCAG A/AA.

These are UI/adapter tests, not real fact-checks or provider accuracy tests. SQL tests use the actual base migration in isolated PostgreSQL. Hosted email delivery and the purge scheduler require live testing.

## Local demo

1. Run `npm run dev:mock`. Point out the synthetic banner.
2. Choose Mixed claims, Use this example, Check the facts. Show separate verdicts, dated sources and excerpts. Links are fictional placeholders.
3. Show Screenshot, Hindi voice note, PDF notice and Article URL examples, extraction review and warnings. Edit text: changes are preserved and unrelated canned verification is refused.
4. Show Insufficient evidence: Unconfirmed, no fabricated citation, limitations and next steps.
5. Switch Hindi/Marathi and easy reading. Local labels change; claim explanations require P1. A failed rewrite retains the original cited result.
6. Show disabled private history without configuration. No submission is saved automatically; synthetic reports cannot enter live history.

## Live acceptance when services arrive

- [ ] Confirm P1 OpenAPI revision and all provisional decisions.
- [ ] Long forward produces multiple independently justified claims with actual sources.
- [ ] Real screenshot, audio, PDF/scanned page and URL all extract real text, allow review and verify.
- [ ] ₹500 currency forward uses actual RBI evidence retrieved by P1; no scripted verdict.
- [ ] Missing evidence, contradictory sources and stale information remain cautious.
- [ ] Grounded en/hi/mr rewrites preserve claim identities, verdicts and evidence URLs.
- [ ] At least three modalities run live; remaining two have documented tests. Aim for all five live.
- [ ] Two real Supabase users prove owner isolation; anonymous access denied; save, expiry and deletion work.
- [ ] Test full keyboard journey, screen-reader announcements, 320px width, 200% zoom, reduced motion and unavailable speech.
- [ ] Confirm HTTPS, host upload/time limits, shared rate limits, minimal logging and provider privacy disclosures.

Until live checks pass, describe the result as a tested frontend/integration implementation, not a completed live verification service.
