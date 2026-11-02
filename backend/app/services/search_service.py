import logging
import re
from datetime import datetime, timezone

from app.core.config import settings
from app.services.embedding_service import embed_texts
from app.services.opensearch_client import get_opensearch_client


logger = logging.getLogger(__name__)


STOP_WORDS = {
    "what", "is", "the", "for", "a", "an", "in", "on",
    "of", "to", "my", "does", "do", "can", "could",
    "should", "please", "where", "when", "who", "which",
    "how", "me", "about", "available", "document",
    "documents", "uploaded", "information", "tell",
    "show", "give", "explain", "describe",
}


def _timestamp_rank(value: str | None) -> float:
    """Convert an ISO timestamp into a comparable numeric value."""

    if not value:
        return 0.0

    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed.timestamp()

    except (ValueError, OverflowError):
        return 0.0


def _normalize_chunk_text(text: str) -> str:
    """Normalize text for duplicate detection only."""

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip().casefold()


def _content_terms(text: str) -> set[str]:
    """
    Extract meaningful words for lexical relevance scoring.

    Basic plural normalization helps match words such as
    'incidents' with 'incident'.
    """

    tokens = re.findall(
        r"[a-z0-9]+",
        text.casefold(),
    )

    terms = set()

    for token in tokens:

        if token in STOP_WORDS:
            continue

        if token.endswith("s") and len(token) > 4:
            token = token[:-1]

        terms.add(token)

    return terms


def semantic_search(
    question: str,
    user_id: str,
    top_k: int = 5,
) -> list[dict]:
    """
    Retrieve relevant document chunks.

    Features:
    - User-level filtering.
    - Semantic vector retrieval.
    - Candidate over-fetching.
    - Duplicate chunk detection.
    - Newest-version preference for identical content.
    - Lightweight lexical and semantic re-ranking.

    Original document text is never modified.
    """

    question = question.strip()

    if not question:
        raise ValueError(
            "Search question cannot be empty"
        )

    if top_k < 1:
        raise ValueError(
            "top_k must be at least 1"
        )

    # ==========================================
    # STEP 1: GENERATE QUESTION EMBEDDING
    # ==========================================

    query_vector = embed_texts([question])[0]

    # ==========================================
    # STEP 2: CONNECT TO OPENSEARCH
    # ==========================================

    client = get_opensearch_client()

    # Retrieve more candidates than requested.
    candidate_k = min(top_k * 10, 100)

    # ==========================================
    # STEP 3: PERFORM USER-FILTERED VECTOR SEARCH
    # ==========================================

    query = {
        "size": candidate_k,

        "_source": [
            "document_id",
            "user_id",
            "filename",
            "page_number",
            "chunk_text",
            "created_at",
        ],

        "query": {
            "knn": {
                "embedding": {
                    "vector": query_vector,
                    "k": candidate_k,

                    "filter": {
                        "term": {
                            "user_id": user_id
                        }
                    },
                }
            }
        },
    }

    response = client.search(
        index=settings.opensearch_index_name,
        body=query,
    )

    hits = response["hits"]["hits"]

    # ==========================================
    # STEP 4: DEDUPLICATE IDENTICAL CHUNKS
    # ==========================================

    unique_chunks = {}

    for hit in hits:

        source = hit["_source"]

        chunk_text = source.get("chunk_text", "")

        normalized_text = _normalize_chunk_text(
            chunk_text
        )

        dedupe_key = (
            normalized_text
            if normalized_text
            else hit["_id"]
        )

        created_at = source.get("created_at", "")

        timestamp_rank = _timestamp_rank(
            created_at
        )

        result = {
            "document_id": source["document_id"],
            "filename": source["filename"],
            "page_number": source.get("page_number"),
            "chunk_text": chunk_text,
            "score": hit["_score"],
        }

        existing = unique_chunks.get(dedupe_key)

        if existing is None:

            unique_chunks[dedupe_key] = (
                timestamp_rank,
                result,
            )

        else:

            existing_timestamp, existing_result = existing

            if (
                timestamp_rank > existing_timestamp
                or (
                    timestamp_rank == existing_timestamp
                    and result["score"] > existing_result["score"]
                )
            ):

                unique_chunks[dedupe_key] = (
                    timestamp_rank,
                    result,
                )

    unique_results = [
        item[1]
        for item in unique_chunks.values()
    ]

    # ==========================================
    # STEP 5: CALCULATE SEMANTIC RANK
    # ==========================================

    semantic_order = sorted(
        unique_results,
        key=lambda item: item["score"],
        reverse=True,
    )

    denominator = max(
        len(semantic_order) - 1,
        1,
    )

    semantic_ranks = {
        id(item): 1.0 - (rank / denominator)
        for rank, item in enumerate(semantic_order)
    }

    # ==========================================
    # STEP 6: CALCULATE LEXICAL RELEVANCE
    # ==========================================

    question_terms = _content_terms(question)

    ranked_results = []

    for result in unique_results:

        chunk_terms = _content_terms(
            result["chunk_text"]
        )

        if question_terms:

            matching_terms = (
                question_terms & chunk_terms
            )

            lexical_score = (
                len(matching_terms)
                / len(question_terms)
            )

        else:

            lexical_score = 0.0

        semantic_score = semantic_ranks[id(result)]

        # Blended relevance:
        # 60% lexical evidence, 40% semantic ranking.
        combined_score = (
            0.60 * lexical_score
            + 0.40 * semantic_score
        )

        ranked_results.append(
            (combined_score, result)
        )

    # ==========================================
    # STEP 7: SORT BY COMBINED RELEVANCE
    # ==========================================

    ranked_results.sort(
        key=lambda item: (
            item[0],
            item[1]["score"],
        ),
        reverse=True,
    )

    results = [
        item[1]
        for item in ranked_results[:top_k]
    ]

    # ==========================================
    # STEP 8: LOG SEARCH RESULTS
    # ==========================================

    logger.info(
        "Semantic search completed: "
        "user=%s candidates=%s unique=%s returned=%s",
        user_id,
        len(hits),
        len(unique_results),
        len(results),
    )

    return results
