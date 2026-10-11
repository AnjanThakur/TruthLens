import pytest
from conftest import CLAIMS, StubFetcher, StubLLM, StubSearch, article
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.search.client import SearchHit

VERDICTS = ["verified", "false", "partially_true", "outdated", "misleading_context", "unconfirmed"]


@pytest.mark.parametrize("verdict", VERDICTS)
def test_each_verdict_uses_only_retrieved_fixture_evidence(settings, verdict):
    # These are fictional, retrieved HTTP fixtures, never live institutional facts.
    urls = ["https://rbi.org.in/offline-historical", "https://pib.gov.in/offline-current"]
    dates = ["2020-01-01", "2026-01-01"] if verdict == "outdated" else []
    claim_text, source_texts = {
        "verified": (CLAIMS[0], ["The demo library opens at 9 am."] * 2),
        "false": (CLAIMS[0], ["The demo library opens at 10 am, never at 9 am."] * 2),
        "partially_true": (
            "The demo library opens at 9 am every day.",
            ["The demo library opens at 9 am on weekdays only. It stays closed at weekends."] * 2,
        ),
        "outdated": (
            CLAIMS[0],
            [
                "2020-01-01: The demo library opened at 9 am.",
                "2026-01-01: The demo library changed its opening time to 10 am. The old time no longer applies.",
            ],
        ),
        "misleading_context": (
            "The demo library has closed.",
            [
                "The demo library closed its building temporarily for repairs. Its digital services remain open, and the building reopens next week."
            ]
            * 2,
        ),
        "unconfirmed": (
            CLAIMS[0],
            ["This document discusses library books but does not establish any opening time."] * 2,
        ),
    }[verdict]
    pages = {
        url: article(text + " This is an offline fictional fixture.")
        for url, text in zip(urls, source_texts, strict=True)
    }
    stance = {"verified": "supports", "false": "contradicts"}.get(verdict, "context")
    llm = StubLLM(
        [claim_text], verdict=verdict, stances=[stance, stance], dates=dates, current=True
    )
    hits = [SearchHit(url, "Offline fixture", "Fixture snippet", 0.9) for url in urls]
    client = TestClient(create_app(settings, llm, StubSearch(hits), StubFetcher(pages)))
    result = client.post("/api/verify", json={"text": claim_text}).json()
    claim = result["claims"][0]
    assert result["status"] == "completed" and claim["verdict"] == verdict
    assert {item["url"] for item in claim["evidence"]} == set(urls)
    assessment_input = next(data for _, data in llm.requests if "evidence" in data)
    retrieved = {item["evidence_id"]: item["excerpt"] for item in assessment_input["evidence"]}
    assert all(item["excerpt"] in retrieved[item["evidence_id"]] for item in claim["evidence"])
    assert all(item["excerpt_provenance"] == "fetched_page" for item in claim["evidence"])
    mutable = {"explanation", "short_summary", "key_points", "next_step"}
    for language in ("en", "hi", "mr"):
        response = client.post("/api/explain", json={"result": result, "language": language})
        assert response.status_code == 200
        translated = response.json()["claims"][0]
        assert {k: v for k, v in translated.items() if k not in mutable} == {
            k: v for k, v in claim.items() if k not in mutable
        }


@pytest.mark.parametrize("proposed", VERDICTS)
def test_missing_sources_never_support_any_decisive_verdict(settings, proposed):
    llm = StubLLM([CLAIMS[0]], verdict=proposed)
    result = (
        TestClient(create_app(settings, llm, StubSearch([]), StubFetcher()))
        .post("/api/verify", json={"text": CLAIMS[0]})
        .json()
    )
    assert result["claims"][0]["verdict"] == "unconfirmed"
    assert result["claims"][0]["evidence"] == [] and result["status"] == "completed"
    assert "no_usable_evidence_retrieved" in result["warnings"]
    assert len(llm.requests) == 1  # no model is asked to classify absent evidence
