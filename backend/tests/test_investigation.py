from datetime import UTC, datetime

import httpx
import pytest
from conftest import CLAIMS, StubFetcher, StubLLM, StubSearch, article
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.errors import AppError
from app.main import create_app
from app.schemas.models import AtomicClaim
from app.services.claims.dates import quoted_dates, relative_dates
from app.services.providers import ModelBudget
from app.services.search.client import CURRENT_SEARCH_BUDGET, SearchBudget, SearchHit, TavilySearch
from app.services.search.investigation import authority_for, investigation_plan
from app.services.search.ledger import Ledger, identity


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Investigation regressions cannot use live HTTP.")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)


def claim(text=CLAIMS[0]):
    return AtomicClaim(
        claim_text=text,
        original_span=text,
        entities=["demo library"],
        dates=[],
        qualifiers=[],
        queries=[text],
        current_assertion=True,
    )


@pytest.mark.parametrize(
    "text,domain",
    [
        ("A ticket costs ₹500.", None),
        ("₹500 banknotes become invalid next Monday.", "rbi.org.in"),
        ("आधार आज बंद है।", "uidai.gov.in"),
        ("निवडणूक सोमवारी आहे.", "eci.gov.in"),
        ("Supreme Court announces a ruling.", "sci.gov.in"),
    ],
)
def test_relevant_authority_not_any_money(text, domain):
    assert authority_for(text) == domain
    assert authority_for(text, "US") is None


def test_registry_never_trusts_lookalikes():
    assert identity("https://eci.gov.in/announcement")[1] == "primary"
    assert identity("https://eci.gov.in.evil.example/announcement")[1] == "other"
    assert identity("https://unreviewed.gov.in/announcement")[1] == "other"


def test_plan_has_explicit_contradiction_and_bounded_pdf_fallback():
    stages = investigation_plan(claim("All ₹500 banknotes become invalid next Monday."))
    assert [s.name for s in stages] == ["primary", "corroboration", "contradiction", "fallback"]
    assert stages[0].query.startswith("site:rbi.org.in")
    assert "false claim" in stages[2].query and "PDF" in stages[3].query
    assert len({s.query for s in stages}) == 4 and all(len(s.query) <= 400 for s in stages)


async def test_official_below_score_threshold_still_ranks_first(settings):
    settings.max_evidence = 1
    sources, _ = await Ledger(
        settings,
        StubSearch(
            [
                SearchHit("https://unreviewed.example/a", "Other", "Snippet", 0.99),
                SearchHit("https://rbi.org.in/a", "Official", "Snippet", 0.49),
            ]
        ),
        StubFetcher(),
    ).retrieve(claim())
    assert sources[0].source_type == "primary"


async def test_alternate_queries_recover_and_preserve_counterevidence(settings):
    class Search:
        def __init__(self):
            self.calls = []

        async def search(self, query):
            self.calls.append(query)
            if len(self.calls) == 1:
                return []
            url = (
                "https://reuters.com/support"
                if len(self.calls) == 2
                else "https://rbi.org.in/clarification"
            )
            return [SearchHit(url, "Fixture", "snippet", 0.4)]

    search = Search()
    sources, _ = await Ledger(settings, search, StubFetcher()).retrieve(claim())
    assert len(search.calls) == 3
    assert {e.url for e in sources} == {
        "https://reuters.com/support",
        "https://rbi.org.in/clarification",
    }
    assert any("investigation_stage=contradiction" in e.authority_basis for e in sources)


async def test_identical_syndicated_passages_are_marked_not_removed(settings):
    hits = [
        SearchHit("https://rbi.org.in/a", "A", "x"),
        SearchHit("https://reuters.com/b", "B", "x"),
    ]
    sources, _ = await Ledger(settings, StubSearch(hits), StubFetcher()).retrieve(claim())
    assert len(sources) == 2
    assert sum("duplicated_passage:" in e.authority_basis for e in sources) == 1


async def test_successful_page_cache_isolated_from_claim_assessment(settings):
    class Fetcher(StubFetcher):
        calls = 0

        async def fetch(self, url):
            self.calls += 1
            return await super().fetch(url)

    fetcher = Fetcher()
    ledger = Ledger(settings, StubSearch(), fetcher)
    first, _ = await ledger.retrieve(claim())
    first[0].excerpt = "mutated"
    second, _ = await ledger.retrieve(claim(CLAIMS[1]))
    assert fetcher.calls == 1 and second[0].excerpt != "mutated"
    assert second[0].stance == "unclear"
    assert second[0].retrieved_at == first[0].retrieved_at


@pytest.mark.parametrize("status", [402, 432, 433, 429])
async def test_provider_limit_blocks_repeated_queries_without_http(settings, status):
    settings.tavily_api_key = SecretStr("fixture-not-a-key")
    calls = []
    transport = httpx.MockTransport(
        lambda request: (
            calls.append(request) or httpx.Response(status, headers={"retry-after": "120"})
        )
    )
    search = TavilySearch(settings, transport)
    for query in ("first", "alternate", "another claim"):
        with pytest.raises(AppError) as caught:
            await search.search(query)
        assert caught.value.code == (
            "search_rate_limited" if status == 429 else "search_quota_exhausted"
        )
    assert len(calls) == search.request_count == 1


