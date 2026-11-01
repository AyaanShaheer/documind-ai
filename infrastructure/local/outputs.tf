output "s3_bucket_name" {
  value = aws_s3_bucket.documents.bucket
}

output "processing_queue_url" {
  value = aws_sqs_queue.processing.url
}

output "dlq_queue_url" {
  value = aws_sqs_queue.dlq.url
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.metadata.name
}
