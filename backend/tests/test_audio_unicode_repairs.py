import base64
import io
import json
import logging
import wave

import httpx
import pytest
from conftest import StubLLM, StubSearch, article
from fastapi.testclient import TestClient
from pydantic import SecretStr
from test_gemini_regressions import output
from test_http_security import Resolver

from app.errors import AppError
from app.main import create_app
from app.services.extract.media import MediaExtractor
from app.services.extract.url import SafeFetcher, article_from_html
from app.services.providers import GeminiLLM
from app.services.search.client import SearchHit

HINDI = "भारत में ₹५०० की राशि दी गई है। पुस्तकालय रविवार को खुला रहता है।"
MARATHI = "महाराष्ट्रातील वाचनालय रविवारी उघडे असते. मूळ बातमी वाचा."
TITLE = "भारत आणि महाराष्ट्र ₹५००"


def wav_bytes():
    audio = io.BytesIO()
    with wave.open(audio, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0\0" * 160)
    return audio.getvalue()


def provider_failure(status=503, retry_after=None):
    return httpx.Response(
        status,
        headers={"Retry-After": retry_after} if retry_after else {},
        json={"error": {"code": "unavailable", "message": "fixture-secret private speech"}},
    )


@pytest.mark.parametrize("retry_after,expected_wait", [(None, 0.5), ("2", 2)])
async def test_real_audio_adapter_recovers_from_503_without_changing_audio(
    settings, monkeypatch, caplog, retry_after, expected_wait
):
    settings.gemini_api_key = SecretStr("fixture-secret")
    caplog.set_level(logging.WARNING, logger="truthlens.diagnostics")
    waits, calls = [], []

    async def sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr("app.services.providers.asyncio.sleep", sleep)

    def handler(request):
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            return provider_failure(retry_after=retry_after)
        return output(json.dumps({"text": HINDI + " " + MARATHI, "detected_language": "hi"}))

    provider = GeminiLLM(settings, httpx.MockTransport(handler))
    result = await MediaExtractor(settings, provider=provider).extract(wav_bytes())
    assert result.text == HINDI + " " + MARATHI and result.input_type == "audio"
    assert len(calls) == provider.request_count == 2 and waits == [expected_wait]
    assert calls[0] == calls[1]
    audio = calls[0]["input"][0]["content"][0]
    assert audio["mime_type"] == "audio/wav" and base64.b64decode(audio["data"]) == wav_bytes()
    event = next(r.truthlens_event for r in caplog.records if hasattr(r, "truthlens_event"))
    assert event["stage"] == "transcription" and event["category"] == "transient_retry"
    assert event["provider_http_status"] == 503 and event["attempt"] == 1
    assert "fixture-secret" not in caplog.text and "private speech" not in caplog.text


@pytest.mark.parametrize(
    "attempts,wait_budget,expected_waits", [(1, 3, []), (2, 3, [0.5]), (3, 3, [0.5, 1]), (3, 0, [])]
)
async def test_persistent_audio_503_is_bounded_and_retains_sanitized_diagnostics(
    settings, monkeypatch, caplog, attempts, wait_budget, expected_waits
):
    settings.gemini_api_key = SecretStr("fixture-secret")
    settings.provider_max_attempts = attempts
    settings.provider_max_retry_wait_seconds = wait_budget
    caplog.set_level(logging.WARNING, logger="truthlens.diagnostics")
    waits = []

    async def sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr("app.services.providers.asyncio.sleep", sleep)
    provider = GeminiLLM(settings, httpx.MockTransport(lambda r: provider_failure()))
    with pytest.raises(AppError) as error:
        await MediaExtractor(settings, provider=provider).extract(wav_bytes())
    assert provider.request_count == len(expected_waits) + 1 and waits == expected_waits
    assert error.value.code == "transcription_provider_error" and error.value.status == 502
    assert error.value.category == "transient_server" and error.value.provider_status == 503
    assert "Retry later" in error.value.message and "shorter WAV" not in error.value.message
    events = [r.truthlens_event for r in caplog.records if hasattr(r, "truthlens_event")]
    assert events[-1]["stage"] == "transcription" and events[-1]["category"] == "transient_server"
    assert events[-1]["provider_http_status"] == 503
    assert "fixture-secret" not in caplog.text + error.value.message
    assert "private speech" not in caplog.text + error.value.message


def test_audio_long_503_guidance_returns_without_early_retry_and_preserves_error_contract(
    settings, caplog
):
    settings.gemini_api_key = SecretStr("fixture-secret")
    caplog.set_level(logging.WARNING, logger="truthlens.diagnostics")
    provider = GeminiLLM(
        settings, httpx.MockTransport(lambda r: provider_failure(retry_after="90"))
    )
    client = TestClient(create_app(settings, llm=provider))
    response = client.post("/api/extract", files={"file": ("voice.wav", wav_bytes(), "audio/wav")})
    assert response.status_code == 502 and provider.request_count == 1
    assert response.headers["Retry-After"] == "90"
    error = response.json()["error"]
    assert set(error) == {"code", "message", "request_id"}
    assert error["code"] == "transcription_provider_error"
    events = [r.truthlens_event for r in caplog.records if hasattr(r, "truthlens_event")]
    assert events[-1]["request_id"] == response.headers["x-request-id"] == error["request_id"]
    assert (
        events[-1]["category"] == "transient_server" and events[-1]["provider_http_status"] == 503
    )
    assert "fixture-secret" not in response.text + caplog.text


async def test_audio_daily_quota_fail_fast_survives_retry_changes(settings, monkeypatch):
    settings.gemini_api_key = SecretStr("fixture-secret")
    settings.provider_max_attempts = 3

    async def no_sleep(seconds):
        pytest.fail("Daily quota must not back off or retry")

    monkeypatch.setattr("app.services.providers.asyncio.sleep", no_sleep)
    provider = GeminiLLM(
        settings,
        httpx.MockTransport(
            lambda r: httpx.Response(
                429,
                json={
                    "error": {
                        "code": "RESOURCE_EXHAUSTED",
                        "message": "Daily quota exhausted; retry in 3600s.",
                    }
                },
            )
        ),
    )
    extractor = MediaExtractor(settings, provider=provider)
    for _ in range(2):
        with pytest.raises(AppError) as error:
            await extractor.extract(wav_bytes())
        assert error.value.code == "llm_quota_exhausted" and error.value.retry_after_seconds > 0
    assert provider.request_count == 1


async def test_audio_timeout_remains_bounded_and_safely_classified(settings, caplog):
    settings.gemini_api_key = SecretStr("fixture-secret")
    caplog.set_level(logging.WARNING, logger="truthlens.diagnostics")

    def handler(request):
        raise httpx.ReadTimeout("fixture-secret private speech", request=request)

    provider = GeminiLLM(settings, httpx.MockTransport(handler))
    with pytest.raises(AppError) as error:
        await MediaExtractor(settings, provider=provider).extract(wav_bytes())
    assert error.value.code == "transcription_provider_error" and error.value.status == 504
    assert provider.request_count == 1 and "timed out" in error.value.message
    assert "fixture-secret" not in caplog.text + error.value.message
    event = next(r.truthlens_event for r in caplog.records if hasattr(r, "truthlens_event"))
    assert event["stage"] == "transcription" and event["category"] == "timeout"


@pytest.mark.parametrize("fallback", [False, True])
@pytest.mark.parametrize(
    "declaration", ["", '<meta charset="UTF-8">', '<meta charset="iso-8859-1">']
)
def test_unicode_webpage_text_title_and_dates_are_preserved(monkeypatch, fallback, declaration):
    if fallback:
        monkeypatch.setattr("trafilatura.bare_extraction", lambda *args, **kwargs: None)
    body = article(HINDI + " " + MARATHI, title=TITLE).replace(
        b"</head>", declaration.encode() + b"</head>"
    )
    result = article_from_html(body, "https://public.test/news")
    assert HINDI in result.text and MARATHI in result.text
    assert result.extraction_details["title"] == TITLE
    assert result.extraction_details["published_at"] == "2026-10-09"
    assert result.extraction_details["url"] == "https://public.test/news"
    assert result.extraction_details["text_encoding"] == "utf-8"
    assert result.extraction_details["content_complete"]
    if fallback:
        assert result.extraction_details["article_extraction"] == "semantic_html_fallback"


@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-16", "utf-32"])
def test_unicode_bom_webpage_preserves_publication_metadata(encoding):
    body = article(HINDI + " " + MARATHI, title=TITLE).decode().encode(encoding)
    result = article_from_html(body, "https://public.test/news")
    assert HINDI in result.text and MARATHI in result.text
    assert result.extraction_details["title"] == TITLE
    assert result.extraction_details["published_at"] == "2026-10-09"


@pytest.mark.parametrize("mime", ["text/html", "text/plain"])
def test_http_charset_survives_pinned_fetch_and_route_extraction(settings, mime):
    text = "A café announced a £50 fee. Residents should read the public notice. " * 4
    body = (
        article(text).decode().encode("windows-1252")
        if mime == "text/html"
        else text.encode("windows-1252")
    )
    fetcher = SafeFetcher(
        settings,
        Resolver({}),
        httpx.MockTransport(
            lambda r: httpx.Response(
                200, headers={"Content-Type": mime + "; charset=windows-1252"}, content=body
            )
        ),
    )
    response = TestClient(create_app(settings, fetcher=fetcher)).post(
        "/api/extract/url", json={"url": "https://public.test/news"}
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert "café" in result["text"] and "£50" in result["text"]
    assert result["extraction_details"]["text_encoding"] == "cp1252"
    assert result["extraction_details"]["source_url"] == "https://public.test/news"


@pytest.mark.parametrize("mime", ["text/html", "text/plain"])
def test_unicode_page_bytes_survive_route_and_source_ledger(settings, mime, monkeypatch):
    monkeypatch.setattr("trafilatura.bare_extraction", lambda *args, **kwargs: None)
    text = HINDI + " " + MARATHI
    body = article(text, title=TITLE) if mime == "text/html" else text.encode("utf-8")
    fetcher = SafeFetcher(
        settings,
        Resolver({}),
        httpx.MockTransport(
            lambda r: httpx.Response(200, headers={"Content-Type": mime}, content=body)
        ),
    )
    llm = StubLLM([HINDI])
    hits = [SearchHit("https://rbi.org.in/offline-fixture", "Fixture", "Snippet", 0.9)]
    client = TestClient(create_app(settings, llm, StubSearch(hits), fetcher))
    extracted = client.post("/api/extract/url", json={"url": "https://public.test/news"})
    assert extracted.status_code == 200 and text in extracted.json()["text"]
    verified = client.post("/api/verify", json={"text": HINDI}).json()
    source = verified["claims"][0]["evidence"][0]
    assert HINDI in source["excerpt"] and MARATHI in source["excerpt"]
    assert source["excerpt_provenance"] == "fetched_page"


def test_undecodable_webpage_is_incomplete_and_cannot_support_decisive_verdict(settings):
    body = article(HINDI + " " + MARATHI).replace(b"</p>", b"\xff</p>")
    fetcher = SafeFetcher(
        settings,
        Resolver({}),
        httpx.MockTransport(
            lambda r: httpx.Response(
                200, headers={"Content-Type": "text/html; charset=unknown"}, content=body
            )
        ),
    )
    llm = StubLLM([HINDI])
    hits = [SearchHit("https://rbi.org.in/offline-fixture", "Fixture", "Snippet", 0.9)]
    client = TestClient(create_app(settings, llm, StubSearch(hits), fetcher))
    extracted = client.post("/api/extract/url", json={"url": "https://public.test/news"}).json()
    assert not extracted["extraction_details"]["content_complete"]
    assert any(w.startswith("text_encoding_loss") for w in extracted["warnings"])
    result = client.post("/api/verify", json={"text": HINDI}).json()
    assert result["claims"][0]["verdict"] == "unconfirmed"
    assert "source_content_incomplete" in result["warnings"]
    assert len(llm.requests) == 1
