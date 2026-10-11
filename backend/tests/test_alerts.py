import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.alerts_app import MAX_BODY_BYTES, AlertsBoundary, create_alerts_app
from app.errors import AppError
from app.services.alerts.clustering import Matcher
from app.services.alerts.engine import AlertEngine
from app.services.alerts.models import ApproveRequest, EditRequest, IngestRequest, RejectRequest
from app.services.alerts.privacy import protected_anchors, redact
from app.services.alerts.repository import MemoryAlertRepository
from app.services.alerts.settings import AlertsSettings
from scripts.demo_alerts import SAMPLE_CLAIMS, demo, fixture_record

INSTANT = datetime(2026, 10, 11, 8, tzinfo=UTC)


@pytest.fixture(autouse=True)
def block_live_transport(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Alert regression tests must never use a live HTTP transport.")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


@pytest.fixture
def config():
    return AlertsSettings(
        _env_file=None, ingest_token="i" * 40, admin_token="a" * 40, pseudonym_secret="p" * 40
    )


@pytest.fixture
def clock():
    return [INSTANT]


@pytest.fixture
def engine(config, clock):
    return AlertEngine(config, clock=lambda: clock[0])


def ingest(engine, *, source=None, language="en", record=None, submission_id=None, text=None):
    return engine.ingest(
        IngestRequest(
            consent=True,
            submission_id=submission_id or uuid4(),
            source_token=source or str(uuid4()),
            verification=record or fixture_record(engine.clock(), language, text=text),
        )
    )


def activate(engine):
    for language in SAMPLE_CLAIMS:
        ingest(engine, language=language)
    return engine.drafts()[0]


def approve(engine, draft):
    engine.submit(draft.alert_id, draft.content_version)
    return engine.approve(
        draft.alert_id,
        ApproveRequest(
            expected_version=draft.content_version, reviewer_id=uuid4(), evidence_reviewed=True
        ),
    )


def fails(code, operation):
    with pytest.raises(AppError) as exc:
        operation()
    assert exc.value.code == code


def test_three_languages_form_one_cluster_and_localized_drafts(engine):
    draft = activate(engine)
    cluster = engine.clusters()[0]
    assert len(engine.clusters()) == 1
    assert cluster.unique_submission_count == 3
    assert cluster.trend.recurring and cluster.trend.high_severity_indicators
    assert cluster.status == "review_available"
    assert draft.evidence_based_status == "claim_contradicted"
    assert "does not establish criminal fraud" in draft.explanation
    assert "not population-wide" in cluster.trend.scope
    for lang in SAMPLE_CLAIMS:
        localized = engine.create_draft(cluster.cluster_id, lang)
        assert localized.language_content_status == "ready"
        assert localized.claim_summary == SAMPLE_CLAIMS[lang]


def test_repeat_source_and_exact_id_are_not_independent(engine):
    source = str(uuid4())
    record = fixture_record(INSTANT)
    submission_id = uuid4()
    first = ingest(engine, source=source, record=record, submission_id=submission_id)
    repeated = ingest(engine, source=source, record=record, submission_id=submission_id)
    for _ in range(4):
        ingest(engine, source=source)
    assert not first.duplicate and repeated.duplicate
    assert engine.clusters()[0].unique_submission_count == 1
    assert not engine.drafts()


def test_idempotency_conflicts_include_provider_quality_changes(engine):
    source, submission = str(uuid4()), uuid4()
    record = fixture_record(INSTANT)
    ingest(engine, source=source, record=record, submission_id=submission)
    record.warnings = ["llm_provider_error"]
    fails(
        "alerts_submission_conflict",
        lambda: ingest(engine, source=source, record=record, submission_id=submission),
    )
    fails(
        "alerts_submission_conflict",
        lambda: ingest(engine, record=record, submission_id=submission),
    )


@pytest.mark.parametrize(
    "left,right",
    [
        ("Send OTP to verify bank account KYC", "Pay bank account KYC processing fee"),
        ("Send OTP to verify bank account KYC", "Do not send OTP to verify bank account KYC"),
        ("Pay bank account KYC fee 5000", "Pay bank account KYC fee 7000"),
        ("Government scholarship approved", "Government pension approved"),
    ],
)
def test_unrelated_or_opposite_claims_do_not_cluster(engine, left, right):
    ingest(engine, text=left)
    ingest(engine, text=right)
    assert len(engine.clusters()) == 2


def test_entity_guard(engine):
    for entity in ("Example Bank", "Another Bank"):
        record = fixture_record(INSTANT)
        record.claims[0].entities = [entity]
        ingest(engine, record=record)
    assert len(engine.clusters()) == 2
    with engine.repository.transaction() as state:
        assert "Example Bank" not in repr(state)


def test_threshold_not_met(engine):
    result = ingest(engine)
    ingest(engine)
    assert not engine.drafts()
    assert result.deferred_reasons == ["trend_threshold_not_met"]
    fails("alerts_draft_deferred", lambda: engine.create_draft(result.cluster_ids[0], "en"))


def test_baseline_growth_and_old_evidence_do_not_block_current_cohort(engine, clock):
    clock[0] = INSTANT - timedelta(days=3)
    ingest(engine)
    clock[0] = INSTANT
    activate(engine)
    trend = engine.clusters()[0].trend
    assert trend.increasing and trend.baseline_daily_average == 0.143
    assert engine.drafts()[0].last_verified_at == INSTANT


@pytest.mark.parametrize(
    "failure",
    [
        "none",
        "search_excerpt",
        "irrelevant",
        "unknown_domain",
        "lookalike",
        "incomplete",
        "future",
        "stale",
        "low_relevance",
        "private_url",
    ],
)
def test_insufficient_evidence_suppresses_high_risk_alert(engine, failure):
    for _ in range(3):
        record = fixture_record(INSTANT, text="Urgent! Send OTP and PAN and pay immediately.")
        e = record.claims[0].evidence[0]
        if failure == "none":
            record.claims[0].evidence = []
        elif failure == "search_excerpt":
            e.excerpt_provenance = "search_excerpt"
        elif failure == "irrelevant":
            e.directly_relevant = False
        elif failure == "unknown_domain":
            e.url = "https://example.org/fact"
        elif failure == "lookalike":
            e.url = "https://rbi.org.in.attacker.example/fact"
        elif failure == "incomplete":
            e.authority_basis += " incomplete_content:truncated"
        elif failure == "future":
            e.retrieved_at += timedelta(seconds=1)
        elif failure == "stale":
            e.retrieved_at -= timedelta(hours=49)
        elif failure == "low_relevance":
            e.relevance_score = 0.2
        elif failure == "private_url":
            e.url = "https://rbi.org.in/fact?phone=9876543210"
        ingest(engine, record=record)
    assert engine.clusters()[0].trend.high_severity_indicators
    assert engine.clusters()[0].status == "deferred"
    assert not engine.drafts()


@pytest.mark.parametrize(
    "error", ["llm_provider_error", "search_provider_error", "source_page_unavailable"]
)
def test_provider_errors_never_become_public_warning(engine, error):
    for _ in range(3):
        record = fixture_record(INSTANT)
        record.warnings = [error]
        result = ingest(engine, record=record)
    assert not engine.drafts()
    assert "technical_verification_failure" in result.deferred_reasons


@pytest.mark.parametrize(
    "verdict,stance,expected",
    [
        ("verified", "supports", None),
        ("false", "supports", None),
        ("unconfirmed", "contradicts", None),
        ("unconfirmed", "context", "suspicious_indicators"),
        ("partially_true", "context", "claim_needs_context"),
        ("misleading_context", "context", "claim_needs_context"),
        ("outdated", "context", None),
    ],
)
def test_all_six_verdicts_have_evidence_gates(engine, verdict, stance, expected):
    for _ in range(3):
        ingest(engine, record=fixture_record(INSTANT, verdict=verdict, stance=stance))
    assert (engine.drafts()[0].evidence_based_status if engine.drafts() else None) == expected


def test_outdated_requires_distinct_source_event_dates(engine):
    for _ in range(3):
        record = fixture_record(INSTANT, verdict="outdated", stance="context")
        e = record.claims[0].evidence[0]
        e.excerpt = "OFFLINE FIXTURE: The previous event was on 2020-01-01."
        other = e.model_copy(deep=True)
        other.evidence_id, other.url = uuid4(), "https://pib.gov.in/offline-fixture-only"
        other.excerpt = "OFFLINE FIXTURE: The new event was on 2026-01-01."
        record.claims[0].evidence.append(other)
        record.claims[0].temporal_context.relevant_source_dates = ["2020-01-01", "2026-01-01"]
        ingest(engine, record=record)
    assert engine.drafts()[0].evidence_based_status == "claim_needs_context"


def test_contradictory_findings_preserved_even_with_same_evidence_id(engine):
    for _ in range(3):
        record = fixture_record(INSTANT)
        other = record.claims[0].evidence[0].model_copy(deep=True)
        other.stance = "supports"
        other.excerpt = "OFFLINE FIXTURE: A contradictory statement."
        record.claims[0].evidence.append(other)
        ingest(engine, record=record)
    assert {e.stance for e in engine.clusters()[0].evidence_references} == {
        "supports",
        "contradicts",
    }
    assert not engine.drafts()


def test_verified_observation_suppresses_cluster_and_existing_export(engine):
    draft = approve(engine, activate(engine))
    ingest(engine, record=fixture_record(INSTANT, verdict="verified", stance="supports"))
    fails("alerts_export_forbidden", lambda: engine.export(draft.alert_id))
    assert engine.drafts()[0].approval_status == "expired"


def test_approval_requires_review_and_unreviewed_export_is_forbidden(engine):
    draft = activate(engine)
    request = ApproveRequest(expected_version=1, reviewer_id=uuid4(), evidence_reviewed=True)
    fails("alerts_export_forbidden", lambda: engine.export(draft.alert_id))
    fails("alerts_review_required", lambda: engine.approve(draft.alert_id, request))
    approved = approve(engine, draft)
    assert (
        approved.review.content_version == 1
        and approved.review.evidence_review_status == "reviewed"
    )
    exported = engine.export(draft.alert_id)
    assert exported.mode == "manual_copy_only"
    assert "https://rbi.org.in/offline-fixture-only" in exported.channel_text
    assert exported.reviewer_id == approved.review.reviewer_id


def test_new_evidence_or_sample_membership_revokes_approval(engine):
    approved = approve(engine, activate(engine))
    ingest(engine)
    current = engine.drafts()[0]
    assert current.alert_id == approved.alert_id and current.content_version == 2
    assert current.approval_status == "pending_review" and current.review is None
    fails("alerts_export_forbidden", lambda: engine.export(current.alert_id))
    fails("alerts_version_conflict", lambda: approve(engine, approved))
    assert approve(engine, current).review.content_version == 2


def test_edit_requires_reapproval_and_optimistic_version(engine):
    draft = approve(engine, activate(engine))
    updated = engine.edit(
        draft.alert_id,
        EditRequest(
            expected_version=1,
            title=draft.title,
            claim_summary=draft.claim_summary,
            explanation="Review the original source before forwarding.",
        ),
    )
    assert updated.content_version == 2 and updated.approval_status == "pending_review"
    fails("alerts_export_forbidden", lambda: engine.export(updated.alert_id))
    assert len(approve(engine, updated).review_history) == 2


def test_rejection_is_terminal_and_reason_is_retained(engine):
    draft = activate(engine)
    rejected = engine.reject(
        draft.alert_id,
        RejectRequest(expected_version=1, reviewer_id=uuid4(), reason="incorrect_content"),
    )
    assert rejected.review.rejection_reason == "incorrect_content"
    ingest(engine)
    assert (
        next(d for d in engine.drafts() if d.alert_id == draft.alert_id).approval_status
        == "rejected"
    )
    fails("alerts_not_reviewable", lambda: engine.submit(draft.alert_id, 1))
    fails("alerts_export_forbidden", lambda: engine.export(draft.alert_id))


def test_stale_evidence_and_draft_expiry_block_export(engine, clock):
    draft = approve(engine, activate(engine))
    clock[0] += timedelta(hours=13)
    assert engine.drafts()[0].approval_status == "expired"
    fails("alerts_export_forbidden", lambda: engine.export(draft.alert_id))
    fresh = engine.create_draft(draft.cluster_id, "en")
    approve(engine, fresh)
    clock[0] += timedelta(hours=36)
    fails("alerts_export_forbidden", lambda: engine.export(fresh.alert_id))
    fails("alerts_draft_deferred", lambda: engine.create_draft(draft.cluster_id, "en"))


def test_missing_translation_is_explicit_and_human_review_is_required(engine):
    for _ in range(3):
        ingest(engine)
    english = engine.drafts()[0]
    hindi = engine.create_draft(english.cluster_id, "hi")
    assert hindi.claim_summary is None and hindi.language_content_status == "pending_translation"
    fails("alerts_translation_pending", lambda: engine.submit(hindi.alert_id, 1))
    edited = engine.edit(
        hindi.alert_id,
        EditRequest(
            expected_version=1,
            title=hindi.title,
            claim_summary=SAMPLE_CLAIMS["hi"],
            explanation=hindi.explanation,
            translation_reviewed=True,
        ),
    )
    assert edited.language_content_status == "ready"
    assert approve(engine, edited).approval_status == "approved"


@pytest.mark.parametrize(
    "translation", [None, "OTP: 123456", " ", RuntimeError("private provider response")]
)
def test_optional_translation_failure_never_fabricates_text(config, translation):
    class Translator:
        def translate(self, *args):
            if isinstance(translation, Exception):
                raise translation
            return translation

    engine = AlertEngine(config, clock=lambda: INSTANT, translator=Translator())
    for _ in range(3):
        ingest(engine)
    translated = engine.create_draft(engine.clusters()[0].cluster_id, "mr")
    assert (
        translated.language_content_status == "pending_translation"
        and translated.claim_summary is None
    )


@pytest.mark.parametrize(
    "secret",
    [
        "9876543210",
        "+91 98765 43210",
        "1234 5678 9012",
        "ABCDE1234F",
        "password is hunter2",
        "OTP: 123456",
        "१२३४५६",
        "me@example.com",
        "person@okaxis",
        "SBIN0123456",
        "4111 1111 1111 1111",
        "https://attacker.example/private",
        "Mr. Anil Kumar",
    ],
)
def test_sensitive_content_redacted_before_storage(engine, secret):
    raw = "Send OTP to verify bank account KYC. " + secret
    record = fixture_record(INSTANT, text=raw)
    record.input.text += " PRIVATE CHAT TRAILING MESSAGE"
    record.claims[0].evidence[0].excerpt += " " + secret
    ingest(engine, record=record)
    with engine.repository.transaction() as state:
        stored = repr(state)
        assert secret not in stored and "PRIVATE CHAT TRAILING MESSAGE" not in stored
    assert "[REDACTED]" in engine.clusters()[0].canonical_claim


def test_sensitive_edits_and_blank_edits_rejected(engine):
    draft = activate(engine)
    for text in ("OTP 123456", "   "):
        fails(
            "alerts_sensitive_content",
            lambda text=text: engine.edit(
                draft.alert_id,
                EditRequest(
                    expected_version=1,
                    title=text,
                    claim_summary=draft.claim_summary,
                    explanation=draft.explanation,
                ),
            ),
        )


def test_retention_and_source_withdrawal_delete_private_derivatives(engine, clock):
    source = str(uuid4())
    ingest(engine, source=source)
    ingest(engine)
    ingest(engine)
    assert engine.withdraw(source) == 1
    assert not engine.drafts() and engine.clusters()[0].unique_submission_count == 2
    assert engine.withdraw(source) == 0
    clock[0] += timedelta(days=15)
    assert not engine.clusters() and not engine.drafts()
    with engine.repository.transaction() as state:
        assert not state.observations and not state.receipts


def test_old_replay_preserves_first_seen_and_fresher_evidence(engine, clock):
    source = str(uuid4())
    ingest(engine, source=source)
    clock[0] += timedelta(hours=1)
    record = fixture_record(INSTANT - timedelta(hours=1))
    ingest(engine, source=source, record=record)
    with engine.repository.transaction() as state:
        observation = next(iter(state.observations.values()))
        assert observation.checked_at == INSTANT and observation.received_at == INSTANT
        assert observation.last_seen_at == clock[0]


@pytest.mark.parametrize("value", [False, 1, "true", None])
def test_consent_must_be_explicit_boolean(value):
    with pytest.raises(ValidationError):
        IngestRequest(
            consent=value,
            submission_id=uuid4(),
            source_token=str(uuid4()),
            verification=fixture_record(INSTANT),
        )


def test_no_naive_or_future_check_dates_or_unanchored_spans(engine):
    for change in ("naive", "future", "span", "empty_span"):
        record = fixture_record(INSTANT)
        if change == "naive":
            record.claims[0].evidence[0].retrieved_at = INSTANT.replace(tzinfo=None)
        elif change == "future":
            record.checked_at += timedelta(seconds=1)
        else:
            record.claims[0].original_span = "invented" if change == "span" else ""
        with pytest.raises(AppError):
            ingest(engine, record=record)
    assert not engine.clusters()


def test_repository_rollback_and_copy_isolation():
    repo = MemoryAlertRepository()
    with pytest.raises(RuntimeError), repo.transaction() as state:
        state.receipts[uuid4()] = None
        raise RuntimeError("rollback")
    with repo.transaction() as state:
        assert not state.receipts
    state.receipts[uuid4()] = None
    with repo.transaction() as state:
        assert not state.receipts


def test_optional_embeddings_have_safety_guards():
    class Embedder:
        def encode(self, texts):
            return [[1.0, 0.0], [1.0, 0.0]]

    matcher = Matcher(Embedder())
    assert matcher.similar(
        "Send OTP to verify bank account KYC quickly",
        "Send OTP to verify bank account KYC safely",
        [],
        [],
    )
    assert not matcher.similar(
        "Send OTP to verify bank account KYC", "Send OTP to verify a prize lottery account", [], []
    )
    assert not matcher.similar(
        "Pay bank account KYC fee 500", "Pay bank account KYC fee 700", [], []
    )
    assert not matcher.similar(
        "Send OTP to verify bank account KYC", "Never send OTP to verify bank account KYC", [], []
    )


def test_numeric_anchor_normalization_without_storing_values():
    assert protected_anchors("5000", [], "secret") == protected_anchors("५०००", [], "secret")
    assert "5000" not in repr(protected_anchors("5000", [], "secret"))
    assert redact("Event on 2020-01-01")[0] == "Event on 2020-01-01"


def test_api_auth_roles_and_error_privacy(config, engine):
    with TestClient(create_alerts_app(config, engine)) as client:
        assert client.get("/api/alerts/clusters").status_code == 401
        assert (
            client.get(
                "/api/alerts/clusters", headers={"Authorization": "Bearer " + "i" * 40}
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/alerts/ingest", json={}, headers={"Authorization": "Bearer " + "a" * 40}
            ).status_code
            == 403
        )
        request = IngestRequest(
            consent=True,
            submission_id=uuid4(),
            source_token=str(uuid4()),
            verification=fixture_record(INSTANT),
        )
        payload = request.model_dump(mode="json")
        payload["source_token"] = request.source_token.get_secret_value()
        response = client.post(
            "/api/alerts/ingest", json=payload, headers={"Authorization": "Bearer " + "i" * 40}
        )
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        payload["source_token"] = "9876543210"
        response = client.post(
            "/api/alerts/ingest", json=payload, headers={"Authorization": "Bearer " + "i" * 40}
        )
        assert response.status_code == 422
        assert "9876543210" not in response.text and "input" not in response.text
        assert (
            client.post("/api/alerts/ingest", content="x" * (MAX_BODY_BYTES + 1)).status_code == 413
        )


def test_unconfigured_routes_fail_closed():
    with TestClient(create_alerts_app(AlertsSettings(_env_file=None))) as client:
        assert client.get("/api/alerts/clusters").status_code == 503
        assert client.get("/health").json()["publishing"] is False


def test_configuration_requires_strong_distinct_secrets():
    with pytest.raises(ValidationError):
        AlertsSettings(_env_file=None, ingest_token="short")
    with pytest.raises(ValidationError):
        AlertsSettings(
            _env_file=None, ingest_token="a" * 40, admin_token="a" * 40, pseudonym_secret="a" * 40
        )


def test_api_review_workflow_and_withdrawal(config, engine):
    draft = activate(engine)
    headers = {"Authorization": "Bearer " + "a" * 40}
    with TestClient(create_alerts_app(config, engine)) as client:
        assert (
            client.get(f"/api/alerts/{draft.alert_id}/export", headers=headers).status_code == 409
        )
        assert (
            client.post(
                f"/api/alerts/{draft.alert_id}/submit",
                headers=headers,
                json={"expected_version": 1},
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/alerts/{draft.alert_id}/approve",
                headers=headers,
                json={
                    "expected_version": 1,
                    "reviewer_id": str(uuid4()),
                    "evidence_reviewed": True,
                },
            ).status_code
            == 200
        )
        assert (
            client.get(f"/api/alerts/{draft.alert_id}/export", headers=headers).status_code == 200
        )
        assert (
            client.get("/api/alerts/drafts", headers=headers).json()[0]["approval_status"]
            == "approved"
        )
        assert client.get("/api/alerts/clusters", headers=headers).status_code == 200


def test_local_demo_is_offline_and_never_publishes():
    report = demo()
    assert report["live_gemini_calls"] == report["live_tavily_calls"] == 0
    assert report["cluster"]["unique_submission_count"] == 3
    assert len(report["languages"]) == 3 and report["drafts_after_withdrawal"] == 0
    assert "source_hash" not in json.dumps(report)


def test_window_membership_change_requires_re_review(config, clock):
    config.draft_ttl_hours = 48
    engine = AlertEngine(config, clock=lambda: clock[0])
    clock[0] = INSTANT - timedelta(hours=23)
    ingest(engine)
    clock[0] = INSTANT
    for _ in range(3):
        ingest(engine)
    approved = approve(engine, engine.drafts()[0])
    clock[0] += timedelta(hours=2)
    fails("alerts_export_forbidden", lambda: engine.export(approved.alert_id))
    fresh = engine.create_draft(approved.cluster_id, "en")
    assert fresh.content_version == approved.content_version + 1
    assert "3 independent consented submissions" in fresh.scope_note
    assert fresh.approval_status == "pending_review"


def test_purge_deletes_derivative_drafts_of_expired_sources(config, clock):
    engine = AlertEngine(config, clock=lambda: clock[0])
    old = INSTANT - timedelta(days=13, hours=23)
    clock[0] = old
    ingest(engine)
    clock[0] = INSTANT
    for _ in range(3):
        ingest(engine)
    assert len(engine.drafts()) == 1
    clock[0] += timedelta(hours=2)
    assert engine.purge() == 1
    assert not engine.drafts()
    assert engine.clusters()[0].unique_submission_count == 3


def test_unchanged_replay_does_not_revoke_approval(engine):
    source = str(uuid4())
    record = fixture_record(INSTANT)
    ingest(engine, source=source, record=record)
    ingest(engine)
    ingest(engine)
    approved = approve(engine, engine.drafts()[0])
    ingest(engine, source=source, record=record)
    assert engine.drafts()[0].content_version == 1
    assert engine.export(approved.alert_id).content_version == 1


def test_storage_capacity_fails_atomically(config):
    config.max_clusters = 10
    engine = AlertEngine(config, clock=lambda: INSTANT)
    for index in range(10):
        ingest(engine, text=f"Unrelated fixture claim number {index}")
    fails("alerts_capacity", lambda: ingest(engine, text="A completely different fixture claim"))
    assert len(engine.clusters()) == 10
    with engine.repository.transaction() as state:
        assert len(state.observations) == len(state.receipts) == 10


def test_api_generic_failure_sanitizes_diagnostics(config, engine, monkeypatch, caplog):
    def failure():
        raise RuntimeError("9876543210 secret-provider-key")

    monkeypatch.setattr(engine, "clusters", failure)
    with TestClient(create_alerts_app(config, engine), raise_server_exceptions=True) as client:
        response = client.get(
            "/api/alerts/clusters", headers={"Authorization": "Bearer " + "a" * 40}
        )
        assert response.status_code == 500
        assert "9876543210" not in response.text + caplog.text
        assert "secret-provider-key" not in response.text + caplog.text
        assert "RuntimeError" in caplog.text


def test_api_withdraw_and_purge_roles(config, engine):
    source = str(uuid4())
    ingest(engine, source=source)
    with TestClient(create_alerts_app(config, engine)) as client:
        admin = {"Authorization": "Bearer " + "a" * 40}
        producer = {"Authorization": "Bearer " + "i" * 40}
        assert (
            client.post(
                "/api/alerts/withdraw", json={"source_token": source}, headers=admin
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/alerts/withdraw", json={"source_token": source}, headers=producer
            ).json()["deleted_observations"]
            == 1
        )
        assert client.post("/api/alerts/purge", headers=producer).status_code == 403
        assert client.post("/api/alerts/purge", headers=admin).status_code == 200


def test_approval_requires_explicit_boolean_evidence_review():
    with pytest.raises(ValidationError):
        ApproveRequest(expected_version=1, reviewer_id=uuid4(), evidence_reviewed=1)


def test_unicode_citation_and_ssrf_private_url_rejected(engine):
    for url in (
        "http://127.0.0.1/private",
        "https://user:password@rbi.org.in/fact",
        "https://rbi.org.in/person/9876543210",
    ):
        record = fixture_record(INSTANT)
        record.claims[0].evidence[0].url = url
        result = ingest(engine, record=record)
        assert result.cluster_ids
    assert not engine.clusters()[0].evidence_references


def test_source_uuid_aliases_cannot_inflate_independence(engine):
    source = str(uuid4())
    ingest(engine, source=source)
    ingest(engine, source=source.upper())
    ingest(engine, source="{" + source + "}")
    assert engine.clusters()[0].unique_submission_count == 1
    assert engine.withdraw(source.upper()) == 1


def test_unknown_language_metadata_does_not_store_private_strings(engine):
    record = fixture_record(INSTANT)
    record.input.detected_language = "private 9876543210"
    ingest(engine, record=record)
    assert engine.clusters()[0].similar_observed_submissions[0].language == "und"
    with engine.repository.transaction() as state:
        assert "9876543210" not in repr(state)


def test_separate_openapi_matches_snapshot(config):
    target = Path(__file__).resolve().parents[2] / "docs" / "scam-alert-openapi.json"
    assert (
        target.read_text(encoding="utf-8")
        == json.dumps(create_alerts_app(config).openapi(), ensure_ascii=False, indent=2) + "\n"
    )


@pytest.mark.parametrize(
    "secret", ["987-654-3210", "9876 543 210", "my name is Rahul Patil", "balance is Rs 12"]
)
def test_additional_private_formats_are_redacted(secret):
    cleaned, changed = redact(secret)
    assert changed and secret not in cleaned


@pytest.mark.parametrize(
    "failure,expected", [("streamed_oversize", 413), ("disconnect", 400), ("timeout", 408)]
)
async def test_streamed_body_boundary(failure, expected, monkeypatch):
    import asyncio

    messages = []
    chunks = [
        {"type": "http.request", "body": b"x" * (MAX_BODY_BYTES // 2), "more_body": True},
        {"type": "http.request", "body": b"x" * (MAX_BODY_BYTES // 2 + 1), "more_body": False},
    ]

    async def receive():
        if failure == "disconnect":
            return {"type": "http.disconnect"}
        return chunks.pop(0)

    async def send(message):
        messages.append(message)

    async def application(*args):
        pytest.fail("Invalid body must not reach routes.")

    if failure == "timeout":

        async def timeout(awaitable, **kwargs):
            awaitable.close()
            raise TimeoutError("private secret request content")

        monkeypatch.setattr(asyncio, "wait_for", timeout)
    await AlertsBoundary(application)({"type": "http", "method": "POST"}, receive, send)
    assert messages[0]["status"] == expected
    assert "private secret" not in repr(messages)


def test_receipt_replay_remains_idempotent_after_evidence_ages(engine, clock):
    source, submission = str(uuid4()), uuid4()
    record = fixture_record(INSTANT)
    ingest(engine, source=source, submission_id=submission, record=record)
    clock[0] += timedelta(hours=49)
    result = ingest(engine, source=source, submission_id=submission, record=record)
    assert result.duplicate and not engine.drafts()


def test_service_boundary_enforces_consent_and_review_even_for_constructed_models(engine):
    record = IngestRequest.model_construct(
        consent=False,
        submission_id=uuid4(),
        source_token=None,
        verification=fixture_record(INSTANT),
    )
    fails("alerts_consent_required", lambda: engine.ingest(record))
    draft = activate(engine)
    engine.submit(draft.alert_id, draft.content_version)
    request = ApproveRequest.model_construct(
        expected_version=1, reviewer_id=uuid4(), evidence_reviewed=False
    )
    fails("alerts_review_required", lambda: engine.approve(draft.alert_id, request))
    fails("alerts_export_forbidden", lambda: engine.export(draft.alert_id))


@pytest.mark.parametrize("text", ["Don't", "Won't", "Can't", "Doesn’t"])
def test_negation_contractions_do_not_merge_with_positive_claim(engine, text):
    ingest(engine, text="Send OTP to verify bank account KYC")
    ingest(engine, text=text + " send OTP to verify bank account KYC")
    assert len(engine.clusters()) == 2


def test_invalid_environment_startup_does_not_echo_secrets(monkeypatch):
    import traceback

    monkeypatch.setenv("ALERTS_INGEST_TOKEN", "private-secret-invalid-length")
    with pytest.raises(RuntimeError) as exc:
        create_alerts_app()
    assert "private-secret-invalid-length" not in "".join(traceback.format_exception(exc.value))


@pytest.mark.parametrize("score", [float("nan"), float("inf"), 2.0])
def test_nonfinite_or_out_of_range_evidence_scores_cannot_support_draft(engine, score):
    for _ in range(3):
        record = fixture_record(INSTANT)
        record.claims[0].evidence[0].relevance_score = score
        ingest(engine, record=record)
    assert not engine.drafts()


def test_replay_detects_changed_evidence_quality(engine):
    source, submission = str(uuid4()), uuid4()
    record = fixture_record(INSTANT)
    ingest(engine, source=source, submission_id=submission, record=record)
    record.claims[0].evidence[0].directly_relevant = False
    fails(
        "alerts_submission_conflict",
        lambda: ingest(engine, source=source, submission_id=submission, record=record),
    )
