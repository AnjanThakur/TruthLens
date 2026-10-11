"""Twilio Sandbox form webhooks. No provider calls run in the HTTP request."""

import re
import time
from urllib.parse import parse_qsl, urlsplit
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from starlette.datastructures import FormData

from .errors import ServiceError
from .meta_client import MIMES

router = APIRouter()
MESSAGE_SID = re.compile(r"(?:SM|MM)[0-9a-fA-F]{32}")


async def authenticated_form(request):
    settings = request.app.state.settings
    if settings.messaging_provider != "twilio":
        raise HTTPException(404, "Transport not enabled")
    if request.url.query:
        raise HTTPException(400, "Query parameters are not supported")
    if (
        request.headers.get("content-type", "").split(";")[0].lower()
        != "application/x-www-form-urlencoded"
    ):
        raise HTTPException(415, "Expected a form webhook")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > settings.max_webhook_bytes:
            raise HTTPException(413, "Webhook body too large")
    try:
        form = FormData(
            parse_qsl(
                data.decode("utf-8"), keep_blank_values=True, errors="strict", max_num_fields=128
            )
        )
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(400, "Invalid webhook form") from exc
    # Include every field, including future Twilio additions, in SDK validation.
    from twilio.request_validator import RequestValidator

    signed_url = settings.twilio_public_base_url + request.url.path
    if not RequestValidator(settings.twilio_auth_token.get_secret_value()).validate(
        signed_url, form, request.headers.get("x-twilio-signature", "")
    ):
        raise HTTPException(403, "Invalid signature")
    if form.get("AccountSid") != settings.twilio_account_sid:
        raise HTTPException(403, "Unexpected Twilio account")
    # Reject ambiguous forms even if their multi-value signature is valid.
    if any(len(form.getlist(key)) != 1 for key in form):
        raise HTTPException(400, "Duplicate webhook field")
    return form


def media_reference(url, settings, sid):
    parsed = urlsplit(url)
    prefix = f"/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages/{sid}/Media/"
    if (
        parsed.scheme != "https"
        or parsed.netloc != "api.twilio.com"
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith(prefix)
        or not re.fullmatch(r"ME[0-9a-fA-F]{32}", parsed.path.removeprefix(prefix))
    ):
        raise ValueError("Unexpected media reference")
    return parsed.path


@router.post("/webhook/twilio/whatsapp")
async def inbound(request: Request):
    form = await authenticated_form(request)
    config = request.app.state.settings
    try:
        sid, sender = form["MessageSid"], form["From"]
        if (
            not MESSAGE_SID.fullmatch(sid)
            or not re.fullmatch(r"whatsapp:\+[1-9][0-9]{5,14}", sender)
            or form.get("To") != config.twilio_whatsapp_number
        ):
            raise ValueError
        body, count = form.get("Body", ""), int(form.get("NumMedia", "0"))
        if len(body) > 24000 or not 0 <= count <= 10:
            raise ValueError
        message = {
            "id": f"twilio:{sid}",
            "from": sender.removeprefix("whatsapp:+"),
            "type": "text",
            # The worker replaces receipt time with Twilio's canonical date_created
            # BEFORE any verification or send; a retry cannot reopen the window.
            "timestamp": str(int(time.time())),
            "text": {"body": body},
        }
        if count == 1:
            mime = form.get("MediaContentType0", "").split(";")[0].lower()
            kind = next((key for key, values in MIMES.items() if mime in values), "unsupported")
            message["type"] = kind
            if kind != "unsupported":
                message[kind] = {
                    "id": media_reference(form["MediaUrl0"], config, sid),
                    "mime_type": mime,
                }
        elif count > 1:
            message["type"] = "unsupported"
        request.app.state.store.enqueue([message])
    except ServiceError as exc:
        raise HTTPException(
            503, "Queue temporarily unavailable", headers={"Retry-After": "60"}
        ) from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(400, "Invalid inbound message") from exc
    # Acknowledge immediately. Actual replies come from the durable worker, not
    # synchronous TwiML that could repeat paid verification on webhook retries.
    return Response("<Response/>", media_type="application/xml")


@router.post("/webhook/twilio/status/{outbox_id}")
async def status(request: Request, outbox_id: str):
    form = await authenticated_form(request)
    try:
        if str(UUID(outbox_id)) != outbox_id or not MESSAGE_SID.fullmatch(form["MessageSid"]):
            raise ValueError
    except (ValueError, KeyError) as exc:
        raise HTTPException(400, "Invalid status callback") from exc
    state = form.get("MessageStatus")
    if form.get("EventType") == "READ":
        state = "read"
    state = {"undelivered": "failed"}.get(state, state)
    request.app.state.store.delivery(
        {
            "id": f"twilio:{form['MessageSid']}",
            "status": state,
            "biz_opaque_callback_data": outbox_id,
        }
    )
    return Response(status_code=204)
