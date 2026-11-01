
import logging
from datetime import datetime, timezone
from uuid import uuid4

from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.services.aws_clients import (
    get_s3_client,
    get_dynamodb_resource,
)


logger = logging.getLogger(__name__)


class DocumentStorageError(Exception):
    pass


def persist_document(
    user_id: str,
    filename: str,
    content: bytes,
    content_type: str,
) -> dict:

    document_id = str(uuid4())

    created_at = datetime.now(timezone.utc).isoformat()

    safe_filename = filename

    s3_key = (
        f"incoming/{user_id}/"
        f"{document_id}/{safe_filename}"
    )

    s3 = get_s3_client()

    dynamodb = get_dynamodb_resource()

    table = dynamodb.Table(settings.dynamodb_table_name)

    s3_uploaded = False

    try:

        # Upload original document to S3
        s3.put_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            Body=content,
            ContentType=content_type,
            Metadata={
                "document-id": document_id,
                "user-id": user_id,
            },
        )

        s3_uploaded = True

        # Prepare document metadata
        item = {
            "user_id": user_id,
            "document_id": document_id,
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(content),
            "status": "UPLOADED",
            "s3_bucket": settings.s3_bucket_name,
            "s3_key": s3_key,
            "created_at": created_at,
            "updated_at": created_at,
        }

        # Save metadata to DynamoDB
        table.put_item(Item=item)

        return {
            "document_id": document_id,
            "user_id": user_id,
            "filename": filename,
            "status": "UPLOADED",
            "content_type": content_type,
            "size_bytes": len(content),
            "s3_bucket": settings.s3_bucket_name,
            "s3_key": s3_key,
            "created_at": created_at,
        }

    except (BotoCoreError, ClientError) as exc:

        logger.exception("Document storage failed")

        # Compensating action: remove uploaded object
        if s3_uploaded:

            try:
                s3.delete_object(
                    Bucket=settings.s3_bucket_name,
                    Key=s3_key,
                )

            except (BotoCoreError, ClientError):
                logger.exception(
                    "S3 cleanup failed for document %s",
                    document_id,
                )

        raise DocumentStorageError(
            "Unable to store document"
        ) from exc
