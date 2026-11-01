from app.services.aws_clients import (
    get_s3_client,
    get_dynamodb_resource,
)


def verify_aws_connection():

    s3 = get_s3_client()

    dynamodb = get_dynamodb_resource()

    buckets = s3.list_buckets()

    table = dynamodb.Table("documind-metadata")

    table_description = table.table_status

    print("S3 connection successful")
    print("Buckets:", buckets["Buckets"])

    print("DynamoDB connection successful")
    print("Table status:", table_description)


if __name__ == "__main__":
    verify_aws_connection()
