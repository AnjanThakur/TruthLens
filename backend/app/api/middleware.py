import asyncio
import json
import logging
import time
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import Settings
from app.errors import AppError
from app.services.diagnostics import request_id as diagnostic_request_id

logger = logging.getLogger("truthlens.requests")


class SafetyMiddleware:
    def __init__(self, app: ASGIApp, settings: Settings):
        self.app, self.settings = app, settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid4())
        diagnostic_token = diagnostic_request_id.set(request_id)
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.monotonic()
        response_started = False
        status = 500

        async def tracked_send(message: Message):
            nonlocal response_started, status
            if message["type"] == "http.response.start":
                response_started = True
                status = message["status"]
                message["headers"] = [
                    *message.get("headers", []),
                    (b"x-request-id", request_id.encode()),
                    (b"cache-control", b"no-store"),
                ]
            await send(message)

        async def fail(code, message, code_status):
            body = json.dumps(
                {"error": {"code": code, "message": message, "request_id": request_id}}
            ).encode()
            await tracked_send(
                {
                    "type": "http.response.start",
                    "status": code_status,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await tracked_send({"type": "http.response.body", "body": body})

        try:
            async with asyncio.timeout(self.settings.request_timeout_seconds):
                # Bound the actual stream before multipart parsing/spooling. Content-Length
                # is not trusted. Only one in-memory upload body is accepted per request.
                upload = scope.get("path") == "/api/extract"
                if upload:
                    limit = self.settings.max_upload_bytes + 65536
                elif scope.get("path") == "/api/explain":
                    limit = 2 * 1024 * 1024
                else:
                    limit = 256 * 1024
                body = bytearray()
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    if len(body) + len(chunk) > limit:
                        raise AppError(
                            "request_too_large", "The request exceeds the safe size limit.", 413
                        )
                    body.extend(chunk)
                    if not message.get("more_body", False):
                        break
                delivered = False

                async def bounded_receive():
                    nonlocal delivered
                    if not delivered:
                        delivered = True
                        return {"type": "http.request", "body": bytes(body), "more_body": False}
                    return await receive()

                await self.app(scope, bounded_receive, tracked_send)
        except AppError as exc:
            if not response_started:
                await fail(exc.code, exc.message, exc.status)
        except TimeoutError:
            if not response_started:
                await fail(
                    "request_timeout",
                    "This request took too long. Try a shorter message or smaller file.",
                    504,
                )
        except Exception:
            # Never log raw exception details, content, URLs, headers or tokens.
            if not response_started:
                await fail(
                    "internal_error", "The request could not be completed. Please retry.", 500
                )
        finally:
            logger.info(
                json.dumps(
                    {
                        "request_id": request_id,
                        "method": scope["method"],
                        "status": status,
                        "elapsed_ms": round((time.monotonic() - started) * 1000),
                    }
                )
            )
            diagnostic_request_id.reset(diagnostic_token)
