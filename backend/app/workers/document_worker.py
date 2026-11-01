
import json
import logging

from datetime import datetime, timezone
from io import BytesIO
from urllib.parse import unquote_plus

import pymupdf
from docx import Document

from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.services.aws_clients import (
    get_s3_client,
    get_sqs_client,
    get_dynamodb_resource,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("documind-worker")


TERMINAL_STATUSES = {"EXTRACTED", "NEEDS_OCR"}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def extract_pdf(content: bytes):
    """
    Extract text from a PDF document.
    Returns extracted text and page count.
    """

    with pymupdf.open(
        stream=content,
        filetype="pdf",
    ) as pdf:

        page_count = len(pdf)

        text = "\n".join(
            page.get_text("text")
            for page in pdf
        )

    return text.strip(), page_count


def extract_docx(content: bytes):
    """
    Extract paragraphs and table contents from DOCX.
    """

    document = Document(BytesIO(content))

    sections = []

    for paragraph in document.paragraphs:

        if paragraph.text.strip():
            sections.append(paragraph.text)

    for table in document.tables:

        for row in table.rows:

            cells = [
                cell.text.strip()
                for cell in row.cells
            ]

            sections.append(" | ".join(cells))

    return "\n".join(sections).strip()


def update_failed_status(
    table,
    user_id,
    document_id,
    error,
):
    """
    Record processing failure in DynamoDB.
    """

    try:

        table.update_item(
            Key={
                "user_id": user_id,
                "document_id": document_id,
            },

            UpdateExpression=(
                "SET #status = :status, "
                "error_message = :error, "
                "updated_at = :updated"
            ),

            ExpressionAttributeNames={
                "#status": "status",
            },

            ExpressionAttributeValues={
                ":status": "FAILED",
                ":error": str(error)[:500],
                ":updated": utc_now(),
            },
        )

    except (BotoCoreError, ClientError):

        logger.exception(
            "Could not update failure status for %s",
            document_id,
        )


def process_s3_record(record):
    """
    Process one S3 ObjectCreated event.
    """

    s3 = get_s3_client()

    dynamodb = get_dynamodb_resource()

    table = dynamodb.Table(
        settings.dynamodb_table_name
    )

    event_name = record.get("eventName", "")

    if not event_name.startswith("ObjectCreated:"):

        logger.info(
            "Ignoring unsupported S3 event: %s",
            event_name,
        )

        return

    s3_data = record["s3"]

    bucket_name = s3_data["bucket"]["name"]

    raw_key = s3_data["object"]["key"]

    # S3 event keys are URL encoded.
    object_key = unquote_plus(raw_key)

    if bucket_name != settings.s3_bucket_name:

        logger.warning(
            "Ignoring unexpected bucket: %s",
            bucket_name,
        )

        return

    # Expected format:
    # incoming/{user_id}/{document_id}/{filename}

    parts = object_key.split("/", 3)

    if (
        len(parts) != 4
        or parts[0] != "incoming"
        or not all(parts[1:])
    ):

        logger.warning(
            "Ignoring object outside DocuMind key structure: %s",
            object_key,
        )

        return

    _, user_id, document_id, filename = parts

    key = {
        "user_id": user_id,
        "document_id": document_id,
    }

    response = table.get_item(
        Key=key,
        ConsistentRead=True,
    )

    item = response.get("Item")

    if not item:

        # A valid upload event can arrive before the
        # API's DynamoDB write becomes visible.
        # Retry instead of incorrectly acknowledging it.

        raise RuntimeError(
            f"Metadata not available for document {document_id}"
        )

    if item.get("status") in TERMINAL_STATUSES:

        logger.info(
            "Document already processed; skipping duplicate: %s",
            document_id,
        )

        return

    now = utc_now()

    table.update_item(
        Key=key,

        UpdateExpression=(
            "SET #status = :status, updated_at = :updated"
        ),

        ExpressionAttributeNames={
            "#status": "status",
        },

        ExpressionAttributeValues={
            ":status": "PROCESSING",
            ":updated": now,
        },
    )

    try:

        # ---------------------------------
        # Download document from S3
        # ---------------------------------

        logger.info(
            "Downloading document: %s",
            document_id,
        )

        obj = s3.get_object(
            Bucket=bucket_name,
            Key=object_key,
        )

        content = obj["Body"].read()

        # ---------------------------------
        # Extract document content
        # ---------------------------------

        if filename.lower().endswith(".pdf"):

            extracted_text, page_count = extract_pdf(
                content
            )

        elif filename.lower().endswith(".docx"):

            extracted_text = extract_docx(content)

            page_count = None

        else:

            raise ValueError(
                f"Unsupported document format: {filename}"
            )

        logger.info(
            "Extracted %s characters from %s",
            len(extracted_text),
            document_id,
        )

        # ---------------------------------
        # Handle scanned or empty documents
        # ---------------------------------

        if not extracted_text:

            table.update_item(
                Key=key,

                UpdateExpression=(
                    "SET #status = :status, "
                    "processing_note = :note, "
                    "updated_at = :updated"
                ),

                ExpressionAttributeNames={
                    "#status": "status",
                },

                ExpressionAttributeValues={
                    ":status": "NEEDS_OCR",
                    ":note": "No extractable text found",
                    ":updated": utc_now(),
                },
            )

            logger.warning(
                "Document requires OCR: %s",
                document_id,
            )

            return

        # ---------------------------------
        # Store extracted text in S3
        # ---------------------------------

        extracted_key = (
            f"processed/{user_id}/"
            f"{document_id}/extracted.txt"
        )

        s3.put_object(
            Bucket=bucket_name,
            Key=extracted_key,
            Body=extracted_text.encode("utf-8"),
            ContentType="text/plain; charset=utf-8",
        )

        # ---------------------------------
        # Update DynamoDB metadata
        # ---------------------------------

        update_expression = (
            "SET #status = :status, "
            "extracted_text_s3_key = :text_key, "
            "character_count = :char_count, "
            "updated_at = :updated, "
            "processing_completed_at = :completed"
        )

        values = {
            ":status": "EXTRACTED",
            ":text_key": extracted_key,
            ":char_count": len(extracted_text),
            ":updated": utc_now(),
            ":completed": utc_now(),
        }

        if page_count is not None:

            update_expression += ", page_count = :pages"

            values[":pages"] = page_count

        update_expression += (
            " REMOVE error_message, processing_note"
        )

        table.update_item(
            Key=key,

            UpdateExpression=update_expression,

            ExpressionAttributeNames={
                "#status": "status",
            },

            ExpressionAttributeValues=values,
        )

        logger.info(
            "Document successfully processed: %s",
            document_id,
        )
        

    except Exception as exc:

        update_failed_status(
            table,
            user_id,
            document_id,
            exc,
        )

        logger.exception(
            "Document processing failed: %s",
            document_id,
        )

        raise


def handle_message(message):
    """
    Handle one SQS message containing S3 events.
    """

    body = json.loads(message["Body"])

    # S3 sends an initial TestEvent when the
    # bucket notification configuration is created.

    if body.get("Event") == "s3:TestEvent":

        logger.info(
            "S3 TestEvent received and acknowledged"
        )

        return

    records = body.get("Records")

    if not isinstance(records, list):

        raise ValueError(
            "Message does not contain a valid S3 Records array"
        )

    for record in records:

        process_s3_record(record)


def run_worker():
    """
    Continuously poll SQS and process documents.
    """

    sqs = get_sqs_client()

    response = sqs.get_queue_url(
        QueueName=settings.sqs_processing_queue_name
    )

    queue_url = response["QueueUrl"]

    logger.info(
        "DocuMind worker started"
    )

    logger.info(
        "Connected to queue: %s",
        queue_url,
    )

    while True:

        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=5,
            WaitTimeSeconds=10,
            VisibilityTimeout=120,
        )

        messages = response.get("Messages", [])

        if not messages:
            continue

        for message in messages:

            receipt_handle = message["ReceiptHandle"]

            try:

                logger.info(
                    "Received SQS message: %s",
                    message["MessageId"],
                )

                handle_message(message)

                # Acknowledge only after successful processing.

                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle,
                )

                logger.info(
                    "SQS message acknowledged: %s",
                    message["MessageId"],
                )

            except Exception:

                # Do not delete failed messages.
                # SQS will make them visible again
                # after the visibility timeout.

                logger.exception(
                    "Message processing failed; "
                    "leaving message for retry"
                )


if __name__ == "__main__":

    try:

        run_worker()

    except KeyboardInterrupt:

        logger.info(
            "DocuMind worker stopped"
        )

