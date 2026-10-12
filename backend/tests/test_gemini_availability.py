"""Real SDK with mocked HTTP: stable routing and bounded outage recovery."""

import json

import httpx
import pytest
from pydantic import SecretStr, ValidationError
from test_gemini_regressions import output

from app.errors import AppError
from app.schemas.models import ClaimBatch
from app.services.providers import CURRENT_MODEL_BUDGET, GeminiLLM, ModelBudget, retry_wait

SUCCESS = json.dumps({"detected_language": "en", "claims": [], "truncated": False})


@pytest.mark.parametrize("version", ["v1", "v1beta"])
async def test_sdk_routes_to_selected_version_without_changing_schema_or_privacy(settings, version):
    settings.gemini_api_key = SecretStr("fixture-key")
    settings.gemini_api_version = version
    calls = []

    def handler(request):
        calls.append(request)
        assert request.url.path == f"/{version}/interactions"
        body = json.loads(request.content)
        assert body["store"] is False
        assert body["model"] == settings.gemini_model
        assert body["response_format"]["mime_type"] == "application/json"
        assert "claims" in body["response_format"]["schema"]["properties"]
        assert json.loads(body["input"][0]["content"][0]["text"])["text"] == "₹ हिंदी मराठी"
        return output(SUCCESS)

    llm = GeminiLLM(settings, httpx.MockTransport(handler))
    result = await llm.structured("Extract", {"text": "₹ हिंदी मराठी"}, ClaimBatch)
    assert not result.claims and len(calls) == llm.request_count == 1


def test_stable_api_default_and_unknown_version_rejected(settings):
    assert settings.gemini_api_version == "v1"
    with pytest.raises(ValidationError):
        type(settings)(_env_file=None, gemini_api_version="untrusted/route")


@pytest.mark.parametrize(
    "status,retry_after", [(500, None), (502, None), (503, None), (504, None), (503, "90")]
)
async def test_failed_server_attempt_opens_model_cooldown_and_recovers_after_expiry(
    settings, monkeypatch, caplog, status, retry_after
):
    settings.gemini_api_key = SecretStr("fixture-key")
    settings.provider_max_attempts = 1
    clock = [100.0]
    monkeypatch.setattr("app.services.providers.time.monotonic", lambda: clock[0])
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(
                status,
                headers={"Retry-After": retry_after} if retry_after else {},
                json={
                    "error": {"code": "service_unavailable", "message": "fixture-key private text"}
                },
            )
        return output(SUCCESS)

    llm = GeminiLLM(settings, httpx.MockTransport(handler))
    for _ in range(2):
        with pytest.raises(AppError) as caught:
            await llm.structured("Extract", {}, ClaimBatch)
        assert caught.value.code == "llm_provider_error"
        assert caught.value.category == "transient_server"
        assert caught.value.provider_status == status
        assert caught.value.retry_after_seconds == (90 if retry_after else 15)
    assert len(calls) == llm.request_count == 1
    assert "no new provider call" in caught.value.message
    assert "fixture-key" not in caplog.text and "private text" not in caplog.text
    clock[0] += (90 if retry_after else 15) + 1
    assert not (await llm.structured("Extract", {}, ClaimBatch)).claims
    assert len(calls) == llm.request_count == 2
    assert not llm._server_cooldowns


async def test_cooldown_is_model_specific_and_daily_quota_still_has_priority(settings):
    settings.gemini_api_key = SecretStr("fixture-key")
    settings.provider_max_attempts = 1

    def handler(request):
        if json.loads(request.content)["model"] == settings.gemini_model:
            return httpx.Response(503, json={"error": {"code": "service_unavailable"}})
        return output(SUCCESS)

    llm = GeminiLLM(settings, httpx.MockTransport(handler))
    with pytest.raises(AppError):
        await llm.structured("Extract", {}, ClaimBatch)
    llm.ensure_available("different-configured-model")
    llm.quota.block(settings.gemini_model, 3600, True)
    with pytest.raises(AppError) as caught:
        await llm.structured("Extract", {}, ClaimBatch)
    assert caught.value.code == "llm_quota_exhausted"
    assert llm.request_count == 1


async def test_retry_has_jitter_but_respects_explicit_guidance_and_global_budget(
    settings, monkeypatch
):
    for attempt in range(3):
        assert min(2, 2**attempt) <= retry_wait(attempt) <= min(2, 2**attempt) + 0.25
    settings.gemini_api_key = SecretStr("fixture-key")
    waits = []

    async def sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr("app.services.providers.asyncio.sleep", sleep)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            503, headers={"Retry-After": "2"}, json={"error": {"code": "service_unavailable"}}
        )

    llm = GeminiLLM(settings, httpx.MockTransport(handler))
    token = CURRENT_MODEL_BUDGET.set(ModelBudget(1))
    try:
        with pytest.raises(AppError) as caught:
            await llm.structured("Extract", {}, ClaimBatch)
    finally:
        CURRENT_MODEL_BUDGET.reset(token)
    assert caught.value.provider_status == 503
    assert llm.request_count == len(calls) == 1 and not waits


async def test_stable_daily_quota_code_without_daily_wording_never_retries(settings, monkeypatch):
    settings.gemini_api_key = SecretStr("fixture-key")
    settings.provider_max_attempts = 3

    async def no_sleep(seconds):
        pytest.fail("Daily quota must not sleep or retry")

    monkeypatch.setattr("app.services.providers.asyncio.sleep", no_sleep)
    llm = GeminiLLM(
        settings,
        httpx.MockTransport(
            lambda request: httpx.Response(
                429, json={"error": {"code": "quota_exceeded", "message": "Limit reached"}}
            )
        ),
    )
    for _ in range(2):
        with pytest.raises(AppError) as caught:
            await llm.structured("Extract", {}, ClaimBatch)
        assert caught.value.code == "llm_quota_exhausted"
    assert llm.request_count == 1 and not llm._server_cooldowns
