import json

import httpx
import pytest
from conftest import CLAIMS, StubFetcher, StubLLM, StubSearch, article
from fastapi.testclient import TestClient
from pydantic import SecretStr
from test_audio_unicode_repairs import wav_bytes
from test_gemini_regressions import output

from app.config import Settings
from app.errors import AppError
from app.main import create_app
from app.schemas.models import ClaimBatch, Decision, Wording
from app.services.claims.parser import extract_claims
from app.services.providers import GeminiLLM
from app.services.search.client import SearchHit
from scripts import validate_live


@pytest.mark.parametrize("provider_type", ["gemini", "tavily"])
async def test_budget_counts_failed_attempts_and_blocks_retry_before_http(
    settings, monkeypatch, provider_type
):
    settings.gemini_api_key = settings.tavily_api_key = SecretStr("fixture-only")
    settings.provider_max_attempts = 3
    calls = []

    async def sleep(seconds):
        pass

    monkeypatch.setattr("app.services.providers.asyncio.sleep", sleep)

    def handler(request):
        calls.append(request)
        return httpx.Response(
            503, json={"error": {"message": "unavailable", "code": "unavailable"}}
        )

    provider = (
        validate_live.BudgetedGemini if provider_type == "gemini" else validate_live.BudgetedSearch
    )(settings, httpx.MockTransport(handler))
    provider.budget = 1
    with pytest.raises(AppError) as error:
        if provider_type == "gemini":
            await provider.structured("Extract", {}, ClaimBatch)
        else:
            await provider.search("fixture")
    assert error.value.code == (
        "llm_live_budget_exhausted" if provider_type == "gemini" else "search_budget_exhausted"
    )
    assert provider.request_count == len(calls) == 1


@pytest.mark.parametrize("weakness", ["unreviewed", "irrelevant", "snippet", "incomplete"])
def test_weak_opposing_source_cannot_erase_strong_direct_support(settings, weakness):
    class WeakOpposition(StubLLM):
        async def structured(self, task, data, model):
            decision = await super().structured(task, data, model)
            if model is Decision:
                for item, assessment in zip(data["evidence"], decision.assessments, strict=True):
                    if "weak-fixture" in item["url"]:
                        assessment.stance = "contradicts"
                        assessment.directly_relevant = weakness != "irrelevant"
            return decision

    class Pages(StubFetcher):
        async def fetch(self, url):
            if "weak-fixture" in url and weakness == "snippet":
                raise AppError("url_fetch_error", "Offline fixture", 502)
            result = await super().fetch(url)
            if "weak-fixture" in url and weakness == "incomplete":
                result.body += b'<script type="application/ld+json">{"@type":"Article","isAccessibleForFree":false}</script>'
            return result

    weak = (
        "https://unreviewed.test/weak-fixture"
        if weakness == "unreviewed"
        else "https://reuters.com/weak-fixture"
    )
    hits = [
        SearchHit("https://rbi.org.in/strong-fixture", "Offline support", "Fixture", 0.9),
        SearchHit(weak, "Offline weak opposition", "Fixture", 0.8),
    ]
    result = (
        TestClient(create_app(settings, WeakOpposition([CLAIMS[0]]), StubSearch(hits), Pages()))
        .post("/api/verify", json={"text": CLAIMS[0]})
        .json()
    )
    assert result["claims"][0]["verdict"] == "verified"
    assert {e["stance"] for e in result["claims"][0]["evidence"]} == {"supports", "contradicts"}


