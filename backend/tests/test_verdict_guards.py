from conftest import CLAIMS, StubFetcher, StubLLM, StubSearch, article
from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.models import Decision
from app.services.search.client import SearchHit


def test_rejected_date_does_not_mutate_source_stances(settings):
    llm = StubLLM([CLAIMS[0]], dates=["1900-01-01"])
    client = TestClient(create_app(settings, llm, StubSearch(), StubFetcher()))
    result = client.post("/api/verify", json={"text": CLAIMS[0]}).json()
    assert "evidence_date_invalid" in result["warnings"]
    assert result["claims"][0]["verdict"] == "unconfirmed"
    assert all(e["stance"] == "unclear" for e in result["claims"][0]["evidence"])


def test_irrelevant_reviewed_source_cannot_prove_claim(settings):
    class Irrelevant(StubLLM):
        async def structured(self, task, data, model):
            output = await super().structured(task, data, model)
            if model is Decision:
                for assessment in output.assessments:
                    assessment.directly_relevant = False
            return output

    client = TestClient(create_app(settings, Irrelevant([CLAIMS[0]]), StubSearch(), StubFetcher()))
    claim = client.post("/api/verify", json={"text": CLAIMS[0]}).json()["claims"][0]
    assert claim["verdict"] == "unconfirmed"
    assert claim["evidence"][0]["directly_relevant"] is False


def test_publication_dates_alone_do_not_establish_outdated(settings):
    class NoEventDates(StubLLM):
        async def structured(self, task, data, model):
            output = await super().structured(task, data, model)
            if model is Decision:
                output.temporal_witnesses = []
            return output

    text = "The demo scheme is open now."
    hits = [
        SearchHit("https://pib.gov.in/fixture-old", "Old", "old", 0.9),
        SearchHit("https://pib.gov.in/fixture-current", "Current", "current", 0.9),
    ]
    dates = ["2020-01-01", "2026-01-01"]
    pages = {
        h.url: article(
            "The scheme information is discussed in this offline fixture. Publication metadata alone does not establish whether applications are open.",
            date=d,
        )
        for h, d in zip(hits, dates, strict=True)
    }
    llm = NoEventDates([text], "outdated", ["context", "context"], dates, current=True)
    client = TestClient(create_app(settings, llm, StubSearch(hits), StubFetcher(pages)))
    assert (
        client.post("/api/verify", json={"text": text}).json()["claims"][0]["verdict"]
        == "unconfirmed"
    )


def test_unreviewed_domain_cannot_definitively_verify(settings):
    hits = [SearchHit("https://official-looking.test/fixture", "Claimed authority", "fixture", 0.9)]
    client = TestClient(create_app(settings, StubLLM([CLAIMS[0]]), StubSearch(hits), StubFetcher()))
    claim = client.post("/api/verify", json={"text": CLAIMS[0]}).json()["claims"][0]
    assert claim["verdict"] == "unconfirmed"
    assert claim["evidence"][0]["source_type"] == "other"
