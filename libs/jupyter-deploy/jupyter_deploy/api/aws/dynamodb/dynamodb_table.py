from __future__ import annotations

import time

from mypy_boto3_dynamodb.client import DynamoDBClient
from mypy_boto3_dynamodb.type_defs import DescribeTableOutputTypeDef, TagTypeDef


def get_table_by_name(dynamodb_client: DynamoDBClient, table_name: str) -> DescribeTableOutputTypeDef:
    """Call DynamoDB:DescribeTable filtered by table name, return the result."""

    return dynamodb_client.describe_table(TableName=table_name)


def create_lock_table(dynamodb_client: DynamoDBClient, table_name: str, tags: dict[str, str]) -> None:
    """Create a DynamoDB table with a LockID string partition key.

    Raises:
        botocore.exceptions.ClientError on AWS API errors.
    """
    tag_list: list[TagTypeDef] = [{"Key": k, "Value": v} for k, v in tags.items()]
    dynamodb_client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "LockID", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "LockID", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
        Tags=tag_list,
    )


def wait_for_table_active(
    dynamodb_client: DynamoDBClient,
    table_name: str,
    timeout_seconds: int = 60,
    poll_interval_seconds: int = 2,
) -> None:
    """Poll DynamoDB:DescribeTable until the table status is ACTIVE.

    Raises:
        TimeoutError if the table does not become ACTIVE within the timeout.
        botocore.exceptions.ClientError on AWS API errors.
    """
    start_time = time.time()
    while True:
        response = dynamodb_client.describe_table(TableName=table_name)
        status = response["Table"].get("TableStatus", "UNKNOWN")
        if status == "ACTIVE":
            return
        if time.time() - start_time > timeout_seconds:
            raise TimeoutError(f"Timed out waiting for table '{table_name}' to become ACTIVE (status: {status})")
        time.sleep(poll_interval_seconds)


def delete_table(dynamodb_client: DynamoDBClient, table_name: str) -> None:
    """Call DynamoDB:DeleteTable on the table name.

    Raises:
        botocore.exceptions.ClientError on AWS API errors.
    """
    dynamodb_client.delete_table(TableName=table_name)
