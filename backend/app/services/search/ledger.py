import asyncio
import math
import re
from typing import cast
from urllib.parse import urlsplit

from app.config import Settings
from app.errors import AppError
from app.schemas.models import AtomicClaim, Evidence, ExtractionResult, Provenance, SourceType
from app.services.common import normalize, now
from app.services.extract.encoding import decode_web_text
from app.services.extract.url import SafeFetcher, article_from_html, canonical_url
from app.services.search.client import SearchHit, SearchProvider

# Deliberate institution registry; arbitrary .gov.in or lookalike domains do not qualify.
# This is publisher identity, not a guarantee of truth or relevance.
REGISTRY = {
    "rbi.org.in": ("Reserve Bank of India", "primary"),
    "pib.gov.in": ("Press Information Bureau", "primary"),
    "mohfw.gov.in": ("Ministry of Health and Family Welfare", "primary"),
    "education.gov.in": ("Ministry of Education", "primary"),
    "scholarships.gov.in": ("National Scholarship Portal", "primary"),
    "uidai.gov.in": ("UIDAI", "primary"),
    "who.int": ("World Health Organization", "primary"),
    "reuters.com": ("Reuters", "secondary"),
    "apnews.com": ("Associated Press", "secondary"),
    "bbc.com": ("BBC", "secondary"),
    "bbc.co.uk": ("BBC", "secondary"),
    "altnews.in": ("Alt News", "fact_check"),
    "boomlive.in": ("BOOM", "fact_check"),
}


def relevant_window(text: str, queries: list[str], limit: int = 5000) -> str:
    """Select a contiguous actual-text window, retaining excerpt provenance."""
    if len(text) <= limit:
        return text
    tokens = {word.casefold() for query in queries for word in re.findall(r"\w{3,}", query)}
    starts = list(range(0, len(text), max(1, limit // 2)))
    best = max(
        starts,
        key=lambda offset: len(
            tokens & set(re.findall(r"\w{3,}", text[offset : offset + limit].casefold()))
        ),
    )
    return text[best : best + limit]


def identity(url: str) -> tuple[str, str, str]:
    host = (urlsplit(url).hostname or "").lower()
    for domain, (name, kind) in REGISTRY.items():
        if host == domain or host.endswith("." + domain):
            return name, kind, "Reviewed institution domain registry: " + domain
    return host, "other", "Publisher domain only; authority has not been independently established."


class Ledger:
    def __init__(self, settings: Settings, search: SearchProvider, fetcher: SafeFetcher):
        self.settings, self.search, self.fetcher = settings, search, fetcher

    async def retrieve(self, claim: AtomicClaim) -> tuple[list[Evidence], list[str]]:
        hits = []
        warnings: list[str] = []
        # Query failures remain visible; successful queries may still provide evidence.
        for query in list(dict.fromkeys(claim.queries))[
            : self.settings.max_search_queries_per_claim
        ]:
            try:
                returned = await self.search.search(query)
                hits.extend(returned)
                warnings.extend(getattr(returned, "warnings", []))
            except AppError as exc:
                warnings.append(exc.code)
        unique: dict[str, SearchHit] = {}
        for hit in hits:
            if (
                not isinstance(hit, SearchHit)
                or not isinstance(hit.url, str)
                or not isinstance(hit.content, str)
                or not isinstance(hit.title, str)
                or not isinstance(hit.score, (int, float))
                or not math.isfinite(hit.score)
                or (hit.published_at is not None and not isinstance(hit.published_at, str))
            ):
                warnings.append("search_result_invalid_discarded")
                continue
            try:
                url = canonical_url(hit.url)
            except AppError:
                warnings.append("unsafe_search_result_discarded")
                continue
            if url not in unique or hit.score > unique[url].score:
                unique[url] = hit
        ranked = sorted(
            unique.items(),
            key=lambda x: (
                math.isfinite(x[1].score) and x[1].score >= 0.5,
                {"primary": 3, "secondary": 2, "fact_check": 2, "other": 0}[identity(x[0])[1]],
                x[1].score if math.isfinite(x[1].score) else 0,
            ),
            reverse=True,
        )[: self.settings.max_evidence]
        semaphore = asyncio.Semaphore(2)

        async def item(url, hit):
            async with semaphore:
                excerpt = normalize(hit.content)[:5000]
                title = hit.title[:500]
                published = hit.published_at
                updated = None
                incomplete = False
                provenance = "search_excerpt"
                final_url = url
                try:
                    fetched = await self.fetcher.fetch(url)
                    final_url = fetched.url
                    if fetched.content_type == "application/pdf":
                        # Search sources often link actual RBI circular PDFs.
                        from app.services.extract.media import pdf_extract

                        extracted = await asyncio.to_thread(
                            pdf_extract, fetched.body, self.settings
                        )
                    elif fetched.content_type == "text/plain":
                        decoded, _, lossy = decode_web_text(fetched.body, fetched.charset)
                        extracted = ExtractionResult(
                            text=normalize(decoded),
                            detected_language="und",
                            input_type="url",
                            warnings=["text_encoding_loss: Source decoding was incomplete."]
                            if lossy
                            else [],
                        )
                    else:
                        extracted = await asyncio.to_thread(
                            article_from_html, fetched.body, final_url, fetched.charset
                        )
                    excerpt = relevant_window(
                        extracted.text, claim.queries, self.settings.source_excerpt_chars
                    )
                    title = str(extracted.extraction_details.get("title") or title)[:500]
                    # Explicit page metadata supersedes search dates; inferred dates
                    # are never silently labeled publication/event dates.
                    published = extracted.extraction_details.get("published_at")
                    updated = extracted.extraction_details.get("updated_at")
                    incomplete = any(
                        "ocr_" in note
                        or note.startswith(
                            (
                                "article_content_incomplete",
                                "text_encoding_loss",
                                "extraction_text_truncated",
                                "pdf_page_limit",
                            )
                        )
                        for note in extracted.warnings
                    )
                    if incomplete:
                        warnings.append("source_content_incomplete")
                    published = str(published)[:100] if published is not None else None
                    provenance = "fetched_page"
                except AppError as exc:
                    warnings.append("source_page_unavailable:" + exc.code)
                    # Unsafe addresses are not even retained as usable snippets.
                    if exc.code == "unsafe_url":
                        return None
                if not excerpt.strip():
                    return None
                publisher, kind, basis = identity(final_url)
                if incomplete:
                    basis += "; incomplete_content: The fetched article/document did not provide full content."
                return Evidence(
                    title=title,
                    url=final_url,
                    publisher=publisher,
                    source_type=cast(SourceType, kind),
                    published_at=published,
                    updated_at=updated,
                    retrieved_at=now(),
                    excerpt=excerpt,
                    excerpt_provenance=cast(Provenance, provenance),
                    authority_basis=basis,
                    relevance_score=hit.score if math.isfinite(hit.score) else 0,
                )

        results = await asyncio.gather(*(item(url, hit) for url, hit in ranked))
        dedup = {}
        for evidence in results:
            if evidence and evidence.url not in dedup:
                dedup[evidence.url] = evidence
        if not dedup:
            warnings.append("no_usable_evidence_retrieved")
        return list(dedup.values()), list(dict.fromkeys(warnings))
