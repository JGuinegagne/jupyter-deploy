import unittest
from typing import Any, cast
from unittest.mock import Mock, patch

import botocore.exceptions

from jupyter_deploy.engine.supervised_execution import NullDisplay
from jupyter_deploy.enum import StoreType
from jupyter_deploy.exceptions import ProviderPermissionError
from jupyter_deploy.provider.aws.store.s3_dynamodb_store import S3DynamoDbTableStoreManager
from jupyter_deploy.provider.aws.store.s3_store import S3StoreManager
from jupyter_deploy.provider.store.store_manager import StoreInfo

_S3_MODULE = "jupyter_deploy.provider.aws.store.s3_store"
_DDB_MODULE = "jupyter_deploy.provider.aws.store.s3_dynamodb_store"


class TestFindStore(unittest.TestCase):
    @patch(f"{_S3_MODULE}.s3_bucket")
    @patch(f"{_S3_MODULE}.boto3")
    @patch(f"{_DDB_MODULE}.boto3")
    def test_returns_s3_ddb_store_type(self, mock_ddb_boto3: Mock, mock_s3_boto3: Mock, mock_s3_bucket: Mock) -> None:
        mock_s3_bucket.find_buckets_by_tag.return_value = [{"Name": "existing-bucket"}]
        provider = S3DynamoDbTableStoreManager(region="us-east-1")

        result = provider.find_store()

        self.assertEqual(result.store_type, StoreType.S3_DDB)


class TestEnsureStore(unittest.TestCase):
    @patch(f"{_DDB_MODULE}.dynamodb_table")
    @patch.object(S3StoreManager, "ensure_store")
    @patch(f"{_DDB_MODULE}.boto3")
    @patch(f"{_S3_MODULE}.boto3")
    def test_creates_ddb_table_when_not_found(
        self, mock_s3_boto3: Mock, mock_ddb_boto3: Mock, mock_parent_ensure: Mock, mock_ddb: Mock
    ) -> None:
        mock_parent_ensure.return_value = StoreInfo(
            store_type=StoreType.S3_DDB, store_id="bucket", location="us-east-1"
        )
        error_response = cast(Any, {"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}})
        mock_ddb.get_table_by_name.side_effect = botocore.exceptions.ClientError(error_response, "DescribeTable")
        provider = S3DynamoDbTableStoreManager(region="us-east-1")

        provider.ensure_store(NullDisplay())

        mock_ddb.create_lock_table.assert_called_once()
        mock_ddb.wait_for_table_active.assert_called_once()

    @patch(f"{_DDB_MODULE}.dynamodb_table")
    @patch.object(S3StoreManager, "ensure_store")
    @patch(f"{_DDB_MODULE}.boto3")
    @patch(f"{_S3_MODULE}.boto3")
    def test_finds_existing_ddb_table(
        self, mock_s3_boto3: Mock, mock_ddb_boto3: Mock, mock_parent_ensure: Mock, mock_ddb: Mock
    ) -> None:
        mock_parent_ensure.return_value = StoreInfo(
            store_type=StoreType.S3_DDB, store_id="bucket", location="us-east-1"
        )
        mock_ddb.get_table_by_name.return_value = {"Table": {"TableStatus": "ACTIVE"}}
        provider = S3DynamoDbTableStoreManager(region="us-east-1")

        provider.ensure_store(NullDisplay())

        mock_ddb.create_lock_table.assert_not_called()

    @patch(f"{_DDB_MODULE}.dynamodb_table")
    @patch.object(S3StoreManager, "ensure_store")
    @patch(f"{_DDB_MODULE}.boto3")
    @patch(f"{_S3_MODULE}.boto3")
    def test_raises_on_ddb_lookup_failure(
        self, mock_s3_boto3: Mock, mock_ddb_boto3: Mock, mock_parent_ensure: Mock, mock_ddb: Mock
    ) -> None:
        mock_parent_ensure.return_value = StoreInfo(
            store_type=StoreType.S3_DDB, store_id="bucket", location="us-east-1"
        )
        mock_ddb.get_table_by_name.side_effect = botocore.exceptions.ClientError(
            cast(Any, {"Error": {"Code": "AccessDeniedException", "Message": "Forbidden"}}), "DescribeTable"
        )
        provider = S3DynamoDbTableStoreManager(region="us-east-1")

        with self.assertRaises(ProviderPermissionError):
            provider.ensure_store(NullDisplay())

    @patch(f"{_DDB_MODULE}.dynamodb_table")
    @patch.object(S3StoreManager, "ensure_store")
    @patch(f"{_DDB_MODULE}.boto3")
    @patch(f"{_S3_MODULE}.boto3")
    def test_raises_on_ddb_create_failure(
        self, mock_s3_boto3: Mock, mock_ddb_boto3: Mock, mock_parent_ensure: Mock, mock_ddb: Mock
    ) -> None:
        mock_parent_ensure.return_value = StoreInfo(
            store_type=StoreType.S3_DDB, store_id="bucket", location="us-east-1"
        )
        error_response = cast(Any, {"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}})
        mock_ddb.get_table_by_name.side_effect = botocore.exceptions.ClientError(error_response, "DescribeTable")
        mock_ddb.create_lock_table.side_effect = botocore.exceptions.ClientError(
            cast(Any, {"Error": {"Code": "AccessDeniedException", "Message": "Forbidden"}}), "CreateTable"
        )
        provider = S3DynamoDbTableStoreManager(region="us-east-1")

        with self.assertRaises(ProviderPermissionError):
            provider.ensure_store(NullDisplay())

    @patch(f"{_DDB_MODULE}.dynamodb_table")
    @patch.object(S3StoreManager, "ensure_store")
    @patch(f"{_DDB_MODULE}.boto3")
    @patch(f"{_S3_MODULE}.boto3")
    def test_returns_store_info_from_parent(
        self, mock_s3_boto3: Mock, mock_ddb_boto3: Mock, mock_parent_ensure: Mock, mock_ddb: Mock
    ) -> None:
        expected = StoreInfo(store_type=StoreType.S3_DDB, store_id="my-bucket", location="us-west-2")
        mock_parent_ensure.return_value = expected
        mock_ddb.get_table_by_name.return_value = {"Table": {"TableStatus": "ACTIVE"}}
        provider = S3DynamoDbTableStoreManager(region="us-west-2")

        result = provider.ensure_store(NullDisplay())

        self.assertEqual(result, expected)
