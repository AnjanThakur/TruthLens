import base64
import hashlib
from urllib.parse import urlsplit

import httpx

from .errors import AmbiguousSend, ServiceError

MIMES = {
    "image": {"image/png", "image/jpeg"},
    "audio": {"audio/ogg", "audio/mpeg", "audio/wav", "audio/x-wav"},
    "document": {"application/pdf"},
}


def retry_after(response):
    try:
        return min(max(int(response.headers.get("retry-after", "0")), 0), 3600)
    except ValueError:
        return 0


class MetaClient:
    def __init__(self, settings, client):
        self.settings, self.client = settings, client
        self.base = f"https://graph.facebook.com/{settings.graph_api_version}"
        self.headers = {
            "Authorization": f"Bearer {settings.whatsapp_access_token.get_secret_value()}"
        }

    def enabled(self):
        if not self.settings.meta_outbound_enabled:
            raise ServiceError("meta_disabled")

    async def send(self, to, body, callback):
        self.enabled()
        try:
            response = await self.client.post(
                f"{self.base}/{self.settings.whatsapp_phone_number_id}/messages",
                headers=self.headers,
                json={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": to,
                    "type": "text",
                    "text": {"preview_url": False, "body": body},
                    "biz_opaque_callback_data": callback,
                },
                timeout=20,
            )
        except httpx.HTTPError as exc:
            raise AmbiguousSend("send_uncertain") from exc
        if response.status_code == 429:
            raise ServiceError("meta_rate_limit", retry_after=retry_after(response) or 60)
        if response.status_code >= 500:
            raise AmbiguousSend("send_uncertain")
        if not response.is_success:
            raise ServiceError("meta_rejected")
        try:
            value = response.json()["messages"][0]["id"]
            if not isinstance(value, str) or not value or len(value) > 512:
                raise ValueError
            return value
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AmbiguousSend("send_uncertain") from exc

    async def media(self, media_id, kind):
        self.enabled()
        if not isinstance(media_id, str) or not media_id.isdecimal() or len(media_id) > 64:
            raise ServiceError("unsupported_media")
        try:
            response = await self.client.get(
                f"{self.base}/{media_id}",
                headers=self.headers,
                params={"phone_number_id": self.settings.whatsapp_phone_number_id},
                timeout=20,
            )
            if not response.is_success:
                raise ServiceError("media_unavailable")
            metadata = response.json()
            content_type = metadata["mime_type"].split(";")[0].lower()
            if content_type not in MIMES[kind]:
                raise ServiceError("unsupported_media")
            if int(metadata.get("file_size", 0)) > self.settings.max_media_bytes:
                raise ServiceError("media_too_large")
            url = urlsplit(metadata["url"])
            # Do not send bearer credentials to arbitrary hosts or follow redirects.
            if (
                url.scheme != "https"
                or url.hostname != "lookaside.fbsbx.com"
                or url.username
                or url.password
                or url.port not in {None, 443}
            ):
                raise ServiceError("media_host")
            async with self.client.stream(
                "GET", metadata["url"], headers=self.headers, timeout=30
            ) as downloaded:
                if not downloaded.is_success:
                    raise ServiceError("media_unavailable")
                actual_type = downloaded.headers.get("content-type", "").split(";")[0].lower()
                if actual_type not in {content_type, "application/octet-stream"}:
                    raise ServiceError("unsupported_media")
                chunks, total = [], 0
                async for chunk in downloaded.aiter_bytes():
                    total += len(chunk)
                    if total > self.settings.max_media_bytes:
                        raise ServiceError("media_too_large")
                    chunks.append(chunk)
            data = b"".join(chunks)
            if not data:
                raise ServiceError("media_empty")
            expected = metadata.get("sha256")
            digest = hashlib.sha256(data)
            if expected and expected not in {
                digest.hexdigest(),
                base64.b64encode(digest.digest()).decode(),
            }:
                raise ServiceError("media_checksum")
            valid = (
                (
                    kind == "image"
                    and (data.startswith(b"\x89PNG\r\n\x1a\n") or data.startswith(b"\xff\xd8\xff"))
                )
                or (kind == "document" and data.startswith(b"%PDF-"))
                or (
                    kind == "audio"
                    and (
                        data.startswith((b"OggS", b"ID3"))
                        or (data.startswith(b"RIFF") and data[8:12] == b"WAVE")
                        or (data[0] == 255 and len(data) > 1 and data[1] & 224 == 224)
                    )
                )
            )
            if not valid:
                raise ServiceError("unsupported_media")
            return data, content_type
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise ServiceError("media_unavailable") from exc
