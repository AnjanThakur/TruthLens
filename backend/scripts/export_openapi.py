import json
from pathlib import Path

from app.main import create_app

if __name__ == "__main__":
    target = Path(__file__).resolve().parents[2] / "docs" / "backend-openapi.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    spec = create_app().openapi()
    target.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    contract = target.with_name("backend-api-contract.md")
    marker = "<!-- GENERATED SCHEMAS -->"
    preamble = contract.read_text(encoding="utf-8").split(marker)[0]
    appendix = "\n## Generated exact schemas\n\nReferences resolve against `components.schemas` in backend-openapi.json. This appendix is generated from the application, not handwritten.\n"
    for name, schema in sorted(spec["components"]["schemas"].items()):
        appendix += (
            f"\n### {name}\n\n```json\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n```\n"
        )
    contract.write_text(preamble + marker + "\n" + appendix, encoding="utf-8")
    print(target)
