
from datetime import datetime, timezone

from app.services.embedding_service import embed_texts
from app.services.opensearch_client import get_opensearch_client
from app.services.vector_index import ensure_vector_index
from app.core.config import settings


client = get_opensearch_client()

ensure_vector_index()

texts = [
    "Amazon S3 provides scalable cloud object storage.",

    "AWS SQS enables asynchronous communication between services.",

    "Kubernetes orchestrates containers across multiple nodes.",
]


vectors = embed_texts(texts)

index_name = settings.opensearch_index_name

for i, text in enumerate(texts):

    document = {
        "chunk_id": f"demo-chunk-{i + 1}",
        "document_id": "embedding-demo",
        "user_id": "demo-user",
        "filename": "architecture-demo.txt",
        "page_number": 1,
        "chunk_text": text,
        "embedding": vectors[i],
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    client.index(
        index=index_name,
        id=f"demo-chunk-{i + 1}",
        body=document,
        refresh="wait_for",
    )

    print(f"Indexed demo chunk {i + 1}")


# Query using a new question

question = "Where can I store documents in AWS?"

query_vector = embed_texts([question])[0]


response = client.search(

    index=index_name,

    body={

        "size": 3,

        "query": {

            "knn": {

                "embedding": {

                    "vector": query_vector,

                    "k": 3,

                }

            }

        }

    }

)


print("\nSemantic search results:")

for hit in response["hits"]["hits"]:

    source = hit["_source"]

    print("\nScore:", hit["_score"])
    print("Text:", source["chunk_text"])
