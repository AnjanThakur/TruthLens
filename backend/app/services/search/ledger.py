import asyncio
import math
import re
from datetime import datetime
from typing import cast
from urllib.parse import urlsplit

from app.config import Settings
from app.errors import AppError
from app.schemas.models import AtomicClaim, Evidence, ExtractionResult, Provenance, SourceType
from app.services.cache import AsyncMemo
from app.services.common import normalize, now
from app.services.extract.encoding import decode_web_text
from app.services.extract.url import Fetched, SafeFetcher, article_from_html, canonical_url
from app.services.search.client import SearchHit, SearchProvider
from app.services.search.investigation import investigation_plan

# Deliberate institution registry; arbitrary .gov.in or lookalike domains do not qualify.
# This is publisher identity, not a guarantee of truth or relevance.
REGISTRY = {
    "rbi.org.in": ("Reserve Bank of India", "primary"),
    "pib.gov.in": ("Press Information Bureau", "primary"),
    "mohfw.gov.in": ("Ministry of Health and Family Welfare", "primary"),
    "education.gov.in": ("Ministry of Education", "primary"),
    "scholarships.gov.in": ("National Scholarship Portal", "primary"),
    "uidai.gov.in": ("UIDAI", "primary"),
    "eci.gov.in": ("Election Commission of India", "primary"),
    "sci.gov.in": ("Supreme Court of India", "primary"),
    "indiacode.nic.in": ("India Code", "primary"),
    "incometax.gov.in": ("Income Tax Department", "primary"),
    "pmkisan.gov.in": ("PM-Kisan official portal", "primary"),
    "finmin.gov.in": ("Ministry of Finance", "primary"),
    "meity.gov.in": ("Ministry of Electronics and Information Technology", "primary"),
    "cybercrime.gov.in": ("National Cyber Crime Reporting Portal", "primary"),
    "who.int": ("World Health Organization", "primary"),
    "reuters.com": ("Reuters", "secondary"),
    "apnews.com": ("Associated Press", "secondary"),
    "bbc.com": ("BBC", "secondary"),
    "bbc.co.uk": ("BBC", "secondary"),
    "altnews.in": ("Alt News", "fact_check"),
    "boomlive.in": ("BOOM", "fact_check"),
    "thehindu.com": ("The Hindu", "secondary"),
    "indianexpress.com": ("The Indian Express", "secondary"),
    "loksatta.com": ("Loksatta", "secondary"),
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
        self.pages = AsyncMemo[tuple[Fetched, ExtractionResult]](
            settings.verification_cache_ttl_seconds, settings.search_cache_entries
        )

    async def _page(self, url: str) -> tuple[Fetched, ExtractionResult]:
        async def download() -> tuple[Fetched, ExtractionResult]:
            fetched = await self.fetcher.fetch(url)
            if fetched.content_type == "application/pdf":
                from app.services.extract.media import pdf_extract

                extracted = await asyncio.to_thread(pdf_extract, fetched.body, self.settings)
            elif fetched.content_type == "text/plain":
                decoded, _, lossy = decode_web_text(fetched.body, fetched.charset)
                extracted = ExtractionResult(
                    text=normalize(decoded),
                    detected_language="und",
                    input_type="url",
                    warnings=["text_encoding_loss"] if lossy else [],
                )
            else:
                extracted = await asyncio.to_thread(
                    article_from_html, fetched.body, fetched.url, fetched.charset
                )
            extracted.extraction_details["source_retrieved_at"] = now().isoformat()
            return fetched, extracted

        result, _, _ = await self.pages.run(
            url,
            download,
            lambda value: (
                bool(value[1].text)
                and value[1].extraction_details.get("content_complete") is not False
                and not any(
                    note.startswith(
                        (
                            "ocr_",
                            "text_encoding_loss",
                            "extraction_text_truncated",
                            "pdf_page_limit",
                            "article_content_incomplete",
                        )
                    )
                    for note in value[1].warnings
                )
            ),
        )
        return result

    async def retrieve(
        self, claim: AtomicClaim, jurisdiction: str = "IN"
    ) -> tuple[list[Evidence], list[str]]:
        evidence: dict[str, Evidence] = {}
        attempted: set[str] = set()
        warnings: list[str] = []
        stages = investigation_plan(claim, jurisdiction)
        if self.settings.max_search_queries_per_claim == 2:
            # A two-search acceptance budget still checks both support and contradiction.
            stages = [stages[0], next(stage for stage in stages if stage.name == "contradiction")]
        for stage in stages[: self.settings.max_search_queries_per_claim]:
            # The extra fallback is for missing usable pages, not a mandatory paid call.
            if stage.name == "fallback" and any(
                e.source_type != "other"
                and e.excerpt_provenance == "fetched_page"
                and "incomplete_content:" not in e.authority_basis
                for e in evidence.values()
            ):
                break
            try:
                returned = await self.search.search(stage.query)
                warnings.extend(getattr(returned, "warnings", []))
            except AppError as exc:
                warnings.append(exc.code)
                if exc.code in {
                    "search_quota_exhausted",
                    "search_rate_limited",
                    "search_auth_error",
                    "search_budget_exhausted",
                    "search_live_budget_exhausted",
                }:
                    break
                continue
            fresh = []
            for hit in returned:
                if isinstance(hit, SearchHit):
                    try:
                        url = canonical_url(hit.url)
                    except (AppError, TypeError):
                        warnings.append("unsafe_search_result_discarded")
                        continue
                    if url in attempted:
                        continue
                fresh.append(hit)
            found, notes = await self._retrieve_hits(claim, fresh)
            warnings.extend(notes)
            attempted.update(canonical_url(hit.url) for hit in fresh if isinstance(hit, SearchHit))
            for source in found:
                source.authority_basis += "; investigation_stage=" + stage.name
                evidence.setdefault(source.url, source)
        if not evidence:
            warnings.append("no_usable_evidence_retrieved")
        # Identical syndicated passages do not provide independent corroboration.
        ranked = sorted(
            evidence.values(),
            key=lambda e: (
                {"primary": 3, "secondary": 2, "fact_check": 2, "other": 0}[e.source_type],
                e.relevance_score,
            ),
            reverse=True,
        )
        selected = ranked[:1]
        opposition = next(
            (
                e
                for e in ranked
                if e not in selected and "investigation_stage=contradiction" in e.authority_basis
            ),
            None,
        )
        if opposition and self.settings.max_evidence > 1:
            selected.append(opposition)
        selected.extend(e for e in ranked if e not in selected)
        fingerprints: set[str] = set()
        for source in selected:
            fingerprint = normalize(source.excerpt).casefold()
            if fingerprint in fingerprints:
                source.authority_basis += "; duplicated_passage: This passage is also present in another retrieved source; it is not independent corroboration."
            fingerprints.add(fingerprint)
        return selected[: self.settings.max_evidence], list(dict.fromkeys(warnings))

    async def _retrieve_hits(
        self, claim: AtomicClaim, hits: list[SearchHit]
    ) -> tuple[list[Evidence], list[str]]:
        warnings: list[str] = []
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
                retrieved_at = now()
                final_url = url
                try:
                    fetched, extracted = await self._page(url)
                    final_url = fetched.url
                    retrieved_at = datetime.fromisoformat(
                        extracted.extraction_details["source_retrieved_at"]
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
                    retrieved_at=retrieved_at,
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
        return list(dedup.values()), list(dict.fromkeys(warnings))
