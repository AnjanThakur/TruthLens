"""Explicit, budgeted selective acceptance; never runs live as part of pytest."""

import argparse
import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings
from app.errors import AppError
from app.main import create_app
from app.schemas.models import VerificationResult
from app.services.diagnostics import emit
from app.services.diagnostics import logger as diagnostic_logger
from app.services.providers import GeminiLLM
from app.services.search.client import TavilySearch

INPUTS = {
    "text": None,
    "image": "banknote.png",
    "audio": "voice-en.wav",
    "pdf": "banknote-scanned.pdf",
    "url": None,
    "hindi_image": "banknote-hi.png",
    "marathi_image": "banknote-mr.png",
}
FORMATS = set(INPUTS)
STOP_CODES = {
    "llm_quota_exhausted",
    "llm_rate_limited",
    "llm_live_budget_exhausted",
    "search_budget_exhausted",
    "search_rate_limited",
    "search_quota_exhausted",
}


class BudgetedGemini(GeminiLLM):
    budget = 12

    async def generate(self, *args, **kwargs):
        if self.request_count >= self.budget:
            raise AppError(
                "llm_live_budget_exhausted", "Selective acceptance model-call budget reached.", 503
            )
        return await super().generate(*args, **kwargs)

    def reserve_request(self):
        if self.request_count >= self.budget:
            raise AppError(
                "llm_live_budget_exhausted", "Selective acceptance model-call budget reached.", 503
            )
        super().reserve_request()


class BudgetedSearch(TavilySearch):
    budget = 5

    async def _search(self, query):
        if self.request_count >= self.budget:
            raise AppError(
                "search_budget_exhausted", "Selective acceptance search budget reached.", 503
            )
        return await super()._search(query)

    def reserve_request(self):
        if self.request_count >= self.budget:
            raise AppError(
                "search_budget_exhausted", "Selective acceptance search budget reached.", 503
            )
        super().reserve_request()


class DiagnosticCapture(logging.Handler):
    def __init__(self, events: list[dict[str, Any]]):
        super().__init__()
        self.events = events

    def emit(self, record):
        event = getattr(record, "truthlens_event", None)
        if isinstance(event, dict) and len(self.events) < 128:
            self.events.append(dict(event))


def stop_code(body: dict[str, Any]) -> str | None:
    codes = [body.get("error", {}).get("code", ""), *body.get("warnings", [])]
    return next((known for code in codes for known in STOP_CODES if known in code), None)


def acceptance(result: VerificationResult) -> tuple[str, list[str]]:
    reasons = []
    if result.status != "completed":
        reasons.append("Pipeline returned " + result.status + "; not full live acceptance.")
    if not result.claims or any(not claim.evidence for claim in result.claims):
        reasons.append("No checkable claim or no retrieved source ledger.")
    for claim in result.claims:
        if claim.original_span not in result.input.text:
            reasons.append("Original span is not anchored to submitted text.")
        for evidence in claim.evidence:
            if not evidence.url.startswith(("https://", "http://")) or not evidence.excerpt:
                reasons.append("Source attribution/excerpt is missing.")
    return ("FAIL" if reasons else "PASS"), reasons


