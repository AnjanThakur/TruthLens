import asyncio
import ipaddress
import re
import socket
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import httpx

from app.config import Settings
from app.errors import AppError
from app.schemas.models import ExtractionResult
from app.services.common import detect_language, normalize
from app.services.diagnostics import emit
from app.services.extract.article_content import semantic_content
from app.services.extract.encoding import decode_web_text
from app.services.extract.metadata import article_metadata


def canonical_url(value: str) -> str:
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
            raise ValueError
        if parts.username is not None or parts.password is not None or "\\" in value:
            raise ValueError
        if any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ValueError
        if parts.port not in {None, 80, 443}:
            raise ValueError
        hostname = parts.hostname.encode("idna").decode("ascii").lower().rstrip(".")
        host = f"[{hostname}]" if ":" in hostname else hostname
        if parts.port and parts.port != (443 if parts.scheme == "https" else 80):
            host += f":{parts.port}"
        query = [
            (k, v)
            for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}
        ]
        return urlunsplit((parts.scheme.lower(), host, parts.path or "/", urlencode(query), ""))
    except (ValueError, UnicodeError) as exc:
        raise AppError(
            "unsafe_url", "Use a public HTTP/HTTPS URL without credentials or custom ports."
        ) from exc


def is_public_ip(value: str) -> bool:
    address = ipaddress.ip_address(value)
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return address.is_global and not address.is_multicast and not address.is_reserved


class Resolver(Protocol):
    async def resolve(self, host: str, port: int) -> list[str]: ...


class DNSResolver:
    async def resolve(self, host: str, port: int) -> list[str]:
        try:
            results = await asyncio.wait_for(
                asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM),
                5,
            )
            return list(dict.fromkeys(str(x[4][0]) for x in results))
        except (OSError, TimeoutError) as exc:
            raise AppError(
                "url_dns_error",
                "The public site's address could not be resolved.",
                502,
                category="dns_failure",
            ) from exc


@dataclass
class Fetched:
    url: str
    body: bytes
    content_type: str
    charset: str | None = None


