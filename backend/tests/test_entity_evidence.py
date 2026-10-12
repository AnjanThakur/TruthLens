"""Fictional offline evidence only; never asserts a real person's death."""

import logging

import httpx
import pytest
from conftest import StubFetcher, StubLLM, StubSearch, article
from fastapi.testclient import TestClient
from test_http_security import Resolver

from app.errors import AppError
from app.main import create_app
from app.schemas.models import AtomicClaim, ClaimBatch
from app.services.extract.url import SafeFetcher, article_from_html
from app.services.search.client import CURRENT_SEARCH_DOMAINS, SearchHit, TavilySearch
from app.services.search.investigation import investigation_plan
from app.services.search.ledger import Ledger, identity, relevant_window

TEXT = "Example Actor died."
SUPPORT = (
    "OFFLINE FICTIONAL FIXTURE: Example Actor died. The family confirmed the death to the reporter. "
    * 3
)
DENIAL = (
    "OFFLINE FICTIONAL FIXTURE: Example Actor is alive. His family denied the death rumor as false. "
    * 3
)
UNKNOWN = (
    "OFFLINE FICTIONAL FIXTURE: Example Actor's family declined to comment. The report remains unconfirmed. "
    * 3
)
WIRE = "https://reuters.com/world/offline-fictional-actor"
AP = "https://apnews.com/article/offline-fictional-actor"
MANGA = "https://en.wikipedia.org/wiki/Example_(manga)"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Evidence regressions cannot use live HTTP.")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)


def claim():
    return AtomicClaim(
        claim_text=TEXT,
        original_span=TEXT,
        entities=["Example Actor"],
        dates=[],
        qualifiers=[],
        queries=["Example Actor death", "Example Actor alive death hoax"],
        current_assertion=False,
    )


class Model(StubLLM):
    async def structured(self, task, data, model):
        if model is ClaimBatch:
            self.requests.append((task, data))
            return ClaimBatch(detected_language="en", truncated=False, claims=[claim()])
        return await super().structured(task, data, model)


def verify(settings, pages, hits, verdict="verified", stances=None, failed=False):
    llm = Model([TEXT], verdict, stances)
    with TestClient(
        create_app(settings, llm, StubSearch(hits), StubFetcher(pages, failed))
    ) as client:
        result = client.post("/api/verify", json={"text": TEXT}).json()
    return result, llm


def test_unknown_authority_discovery_is_neutral_and_preserves_wire_search_in_two_queries():
    plan = investigation_plan(claim())
    assert '"Example Actor"' in plan[0].query
    assert plan[0].include_domains == ("reuters.com", "apnews.com", "bbc.com")
    assert "hoax" not in plan[0].query and "hoax" not in plan[1].query
    assert "false claim" in plan[2].query and "PDF" not in plan[3].query


async def test_two_searches_discover_wires_and_check_contradictions(settings):
    settings.max_search_queries_per_claim = 2

    class Search:
        calls = []

        async def search(self, query):
            self.calls.append((query, CURRENT_SEARCH_DOMAINS.get()))
            return []

    search = Search()
    await Ledger(settings, search, StubFetcher()).retrieve(claim())
    assert len(search.calls) == 2
    assert "apnews.com" in search.calls[0][1] and "correction" in search.calls[1][0]
    assert not search.calls[1][1] and not CURRENT_SEARCH_DOMAINS.get()


async def test_domain_filters_reach_provider_and_have_separate_cache_keys(settings):
    import json

    from pydantic import SecretStr

    settings.tavily_api_key = SecretStr("fixture-key")
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"results": []})

    search = TavilySearch(settings, httpx.MockTransport(handler))
    await search.search("same text")
    token = CURRENT_SEARCH_DOMAINS.set(("reuters.com", "apnews.com"))
    try:
        await search.search("same text")
        await search.search("same text")
    finally:
        CURRENT_SEARCH_DOMAINS.reset(token)
    assert len(bodies) == search.request_count == 2
    assert "include_domains" not in bodies[0]
    assert bodies[1]["include_domains"] == ["reuters.com", "apnews.com"]
    assert bodies[1]["include_domains_mode"] == "prefer"


