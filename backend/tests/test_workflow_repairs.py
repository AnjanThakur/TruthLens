import json
from types import SimpleNamespace

import httpx
import pytest
from conftest import CLAIMS, StubFetcher, StubLLM, StubSearch, article
from fastapi.testclient import TestClient
from pydantic import SecretStr
from test_extraction import pdf_bytes
from test_http_security import Resolver

from app.errors import AppError
from app.main import create_app
from app.schemas.models import Decision, ExtractionResult
from app.services.chunks import split_text
from app.services.claims.parser import extract_claims
from app.services.extract.media import capabilities, pdf_extract
from app.services.extract.url import Fetched, SafeFetcher, article_from_html
from app.services.providers import GeminiLLM
from app.services.search.client import SearchHit, TavilySearch


def test_screenshot_missing_pages_preserves_exact_snippets_and_uncertainty(settings, screenshot):
    if not capabilities(settings)["ocr"]:
        pytest.skip("Tesseract unavailable")

    class MissingPage(StubFetcher):
        async def fetch(self, url):
            raise AppError("url_no_text", "Offline fixture: unreadable page", 422)

    llm = StubLLM(["The library opens at 9 am."], verdict="false")
    hits = [
        SearchHit(
            "https://rbi.org.in/offline-only",
            "Offline fixture",
            "No actual claim contradiction here.",
            0.9,
        )
    ]
    client = TestClient(create_app(settings, llm, StubSearch(hits), MissingPage()))
    extracted = client.post("/api/extract", files={"file": ("screen.png", screenshot)}).json()
    result = client.post(
        "/api/verify", json={"text": extracted["text"], "input_type": "image"}
    ).json()
    assert result["status"] == "partial" and result["claims"][0]["verdict"] == "unconfirmed"
    evidence = result["claims"][0]["evidence"][0]
    assert evidence["url"] == hits[0].url and evidence["excerpt"] == hits[0].content
    assert evidence["excerpt_provenance"] == "search_excerpt" and evidence["stance"] == "unclear"
    assert len(llm.requests) == 1  # no pointless assessment of snippets-only evidence


def test_partial_tavily_response_retains_valid_hits_and_warning(settings):
    settings.tavily_api_key = SecretStr("test-only")
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "results": [
                    {
                        "url": "https://rbi.org.in/fixture-only",
                        "title": "Offline source",
                        "content": "Actual fixture excerpt",
                        "score": 0.8,
                    },
                    {"url": "https://broken.test", "content": None},
                    {"url": 123},
                ]
            },
        )
    )
    client = TestClient(
        create_app(settings, StubLLM([CLAIMS[0]]), TavilySearch(settings, transport), StubFetcher())
    )
    result = client.post("/api/verify", json={"text": CLAIMS[0]}).json()
    assert result["status"] == "partial"
    assert "search_result_invalid_discarded" in result["warnings"]
    assert len(result["claims"][0]["evidence"]) == 1


def test_relevant_primary_source_ranked_before_higher_score_unreviewed(settings):
    settings.max_evidence = 1
    hits = [
        SearchHit("https://youtube.com/fixture", "Video", "Fixture", 0.99),
        SearchHit("https://rbi.org.in/fixture", "Primary", "Fixture", 0.7),
    ]
    result = (
        TestClient(create_app(settings, StubLLM([CLAIMS[0]]), StubSearch(hits), StubFetcher()))
        .post("/api/verify", json={"text": CLAIMS[0]})
        .json()
    )
    assert result["claims"][0]["evidence"][0]["publisher"] == "Reserve Bank of India"


def test_scanned_pdf_incomplete_structured_answer_is_rejected_once(settings, screenshot):
    if not capabilities(settings)["ocr"]:
        pytest.skip("Tesseract unavailable")
    settings.gemini_api_key = SecretStr("test-only")
    calls = []
    fallback = StubLLM(["The library opens at 9 am."])
    provider = GeminiLLM(
        settings,
        httpx.MockTransport(
            lambda request: (
                calls.append(request) or httpx.Response(200, json={"status": "incomplete"})
            )
        ),
    )

    class Incomplete(StubLLM):
        async def structured(self, task, data, model):
            if model is Decision:
                return await provider.structured(task, data, model)
            return await fallback.structured(task, data, model)

    client = TestClient(create_app(settings, Incomplete(), StubSearch(), StubFetcher()))
    extracted = client.post(
        "/api/extract", files={"file": ("scan.pdf", pdf_bytes(screenshot))}
    ).json()
    assert extracted["extraction_details"]["pages"][0]["method"] == "ocr"
    result = client.post(
        "/api/verify", json={"text": extracted["text"], "input_type": "pdf"}
    ).json()
    assert result["status"] == "partial" and "llm_output_invalid" in result["warnings"]
    assert result["claims"][0]["verdict"] == "unconfirmed" and len(calls) == 1
    assert all(e["stance"] == "unclear" for e in result["claims"][0]["evidence"])


