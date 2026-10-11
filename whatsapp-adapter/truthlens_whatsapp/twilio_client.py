"""Optional Twilio Sandbox transport; no model/extraction code lives here."""

import re
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from uuid import UUID

import httpx

from .errors import AmbiguousSend, ServiceError
from .meta_client import MIMES, retry_after


def split_reply(body, limit=1500):
    """Preserve clickable URLs while counting UTF-16 conservatively."""
    if limit < 128:
        raise ValueError("Reply limit must allow the source limitation notice")
    parts, current, size = [], [], 0
    for token in re.findall(r"https?://\S+|[\s\S]", body):
        units = len(token.encode("utf-16-le")) // 2
        if units > limit:
            token = "[Source URL omitted: it exceeds the WhatsApp reply limit. Check the original source before acting.]"
            units = len(token)
        if size + units > limit:
            parts.append("".join(current))
            current, size = [], 0
        current.append(token)
        size += units
    if current:
        parts.append("".join(current))
    return parts


class TwilioClient:
    def __init__(self, settings, client):
        self.settings, self.client = settings, client
        self.base = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}"
        self.auth = httpx.BasicAuth(
            settings.twilio_account_sid, settings.twilio_auth_token.get_secret_value()
        )

    def enabled(self):
        if (
            self.settings.messaging_provider != "twilio"
            or not self.settings.twilio_outbound_enabled
        ):
            raise ServiceError("twilio_disabled")

    async def received_at(self, message):
        self.enabled()
        sid = message["id"].removeprefix("twilio:")
        if not re.fullmatch(r"(?:SM|MM)[0-9a-fA-F]{32}", sid):
            raise ServiceError("window_expired")
        try:
            async with self.client.stream(
                "GET",
                f"{self.base}/Messages/{sid}.json",
                auth=self.auth,
                timeout=20,
                follow_redirects=False,
            ) as response:
                if not response.is_success:
                    raise ServiceError("window_expired")
                raw = bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 65536:
                        raise ServiceError("window_expired")
                import json

                result = json.loads(raw)
            if (
                result["sid"] != sid
                or result["account_sid"] != self.settings.twilio_account_sid
                or result["from"] != f"whatsapp:+{message['from']}"
                or result["to"] != self.settings.twilio_whatsapp_number
                or result["status"] != "received"
            ):
                raise ServiceError("window_expired")
            value = result["date_created"]
            try:
                created = parsedate_to_datetime(value)
            except ValueError:
                created = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if created.tzinfo is None:
                raise ValueError
            timestamp = int(created.timestamp())
            if timestamp > time.time() + 300 or time.time() - timestamp >= 86400:
                raise ServiceError("window_expired")
            return timestamp
        except (httpx.HTTPError, KeyError, ValueError, TypeError, AttributeError) as exc:
            # An unverified receipt time never authorizes a provider call or reply.
            raise ServiceError("window_expired") from exc

    async def send(self, to, body, callback):
        self.enabled()
        if not re.fullmatch(r"[1-9][0-9]{5,14}", to) or len(body.encode("utf-16-le")) // 2 > 1500:
            raise ServiceError("twilio_rejected")
        if str(UUID(callback)) != callback:
            raise ServiceError("twilio_rejected")
        try:
            response = await self.client.post(
                f"{self.base}/Messages.json",
                auth=self.auth,
                data={
                    "From": self.settings.twilio_whatsapp_number,
                    "To": f"whatsapp:+{to}",
                    "Body": body,
                    "StatusCallback": f"{self.settings.twilio_public_base_url}/webhook/twilio/status/{callback}",
                },
                timeout=20,
                follow_redirects=False,
            )
        except httpx.HTTPError as exc:
            raise AmbiguousSend("send_uncertain") from exc
        if response.status_code == 429:
            raise ServiceError("twilio_rate_limit", retry_after=retry_after(response) or 60)
        if response.status_code >= 500:
            raise AmbiguousSend("send_uncertain")
        if not response.is_success:
            raise ServiceError("twilio_rejected")
        try:
            sid = response.json()["sid"]
            if not isinstance(sid, str) or not re.fullmatch(r"(?:SM|MM)[0-9a-fA-F]{32}", sid):
                raise ValueError
            return f"twilio:{sid}"
        except (KeyError, TypeError, ValueError) as exc:
            raise AmbiguousSend("send_uncertain") from exc

    async def media(self, path, kind):
        self.enabled()
        prefix = f"/2010-04-01/Accounts/{self.settings.twilio_account_sid}/Messages/"
        if kind not in MIMES or not re.fullmatch(
            re.escape(prefix) + r"(?:SM|MM)[0-9a-fA-F]{32}/Media/ME[0-9a-fA-F]{32}", path
        ):
            raise ServiceError("unsupported_media")
        try:
            async with self.client.stream(
                "GET",
                f"https://api.twilio.com{path}",
                auth=self.auth,
                follow_redirects=False,
                timeout=30,
            ) as response:
                # Refuse redirects rather than forward account credentials to a CDN.
                # Redirecting media remains a documented live acceptance blocker.
                if not response.is_success:
                    raise ServiceError("media_unavailable")
                mime = response.headers.get("content-type", "").split(";")[0].lower()
                if mime not in MIMES[kind]:
                    raise ServiceError("unsupported_media")
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > self.settings.max_media_bytes:
                        raise ServiceError("media_too_large")
            valid = (
                (mime == "image/png" and data.startswith(b"\x89PNG\r\n\x1a\n"))
                or (mime == "image/jpeg" and data.startswith(b"\xff\xd8\xff"))
                or (mime == "application/pdf" and data.startswith(b"%PDF-"))
                or (mime == "audio/ogg" and data.startswith(b"OggS"))
                or (
                    mime in {"audio/wav", "audio/x-wav"}
                    and data.startswith(b"RIFF")
                    and data[8:12] == b"WAVE"
                )
                or (
                    mime == "audio/mpeg"
                    and (
                        data.startswith(b"ID3")
                        or (len(data) > 1 and data[0] == 255 and data[1] & 224 == 224)
                    )
                )
            )
            if not valid:
                raise ServiceError("unsupported_media")
            return bytes(data), mime
        except httpx.HTTPError as exc:
            raise ServiceError("media_unavailable") from exc