async def run(
    formats: set[str] | list[str],
    languages: list[str],
    output: Path | None = None,
    model_budget: int = 12,
    search_budget: int = 5,
    *,
    final_pass: bool = False,
    audio_file: Path | None = None,
):
    ordered = (
        [kind for kind in INPUTS if kind in formats]
        if isinstance(formats, set)
        else list(dict.fromkeys(formats))
    )
    if not ordered or not set(ordered) <= FORMATS:
        raise ValueError("Unsupported or empty format selection")
    if final_pass and (
        ordered != ["audio", "text"]
        or languages != ["en"]
        or not 1 <= model_budget <= 5
        or not 1 <= search_budget <= 2
    ):
        raise ValueError(
            "Final pass requires audio,text; English; maximum five Gemini attempts and two searches"
        )
    settings = Settings(
        llm_timeout_seconds=60,
        url_timeout_seconds=15,
        request_timeout_seconds=180,
        provider_max_attempts=1,
        max_claims=1,
        max_evidence=3,
        max_search_queries_per_claim=2,
    )
    llm, search = BudgetedGemini(settings), BudgetedSearch(settings)
    llm.budget, search.budget = model_budget, search_budget
    app = create_app(settings, llm=llm, search=search)
    folder = Path(__file__).resolve().parents[1] / "demo-output" / "fixtures"
    output = output or folder.parent / (
        "acceptance-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + ".json"
    )
    events: list[dict[str, Any]] = []
    report: dict[str, Any] = {
        "checked_at": datetime.now(UTC).isoformat(),
        "scope": (
            "Final audio and counterclaim through actual FastAPI routes, maximum five Gemini attempts and two searches. Expected categories are acceptance criteria only; no verdict is forced. Stop on provider failure."
            if final_pass
            else "Production providers through actual FastAPI routes. Exact repeated text can reuse a recent successful check; cache metadata and original checked_at are retained. URL checks only the disclosed literal FAQ sentence."
        ),
        "budgets": {"gemini": model_budget, "tavily": search_budget},
        "selected_formats": ordered,
        "final_pass": final_pass,
        "diagnostics": events,
        "formats": {
            kind: {
                "status": "SKIPPED",
                "reason": "Not attempted",
                "stage": "pending",
                "input_format": kind,
                "gemini_http_requests": 0,
                "tavily_http_requests": 0,
            }
            for kind in ordered
        },
    }
    if final_pass:
        report["formats"]["audio"]["expected_spoken_text"] = (
            "One rupee notes in India are issued by the Government of India."
        )
        report["formats"]["text"]["test_input"] = (
            "One rupee notes in India are issued by the Reserve Bank of India."
        )

    def save():
        report["gemini_http_requests"] = llm.request_count
        report["tavily_http_requests"] = search.request_count
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def body(response: httpx.Response, record: dict[str, Any]) -> dict[str, Any]:
        stage = record["stage"]
        record.setdefault("http_statuses", {})[stage] = response.status_code
        record.setdefault("request_ids", {})[stage] = response.headers.get("x-request-id")
        parsed = response.json()
        if not isinstance(parsed, dict):
            raise ValueError("Expected response object")
        return parsed

    def failed(response: httpx.Response, parsed: dict[str, Any], record: dict[str, Any]) -> bool:
        stopping = stop_code(parsed)
        if stopping:
            record["stop_code"] = stopping
        if response.is_error:
            record.update(status="SKIPPED" if stopping else "FAIL", reason=parsed["error"]["code"])
        return response.is_error

    async def exercise(kind: str, record: dict[str, Any], client: httpx.AsyncClient):
        record.pop("reason", None)
        actual_kind = "image" if kind.endswith("_image") else kind
        text = "All Rs 500 notes will become invalid next Monday."
        if final_pass:
            text = "One rupee notes in India are issued by the Reserve Bank of India."
            record["expected_verdict"] = "verified" if kind == "audio" else "false"
        if kind != "text":
            record["stage"] = "extraction"
            if kind == "url":
                response = await client.post(
                    "/api/extract/url",
                    json={"url": "https://www.rbi.org.in/scripts/FS_FAQs.aspx?Id=136&fn=2753"},
                )
            else:
                path = audio_file if kind == "audio" and audio_file else folder / str(INPUTS[kind])
                if not path.is_file():
                    record.update(
                        status="SKIPPED", reason="Input fixture not supplied: " + path.name
                    )
                    return
                response = await client.post(
                    "/api/extract", files={"file": (path.name, path.read_bytes())}
                )
                record["input_file"] = path.name
            parsed = body(response, record)
            record["extraction"] = parsed
            if failed(response, parsed, record):
                return
            text = parsed["text"]
            if kind == "url":
                sentence = "₹1 notes issued by Government of India are also Legal Tender."
                text = sentence if sentence in text else ""
                record["verification_scope"] = text
            if not text:
                record.update(status="FAIL", reason="No text in selected extraction scope.")
                return
        record["stage"] = "verification"
        record["test_input"] = text
        response = await client.post(
            "/api/verify",
            json={
                "text": text,
                "input_type": actual_kind,
                "response_language": "en",
                "audience": "adult",
            },
        )
        parsed = body(response, record)
        record["verification"] = parsed
        if failed(response, parsed, record):
            return
        result = VerificationResult.model_validate(parsed)
        record["status"], record["reasons"] = acceptance(result)
        if final_pass and (
            len(result.claims) != 1 or result.claims[0].verdict != record["expected_verdict"]
        ):
            record["status"] = "FAIL"
            record["reasons"].append(
                "Actual verdict did not establish the expected factual category; no verdict was forced."
            )
        record["languages"] = {"en": result.model_dump(mode="json")}
        for language in languages:
            if language == "en" or record.get("stop_code"):
                continue
            record["stage"] = "explanation_" + language
            response = await client.post(
                "/api/explain",
                json={
                    "result": result.model_dump(mode="json"),
                    "language": language,
                    "audience": "adult",
                },
            )
            parsed = body(response, record)
            record["languages"][language] = parsed
            if response.is_error:
                record["status"] = "FAIL"
                record["reasons"].append("Explanation failed: " + parsed["error"]["code"])
                if stopping := stop_code(parsed):
                    record["stop_code"] = stopping
                continue
            changed = VerificationResult.model_validate(parsed)
            mutable = {"explanation", "short_summary", "key_points", "next_step"}
            for before, after in zip(result.claims, changed.claims, strict=True):
                if before.model_dump(exclude=mutable) != after.model_dump(exclude=mutable):
                    raise RuntimeError("Explanation changed immutable fields")
        record["stage"] = "completed"

    capture = DiagnosticCapture(events)
    diagnostic_logger.addHandler(capture)
    stopped = None
    try:
        save()  # Every selected format exists before any operation, including interruptions.
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test", timeout=190
        ) as client:
            for kind in ordered:
                record = report["formats"][kind]
                if stopped:
                    record.update(status="SKIPPED", reason="Stopped after " + stopped)
                else:
                    model_before, search_before = llm.request_count, search.request_count
                    diagnostic_before = len(events)
                    try:
                        await exercise(kind, record, client)
                    except Exception:
                        # Never serialize exception text: it can contain upstream bodies/keys.
                        record.update(
                            status="FAIL",
                            reason="runner_input_error",
                            reasons=[
                                "Unexpected failure during "
                                + record["stage"]
                                + "; other inputs continue."
                            ],
                        )
                        emit("acceptance_runner", "local_exception", "runner_input_error")
                    stopped = record.get("stop_code")
                    if final_pass and any(
                        e["category"]
                        in {"transient_server", "timeout", "authentication", "connection"}
                        for e in events[diagnostic_before:]
                    ):
                        stopped = "provider_unavailable_or_timeout"
                    record["gemini_http_requests"] = llm.request_count - model_before
                    record["tavily_http_requests"] = search.request_count - search_before
                print(kind, record["status"], "stage", record["stage"], flush=True)
                save()
    finally:
        try:
            save()
        finally:
            diagnostic_logger.removeHandler(capture)
    print(
        "Actual requests:",
        llm.request_count,
        "Gemini;",
        search.request_count,
        "Tavily. Report:",
        output,
        flush=True,
    )
    statuses = [record["status"] for record in report["formats"].values()]
    return 1 if "FAIL" in statuses else 2 if "SKIPPED" in statuses else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument(
        "--quota-available",
        action="store_true",
        help="Confirm available quota; no availability probe is performed.",
    )
    parser.add_argument(
        "--formats",
        default="text,image,audio,pdf,url",
        help="Comma-separated formats, executed in the specified order.",
    )
    parser.add_argument("--languages", default="en")
    parser.add_argument("--model-budget", type=int, default=12)
    parser.add_argument("--search-budget", type=int, default=5)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--final-pass",
        action="store_true",
        help="Audio then known counterclaim; strict maximum 5 Gemini attempts and 2 searches.",
    )
    parser.add_argument("--audio-file", type=Path)
    args = parser.parse_args()
    if not args.live or not args.quota_available:
        parser.error("Both --live and --quota-available are required; no provider calls were made.")
    formats, languages = args.formats.split(","), args.languages.split(",")
    if not formats or not set(formats) <= FORMATS or not set(languages) <= {"en", "hi", "mr"}:
        parser.error("Unsupported format or language.")
    if not 1 <= args.model_budget <= 20 or not 1 <= args.search_budget <= 10:
        parser.error("Model budget must be 1..20 and search budget 1..10.")
    raise SystemExit(
        asyncio.run(
            run(
                formats,
                languages,
                args.output,
                args.model_budget,
                args.search_budget,
                final_pass=args.final_pass,
                audio_file=args.audio_file,
            )
        )
    )