async def test_distinct_complete_publishers_survive_final_selection(settings):
    settings.max_evidence = 2

    class Search:
        calls = 0

        async def search(self, query):
            self.calls += 1
            return (
                [
                    SearchHit(WIRE, "Report", SUPPORT, 0.9),
                    SearchHit(WIRE + "-followup", "Followup", SUPPORT, 0.8),
                ]
                if self.calls == 1
                else [SearchHit(AP, "Other report", SUPPORT, 0.2)]
                if self.calls == 2
                else []
            )

    pages = {u: article(SUPPORT) for u in [WIRE, WIRE + "-followup", AP]}
    sources, _ = await Ledger(settings, Search(), StubFetcher(pages)).retrieve(claim())
    assert {e.publisher for e in sources} == {"Reuters", "Associated Press"}


async def test_full_entity_beats_high_scoring_namesake_before_fetch(settings):
    settings.max_evidence = 1
    hits = [
        SearchHit(MANGA, "Example manga dies", "Example manga death", 0.99),
        SearchHit(WIRE, TEXT, SUPPORT, 0.01),
    ]
    sources, _ = await Ledger(
        settings, StubSearch(hits), StubFetcher({WIRE: article(SUPPORT)})
    ).retrieve(claim())
    assert len(sources) == 1 and sources[0].url == WIRE


def test_actual_entity_window_beats_generic_death_words():
    body = "death report false fact correction " * 160 + SUPPORT
    window = relevant_window(body, claim().queries, 900, claim())
    assert "Example Actor" in window and window in body


def test_independent_fetched_bodies_reach_assessment_with_ids_and_dates(settings):
    pages = {
        WIRE: article(SUPPORT, "Fictional report", "2026-10-08"),
        AP: article(SUPPORT.replace("family", "hospital"), "Fictional second report", "2026-10-09"),
    }
    hits = [
        SearchHit(WIRE, "Misleading search title", "Search-only invented text", 0.2),
        SearchHit(AP, "Second", "Search-only invented text", 0.1),
    ]
    result, llm = verify(settings, pages, hits, stances=["supports", "supports"])
    assert result["claims"][0]["verdict"] == "verified" and result["status"] == "completed"
    assessment = next(data for _, data in llm.requests if "evidence" in data)
    assert len(assessment["evidence"]) == 2
    for source in assessment["evidence"]:
        assert source["excerpt_provenance"] == "fetched_page" and source["content_complete"]
        assert "Search-only invented text" not in source["excerpt"]
        assert "Example Actor" in source["excerpt"] and source["evidence_id"]
        assert source["published_at"] in {"2026-10-08", "2026-10-09"}
    for source in result["claims"][0]["evidence"]:
        assert source["what_source_says"] == source["excerpt"]


@pytest.mark.parametrize(
    "body,proposal,stance,expected",
    [
        (DENIAL, "false", "contradicts", "false"),
        (UNKNOWN, "unconfirmed", "unclear", "unconfirmed"),
        (DENIAL, "verified", "contradicts", "unconfirmed"),
    ],
)
def test_misleading_headline_does_not_override_actual_body(
    settings, body, proposal, stance, expected
):
    result, _ = verify(
        settings,
        {WIRE: article(body, "Fictional death rumor")},
        [SearchHit(WIRE, "Example Actor died", SUPPORT)],
        proposal,
        [stance],
    )
    assert result["claims"][0]["verdict"] == expected
    assert body[:90] in result["claims"][0]["evidence"][0]["excerpt"]


def test_conflicting_complete_reporting_stays_unconfirmed(settings):
    result, _ = verify(
        settings,
        {WIRE: article(SUPPORT), AP: article(DENIAL)},
        [SearchHit(WIRE, "Report", SUPPORT), SearchHit(AP, "Denial", DENIAL)],
        "verified",
        ["supports", "contradicts"],
    )
    assert result["claims"][0]["verdict"] == "unconfirmed"
    assert {e["stance"] for e in result["claims"][0]["evidence"]} == {"supports", "contradicts"}


def test_fetched_namesake_cannot_establish_verdict_even_if_model_supports(settings):
    namesake = "OFFLINE FIXTURE: Example is a manga character who died in the series. " * 8
    result, llm = verify(settings, {WIRE: article(namesake)}, [SearchHit(WIRE, TEXT, SUPPORT)])
    assert result["claims"][0]["verdict"] == "unconfirmed"
    assert "entity_mismatch:" in result["claims"][0]["evidence"][0]["authority_basis"]
    assert not any("evidence" in data for _, data in llm.requests)
    assert "0 complete reviewed source(s)" in result["claims"][0]["explanation"]


