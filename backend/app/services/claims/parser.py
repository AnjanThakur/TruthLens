import re
from datetime import datetime

from app.config import Settings
from app.errors import AppError
from app.schemas.models import AtomicClaim, ClaimBatch
from app.services.chunks import split_text
from app.services.claims.dates import relative_dates
from app.services.common import detect_language
from app.services.providers import LLM
from app.services.search.investigation import authority_for

PROMPT = """Extract 0..N distinct, independent falsifiable factual assertions. Exclude greetings, opinions, commands and unverifiable predictions. Never combine unrelated assertions. Keep entities, amounts, dates, locations, scope and qualifications. original_span MUST be an exact contiguous substring of input text. Write claim_text in its original language. Supply up to 3 precise queries, including an English query for Hindi/Marathi claims; use relevant authoritative institution names (RBI for Indian currency, PIB/relevant ministry for scheme announcements) and a general cross-check query. Relative dates remain relative to checked_at; do not guess their resolution. Set current_assertion only for claims presented as current/new. Detect en/hi/mr/und. Set truncated if the claim cap omits assertions. No claims is a valid answer."""

PROMPT += """ Factual yes/no questions are also checkable inputs, even with informal grammar: 'did a named person died', 'has a named person died', or 'was an institution established on a stated date'. Convert the question to the positive factual proposition to investigate, retaining the exact original question as original_span. This conversion is not an answer: do not assume the proposition is true or search for an answer during extraction. Keep negation, dates and qualifications; do not invent identities or resolve pronouns. Apply the same rule to English, Hindi and Marathi factual questions. Questions asking for opinions, advice, recommendations or unknowable future predictions still do not establish factual assertions."""


def death_questions(text: str) -> list[AtomicClaim]:
    """Recover explicit named-subject death questions when the model returns none.

    This narrow syntax fallback establishes intent only, never a death or verdict.
    Qualified, negated, fictional and unresolved-person questions stay with the model.
    """
    claims = []
    fragments = re.split(r"[?!;\n]+|\s+and\s+(?=(?:did|has|is)\b)", text, flags=re.I)
    excluded = {
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "someone",
        "anyone",
        "everybody",
        "somebody",
        "anybody",
        "everyone",
        "nobody",
        "my",
        "your",
        "our",
        "his",
        "her",
        "their",
        "not",
        "never",
        "allegedly",
        "fictional",
        "movie",
        "film",
        "character",
        "and",
        "or",
        "if",
        "when",
        "why",
        "where",
        "what",
        "who",
        "how",
        "did",
        "has",
        "is",
        "already",
        "recently",
        "today",
        "yesterday",
        "last",
        "next",
        "now",
        "really",
        "reportedly",
        "rumored",
        "rumoured",
    }
    for fragment in fragments:
        span = fragment.strip()
        match = re.fullmatch(
            r"(?:did|has)\s+(.{1,120}?)\s+(?:die|died|pass away|passed away)\.?",
            span,
            flags=re.I,
        ) or re.fullmatch(r"is\s+(.{1,120}?)\s+(?:dead|deceased)\.?", span, flags=re.I)
        if not match:
            continue
        subject = match[1].strip()
        if not re.fullmatch(r"[^\W\d_]+(?:[ '\u2019-]+[^\W\d_]+){0,7}", subject):
            continue
        if set(subject.casefold().split()) & excluded:
            continue
        claims.append(
            AtomicClaim(
                claim_text=f"{subject} has died.",
                original_span=span,
                entities=[subject],
                dates=[],
                qualifiers=[
                    "Interpreted from a factual yes/no question; no factual answer is assumed."
                ],
                queries=[f"{subject} death report", f"{subject} alive death hoax"],
                current_assertion=False,
            )
        )
    return claims


def simple_mortality_claim(text: str) -> AtomicClaim | None:
    """Parse one unqualified English mortality input without a model request.

    This extracts the user's proposition only. It cannot establish a verdict.
    Everything outside this narrow syntax still uses the model parser.
    """
    span = text.strip()
    if len(span) > 160 or "\n" in span or ";" in span:
        return None
    excluded = {
        "i",
        "you",
        "he",
        "she",
        "we",
        "they",
        "my",
        "your",
        "our",
        "his",
        "her",
        "their",
        "no",
        "one",
        "someone",
        "anyone",
        "everyone",
        "allegedly",
        "reportedly",
        "rumored",
        "rumoured",
        "fictional",
        "movie",
        "film",
        "character",
        "and",
        "or",
        "not",
        "never",
        "today",
        "yesterday",
        "the",
        "a",
        "an",
        "actor",
        "actress",
        "singer",
        "minister",
        "president",
    }
    questions = death_questions(span)
    if (
        len(questions) == 1
        and span.rstrip("?!. ") == questions[0].original_span.rstrip(". ")
        and len(questions[0].entities[0].split()) >= 2
        and not set(questions[0].entities[0].casefold().split()) & excluded
    ):
        return questions[0]
    match = re.fullmatch(
        r"(.+?)\s+(?:has\s+)?(?:died|passed away)\.?",
        span,
        flags=re.I,
    )
    if not match:
        return None
    subject = match[1].strip()
    if not re.fullmatch(r"[^\W\d_]+(?:[ '\u2019-]+[^\W\d_]+){1,7}", subject):
        return None
    if set(subject.casefold().split()) & excluded:
        return None
    return AtomicClaim(
        claim_text=f"{subject} has died.",
        original_span=span,
        entities=[subject],
        dates=[],
        qualifiers=[],
        queries=[f"{subject} death report", f"{subject} alive death hoax"],
        current_assertion=False,
    )


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
    if language in {"auto", "en"} and (simple := simple_mortality_claim(text)):
        return ClaimBatch(detected_language="en", claims=[simple], truncated=False)
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
        if not output.claims:
            recovered = death_questions(chunk.text)
            remaining = settings.max_claims - len(batch.claims)
            output.claims = recovered[:remaining]
            output.truncated |= len(recovered) > remaining
            if recovered and output.detected_language == "und":
                output.detected_language = detect_language(chunk.text)
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
