import asyncio
import json
import logging
from types import SimpleNamespace

import httpx
import pytest
from conftest import StubFetcher, StubLLM, StubSearch, article
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient
from pydantic import SecretStr
from test_extraction import pdf_bytes
from test_gemini_regressions import output
from test_http_security import Resolver

from app.config import Settings
from app.errors import AppError
from app.main import create_app
from app.schemas.models import ClaimBatch, ExtractionResult
from app.services.extract.url import SafeFetcher, article_from_html
from app.services.providers import GeminiLLM
from app.services.search.client import SearchHit
from scripts import validate_live

FAQ_CLAIM = "₹1 notes issued by Government of India are also Legal Tender."
PRIMARY = "https://www.rbi.org.in/Commonperson/english/Scripts/FAQs.aspx?Id=3158"
INSTAGRAM = "https://www.instagram.com/reel/DVsU6Ilkj-K?hl=en"
JAVASCRIPT = b'<html><head><title>App</title></head><body><div id="root"></div><noscript>Enable JavaScript</noscript><script src="app.js"></script></body></html>'


@pytest.mark.parametrize("failure", ["server", "invalid_json"])
def test_latest_url_workflow_fails_at_assessment_not_input_extraction(settings, caplog, failure):
    settings.gemini_api_key = SecretStr("fixture-secret")
    settings.provider_max_attempts = 1
    calls = []

    def model_handler(request):
        calls.append(request)
        if len(calls) == 1:
            return output(
                json.dumps(
                    {
                        "detected_language": "en",
                        "truncated": False,
                        "claims": [
                            {
                                "claim_text": FAQ_CLAIM,
                                "original_span": FAQ_CLAIM,
                                "entities": ["Government of India"],
                                "dates": [],
                                "qualifiers": [],
                                "queries": ["one rupee legal tender RBI"],
                                "current_assertion": True,
                            }
                        ],
                    }
                )
            )
        if failure == "server":
            return httpx.Response(
                503,
                json={
                    "error": {"message": "fixture-secret private response", "code": "unavailable"}
                },
            )
        return output('{"verdict":"invented","private":"fixture-secret"}')

    def page_handler(request):
        if request.headers["host"] == "www.instagram.com":
            return httpx.Response(200, headers={"content-type": "text/html"}, content=JAVASCRIPT)
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=article(FAQ_CLAIM + " Offline reconstruction of a currency FAQ passage. " * 8),
        )

    fetcher = SafeFetcher(settings, Resolver({}), httpx.MockTransport(page_handler))
    hits = [
        SearchHit(PRIMARY, "FAQ", FAQ_CLAIM, 0.9),
        SearchHit(INSTAGRAM, "Social result", "Snippet only", 0.8),
    ]
    app = create_app(
        settings, GeminiLLM(settings, httpx.MockTransport(model_handler)), StubSearch(hits), fetcher
    )
    client = TestClient(app)
    caplog.set_level(logging.WARNING, logger="truthlens.diagnostics")
    extracted = client.post(
        "/api/extract/url",
        json={"url": "https://www.rbi.org.in/scripts/FS_FAQs.aspx?Id=136&fn=2753"},
    )
    assert extracted.status_code == 200 and FAQ_CLAIM in extracted.json()["text"]
    assert calls == []
    response = client.post("/api/verify", json={"text": FAQ_CLAIM, "input_type": "url"})
    result = response.json()
    expected = "llm_provider_error" if failure == "server" else "llm_output_invalid"
    assert result["status"] == "partial" and result["claims"][0]["verdict"] == "unconfirmed"
    assert (
        "source_page_unavailable:url_no_text" in result["warnings"]
        and expected in result["warnings"]
    )
    assert len(calls) == 2 and '"claim":' in str(json.loads(calls[1].content)["input"])
    evidence = {e["url"]: e for e in result["claims"][0]["evidence"]}
    assert evidence[PRIMARY]["excerpt_provenance"] == "fetched_page"
    assert evidence[INSTAGRAM]["excerpt_provenance"] == "search_excerpt"
    events = [r.truthlens_event for r in caplog.records if hasattr(r, "truthlens_event")]
    error = next(e for e in events if e["stage"] == "evidence_assessment")
    assert error["category"] == (
        "transient_server" if failure == "server" else "local_schema_validation"
    )
    assert error["provider_http_status"] == (503 if failure == "server" else 200)
    assert error["request_id"] == response.headers["x-request-id"]
    assert "fixture-secret" not in caplog.text and "private response" not in caplog.text


