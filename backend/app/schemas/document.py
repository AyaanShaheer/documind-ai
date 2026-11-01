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