class SafeFetcher:
    def __init__(
        self,
        settings: Settings,
        resolver: Resolver | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.settings = settings
        self.resolver = resolver or DNSResolver()
        self.transport = transport

    async def fetch(self, url: str) -> Fetched:
        # One whole-operation deadline, including slow streaming and redirect chains.
        try:
            async with asyncio.timeout(
                self.settings.url_timeout_seconds or self.settings.external_timeout_seconds
            ):
                return await self._fetch(url)
        except TimeoutError as exc:
            raise AppError(
                "url_timeout", "The public site took too long to respond.", 504, category="deadline"
            ) from exc

    async def _fetch(self, url: str) -> Fetched:
        current = canonical_url(url)
        for _ in range(4):
            parsed = urlsplit(current)
            host = parsed.hostname or ""
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            addresses = await self.resolver.resolve(host, port)
            if not addresses or any(not is_public_ip(ip) for ip in addresses):
                raise AppError(
                    "unsafe_url", "Private, local and reserved network addresses are blocked."
                )
            # Connect to a validated literal IP, not a second DNS lookup. TLS still
            # verifies the original hostname through httpcore's SNI extension.
            pinned = httpx.URL(current).copy_with(host=addresses[0])
            headers = {
                "Host": parsed.netloc,
                "User-Agent": "TruthLens/0.1 article-reader",
                "Accept-Encoding": "identity",
            }
            try:
                async with httpx.AsyncClient(
                    timeout=self.settings.url_timeout_seconds
                    or self.settings.external_timeout_seconds,
                    trust_env=False,
                    follow_redirects=False,
                    transport=self.transport,
                ) as client:
                    async with client.stream(
                        "GET", pinned, headers=headers, extensions={"sni_hostname": host}
                    ) as response:
                        if response.status_code in {301, 302, 303, 307, 308}:
                            location = response.headers.get("location")
                            if not location:
                                raise AppError(
                                    "url_redirect_error",
                                    "The site returned an incomplete redirect.",
                                    502,
                                )
                            current = canonical_url(urljoin(current, location))
                            continue
                        if response.status_code >= 400:
                            status = response.status_code
                            category = (
                                "access_denied"
                                if status in {401, 403}
                                else "not_found"
                                if status in {404, 410}
                                else "rate_limited"
                                if status == 429
                                else "transient_server"
                                if status >= 500
                                else "http_rejected"
                            )
                            raise AppError(
                                "url_fetch_error",
                                "The source rejected the download.",
                                502,
                                category=category,
                                provider_status=status,
                            )
                        if response.headers.get("content-encoding", "identity").lower() not in {
                            "",
                            "identity",
                        }:
                            raise AppError(
                                "url_encoding_unsupported",
                                "The site ignored the bounded uncompressed download request.",
                                422,
                            )
                        kind = response.headers.get("content-type", "").split(";")[0].lower()
                        if kind not in {
                            "text/html",
                            "application/xhtml+xml",
                            "text/plain",
                            "application/pdf",
                            "application/octet-stream",
                        }:
                            raise AppError(
                                "url_content_unsupported",
                                "This link is not an article, text page or PDF.",
                                415,
                            )
                        chunks = bytearray()
                        async for chunk in response.aiter_bytes():
                            if len(chunks) + len(chunk) > self.settings.max_url_bytes:
                                raise AppError(
                                    "url_too_large",
                                    "This page exceeds the safe download limit.",
                                    413,
                                )
                            chunks.extend(chunk)
                        if bytes(chunks[:5]) == b"%PDF-":
                            kind = "application/pdf"
                        elif kind == "application/octet-stream":
                            raise AppError(
                                "url_content_unsupported",
                                "The binary link is not a supported PDF.",
                                415,
                            )
                        return Fetched(current, bytes(chunks), kind, response.charset_encoding)
            except httpx.TimeoutException as exc:
                raise AppError(
                    "url_timeout",
                    "The public site took too long to respond.",
                    504,
                    category="timeout",
                ) from exc
            except httpx.ConnectError as exc:
                raise AppError(
                    "url_fetch_error",
                    "The source connection could not be established.",
                    502,
                    category="connection_failed",
                ) from exc
            except httpx.HTTPError as exc:
                raise AppError(
                    "url_fetch_error",
                    "The public page could not be downloaded safely.",
                    502,
                    category="transport_error",
                ) from exc
        raise AppError("url_redirect_limit", "The site redirected too many times.", 422)


def article_from_html(body: bytes, url: str, charset: str | None = None) -> ExtractionResult:
    decoded, encoding, lossy = decode_web_text(body, charset, html=True)
    fallback, fallback_title, javascript = semantic_content(decoded)
    mode = "precision"
    try:
        import trafilatura
    except ImportError as exc:
        raise AppError(
            "article_extraction_unavailable",
            "Install trafilatura to read public article pages.",
            503,
        ) from exc
    try:
        document = trafilatura.bare_extraction(
            decoded, with_metadata=True, favor_precision=True, include_comments=False
        )
        if document is None or isinstance(document, dict) or not document.text:
            mode = "recall"
            document = trafilatura.bare_extraction(
                decoded, with_metadata=True, favor_recall=True, include_comments=False
            )
    except Exception:
        raise AppError(
            "url_extraction_failed", "The article could not be parsed safely.", 422
        ) from None
    text = (
        normalize(document.text)
        if document is not None and not isinstance(document, dict) and document.text
        else ""
    )
    if not text and fallback:
        text, mode = fallback, "semantic_html_fallback"
    if javascript and not fallback:
        emit("article_extraction", "javascript_required", "url_no_text")
        raise AppError(
            "url_no_text",
            "This page requires JavaScript and supplied no readable article HTML. Use a public article or PDF link.",
            422,
            category="javascript_required",
        )
    if not text:
        emit("article_extraction", "empty_article", "url_no_text")
        raise AppError(
            "url_no_text",
            "No readable article text was found on this page.",
            422,
            category="empty_article",
        )
    # Remove only empty layout-table rows, preserving all actual cell text.
    text = normalize(re.sub(r"(?m)^[ \t|]+$", "", text))
    if not text or (
        len(text) < 500
        and any(
            phrase in text.casefold()
            for phrase in (
                "verify you are human",
                "checking your browser",
                "enable javascript",
                "access denied",
                "sign in to continue",
                "subscribe to continue",
            )
        )
    ):
        emit("article_extraction", "access_shell", "url_no_text")
        raise AppError(
            "url_no_text",
            "The site returned an access or browser-check page, not readable article content.",
            422,
            category="access_shell",
        )
    metadata = article_metadata(decoded)
    notes = []
    if lossy:
        notes.append(
            "text_encoding_loss: Some downloaded bytes could not be decoded; review the source."
        )
    if metadata["content_restricted"]:
        notes.append("article_content_incomplete: Publisher metadata indicates restricted content.")
    short = len(text) < 200
    if short:
        notes.append(
            "article_short_content: Only a short passage was extracted; review its completeness."
        )
    return ExtractionResult(
        text=text,
        detected_language=getattr(document, "language", None) or detect_language(text),
        input_type="url",
        warnings=notes,
        extraction_details={
            "url": url,
            "title": getattr(document, "title", None) or fallback_title,
            "publisher": getattr(document, "sitename", None) or urlsplit(url).hostname,
            "author": getattr(document, "author", None),
            "article_extraction": mode,
            "text_encoding": encoding,
            **metadata,
            "full_text_chars": len(text),
            # A brief semantic article/notice can be complete. A short generic
            # extraction (e.g. video-player chrome) cannot claim completeness.
            "content_complete": not metadata["content_restricted"]
            and not lossy
            and not (short and not fallback),
        },
    )