def test_semantic_article_fallback_preserves_dates_and_ignores_navigation(monkeypatch):
    monkeypatch.setattr("trafilatura.bare_extraction", lambda *a, **k: None)
    html = (
        article("Useful offline article content. " * 10, date="2025-01-01")
        .replace(b"</head>", b'<meta property="article:modified_time" content="2026-01-01"></head>')
        .replace(b"<body>", b"<body><nav>Unrelated menu links</nav><script>ignore()</script>")
    )
    result = article_from_html(html, "https://public.test/article")
    assert "Useful offline article" in result.text and "Unrelated menu" not in result.text
    assert result.extraction_details["article_extraction"] == "semantic_html_fallback"
    assert result.extraction_details["published_at"] == "2025-01-01"
    assert result.extraction_details["updated_at"] == "2026-01-01"
    assert result.extraction_details["url"] == "https://public.test/article"


def test_layout_table_noise_removed_without_losing_content(monkeypatch):
    monkeypatch.setattr(
        "trafilatura.bare_extraction",
        lambda *a, **k: SimpleNamespace(
            text="| | |\nIndian Currency\n| |\n" + FAQ_CLAIM,
            language="en",
            title="FAQ",
            sitename=None,
            author=None,
        ),
    )
    result = article_from_html(article(FAQ_CLAIM), "https://public.test/article")
    assert "|" not in result.text and FAQ_CLAIM in result.text


def test_javascript_shell_is_distinct_and_does_not_fabricate_article(caplog):
    caplog.set_level(logging.WARNING, logger="truthlens.diagnostics")
    with pytest.raises(AppError) as error:
        article_from_html(JAVASCRIPT, INSTAGRAM)
    assert error.value.code == "url_no_text" and error.value.category == "javascript_required"
    assert "requires JavaScript" in error.value.message


def test_third_party_article_warnings_do_not_log_source_url_query(caplog):
    caplog.set_level(logging.WARNING)
    with pytest.raises(AppError):
        article_from_html(JAVASCRIPT, "https://public.test/app?token=fixture-secret")
    assert "fixture-secret" not in caplog.text and "token=" not in caplog.text


def test_public_redirect_preserves_final_original_urls_and_dates(settings):
    seen = []

    def handler(request):
        seen.append(request)
        if len(seen) == 1:
            return httpx.Response(302, headers={"location": "https://publisher.test/article"})
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            content=article("An actual offline article body. " * 12, date="2025-04-15"),
        )

    resolver = Resolver({"publisher.test": ["8.8.8.8"]})
    fetcher = SafeFetcher(settings, resolver, httpx.MockTransport(handler))
    result = (
        TestClient(create_app(settings, fetcher=fetcher))
        .post("/api/extract/url", json={"url": "https://public.test/original"})
        .json()
    )
    assert result["extraction_details"]["source_url"] == "https://public.test/original"
    assert result["extraction_details"]["url"] == "https://publisher.test/article"
    assert result["extraction_details"]["published_at"] == "2025-04-15"
    assert resolver.calls == ["public.test", "publisher.test"]
    assert [request.url.host for request in seen] == ["93.184.216.34", "8.8.8.8"]
    assert seen[1].headers["host"] == seen[1].extensions["sni_hostname"] == "publisher.test"


@pytest.mark.parametrize(
    "content_type", ["application/pdf", "application/octet-stream", "text/html"]
)
def test_supported_pdf_url_uses_pdf_parser_without_llm(settings, content_type):
    llm = StubLLM()
    fetcher = SafeFetcher(
        settings,
        Resolver({}),
        httpx.MockTransport(
            lambda r: httpx.Response(
                200, headers={"content-type": content_type}, content=pdf_bytes()
            )
        ),
    )
    response = TestClient(create_app(settings, llm=llm, fetcher=fetcher)).post(
        "/api/extract/url", json={"url": "https://public.test/circular.pdf"}
    )
    assert response.status_code == 200
    result = response.json()
    assert "library opens" in result["text"] and result["input_type"] == "url"
    assert result["extraction_details"]["document_type"] == "pdf"
    assert result["extraction_details"]["source_url"] == result["extraction_details"]["url"]
    assert llm.requests == []


async def test_non_pdf_binary_not_accepted(settings):
    fetcher = SafeFetcher(
        settings,
        Resolver({}),
        httpx.MockTransport(
            lambda r: httpx.Response(
                200, headers={"content-type": "application/octet-stream"}, content=b"not a pdf"
            )
        ),
    )
    with pytest.raises(AppError) as error:
        await fetcher.fetch("https://public.test/file")
    assert error.value.code == "url_content_unsupported"


