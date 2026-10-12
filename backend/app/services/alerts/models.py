from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field, SecretStr, field_validator

from app.schemas.models import Language, Model, Stance, Verdict, VerificationResult

ApprovalState = Literal["draft", "pending_review", "approved", "rejected", "expired"]
EvidenceStatus = Literal["claim_contradicted", "claim_needs_context", "suspicious_indicators"]
RejectionReason = Literal[
    "insufficient_evidence", "translation_needed", "incorrect_content", "other"
]


def opaque_source(value: SecretStr) -> SecretStr:
    try:
        token = UUID(value.get_secret_value())
        if token.version != 4:
            raise ValueError
    except ValueError:
        raise ValueError(
            "Use a random UUIDv4 source token, never a phone/chat identifier."
        ) from None
    return SecretStr(str(token))


class IngestRequest(Model):
    consent: Literal[True]
    submission_id: UUID
    source_token: SecretStr
    verification: VerificationResult

    @field_validator("consent", mode="before")
    @classmethod
    def explicit_consent(cls, value: object) -> object:
        if value is not True:
            raise ValueError("Explicit consent is required.")
        return value

    _opaque_source = field_validator("source_token")(opaque_source)


class WithdrawRequest(Model):
    source_token: SecretStr

    _opaque_source = field_validator("source_token")(opaque_source)


class EvidenceReference(Model):
    evidence_id: UUID
    url: str
    publisher: str
    excerpt: str
    stance: Stance
    retrieved_at: datetime
    published_at: str | None = None
    updated_at: str | None = None
    eligible: bool
    issues: list[str]


class Observation(Model):
    observation_id: UUID = Field(default_factory=uuid4)
    cluster_id: UUID
    source_hash: str
    claim_text: str
    language: str
    verdict: Verdict
    received_at: datetime
    last_seen_at: datetime
    checked_at: datetime
    technical_failure: bool
    warning_signs: list[str]
    evidence: list[EvidenceReference]
    privacy_redacted: bool
    entities: list[str]
    source_dates: list[str]


class ObservedClaim(Model):
    text: str
    language: str
    first_seen_at: datetime
    last_seen_at: datetime
    verdict: Verdict


class Trend(Model):
    independent_in_window: int
    baseline_daily_average: float
    increasing: bool
    recurring: bool
    high_severity_indicators: bool
    scope: str = "Consented retained submissions only; not population-wide WhatsApp activity."


class Cluster(Model):
    cluster_id: UUID = Field(default_factory=uuid4)
    canonical_claim: str
    first_observed_at: datetime
    last_observed_at: datetime
    unique_submission_count: int = 0
    similar_observed_submissions: list[ObservedClaim] = Field(default_factory=list)
    evidence_references: list[EvidenceReference] = Field(default_factory=list)
    status: Literal["observing", "recurring", "increasing", "deferred", "review_available"] = (
        "observing"
    )
    trend: Trend | None = None


class Review(Model):
    reviewer_id: UUID
    reviewed_at: datetime
    content_version: int
    content_hash: str
    evidence_fingerprint: str
    evidence_review_status: Literal["reviewed", "not_reviewed"]
    action: Literal["approved", "rejected"]
    rejection_reason: RejectionReason | None = None


class AlertDraft(Model):
    alert_id: UUID = Field(default_factory=uuid4)
    cluster_id: UUID
    title: str
    claim_summary: str | None
    evidence_based_status: EvidenceStatus
    explanation: str
    scam_warning_signs: list[str]
    recommended_user_actions: list[str]
    authoritative_source_links: list[str]
    language: Language
    language_content_status: Literal["ready", "pending_translation"]
    created_at: datetime
    last_verified_at: datetime
    expires_at: datetime
    approval_status: ApprovalState = "draft"
    content_version: int = 1
    evidence_fingerprint: str
    review: Review | None = None
    review_history: list[Review] = Field(default_factory=list)
    scope_note: str


class VersionRequest(Model):
    expected_version: int = Field(ge=1)


class ApproveRequest(VersionRequest):
    reviewer_id: UUID
    evidence_reviewed: Literal[True]

    @field_validator("evidence_reviewed", mode="before")
    @classmethod
    def explicit_review(cls, value: object) -> object:
        if value is not True:
            raise ValueError("Explicit evidence review is required.")
        return value


class RejectRequest(VersionRequest):
    reviewer_id: UUID
    reason: RejectionReason


class DraftRequest(Model):
    language: Language = "en"


class EditRequest(VersionRequest):
    title: str = Field(min_length=1, max_length=160)
    claim_summary: str = Field(min_length=1, max_length=1200)
    explanation: str = Field(min_length=1, max_length=1800)
    translation_reviewed: bool = False


class IngestResponse(Model):
    submission_id: UUID
    duplicate: bool
    cluster_ids: list[UUID]
    draft_ids: list[UUID]
    deferred_reasons: list[str]


class ExportPayload(Model):
    alert_id: UUID
    content_version: int
    language: Language
    channel_text: str
    approved_at: datetime
    reviewer_id: UUID
    expires_at: datetime
    mode: Literal["manual_copy_only"] = "manual_copy_only"