@pytest.mark.parametrize(
    "body,stances,expected",
    [
        (UNKNOWN, ["unclear", "supports"], "unconfirmed"),
        (SUPPORT, ["supports", "contradicts"], "verified"),
    ],
)
def test_namesake_assessment_cannot_establish_support_or_conflict(
    settings, body, stances, expected
):
    namesake = "OFFLINE FIXTURE: Example is a manga character who died in the series. " * 8
    result, _ = verify(
        settings,
        {WIRE: article(body), AP: article(namesake)},
        [SearchHit(WIRE, TEXT, body), SearchHit(AP, TEXT, SUPPORT)],
        "verified",
        stances,
    )
    assert result["claims"][0]["verdict"] == expected


def test_titles_and_snippets_never_verify_unavailable_pages(settings):
    result, llm = verify(settings, {}, [SearchHit(WIRE, TEXT, SUPPORT)], failed=True)
    assert result["claims"][0]["verdict"] == "unconfirmed" and result["status"] == "partial"
    source = result["claims"][0]["evidence"][0]
    assert source["excerpt_provenance"] == "search_excerpt"
    assert "source_fetch_failure=url_fetch_error" in source["authority_basis"]
    assert not any("evidence" in data for _, data in llm.requests)


@pytest.mark.parametrize(
    "status,category",
    [
        (401, "access_denied"),
        (403, "access_denied"),
        (404, "not_found"),
        (410, "not_found"),
        (429, "rate_limited"),
        (503, "transient_server"),
    ],
)
async def test_http_failures_are_specific_sanitized_and_not_retried(
    settings, status, category, caplog
):
    caplog.set_level(logging.WARNING, logger="truthlens.diagnostics")
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(status, text="fixture-private-token full response")

    fetcher = SafeFetcher(settings, Resolver({}), httpx.MockTransport(handler))
    with pytest.raises(AppError) as error:
        await fetcher.fetch(WIRE + "?token=fixture-private-token")
    assert error.value.category == category and error.value.provider_status == status
    ledger = Ledger(settings, StubSearch(), fetcher)
    sources, _ = await ledger._retrieve_hits(claim(), [SearchHit(WIRE, TEXT, SUPPORT)])
    assert f"source_fetch_category={category}" in sources[0].authority_basis
    assert f"source_fetch_http_status={status}" in sources[0].authority_basis
    assert len(requests) == 2  # one fetch per invocation, no retries
    assert "fixture-private-token" not in caplog.text and "reuters.com" not in caplog.text


@pytest.mark.parametrize(
    "exc,category",
    [
        (httpx.ConnectError("private"), "connection_failed"),
        (httpx.ReadTimeout("private"), "timeout"),
        (httpx.RemoteProtocolError("private"), "transport_error"),
    ],
)
async def test_network_errors_do_not_collapse_or_leak(settings, exc, category):
    def handler(request):
        raise exc

    with pytest.raises(AppError) as caught:
        await SafeFetcher(settings, Resolver({}), httpx.MockTransport(handler)).fetch(WIRE)
    assert caught.value.category == category and "private" not in caught.value.message


def test_short_non_article_page_is_incomplete(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(
        "trafilatura.bare_extraction",
        lambda *a, **k: SimpleNamespace(
            text="Video player. Subscribe and watch now.", title="Death headline", language="en"
        ),
    )
    result = article_from_html(b"<html><body><div>Video player</div></body></html>", WIRE)
    assert not result.extraction_details["content_complete"]


@pytest.mark.parametrize(
    "url,kind",
    [
        ("https://timesofindia.indiatimes.com/india/report/articleshow/1.cms", "secondary"),
        (
            "https://timesofindia.indiatimes.com/entertainment/hindi/bollywood/news/topic/liveblog/1.cms",
            "secondary",
        ),
        ("https://timesofindia.indiatimes.com/blogs/opinion/story", "other"),
        ("https://www.ndtv.com/india-news/article-123", "secondary"),
        ("https://www.ndtv.com/video/headline-123", "other"),
        ("https://ndtv.com.evil.example/india-news/article", "other"),
        ("https://www.nbcnews.com/news/report", "other"),
    ],
)
def test_reviewed_publishers_are_scoped_and_lookalikes_not_trusted(url, kind):
    assert identity(url)[1] == kind
