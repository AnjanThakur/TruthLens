import time
from pathlib import Path
from uuid import UUID

import pytest
from cryptography.fernet import Fernet

from truthlens_whatsapp.config import Settings
from truthlens_whatsapp.store import Store


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import httpx

    def blocked(*args, **kwargs):
        raise AssertionError("Tests must not access the network")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", blocked)


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,
        whatsapp_phone_number_id="12345",
        whatsapp_waba_id="67890",
        whatsapp_verify_token="offline-verify-token",
        meta_app_secret="offline-app-secret",
        state_encryption_key=Fernet.generate_key().decode(),
        identity_hash_secret="offline-hash-secret-" * 3,
        database_url=f"sqlite:///{tmp_path / 'test.sqlite3'}",
        graph_api_version="v99.0",
        whatsapp_access_token="offline-access-token",
    )


@pytest.fixture
def store(settings):
    return Store(settings)


@pytest.fixture
def message():
    return {
        "id": "wamid.offline-1",
        "from": "15550000001",
        "type": "text",
        "timestamp": str(int(time.time())),
        "text": {"body": "A fictional test claim."},
    }


@pytest.fixture
def event(settings, message):
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": settings.whatsapp_waba_id,
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"phone_number_id": settings.whatsapp_phone_number_id},
                            "messages": [message],
                        },
                    }
                ],
            }
        ],
    }


@pytest.fixture
def report():
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    uid = str(UUID(int=1))
    return {
        "verification_id": uid,
        "status": "completed",
        "input": {
            "text": "A fictional test claim.",
            "input_type": "text",
            "detected_language": "en",
            "warnings": [],
            "extraction_details": {},
        },
        "summary": "OFFLINE TEST RESPONSE, not a real fact-check.",
        "checked_at": now,
        "warnings": [],
        "response_language": "en",
        "audience": "adult",
        "claims": [
            {
                "claim_id": uid,
                "claim_text": "A fictional test claim.",
                "original_span": "A fictional test claim.",
                "entities": [],
                "dates": [],
                "qualifiers": [],
                "normalized_claim": "a fictional test claim.",
                "lexical_hash": "test",
                "verdict": "unconfirmed",
                "grounded_explanation": "No conclusion established in this offline test.",
                "explanation": "No conclusion established in this offline test.",
                "short_summary": "Unconfirmed test",
                "key_points": [],
                "next_step": "Check real sources.",
                "limitations": ["Offline test"],
                "checked_at": now,
                "risk": {
                    "score": 0,
                    "level": "low",
                    "factors": [],
                    "is_probability": False,
                    "label": "Not a probability",
                },
                "temporal_context": {"claim_date": None, "relevant_source_dates": [], "notes": ""},
                "original_context": {"status": "not_checked", "notes": "", "source_urls": []},
                "evidence": [
                    {
                        "evidence_id": uid,
                        "title": "Offline source fixture",
                        "url": "https://example.test/source",
                        "publisher": "Fictional test publisher",
                        "source_type": "other",
                        "published_at": None,
                        "updated_at": None,
                        "retrieved_at": now,
                        "stance": "unclear",
                        "excerpt": "Offline evidence fixture.",
                        "excerpt_provenance": "search_excerpt",
                        "what_source_says": "Offline evidence fixture.",
                        "authority_basis": "Unestablished fixture",
                        "relevance_score": 0,
                        "directly_relevant": False,
                    }
                ],
            }
        ],
    }


def extraction(kind="image", **details):
    return {
        "text": "A fictional test claim.",
        "input_type": kind,
        "detected_language": "en",
        "warnings": [],
        "extraction_details": details,
    }


ROOT = Path(__file__).resolve().parents[2]
