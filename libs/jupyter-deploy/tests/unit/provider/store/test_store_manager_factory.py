import unittest
from unittest.mock import Mock, patch

from jupyter_deploy.provider.aws.store.s3_dynamodb_store import S3DynamoDbTableStoreManager
from jupyter_deploy.provider.store.store_manager_factory import StoreManagerFactory


class TestStoreManagerFactory(unittest.TestCase):
    @patch.object(S3DynamoDbTableStoreManager, "resolve_lead_region", return_value="us-east-1")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_returns_s3_provider(self, mock_boto3: Mock, mock_resolve: Mock) -> None:
        provider = StoreManagerFactory.get_manager("s3-ddb", store_id="my-bucket")

        self.assertIsInstance(provider, S3DynamoDbTableStoreManager)

    def test_raises_for_unknown_store_type(self) -> None:
        with self.assertRaises(NotImplementedError) as ctx:
            StoreManagerFactory.get_manager("gcs")

        self.assertIn("gcs", str(ctx.exception))

    @patch.object(S3DynamoDbTableStoreManager, "resolve_lead_region", return_value="us-east-1")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_s3_provider_receives_store_id(self, mock_boto3: Mock, mock_resolve: Mock) -> None:
        provider = StoreManagerFactory.get_manager("s3-ddb", store_id="custom-bucket")

        self.assertEqual(provider._bucket_name, "custom-bucket")  # type: ignore[attr-defined]

    @patch.object(S3DynamoDbTableStoreManager, "resolve_lead_region", return_value="us-east-1")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_resolves_region_and_passes_to_constructor(self, mock_boto3: Mock, mock_resolve: Mock) -> None:
        provider = StoreManagerFactory.get_manager("s3-ddb")

        mock_resolve.assert_called_once()
        self.assertEqual(provider._region, "us-east-1")  # type: ignore[attr-defined]
