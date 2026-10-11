import html
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from app.config import Settings
from app.errors import AppError
from app.main import create_app
from app.schemas.models import ClaimBatch, Decision, Wording
from app.services.extract.url import Fetched
from app.services.search.client import SearchHit

CLAIMS = ["The demo library opens at 9 am.", "The demo library is closed on Sundays."]
FORWARD = (
    "Good morning! " + "Please read carefully. " * 80 + " ".join(CLAIMS) + " Forward to everyone!"
)


@pytest.fixture
def settings():
    return Settings(_env_file=None, gemini_api_key="", tavily_api_key="", max_pdf_pages=3)


def article(text, title="Fixture article", date="2026-10-09"):
    return (
        f'<html><head><title>{title}</title><meta property="og:title" content="{title}"><meta property="article:published_time" content="{date}"></head><body><article><h1>{title}</h1><p>{html.escape(text)}</p><p>'
        + html.escape(text)
        + "</p></article></body></html>"
    ).encode()


class StubLLM:
    # Test-only model doubles, never imported by production services.
    def __init__(self, claims=None, verdict="verified", stances=None, dates=None, current=False):
        self.claims = CLAIMS if claims is None else claims
        self.verdict = verdict
        self.stances = stances
        self.dates = dates or []
        self.current = current
        self.fail_assessment = False
        self.bad_excerpt = False
        self.bad_reference = False
        self.bad_span = False
        self.requests = []

    async def structured(self, task, data, model):
        self.requests.append((task, data))
        if model is ClaimBatch:
            return ClaimBatch(
                detected_language="en",
                truncated=False,
                claims=[
                    {
                        "claim_text": c,
                        "original_span": "invented span" if self.bad_span else c,
                        "entities": ["demo library"],
                        "dates": [],
                        "qualifiers": [],
                        "queries": [c],
                        "current_assertion": self.current,
                    }
                    for c in self.claims
                ],
            )
        if model is Decision:
            if self.fail_assessment:
                raise AppError("llm_provider_error", "Test failure", 502)
            sources = data["evidence"]
            return Decision(
                verdict=self.verdict,
                explanation="The fixture evidence establishes the opening time. This test uses mock sources.",
                short_summary="Fixture wording.",
                key_points=["Check the original announcement."],
                assessments=[
                    {
                        "evidence_id": "unknown" if self.bad_reference else e["evidence_id"],
                        "stance": self.stances[i]
                        if self.stances
                        else (
                            "contradicts"
                            if "Sundays" in data["claim"]["claim_text"]
                            else "supports"
                        ),
                        "excerpt": "invented quotation" if self.bad_excerpt else e["excerpt"][:700],
                        "what_source_says": "An unattributed model paraphrase should not become a quotation.",
                        "directly_relevant": True,
                    }
                    for i, e in enumerate(sources)
                ],
                decisive_evidence_ids=[e["evidence_id"] for e in sources],
                component_assessments=[
                    {
                        "original_span": data["claim"]["original_span"].removesuffix(" every day."),
                        "status": "supported",
                        "evidence_ids": [e["evidence_id"] for e in sources],
                    },
                    {
                        "original_span": "every day",
                        "status": "contradicted",
                        "evidence_ids": [e["evidence_id"] for e in sources],
                    },
                ]
                if self.verdict == "partially_true"
                else [],
                limitations=[],
                temporal_notes="Fixture dated context.",
                relevant_source_dates=self.dates,
                context_evidence_ids=[],
                temporal_witnesses=[
                    {
                        "evidence_id": e["evidence_id"],
                        "event_date": date,
                        "role": "historical" if i == 0 else "current",
                        "excerpt": e["excerpt"][:700],
                    }
                    for i, (e, date) in enumerate(zip(sources, self.dates, strict=False))
                ],
            )
        if model is Wording:
            text = {
                "en": "Read the original source. Keep the uncertainty in mind.",
                "hi": "मूल स्रोत पढ़ें। जहाँ जानकारी अधूरी है, वहाँ सावधानी रखें।",
                "mr": "मूळ स्रोत वाचा. माहिती अपुरी असल्यास काळजी घ्या.",
            }[data["language"]]
            return Wording(explanation=text, short_summary=text, key_points=[text], next_step=text)
        raise AssertionError(model)


class StubSearch:
    def __init__(self, hits=None, fail=False):
        self.hits = hits
        self.fail = fail

    async def search(self, query):
        if self.fail:
            raise AppError("search_provider_error", "Test search unavailable", 502)
        return (
            self.hits
            if self.hits is not None
            else [
                SearchHit(
                    url="https://rbi.org.in/fixture-announcement",
                    title="Offline fixture only",
                    content="The demo library opens at 9 am and remains open on Sundays.",
                    score=0.95,
                )
            ]
        )


class StubFetcher:
    def __init__(self, pages=None, fail=False):
        self.pages = pages or {}
        self.fail = fail

    async def fetch(self, url):
        if self.fail:
            raise AppError("url_fetch_error", "Fixture failure", 502)
        return Fetched(
            url,
            self.pages.get(
                url,
                article(
                    "The demo library opens at 9 am and remains open on Sundays. This is an offline test fixture, not an actual institutional statement."
                ),
            ),
            "text/html",
        )


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings, StubLLM(), StubSearch(), StubFetcher())) as session:
        yield session


@pytest.fixture
def screenshot():
    image = Image.new("RGB", (1400, 220), "white")
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 48)
    except OSError:
        font = ImageFont.load_default(size=48)
    ImageDraw.Draw(image).text((30, 70), "The library opens at 9 am.", fill="black", font=font)
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()
