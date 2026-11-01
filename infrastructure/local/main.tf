
# --------------------------------
# S3 - Document Storage
# --------------------------------

resource "aws_s3_bucket" "documents" {
  bucket = "${var.project_name}-documents"

  tags = {
    Name        = "DocuMind Documents"
    Environment = "local"
    Project     = "DocuMind AI"
  }
}


# --------------------------------
# SQS - Document Processing Queue
# --------------------------------

resource "aws_sqs_queue" "processing" {
  name = "${var.project_name}-processing"

  visibility_timeout_seconds = 30
  max_message_size           = 1048576
}


# --------------------------------
# SQS - Dead Letter Queue
# --------------------------------

resource "aws_sqs_queue" "dlq" {
  name             = "${var.project_name}-processing-dlq"
  max_message_size = 1048576
}


# --------------------------------
# DynamoDB - Document Metadata
# --------------------------------

resource "aws_dynamodb_table" "metadata" {

  name         = "${var.project_name}-metadata"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "user_id"
  range_key = "document_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "document_id"
    type = "S"
  }

  tags = {
    Name        = "DocuMind Metadata"
    Environment = "local"
    Project     = "DocuMind AI"
  }
}

