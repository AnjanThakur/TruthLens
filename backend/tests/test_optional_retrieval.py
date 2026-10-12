"""Offline regression for the recorded WHO non-decisive DNS failure."""

import pytest
from conftest import StubFetcher, StubLLM, StubSearch, article
from fastapi.testclient import TestClient

from app.errors import AppError
from app.main import create_app
from app.services.search.client import SearchHit

CLAIM = "The World Health Organization was established on 7 April 1948."
PRIMARY = "https://www.who.int/about/governance/constitution"
SECOND = "https://www.who.int/hongkongchina/about-us"
OPTIONAL = "https://en.wikipedia.org/wiki/World_Health_Organization"


class FailedPage(StubFetcher):
    def __init__(self, failed, code):
        super().__init__({PRIMARY: article(CLAIM), SECOND: article(CLAIM)})
        self.failed, self.code = failed, code

    async def fetch(self, url):
        if url == self.failed:
            raise AppError(self.code, "Offline page failure", 502)
        return await super().fetch(url)


@pytest.mark.parametrize(
    "failed,code,verdict,empty,expected",
    [
        (OPTIONAL, "url_dns_error", "verified", False, "completed"),
        (OPTIONAL, "url_no_text", "verified", False, "completed"),
        (OPTIONAL, "url_dns_error", "unconfirmed", False, "partial"),
        (PRIMARY, "url_dns_error", "verified", False, "partial"),
        (OPTIONAL, "unsafe_url", "verified", False, "partial"),
        (OPTIONAL, "url_dns_error", "verified", True, "partial"),
    ],
)
def test_optional_failure_preserves_warning_and_trusted_guard(
    settings, failed, code, verdict, empty, expected
):
    hits = [
        SearchHit(PRIMARY, "Constitution", CLAIM, 0.9),
        SearchHit(SECOND, "About WHO", CLAIM, 0.8),
        SearchHit(OPTIONAL, "Optional result", "" if empty else CLAIM, 0.7),
    ]
    llm = StubLLM([CLAIM], verdict, ["supports"] * 3)
    with TestClient(
        create_app(settings, llm, StubSearch(hits), FailedPage(failed, code))
    ) as client:
        result = client.post("/api/verify", json={"text": CLAIM}).json()
    assert result["status"] == expected
    assert "source_page_unavailable:" + code in result["warnings"]
    claim = result["claims"][0]
    assert claim["verdict"] == verdict
    sources = {source["url"]: source for source in claim["evidence"]}
    assert sources[SECOND]["excerpt_provenance"] == "fetched_page"
    if expected == "completed":
        assert sources[OPTIONAL]["source_type"] == "other"
        assert sources[OPTIONAL]["excerpt_provenance"] == "search_excerpt"
        assert any("optional unreviewed" in note for note in claim["limitations"])


def test_optional_dns_failure_does_not_hide_assessment_error(settings):
    llm = StubLLM([CLAIM])
    llm.fail_assessment = True
    hits = [SearchHit(PRIMARY, "WHO", CLAIM, 0.9), SearchHit(OPTIONAL, "Other", CLAIM, 0.8)]
    with TestClient(
        create_app(settings, llm, StubSearch(hits), FailedPage(OPTIONAL, "url_dns_error"))
    ) as client:
        result = client.post("/api/verify", json={"text": CLAIM}).json()
    assert result["status"] == "partial"
    assert result["claims"][0]["verdict"] == "unconfirmed"
    assert "llm_provider_error" in result["warnings"]


def test_optional_failure_does_not_hide_an_incomplete_search_stage(settings):
    class InterruptedSearch(StubSearch):
        calls = 0

        async def search(self, query):
            self.calls += 1
            if self.calls > 1:
                raise AppError("search_provider_error", "Offline stage failure", 502)
            return await super().search(query)

    hits = [SearchHit(PRIMARY, "WHO", CLAIM, 0.9), SearchHit(OPTIONAL, "Other", CLAIM, 0.8)]
    with TestClient(
        create_app(
            settings,
            StubLLM([CLAIM]),
            InterruptedSearch(hits),
            FailedPage(OPTIONAL, "url_dns_error"),
        )
    ) as client:
        result = client.post("/api/verify", json={"text": CLAIM}).json()
    assert result["status"] == "partial"
    assert result["claims"][0]["verdict"] == "verified"
    assert "search_provider_error" in result["warnings"]
    assert "source_page_unavailable:url_dns_error" in result["warnings"]
