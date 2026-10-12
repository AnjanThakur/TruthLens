"""Allow-listed diagnostics: no prompts, URLs, response bodies, headers or secrets."""

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
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
    elapsed_ms: int | None = None,
    input_chars: int | None = None,
    prompt_chars: int | None = None,
    schema_chars: int | None = None,
    output_chars: int | None = None,
    timeout_seconds: float | None = None,
    evidence_count: int | None = None,
    eligible_count: int | None = None,
    excerpt_chars: int | None = None,
    remaining_attempts: int | None = None,
    retry_after_seconds: int | None = None,
    retry_wait_ms: int | None = None,
    api_version: str | None = None,
) -> None:
    event: dict[str, Any] = {
        "request_id": request_id.get(),
        "stage": stage,
        "category": category,
        "code": code,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if status is not None:
        event["provider_http_status"] = status
    if attempt is not None:
        event["attempt"] = attempt
    if validation_types:
        event["validation_types"] = validation_types[:8]
    if api_version in {"v1", "v1beta"}:
        event["api_version"] = api_version
    for key, value in {
        "elapsed_ms": elapsed_ms,
        "input_chars": input_chars,
        "prompt_chars": prompt_chars,
        "schema_chars": schema_chars,
        "output_chars": output_chars,
        "timeout_seconds": timeout_seconds,
        "evidence_count": evidence_count,
        "eligible_count": eligible_count,
        "excerpt_chars": excerpt_chars,
        "remaining_attempts": remaining_attempts,
        "retry_after_seconds": retry_after_seconds,
        "retry_wait_ms": retry_wait_ms,
    }.items():
        if value is not None:
            event[key] = value
    logger.warning(json.dumps(event), extra={"truthlens_event": event})
