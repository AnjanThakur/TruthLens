"""Explicit low-cost live credentials check; never prints keys or provider error bodies."""

import argparse
import asyncio
import json

from google import genai
from google.genai import errors, types

from app.config import Settings
from app.errors import AppError
from app.schemas.models import ClaimBatch
from app.services.providers import GeminiLLM
from app.services.search.client import TavilySearch


async def run(list_models=False, gemini_only=False):
    settings = Settings()
    if list_models:
        try:
            async with genai.Client(
                api_key=settings.gemini_api_key.get_secret_value(),
                http_options=types.HttpOptions(timeout=20000),
            ).aio as client:
                names = [
                    m.name
                    async for m in await client.models.list()
                    if m.name
                    and "flash" in m.name
                    and "image" not in m.name
                    and "tts" not in m.name
                    and "live" not in m.name
                ]
            print(json.dumps({"available_flash_models": names}))
        except errors.APIError as exc:
            text = str(exc).casefold()
            print(
                json.dumps(
                    {
                        "model_listing": "FAIL",
                        "upstream_status": exc.code,
                        "invalid_key": "api key" in text
                        and any(w in text for w in ["invalid", "not valid", "expired"]),
                        "schema_error": "schema" in text,
                        "quota_error": "quota" in text,
                    }
                )
            )
        except Exception:
            print(
                json.dumps(
                    {
                        "model_listing": "FAIL",
                        "reason": "Provider access/network failed; error body suppressed.",
                    }
                )
            )
        return
    for name in ("gemini",) if gemini_only else ("gemini", "tavily"):
        try:
            if name == "gemini":
                result = await GeminiLLM(settings).structured(
                    "Return zero checkable claims for a greeting. detected_language=en; truncated=false.",
                    {"text": "Good morning!"},
                    ClaimBatch,
                )
                print(
                    json.dumps(
                        {
                            "provider": name,
                            "status": "PASS",
                            "model": settings.gemini_model,
                            "claims": len(result.claims),
                        }
                    )
                )
            else:
                search = TavilySearch(settings)
                hits = await search.search(
                    "site:rbi.org.in currency banknotes 500 legal tender FAQ"
                )
                print(
                    json.dumps(
                        {
                            "provider": name,
                            "status": "PASS",
                            "results": len(hits),
                            "requests": search.request_count,
                            "depth": settings.search_depth,
                            "urls": [h.url for h in hits],
                        }
                    )
                )
        except AppError as exc:
            print(
                json.dumps(
                    {"provider": name, "status": "FAIL", "code": exc.code, "message": exc.message}
                )
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--gemini-only", action="store_true")
    args = parser.parse_args()
    if not args.live:
        parser.error("Pass --live to enable the real provider checks.")
    asyncio.run(run(args.list_models, args.gemini_only))
