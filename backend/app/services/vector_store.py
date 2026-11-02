
import logging

from datetime import datetime, timezone

from opensearchpy.helpers import bulk

from app.core.config import settings
from app.services.opensearch_client import (
    get_opensearch_client,
)


logger = logging.getLogger(__name__)


def index_document_chunks(
    user_id: str,
    document_id: str,
    filename: str,
    chunks: list[dict],
    embeddings: list[list[float]],
) -> int:
    """
    Store document chunks and embeddings in OpenSearch.

    Deterministic IDs make retries idempotent:
    the same document/chunk combination is overwritten.
    """

    if len(chunks) != len(embeddings):
        raise ValueError(
            "Number of chunks and embeddings must match"
        )

    if not chunks:
        return 0

    client = get_opensearch_client()

    index_name = settings.opensearch_index_name

    actions = []

    created_at = datetime.now(
        timezone.utc
    ).isoformat()

    for chunk, embedding in zip(chunks, embeddings):

        if len(embedding) != settings.embedding_dimension:
            raise ValueError(
                f"Invalid embedding dimensions for "
                f"{chunk['chunk_id']}"
            )

        # Stable ID prevents duplicate documents on retries.
        vector_id = (
            f"{document_id}:{chunk['chunk_id']}"
        )

        source = {
            "chunk_id": chunk["chunk_id"],
            "document_id": document_id,
            "user_id": user_id,
            "filename": filename,
            "page_number": chunk.get("page_number"),
            "chunk_text": chunk["text"],
            "embedding": embedding,
            "created_at": created_at,
        }

        actions.append({
            "_op_type": "index",
            "_index": index_name,
            "_id": vector_id,
            "_source": source,
        })

    successful, errors = bulk(
        client,
        actions,
        chunk_size=100,
        refresh="wait_for",
        raise_on_error=False,
        request_timeout=60,
    )

    if errors:
        raise RuntimeError(
            f"OpenSearch indexing failed: {errors[:3]}"
        )

    logger.info(
        "Indexed %s chunks for document %s",
        successful,
        document_id,
    )

    return successful
