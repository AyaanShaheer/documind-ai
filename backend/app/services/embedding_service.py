
import logging

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import settings


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Load the embedding model once and reuse it.
    """

    logger.info(
        "Loading embedding model: %s",
        settings.embedding_model,
    )

    model = SentenceTransformer(
        settings.embedding_model,
        device="cpu",
    )

    logger.info(
        "Embedding model loaded. Max sequence length: %s",
        model.max_seq_length,
    )

    return model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Convert text chunks into normalized embeddings.

    Returns:
        A list of 384-dimensional vectors.
    """

    if not texts:
        return []

    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("Embedding inputs must be non-empty strings")

    model = get_embedding_model()

    # Check token lengths before encoding.
    # Avoid silently truncating document content.
    tokenized = model.tokenizer(
        texts,
        add_special_tokens=True,
        truncation=False,
        padding=False,
    )

    token_lengths = [
        len(input_ids)
        for input_ids in tokenized["input_ids"]
    ]

    max_length = model.max_seq_length

    oversized = [
        index
        for index, length in enumerate(token_lengths)
        if length > max_length
    ]

    if oversized:
        raise ValueError(
            f"Chunks {oversized} exceed the model's "
            f"maximum sequence length of {max_length} tokens. "
            "Reduce chunk size before embedding."
        )

    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    if embeddings.shape[1] != settings.embedding_dimension:
        raise RuntimeError(
            f"Expected {settings.embedding_dimension} dimensions, "
            f"received {embeddings.shape[1]}"
        )

    return embeddings.tolist()

