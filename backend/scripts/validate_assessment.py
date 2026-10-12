"""One explicitly approved text verification: at most 1 Gemini and 2 Tavily attempts."""

import argparse
import asyncio
import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

from app.config import Settings
from app.main import create_app
from app.schemas.models import Decision
from app.services.diagnostics import logger
from scripts.validate_live import BudgetedGemini, BudgetedSearch, DiagnosticCapture


class CapturingGemini(BudgetedGemini):
    budget = 1

    def __init__(self, settings):
        super().__init__(settings)
        self.assessment_payload = None

    async def structured(self, task, data, model):
        if model is Decision:
            # Private acceptance artifact, never application logs. Public source
            # excerpts are retained to audit the actual input if assessment fails.
            self.assessment_payload = copy.deepcopy(data)
        return await super().structured(task, data, model)


async def run(env_file: Path, output: Path):
    settings = Settings(  # type: ignore[call-arg]
        _env_file=env_file,
        provider_max_attempts=1,
        max_llm_attempts_per_check=1,
        max_search_queries_per_claim=2,
        max_search_attempts_per_check=2,
    )
    if (
        not settings.gemini_api_key.get_secret_value()
        or not settings.tavily_api_key.get_secret_value()
    ):
        raise ValueError("Provider credentials are not configured")
    model = CapturingGemini(settings)
    search = BudgetedSearch(settings)
    search.budget = 2
    events = []
    capture = DiagnosticCapture(events)
    report = {
        "started_at": datetime.now(UTC).isoformat(),
        "limits": {"gemini": 1, "tavily": 2, "twilio": 0},
    }
    # Reserve the artifact before any paid attempt, and never overwrite a report.
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        logger.addHandler(capture)
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=create_app(settings, model, search)),
                base_url="http://acceptance.test",
                trust_env=False,
            ) as client:
                response = await client.post("/api/verify", json={"text": "Nana Patekar died"})
                report.update(http_status=response.status_code, result=response.json())
        finally:
            logger.removeHandler(capture)
            report.update(
                finished_at=datetime.now(UTC).isoformat(),
                diagnostics=events,
                assessment_payload=model.assessment_payload,
                actual_attempts={
                    "gemini": model.request_count,
                    "tavily": search.request_count,
                    "twilio": 0,
                },
            )
            json.dump(report, stream, ensure_ascii=False, indent=2)
    print(
        json.dumps(
            {
                "report": str(output),
                "actual_attempts": report["actual_attempts"],
                "status": report.get("result", {}).get("status", "failed"),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="Only after the owner approves this budget"
    )
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.live:
        parser.error("No request made: --live and prior owner approval are required")
    asyncio.run(run(args.env_file, args.output))
