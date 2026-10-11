"""Explicit live API exercise. Does not assert a predetermined factual verdict."""

import argparse
import json
from pathlib import Path

import httpx

from app.schemas.models import VerificationResult


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="Explicitly enable real network/paid provider calls."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--image", type=Path)
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--pdf", type=Path)
    parser.add_argument(
        "--url", default="https://www.rbi.org.in/scripts/FS_FAQs.aspx?Id=136&fn=2753"
    )
    parser.add_argument(
        "--output", type=Path, help="Optional sensitive full results file; omitted by default."
    )
    args = parser.parse_args()
    if not args.live:
        parser.error("Pass --live to acknowledge real provider calls. Offline tests use pytest.")
    reports = {}
    failures = []
    with httpx.Client(base_url=args.base_url, timeout=300, trust_env=False) as client:
        health = client.get("/api/health")
        health.raise_for_status()
        print(json.dumps(health.json(), ensure_ascii=False))
        inputs = [
            (
                "text",
                "From Monday all ₹500 notes are invalid. RBI publishes currency notices. Forward to everyone!",
            )
        ]
        for kind in ("image", "audio", "pdf"):
            path = getattr(args, kind)
            if path is None:
                failures.append(kind + ": input fixture not supplied")
                continue
            with path.open("rb") as file:
                response = client.post("/api/extract", files={"file": (path.name, file)})
            if response.is_error:
                failures.append(kind + ":" + response.json()["error"]["code"])
                continue
            extracted = response.json()
            reports[kind + "_extraction"] = extracted
            inputs.append((kind, extracted["text"]))
        response = client.post("/api/extract/url", json={"url": args.url})
        if response.is_error:
            failures.append("url:" + response.json()["error"]["code"])
        else:
            reports["url_extraction"] = response.json()
            inputs.append(("url", response.json()["text"]))
        for kind, text in inputs:
            response = client.post(
                "/api/verify", json={"text": text, "input_type": kind, "response_language": "hi"}
            )
            if response.is_error:
                failures.append(kind + "_verification:" + response.json()["error"]["code"])
                continue
            result = VerificationResult.model_validate(response.json())
            reports[kind] = result.model_dump(mode="json")
            print(
                f"{kind}: {result.status}, {len(result.claims)} claims, "
                f"{sum(len(c.evidence) for c in result.claims)} real retrieved evidence items"
            )
            # Three actual languages, invariant core, no hard-coded expected verdict.
            for language in ("en", "hi", "mr"):
                translated = client.post(
                    "/api/explain",
                    json={"result": reports[kind], "language": language, "audience": "senior"},
                )
                if translated.is_error:
                    failures.append(kind + "_explanation_" + language)
                    continue
                changed = VerificationResult.model_validate(translated.json())
                for before, after in zip(result.claims, changed.claims, strict=True):
                    if (before.claim_id, before.verdict, before.evidence) != (
                        after.claim_id,
                        after.verdict,
                        after.evidence,
                    ):
                        raise RuntimeError("Explanation changed immutable verification fields")
                reports[kind + "_" + language] = changed.model_dump(mode="json")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    for failure in failures:
        print("INCOMPLETE: " + failure)
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