def test_pdf_preview_keeps_later_page_chunks(settings):
    settings.max_text_chars = 100
    result = pdf_extract(pdf_bytes(), settings)
    assert len(result.text) == 100 and result.extraction_details["text_is_preview"]
    chunks = result.extraction_details["chunks"]
    assert {c["page_number"] for c in chunks} == {1, 2}
    assert any("Sundays" in c["text"] for c in chunks)
    assert any(w.startswith("extraction_text_truncated") for w in result.warnings)
    for chunk in chunks:
        page = result.extraction_details["pages"][chunk["page_number"] - 1]
        assert chunk["text"] == page["text"][chunk["page_start"] : chunk["page_end"]]


def test_pdf_excess_chunk_budget_is_explicit_error(settings):
    settings.document_chunk_chars = 100
    settings.max_document_chunks = 1
    with pytest.raises(AppError) as error:
        pdf_extract(pdf_bytes(), settings)
    assert error.value.code == "document_too_large" and error.value.status == 413
    settings.max_upload_bytes = 100
    with pytest.raises(AppError) as error:
        pdf_extract(pdf_bytes(), settings)
    assert error.value.code == "upload_too_large"


async def test_chunked_claim_extraction_preserves_tail_and_deduplicates(settings):
    settings.document_chunk_chars = 200
    text = "A factual first claim. " + "neutral filler " * 35 + "A factual last claim."
    llm = StubLLM([])

    class ByChunk(StubLLM):
        async def structured(self, task, data, model):
            llm.requests.append((task, data))
            found = [
                c for c in ["A factual first claim.", "A factual last claim."] if c in data["text"]
            ]
            return await StubLLM(found).structured(task, data, model)

    batch = await extract_claims(ByChunk(), text, "en", "IN", settings, "2026-10-11T00:00:00Z")
    assert [c.claim_text for c in batch.claims] == [
        "A factual first claim.",
        "A factual last claim.",
    ]
    assert all(len(data["text"]) <= 200 for _, data in llm.requests)
    assert not batch.truncated


async def test_chunk_budget_rejected_before_any_model_call(settings):
    settings.document_chunk_chars = 100
    settings.max_document_chunks = 1
    llm = StubLLM([])
    with pytest.raises(AppError):
        await extract_claims(llm, "a" * 400, "en", "IN", settings, "2026-10-11T00:00:00Z")
    assert not llm.requests


def test_chunk_spans_and_long_sentence_context():
    text = "A " * 500
    chunks = split_text(text, 400, 8)
    assert all(c.text == text[c.start : c.end] and len(c.text) <= 400 for c in chunks)
    assert any(c.boundary_split for c in chunks)
    assert chunks[-1].end == len(text) and chunks[1].start < chunks[0].end


async def test_http_read_timeout_is_504_and_still_pinned(settings):
    requests = []

    def handler(request):
        requests.append(request)
        raise httpx.ReadTimeout("Private fixture detail", request=request)

    with pytest.raises(AppError) as error:
        await SafeFetcher(settings, Resolver({}), httpx.MockTransport(handler)).fetch(
            "https://public.test/article"
        )
    assert error.value.code == "url_timeout" and error.value.status == 504
    assert "Private fixture detail" not in str(error.value)
    assert requests[0].url.host == "93.184.216.34" and requests[0].headers["host"] == "public.test"


def test_publication_modification_and_event_dates_are_separate():
    body = article(
        "An event happened on 2020-02-01. This offline fixture discusses its context without assigning its date to publication.",
        date="2026-01-01",
    )
    body = body.replace(
        b"</head>", b'<meta property="article:modified_time" content="2026-02-02T10:00:00Z"></head>'
    )
    details = article_from_html(body, "https://public.test/article").extraction_details
    assert details["published_at"] == "2026-01-01"
    assert details["updated_at"] == "2026-02-02T10:00:00Z"
    assert details["event_date"] is None and details["date_provenance"].startswith("explicit_meta")


