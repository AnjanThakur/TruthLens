"""Run identical offline scenarios against preserved and feature backend code."""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def scenarios(backend: Path) -> dict:
    sys.path.insert(0, str(backend / "tests"))
    sys.path.insert(0, str(backend))
    import httpx
    from conftest import CLAIMS, StubFetcher, StubLLM, StubSearch, article
    from fastapi.testclient import TestClient

    from app.config import Settings
    from app.main import create_app
    from app.services.search.client import SearchHit

    def forbidden(*args, **kwargs):
        raise AssertionError("Before/after comparison is offline only")

    httpx.HTTPTransport.handle_request = forbidden
    httpx.AsyncHTTPTransport.handle_async_request = forbidden

    def settings(**kwargs):
        return Settings(_env_file=None, gemini_api_key="", tavily_api_key="", **kwargs)

    def check(config, model, search, fetcher, text=CLAIMS[0]):
        response = TestClient(create_app(config, model, search, fetcher)).post(
            "/api/verify", json={"text": text}
        )
        result = response.json()
        return {
            "status": result["status"],
            "verdict": result["claims"][0]["verdict"],
            "sources": len(result["claims"][0]["evidence"]),
        }

    class DelayedSearch(StubSearch):
        def __init__(self):
            super().__init__()
            self.calls = 0

        async def search(self, query):
            self.calls += 1
            return [] if self.calls == 1 else await super().search(query)

    urls = ["https://rbi.org.in/offline-history", "https://reuters.com/offline-current"]
    outdated = "The demo library currently opens at 10 am."
    pages = {
        urls[0]: article(
            "FICTIONAL ARCHIVE: Effective 1 October 2026 the demo library opened at 10 am."
        ),
        urls[1]: article(
            "FICTIONAL CURRENT RECORD: Effective 10 October 2026 the demo library opens at 9 am, replacing the previous 10 am time."
        ),
    }
    return {
        "low_score_official": check(
            settings(max_evidence=1),
            StubLLM([CLAIMS[0]]),
            StubSearch(
                [
                    SearchHit(
                        "https://unreviewed.example/a",
                        "Fictional other source",
                        "Snippet",
                        0.99,
                    ),
                    SearchHit(
                        "https://rbi.org.in/offline-only",
                        "Fictional official fixture",
                        "Snippet",
                        0.49,
                    ),
                ]
            ),
            StubFetcher(),
        ),
        "initial_query_empty": check(
            settings(), StubLLM([CLAIMS[0]]), DelayedSearch(), StubFetcher()
        ),
        "missing_reviewed_institution": check(
            settings(),
            StubLLM([CLAIMS[0]]),
            StubSearch(
                [
                    SearchHit(
                        "https://eci.gov.in/offline-only",
                        "Fictional institution fixture",
                        "Snippet",
                        0.9,
                    )
                ]
            ),
            StubFetcher(),
        ),
        "natural_event_dates": check(
            settings(),
            StubLLM(
                [outdated],
                verdict="outdated",
                stances=["context", "context"],
                dates=["2026-10-01", "2026-10-10"],
                current=True,
            ),
            StubSearch([SearchHit(url, "Fictional dated record", "Snippet", 0.9) for url in urls]),
            StubFetcher(pages),
            outdated,
        ),
    }


def compare(before: Path, after: Path, python: Path) -> dict:
    outcomes = []
    for root in (before, after):
        result = subprocess.run(  # noqa: S603 - local Python and this script, shell disabled.
            [str(python), str(Path(__file__).resolve()), "--backend", str(root)],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        outcomes.append(json.loads(result.stdout))
    cases = [
        {"scenario": key, "before": outcomes[0][key], "after": outcomes[1][key]}
        for key in outcomes[0]
    ]
    fixed = sum(
        item["before"]["verdict"] == "unconfirmed"
        and item["after"]["verdict"] != "unconfirmed"
        and item["after"]["status"] == "completed"
        for item in cases
    )
    return {
        "scope": "Identical deterministic fictional records; actual preserved backend code compared with feature backend code. Not live claim accuracy.",
        "status": "PASS" if fixed == 4 else "FAIL",
        "avoidable_scenarios_fixed": fixed,
        "cases": cases,
        "provider_requests": {"gemini": 0, "tavily": 0, "twilio": 0},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", type=Path)
    parser.add_argument("--before", type=Path)
    parser.add_argument("--after", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.backend:
        print(json.dumps(scenarios(args.backend), ensure_ascii=False))
    else:
        report = compare(args.before, args.after, Path(sys.executable))
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(
            f"{report['status']}: {report['avoidable_scenarios_fixed']} offline avoidable abstentions resolved."
        )
