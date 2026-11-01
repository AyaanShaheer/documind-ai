
# ==========================================
# 1. SQS QUEUE POLICY
# Allow S3 to send document upload events
# ==========================================

resource "aws_sqs_queue_policy" "allow_s3" {

  queue_url = aws_sqs_queue.processing.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "AllowS3DocumentNotifications"
        Effect = "Allow"

        Principal = {
          Service = "s3.amazonaws.com"
        }

        Action = "sqs:SendMessage"

        Resource = aws_sqs_queue.processing.arn

        Condition = {
          ArnLike = {
            "aws:SourceArn" = aws_s3_bucket.documents.arn
          }
        }
      }
    ]
  })
}


# ==========================================
# 2. SQS DEAD LETTER QUEUE REDRIVE POLICY
# Move repeatedly failing messages to DLQ
# ==========================================

resource "aws_sqs_queue_redrive_policy" "processing_to_dlq" {

  queue_url = aws_sqs_queue.processing.id

  redrive_policy = jsonencode({

    deadLetterTargetArn = aws_sqs_queue.dlq.arn

    maxReceiveCount = 3
  })
}


# ==========================================
# 3. S3 BUCKET NOTIFICATION
# Trigger SQS when a document is uploaded
# ==========================================

resource "aws_s3_bucket_notification" "documents" {

  bucket = aws_s3_bucket.documents.id

  queue {
    id        = "documind-document-upload"
    queue_arn = aws_sqs_queue.processing.arn

    events = [
      "s3:ObjectCreated:*"
    ]

    filter_prefix = "incoming/"
  }

  depends_on = [
    aws_sqs_queue_policy.allow_s3
  ]
}

