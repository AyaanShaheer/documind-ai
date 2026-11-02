
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):

    question: str = Field(
        min_length=3,
        max_length=2000,
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
    )


class ChatSource(BaseModel):

    source_id: int

    document_id: str

    filename: str

    page_number: int | None = None

    relevance_score: float


class ChatResponse(BaseModel):

    question: str

    answer: str

    model: str

    retrieved_chunks: int

    sources: list[ChatSource]
