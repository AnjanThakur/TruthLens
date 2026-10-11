# Windows startup and controlled acceptance

Use the feature worktree on this laptop. Do not copy a checkout over existing private configuration/state.

```powershell
Set-Location D:\HackOnTrack-TruthLens\.worktrees\scam-alert-intelligence
& .\scripts\Manage-TruthLens.ps1 -Action check -Services @('backend','alerts','website','adapter') -WebsitePort 3001
& .\scripts\Manage-TruthLens.ps1 -Action status -Services @('backend','alerts','website','adapter','worker','ngrok')
```

The owner's website on 3000 and adapter on 8100 are independent existing processes. Status lists only processes launched by this script. A start on an occupied port refuses without terminating its owner; omit existing services. To start only missing feature services:

```powershell
& .\scripts\Manage-TruthLens.ps1 -Action start -Services @('backend','alerts','website') -WebsitePort 3001
# Only if these are this launcher's owned instances:
& .\scripts\Manage-TruthLens.ps1 -Action restart -Services @('backend','alerts','website') -WebsitePort 3001
& .\scripts\Manage-TruthLens.ps1 -Action stop -Services @('backend','alerts','website')
```

Backend health: `http://127.0.0.1:8000/api/health`; alerts health/docs: `http://127.0.0.1:8001/health`, `/docs`; website: `http://127.0.0.1:3001`. Startup checks actual HTTP readiness. Stop uses a random owned-instance marker for graceful shutdown and never kills an unrelated port owner. Restart affects only selected owned instances; inspect status first.

Private configuration is read from main `backend/.env`, `frontend/.env.local`, `whatsapp-adapter/.env.twilio`; no values are printed. A different installation can specify `-PrivateRoot <directory>`. Environments are reused from this checkout or private-root environments. Main relative WhatsApp SQLite paths remain anchored to the original env folder; encryption/hash/account keys and existing state are preserved. New alert state is separate encrypted `backend/state/alerts.sqlite3`; stable local keys/tokens are retained in ignored `.tmp/runtime/secrets.env`. Back up encrypted alert state together with its original private key. Do not delete/regenerate keys to repair an existing database.

Default backend children blank Gemini/Tavily keys, adapter children disable outbound/backend consumption, and `-Services @('worker')` creates **paused standby only**: no Store initialization, queue claim, outbox retry or provider call. Stop it with the same service selection. Existing signed webhook and callback handling are preserved. The ordinary consuming worker command remains the existing adapter CLI; using it requires separately approved eligibility/configuration, not merely this standby's healthy state. HELP/STOP/etc remain blocked outbound on the confirmed template-only trial account.

For ngrok, install/authenticate the official executable using your private account setup, inspect any existing tunnel first, then explicitly select `-Services @('ngrok')`. It points to 8100, checks the local admin port 4040 to avoid a competing tunnel, and never hardcodes temporary domains or tokens. Updating a public signed-webhook URL requires corresponding private adapter/Console configuration. The existing tunnel was not replaced during acceptance.

## Dependencies and offline validation

From a fresh checkout install backend `pip install -e '.[dev]'`, adapter its existing `requirements-twilio-lock.txt` and `pip install --no-deps -e .`, frontend `npm ci` then `npm run build`. The runner checks missing environments, production build, dependencies and port conflicts before starting anything. Native extraction needs Tesseract with `eng`, `hin`, `mar` and FFmpeg/FFprobe. This laptop reuses main `backend/.runtime/tessdata` and installed native tools. Use the documented environment example to configure other machines without copying secrets.

```powershell
Set-Location D:\HackOnTrack-TruthLens\.worktrees\scam-alert-intelligence\backend
$env:TESSDATA_DIR='D:\HackOnTrack-TruthLens\backend\.runtime\tessdata'
& D:\HackOnTrack-TruthLens\backend\.venv\Scripts\python.exe -m pytest -q
& D:\HackOnTrack-TruthLens\backend\.venv\Scripts\python.exe -m ruff check app tests scripts ..\scripts\runtime.py ..\scripts\compare_avoidable.py
& D:\HackOnTrack-TruthLens\backend\.venv\Scripts\python.exe -m mypy app
& D:\HackOnTrack-TruthLens\backend\.venv\Scripts\python.exe -m scripts.evaluate_policy
Set-Location ..\whatsapp-adapter
& D:\HackOnTrack-TruthLens\whatsapp-adapter\.venv\Scripts\python.exe -m pytest -q
& D:\HackOnTrack-TruthLens\backend\.venv\Scripts\python.exe -m ruff check truthlens_whatsapp tests
Set-Location ..\frontend
npm run lint
npm run typecheck
npm run format:check
npm test
$env:CI='true'
$env:PLAYWRIGHT_PORT='3100' # isolated from the owner's 3000 website
npm run test:e2e
npm run build
npm run test:integration
```

Browser/proxy suites use deterministic fixtures and isolated servers, never live providers. Run each check only after preceding dependencies/build requirements succeed. Windows temp/spawn ACL restrictions may require the host's normal approved execution context. Hosted CI installs native tools and runs complete backend, adapter and website suites; hosted results are not implied by local PASS.

## Approved one-claim live phase only

**Do not run these start commands until the owner explicitly approves new provider consumption.** Preflight `-Action check` alone makes no provider call. Controlled acceptance selects lifetime ceilings 5 Gemini / 2 Tavily / 0 Twilio; normal `-EnableProviders` does not impose those lifetime ceilings and is inappropriate for this phase.

```powershell
Set-Location D:\HackOnTrack-TruthLens\.worktrees\scam-alert-intelligence
# Requires fresh explicit owner approval, available quota and no other acceptance instance:
& .\scripts\Manage-TruthLens.ps1 -Action start -Services @('backend','website') -ControlledAcceptance -WebsitePort 3002
```

Visit `http://127.0.0.1:3002`, submit exactly the single WHO establishment-date claim in the acceptance report, English/adult/text. Do not request translations, other formats or a second claim. Record actual `/api/verify` status/result, full evidence/source dates and rendered explanation. The ignored `.tmp/runtime/<backend-instance>.acceptance.json` records actual request counters including retries, shared across all requests in that process. A successful HTTP response or an unconfirmed/partial display is not automatically factual acceptance. On quota exhaustion stop immediately; no repeated provider probes.

```powershell
# Graceful rollback targets only controlled instances, leaving ordinary services intact:
& .\scripts\Manage-TruthLens.ps1 -Action stop -Services @('backend','website') -ControlledAcceptance -WebsitePort 3002
```

The regular 8000/3001 provider-disabled servers continue running. No consuming worker was enabled and no WhatsApp send is part of this proposal. If a later separately approved format check is necessary, use the existing bounded selective CLI rather than all five formats. For example, from feature `backend/`:

```powershell
# REFERENCE ONLY: separate approval, not part of the one-claim phase above.
& D:\HackOnTrack-TruthLens\backend\.venv\Scripts\python.exe -m scripts.validate_live --live --quota-available --formats url --languages en --model-budget 3 --search-budget 2
& D:\HackOnTrack-TruthLens\backend\.venv\Scripts\python.exe -m scripts.validate_live --live --quota-available --formats audio --languages en --model-budget 1 --search-budget 1
```

The one-attempt audio command diagnoses transcription but may exhaust its model budget before verification; it is not full audio acceptance. Counts are actual attempts, successful cached calls can cost zero, and these independent commands do not share a process-wide budget. Never combine them and claim the one-claim ceiling still covers the aggregate.
