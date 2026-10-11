import hashlib
import hmac
import json
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from .config import Settings
from .errors import ServiceError
from .store import Store


def create_app(settings=None, store=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.settings = settings or Settings()
        app.state.store = store or Store(app.state.settings)
        yield

    app = FastAPI(
        title="TruthLens WhatsApp transport",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.middleware("http")
    async def headers(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/health")
    async def health(request: Request):
        config = request.app.state.settings
        return {
            "status": "ok",
            "response_mode": config.response_mode,
            "meta_outbound_enabled": config.meta_outbound_enabled,
            "note": "Configuration only; not proof of Meta delivery or provider availability.",
        }

    @app.get("/webhook/whatsapp", response_class=PlainTextResponse)
    async def challenge(request: Request):
        query = request.query_params
        expected = request.app.state.settings.whatsapp_verify_token.get_secret_value()
        token = query.get("hub.verify_token", "")
        value = query.get("hub.challenge", "")
        if (
            query.get("hub.mode") != "subscribe"
            or not hmac.compare_digest(token.encode(), expected.encode())
            or not value
            or len(value) > 1024
        ):
            raise HTTPException(403, "Webhook verification rejected")
        return value

    @app.post("/webhook/whatsapp")
    async def webhook(request: Request):
        config = request.app.state.settings
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > config.max_webhook_bytes:
                raise HTTPException(413, "Webhook body too large")
        digest = hmac.new(
            config.meta_app_secret.get_secret_value().encode(), data, hashlib.sha256
        ).hexdigest()
        signature = request.headers.get("x-hub-signature-256", "")
        if not hmac.compare_digest(signature.encode(), f"sha256={digest}".encode()):
            raise HTTPException(403, "Invalid signature")
        try:
            event = json.loads(data)
            if not isinstance(event, dict):
                raise ValueError
            if event.get("object") != "whatsapp_business_account":
                return {"accepted": True}
            messages, statuses = [], []
            for entry in event.get("entry", []):
                if entry.get("id") != config.whatsapp_waba_id:
                    continue
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    if (
                        change.get("field") != "messages"
                        or value.get("metadata", {}).get("phone_number_id")
                        != config.whatsapp_phone_number_id
                    ):
                        continue
                    for message in value.get("messages", []):
                        ident, sender, kind = message["id"], message["from"], message["type"]
                        timestamp = int(message["timestamp"])
                        if (
                            not isinstance(ident, str)
                            or not 1 <= len(ident) <= 512
                            or not isinstance(sender, str)
                            or not sender.isdecimal()
                            or not 5 <= len(sender) <= 20
                            or not isinstance(kind, str)
                        ):
                            raise ValueError
                        if timestamp > time.time() + 300 or timestamp < time.time() - 7 * 86400:
                            continue
                        # Retain only data needed to route this submission; drop contacts and profiles.
                        clean = {
                            "id": ident,
                            "from": sender,
                            "type": kind,
                            "timestamp": str(timestamp),
                        }
                        if kind == "text":
                            body = message["text"]["body"]
                            if not isinstance(body, str) or len(body) > 24000:
                                raise ValueError
                            clean["text"] = {"body": body}
                        elif kind in {"image", "audio", "document"}:
                            media_id = message[kind]["id"]
                            if (
                                not isinstance(media_id, str)
                                or not media_id.isdecimal()
                                or len(media_id) > 64
                            ):
                                raise ValueError
                            clean[kind] = {
                                "id": media_id,
                                "mime_type": message[kind].get("mime_type", ""),
                            }
                        messages.append(clean)
                    statuses.extend(value.get("statuses", []))
            if len(messages) > 100 or len(statuses) > 100:
                raise ValueError
            request.app.state.store.enqueue(messages)
            for status in statuses:
                request.app.state.store.delivery(status)
        except ServiceError as exc:
            raise HTTPException(
                503, "Queue temporarily unavailable", headers={"Retry-After": "60"}
            ) from exc
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise HTTPException(400, "Invalid webhook event") from exc
        return {"accepted": True}

    return app


app = create_app()
