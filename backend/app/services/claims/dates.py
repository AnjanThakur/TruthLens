"""Resolve only unambiguous relative dates without changing the submitted claim."""

import re
from datetime import UTC, datetime, timedelta, timezone

INDIA_TIME = timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")
WEEKDAYS = [
    ("monday", "सोमवार"),
    ("tuesday", "मंगलवार", "मंगळवार"),
    ("wednesday", "बुधवार"),
    ("thursday", "thursday", "गुरुवार"),
    ("friday", "शुक्रवार"),
    ("saturday", "शनिवार"),
    ("sunday", "रविवार"),
]


def relative_dates(text: str, reference: datetime, jurisdiction: str) -> list[str]:
    local = reference.astimezone(INDIA_TIME if jurisdiction == "IN" else UTC)
    found: set[str] = set()
    for offset, pattern in (
        (0, r"\btoday\b|आज(?![\u0900-\u097f])"),
        (1, r"\btomorrow\b|उद्या(?![\u0900-\u097f])"),
        (-1, r"\byesterday\b|बीते कल|मागील दिवस"),
    ):
        if re.search(pattern, text, re.I):
            found.add((local.date() + timedelta(days=offset)).isoformat())
    # Hindi 'कल' alone means either yesterday or tomorrow: leave it unresolved.
    for number, names in enumerate(WEEKDAYS):
        options = "|".join(re.escape(name) for name in names)
        if re.search(rf"(?:\bnext\s+|अगले\s+|पुढील\s+)(?:{options})", text, re.I):
            distance = (number - local.weekday()) % 7 or 7
            found.add((local.date() + timedelta(days=distance)).isoformat())
    return sorted(found)


def quoted_dates(text: str) -> set[str]:
    """ISO and explicit English calendar dates in a verbatim passage; no metadata inference."""
    found: set[str] = set()
    for value in re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text):
        try:
            found.add(datetime.strptime(value, "%Y-%m-%d").date().isoformat())
        except ValueError:
            pass
    months = "January|February|March|April|May|June|July|August|September|October|November|December"
    for match in re.finditer(
        rf"\b(?:(\d{{1,2}})\s+({months})|({months})\s+(\d{{1,2}})),?\s+(\d{{4}})\b", text, re.I
    ):
        day, month = (match[1], match[2]) if match[1] else (match[4], match[3])
        try:
            found.add(datetime.strptime(f"{day} {month} {match[5]}", "%d %B %Y").date().isoformat())
        except ValueError:
            pass
    return found