@pytest.mark.parametrize(
    "problem", ["missing", "overlap", "invented_span", "invented_source", "unsupported"]
)
def test_partially_true_requires_distinct_grounded_components(settings, problem):
    text = "The demo library opens at 9 am every day."

    class BadComponents(StubLLM):
        async def structured(self, task, data, model):
            decision = await super().structured(task, data, model)
            if model is Decision:
                if problem == "missing":
                    decision.component_assessments = []
                elif problem == "overlap":
                    decision.component_assessments[1].original_span = "9 am"
                elif problem == "invented_span":
                    decision.component_assessments[0].original_span = "every night"
                elif problem == "invented_source":
                    decision.component_assessments[0].evidence_ids = ["invented"]
                else:
                    decision.component_assessments[0].evidence_ids = []
            return decision

    client = TestClient(
        create_app(
            settings,
            BadComponents([text], verdict="partially_true", stances=["context"]),
            StubSearch(),
            StubFetcher(),
        )
    )
    result = client.post("/api/verify", json={"text": text}).json()
    assert result["claims"][0]["verdict"] == "unconfirmed"
    if problem.startswith("invented"):
        assert result["status"] == "partial" and "evidence_reference_invalid" in result["warnings"]


def test_mixed_components_are_not_mistaken_for_whole_claim_conflict(settings):
    text = "The demo library opens at 9 am every day."
    hits = [
        SearchHit("https://rbi.org.in/fixture-support", "Offline support", "Fixture", 0.9),
        SearchHit(
            "https://reuters.com/fixture-qualification", "Offline qualification", "Fixture", 0.9
        ),
    ]
    client = TestClient(
        create_app(
            settings,
            StubLLM([text], "partially_true", ["supports", "contradicts"]),
            StubSearch(hits),
            StubFetcher(),
        )
    )
    result = client.post("/api/verify", json={"text": text}).json()
    assert result["status"] == "completed" and result["claims"][0]["verdict"] == "partially_true"


def test_misleading_context_requires_actual_context_stance(settings):
    client = TestClient(
        create_app(
            settings,
            StubLLM([CLAIMS[0]], verdict="misleading_context", stances=["supports"]),
            StubSearch(),
            StubFetcher(),
        )
    )
    claim = client.post("/api/verify", json={"text": CLAIMS[0]}).json()["claims"][0]
    assert claim["verdict"] == "unconfirmed"


@pytest.mark.parametrize(
    "language,text",
    [
        ("en", CLAIMS[0]),
        ("hi", "पुस्तकालय सुबह नौ बजे खुलता है।"),
        ("mr", "वाचनालय सकाळी नऊ वाजता उघडते."),
    ],
)
def test_complete_audio_pipeline_with_actual_adapters_and_mocked_cloud(settings, language, text):
    settings.gemini_api_key = SecretStr("fixture-only")
    stub = StubLLM([text])
    stages = []

    async def handler(request):
        payload = json.loads(request.content)
        content = payload["input"][0]["content"][0]
        if content["type"] == "audio":
            stages.append("audio")
            return output(json.dumps({"text": text, "detected_language": language}))
        data = json.loads(content["text"])
        model = (
            Decision
            if "evidence" in data and "claim" in data
            else Wording
            if "verdict" in data
            else ClaimBatch
        )
        stages.append(model.__name__)
        return output((await stub.structured("fixture", data, model)).model_dump_json())

    provider = GeminiLLM(settings, httpx.MockTransport(handler))
    page = article(text + " This is an attributed offline fixture.")
    fetcher = StubFetcher({"https://rbi.org.in/fixture-announcement": page})
    client = TestClient(create_app(settings, provider, StubSearch(), fetcher))
    extraction = client.post(
        "/api/extract", files={"file": ("voice.wav", wav_bytes(), "audio/wav")}
    )
    assert extraction.status_code == 200 and extraction.json()["text"] == text
    result = client.post(
        "/api/verify", json={"text": text, "input_type": "audio", "response_language": language}
    ).json()
    assert result["status"] == "completed" and result["claims"][0]["verdict"] == "verified"
    assert result["claims"][0]["original_span"] == text
    assert stages == ["audio", "ClaimBatch", "Decision"] + ([] if language == "en" else ["Wording"])


