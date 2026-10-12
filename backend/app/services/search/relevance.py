"""Lexical subject ranking is a discovery aid, never a factual assessment."""

import re

from app.schemas.models import AtomicClaim


def words(value: str) -> list[str]:
    return re.findall(r"[^\W_]+", value.casefold())


def entity_score(text: str, claim: AtomicClaim) -> float:
    tokens = words(text)
    joined = " " + " ".join(tokens) + " "
    entities = [words(e) for e in claim.entities if words(e)]
    if not entities:
        return 1.0
    # A full multiword name outweighs a generic first-name match. All entities
    # remain in the model input for its stricter scope and alias assessment.
    return max(
        1.0
        if " " + " ".join(entity) + " " in joined
        else 0.5 * len(set(entity) & set(tokens)) / len(set(entity))
        for entity in entities
    )


def subject_missing(text: str, claim: AtomicClaim) -> bool:
    # Conservative negative gate for an explicit named mortality claim. General
    # topics/institutions may use abbreviations ("library" vs "demo library");
    # their semantic relevance remains with assessment rather than this gate.
    if not re.search(
        r"\b(?:die|died|dies|dead|death|deceased)\b|passed away", claim.claim_text, re.I
    ):
        return False
    explicit = [
        e for e in claim.entities if " ".join(words(e)) in " ".join(words(claim.claim_text))
    ]
    return (
        bool(explicit)
        and all(len(words(e)) >= 2 for e in explicit)
        and entity_score(text, claim) < 1
    )
