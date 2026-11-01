
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    app_name: str = "DocuMind AI"
    app_env: str = "local"

    aws_region: str = "us-east-1"

    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"

    floci_endpoint: str = "http://localhost:4566"

    s3_bucket_name: str = "documind-documents"

    dynamodb_table_name: str = "documind-metadata"

    sqs_processing_queue_name: str = "documind-processing"
    sqs_dlq_name: str = "documind-processing-dlq"

    max_upload_size_mb: int = 25


settings = Settings()

