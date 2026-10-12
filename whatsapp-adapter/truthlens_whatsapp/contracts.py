"""Validate against Person 1's exported OpenAPI without importing their application."""

import copy
import json
from pathlib import Path

from .errors import ServiceError

SCHEMA = json.loads(
    (Path(__file__).parent / "backend-openapi.json").read_text(encoding="utf-8-sig")
)


def validate(value, name):
    # JSON Schema draft 2020-12 validates the exact exported Pydantic schema.
    from jsonschema import Draft202012Validator, FormatChecker

    schema = {"$ref": f"#/components/schemas/{name}", "components": SCHEMA["components"]}
    if not Draft202012Validator(schema, format_checker=FormatChecker()).is_valid(value):
        raise ServiceError("backend_contract")
    return value


def immutable(result):
    result = copy.deepcopy(result)
    for field in ("summary", "response_language", "audience"):
        result.pop(field, None)
    for claim in result["claims"]:
        for field in ("explanation", "short_summary", "key_points", "next_step"):
            claim.pop(field, None)
    return result
