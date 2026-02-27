import unittest
from unittest.mock import Mock, patch

from jupyter_deploy.provider.aws.store.s3_dynamodb_store import S3DynamoDbTableStoreManager
from jupyter_deploy.provider.store.store_manager_factory import StoreManagerFactory


class TestStoreManagerFactory(unittest.TestCase):
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_returns_s3_provider(self, mock_boto3: Mock) -> None:
        provider = StoreManagerFactory.get_manager("s3-ddb", "us-west-2", "my-bucket")

        self.assertIsInstance(provider, S3DynamoDbTableStoreManager)

    def test_raises_for_unknown_store_type(self) -> None:
        with self.assertRaises(NotImplementedError) as ctx:
            StoreManagerFactory.get_manager("gcs", "us-west-2")

        self.assertIn("gcs", str(ctx.exception))

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_s3_provider_receives_region(self, mock_boto3: Mock) -> None:
        provider = StoreManagerFactory.get_manager("s3-ddb", "eu-west-1")

        self.assertEqual(provider._region, "eu-west-1")  # type: ignore[attr-defined]

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_s3_provider_receives_store_id(self, mock_boto3: Mock) -> None:
        provider = StoreManagerFactory.get_manager("s3-ddb", "us-east-1", "custom-bucket")

        self.assertEqual(provider._bucket_name, "custom-bucket")  # type: ignore[attr-defined]
