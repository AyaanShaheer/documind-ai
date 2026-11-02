from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):

    document_id: str
    user_id: str
    filename: str

    status: str

    content_type: str
    size_bytes: int

    s3_bucket: str
    s3_key: str

    created_at: str


class DocumentListItem(BaseModel):
    document_id: str
    filename: str
    content_type: str
    size_bytes: int
    status: str
    created_at: str
    updated_at: str | None = None
    chunk_count: int = 0
    error_message: str | None = None


class DocumentListResponse(BaseModel):
    total: int
    documents: list[DocumentListItem]
