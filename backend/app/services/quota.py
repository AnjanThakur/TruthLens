import math
import re
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

from app.errors import AppError


def guidance(error: Any) -> tuple[bool, int | None]:
    """Classify provider guidance internally; never return provider body/messages."""
    text = str(error).casefold()
    compact = re.sub(r"[^a-z]", "", text)
    daily = "perday" in compact or "daily" in compact or "per day" in text
    delay = None
    response = getattr(error, "response", None)
    if response is not None and (header := response.headers.get("retry-after")):
        try:
            delay = math.ceil(float(header))
        except (ValueError, OverflowError):
            try:
                stamp = parsedate_to_datetime(header)
                delay = math.ceil((stamp.astimezone(UTC) - datetime.now(UTC)).total_seconds())
            except (ValueError, TypeError, OverflowError):
                pass
    if delay is None:
        if match := re.search(r"retry(?:delay|_delay)[\"']?\s*[:=]\s*[\"']?(\d+(?:\.\d+)?)s", text):
            delay = math.ceil(float(match[1]))
        elif match := re.search(
            r"retry\s+(?:in|after)\s+(?:(\d+)h)?\s*(?:(\d+)m)?\s*(\d+(?:\.\d+)?)s", text
        ):
            delay = math.ceil(int(match[1] or 0) * 3600 + int(match[2] or 0) * 60 + float(match[3]))
    return daily, min(86400, max(1, delay)) if delay is not None else None


class QuotaGate:
    def __init__(self):
        self.blocked: dict[str, tuple[float, str]] = {}

    def block(self, model: str, seconds: int, daily: bool) -> None:
        self.blocked[model] = (
            time.monotonic() + seconds,
            "llm_quota_exhausted" if daily else "llm_rate_limited",
        )

    def check(self, model: str) -> None:
        if item := self.blocked.get(model):
            seconds = math.ceil(item[0] - time.monotonic())
            if seconds > 0:
                message = (
                    "Gemini's daily quota is exhausted."
                    if item[1] == "llm_quota_exhausted"
                    else "Gemini is temporarily rate limited."
                )
                raise AppError(
                    item[1],
                    f"{message} Retry after {seconds} seconds; no new provider call was made.",
                    503,
                    seconds,
                )
            self.blocked.pop(model, None)
