from __future__ import annotations

import boto3
import botocore.exceptions
from mypy_boto3_dynamodb.client import DynamoDBClient

from jupyter_deploy.api.aws.dynamodb import dynamodb_table
from jupyter_deploy.engine.supervised_execution import DisplayManager
from jupyter_deploy.enum import StoreType
from jupyter_deploy.provider.aws.aws_error_handler import aws_error_context_manager
from jupyter_deploy.provider.aws.store.constants import (
    STORE_DDB_TABLE_NAME,
    STORE_TAG_SOURCE_KEY,
    STORE_TAG_SOURCE_VALUE,
    STORE_TAG_VERSION_KEY,
)
from jupyter_deploy.provider.aws.store.s3_store import S3StoreManager
from jupyter_deploy.provider.store.store_manager import StoreInfo


class S3DynamoDbTableStoreManager(S3StoreManager):
    """StoreManager backed by S3 and DynamoDB.

    Extends S3StoreManager with a DynamoDB lock table for terraform state locking.
    """

    _store_type = StoreType.S3_DDB

    def __init__(self, region: str, bucket_name: str | None = None) -> None:
        super().__init__(region, bucket_name)
        self._dynamodb_client: DynamoDBClient = boto3.client("dynamodb", region_name=region)

    def ensure_store(self, display_manager: DisplayManager) -> StoreInfo:
        store_info = super().ensure_store(display_manager)

        with aws_error_context_manager():
            ddb_table_created = False
            try:
                display_manager.info("Looking for existing dynamoDB table...")
                dynamodb_table.get_table_by_name(self._dynamodb_client, STORE_DDB_TABLE_NAME)
                display_manager.info(f"Found existing dynamoDB table: {STORE_DDB_TABLE_NAME}")
            except botocore.exceptions.ClientError as e:
                if e.response.get("Error", {}).get("Code") != "ResourceNotFoundException":
                    raise
                display_manager.info(f"Creating dynamoDB table: {STORE_DDB_TABLE_NAME}")
                tags = {
                    STORE_TAG_SOURCE_KEY: STORE_TAG_SOURCE_VALUE,
                    STORE_TAG_VERSION_KEY: "1",
                }
                dynamodb_table.create_lock_table(self._dynamodb_client, STORE_DDB_TABLE_NAME, tags)
                dynamodb_table.wait_for_table_active(self._dynamodb_client, STORE_DDB_TABLE_NAME)
                ddb_table_created = True

            if ddb_table_created:
                display_manager.success(f"State lock DynamoDB table created: {STORE_DDB_TABLE_NAME}")
                display_manager.line()

        return store_info
