import json
import re
from datetime import datetime
from typing import Any

from lxml import etree, html

from app.services.extract.encoding import decode_web_text


def article_metadata(body: bytes | str) -> dict[str, Any]:
    """Read explicit publisher metadata only; event dates never follow from these."""
    result: dict[str, Any] = {
        "published_at": None,
        "updated_at": None,
        "event_date": None,
        "date_provenance": None,
        "content_restricted": False,
    }
    if isinstance(body, bytes):
        body = decode_web_text(body, html=True)[0]
    try:
        tree = html.fromstring(
            body.encode("utf-8"), parser=html.HTMLParser(no_network=True, encoding="utf-8")
        )
    except (etree.ParserError, ValueError):
        return result

    def assign(field: str, value: Any, provenance: str) -> None:
        if result.get(field) is not None or not isinstance(value, str):
            return
        if not re.match(r"^\d{4}-\d{2}-\d{2}(?:$|T| )", value) or len(value) > 100:
            return
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return
        result[field] = value
        result[field + "_provenance"] = provenance

    for element in tree.xpath("//meta"):
        name = (
            element.get("property") or element.get("name") or element.get("itemprop") or ""
        ).casefold()
        if name in {"article:published_time", "datepublished", "pubdate", "dcterms.created"}:
            assign("published_at", element.get("content"), "explicit_meta:" + name)
        if name in {"article:modified_time", "og:updated_time", "datemodified", "dcterms.modified"}:
            assign("updated_at", element.get("content"), "explicit_meta:" + name)
    visited = 0

    def inspect(node: Any, depth: int = 0) -> None:
        nonlocal visited
        visited += 1
        if depth > 8 or visited > 128:
            return
        if isinstance(node, list):
            for value in node:
                inspect(value, depth + 1)
        elif isinstance(node, dict):
            kind = node.get("@type", [])
            kinds = [kind] if isinstance(kind, str) else kind
            if isinstance(kinds, list) and any(
                value in {"Article", "NewsArticle", "BlogPosting", "Report"}
                for value in kinds
                if isinstance(value, str)
            ):
                assign("published_at", node.get("datePublished"), "explicit_jsonld:datePublished")
                assign("updated_at", node.get("dateModified"), "explicit_jsonld:dateModified")
                if node.get("isAccessibleForFree") in (False, "False", "false"):
                    result["content_restricted"] = True
            if "@graph" in node:
                inspect(node["@graph"], depth + 1)

    for element in tree.xpath("//script[@type='application/ld+json']")[:8]:
        raw = element.text or ""
        if len(raw) <= 200000:
            try:
                inspect(json.loads(raw))
            except (ValueError, RecursionError):
                pass
    result["date_provenance"] = result.get("published_at_provenance")
    return result
