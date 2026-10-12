import logging

import httpx
import pytest
from pydantic import SecretStr
from test_gemini_regressions import output

from app.errors import AppError
from app.schemas.models import ClaimBatch
from app.services.providers import GeminiLLM


@pytest.mark.parametrize(
    "failure,code,category",
    [
        ("daily", "llm_quota_exhausted", "daily_quota"),
        ("rate", "llm_rate_limited", "transient_rate_limit"),
        ("auth", "llm_auth_error", "authentication"),
        ("server", "llm_provider_error", "transient_server"),
        ("rejected", "llm_provider_error", "request_rejected"),
        ("invalid", "llm_output_invalid", "local_schema_validation"),
        ("timeout", "llm_timeout", "transport_timeout"),
        ("connection", "llm_provider_error", "connection"),
    ],
)
async def test_provider_error_categories_are_safely_logged_without_raw_content(
    settings, caplog, failure, code, category
):
    settings.gemini_api_key = SecretStr("fixture-secret")
    settings.provider_max_attempts = 1
    caplog.set_level(logging.WARNING, logger="truthlens.diagnostics")
    calls = []

    def handler(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("fixture-secret private-input", request=request)
        if failure == "connection":
            raise httpx.ConnectError("fixture-secret private-input", request=request)
        if failure == "invalid":
            return output(
                '{"detected_language":"en","claims":[],"truncated":"private-input","fixture-secret":"hidden"}'
            )
        status = {"daily": 429, "rate": 429, "auth": 401, "server": 503, "rejected": 400}[failure]
        return httpx.Response(
            status,
            json={
                "error": {
                    "message": "Daily quota exceeded"
                    if failure == "daily"
                    else "fixture-secret private-input",
                    "code": "RESOURCE_EXHAUSTED" if failure == "daily" else "upstream_error",
                }
            },
        )

    with pytest.raises(AppError) as error:
        await GeminiLLM(settings, httpx.MockTransport(handler)).structured(
            "Extract", {"text": "private-input"}, ClaimBatch
        )
    assert error.value.code == code and len(calls) == 1
    events = [r.truthlens_event for r in caplog.records if hasattr(r, "truthlens_event")]
    assert events[-1]["stage"] == "claim_extraction" and events[-1]["category"] == category
    if failure in {"auth", "server", "rejected", "invalid"}:
        assert (
            events[-1]["provider_http_status"]
            == {"auth": 401, "server": 503, "rejected": 400, "invalid": 200}[failure]
        )
    if failure == "invalid":
        validation = next(e for e in events if "validation_types" in e)
        assert "bool_parsing" in validation["validation_types"]
        assert "extra_forbidden" in validation["validation_types"]
    assert "fixture-secret" not in caplog.text and "private-input" not in caplog.text
    assert (
        "fixture-secret" not in error.value.message and "private-input" not in error.value.message
    )


async def test_malformed_provider_envelope_is_not_classified_as_server_failure(settings, caplog):
    settings.gemini_api_key = SecretStr("fixture-secret")
    settings.provider_max_attempts = 1
    caplog.set_level(logging.WARNING, logger="truthlens.diagnostics")
    with pytest.raises(AppError) as error:
        await GeminiLLM(
            settings,
            httpx.MockTransport(
                lambda r: httpx.Response(
                    200,
                    headers={"content-type": "application/json"},
                    content=b"fixture-secret non-JSON envelope",
                )
            ),
        ).structured("Extract", {}, ClaimBatch)
    assert error.value.code == "llm_output_invalid"
    events = [r.truthlens_event for r in caplog.records if hasattr(r, "truthlens_event")]
    assert events[-1]["category"] in {"provider_response_validation", "invalid_response"}
    assert "fixture-secret" not in caplog.text
