import asyncio
import json

import httpx
import pytest
from conftest import CLAIMS, StubFetcher, StubLLM, StubSearch
from fastapi.testclient import TestClient
from pydantic import SecretStr
from test_gemini_regressions import output

from app.errors import AppError
from app.main import create_app
from app.schemas.models import ClaimBatch, Decision, VerifyRequest, Wording
from app.services.providers import GeminiLLM
from app.services.quota import guidance


@pytest.mark.parametrize(
    "message",
    [
        "Rate limit exceeded: 20 requests per day. Retry in 5h27m44s.",
        "RESOURCE_EXHAUSTED GenerateRequestsPerDayPerProjectPerModel",
    ],
)
def test_daily_quota_does_not_retry_or_call_search_or_audio(settings, message):
    settings.gemini_api_key = SecretStr("fixture-secret")
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            429,
            json={"error": {"code": "RESOURCE_EXHAUSTED", "message": message + " fixture-secret"}},
        )

    llm = GeminiLLM(settings, httpx.MockTransport(handler))
    client = TestClient(create_app(settings, llm=llm, search=StubSearch(), fetcher=StubFetcher()))
    for _ in range(2):
        response = client.post("/api/verify", json={"text": CLAIMS[0]})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "llm_quota_exhausted"
        assert int(response.headers["Retry-After"]) > 0
        assert "fixture-secret" not in response.text
    response = client.post(
        "/api/extract", files={"file": ("voice.wav", b"RIFF1234WAVE" + b"\0" * 20)}
    )
    assert response.json()["error"]["code"] == "llm_quota_exhausted"
    assert len(calls) == 1 and llm.request_count == 1


async def test_transient_retry_after_is_respected(settings, monkeypatch):
    settings.gemini_api_key = SecretStr("test-only")
    waits = []
    calls = []

    async def sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr("app.services.providers.asyncio.sleep", sleep)

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "2"},
                json={"error": {"message": "Requests per minute exceeded", "code": "rate_limit"}},
            )
        return output(json.dumps({"detected_language": "en", "claims": [], "truncated": False}))

    await GeminiLLM(settings, httpx.MockTransport(handler)).structured("Extract", {}, ClaimBatch)
    assert waits == [2] and len(calls) == 2


async def test_long_transient_guidance_returns_without_early_retry(settings):
    settings.gemini_api_key = SecretStr("test-only")
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            429,
            headers={"Retry-After": "90"},
            json={"error": {"message": "RPM limit", "code": "rate_limit"}},
        )

    llm = GeminiLLM(settings, httpx.MockTransport(handler))
    for _ in range(2):
        with pytest.raises(AppError) as error:
            await llm.structured("Extract", {}, ClaimBatch)
        assert error.value.code == "llm_rate_limited" and error.value.retry_after_seconds >= 89
    assert len(calls) == 1


@pytest.mark.parametrize("header", ["NaN", "Infinity", "not a date"])
def test_malformed_retry_header_is_ignored(header):
    error = type(
        "ProviderError", (), {"response": httpx.Response(429, headers={"Retry-After": header})}
    )()
    assert guidance(error) == (False, None)


def test_google_retryinfo_and_daily_delay_parsing():
    daily, seconds = guidance(
        Exception(
            '{"status":"RESOURCE_EXHAUSTED","quotaId":"GenerateRequestsPerDay", "retryDelay":"17.5s"}'
        )
    )
    assert daily and seconds == 18


async def test_quota_gate_expires(settings, monkeypatch):
    llm = GeminiLLM(settings)
    instant = [100.0]
    monkeypatch.setattr("app.services.quota.time.monotonic", lambda: instant[0])
    llm.quota.block(settings.gemini_model, 10, True)
    with pytest.raises(AppError):
        llm.ensure_available()
    instant[0] = 111
    llm.ensure_available()
    assert not llm.quota.blocked


class CountingSearch(StubSearch):
    def __init__(self, fail=False):
        super().__init__(fail=fail)
        self.calls = 0

    async def search(self, query):
        self.calls += 1
        return await super().search(query)


