import re
from datetime import datetime

from app.config import Settings
from app.errors import AppError
from app.schemas.models import ClaimBatch
from app.services.chunks import split_text
from app.services.claims.dates import relative_dates
from app.services.providers import LLM
from app.services.search.investigation import authority_for

PROMPT = """Extract 0..N distinct, independent falsifiable factual assertions. Exclude greetings, opinions, commands and unverifiable predictions. Never combine unrelated assertions. Keep entities, amounts, dates, locations, scope and qualifications. original_span MUST be an exact contiguous substring of input text. Write claim_text in its original language. Supply up to 3 precise queries, including an English query for Hindi/Marathi claims; use relevant authoritative institution names (RBI for Indian currency, PIB/relevant ministry for scheme announcements) and a general cross-check query. Relative dates remain relative to checked_at; do not guess their resolution. Set current_assertion only for claims presented as current/new. Detect en/hi/mr/und. Set truncated if the claim cap omits assertions. No claims is a valid answer."""


async def extract_claims(
    llm: LLM,
    text: str,
    language: str,
    jurisdiction: str,
    settings: Settings,
    checked_at: str,
    *,
    message_time: datetime | None = None,
) -> ClaimBatch:
    chunks = split_text(text, settings.document_chunk_chars, settings.max_document_chunks)
    batch = ClaimBatch(detected_language="und", claims=[], truncated=False)
    for index, chunk in enumerate(chunks):
        if len(batch.claims) >= settings.max_claims:
            batch.truncated = True
            break
        output = await llm.structured(
            PROMPT,
            {
                "text": chunk.text,
                "input_language": language,
                "jurisdiction": jurisdiction,
                "max_claims": settings.max_claims - len(batch.claims),
                "checked_at": checked_at,
                "original_message_time": message_time.isoformat() if message_time else None,
                "reference_timezone": "Asia/Kolkata" if jurisdiction == "IN" else "UTC",
                "chunk_index": index + 1,
                "chunk_count": len(chunks),
            },
            ClaimBatch,
        )
        if any(claim.original_span not in chunk.text for claim in output.claims):
            raise AppError(
                "claim_span_invalid",
                "A model claim was not anchored to its submitted document chunk.",
                502,
            )
        batch.detected_language = (
            output.detected_language
            if batch.detected_language == "und"
            else batch.detected_language
        )
        batch.truncated |= output.truncated
        keys = {claim.claim_text.casefold().strip() for claim in batch.claims}
        batch.claims.extend(
            claim for claim in output.claims if claim.claim_text.casefold().strip() not in keys
        )
    seen: set[str] = set()
    distinct = []
    for claim in batch.claims:
        reference = message_time or datetime.fromisoformat(checked_at)
        resolved = relative_dates(claim.original_span, reference, jurisdiction)
        claim.dates = list(dict.fromkeys([*claim.dates, *resolved]))
        if resolved:
            claim.qualifiers.append(
                "Relative dates resolved against original message time."
                if message_time
                else "Original message time unavailable; relative dates use the check time."
            )
        if claim.original_span not in text:
            raise AppError(
                "claim_span_invalid",
                "The model could not anchor a claim to the input. Please retry.",
                502,
            )
        if any(len(q) > 400 or not q.strip() for q in claim.queries):
            raise AppError(
                "claim_query_invalid", "The model returned an invalid search query.", 502
            )
        if authority_for(claim.claim_text, jurisdiction) == "rbi.org.in":
            # A bare RBI query also matches Restaurant Brands International. Spend
            # the first bounded search on the actual currency authority, retaining
            # any additional cross-check queries and all source/verdict guards.
            query = re.sub(r"\bRBI\b", "Reserve Bank of India", claim.queries[0], flags=re.I)
            query = re.sub(r"\bsite:\S+", "", query).strip()
            claim.queries[0] = ("site:rbi.org.in " + query)[:400]
        key = claim.claim_text.casefold().strip()
        if key not in seen:
            distinct.append(claim)
            seen.add(key)
    batch.truncated = batch.truncated or len(distinct) > settings.max_claims
    batch.claims = distinct[: settings.max_claims]
    return batch
