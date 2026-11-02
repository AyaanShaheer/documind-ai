
import logging
import re
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)

from app.core.auth import get_current_user_id
from app.core.config import settings
from app.schemas.document import DocumentUploadResponse
from app.services.document_service import (
    DocumentStorageError,
    persist_document,
)


logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".docx": (
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    ),
}


def validate_document(
    content: bytes,
    extension: str,
) -> bool:

    if extension == ".pdf":

        return content.startswith(b"%PDF-")

    if extension == ".docx":

        try:
            with ZipFile(BytesIO(content)) as archive:

                files = set(archive.namelist())

                return (
                    "[Content_Types].xml" in files
                    and "word/document.xml" in files
                )

        except BadZipFile:

            return False

    return False


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),

    user_id: str = Depends(get_current_user_id),
):

    # Validate filename
    original_filename = Path(
        file.filename or ""
    ).name

    if not original_filename:

        raise HTTPException(
            status_code=400,
            detail="Filename is required",
        )

    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_TYPES:

        raise HTTPException(
            status_code=415,
            detail="Only PDF and DOCX files are supported",
        )

    expected_content_type = ALLOWED_TYPES[extension]

    if file.content_type not in (
        expected_content_type,
        "application/octet-stream",
    ):

        raise HTTPException(
            status_code=415,
            detail="File content type does not match the extension",
        )

    content = await file.read(
        settings.max_upload_size_mb * 1024 * 1024 + 1
    )

    if not content:

        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty",
        )

    if len(content) > settings.max_upload_size_mb * 1024 * 1024:

        raise HTTPException(
            status_code=413,
            detail="Maximum file size is 25 MB",
        )

    if not validate_document(content, extension):

        raise HTTPException(
            status_code=400,
            detail="Invalid or corrupted document",
        )

    # Sanitize filename for storage path
    safe_filename = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        original_filename,
    ).strip("._")

    safe_filename = safe_filename or "document"

    try:

        result = persist_document(
            user_id=user_id,
            filename=safe_filename,
            content=content,
            content_type=expected_content_type,
        )

        return DocumentUploadResponse(**result)

    except DocumentStorageError as exc:

        logger.exception("Document upload failed")

        raise HTTPException(
            status_code=502,
            detail="Document storage operation failed",
        ) from exc
