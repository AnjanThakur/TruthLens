from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

Language = Literal["en", "hi", "mr"]
Audience = Literal["child", "teen", "adult", "senior"]
Verdict = Literal[
    "verified", "false", "partially_true", "outdated", "misleading_context", "unconfirmed"
]
Stance = Literal["supports", "contradicts", "context", "neutral", "unclear"]
InputType = Literal["text", "image", "audio", "pdf", "url"]
SourceType = Literal["primary", "secondary", "fact_check", "other"]
Provenance = Literal["fetched_page", "search_excerpt", "fact_check_api"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VerifyRequest(Model):
    text: str = Field(min_length=1, max_length=50000)
    input_language: Literal["auto", "en", "hi", "mr"] = "auto"
    response_language: Language = "en"
    audience: Audience = "adult"
    jurisdiction: str = Field(default="IN", pattern=r"^[A-Z]{2}$")
    input_type: InputType = "text"

    @field_validator("text")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Enter some text to check.")
        return value


class URLRequest(Model):
    url: str = Field(min_length=1, max_length=2048)


class ExtractionResult(Model):
    text: str
    detected_language: str
    input_type: InputType
    warnings: list[str] = Field(default_factory=list)
    extraction_details: dict[str, Any] = Field(default_factory=dict)


class AtomicClaim(Model):
    claim_text: str = Field(min_length=1, max_length=1200)
    original_span: str = Field(min_length=1, max_length=3000)
    entities: list[str] = Field(max_length=12)
    dates: list[str] = Field(max_length=6)
    qualifiers: list[str] = Field(max_length=8)
    queries: list[str] = Field(min_length=1, max_length=3)
    current_assertion: bool


class ClaimBatch(Model):
    detected_language: str
    claims: list[AtomicClaim] = Field(max_length=12)
    truncated: bool


class Evidence(Model):
    evidence_id: UUID = Field(default_factory=uuid4)
    title: str = Field(max_length=500)
    url: str = Field(max_length=2048)
    publisher: str = Field(max_length=300)
    source_type: SourceType
    published_at: str | None = Field(default=None, max_length=100)
    updated_at: str | None = Field(default=None, max_length=100)
    retrieved_at: datetime
    stance: Stance = "unclear"
    excerpt: str = Field(max_length=5000)
    excerpt_provenance: Provenance
    what_source_says: str = ""
    authority_basis: str
    relevance_score: float = 0
    directly_relevant: bool = False


class SourceAssessment(Model):
    evidence_id: str
    stance: Stance
    excerpt: str = Field(max_length=900)
    what_source_says: str = Field(max_length=700)
    directly_relevant: bool


class TemporalWitness(Model):
    evidence_id: str
    event_date: str
    role: Literal["historical", "current"]
    excerpt: str = Field(min_length=1, max_length=900)


class ComponentAssessment(Model):
    # Internal model output only; no change to the public FastAPI schemas.
    original_span: str = Field(min_length=1, max_length=1200)
    status: Literal["supported", "contradicted", "not_established"]
    evidence_ids: list[str] = Field(max_length=10)


class Decision(Model):
    verdict: Verdict
    explanation: str = Field(min_length=1, max_length=1800)
    short_summary: str = Field(max_length=350)
    key_points: list[str] = Field(max_length=5)
    assessments: list[SourceAssessment] = Field(max_length=10)
    decisive_evidence_ids: list[str] = Field(max_length=10)
    limitations: list[str] = Field(max_length=8)
    temporal_notes: str = Field(max_length=700)
    relevant_source_dates: list[str] = Field(max_length=10)
    context_evidence_ids: list[str] = Field(max_length=10)
    temporal_witnesses: list[TemporalWitness] = Field(max_length=6)
    component_assessments: list[ComponentAssessment] = Field(default_factory=list, max_length=8)


class RiskFactor(Model):
    rule: str
    weight: int
    description: str


class Risk(Model):
    score: int = Field(ge=0, le=100)
    level: Literal["low", "medium", "high"]
    factors: list[RiskFactor]
    is_probability: Literal[False] = False
    label: str = "Forwarding caution heuristic; not a probability that a claim is false."


class TemporalContext(Model):
    claim_date: str | None = None
    relevant_source_dates: list[str] = Field(default_factory=list)
    notes: str = ""


class OriginalContext(Model):
    status: Literal["not_checked", "inconclusive", "found"] = "not_checked"
    notes: str = ""
    source_urls: list[str] = Field(default_factory=list)


class ClaimResult(Model):
    claim_id: UUID = Field(default_factory=uuid4)
    claim_text: str = Field(max_length=1200)
    original_span: str = Field(max_length=3000)
    entities: list[str]
    dates: list[str]
    qualifiers: list[str]
    normalized_claim: str
    lexical_hash: str
    verdict: Verdict
    grounded_explanation: str = Field(max_length=1800)
    explanation: str = Field(max_length=2500)
    short_summary: str = Field(max_length=350)
    key_points: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(max_length=10)
    risk: Risk
    temporal_context: TemporalContext
    original_context: OriginalContext
    limitations: list[str]
    next_step: str
    checked_at: datetime


class VerificationResult(Model):
    verification_id: UUID = Field(default_factory=uuid4)
    status: Literal["completed", "partial", "no_checkable_claims"]
    input: ExtractionResult
    claims: list[ClaimResult] = Field(max_length=12)
    summary: str
    checked_at: datetime
    warnings: list[str] = Field(default_factory=list)
    response_language: Language
    audience: Audience


class ExplainRequest(Model):
    result: VerificationResult
    language: Language
    audience: Audience = "adult"


class Wording(Model):
    explanation: str = Field(min_length=1, max_length=1800)
    short_summary: str = Field(min_length=1, max_length=350)
    key_points: list[str] = Field(max_length=5)
    next_step: str = Field(max_length=350)


class ErrorDetail(Model):
    location: list[str | int]
    type: str


class ErrorBody(Model):
    code: str
    message: str
    request_id: UUID
    details: list[ErrorDetail] | None = None


class ErrorResponse(Model):
    error: ErrorBody


class HealthResponse(Model):
    status: Literal["ok"]
    capabilities: dict[str, Any]
    dependencies: dict[str, bool]
    limits: dict[str, int]
    notes: list[str]