@pytest.mark.parametrize("failure", ["search", "assessment"])
def test_cloud_failure_has_explicit_technical_warning_not_completed_uncertainty(settings, failure):
    llm = StubLLM([CLAIMS[0]])
    llm.fail_assessment = failure == "assessment"
    response = TestClient(
        create_app(settings, llm, StubSearch(fail=failure == "search"), StubFetcher())
    ).post("/api/verify", json={"text": CLAIMS[0]})
    result = response.json()
    assert result["status"] == "partial" and result["claims"][0]["verdict"] == "unconfirmed"
    assert ("search_provider_error" if failure == "search" else "llm_provider_error") in result[
        "warnings"
    ]


def test_empty_grounded_model_explanation_is_explicit_failure(settings):
    settings.gemini_api_key = SecretStr("fixture-only")
    stub = StubLLM([CLAIMS[0]])

    async def handler(request):
        content = json.loads(request.content)["input"][0]["content"][0]
        data = json.loads(content["text"])
        model = Decision if "evidence" in data else ClaimBatch
        result = (await stub.structured("fixture", data, model)).model_dump()
        if model is Decision:
            result["explanation"] = ""
        return output(json.dumps(result))

    provider = GeminiLLM(settings, httpx.MockTransport(handler))
    response = TestClient(create_app(settings, provider, StubSearch(), StubFetcher())).post(
        "/api/verify", json={"text": CLAIMS[0]}
    )
    result = response.json()
    assert response.status_code == 200 and result["status"] == "partial"
    assert result["claims"][0]["verdict"] == "unconfirmed"
    assert "llm_output_invalid" in result["warnings"] and provider.request_count == 2


async def test_currency_query_targets_rbi_not_restaurant_brand(settings):
    text = "One rupee notes are issued by the Government of India."
    batch = await extract_claims(
        StubLLM([text]), text, "en", "IN", settings, "2026-10-11T00:00:00Z"
    )
    assert batch.claims[0].queries[0].startswith("site:rbi.org.in ")
    unrelated = await extract_claims(
        StubLLM([CLAIMS[0]]), CLAIMS[0], "en", "IN", settings, "2026-10-11T00:00:00Z"
    )
    assert unrelated.claims[0].queries == [CLAIMS[0]]


@pytest.mark.parametrize("budgets", [(6, 2), (5, 3)])
async def test_final_live_mode_rejects_overbudget_before_settings_or_calls(budgets):
    with pytest.raises(ValueError, match="maximum"):
        await validate_live.run(
            ["audio", "text"],
            ["en"],
            model_budget=budgets[0],
            search_budget=budgets[1],
            final_pass=True,
        )


async def test_final_mode_stops_after_audio_503_and_records_remaining_text_skipped(
    monkeypatch, tmp_path
):
    original = validate_live.BudgetedGemini
    monkeypatch.setattr(
        validate_live,
        "Settings",
        lambda **kwargs: Settings(
            _env_file=None, gemini_api_key="fixture-only", tavily_api_key="fixture-only", **kwargs
        ),
    )
    monkeypatch.setattr(
        validate_live,
        "BudgetedGemini",
        lambda settings: original(
            settings,
            httpx.MockTransport(
                lambda r: httpx.Response(
                    503, json={"error": {"message": "unavailable", "code": "unavailable"}}
                )
            ),
        ),
    )
    audio = tmp_path / "fixture.wav"
    audio.write_bytes(wav_bytes())
    target = tmp_path / "mock-final.json"
    assert (
        await validate_live.run(
            ["audio", "text"], ["en"], target, 5, 2, final_pass=True, audio_file=audio
        )
        == 1
    )
    report = json.loads(target.read_text())
    assert report["gemini_http_requests"] == 1 and report["tavily_http_requests"] == 0
    assert report["formats"]["audio"]["status"] == "FAIL"
    assert report["formats"]["text"]["status"] == "SKIPPED"
