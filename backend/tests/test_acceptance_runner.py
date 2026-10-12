import http.client
import json
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from conftest import CLAIMS

from app.config import Settings
from app.errors import AppError
from app.schemas.models import ClaimBatch
from scripts import validate_live


def test_cli_requires_explicit_available_quota_without_provider_calls():
    response = subprocess.run(  # noqa: S603 - fixed test module and flags; no shell
        [sys.executable, "-m", "scripts.validate_live", "--live"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert response.returncode == 2
    assert "no provider calls were made" in response.stderr


async def test_acceptance_stops_after_daily_quota_and_records_actual_mock_counts(
    monkeypatch, tmp_path
):
    original = validate_live.BudgetedGemini
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            429,
            json={
                "error": {
                    "code": "RESOURCE_EXHAUSTED",
                    "message": "Daily quota exceeded. Retry in 8h0m0s.",
                }
            },
        )

    monkeypatch.setattr(
        validate_live,
        "Settings",
        lambda **kwargs: Settings(
            _env_file=None, gemini_api_key="test-only", tavily_api_key="", **kwargs
        ),
    )
    monkeypatch.setattr(
        validate_live,
        "BudgetedGemini",
        lambda settings: original(settings, httpx.MockTransport(handler)),
    )
    target = tmp_path / "actual-mocked-results.json"
    assert await validate_live.run({"text", "url"}, ["en"], output=target) == 2
    report = json.loads(target.read_text(encoding="utf-8"))
    assert len(calls) == report["gemini_http_requests"] == 1
    assert report["tavily_http_requests"] == 0
    assert report["formats"]["text"]["status"] == report["formats"]["url"]["status"] == "SKIPPED"
    assert report["formats"]["url"]["reason"] == "Stopped after llm_quota_exhausted"


async def test_live_budgets_fail_before_any_provider_call(settings):
    llm, search = validate_live.BudgetedGemini(settings), validate_live.BudgetedSearch(settings)
    llm.budget = search.budget = 0
    with pytest.raises(AppError, match="budget") as error:
        await llm.structured("fixture", {}, ClaimBatch)
    assert error.value.code == "llm_live_budget_exhausted"
    with pytest.raises(AppError) as error:
        await search._search(CLAIMS[0])
    assert error.value.code == "search_budget_exhausted"
    assert llm.request_count == search.request_count == 0


def test_exported_openapi_contract_is_identical(settings):
    from app.main import create_app

    expected = Path(__file__).resolve().parents[2] / "docs" / "backend-openapi.json"
    # JSON structure is contractual; platform newlines and indentation are not.
    assert json.loads(expected.read_text(encoding="utf-8")) == create_app(settings).openapi()


@pytest.mark.parametrize(
    ("too_large", "unprocessable"),
    [
        ("Request Entity Too Large", "Unprocessable Entity"),
        ("Content Too Large", "Unprocessable Content"),
    ],
)
def test_openapi_contract_is_stable_across_python_http_phrases(
    settings, monkeypatch, too_large, unprocessable
):
    monkeypatch.setitem(http.client.responses, 413, too_large)
    monkeypatch.setitem(http.client.responses, 422, unprocessable)
    # Exercise fresh schema generation under both stdlib versions. Every
    # endpoint/schema/constraint still has to match the published snapshot.
    test_exported_openapi_contract_is_identical(settings)
