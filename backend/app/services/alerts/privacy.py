import hashlib
import hmac
import re
import unicodedata

from app.services.common import normalize

PATTERNS = [
    r"\b[A-Z]{5}\d{4}[A-Z]\b",  # PAN
    r"(?<!\d)\d{4}[ -]\d{4}[ -]\d{4}(?!\d)",  # spaced Aadhaar
    r"(?<!\w)(?:\+?91[ -]?)?\d{10,19}(?!\w)",  # phones, Aadhaar, account/card numbers
    r"(?<!\w)(?:\+?91[ -]?)?(?:\d[ -]?){9,18}\d(?!\w)",
    r"(?<!\w)(?:\+\d{1,3}[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]\d{3}[ .-]\d{4}(?!\w)",
    r"(?<!\w)(?:\+91[ -]?)?\d{5}[ -]\d{5}(?!\w)",
    r"(?<!\w)(?:\d{4}[ -]){2,3}\d{4}(?!\w)",  # spaced financial identifiers
    r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",  # email and UPI
    r"(?:otp|pin|password|passcode|ओटीपी|पासवर्ड|पिन)\s*(?:[:=]|is|है|आहे)\s*\S+",
    r"(?:my name|address|balance|salary)\s*(?:[:=]|is)\s*[^.;\n]+",
    r"\b[A-Z]{4}0[A-Z0-9]{6}\b",  # IFSC
    r"\b[\w.+-]+@(?:upi|paytm|ybl|ibl|ok\w+|apl|axl)\b",  # UPI handles
    r"(?<!\d)\d{4,8}(?!\d)",  # conservative: short secrets; may also redact large amounts
    r"https?://\S+|www\.\S+",  # message URLs are not retained; citations validated separately
    r"(?:Mr\.?|Mrs\.?|Ms\.?|श्री|श्रीमती)\s+[A-Za-z\u0900-\u097f]+(?:\s+[A-Z][a-z]+)?",
]


def redact(text: str) -> tuple[str, bool]:
    text = normalize(text)
    cleaned = text
    # Preserve explicit public event dates, not arbitrary short numeric secrets.
    dates: list[str] = []

    def save_date(match: re.Match[str]) -> str:
        dates.append(match.group())
        return "DATEPLACEHOLDER" + chr(65 + len(dates) - 1) + "END"

    cleaned = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", save_date, cleaned)
    for pattern in PATTERNS:
        cleaned = re.sub(pattern, "[REDACTED]", cleaned, flags=re.I)
    for index, date in enumerate(dates):
        cleaned = cleaned.replace("DATEPLACEHOLDER" + chr(65 + index) + "END", date)
    return cleaned, cleaned != text


def protected_anchors(text: str, entities: list[str], secret: str) -> list[str]:
    """Keep numeric/entity distinctions without retaining their original values."""
    normalized_digits = "".join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in text)
    numbers = sorted(set(re.findall(r"\d+(?:[.,]\d+)?", normalized_digits)))
    anchors = ["number:" + pseudonym(value, secret) for value in numbers]
    anchors.extend(
        "entity:" + pseudonym(normalize(value).casefold(), secret)
        for value in entities
        if normalize(value)
    )
    return sorted(set(anchors))


def pseudonym(source_token: str, secret: str) -> str:
    return hmac.new(secret.encode(), source_token.encode(), hashlib.sha256).hexdigest()
