from pydantic import BaseModel, Field


class SearchRequest(BaseModel):

    question: str = Field(
        min_length=3,
        max_length=2000,
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
    )


class SearchResult(BaseModel):

    document_id: str
    filename: str
    page_number: int | None = None
    chunk_text: str
    score: float


class SearchResponse(BaseModel):

    query: str
    count: int
    results: list[SearchResult]