def test_extractor_inferred_date_is_not_publication_and_local_recall_used(monkeypatch):
    calls = []

    def extract(*args, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return None
        return SimpleNamespace(
            text="Readable offline article content. " * 20,
            date="2026-10-11",
            language="en",
            title="Fixture",
            sitename=None,
            author=None,
        )

    monkeypatch.setattr("trafilatura.bare_extraction", extract)
    result = article_from_html(
        b"<article>Fixture without publisher dates.</article>", "https://public.test/article"
    )
    assert result.extraction_details["published_at"] is None
    assert calls[1]["favor_recall"] and len(calls) == 2


def test_jsonld_restricted_article_not_decisive(settings):
    ld = json.dumps(
        {
            "@type": "NewsArticle",
            "datePublished": "2025-01-01",
            "dateModified": "2026-01-01",
            "isAccessibleForFree": False,
        }
    )
    body = article(
        "This offline fixture contains only the visible introduction of a restricted article. " * 8
    ).replace(b"</head>", f'<script type="application/ld+json">{ld}</script></head>'.encode())
    hit = SearchHit("https://rbi.org.in/fixture-only", "Fixture", "Fixture snippet", 0.9)
    result = (
        TestClient(
            create_app(
                settings,
                StubLLM([CLAIMS[0]], verdict="verified"),
                StubSearch([hit]),
                StubFetcher({hit.url: body}),
            )
        )
        .post("/api/verify", json={"text": CLAIMS[0]})
        .json()
    )
    assert result["status"] == "partial" and result["claims"][0]["verdict"] == "unconfirmed"
    assert "source_content_incomplete" in result["warnings"]
    assert result["claims"][0]["evidence"][0]["updated_at"] == "2026-01-01"


def test_valid_date_outside_selected_quote_is_not_falsely_rejected(settings):
    date = "2025-01-01"
    body = article(
        "Grounded source fixture. " * 55
        + date
        + " is the effective event date in this offline fixture.",
        date="2026-01-01",
    )
    hit = SearchHit("https://rbi.org.in/fixture-only", "Fixture", "Fixture", 0.9)
    llm = StubLLM([CLAIMS[0]], dates=[date])
    result = (
        TestClient(create_app(settings, llm, StubSearch([hit]), StubFetcher({hit.url: body})))
        .post("/api/verify", json={"text": CLAIMS[0]})
        .json()
    )
    assert "evidence_date_invalid" not in result["warnings"]
    assert result["claims"][0]["temporal_context"]["relevant_source_dates"] == [date]


def test_url_preview_warns_and_chunks_bound_output(settings):
    settings.max_text_chars = 100
    client = TestClient(create_app(settings, fetcher=StubFetcher()))
    response = client.post("/api/extract/url", json={"url": "https://public.test/article"})
    assert response.status_code == 200
    result = response.json()
    assert len(result["text"]) == 100 and "extraction_text_truncated" in result["warnings"]
    assert result["extraction_details"]["content_complete"] is False
    assert all(
        len(c["text"]) <= settings.document_chunk_chars
        for c in result["extraction_details"]["chunks"]
    )


def test_low_quality_source_pdf_cannot_establish_decisive_verdict(settings, monkeypatch):
    monkeypatch.setattr(
        "app.services.extract.media.pdf_extract",
        lambda *_: ExtractionResult(
            text="Offline fixture: unreliable OCR words.",
            detected_language="en",
            input_type="pdf",
            warnings=["page_1:low_ocr_readability: Review the words."],
        ),
    )

    class PdfFetcher:
        async def fetch(self, url):
            return Fetched(url, b"%PDF-offline", "application/pdf")

    hit = SearchHit("https://rbi.org.in/offline-ocr.pdf", "Offline fixture", "Snippet", 0.9)
    llm = StubLLM([CLAIMS[0]], verdict="verified")
    result = (
        TestClient(create_app(settings, llm, StubSearch([hit]), PdfFetcher()))
        .post("/api/verify", json={"text": CLAIMS[0]})
        .json()
    )
    assert result["claims"][0]["verdict"] == "unconfirmed" and result["status"] == "partial"
    assert "incomplete_content:" in result["claims"][0]["evidence"][0]["authority_basis"]
    assert len(llm.requests) == 1


def test_pdf_hard_boundaries_overlap_without_losing_page_context(settings):
    import pymupdf

    settings.document_chunk_chars = 100
    with pymupdf.open() as document:
        document.new_page(width=1600, height=500).insert_text((20, 70), "Exact long line " * 14)
        result = pdf_extract(document.tobytes(), settings)
    chunks = result.extraction_details["chunks"]
    assert chunks[0]["boundary_split"] and chunks[1]["page_start"] < chunks[0]["page_end"]
    assert all(
        c["text"] == result.extraction_details["pages"][0]["text"][c["page_start"] : c["page_end"]]
        for c in chunks
    )


def test_invalid_search_ledger_values_discarded_without_crashing(settings):
    hits = [
        SearchHit("https://rbi.org.in/fixture", None, "Text", 0.9),
        SearchHit("https://pib.gov.in/fixture", "Fixture", "Text", float("nan")),
    ]
    result = (
        TestClient(create_app(settings, StubLLM([CLAIMS[0]]), StubSearch(hits), StubFetcher()))
        .post("/api/verify", json={"text": CLAIMS[0]})
        .json()
    )
    assert result["claims"][0]["verdict"] == "unconfirmed" and result["claims"][0]["evidence"] == []
    assert "search_result_invalid_discarded" in result["warnings"]
