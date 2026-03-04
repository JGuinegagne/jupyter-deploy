import unittest
from unittest.mock import Mock, patch

from jupyter_deploy.enum import StoreType
from jupyter_deploy.provider.aws.store.s3_dynamodb_store import S3DynamoDbTableStoreManager
from jupyter_deploy.provider.aws.store.s3_store import S3StoreManager
from jupyter_deploy.provider.store.store_manager_factory import StoreManagerFactory


class TestStoreManagerFactory(unittest.TestCase):
    @patch.object(S3StoreManager, "resolve_lead_region", return_value="us-east-1")
    @patch("jupyter_deploy.provider.aws.store.s3_store.boto3")
    def test_returns_s3_only_provider(self, mock_boto3: Mock, mock_resolve: Mock) -> None:
        provider = StoreManagerFactory.get_manager(StoreType.S3_ONLY, store_id="my-bucket")

        self.assertIsInstance(provider, S3StoreManager)
        self.assertNotIsInstance(provider, S3DynamoDbTableStoreManager)

    @patch.object(S3DynamoDbTableStoreManager, "resolve_lead_region", return_value="us-east-1")
    @patch("jupyter_deploy.provider.aws.store.s3_store.boto3")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_returns_s3_ddb_provider(self, mock_ddb_boto3: Mock, mock_s3_boto3: Mock, mock_resolve: Mock) -> None:
        provider = StoreManagerFactory.get_manager(StoreType.S3_DDB, store_id="my-bucket")

        self.assertIsInstance(provider, S3DynamoDbTableStoreManager)

    def test_raises_for_unknown_store_type(self) -> None:
        with self.assertRaises(ValueError):
            StoreType.from_string("gcs")

    @patch.object(S3StoreManager, "resolve_lead_region", return_value="us-east-1")
    @patch("jupyter_deploy.provider.aws.store.s3_store.boto3")
    def test_s3_only_provider_receives_store_id(self, mock_boto3: Mock, mock_resolve: Mock) -> None:
        provider = StoreManagerFactory.get_manager(StoreType.S3_ONLY, store_id="custom-bucket")

        self.assertEqual(provider._bucket_name, "custom-bucket")  # type: ignore[attr-defined]

    @patch.object(S3StoreManager, "resolve_lead_region", return_value="us-east-1")
    @patch("jupyter_deploy.provider.aws.store.s3_store.boto3")
    def test_resolves_region_and_passes_to_constructor(self, mock_boto3: Mock, mock_resolve: Mock) -> None:
        provider = StoreManagerFactory.get_manager(StoreType.S3_ONLY)

        mock_resolve.assert_called_once()
        self.assertEqual(provider._region, "us-east-1")  # type: ignore[attr-defined]

    @patch.object(S3DynamoDbTableStoreManager, "resolve_lead_region", return_value="cn-north-1")
    @patch("jupyter_deploy.provider.aws.store.s3_store.boto3")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_s3_ddb_resolves_region(self, mock_ddb_boto3: Mock, mock_s3_boto3: Mock, mock_resolve: Mock) -> None:
        provider = StoreManagerFactory.get_manager(StoreType.S3_DDB)

        mock_resolve.assert_called_once()
        self.assertEqual(provider._region, "cn-north-1")  # type: ignore[attr-defined]
