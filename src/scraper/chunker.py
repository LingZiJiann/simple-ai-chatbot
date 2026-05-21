import hashlib
import re

from .schemas import Chunk, ScrapedPage

MIN_CHARS = 200
MAX_CHARS = 500


def chunk_page(enriched: ScrapedPage) -> list[Chunk]:
    fragments = _split(enriched.prod_desc)
    chunks = []
    for i, frag in enumerate(fragments):
        text = f"{enriched.page_title}: {frag}".strip()
        chunks.append(
            Chunk(
                chunk_id=hashlib.sha256(f"{enriched.url}#{i}".encode()).hexdigest()[
                    :16
                ],
                source_url=enriched.url,
                chunk_index=i,
                text=text,
                char_count=len(text),
                page_title=enriched.page_title,
                price_gbp=enriched.price_gbp,
            )
        )
    return chunks


def _split(text: str) -> list[str]:
    if not text.strip():
        return [""]
    if len(text) <= MIN_CHARS:
        return [text]
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    parts = paragraphs if len(paragraphs) > 1 else re.split(r"(?<=[.!?])\s+", text)
    result, buf = [], ""
    for part in parts:
        candidate = f"{buf} {part}".strip() if buf else part
        if len(candidate) > MAX_CHARS and buf:
            result.append(buf)
            buf = part
        else:
            buf = candidate
    if buf:
        result.append(buf)
    return result or [text]
