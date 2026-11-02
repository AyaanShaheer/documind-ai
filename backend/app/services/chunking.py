
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



def chunk_pages_by_tokens(
    pages: list[dict],
    tokenizer,
    max_tokens: int = 220,
    overlap_tokens: int = 30,
) -> list[dict]:
    """
    Token-aware chunking that preserves original text.

    Uses tokenizer offset mappings instead of decoding
    token IDs, avoiding loss of original capitalization.
    """

    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")

    if overlap_tokens < 0 or overlap_tokens >= max_tokens:
        raise ValueError(
            "overlap_tokens must be smaller than max_tokens"
        )

    if not getattr(tokenizer, "is_fast", False):
        raise ValueError(
            "A fast tokenizer with offset mappings is required"
        )

    chunks = []

    stride = max_tokens - overlap_tokens

    for page in pages:

        text = page.get("text", "")

        if not text.strip():
            continue

        encoded = tokenizer(
            text,
            add_special_tokens=False,
            return_offsets_mapping=True,
            truncation=False,
        )

        offsets = encoded["offset_mapping"]

        start = 0

        while start < len(offsets):

            end = min(
                start + max_tokens,
                len(offsets),
            )

            char_start = offsets[start][0]
            char_end = offsets[end - 1][1]

            chunk_content = text[
                char_start:char_end
            ].strip()

            if chunk_content:

                chunks.append({
                    "chunk_id": f"chunk-{len(chunks) + 1:06d}",
                    "page_number": page.get("page_number"),
                    "text": chunk_content,
                    "token_count": end - start,
                })

            if end == len(offsets):
                break

            start += stride

    return chunks