async def test_budget_counts_actual_retries_and_cache_hits_cost_zero(settings):
    settings.tavily_api_key = SecretStr("fixture-not-a-key")
    search = TavilySearch(
        settings, httpx.MockTransport(lambda request: httpx.Response(200, json={"results": []}))
    )
    token = CURRENT_SEARCH_BUDGET.set(SearchBudget(1))
    try:
        await search.search("same")
        await search.search("same")
        with pytest.raises(AppError, match="bounded search"):
            await search.search("different")
        assert search.request_count == 1
    finally:
        CURRENT_SEARCH_BUDGET.reset(token)
    budget = ModelBudget(1)
    budget.reserve()
    with pytest.raises(AppError) as caught:
        budget.reserve()
    assert caught.value.code == "llm_budget_exhausted"


@pytest.mark.parametrize(
    "text,dates",
    [
        ("next Monday", ["2026-10-12"]),
        ("अगले सोमवार", ["2026-10-12"]),
        ("पुढील सोमवार", ["2026-10-12"]),
        ("today", ["2026-10-11"]),
        ("उद्या", ["2026-10-12"]),
        ("कल", []),
    ],
)
def test_relative_dates_use_original_timestamp_and_ist_midnight(text, dates):
    assert relative_dates(text, datetime(2026, 10, 10, 20, tzinfo=UTC), "IN") == dates


def test_natural_event_dates_traceable_no_numeric_ambiguity():
    assert quoted_dates("Effective 1 October 2026; replaced October 10, 2026.") == {
        "2026-10-01",
        "2026-10-10",
    }
    assert quoted_dates("01/10/26; October 2026; 31 February 2026.") == set()
    assert relative_dates("आजादी", datetime(2026, 10, 10, tzinfo=UTC), "IN") == []


def test_relative_date_cache_invalidates_at_indian_midnight(settings, monkeypatch):
    instant = [datetime(2026, 10, 10, 18, 29, 59, tzinfo=UTC)]
    monkeypatch.setattr("app.services.verify.engine.now", lambda: instant[0])
    text = "The demo library opens at 9 am today."
    client = TestClient(create_app(settings, StubLLM([text]), StubSearch(), StubFetcher()))
    first = client.post("/api/verify", json={"text": text}).json()
    instant[0] = datetime(2026, 10, 10, 18, 30, 1, tzinfo=UTC)
    second = client.post("/api/verify", json={"text": text}).json()
    assert first["verification_id"] != second["verification_id"]
    assert first["claims"][0]["dates"] == ["2026-10-10"]
    assert second["claims"][0]["dates"] == ["2026-10-11"]


async def test_invalid_search_dates_do_not_break_frontend_schema(settings):
    settings.tavily_api_key = SecretStr("fixture-not-a-key")
    search = TavilySearch(
        settings,
        httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "url": "https://rbi.org.in/fixture",
                            "content": "snippet",
                            "published_date": "not a date",
                        },
                        {
                            "url": "https://rbi.org.in/other",
                            "content": "snippet",
                            "published_date": "Tue, 11 Mar 2025 17:00:00 GMT",
                        },
                    ]
                },
            )
        ),
    )
    results = await search.search("dates")
    assert results[0].published_at is None and "search_date_invalid_discarded" in results.warnings
    assert results[1].published_at == "2025-03-11T17:00:00+00:00"


def test_message_timestamp_header_preserves_contract_and_cache_context(settings):
    text = "All banknotes become invalid next Monday."
    llm = StubLLM([text])
    client = TestClient(create_app(settings, llm, StubSearch([]), StubFetcher()))
    first = client.post(
        "/api/verify",
        json={"text": text},
        headers={"X-TruthLens-Message-Time": "2026-10-04T22:00:00+05:30"},
    )
    assert first.status_code == 200 and "2026-10-05" in first.json()["claims"][0]["dates"]
    second = client.post(
        "/api/verify",
        json={"text": text},
        headers={"X-TruthLens-Message-Time": "2026-10-05T22:00:00+05:30"},
    )
    assert "2026-10-12" in second.json()["claims"][0]["dates"]
    assert (
        client.post(
            "/api/verify", json={"text": text}, headers={"X-TruthLens-Message-Time": "2026-10-04"}
        ).status_code
        == 400
    )


def test_outdated_accepts_explicit_natural_calendar_dates_in_verbatim_sources(settings):
    text = "The demo library currently opens at 10 am."
    urls = ["https://rbi.org.in/history", "https://reuters.com/current"]
    pages = {
        urls[0]: article(
            "Effective 1 October 2026 the library opened at 10 am. This is an offline fictional archive."
        ),
        urls[1]: article(
            "Effective 10 October 2026 the library opens at 9 am, replacing the previous 10 am opening. This is an offline fictional archive."
        ),
    }
    llm = StubLLM(
        [text],
        verdict="outdated",
        stances=["context", "context"],
        dates=["2026-10-01", "2026-10-10"],
        current=True,
    )
    result = (
        TestClient(
            create_app(
                settings,
                llm,
                StubSearch([SearchHit(u, "Fixture", "snippet") for u in urls]),
                StubFetcher(pages),
            )
        )
        .post("/api/verify", json={"text": text})
        .json()
    )
    assert result["claims"][0]["verdict"] == "outdated"


def test_who_authority_is_global_but_not_the_ordinary_pronoun():
    assert authority_for("WHO was established in 1948.", "US") == "who.int"
    assert authority_for("The World Health Organization was established in 1948.") == "who.int"
    assert authority_for("People who use Aadhaar need a document.") == "uidai.gov.in"
    assert authority_for("People who use the library receive a ticket.") is None
