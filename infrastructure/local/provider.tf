
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # Dummy credentials for Floci
  access_key = "test"
  secret_key = "test"

  # Disable AWS account authentication checks
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  # Floci uses S3 path-style addressing
  s3_use_path_style = true

  # Route AWS API requests to Floci
  endpoints {
    s3         = var.local_endpoint
    sqs        = var.local_endpoint
    dynamodb   = var.local_endpoint
    opensearch = var.local_endpoint
  }
}

