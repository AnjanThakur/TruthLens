"""Regenerate only the separate alerts schema, without provider calls."""

import json
from pathlib import Path

from app.alerts_app import create_alerts_app


def main() -> None:
    target = Path(__file__).resolve().parents[2] / "docs" / "scam-alert-openapi.json"
    target.write_text(
        json.dumps(create_alerts_app().openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Updated separate alerts OpenAPI; existing verification contract unchanged.")


if __name__ == "__main__":
    main()
