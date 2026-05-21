import hashlib
import re

from .schemas import Chunk, ScrapedPage

MIN_CHARS = 200
MAX_CHARS = 500


def chunk_page(enriched: ScrapedPage) -> list[Chunk]:
    """Convert a scraped page into semantically meaningful chunks.

    Splits the product description into chunks within size constraints and
    creates Chunk objects with metadata from the page.

    Args:
        enriched: A ScrapedPage object containing product information.

    Returns:
        A list of Chunk objects, each representing a portion of the page
        with associated metadata (URL, title, price, etc.).
    """
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
    """Split text into chunks respecting size constraints and semantic boundaries.

    Intelligently splits text by preferring paragraph breaks first, then
    sentences, while keeping chunk sizes between MIN_CHARS and MAX_CHARS.

    Args:
        text: The text to split into chunks.

    Returns:
        A list of text chunks, each within the size constraints. Returns
        a single-element list with the original text if it cannot be split.
    """
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
