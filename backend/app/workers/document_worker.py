
import json
import logging

from datetime import datetime, timezone
from urllib.parse import unquote_plus

import pymupdf

from docx import Document
from io import BytesIO

from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings

from app.services.aws_clients import (
    get_s3_client,
    get_sqs_client,
    get_dynamodb_resource,
)

from app.services.embedding_service import (
    get_embedding_model,
    embed_texts,
)

from app.services.chunking import (
    chunk_pages_by_tokens,
)

from app.services.vector_store import (
    index_document_chunks,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("documind-worker")


TERMINAL_STATUSES = {
    "INDEXED",
    "NEEDS_OCR",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def extract_pdf_pages(content: bytes) -> tuple[list[dict], int]:
    """
    Extract PDF text while preserving page numbers.
    """

    pages = []

    with pymupdf.open(
        stream=content,
        filetype="pdf",
    ) as pdf:

        page_count = len(pdf)

        for index, page in enumerate(pdf):

            pages.append({
                "page_number": index + 1,
                "text": page.get_text("text"),
            })

    return pages, page_count


def extract_docx_pages(content: bytes) -> list[dict]:
    """
    Extract DOCX paragraphs and tables.

    DOCX does not have stable page numbers without
    rendering, so page_number is None.
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

    text = "\n".join(sections).strip()

    return [{
        "page_number": None,
        "text": text,
    }]


def update_failed_status(
    table,
    user_id,
    document_id,
    error,
):
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
            "Could not update failed status"
        )


def mark_needs_ocr(table, key):

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


def process_s3_record(record):

    s3 = get_s3_client()

    dynamodb = get_dynamodb_resource()

    table = dynamodb.Table(
        settings.dynamodb_table_name
    )

    event_name = record.get("eventName", "")

    if not event_name.startswith("ObjectCreated:"):

        logger.info(
            "Ignoring unsupported event: %s",
            event_name,
        )

        return

    s3_data = record["s3"]

    bucket_name = s3_data["bucket"]["name"]

    object_key = unquote_plus(
        s3_data["object"]["key"]
    )

    if bucket_name != settings.s3_bucket_name:

        logger.warning(
            "Unexpected bucket: %s",
            bucket_name,
        )

        return

    # Expected:
    # incoming/{user_id}/{document_id}/{filename}

    parts = object_key.split("/", 3)

    if (
        len(parts) != 4
        or parts[0] != "incoming"
        or not all(parts[1:])
    ):

        logger.warning(
            "Ignoring object outside DocuMind structure: %s",
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

        raise RuntimeError(
            f"Metadata unavailable for {document_id}"
        )

    if item.get("status") in TERMINAL_STATUSES:

        logger.info(
            "Document already indexed; skipping: %s",
            document_id,
        )

        return

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
            ":updated": utc_now(),
        },
    )

    try:

        # --------------------------------
        # 1. Download document
        # --------------------------------

        logger.info(
            "Downloading document: %s",
            document_id,
        )

        obj = s3.get_object(
            Bucket=bucket_name,
            Key=object_key,
        )

        content = obj["Body"].read()

        # --------------------------------
        # 2. Extract text
        # --------------------------------

        if filename.lower().endswith(".pdf"):

            pages, page_count = extract_pdf_pages(
                content
            )

        elif filename.lower().endswith(".docx"):

            pages = extract_docx_pages(content)

            page_count = None

        else:

            raise ValueError(
                f"Unsupported file: {filename}"
            )

        extracted_text = "\n".join(
            page["text"]
            for page in pages
            if page["text"].strip()
        ).strip()

        logger.info(
            "Extracted %s characters",
            len(extracted_text),
        )

        if not extracted_text:

            mark_needs_ocr(table, key)

            return

        # --------------------------------
        # 3. Save extracted text in S3
        # --------------------------------

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

        # --------------------------------
        # 4. Chunk the document
        # --------------------------------

        model = get_embedding_model()

        chunks = chunk_pages_by_tokens(
            pages=pages,
            tokenizer=model.tokenizer,
            max_tokens=220,
            overlap_tokens=30,
        )

        if not chunks:

            mark_needs_ocr(table, key)

            return

        logger.info(
            "Generated %s document chunks",
            len(chunks),
        )

        # --------------------------------
        # 5. Generate embeddings
        # --------------------------------

        chunk_texts = [
            chunk["text"]
            for chunk in chunks
        ]

        embeddings = embed_texts(chunk_texts)

        logger.info(
            "Generated %s embeddings",
            len(embeddings),
        )

        # --------------------------------
        # 6. Store vectors in OpenSearch
        # --------------------------------

        indexed_count = index_document_chunks(
            user_id=user_id,
            document_id=document_id,
            filename=filename,
            chunks=chunks,
            embeddings=embeddings,
        )

        if indexed_count != len(chunks):

            raise RuntimeError(
                f"Indexed {indexed_count} of {len(chunks)} chunks"
            )

        # --------------------------------
        # 7. Update DynamoDB
        # --------------------------------

        now = utc_now()

        update_expression = (
            "SET #status = :status, "
            "extracted_text_s3_key = :text_key, "
            "character_count = :char_count, "
            "chunk_count = :chunk_count, "
            "embedding_model = :model, "
            "embedding_dimension = :dimension, "
            "opensearch_index = :index_name, "
            "updated_at = :updated, "
            "processing_completed_at = :completed "
            "REMOVE error_message, processing_note"
        )

        values = {
            ":status": "INDEXED",
            ":text_key": extracted_key,
            ":char_count": len(extracted_text),
            ":chunk_count": len(chunks),
            ":model": settings.embedding_model,
            ":dimension": settings.embedding_dimension,
            ":index_name": settings.opensearch_index_name,
            ":updated": now,
            ":completed": now,
        }

        if page_count is not None:

            update_expression += ", page_count = :pages"

            values[":pages"] = page_count

        table.update_item(
            Key=key,

            UpdateExpression=update_expression,

            ExpressionAttributeNames={
                "#status": "status",
            },

            ExpressionAttributeValues=values,
        )

        logger.info(
            "Document successfully indexed: %s",
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

    body = json.loads(message["Body"])

    if body.get("Event") == "s3:TestEvent":

        logger.info(
            "S3 TestEvent received"
        )

        return

    records = body.get("Records")

    if not isinstance(records, list):

        raise ValueError(
            "Invalid S3 notification payload"
        )

    for record in records:

        process_s3_record(record)


def run_worker():

    sqs = get_sqs_client()

    response = sqs.get_queue_url(
        QueueName=settings.sqs_processing_queue_name
    )

    queue_url = response["QueueUrl"]

    logger.info("DocuMind indexing worker started")

    logger.info("Queue: %s", queue_url)

    while True:

        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=5,
            WaitTimeSeconds=10,
            VisibilityTimeout=300,
        )

        messages = response.get("Messages", [])

        for message in messages:

            receipt_handle = message["ReceiptHandle"]

            try:

                logger.info(
                    "Received message: %s",
                    message["MessageId"],
                )

                handle_message(message)

                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle,
                )

                logger.info(
                    "Message acknowledged: %s",
                    message["MessageId"],
                )

            except Exception:

                logger.exception(
                    "Processing failed. Message will be retried."
                )


if __name__ == "__main__":

    try:

        run_worker()

    except KeyboardInterrupt:

        logger.info("DocuMind worker stopped")

