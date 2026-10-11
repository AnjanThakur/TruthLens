from conftest import CLAIMS, FORWARD, StubFetcher, StubLLM, StubSearch, article
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.search.client import SearchHit


def test_long_forward_separate_claims_and_different_outcomes(settings):
    class DifferentVerdicts(StubLLM):
        async def structured(self, task, data, model):
            if "claim" in data:
                self.verdict = "false" if "Sundays" in data["claim"]["claim_text"] else "verified"
            return await super().structured(task, data, model)

    client = TestClient(create_app(settings, DifferentVerdicts(), StubSearch(), StubFetcher()))
    response = client.post("/api/verify", json={"text": FORWARD})
    assert response.status_code == 200, response.text
    result = response.json()
    assert [c["verdict"] for c in result["claims"]] == ["verified", "false"]
    assert len({c["claim_id"] for c in result["claims"]}) == 2
    for c in result["claims"]:
        assert c["original_span"] in FORWARD
        assert c["evidence"][0]["excerpt_provenance"] == "fetched_page"
        assert c["evidence"][0]["what_source_says"] == c["evidence"][0]["excerpt"]
        assert len(c["lexical_hash"]) == 64


def test_empty_claims(settings):
    client = TestClient(create_app(settings, StubLLM(claims=[]), StubSearch(), StubFetcher()))
    result = client.post("/api/verify", json={"text": "Good morning!"}).json()
    assert result["status"] == "no_checkable_claims"
    assert result["claims"] == []


def test_no_evidence_is_unconfirmed(settings):
    client = TestClient(
        create_app(settings, StubLLM(verdict="false"), StubSearch(hits=[]), StubFetcher())
    )
    result = client.post("/api/verify", json={"text": FORWARD}).json()
    assert all(c["verdict"] == "unconfirmed" and c["evidence"] == [] for c in result["claims"])
    assert "no_usable_evidence_retrieved" in result["warnings"]


def test_conflicting_sources_preserved(settings):
    hits = [
        SearchHit("https://rbi.org.in/fixture-a", "A", "A supports", 0.9),
        SearchHit("https://reuters.com/fixture-b", "B", "B contradicts", 0.9),
    ]
    client = TestClient(
        create_app(
            settings,
            StubLLM(claims=[CLAIMS[0]], stances=["supports", "contradicts"]),
            StubSearch(hits),
            StubFetcher(),
        )
    )
    result = client.post("/api/verify", json={"text": CLAIMS[0]}).json()["claims"][0]
    assert result["verdict"] == "unconfirmed"
    assert {e["stance"] for e in result["evidence"]} == {"supports", "contradicts"}


def test_failed_page_search_excerpt_not_definitive(settings):
    client = TestClient(create_app(settings, StubLLM(), StubSearch(), StubFetcher(fail=True)))
    result = client.post("/api/verify", json={"text": FORWARD}).json()
    assert result["status"] == "partial"
    assert all(c["verdict"] == "unconfirmed" for c in result["claims"])
    assert result["claims"][0]["evidence"][0]["excerpt_provenance"] == "search_excerpt"


def test_search_error_is_distinct_from_no_results(settings):
    client = TestClient(create_app(settings, StubLLM(), StubSearch(fail=True), StubFetcher()))
    result = client.post("/api/verify", json={"text": FORWARD}).json()
    assert result["status"] == "partial"
    assert "search_provider_error" in result["warnings"]
    assert all(c["verdict"] == "unconfirmed" for c in result["claims"])


def test_translation_preserves_all_core_fields(client):
    original = client.post("/api/verify", json={"text": FORWARD}).json()
    mutable = {"explanation", "short_summary", "key_points", "next_step"}
    for language in ("en", "hi", "mr"):
        for audience in ("child", "teen", "adult", "senior"):
            response = client.post(
                "/api/explain",
                json={"result": original, "language": language, "audience": audience},
            )
            assert response.status_code == 200, response.text
            translated = response.json()
            assert translated["verification_id"] == original["verification_id"]
            assert translated["checked_at"] == original["checked_at"]
            for before, after in zip(original["claims"], translated["claims"], strict=True):
                assert {k: v for k, v in before.items() if k not in mutable} == {
                    k: v for k, v in after.items() if k not in mutable
                }


def test_outdated_requires_old_and_current_dated_sources(settings):
    text = "The demo scheme is open now."
    dates = ["2020-01-01", "2026-01-01"]
    hits = [
        SearchHit("https://pib.gov.in/fixture-old", "Old", "old", 0.9),
        SearchHit("https://pib.gov.in/fixture-new", "New", "new", 0.9),
    ]
    pages = {
        hit.url: article(
            "Scheme fixture for dated test "
            + date
            + ". The application window described here has changed. This is only an offline fixture.",
            date=date,
        )
        for hit, date in zip(hits, dates, strict=True)
    }
    llm = StubLLM(
        [text], verdict="outdated", stances=["context", "context"], dates=dates, current=True
    )
    client = TestClient(create_app(settings, llm, StubSearch(hits), StubFetcher(pages)))
    result = client.post("/api/verify", json={"text": text}).json()
    assert result["claims"][0]["verdict"] == "outdated"
    # An old article alone is insufficient.
    llm.dates = [dates[0]]
    client = TestClient(create_app(settings, llm, StubSearch(hits[:1]), StubFetcher(pages)))
    assert (
        client.post("/api/verify", json={"text": text}).json()["claims"][0]["verdict"]
        == "unconfirmed"
    )


def test_otp_warning_is_separate_from_fact_verdict(settings):
    text = CLAIMS[0] + " Send your OTP and Aadhaar urgently. Pay a processing fee."
    client = TestClient(
        create_app(settings, StubLLM([CLAIMS[0]], verdict="false"), StubSearch([]), StubFetcher())
    )
    claim = client.post("/api/verify", json={"text": text}).json()["claims"][0]
    assert claim["verdict"] == "unconfirmed"
    assert claim["risk"]["is_probability"] is False
    assert claim["risk"]["score"] >= 60
    assert "otp_request" in {f["rule"] for f in claim["risk"]["factors"]}


def test_rbi_demo_prompt_has_no_static_evidence(settings):
    text = "From Monday all ₹500 notes are invalid."
    client = TestClient(
        create_app(settings, StubLLM([text], verdict="false"), StubSearch([]), StubFetcher())
    )
    claim = client.post("/api/verify", json={"text": text, "response_language": "hi"}).json()[
        "claims"
    ][0]
    assert claim["verdict"] == "unconfirmed" and claim["evidence"] == []


def test_hallucinated_excerpt_and_reference_rejected(settings):
    for field in ("bad_excerpt", "bad_reference", "fail_assessment"):
        llm = StubLLM([CLAIMS[0]])
        setattr(llm, field, True)
        client = TestClient(create_app(settings, llm, StubSearch(), StubFetcher()))
        claim = client.post("/api/verify", json={"text": CLAIMS[0]}).json()["claims"][0]
        assert claim["verdict"] == "unconfirmed"
        assert all(e["stance"] == "unclear" for e in claim["evidence"])


def test_claim_spans_must_be_in_input(settings):
    llm = StubLLM()
    llm.bad_span = True
    client = TestClient(create_app(settings, llm, StubSearch(), StubFetcher()))
    response = client.post("/api/verify", json={"text": FORWARD})
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "claim_span_invalid"
