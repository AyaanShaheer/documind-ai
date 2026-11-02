
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

    # Amazon Cognito authentication
    cognito_user_pool_id: str = ""
    cognito_app_client_id: str = ""
    cognito_issuer: str = ""
    cognito_jwks_url: str = ""
 
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"

    floci_endpoint: str = "http://localhost:4566"

    s3_bucket_name: str = "documind-documents"

    dynamodb_table_name: str = "documind-metadata"

    sqs_processing_queue_name: str = "documind-processing"
    sqs_dlq_name: str = "documind-processing-dlq"

    max_upload_size_mb: int = 25

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    opensearch_host: str = "localhost"
    opensearch_port: int = 9400
    opensearch_index_name: str = "documind-chunks"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:0.5b-instruct"
    ollama_timeout_seconds: int = 120
    rag_top_k: int = 5


settings = Settings()

