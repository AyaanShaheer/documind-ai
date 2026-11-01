
from typing import Optional


def chunk_text(
    text: str,
    chunk_size_words: int = 120,
    overlap_words: int = 25,
) -> list[str]:
    """
    Split text into overlapping word-based chunks.
    """

    if chunk_size_words <= 0:
        raise ValueError("Chunk size must be positive")

    if overlap_words < 0 or overlap_words >= chunk_size_words:
        raise ValueError(
            "Overlap must be non-negative and smaller than chunk size"
        )

    words = text.split()

    if not words:
        return []

    chunks = []
    start = 0

    while start < len(words):

        end = min(
            start + chunk_size_words,
            len(words),
        )

        chunk = " ".join(words[start:end]).strip()

        if chunk:
            chunks.append(chunk)

        if end == len(words):
            break

        start = end - overlap_words

    return chunks


def chunk_pages(
    pages: list[dict],
    chunk_size_words: int = 120,
    overlap_words: int = 25,
) -> list[dict]:
    """
    Chunk pages while preserving page numbers.

    Each page is chunked independently to avoid
    mixing page citations.
    """

    result = []

    for page in pages:

        page_number: Optional[int] = page.get("page_number")

        text = page.get("text", "")

        page_chunks = chunk_text(
            text,
            chunk_size_words,
            overlap_words,
        )

        for chunk in page_chunks:

            result.append({
                "chunk_id": f"chunk-{len(result) + 1:06d}",
                "page_number": page_number,
                "text": chunk,
            })

    return result
	
