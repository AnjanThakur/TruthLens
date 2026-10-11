import asyncio
import math
import time
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.config import Settings
from app.errors import AppError


@dataclass
class SearchHit:
    url: str
    title: str
    content: str
    score: float = 0
    published_at: str | None = None


class SearchProvider(Protocol):
    async def search(self, query: str) -> list[SearchHit]: ...


class SearchResults(list[SearchHit]):
    def __init__(self, hits: list[SearchHit], warnings: list[str]):
        super().__init__(hits)
        self.warnings = warnings


class TavilySearch:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.transport = transport
        self._cache: OrderedDict[str, tuple[float, list[SearchHit]]] = OrderedDict()
        self._lock = asyncio.Lock()
        self.request_count = 0

    def reserve_request(self) -> None:
        self.request_count += 1

    async def search(self, query: str) -> list[SearchHit]:
        if not self.settings.tavily_api_key.get_secret_value():
            raise AppError(
                "search_unavailable", "Set TAVILY_API_KEY to retrieve source evidence.", 503
            )
        key = " ".join(query.casefold().split())
        async with self._lock:
            cached = self._cache.get(key)
            if cached and time.monotonic() - cached[0] < self.settings.search_cache_ttl_seconds:
                self._cache.move_to_end(key)
                return deepcopy(cached[1])
            self._cache.pop(key, None)
            hits = await self._search(query)
            if self.settings.search_cache_ttl_seconds:
                self._cache[key] = (time.monotonic(), deepcopy(hits))
                while len(self._cache) > self.settings.search_cache_entries:
                    self._cache.popitem(last=False)
            return hits

    async def _search(self, query: str) -> list[SearchHit]:
        async with httpx.AsyncClient(
            timeout=self.settings.external_timeout_seconds,
            trust_env=False,
            transport=self.transport,
        ) as client:
            for attempt in range(self.settings.provider_max_attempts):
                try:
                    self.reserve_request()
                    response = await client.post(
                        "https://api.tavily.com/search",
                        json={
                            "api_key": self.settings.tavily_api_key.get_secret_value(),
                            "query": query,
                            "search_depth": self.settings.search_depth,
                            "max_results": self.settings.max_evidence,
                            "include_answer": False,
                            "include_raw_content": False,
                        },
                    )
                    if (
                        response.status_code in {429, 502, 503, 504}
                        and attempt + 1 < self.settings.provider_max_attempts
                    ):
                        await asyncio.sleep(0.5)
                        continue
                    if response.status_code == 429:
                        raise AppError(
                            "search_rate_limited",
                            "Tavily's quota or rate limit was reached. Wait and retry.",
                            503,
                        )
                    if response.status_code in {401, 403}:
                        raise AppError(
                            "search_auth_error",
                            "Tavily rejected the configured credential or access.",
                            503,
                        )
                    response.raise_for_status()
                    items = response.json()["results"]
                    if not isinstance(items, list):
                        raise ValueError
                    hits, warnings = [], []
                    for item in items[: self.settings.max_evidence]:
                        try:
                            if (
                                not isinstance(item, dict)
                                or not isinstance(item.get("url"), str)
                                or not 1 <= len(item["url"]) <= 2048
                            ):
                                raise ValueError
                            title, content = item.get("title", ""), item.get("content", "")
                            if not isinstance(title, str) or not isinstance(content, str):
                                raise ValueError
                            score = float(item.get("score", 0))
                            published = item.get("published_date")
                            if published is not None and (
                                not isinstance(published, str) or len(published) > 100
                            ):
                                published = None
                                warnings.append("search_date_invalid_discarded")
                            hits.append(
                                SearchHit(
                                    item["url"],
                                    title[:500],
                                    content[:5000],
                                    score if math.isfinite(score) else 0,
                                    published,
                                )
                            )
                        except (ValueError, TypeError):
                            warnings.append("search_result_invalid_discarded")
                    return SearchResults(hits, list(dict.fromkeys(warnings)))
                except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                    raise AppError(
                        "search_provider_error",
                        "Search is unavailable. No conclusion can be drawn from this failure.",
                        502,
                    ) from exc
        return []
