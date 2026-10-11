import math
import re
from collections.abc import Sequence
from typing import Protocol

from app.services.common import normalize

LEXICON = {
    "otp": "otp",
    "ओटीपी": "otp",
    "bank": "bank",
    "बैंक": "bank",
    "बँक": "bank",
    "बँकेचे": "bank",
    "account": "account",
    "खाते": "account",
    "खात्याचे": "account",
    "खाता": "account",
    "kyc": "kyc",
    "केवायसी": "kyc",
    "send": "share",
    "share": "share",
    "provide": "share",
    "भेजें": "share",
    "पाठवा": "share",
    "सांगा": "share",
    "verify": "verify",
    "verification": "verify",
    "सत्यापन": "verify",
    "पडताळणी": "verify",
    "blocked": "blocked",
    "block": "blocked",
    "बंद": "blocked",
    "ब्लॉक": "blocked",
    "pay": "payment",
    "payment": "payment",
    "शुल्क": "payment",
    "भुगतान": "payment",
    "पैसे": "payment",
    "aadhaar": "identity",
    "aadhar": "identity",
    "आधार": "identity",
    "pan": "identity",
    "पॅन": "identity",
    "refund": "refund",
    "परतावा": "refund",
    "वापसी": "refund",
    "prize": "prize",
    "बक्षीस": "prize",
    "इनाम": "prize",
    "currency": "currency",
    "rupee": "currency",
    "rupees": "currency",
    "नोट": "currency",
    "नोटा": "currency",
}
STOP = set(
    "the a an to your for of is are will be in at by this that please now my our and you all के की का को में लिए अपना अपने यह है हैं करें करणे करण्यासाठी करा आहे तुमचे तुमचा देणे".split()
)


class Embedder(Protocol):
    """Injected local multilingual model. Implementations must never download/call APIs."""

    def encode(self, texts: list[str]) -> Sequence[Sequence[float]]: ...


def features(text: str) -> set[str]:
    words = re.findall(r"[a-z]+|[\u0900-\u0963\u0971-\u097f]+|\d+", normalize(text).casefold())
    return {LEXICON.get(word, word) for word in words if word not in STOP and word != "redacted"}


def signature(text: str, entities: list[str]) -> tuple[set[str], bool, set[str]]:
    numbers = set(re.findall(r"\d+(?:[.,]\d+)?", text))
    negated = bool(
        re.search(
            r"\b(?:not|no|never|without|cannot)\b|\b\w+n['’]t\b|नहीं|नाही|नको|नसते|मत|पाठवू नका",
            text,
            re.I,
        )
    )
    anchors = {normalize(value).casefold() for value in entities if normalize(value)}
    return numbers, negated, anchors


class Matcher:
    def __init__(self, embedder: Embedder | None = None, threshold: float = 0.93):
        self.embedder, self.threshold = embedder, threshold

    def similar(
        self, left: str, right: str, left_entities: list[str], right_entities: list[str]
    ) -> bool:
        if signature(left, left_entities) != signature(right, right_entities):
            return False
        if normalize(left).casefold() == normalize(right).casefold():
            return True
        a, b = features(left), features(right)
        topics = {"bank", "kyc", "payment", "identity", "refund", "prize", "currency"}
        if a & topics != b & topics:
            return False
        shared = a & b
        if len(shared) < 3:
            return False
        if len(shared) / max(1, len(a | b)) >= 0.85:
            return True
        concepts = set(LEXICON.values())
        if self.embedder is None or len(shared & concepts) < 3:
            return False
        try:
            x, y = self.embedder.encode([left, right])
            if len(x) == 0 or len(x) != len(y) or any(not math.isfinite(v) for v in [*x, *y]):
                return False
            denom = math.sqrt(sum(v * v for v in x) * sum(v * v for v in y))
            return bool(
                denom and sum(i * j for i, j in zip(x, y, strict=True)) / denom >= self.threshold
            )
        except (ValueError, TypeError, RuntimeError, OSError):
            return False
