import math
import re
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl, unquote, urlsplit

from app.errors import AppError
from app.schemas.models import ClaimResult
from app.services.alerts.models import EvidenceReference, EvidenceStatus, Observation
from app.services.alerts.privacy import redact
from app.services.alerts.settings import AlertsSettings
from app.services.extract.url import canonical_url
from app.services.search.ledger import identity


def utc_time(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise AppError(
            "alerts_timestamp_invalid",
            "Timezone-aware evidence and check timestamps are required.",
            422,
        )
    return value.astimezone(UTC)


def references(
    claim: ClaimResult, clock: datetime, settings: AlertsSettings
) -> list[EvidenceReference]:
    result = []
    for item in claim.evidence:
        issues = []
        try:
            url = canonical_url(item.url)
            if re.search(
                r"\d{10,19}|[A-Z]{5}\d{4}[A-Z]|[\w.+-]+@[\w.-]+",
                unquote(urlsplit(url).path + "?" + urlsplit(url).query),
                re.I,
            ):
                raise AppError("unsafe_url", "Sensitive source URL.")
            if urlsplit(url).scheme != "https" or any(
                name.casefold()
                in {
                    "token",
                    "key",
                    "api_key",
                    "password",
                    "otp",
                    "phone",
                    "aadhaar",
                    "pan",
                    "email",
                }
                for name, _ in parse_qsl(urlsplit(url).query)
            ):
                raise AppError("unsafe_url", "Unsafe source URL.")
            publisher, kind, _ = identity(url)
            if kind == "other" or kind != item.source_type:
                issues.append("unreviewed_publisher")
        except AppError:
            # Never store unsafe URLs (including credentials or private identifiers).
            continue
        retrieved = utc_time(item.retrieved_at)
        if retrieved > clock or clock - retrieved > timedelta(
            hours=settings.evidence_max_age_hours
        ):
            issues.append("stale_or_future_evidence")
        if (
            item.excerpt_provenance != "fetched_page"
            or not item.directly_relevant
            or not math.isfinite(item.relevance_score)
            or not 0.5 <= item.relevance_score <= 1
        ):
            issues.append("not_direct_fetched_evidence")
        if "incomplete_content:" in item.authority_basis:
            issues.append("incomplete_evidence")
        excerpt, redacted = redact(item.excerpt)
        if redacted or not excerpt:
            issues.append("sensitive_or_empty_excerpt")
        result.append(
            EvidenceReference(
                evidence_id=item.evidence_id,
                url=url,
                publisher=publisher,
                excerpt=excerpt,
                stance=item.stance,
                retrieved_at=retrieved,
                eligible=not issues,
                issues=issues,
                published_at=item.published_at
                if item.published_at
                and re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T[0-9:.+Z-]+)?", item.published_at)
                else None,
                updated_at=item.updated_at
                if item.updated_at
                and re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T[0-9:.+Z-]+)?", item.updated_at)
                else None,
            )
        )
    return result


def evidence_status(
    observations: list[Observation], clock: datetime, settings: AlertsSettings
) -> tuple[EvidenceStatus | None, list[EvidenceReference], datetime | None, list[str]]:
    # Historical samples inform baseline counts, not today's public evidence gate.
    observations = [
        o
        for o in observations
        if clock - timedelta(hours=settings.trend_window_hours) <= o.received_at <= clock
    ]
    if any(o.technical_failure for o in observations):
        return None, [], None, ["technical_verification_failure"]
    if any(
        utc_time(o.checked_at) > clock
        or clock - utc_time(o.checked_at) > timedelta(hours=settings.evidence_max_age_hours)
        for o in observations
    ):
        return None, [], None, ["stale_or_future_verification"]
    sources = {
        (e.url, e.stance, e.excerpt): e
        for o in observations
        for e in o.evidence
        if e.eligible
        and e.retrieved_at
        <= clock
        < e.retrieved_at + timedelta(hours=settings.evidence_max_age_hours)
    }
    eligible = list(sources.values())
    if not eligible:
        return None, [], None, ["insufficient_evidence"]
    stances = {e.stance for e in eligible}
    verdicts = {o.verdict for o in observations}
    if (
        "verified" in verdicts
        or {"supports", "contradicts"} <= stances
        and "partially_true" not in verdicts
        and "outdated" not in verdicts
    ):
        return None, eligible, None, ["conflicting_or_verified_claim"]
    status: EvidenceStatus | None = None
    if verdicts == {"false"} and "contradicts" in stances:
        status = "claim_contradicted"
    elif verdicts <= {"partially_true", "misleading_context", "outdated"} and "context" in stances:
        if "outdated" in verdicts:
            dates = {
                date
                for o in observations
                for date in o.source_dates
                if any(date in e.excerpt for e in eligible)
            }
            if len(dates) < 2 or len({e.url for e in eligible}) < 2:
                return None, eligible, None, ["outdated_context_not_established"]
        status = "claim_needs_context"
    elif (
        verdicts == {"unconfirmed"}
        and "context" in stances
        and any(o.warning_signs for o in observations)
    ):
        status = "suspicious_indicators"
    if status is None:
        return None, eligible, None, ["insufficient_matching_evidence"]
    oldest = min([o.checked_at for o in observations] + [e.retrieved_at for e in eligible])
    return status, eligible, oldest, []
