import httpx

from .contracts import immutable, validate
from .errors import ServiceError
from .meta_client import retry_after


class TruthLensClient:
    def __init__(self, settings, client, *, request_budget=None):
        self.settings, self.client = settings, client
        self.request_budget = request_budget

    async def call(self, path, schema, **kwargs):
        if not (self.settings.backend_enabled and self.settings.provider_credentials_authorized):
            raise ServiceError("backend_disabled")
        if self.request_budget is not None:
            self.request_budget.reserve()
        headers = {}
        if self.settings.truthlens_backend_token.get_secret_value():
            headers["Authorization"] = (
                f"Bearer {self.settings.truthlens_backend_token.get_secret_value()}"
            )
        try:
            async with self.client.stream(
                "POST",
                self.settings.truthlens_backend_url.rstrip("/") + path,
                headers=headers,
                timeout=self.settings.backend_timeout_seconds,
                **kwargs,
            ) as response:
                if not response.is_success:
                    raise ServiceError("backend_unavailable", retry_after=retry_after(response))
                chunks, total = [], 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > 2097152:
                        raise ServiceError("backend_contract")
                    chunks.append(chunk)
            import json

            return validate(json.loads(b"".join(chunks)), schema)
        except (httpx.HTTPError, ValueError) as exc:
            raise ServiceError("backend_unavailable") from exc

    async def verify(self, text, kind, language):
        request = {
            "text": text,
            "input_type": kind,
            "input_language": "auto",
            "response_language": language,
            "audience": "adult",
            "jurisdiction": "IN",
        }
        validate(request, "VerifyRequest")
        if len(text) > 24000:
            raise ServiceError("text_too_large")
        result = await self.call("/api/verify", "VerificationResult", json=request)
        if result["verification_id"].startswith("mock-") or any(
            "synthetic" in w.lower() for w in result["warnings"]
        ):
            raise ServiceError("backend_contract")
        return result

    async def extract(self, data, content_type):
        return await self.call(
            "/api/extract", "ExtractionResult", files={"file": ("submission", data, content_type)}
        )

    async def extract_url(self, url):
        validate({"url": url}, "URLRequest")
        return await self.call("/api/extract/url", "ExtractionResult", json={"url": url})

    async def explain(self, result, language):
        response = await self.call(
            "/api/explain",
            "VerificationResult",
            json={"result": result, "language": language, "audience": result["audience"]},
        )
        if immutable(result) != immutable(response) or response["response_language"] != language:
            raise ServiceError("backend_contract")
        return response
