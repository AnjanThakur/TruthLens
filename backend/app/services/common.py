import re
import unicodedata
from datetime import UTC, datetime


def now() -> datetime:
    return datetime.now(UTC)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace("\x00", "")
    return "\n".join(re.sub(r"[^\S\n]+", " ", line).strip() for line in text.splitlines()).strip()


def detect_language(text: str) -> str:
    # Script/word heuristic, never present as reliable language identification.
    if re.search(r"[\u0900-\u097f]", text):
        return (
            "mr"
            if re.search(r"आहे|नाही|करा|म्हण|मराठी|सर्व|होणार|पुढील|होतील|सोमवारी|नोटा", text)
            else "hi"
        )
    return "en" if re.search(r"[A-Za-z]", text) else "und"
