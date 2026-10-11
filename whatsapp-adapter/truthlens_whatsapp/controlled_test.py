"""One selected message only. Existing approval flags are never enabled here."""

import argparse
import asyncio
import json
import re
import time

import httpx

from .config import load_settings
from .errors import ServiceError
from .meta_client import MetaClient
from .store import Store
from .truthlens_client import TruthLensClient
from .worker import Worker


class RequestBudget:
    def __init__(self, maximum):
        if not 0 <= maximum <= 10:
            raise ValueError("Backend request limit must be between zero and ten")
        self.maximum, self.used = maximum, 0

    def reserve(self):
        if self.used >= self.maximum:
            raise ServiceError("test_budget_exhausted")
        self.used += 1


async def run_selected(
    settings, store, http, message_id, *, backend_requests=0, send_attempts=1, wait_seconds=30
):
    if settings.bot_env != "test" or not settings.outbound_enabled:
        raise ValueError("Controlled testing requires test mode and separately approved sending")
    if not 1 <= send_attempts <= 5 or not 1 <= wait_seconds <= 120:
        raise ValueError("Invalid controlled test limits")
    if settings.messaging_provider == "twilio":
        if not re.fullmatch(r"(?:SM|MM)[0-9a-fA-F]{32}", message_id):
            raise ValueError("Use the selected inbound Twilio Message SID")
        from .twilio_client import TwilioClient

        message_id = "twilio:" + message_id
        transport = TwilioClient(settings, http)
    else:
        if not message_id.startswith("wamid.") or len(message_id) > 512:
            raise ValueError("Use the selected inbound Meta message ID")
        transport = MetaClient(settings, http)
    budget = RequestBudget(backend_requests)
    job_id = store.identity(message_id)
    worker = Worker(
        settings,
        store,
        transport,
        TruthLensClient(settings, http, request_budget=budget),
        job_id=job_id,
    )
    deadline = time.monotonic() + wait_seconds
    processed = False
    while time.monotonic() < deadline:
        processed = await worker.process_one()
        if processed:
            break
        # Never resume a completed/failed job or its old outbox on rerun.
        with store.tx() as db:
            existing = store.execute(db, "SELECT state FROM jobs WHERE id=?", (job_id,)).fetchone()
        if existing and existing["state"] != "received":
            return {
                "outcome": "not_new",
                "processed": False,
                "backend_requests": 0,
                "outbox_steps": 0,
            }
        await asyncio.sleep(0.25)
    steps = 0
    if processed:
        while steps < send_attempts and await worker.send_one():
            steps += 1
            if settings.messaging_provider == "twilio" and steps < send_attempts:
                await asyncio.sleep(3.1)
    with store.tx() as db:
        job = store.execute(db, "SELECT state,error FROM jobs WHERE id=?", (job_id,)).fetchone()
        pending = store.execute(
            db, "SELECT COUNT(*) AS n FROM outbox WHERE job_id=? AND state='prepared'", (job_id,)
        ).fetchone()["n"]
    return {
        "outcome": "processed" if processed else "not_received",
        "processed": processed,
        "job_state": job["state"] if job else None,
        "processing_error": job["error"] if job else None,
        "backend_requests": budget.used,
        "outbox_steps": steps,
        "pending_parts": pending,
        "note": "Processing/send attempts are not delivery or accuracy proof. Limits apply to this invocation only.",
    }


async def main(args):
    settings = load_settings()
    async with httpx.AsyncClient(follow_redirects=False, trust_env=False) as http:
        return await run_selected(
            settings,
            Store(settings),
            http,
            args.message_id,
            backend_requests=args.max_backend_requests,
            send_attempts=args.max_send_attempts,
            wait_seconds=args.wait_seconds,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--message-id", required=True, help="One fresh inbound SID/ID, not message text"
    )
    parser.add_argument("--max-backend-requests", type=int, default=0)
    parser.add_argument("--max-send-attempts", type=int, default=1)
    parser.add_argument("--wait-seconds", type=int, default=30)
    try:
        result = asyncio.run(main(parser.parse_args()))
    except Exception:
        # Settings/HTTP exceptions can contain secrets. Do not echo them.
        parser.exit(1, "Controlled test could not start; check private configuration and limits.\n")
    print(json.dumps(result))
