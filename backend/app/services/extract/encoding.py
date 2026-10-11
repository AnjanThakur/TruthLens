"""Decode bounded downloaded text once, before article and metadata parsing."""

import codecs
import re


def decode_web_text(
    body: bytes, charset: str | None = None, *, html: bool = False
) -> tuple[str, str, bool]:
    """Return text, encoding and whether bytes were lost; never guess from language.

    BOMs identify Unicode encodings. Valid UTF-8 takes precedence over stale legacy
    charset declarations; otherwise honor HTTP/HTML declarations using strict decoding.
    Undecodable input is explicitly marked incomplete by callers.
    """
    candidates = []
    for marker, encoding in (
        (codecs.BOM_UTF32_LE, "utf-32"),
        (codecs.BOM_UTF32_BE, "utf-32"),
        (codecs.BOM_UTF16_LE, "utf-16"),
        (codecs.BOM_UTF16_BE, "utf-16"),
        (codecs.BOM_UTF8, "utf-8-sig"),
    ):
        if body.startswith(marker):
            candidates.append(encoding)
            break
    declared = [charset] if charset else []
    if html:
        for tag in re.findall(rb"<meta\b[^>]*>", body[:4096], re.I):
            match = re.search(rb"\bcharset\s*=\s*[\"']?([\w.-]+)", tag, re.I)
            if match:
                declared.append(match[1].decode("ascii"))
    # UTF-16/32 without a BOM may still decode as UTF-8 containing NULs.
    if b"\0" in body[:4096]:
        candidates.extend(declared)
    candidates.extend(["utf-8", *declared])
    for encoding in dict.fromkeys(candidates):
        try:
            text = body.decode(encoding)
            return text, codecs.lookup(encoding).name, False
        except (LookupError, UnicodeError):
            continue
    return body.decode("utf-8", errors="replace"), "utf-8", True
