from app.services.embedding_service import (
    get_embedding_model,
    embed_texts,
)


texts = [
    "DocuMind AI is a cloud-native document intelligence platform.",

    "Users can upload research papers and ask questions.",

    "AWS S3 provides object storage for uploaded documents.",
]


model = get_embedding_model()

vectors = embed_texts(texts)

print("\nModel:", model)

print("\nNumber of vectors:", len(vectors))

print("\nVector dimensions:", len(vectors[0]))

print("\nFirst five embedding values:")

print(vectors[0][:5])

print("\nEmbedding magnitude:")

print(sum(value ** 2 for value in vectors[0]) ** 0.5)
