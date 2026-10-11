import re
from dataclasses import dataclass

from app.errors import AppError


@dataclass
class TextChunk:
    text: str
    start: int
    end: int
    boundary_split: bool = False


def split_text(text: str, limit: int, maximum: int, overlap: bool = True) -> list[TextChunk]:
    """Prefer sentence/paragraph boundaries; retain overlapping context for long lines."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + limit, len(text))
        split = False
        if end < len(text):
            boundaries = [m.end() for m in re.finditer(r"\n\n|[.!?।]\s+", text[start:end])]
            candidates = [point for point in boundaries if point >= limit // 2]
            if candidates:
                end = start + candidates[-1]
            else:
                split = True
        chunks.append(TextChunk(text[start:end], start, end, split))
        if len(chunks) > maximum:
            raise AppError(
                "document_too_large",
                "This content exceeds the bounded chunk budget. Split it into smaller documents.",
                413,
            )
        start = end - min(1200, limit // 3) if split and overlap else end
    return chunks