def test_exact_verification_cache_cross_format_and_privacy_scope(settings):
    llm, search = StubLLM([CLAIMS[0]]), CountingSearch()
    client = TestClient(create_app(settings, llm, search, StubFetcher()))
    first = client.post("/api/verify", json={"text": CLAIMS[0], "input_type": "image"}).json()
    calls = len(llm.requests)
    second = client.post("/api/verify", json={"text": CLAIMS[0], "input_type": "pdf"}).json()
    assert len(llm.requests) == calls and search.calls == 1
    assert second["input"]["input_type"] == "pdf"
    assert second["input"]["extraction_details"]["verification_cache"] == "hit"
    assert second["verification_id"] == first["verification_id"]
    assert second["checked_at"] == first["checked_at"] and second["claims"] == first["claims"]
    second["claims"][0]["evidence"][0]["excerpt"] = "mutated locally"
    again = client.post("/api/verify", json={"text": CLAIMS[0]}).json()
    assert again["claims"] == first["claims"]
    altered = client.post(
        "/api/verify", json={"text": CLAIMS[0] + " Send your OTP urgently!"}
    ).json()
    assert (
        search.calls == 2
        and altered["claims"][0]["risk"]["score"] > first["claims"][0]["risk"]["score"]
    )
    client.post("/api/verify", json={"text": CLAIMS[0], "response_language": "mr"})
    assert search.calls == 3


async def test_verification_singleflight_expiry_and_capacity(settings, monkeypatch):
    settings.verification_cache_entries = 1
    llm, search = StubLLM([CLAIMS[0]]), CountingSearch()
    app = create_app(settings, llm, search, StubFetcher())
    verifier = app.state.verifier
    instant = [100.0]
    monkeypatch.setattr("app.services.cache.time.monotonic", lambda: instant[0])
    request = VerifyRequest(text=CLAIMS[0])
    a, b = await asyncio.gather(verifier.verify(request), verifier.verify(request))
    assert search.calls == 1 and a.verification_id == b.verification_id
    instant[0] += settings.verification_cache_ttl_seconds + 1
    await verifier.verify(request)
    assert search.calls == 2
    await verifier.verify(VerifyRequest(text=CLAIMS[0], audience="teen"))
    await verifier.verify(request)
    assert search.calls == 4 and len(verifier.cache.entries) == 1 and not verifier.cache.locks


def test_partial_failures_are_not_cached(settings):
    llm, search = StubLLM([CLAIMS[0]]), CountingSearch(fail=True)
    client = TestClient(create_app(settings, llm, search, StubFetcher()))
    for _ in range(2):
        assert client.post("/api/verify", json={"text": CLAIMS[0]}).json()["status"] == "partial"
    assert search.calls == 2


def test_assessment_quota_stops_searching_remaining_claims(settings):
    class Exhausted(StubLLM):
        async def structured(self, task, data, model):
            if model is Decision:
                raise AppError("llm_quota_exhausted", "Daily quota", 503, 3600)
            return await super().structured(task, data, model)

    search = CountingSearch()
    client = TestClient(create_app(settings, Exhausted(), search, StubFetcher()))
    result = client.post("/api/verify", json={"text": " ".join(CLAIMS)}).json()
    assert result["status"] == "partial" and len(result["claims"]) == 2
    assert search.calls == 1 and all(c["verdict"] == "unconfirmed" for c in result["claims"])


def test_wording_quota_preserves_verdict_and_stops_subsequent_searches(settings):
    class ExhaustedWording(StubLLM):
        async def structured(self, task, data, model):
            if model is Wording:
                raise AppError("llm_quota_exhausted", "Daily quota", 503, 3600)
            return await super().structured(task, data, model)

    search = CountingSearch()
    result = (
        TestClient(create_app(settings, ExhaustedWording(), search, StubFetcher()))
        .post("/api/verify", json={"text": " ".join(CLAIMS), "response_language": "hi"})
        .json()
    )
    assert result["status"] == "partial" and search.calls == 1
    assert result["claims"][0]["verdict"] == "verified" and result["claims"][0]["evidence"]
    assert result["claims"][1]["verdict"] == "unconfirmed" and not result["claims"][1]["evidence"]
    assert "explanation_fallback:llm_quota_exhausted" in result["warnings"]
