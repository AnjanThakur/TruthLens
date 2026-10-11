"""Read-only public extraction check; no LLM/search calls or factual verdicts."""

import argparse
import asyncio
import json

from app.config import Settings
from app.errors import AppError
from app.services.extract.url import SafeFetcher, article_from_html


async def run(url):
    try:
        fetched = await SafeFetcher(Settings()).fetch(url)
        result = article_from_html(fetched.body, fetched.url, fetched.charset)
        print(
            json.dumps(
                {
                    "url": fetched.url,
                    "title": result.extraction_details.get("title"),
                    "published_at": result.extraction_details.get("published_at"),
                    "characters": len(result.text),
                    "status": "extracted",
                },
                ensure_ascii=False,
            )
        )
    except AppError as exc:
        print(json.dumps({"status": "unavailable", "code": exc.code, "message": exc.message}))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    asyncio.run(run(parser.parse_args().url))
