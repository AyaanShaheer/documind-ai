
from functools import lru_cache

import boto3
from botocore.config import Config

from app.core.config import settings


def get_client_config():
    """
    Build AWS SDK configuration.

    Local:
        Connect to Floci using dummy credentials.

    Production:
        Use the AWS SDK credential chain,
        including ECS task IAM roles.
    """

    options = {
        "region_name": settings.aws_region,
    }

    if settings.app_env == "local":
        options.update({
            "endpoint_url": settings.floci_endpoint,
            "aws_access_key_id": settings.aws_access_key_id,
            "aws_secret_access_key": settings.aws_secret_access_key,
        })

    return options


@lru_cache(maxsize=1)
def get_s3_client():
    return boto3.client(
        "s3",
        **get_client_config(),
        config=Config(
            s3={"addressing_style": "path"},
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )


@lru_cache(maxsize=1)
def get_dynamodb_resource():
    return boto3.resource(
        "dynamodb",
        **get_client_config(),
    )


@lru_cache(maxsize=1)
def get_sqs_client():
    return boto3.client(
        "sqs",
        **get_client_config(),
    )

