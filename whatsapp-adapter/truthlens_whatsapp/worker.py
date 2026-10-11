import asyncio
import logging
import signal
import time

import httpx

from .config import load_settings
from .errors import AmbiguousSend, ServiceError, TwilioSendError
from .message_handler import MessageHandler
from .meta_client import MetaClient
from .store import Store
from .truthlens_client import TruthLensClient

log = logging.getLogger("truthlens.whatsapp")


class Worker:
    def __init__(self, settings, store, meta, backend, *, job_id=None):
        self.settings, self.store, self.meta = settings, store, meta
        self.job_id = job_id
        self.handler = MessageHandler(settings, store, meta, backend)

    async def process_one(self):
        if self.settings.messaging_provider == "twilio" and not self.settings.outbound_enabled:
            return False
        job = self.store.claim(self.job_id)
        if not job:
            return False
        try:
            if self.settings.messaging_provider == "twilio":
                message = self.store.open(job["payload"])
                # Fetch Twilio's authoritative receipt time; never extend the 24h
                # reply window just because a signed webhook was retried/replayed.
                message["timestamp"] = str(await self.meta.received_at(message))
                self.store.refresh_payload(job, message)
            bodies, report = await self.handler.handle(job)
            if self.settings.messaging_provider == "twilio":
                from .twilio_client import split_reply

                bodies = [part for body in bodies for part in split_reply(body)]
            self.store.prepare(job["id"], bodies)
            self.store.finish(job["id"], report=report)
            log.info("stage=processed job=%s", job["id"][:12])
        except ServiceError as exc:
            if exc.code != "window_expired":
                if exc.code.startswith("media") or exc.code in {
                    "unsupported_media",
                    "extraction_empty",
                }:
                    body = "TruthLens could not read this attachment. Please try a supported, clearer file or paste its text. No verdict was generated."
                elif exc.code == "text_too_large":
                    body = "This content is too long for one check. Please send a smaller section. No verdict was generated."
                else:
                    body = "TruthLens checking is temporarily unavailable. Please try later. No factual verdict was generated."
                self.store.prepare(job["id"], [body])
            self.store.finish(job["id"], error=exc.code)
            log.warning("stage=processing_failed job=%s code=%s", job["id"][:12], exc.code)
        except Exception:
            # Do not log exception strings/tracebacks that may embed request data or credentials.
            self.store.prepare(
                job["id"],
                [
                    "TruthLens encountered a service error. No verdict was generated. Please try later."
                ],
            )
            self.store.finish(job["id"], error="internal_error")
            log.error("stage=processing_failed job=%s code=internal_error", job["id"][:12])
        return True

    async def send_one(self):
        # Disabled means no network call and no state transition. Approval is a human action.
        if not self.settings.outbound_enabled:
            return False
        item = self.store.next_send(self.job_id)
        if not item:
            return False
        message = self.store.open(item["payload"])
        command = message.get("text", {}).get("body", "").strip().upper()
        if time.time() - int(message["timestamp"]) >= 86400 or (
            self.store.preference(item["sender"])["stopped"] and command != "STOP"
        ):
            self.store.send_state(item["id"], "suppressed")
            return True
        try:
            meta_id = await self.meta.send(
                message["from"], self.store.open(item["body"]), item["id"]
            )
            self.store.send_state(item["id"], "accepted", meta_id)
            outcome = "accepted"
        except AmbiguousSend as exc:
            self.store.send_state(item["id"], "uncertain")
            outcome = "uncertain"
            self.log_send_diagnostics(exc)
        except ServiceError as exc:
            if exc.code in {"meta_rate_limit", "twilio_rate_limit"} and item["attempts"] < 2:
                self.store.send_state(item["id"], "prepared", delay=exc.retry_after or 60)
                outcome = "retry_scheduled"
            else:
                self.store.send_state(item["id"], "failed")
                outcome = "failed"
            self.log_send_diagnostics(exc)
        except Exception:
            self.store.send_state(item["id"], "uncertain")
            outcome = "uncertain"
        log.info("stage=send_attempt outbox=%s outcome=%s", item["id"], outcome)
        return True

    def log_send_diagnostics(self, error):
        if self.settings.messaging_provider == "twilio" and isinstance(error, TwilioSendError):
            log.warning(
                "stage=twilio_send_error http_status=%s twilio_error_code=%s",
                error.http_status,
                error.twilio_error_code,
            )


async def run():
    settings = load_settings()
    store = Store(settings)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signum, stop.set)
        except NotImplementedError:
            pass  # Windows console Ctrl+C is handled by asyncio.run.
    async with httpx.AsyncClient(follow_redirects=False, trust_env=False) as client:
        if settings.messaging_provider == "twilio":
            from .twilio_client import TwilioClient

            transport = TwilioClient(settings, client)
        else:
            transport = MetaClient(settings, client)
        worker = Worker(settings, store, transport, TruthLensClient(settings, client))
        last_cleanup = 0
        while not stop.is_set():
            if time.time() - last_cleanup >= 60:
                store.cleanup()
                last_cleanup = time.time()
            processed = await worker.process_one()
            sent = await worker.send_one()
            if sent and settings.messaging_provider == "twilio":
                # Sandbox permits at most one message every three seconds.
                try:
                    await asyncio.wait_for(stop.wait(), timeout=3.1)
                except TimeoutError:
                    pass
            if not processed and not sent:
                try:
                    await asyncio.wait_for(stop.wait(), timeout=0.5)
                except TimeoutError:
                    pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    asyncio.run(run())
