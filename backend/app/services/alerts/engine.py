import hashlib
import json
import re
from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import UUID

from pydantic import SecretStr

from app.errors import AppError
from app.schemas.models import Language
from app.services.alerts.clustering import Embedder, Matcher
from app.services.alerts.content import (
    TEXT,
    ClaimTranslator,
    channel_text,
    content_hash,
    fingerprint,
)
from app.services.alerts.evidence import evidence_status, references, utc_time
from app.services.alerts.models import (
    AlertDraft,
    ApproveRequest,
    Cluster,
    EditRequest,
    ExportPayload,
    IngestRequest,
    IngestResponse,
    Observation,
    ObservedClaim,
    RejectRequest,
    Review,
    Trend,
    opaque_source,
)
from app.services.alerts.privacy import protected_anchors, pseudonym, redact
from app.services.alerts.repository import (
    AlertRepository,
    AlertState,
    MemoryAlertRepository,
    Receipt,
)
from app.services.alerts.settings import AlertsSettings
from app.services.common import normalize, now
from app.services.verify.risk import RULES, risk_for


class AlertEngine:
    def __init__(
        self,
        settings: AlertsSettings,
        repository: AlertRepository | None = None,
        *,
        clock: Callable[[], datetime] = now,
        embedder: Embedder | None = None,
        translator: ClaimTranslator | None = None,
    ):
        self.settings = settings
        self.repository = repository or MemoryAlertRepository()
        self.clock, self.translator = clock, translator
        self.matcher = Matcher(embedder, settings.embedding_similarity)

    def _source(self, token: str) -> str:
        if not self.settings.configured:
            raise AppError(
                "alerts_not_configured",
                "Configure the alerts authentication and pseudonym secrets.",
                503,
            )
        token = opaque_source(SecretStr(token)).get_secret_value()
        return pseudonym(token, self.settings.pseudonym_secret.get_secret_value())

    def _observations(self, state: AlertState, cluster_id: UUID) -> list[Observation]:
        return [o for o in state.observations.values() if o.cluster_id == cluster_id]

    def _fingerprint(self, observations: list[Observation], instant: datetime) -> str:
        return fingerprint(
            observations, instant - timedelta(hours=self.settings.trend_window_hours)
        )

    def _rebuild(self, state: AlertState, cluster_id: UUID, instant: datetime) -> None:
        observations = self._observations(state, cluster_id)
        if not observations:
            state.clusters.pop(cluster_id, None)
            state.drafts = {
                key: draft for key, draft in state.drafts.items() if draft.cluster_id != cluster_id
            }
            return
        cluster = state.clusters[cluster_id]
        observations.sort(key=lambda o: o.received_at)
        cluster.canonical_claim = observations[0].claim_text
        cluster.first_observed_at = min(o.received_at for o in observations)
        cluster.last_observed_at = max(o.last_seen_at for o in observations)
        cluster.unique_submission_count = len({o.source_hash for o in observations})
        cluster.similar_observed_submissions = [
            ObservedClaim(
                text=o.claim_text,
                language=o.language,
                first_seen_at=o.received_at,
                last_seen_at=o.last_seen_at,
                verdict=o.verdict,
            )
            for o in observations[:50]
        ]
        cluster.evidence_references = list(
            {(e.url, e.stance, e.excerpt): e for o in observations for e in o.evidence}.values()
        )
        start = instant - timedelta(hours=self.settings.trend_window_hours)
        baseline_start = start - timedelta(days=self.settings.baseline_days)
        recent = len({o.source_hash for o in observations if start <= o.received_at <= instant})
        baseline = (
            len({o.source_hash for o in observations if baseline_start <= o.received_at < start})
            / self.settings.baseline_days
        )
        recurring = recent >= self.settings.min_independent_submissions
        increasing = (
            recurring
            and baseline > 0
            and recent
            >= baseline * (self.settings.trend_window_hours / 24) * self.settings.growth_ratio
        )
        severe = any(
            set(o.warning_signs) & {"otp_request", "identity_collection", "payment_demand"}
            for o in observations
            if start <= o.received_at <= instant
        )
        cluster.trend = Trend(
            independent_in_window=recent,
            baseline_daily_average=round(baseline, 3),
            increasing=increasing,
            recurring=recurring,
            high_severity_indicators=severe,
        )
        status, _, _, _ = evidence_status(observations, instant, self.settings)
        cluster.status = (
            "review_available" if recurring and status else "deferred" if recurring else "observing"
        )
        current = self._fingerprint(observations, instant)
        for draft in state.drafts.values():
            if draft.cluster_id != cluster_id:
                continue
            if draft.approval_status in {"expired", "rejected"}:
                continue
            if instant >= draft.expires_at or not status or not recurring:
                draft.approval_status = "expired"
            elif draft.evidence_fingerprint != current:
                draft.approval_status = "pending_review"
                draft.review = None
                # Existing text is retained for review; export also checks fingerprint.

    def _purge(self, state: AlertState, instant: datetime) -> None:
        cutoff = instant - timedelta(days=self.settings.retention_days)
        affected = {o.cluster_id for o in state.observations.values() if o.received_at <= cutoff}
        state.drafts = {key: d for key, d in state.drafts.items() if d.cluster_id not in affected}
        state.observations = {
            key: o for key, o in state.observations.items() if o.received_at > cutoff
        }
        state.receipts = {key: r for key, r in state.receipts.items() if r.received_at > cutoff}
        state.drafts = {key: d for key, d in state.drafts.items() if d.created_at > cutoff}
        for cluster_id in list(state.clusters):
            self._rebuild(state, cluster_id, instant)
        state.receipts = {
            key: r
            for key, r in state.receipts.items()
            if all(c in state.clusters for c in r.cluster_ids)
        }

    def purge(self) -> int:
        """Periodic retention/expiry sweep; durable adapters should schedule this too."""
        with self.repository.transaction() as state:
            before = len(state.observations)
            self._purge(state, utc_time(self.clock()))
            return before - len(state.observations)

    def ingest(self, request: IngestRequest) -> IngestResponse:
        if request.consent is not True:
            raise AppError(
                "alerts_consent_required", "Explicit consent is required for trend analysis.", 422
            )
        instant = utc_time(self.clock())
        source = self._source(request.source_token.get_secret_value())
        verification = request.verification
        checked = utc_time(verification.checked_at)
        if checked > instant or not verification.claims:
            raise AppError(
                "alerts_record_invalid",
                "Supply an already checked, timezone-aware claim record.",
                422,
            )
        # Hash only minimized records for idempotency; raw conversations are never stored.
        prepared = []
        known_rules = {rule for rule, *_ in RULES}
        for claim in verification.claims:
            if (
                not claim.original_span
                or claim.original_span not in verification.input.text
                or not normalize(claim.claim_text)
            ):
                raise AppError(
                    "alerts_record_invalid", "Claims must be anchored to their verified input.", 422
                )
            claim_time = utc_time(claim.checked_at)
            if len(claim.entities) > 12 or len(claim.temporal_context.relevant_source_dates) > 10:
                raise AppError(
                    "alerts_record_invalid",
                    "Record exceeds the upstream claim metadata limits.",
                    422,
                )
            if claim_time > instant:
                raise AppError(
                    "alerts_timestamp_invalid", "Future check timestamps are not accepted.", 422
                )
            text, redacted = redact(claim.claim_text)
            entities = protected_anchors(
                claim.claim_text, claim.entities, self.settings.pseudonym_secret.get_secret_value()
            )
            detected_signs = {f.rule for f in risk_for(claim.claim_text).factors} | {
                f.rule for f in claim.risk.factors if f.rule in known_rules
            }
            prepared.append(
                (
                    claim,
                    text,
                    redacted,
                    entities,
                    sorted(detected_signs),
                    references(claim, instant, self.settings),
                )
            )
        digest = hashlib.sha256(
            json.dumps(
                [
                    verification.status,
                    bool(verification.warnings),
                    checked.isoformat(),
                    verification.input.detected_language,
                    [
                        (
                            str(c.claim_id),
                            text,
                            redacted,
                            entities,
                            signs,
                            c.verdict,
                            c.checked_at.isoformat(),
                            c.temporal_context.relevant_source_dates,
                            [
                                (
                                    str(e.evidence_id),
                                    e.source_type,
                                    e.excerpt_provenance,
                                    e.directly_relevant,
                                    e.relevance_score,
                                    "incomplete_content:" in e.authority_basis,
                                )
                                for e in c.evidence
                            ],
                            [
                                e.model_dump(mode="json", exclude={"eligible", "issues"})
                                for e in refs
                            ],
                        )
                        for c, text, redacted, entities, signs, refs in prepared
                    ],
                ],
                sort_keys=True,
            ).encode()
        ).hexdigest()
        with self.repository.transaction() as state:
            self._purge(state, instant)
            previous = state.receipts.get(request.submission_id)
            if previous:
                if previous.source_hash != source or previous.digest != digest:
                    raise AppError(
                        "alerts_submission_conflict",
                        "Submission ID already belongs to a different minimized record.",
                        409,
                    )
                return IngestResponse(
                    submission_id=request.submission_id,
                    duplicate=True,
                    cluster_ids=previous.cluster_ids,
                    draft_ids=[],
                    deferred_reasons=[],
                )
            cluster_ids = []
            duplicate = True
            for claim, text, redacted, entities, signs, refs in prepared:
                match = next(
                    (
                        c
                        for c in state.clusters.values()
                        if any(
                            self.matcher.similar(text, o.claim_text, entities, o.entities)
                            for o in self._observations(state, c.cluster_id)[:5]
                        )
                    ),
                    None,
                )
                if match is None:
                    if len(state.clusters) >= self.settings.max_clusters:
                        raise AppError(
                            "alerts_capacity",
                            "Local cluster capacity reached; apply retention or use a durable repository.",
                            503,
                        )
                    match = Cluster(
                        canonical_claim=text, first_observed_at=instant, last_observed_at=instant
                    )
                    state.clusters[match.cluster_id] = match
                existing = next(
                    (
                        o
                        for o in self._observations(state, match.cluster_id)
                        if o.source_hash == source
                    ),
                    None,
                )
                observation = Observation(
                    cluster_id=match.cluster_id,
                    source_hash=source,
                    claim_text=text,
                    language=verification.input.detected_language
                    if verification.input.detected_language in {"en", "hi", "mr"}
                    else "und",
                    verdict=claim.verdict,
                    received_at=instant,
                    last_seen_at=instant,
                    checked_at=min(claim_time, checked),
                    technical_failure=verification.status != "completed"
                    or bool(verification.warnings),
                    warning_signs=signs,
                    evidence=refs,
                    privacy_redacted=redacted,
                    entities=entities,
                    source_dates=[
                        date
                        for date in claim.temporal_context.relevant_source_dates
                        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date)
                    ],
                )
                if existing:
                    if observation.checked_at < existing.checked_at:
                        existing.last_seen_at = (
                            instant  # Old replay cannot replace fresher evidence.
                        )
                    else:
                        observation.observation_id = existing.observation_id
                        observation.received_at = existing.received_at
                        state.observations[existing.observation_id] = observation
                else:
                    if len(state.observations) >= self.settings.max_observations:
                        raise AppError(
                            "alerts_capacity", "Local observation capacity reached.", 503
                        )
                    state.observations[observation.observation_id] = observation
                    duplicate = False
                cluster_ids.append(match.cluster_id)
                self._rebuild(state, match.cluster_id, instant)
            if len(state.receipts) >= self.settings.max_observations * 2:
                raise AppError("alerts_capacity", "Idempotency receipt capacity reached.", 503)
            state.receipts[request.submission_id] = Receipt(
                source, digest, list(dict.fromkeys(cluster_ids)), instant
            )
            drafts, deferred = [], []
            for cluster_id in dict.fromkeys(cluster_ids):
                draft, reasons = self._draft(state, cluster_id, "en", instant)
                if draft:
                    drafts.append(draft.alert_id)
                deferred.extend(reasons)
            return IngestResponse(
                submission_id=request.submission_id,
                duplicate=duplicate,
                cluster_ids=list(dict.fromkeys(cluster_ids)),
                draft_ids=drafts,
                deferred_reasons=list(dict.fromkeys(deferred)),
            )

    def _draft(
        self, state: AlertState, cluster_id: UUID, language: Language, instant: datetime
    ) -> tuple[AlertDraft | None, list[str]]:
        cluster = state.clusters.get(cluster_id)
        if cluster is None:
            raise AppError("alerts_not_found", "Cluster not found.", 404)
        observations = self._observations(state, cluster_id)
        status, sources, verified_at, reasons = evidence_status(
            observations, instant, self.settings
        )
        if cluster.trend is None or not cluster.trend.recurring:
            return None, ["trend_threshold_not_met"]
        if status is None or verified_at is None:
            return None, reasons
        current = self._fingerprint(observations, instant)
        existing = next(
            (
                d
                for d in state.drafts.values()
                if d.cluster_id == cluster_id
                and d.language == language
                and d.approval_status not in {"expired", "rejected"}
            ),
            None,
        )
        if existing and existing.evidence_fingerprint == current:
            return existing, [
                "translation_unavailable"
            ] if existing.language_content_status == "pending_translation" else []
        text = next((o.claim_text for o in observations if o.language == language), None)
        if text is None and self.translator:
            try:
                text = self.translator.translate(
                    cluster.canonical_claim, observations[0].language, language
                )
                if text is not None and (
                    not isinstance(text, str)
                    or not text.strip()
                    or redact(text)[1]
                    or len(text) > 1200
                ):
                    text = None
            except (RuntimeError, ValueError, OSError):
                text = None
        copy = TEXT[language]
        expires = min(
            instant + timedelta(hours=self.settings.draft_ttl_hours),
            verified_at + timedelta(hours=self.settings.evidence_max_age_hours),
        )
        draft = AlertDraft(
            cluster_id=cluster_id,
            title=copy["title"],
            claim_summary=text,
            evidence_based_status=status,
            explanation=copy[status],
            scam_warning_signs=[
                copy["signals"][sign]
                for sign in sorted({s for o in observations for s in o.warning_signs})
            ],
            recommended_user_actions=copy["actions"],
            authoritative_source_links=sorted({e.url for e in sources}),
            language=language,
            language_content_status="ready" if text else "pending_translation",
            created_at=instant,
            last_verified_at=verified_at,
            expires_at=expires,
            evidence_fingerprint=current,
            scope_note=copy["scope"].format(
                count=cluster.trend.independent_in_window, hours=self.settings.trend_window_hours
            ),
        )
        if existing:
            draft.alert_id = existing.alert_id
            draft.created_at = existing.created_at
            draft.content_version = existing.content_version + 1
            draft.review_history = existing.review_history
            draft.approval_status = "pending_review" if text else "draft"
        elif len(state.drafts) >= self.settings.max_drafts:
            return None, ["draft_capacity_reached"]
        state.drafts[draft.alert_id] = draft
        return draft, ["translation_unavailable"] if not text else []

    def create_draft(self, cluster_id: UUID, language: Language) -> AlertDraft:
        instant = utc_time(self.clock())
        with self.repository.transaction() as state:
            self._purge(state, instant)
            draft, reasons = self._draft(state, cluster_id, language, instant)
            if draft is None:
                raise AppError(
                    "alerts_draft_deferred", "Draft deferred: " + ", ".join(reasons), 409
                )
            return draft.model_copy(deep=True)

    def clusters(self) -> list[Cluster]:
        with self.repository.transaction() as state:
            self._purge(state, utc_time(self.clock()))
            return [c.model_copy(deep=True) for c in state.clusters.values()]

    def drafts(self) -> list[AlertDraft]:
        with self.repository.transaction() as state:
            self._purge(state, utc_time(self.clock()))
            return [d.model_copy(deep=True) for d in state.drafts.values()]

    def _editable(
        self, state: AlertState, alert_id: UUID, version: int, instant: datetime
    ) -> AlertDraft:
        self._purge(state, instant)
        draft = state.drafts.get(alert_id)
        if draft is None:
            raise AppError("alerts_not_found", "Draft not found.", 404)
        if draft.content_version != version:
            raise AppError(
                "alerts_version_conflict",
                "Draft changed; reload and review the current version.",
                409,
            )
        if draft.approval_status in {"expired", "rejected"}:
            raise AppError(
                "alerts_not_reviewable",
                "This draft is expired or rejected; prepare a fresh draft.",
                409,
            )
        return draft

    def submit(self, alert_id: UUID, version: int) -> AlertDraft:
        instant = utc_time(self.clock())
        with self.repository.transaction() as state:
            draft = self._editable(state, alert_id, version, instant)
            if draft.language_content_status != "ready":
                raise AppError(
                    "alerts_translation_pending",
                    "Claim translation or human language review is still pending.",
                    409,
                )
            draft.approval_status = "pending_review"
            draft.review = None
            return draft.model_copy(deep=True)

    def approve(self, alert_id: UUID, request: ApproveRequest) -> AlertDraft:
        if request.evidence_reviewed is not True:
            raise AppError("alerts_review_required", "Explicit evidence review is required.", 409)
        instant = utc_time(self.clock())
        with self.repository.transaction() as state:
            draft = self._editable(state, alert_id, request.expected_version, instant)
            observations = self._observations(state, draft.cluster_id)
            status, _, _, reasons = evidence_status(observations, instant, self.settings)
            if (
                draft.approval_status != "pending_review"
                or draft.language_content_status != "ready"
                or status is None
                or draft.evidence_fingerprint != self._fingerprint(observations, instant)
            ):
                raise AppError(
                    "alerts_review_required",
                    "Current content and fresh evidence must be reviewed before approval.",
                    409,
                )
            draft.review = Review(
                reviewer_id=request.reviewer_id,
                reviewed_at=instant,
                content_version=draft.content_version,
                content_hash=content_hash(draft),
                evidence_fingerprint=draft.evidence_fingerprint,
                evidence_review_status="reviewed",
                action="approved",
            )
            draft.review_history = [*draft.review_history, draft.review][-32:]
            draft.approval_status = "approved"
            return draft.model_copy(deep=True)

    def reject(self, alert_id: UUID, request: RejectRequest) -> AlertDraft:
        instant = utc_time(self.clock())
        with self.repository.transaction() as state:
            draft = self._editable(state, alert_id, request.expected_version, instant)
            review = Review(
                reviewer_id=request.reviewer_id,
                reviewed_at=instant,
                content_version=draft.content_version,
                content_hash=content_hash(draft),
                evidence_fingerprint=draft.evidence_fingerprint,
                evidence_review_status="not_reviewed",
                action="rejected",
                rejection_reason=request.reason,
            )
            draft.review, draft.approval_status = review, "rejected"
            draft.review_history = [*draft.review_history, review][-32:]
            return draft.model_copy(deep=True)

    def edit(self, alert_id: UUID, request: EditRequest) -> AlertDraft:
        instant = utc_time(self.clock())
        with self.repository.transaction() as state:
            draft = self._editable(state, alert_id, request.expected_version, instant)
            fields = {
                field: getattr(request, field)
                for field in ("title", "claim_summary", "explanation")
            }
            if any(not normalize(value) or redact(value)[1] for value in fields.values()):
                raise AppError(
                    "alerts_sensitive_content",
                    "Remove sensitive identifiers or message URLs from draft text; citations remain separate.",
                    422,
                )
            for field, value in fields.items():
                setattr(draft, field, normalize(value))
            if (
                draft.language_content_status == "pending_translation"
                and request.translation_reviewed
            ):
                draft.language_content_status = "ready"
            draft.content_version += 1
            draft.review = None
            draft.approval_status = (
                "pending_review" if draft.language_content_status == "ready" else "draft"
            )
            return draft.model_copy(deep=True)

    def export(self, alert_id: UUID) -> ExportPayload:
        instant = utc_time(self.clock())
        with self.repository.transaction() as state:
            self._purge(state, instant)
            draft = state.drafts.get(alert_id)
            if draft is None:
                raise AppError("alerts_not_found", "Draft not found.", 404)
            review = draft.review
            if (
                draft.approval_status != "approved"
                or draft.language_content_status != "ready"
                or review is None
                or review.action != "approved"
                or review.evidence_review_status != "reviewed"
                or review.content_version != draft.content_version
                or review.content_hash != content_hash(draft)
                or review.evidence_fingerprint
                != self._fingerprint(self._observations(state, draft.cluster_id), instant)
            ):
                raise AppError(
                    "alerts_export_forbidden",
                    "Only a current, approved, evidence-reviewed draft may be copied.",
                    409,
                )
            return ExportPayload(
                alert_id=draft.alert_id,
                content_version=draft.content_version,
                language=draft.language,
                channel_text=channel_text(draft),
                approved_at=review.reviewed_at,
                reviewer_id=review.reviewer_id,
                expires_at=draft.expires_at,
            )

    def withdraw(self, source_token: str) -> int:
        source = self._source(source_token)
        with self.repository.transaction() as state:
            affected = {
                o.cluster_id for o in state.observations.values() if o.source_hash == source
            }
            count = sum(o.source_hash == source for o in state.observations.values())
            state.observations = {
                key: o for key, o in state.observations.items() if o.source_hash != source
            }
            state.receipts = {
                key: r for key, r in state.receipts.items() if r.source_hash != source
            }
            for cluster_id in affected:
                # Drafts may contain the withdrawn submitter's wording; delete, not merely revoke.
                state.drafts = {
                    key: d for key, d in state.drafts.items() if d.cluster_id != cluster_id
                }
                self._rebuild(state, cluster_id, utc_time(self.clock()))
            return count
