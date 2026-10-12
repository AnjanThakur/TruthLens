from scripts.evaluate_policy import evaluate


def test_independent_policy_fixture_labels_and_adversarial_proposals():
    report = evaluate()
    assert report["status"] == "PASS"
    assert len(report["cases"]) == 14
    assert all(category["support"] > 0 for category in report["categories"].values())
    assert all(row["source_justification"] for row in report["cases"])
    assert report["provider_requests"] == {"gemini": 0, "tavily": 0, "twilio": 0}
