"""Local semantic HTML fallback; never executes scripts or fetches linked content."""

from lxml import etree, html

from app.services.common import normalize
from app.services.extract.encoding import decode_web_text


def semantic_content(body: bytes | str) -> tuple[str, str | None, bool]:
    if isinstance(body, bytes):
        body = decode_web_text(body, html=True)[0]
    try:
        tree = html.fromstring(
            body.encode("utf-8"), parser=html.HTMLParser(no_network=True, encoding="utf-8")
        )
    except (etree.ParserError, ValueError):
        return "", None, False
    title = normalize(" ".join(tree.xpath("//title/text()")))[:500] or None
    scripts = bool(tree.xpath("//script"))
    app_shell = bool(tree.xpath("//*[@id='root' or @id='app' or @id='__next']"))
    noscript = " ".join(tree.xpath("//noscript//text()")).casefold()
    for element in tree.xpath(
        "//script|//style|//noscript|//nav|//header|//footer|//form|//aside|//template"
    ):
        element.drop_tree()
    for element in tree.xpath("//*[@hidden or @aria-hidden='true']"):
        element.drop_tree()
    for element in tree.xpath("//article|//main|//*[@itemprop='articleBody']")[:16]:
        text = normalize(element.text_content())
        if len(text) >= 40 and sum(c.isalpha() for c in text) >= 20:
            return text, title, False
    visible = normalize(tree.text_content())
    javascript = scripts and (app_shell or "javascript" in noscript) and len(visible) < 120
    return "", title, javascript
