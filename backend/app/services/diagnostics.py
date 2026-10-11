"""Allow-listed diagnostics: no prompts, URLs, response bodies, headers or secrets."""

import json
import logging
from contextvars import ContextVar
from typing import Any

request_id: ContextVar[str | None] = ContextVar("truthlens_request_id", default=None)
logger = logging.getLogger("truthlens.diagnostics")


def emit(
    stage: str,
    category: str,
    code: str,
    *,
    status: int | None = None,
    attempt: int | None = None,
    validation_types: list[str] | None = None,
) -> None:
    event: dict[str, Any] = {
        "request_id": request_id.get(),
        "stage": stage,
        "category": category,
        "code": code,
    }
    if status is not None:
        event["provider_http_status"] = status
    if attempt is not None:
        event["attempt"] = attempt
    if validation_types:
        event["validation_types"] = validation_types[:8]
    logger.warning(json.dumps(event), extra={"truthlens_event": event})
