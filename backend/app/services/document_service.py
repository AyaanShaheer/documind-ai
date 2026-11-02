
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


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def mark_upload_failed(table, key, error):

    try:

        table.update_item(
            Key=key,

            UpdateExpression=(
                "SET #status = :failed, "
                "error_message = :error, "
                "updated_at = :updated"
            ),

            ConditionExpression="#status = :uploading",

            ExpressionAttributeNames={
                "#status": "status",
            },

            ExpressionAttributeValues={
                ":failed": "FAILED",
                ":uploading": "UPLOADING",
                ":error": str(error)[:500],
                ":updated": utc_now(),
            },
        )

    except (BotoCoreError, ClientError):

        logger.exception(
            "Could not mark failed document upload"
        )


def persist_document(
    user_id: str,
    filename: str,
    content: bytes,
    content_type: str,
) -> dict:

    document_id = str(uuid4())

    created_at = utc_now()

    s3_key = (
        f"incoming/{user_id}/"
        f"{document_id}/{filename}"
    )

    s3 = get_s3_client()

    dynamodb = get_dynamodb_resource()

    table = dynamodb.Table(
        settings.dynamodb_table_name
    )

    key = {
        "user_id": user_id,
        "document_id": document_id,
    }

    # -----------------------------------------
    # STEP 1: Create metadata BEFORE S3 upload
    # -----------------------------------------

    item = {
        **key,
        "filename": filename,
        "content_type": content_type,
        "size_bytes": len(content),
        "status": "UPLOADING",
        "s3_bucket": settings.s3_bucket_name,
        "s3_key": s3_key,
        "created_at": created_at,
        "updated_at": created_at,
    }

    try:

        table.put_item(
            Item=item,

            ConditionExpression=(
                "attribute_not_exists(user_id) "
                "AND attribute_not_exists(document_id)"
            ),
        )

        logger.info(
            "Initial metadata created: %s",
            document_id,
        )

    except (BotoCoreError, ClientError) as exc:

        logger.exception(
            "Could not create initial metadata"
        )

        raise DocumentStorageError(
            "Unable to initialise document metadata"
        ) from exc

    # -----------------------------------------
    # STEP 2: Upload original document to S3
    # -----------------------------------------

    try:

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

        logger.info(
            "Original document uploaded: %s",
            document_id,
        )

    except (BotoCoreError, ClientError) as exc:

        logger.exception(
            "S3 upload failed: %s",
            document_id,
        )

        mark_upload_failed(
            table,
            key,
            exc,
        )

        raise DocumentStorageError(
            "Unable to upload document to S3"
        ) from exc

    # -----------------------------------------
    # STEP 3: Mark UPLOADED conditionally
    # -----------------------------------------

    try:

        table.update_item(
            Key=key,

            UpdateExpression=(
                "SET #status = :uploaded, "
                "updated_at = :updated"
            ),

            ConditionExpression="#status = :uploading",

            ExpressionAttributeNames={
                "#status": "status",
            },

            ExpressionAttributeValues={
                ":uploaded": "UPLOADED",
                ":uploading": "UPLOADING",
                ":updated": utc_now(),
            },
        )

    except ClientError as exc:

        error_code = exc.response.get(
            "Error", {}
        ).get("Code")

        if error_code == "ConditionalCheckFailedException":

            # The worker already advanced the document.
            # Never overwrite PROCESSING or INDEXED.

            logger.info(
                "Worker already advanced document status: %s",
                document_id,
            )

        else:

            # S3 upload succeeded and metadata exists.
            # Leave the record for worker reconciliation.

            logger.exception(
                "Could not update upload status: %s",
                document_id,
            )

    except BotoCoreError:

        logger.exception(
            "Transient DynamoDB status update failure: %s",
            document_id,
        )

    # -----------------------------------------
    # STEP 4: Read the latest status
    # -----------------------------------------

    current_status = "UPLOADING"

    try:

        response = table.get_item(
            Key=key,
            ConsistentRead=True,
        )

        current_item = response.get("Item", {})

        current_status = current_item.get(
            "status",
            "UPLOADING",
        )

    except (BotoCoreError, ClientError):

        logger.exception(
            "Could not read latest document status"
        )

    return {
        "document_id": document_id,
        "user_id": user_id,
        "filename": filename,
        "status": current_status,
        "content_type": content_type,
        "size_bytes": len(content),
        "s3_bucket": settings.s3_bucket_name,
        "s3_key": s3_key,
        "created_at": created_at,
    }

