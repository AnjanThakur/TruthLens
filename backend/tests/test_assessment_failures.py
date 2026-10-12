"""Three fictional fetched pages exercise the actual Gemini SDK with no live network."""

import asyncio
import json
from datetime import UTC, datetime

import httpx
import pytest
from conftest import StubFetcher, StubSearch
from fastapi.testclient import TestClient
from pydantic import SecretStr
from test_gemini_regressions import output

from app.errors import AppError
from app.main import create_app
from app.schemas.models import Evidence
from app.services.providers import GeminiLLM
from scripts.validate_assessment import CapturingGemini
from scripts.validate_live import BudgetedSearch


def test_selective_assessment_acceptance_caps_actual_attempts(settings):
    model = CapturingGemini(settings)
    model.reserve_request()
    with pytest.raises(AppError, match="budget"):
        model.reserve_request()
    assert model.request_count == 1
    search = BudgetedSearch(settings)
    search.budget = 2
    search.reserve_request()
    search.reserve_request()
    with pytest.raises(AppError, match="budget"):
        search.reserve_request()
    assert search.request_count == 2


@pytest.fixture(autouse=True)
def no_live_network(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("Live provider call forbidden in assessment regression")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", fail)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", fail)


@pytest.mark.parametrize(
    "mode,code",
    [
        ("success", None),
        ("recovery", None),
        ("json", "llm_output_invalid"),
        ("schema", "llm_output_invalid"),
        ("timeout", "llm_timeout"),
        ("deadline", "llm_timeout"),
        ("server", "llm_provider_error"),
        ("quota", "llm_quota_exhausted"),
        ("unknown_id", "evidence_reference_invalid"),
    ],
)
def test_fetched_evidence_reaches_gemini_and_failures_preserve_it(settings, caplog, mode, code):
    settings.gemini_api_key = SecretStr("private-fixture-key")
    settings.provider_max_attempts = 2 if mode == "recovery" else 1
    if mode == "deadline":
        settings.llm_timeout_seconds = 1
    evidence = [
        Evidence(
            title="Fictional fixture only",
            url=f"https://example.org/{i}",
            publisher=publisher,
            source_type="secondary",
            published_at=f"2026-10-0{i + 1}",
            updated_at=f"2026-10-0{i + 2}",
            retrieved_at=datetime.now(UTC),
            excerpt=f"FICTIONAL TEST ONLY: Avery Example died. The hospital confirmed this to reporter {i}.",
            excerpt_provenance="fetched_page",
            authority_basis="Offline reviewed fixture",
        )
        for i, publisher in enumerate(["Associated Press", "The Hindu", "The Times of India"])
    ]

    class FixtureLedger:
        async def retrieve(self, *args):
            return [e.model_copy(deep=True) for e in evidence], []

    calls = []

    async def handler(request):
        wire = json.loads(request.content)
        bundle = json.loads(wire["input"][0]["content"][0]["text"])
        calls.append(bundle)
        schema = wire["response_format"]["schema"]
        assert "what_source_says" not in schema["properties"]["assessments"]["items"]["properties"]
        for original, sent in zip(evidence, bundle["evidence"], strict=True):
            for key in ("excerpt", "published_at", "updated_at", "excerpt_provenance"):
                assert sent[key] == getattr(original, key)
            assert sent["evidence_id"] == str(original.evidence_id)
            assert sent["content_complete"] and sent["subject_match"]
            assert "stance" not in sent and "directly_relevant" not in sent
        if mode == "deadline":
            await asyncio.sleep(2)
        if mode == "timeout":
            raise httpx.ReadTimeout("private-fixture-key private-body", request=request)
        if mode == "server" or mode == "recovery" and len(calls) == 1:
            return httpx.Response(
                503, json={"error": {"message": "private-body", "code": "unavailable"}}
            )
        if mode == "quota":
            return httpx.Response(
                429,
                json={"error": {"message": "Daily quota exhausted", "code": "RESOURCE_EXHAUSTED"}},
            )
        decision = {
            "verdict": "verified",
            "explanation": "The fictional retrieved reports support the fictional claim.",
            "short_summary": "Fixture",
            "key_points": [],
            "assessments": [
                {
                    "evidence_id": str(e.evidence_id),
                    "stance": "supports",
                    "excerpt": e.excerpt,
                    "directly_relevant": True,
                }
                for e in evidence
            ],
            "decisive_evidence_ids": [str(e.evidence_id) for e in evidence],
            "limitations": [],
            "temporal_notes": "",
            "relevant_source_dates": [e.published_at for e in evidence],
            "context_evidence_ids": [],
            "temporal_witnesses": [],
            "component_assessments": [],
        }
        if mode == "unknown_id":
            decision["decisive_evidence_ids"] = ["invented-id"]
        if mode == "schema":
            decision.pop("verdict")
        return output("not JSON private-body" if mode == "json" else json.dumps(decision))

    llm = GeminiLLM(settings, httpx.MockTransport(handler))
    app = create_app(settings, llm, StubSearch(), StubFetcher())
    app.state.verifier.ledger = FixtureLedger()
    with TestClient(app) as client:
        response = client.post("/api/verify", json={"text": "Avery Example died"})
    result = response.json()
    claim = result["claims"][0]
    assert response.status_code == 200
    assert len(calls) == llm.request_count == (2 if mode == "recovery" else 1)
    assert [e["excerpt"] for e in claim["evidence"]] == [e.excerpt for e in evidence]
    if code:
        assert result["status"] == "partial" and claim["verdict"] == "unconfirmed"
        assert code in result["warnings"]
        assert "AI assessment failed" in claim["explanation"]
        assert "No usable source evidence" not in claim["explanation"]
        assert all(not e["what_source_says"] for e in claim["evidence"])
    else:
        assert result["status"] == "completed" and claim["verdict"] == "verified"
        assert all(e["what_source_says"] == e["excerpt"] for e in claim["evidence"])
    events = [r.truthlens_event for r in caplog.records if hasattr(r, "truthlens_event")]
    prepared = next(e for e in events if e["code"] == "assessment_payload_ready")
    assert prepared["eligible_count"] == prepared["evidence_count"] == 3
    request = next(e for e in events if e["code"] == "llm_request_started")
    assert request["input_chars"] > 0 and request["schema_chars"] > 0
    assert request["timestamp"] and request["timeout_seconds"] == settings.llm_timeout_seconds
    if mode in {"timeout", "deadline"}:
        failure = next(e for e in events if e["code"] == code and "elapsed_ms" in e)
        assert failure["category"] == ("deadline" if mode == "deadline" else "transport_timeout")
    for forbidden in ("private-body", "private-fixture-key", "Avery Example", "example.org"):
        assert forbidden not in caplog.text
