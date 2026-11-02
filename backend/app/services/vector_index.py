
import logging

from app.core.config import settings
from app.services.opensearch_client import (
    get_opensearch_client,
)


logger = logging.getLogger(__name__)


def ensure_vector_index():
    """
    Create the DocuMind vector index if it doesn't exist.

    Validate the embedding dimension if it already exists.
    """

    client = get_opensearch_client()

    index_name = settings.opensearch_index_name

    if client.indices.exists(index=index_name):

        mapping = client.indices.get_mapping(
            index=index_name
        )

        properties = (
            mapping[index_name]["mappings"]["properties"]
        )

        dimension = properties["embedding"]["dimension"]

        if dimension != settings.embedding_dimension:

            raise ValueError(
                f"Index dimension mismatch: "
                f"expected {settings.embedding_dimension}, "
                f"found {dimension}"
            )

        logger.info(
            "Vector index already exists: %s",
            index_name,
        )

        return

    index_body = {

        "settings": {

            "index": {
                "knn": True,
                "number_of_shards": 1,
                "number_of_replicas": 0,
            }

        },

        "mappings": {

            "properties": {

                "chunk_id": {
                    "type": "keyword"
                },

                "document_id": {
                    "type": "keyword"
                },

                "user_id": {
                    "type": "keyword"
                },

                "filename": {
                    "type": "keyword"
                },

                "page_number": {
                    "type": "integer"
                },

                "chunk_text": {
                    "type": "text"
                },

                "embedding": {

                    "type": "knn_vector",

                    "dimension": settings.embedding_dimension,

                    "method": {

                        "name": "hnsw",

                        "engine": "lucene",

                        "space_type": "cosinesimil",

                        "parameters": {
                            "m": 8,
                            "ef_construction": 64,
                        },

                    },

                },

                "created_at": {
                    "type": "date"
                },

            }

        }

    }

    response = client.indices.create(
        index=index_name,
        body=index_body,
    )

    logger.info(
        "Created vector index: %s",
        index_name,
    )

    return response


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    result = ensure_vector_index()

    print("Vector index setup complete")
    print(result)
