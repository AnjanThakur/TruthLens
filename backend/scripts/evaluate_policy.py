"""Offline guard conformance; never a Gemini accuracy benchmark."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.schemas.models import AtomicClaim, Decision, Evidence
from app.services.verify.engine import guard_decision

LABELS = ["verified", "false", "partially_true", "outdated", "misleading_context", "unconfirmed"]
ROOT = Path(__file__).resolve().parents[1] / "evaluation"


def predict(case: dict, proposal: dict) -> str:
    """No expected label is consulted when constructing or validating the proposal."""
    identifiers = {source["id"]: str(uuid4()) for source in case["sources"]}
    evidence = [
        Evidence(
            evidence_id=identifiers[source["id"]],
            title="Fictional evaluation record",
            url="https://example.org/truthlens-offline/" + source["id"],
            publisher="FICTIONAL FIXTURE PUBLISHER",
            source_type=source["kind"],
            excerpt_provenance=source["provenance"],
            retrieved_at=datetime(2026, 10, 11, tzinfo=UTC),
            excerpt=source["text"],
            authority_basis="Offline authority annotation, not a real retrieved source.",
        )
        for source in case["sources"]
    ]
    claim = AtomicClaim(
        claim_text=case["claim"],
        original_span=case["claim"],
        entities=["Demo Civic Centre"],
        dates=[],
        qualifiers=[],
        queries=[case["claim"]],
        current_assertion=True,
    )
    decision = Decision(
        verdict=proposal["verdict"],
        explanation="Offline proposal, evaluated against the supplied fictional records.",
        short_summary="Offline proposal.",
        key_points=[],
        assessments=[
            {
                "evidence_id": identifiers[source["id"]],
                "stance": source["stance"],
                "excerpt": source["text"],
                "what_source_says": source["text"],
                "directly_relevant": source["relevant"],
            }
            for source in case["sources"]
        ],
        decisive_evidence_ids=list(identifiers.values()),
        component_assessments=[
            {
                "original_span": component["span"],
                "status": component["status"],
                "evidence_ids": [identifiers[component["source"]]],
            }
            for component in proposal.get("components", [])
        ],
        temporal_witnesses=[
            {
                "evidence_id": identifiers[w["source"]],
                "event_date": w["date"],
                "role": w["role"],
                "excerpt": next(s["text"] for s in case["sources"] if s["id"] == w["source"]),
            }
            for w in proposal.get("witnesses", [])
        ],
        relevant_source_dates=[w["date"] for w in proposal.get("witnesses", [])],
        limitations=[],
        temporal_notes="",
        context_evidence_ids=[],
    )
    return guard_decision(claim, decision, evidence)[0]


def evaluate() -> dict:
    dataset = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))
    proposals = json.loads((ROOT / "proposals.json").read_text(encoding="utf-8"))
    matrix = {expected: {actual: 0 for actual in LABELS} for expected in LABELS}
    results = []
    for case in dataset["cases"]:
        actual = predict(case, proposals[case["id"]])
        matrix[case["expected"]][actual] += 1
        results.append(
            {
                "id": case["id"],
                "expected": case["expected"],
                "actual": actual,
                "status": "PASS" if actual == case["expected"] else "FAIL",
                "source_justification": case["justification"],
            }
        )
    categories = {}
    for label in LABELS:
        tp = matrix[label][label]
        selected = sum(row[label] for row in matrix.values())
        support = sum(matrix[label].values())
        categories[label] = {
            "support": support,
            "precision": tp / selected if selected else None,
            "recall": tp / support if support else None,
        }
    return {
        "scope": dataset["scope"],
        "metric_interpretation": "Small deterministic guard-policy conformance set. Expected labels are independent of the adversarial proposal file. These metrics do not measure Gemini, real search quality, or population factual accuracy.",
        "status": "PASS" if all(row["status"] == "PASS" for row in results) else "FAIL",
        "cases": results,
        "categories": categories,
        "confusion_matrix": matrix,
        "abstention_rate": sum(row["actual"] == "unconfirmed" for row in results) / len(results),
        "provider_requests": {"gemini": 0, "tavily": 0, "twilio": 0},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "policy-results.json")
    args = parser.parse_args()
    report = evaluate()
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"{report['status']}: {len(report['cases'])} offline policy cases; zero provider requests."
    )
    raise SystemExit(0 if report["status"] == "PASS" else 1)