@pytest.mark.parametrize("failure", ["verification_error", "non_json_response"])
async def test_url_failure_does_not_prevent_independent_audio_result(
    monkeypatch, tmp_path, failure
):
    voice = tmp_path / "fixture.wav"
    voice.write_bytes(b"offline fixture supplied to test-only media extractor")
    monkeypatch.setitem(validate_live.INPUTS, "audio", str(voice))
    monkeypatch.setattr(
        validate_live,
        "Settings",
        lambda **kwargs: Settings(_env_file=None, gemini_api_key="", tavily_api_key="", **kwargs),
    )
    voice_claim = "The demo library opens at 9 am."

    class LLM(StubLLM):
        async def structured(self, task, data, model):
            if model is ClaimBatch and data["text"] == FAQ_CLAIM:
                raise AppError("llm_provider_error", "Offline server-error fixture.", 502)
            return await super().structured(task, data, model)

    class Media:
        async def extract(self, data):
            assert data == voice.read_bytes()
            return ExtractionResult(text=voice_claim, detected_language="en", input_type="audio")

    def make_app(settings, **kwargs):
        app = create_app(
            settings,
            LLM([voice_claim]),
            StubSearch(),
            StubFetcher(
                {"https://www.rbi.org.in/scripts/FS_FAQs.aspx?Id=136&fn=2753": article(FAQ_CLAIM)}
            ),
            media=Media(),
        )
        if failure == "non_json_response":

            @app.middleware("http")
            async def malformed_response(request, call_next):
                if request.url.path == "/api/extract/url":
                    return HTMLResponse("fixture-secret upstream HTML", status_code=502)
                return await call_next(request)

        return app

    monkeypatch.setattr(validate_live, "create_app", make_app)
    target = tmp_path / "offline-acceptance.json"
    assert await validate_live.run(["url", "audio"], ["en"], output=target) == 1
    report = json.loads(target.read_text(encoding="utf-8"))
    assert list(report["formats"]) == ["url", "audio"]
    assert report["formats"]["url"]["status"] == "FAIL"
    assert report["formats"]["audio"]["status"] == "PASS"
    assert report["formats"]["audio"]["extraction"]["text"] == voice_claim
    assert report["formats"]["url"]["reason"] == (
        "llm_provider_error" if failure == "verification_error" else "runner_input_error"
    )
    assert "fixture-secret" not in target.read_text(encoding="utf-8")
    assert not report["gemini_http_requests"] and not report["tavily_http_requests"]


def test_readable_primary_source_survives_unreadable_social_page(settings):
    def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=JAVASCRIPT
            if request.headers["host"] == "www.instagram.com"
            else article(FAQ_CLAIM + " Offline reconstructed FAQ context. " * 10),
        )

    fetcher = SafeFetcher(settings, Resolver({}), httpx.MockTransport(handler))
    hits = [
        SearchHit(PRIMARY, "FAQ", FAQ_CLAIM, 0.9),
        SearchHit(INSTAGRAM, "Social", "Snippet only", 0.8),
    ]
    llm = StubLLM([FAQ_CLAIM], stances=["supports", "unclear"])
    result = (
        TestClient(create_app(settings, llm, StubSearch(hits), fetcher))
        .post("/api/verify", json={"text": FAQ_CLAIM, "input_type": "url"})
        .json()
    )
    claim = result["claims"][0]
    assert result["status"] == "completed" and claim["verdict"] == "verified"
    assert "source_page_unavailable:url_no_text" in result["warnings"]
    assert claim["evidence"][0]["url"] == PRIMARY and FAQ_CLAIM in claim["evidence"][0]["excerpt"]
    assert claim["evidence"][1]["url"] == INSTAGRAM and claim["evidence"][1]["stance"] == "unclear"


async def test_runner_records_all_selected_inputs_before_interruption(monkeypatch, tmp_path):
    monkeypatch.setattr(
        validate_live,
        "Settings",
        lambda **kwargs: Settings(_env_file=None, gemini_api_key="", tavily_api_key="", **kwargs),
    )
    target = tmp_path / "interrupted.json"

    class InterruptedClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            saved = json.loads(target.read_text(encoding="utf-8"))
            assert list(saved["formats"]) == ["url", "audio"]
            raise asyncio.CancelledError

    monkeypatch.setattr(validate_live.httpx, "AsyncClient", lambda **kwargs: InterruptedClient())
    handlers = list(validate_live.diagnostic_logger.handlers)
    with pytest.raises(asyncio.CancelledError):
        await validate_live.run(["url", "audio"], ["en"], output=target)
    report = json.loads(target.read_text(encoding="utf-8"))
    assert all(row["status"] == "SKIPPED" for row in report["formats"].values())
    assert report["formats"]["audio"]["reason"] == "Not attempted"
    assert list(validate_live.diagnostic_logger.handlers) == handlers
