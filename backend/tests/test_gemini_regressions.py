import asyncio
import io
import json
import wave

import httpx
import pytest
from pydantic import SecretStr

from app.errors import AppError
from app.schemas.models import ClaimBatch
from app.services.extract.media import MediaExtractor
from app.services.extract.runtime import executable
from app.services.providers import GeminiLLM, provider_schema
from app.services.search.client import TavilySearch


def output(text):
    return httpx.Response(
        200,
        json={
            "status": "completed",
            "steps": [{"type": "model_output", "content": [{"type": "text", "text": text}]}],
        },
    )


@pytest.mark.parametrize(
    "status,code",
    [
        (400, "llm_provider_error"),
        (401, "llm_auth_error"),
        (403, "llm_auth_error"),
        (404, "llm_model_unavailable"),
        (429, "llm_rate_limited"),
        (503, "llm_provider_error"),
    ],
)
async def test_gemini_errors_sanitized_and_bounded(settings, status, code):
    settings.gemini_api_key = SecretStr("test-only-secret")
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(
            status,
            json={"error": {"message": "test-only-secret private input", "code": "upstream_error"}},
        )

    with pytest.raises(AppError) as error:
        await GeminiLLM(settings, httpx.MockTransport(handler)).structured(
            "Extract", {}, ClaimBatch
        )
    assert error.value.code == code
    assert "test-only-secret" not in str(error.value)
    assert "private input" not in str(error.value)
    assert calls == (2 if status in (429, 503) else 1)


async def test_gemini_transient_retry_then_valid_response(settings):
    settings.gemini_api_key = SecretStr("test-only")
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                503, json={"error": {"message": "temporary", "code": "unavailable"}}
            )
        return output(json.dumps({"detected_language": "en", "claims": [], "truncated": False}))

    assert not (
        await GeminiLLM(settings, httpx.MockTransport(handler)).structured(
            "Extract", {}, ClaimBatch
        )
    ).claims
    assert calls == 2


async def test_gemini_timeout_and_prompt_limit(settings):
    settings.gemini_api_key = SecretStr("test-only")

    def handler(request):
        raise httpx.ReadTimeout("test-only", request=request)

    with pytest.raises(AppError) as error:
        await GeminiLLM(settings, httpx.MockTransport(handler)).structured(
            "Extract", {}, ClaimBatch
        )
    assert error.value.code == "llm_timeout"
    settings.max_prompt_chars = 1000
    with pytest.raises(AppError) as error:
        await GeminiLLM(settings, httpx.MockTransport(handler)).structured(
            "Extract", {"text": "a" * 1001}, ClaimBatch
        )
    assert error.value.code == "prompt_too_large"


@pytest.mark.parametrize(
    "text",
    ["not JSON", '{"detected_language":"en","claims":[],"truncated":false,"invented":"value"}'],
)
async def test_gemini_strict_local_validation(settings, text):
    settings.gemini_api_key = SecretStr("test-only")
    with pytest.raises(AppError) as error:
        await GeminiLLM(settings, httpx.MockTransport(lambda r: output(text))).structured(
            "Extract", {}, ClaimBatch
        )
    assert error.value.code == "llm_output_invalid"


def test_schema_subset_preserves_named_properties():
    schema = provider_schema(ClaimBatch)
    assert "claim_text" in schema["properties"]["claims"]["items"]["properties"]
    assert "$ref" not in json.dumps(schema)
    assert "maxLength" not in json.dumps(schema)
    assert ClaimBatch.model_json_schema()["additionalProperties"] is False


async def test_search_singleflight_cache_copy_expiry_and_bounds(settings, monkeypatch):
    settings.tavily_api_key = SecretStr("test-only")
    settings.search_cache_entries = 1
    instant = [100.0]
    monkeypatch.setattr("app.services.search.client.time.monotonic", lambda: instant[0])
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        assert json.loads(request.content)["search_depth"] == "basic"
        return httpx.Response(
            200, json={"results": [{"url": "https://rbi.org.in/fixture", "content": "fixture"}]}
        )

    search = TavilySearch(settings, httpx.MockTransport(handler))
    first, second = await asyncio.gather(
        search.search(" RBI currency "), search.search("rbi  currency")
    )
    assert calls == 1
    first[0].content = "mutated"
    assert second[0].content == "fixture"
    instant[0] += settings.search_cache_ttl_seconds + 1
    await search.search("rbi currency")
    assert calls == 2
    await search.search("other")
    await search.search("rbi currency")
    assert calls == 4 and len(search._cache) == 1


async def test_search_errors_not_cached(settings):
    settings.tavily_api_key = SecretStr("test-only")
    search = TavilySearch(settings, httpx.MockTransport(lambda r: httpx.Response(401, json={})))
    for _ in range(2):
        with pytest.raises(AppError):
            await search.search("same")
    assert search.request_count == 2 and not search._cache


async def test_invalid_and_overlong_audio_rejected_before_provider(settings):
    settings.gemini_api_key = SecretStr("test-only")
    extractor = MediaExtractor(settings)
    with pytest.raises(AppError) as error:
        await extractor.extract(b"RIFF1234WAVE" + b"\0" * 20)
    assert error.value.code == "invalid_audio"
    settings.max_audio_seconds = 1
    data = io.BytesIO()
    with wave.open(data, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\0\0" * 32000)
    with pytest.raises(AppError) as error:
        await extractor.extract(data.getvalue())
    assert error.value.code == "audio_too_long"


def test_explicit_invalid_runtime_path_never_falls_back():
    assert executable("tesseract", "Z:/missing/tesseract.exe") is None
    assert executable("ffmpeg", "Z:/missing/ffmpeg.exe") is None
