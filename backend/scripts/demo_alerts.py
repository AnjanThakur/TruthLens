"""Entirely fictional, offline alert demonstration; simulated review, no publishing."""

import argparse
import json
import secrets
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.schemas.models import (
    ClaimResult,
    Evidence,
    ExtractionResult,
    Language,
    OriginalContext,
    Stance,
    TemporalContext,
    Verdict,
    VerificationResult,
)
from app.services.alerts.engine import AlertEngine
from app.services.alerts.models import ApproveRequest, IngestRequest
from app.services.alerts.settings import AlertsSettings
from app.services.verify.risk import risk_for

SAMPLE_CLAIMS: dict[Language, str] = {
    "en": "Send OTP to verify your bank account KYC.",
    "hi": "बैंक खाते के केवायसी सत्यापन के लिए ओटीपी भेजें।",
    "mr": "बँक खात्याचे केवायसी पडताळणी करण्यासाठी ओटीपी पाठवा.",
}


def fixture_record(
    instant: datetime,
    language: Language = "en",
    *,
    text: str | None = None,
    verdict: Verdict = "false",
    stance: Stance = "contradicts",
) -> VerificationResult:
    """Fictional source path/content, never evidence of an actual RBI announcement."""
    text = text or SAMPLE_CLAIMS[language]
    evidence = Evidence(
        title="Fictional offline example",
        url="https://rbi.org.in/offline-fixture-only",
        publisher="Reserve Bank of India",
        source_type="primary",
        published_at="2026-10-09",
        retrieved_at=instant,
        stance=stance,
        excerpt="OFFLINE FICTIONAL FIXTURE: This example claim is contradicted. Do not send OTP for bank account KYC.",
        excerpt_provenance="fetched_page",
        authority_basis="Offline fixture for tests only",
        directly_relevant=True,
        relevance_score=1,
    )
    claim = ClaimResult(
        claim_text=text,
        original_span=text,
        entities=[],
        dates=[],
        qualifiers=[],
        normalized_claim=text,
        lexical_hash="fixture",
        verdict=verdict,
        grounded_explanation="Fictional offline assessment",
        explanation="Fixture",
        short_summary="Fixture",
        evidence=[evidence],
        risk=risk_for(text),
        temporal_context=TemporalContext(),
        original_context=OriginalContext(),
        limitations=[],
        next_step="Review sources.",
        checked_at=instant,
    )
    return VerificationResult(
        status="completed",
        input=ExtractionResult(text=text, detected_language=language, input_type="text"),
        claims=[claim],
        summary="Fictional offline fixture",
        checked_at=instant,
        response_language=language,
        audience="adult",
    )


def demo() -> dict:
    instant = datetime(2026, 10, 11, 8, tzinfo=UTC)
    config = AlertsSettings(
        _env_file=None,
        ingest_token=secrets.token_urlsafe(32),
        admin_token=secrets.token_urlsafe(32),
        pseudonym_secret=secrets.token_urlsafe(32),
    )
    engine = AlertEngine(config, clock=lambda: instant)
    sources = [str(uuid4()) for _ in range(3)]
    for source, language in zip(sources, SAMPLE_CLAIMS, strict=True):
        engine.ingest(
            IngestRequest(
                consent=True,
                submission_id=uuid4(),
                source_token=source,
                verification=fixture_record(instant, language),
            )
        )
    cluster = engine.clusters()[0]
    drafts = []
    for language in SAMPLE_CLAIMS:
        draft = engine.create_draft(cluster.cluster_id, language)
        engine.submit(draft.alert_id, draft.content_version)
        reviewed = engine.approve(
            draft.alert_id,
            ApproveRequest(
                expected_version=draft.content_version, reviewer_id=uuid4(), evidence_reviewed=True
            ),
        )
        drafts.append(
            {
                "draft": reviewed.model_dump(mode="json"),
                "manual_export": engine.export(draft.alert_id).model_dump(mode="json"),
            }
        )
    return {
        "demo_only": True,
        "review": "SIMULATED HUMAN APPROVAL; fictional evidence, do not publish",
        "live_gemini_calls": 0,
        "live_tavily_calls": 0,
        "cluster": cluster.model_dump(mode="json"),
        "languages": drafts,
        "withdrawn_observations": engine.withdraw(sources[0]),
        "drafts_after_withdrawal": len(engine.drafts()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, help="Write UTF-8 demo JSON instead of console output."
    )
    args = parser.parse_args()
    data = demo()
    if args.output:
        args.output.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    else:
        print(json.dumps(data, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
