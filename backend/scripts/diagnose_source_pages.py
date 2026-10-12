"""Read public source pages without search/model calls; never print page bodies."""

import asyncio
import json
import sys

from app.config import Settings
from app.errors import AppError
from app.services.extract.url import SafeFetcher
from app.services.search.client import SearchHit
from app.services.search.ledger import Ledger, identity


class NoSearch:
    async def search(self, query: str) -> list[SearchHit]:
        raise RuntimeError("Source diagnostics cannot call a search provider.")


async def main() -> None:
    settings = Settings(_env_file=None, gemini_api_key="", tavily_api_key="")
    ledger = Ledger(settings, NoSearch(), SafeFetcher(settings))
    rows = []
    for url in sys.argv[1:]:
        row = {"url": url, "publisher_type": identity(url)[1]}
        try:
            fetched, extracted = await ledger._page(url)
            row.update(
                status="PASS",
                final_url=fetched.url,
                text_chars=len(extracted.text),
                complete=extracted.extraction_details.get("content_complete", True),
                extraction=extracted.extraction_details.get("article_extraction"),
                published_at=extracted.extraction_details.get("published_at"),
                warnings=extracted.warnings,
                entity_present="nana patekar" in extracted.text.casefold(),
            )
        except AppError as exc:
            row.update(
                status="FAIL", code=exc.code, category=exc.category, http_status=exc.provider_status
            )
        rows.append(row)
    print(json.dumps({"provider_calls": 0, "source_checks": rows}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
