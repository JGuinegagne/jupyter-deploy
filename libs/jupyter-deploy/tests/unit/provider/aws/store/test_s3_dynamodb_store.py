import re
import unittest
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock, patch

import botocore.exceptions
from mypy_boto3_s3.type_defs import ObjectTypeDef

from jupyter_deploy.api.aws.s3.s3_sync import S3SyncResult
from jupyter_deploy.engine.supervised_execution import NullDisplay
from jupyter_deploy.exceptions import BackupStoreNotFoundError, ProviderPermissionError
from jupyter_deploy.provider.aws.store.s3_dynamodb_store import S3DynamoDbTableStoreManager


def _obj(key: str, size: int, last_modified: datetime) -> ObjectTypeDef:
    return {
        "Key": key,
        "Size": size,
        "LastModified": last_modified,
        "ETag": "",
        "ChecksumAlgorithm": [],
        "ChecksumType": "FULL_OBJECT",
        "StorageClass": "STANDARD",
        "Owner": {"DisplayName": "", "ID": ""},
        "RestoreStatus": {},  # type: ignore[typeddict-item]
    }


class TestResolveLeadRegion(unittest.TestCase):
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.sts_identity")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_delegates_to_sts_identity(self, mock_boto3: Mock, mock_sts_identity: Mock) -> None:
        mock_sts_client = Mock()
        mock_boto3.client.return_value = mock_sts_client
        mock_sts_identity.get_partition_lead_region.return_value = "us-east-1"

        result = S3DynamoDbTableStoreManager.resolve_lead_region()

        self.assertEqual(result, "us-east-1")
        mock_boto3.client.assert_called_once_with("sts")
        mock_sts_identity.get_partition_lead_region.assert_called_once_with(mock_sts_client)


class TestEnsureStore(unittest.TestCase):
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.dynamodb_table")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_bucket")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_discovers_existing_bucket(self, mock_boto3: Mock, mock_s3_bucket: Mock, mock_ddb: Mock) -> None:
        mock_s3_bucket.find_buckets_by_tag.return_value = [{"Name": "existing-bucket"}]
        mock_ddb.get_table_by_name.return_value = {"Table": {"TableStatus": "ACTIVE"}}
        provider = S3DynamoDbTableStoreManager(region="us-east-1")

        result = provider.ensure_store(NullDisplay())

        self.assertEqual(result.store_id, "existing-bucket")
        self.assertEqual(result.store_type, "s3-ddb")
        self.assertEqual(result.location, "us-east-1")
        mock_s3_bucket.find_buckets_by_tag.assert_called_once_with(
            mock_boto3.client.return_value, "Source", "jupyter-deploy-cli", stop_at_first_match=True
        )
        mock_s3_bucket.create_bucket.assert_not_called()

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.dynamodb_table")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_bucket")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_creates_bucket_when_not_found(self, mock_boto3: Mock, mock_s3_bucket: Mock, mock_ddb: Mock) -> None:
        mock_s3_bucket.find_buckets_by_tag.return_value = []
        mock_ddb.get_table_by_name.return_value = {"Table": {"TableStatus": "ACTIVE"}}
        provider = S3DynamoDbTableStoreManager(region="us-east-1")

        result = provider.ensure_store(NullDisplay())

        mock_s3_bucket.create_bucket.assert_called_once()
        self.assertTrue(result.store_id.startswith("jupyter-deploy-projects-"))

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.dynamodb_table")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_bucket")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_generated_bucket_name_is_valid_s3_name(
        self, mock_boto3: Mock, mock_s3_bucket: Mock, mock_ddb: Mock
    ) -> None:
        mock_s3_bucket.find_buckets_by_tag.return_value = []
        mock_ddb.get_table_by_name.return_value = {"Table": {"TableStatus": "ACTIVE"}}
        provider = S3DynamoDbTableStoreManager(region="us-east-1")

        result = provider.ensure_store(NullDisplay())

        # S3 bucket names: 3-63 chars, lowercase alphanumeric and hyphens,
        # must start/end with letter or number.
        # ref: https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html
        s3_bucket_pattern = re.compile(r"^[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]$")
        self.assertRegex(result.store_id, s3_bucket_pattern)
        self.assertLessEqual(len(result.store_id), 63)

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.dynamodb_table")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_bucket")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_creates_ddb_table_when_not_found(self, mock_boto3: Mock, mock_s3_bucket: Mock, mock_ddb: Mock) -> None:
        mock_s3_bucket.find_buckets_by_tag.return_value = [{"Name": "existing-bucket"}]
        error_response = cast(Any, {"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}})
        mock_ddb.get_table_by_name.side_effect = botocore.exceptions.ClientError(error_response, "DescribeTable")
        provider = S3DynamoDbTableStoreManager(region="us-east-1")

        provider.ensure_store(NullDisplay())

        mock_ddb.create_lock_table.assert_called_once()
        mock_ddb.wait_for_table_active.assert_called_once()

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.dynamodb_table")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_bucket")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_raises_on_bucket_creation_failure(self, mock_boto3: Mock, mock_s3_bucket: Mock, mock_ddb: Mock) -> None:
        mock_s3_bucket.find_buckets_by_tag.return_value = []
        mock_s3_bucket.create_bucket.side_effect = RuntimeError("creation failed")
        provider = S3DynamoDbTableStoreManager(region="us-east-1")

        with self.assertRaises(RuntimeError):
            provider.ensure_store(NullDisplay())

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.dynamodb_table")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_bucket")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_uses_provided_bucket_name(self, mock_boto3: Mock, mock_s3_bucket: Mock, mock_ddb: Mock) -> None:
        mock_ddb.get_table_by_name.return_value = {"Table": {"TableStatus": "ACTIVE"}}
        provider = S3DynamoDbTableStoreManager(region="us-east-1", bucket_name="my-bucket")

        result = provider.ensure_store(NullDisplay())

        self.assertEqual(result.store_id, "my-bucket")
        mock_s3_bucket.find_buckets_by_tag.assert_not_called()

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.dynamodb_table")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_bucket")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_raises_on_s3_lookup_failure(self, mock_boto3: Mock, mock_s3_bucket: Mock, mock_ddb: Mock) -> None:
        mock_s3_bucket.find_buckets_by_tag.side_effect = botocore.exceptions.ClientError(
            cast(Any, {"Error": {"Code": "AccessDenied", "Message": "Forbidden"}}), "ListBuckets"
        )
        provider = S3DynamoDbTableStoreManager(region="us-east-1")

        with self.assertRaises(ProviderPermissionError):
            provider.ensure_store(NullDisplay())

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.dynamodb_table")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_bucket")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_raises_on_ddb_lookup_failure(self, mock_boto3: Mock, mock_s3_bucket: Mock, mock_ddb: Mock) -> None:
        mock_s3_bucket.find_buckets_by_tag.return_value = [{"Name": "existing-bucket"}]
        mock_ddb.get_table_by_name.side_effect = botocore.exceptions.ClientError(
            cast(Any, {"Error": {"Code": "AccessDeniedException", "Message": "Forbidden"}}), "DescribeTable"
        )
        provider = S3DynamoDbTableStoreManager(region="us-east-1")

        with self.assertRaises(ProviderPermissionError):
            provider.ensure_store(NullDisplay())

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.dynamodb_table")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_bucket")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_raises_on_s3_create_failure(self, mock_boto3: Mock, mock_s3_bucket: Mock, mock_ddb: Mock) -> None:
        mock_s3_bucket.find_buckets_by_tag.return_value = []
        mock_s3_bucket.create_bucket.side_effect = botocore.exceptions.ClientError(
            cast(Any, {"Error": {"Code": "AccessDenied", "Message": "Forbidden"}}), "CreateBucket"
        )
        provider = S3DynamoDbTableStoreManager(region="us-east-1")

        with self.assertRaises(ProviderPermissionError):
            provider.ensure_store(NullDisplay())

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.dynamodb_table")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_bucket")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_raises_on_ddb_create_failure(self, mock_boto3: Mock, mock_s3_bucket: Mock, mock_ddb: Mock) -> None:
        mock_s3_bucket.find_buckets_by_tag.return_value = [{"Name": "existing-bucket"}]
        error_response = cast(Any, {"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}})
        mock_ddb.get_table_by_name.side_effect = botocore.exceptions.ClientError(error_response, "DescribeTable")
        mock_ddb.create_lock_table.side_effect = botocore.exceptions.ClientError(
            cast(Any, {"Error": {"Code": "AccessDeniedException", "Message": "Forbidden"}}), "CreateTable"
        )
        provider = S3DynamoDbTableStoreManager(region="us-east-1")

        with self.assertRaises(ProviderPermissionError):
            provider.ensure_store(NullDisplay())


class TestPush(unittest.TestCase):
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_sync")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_syncs_project_to_remote(self, mock_boto3: Mock, mock_sync: Mock) -> None:
        mock_sync.sync_to_remote.return_value = S3SyncResult(uploaded=3, deleted=1, unchanged=5)
        provider = S3DynamoDbTableStoreManager(region="us-east-1", bucket_name="bucket")

        with patch.object(Path, "exists", return_value=True):
            result = provider.push(Path("/project"), "my-project", NullDisplay())

        self.assertEqual(result.uploaded, 3)
        self.assertEqual(result.deleted, 1)
        self.assertEqual(result.unchanged, 5)

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_raises_when_store_not_initialized(self, mock_boto3: Mock) -> None:
        provider = S3DynamoDbTableStoreManager(region="us-east-1")

        with self.assertRaises(BackupStoreNotFoundError):
            provider.push(Path("/project"), "my-project", NullDisplay())

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_sync")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_raises_on_sync_failure(self, mock_boto3: Mock, mock_sync: Mock) -> None:
        mock_sync.sync_to_remote.side_effect = RuntimeError("upload failed")
        provider = S3DynamoDbTableStoreManager(region="us-east-1", bucket_name="bucket")

        with patch.object(Path, "exists", return_value=False), self.assertRaises(RuntimeError):
            provider.push(Path("/project"), "my-project", NullDisplay())

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_sync")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_raises_on_sync_to_remote_permission_error(self, mock_boto3: Mock, mock_sync: Mock) -> None:
        mock_sync.sync_to_remote.side_effect = botocore.exceptions.ClientError(
            cast(Any, {"Error": {"Code": "AccessDenied", "Message": "Forbidden"}}), "PutObject"
        )
        provider = S3DynamoDbTableStoreManager(region="us-east-1", bucket_name="bucket")

        with patch.object(Path, "exists", return_value=False), self.assertRaises(ProviderPermissionError):
            provider.push(Path("/project"), "my-project", NullDisplay())


class TestPull(unittest.TestCase):
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_sync")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_syncs_from_remote(self, mock_boto3: Mock, mock_sync: Mock) -> None:
        mock_sync.sync_from_remote.return_value = S3SyncResult(uploaded=5, deleted=0, unchanged=0)
        provider = S3DynamoDbTableStoreManager(region="us-east-1", bucket_name="bucket")

        result = provider.pull("my-project", Path("/dest"), NullDisplay())

        self.assertEqual(result.uploaded, 5)

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_raises_when_store_not_initialized(self, mock_boto3: Mock) -> None:
        provider = S3DynamoDbTableStoreManager(region="us-east-1")

        with self.assertRaises(BackupStoreNotFoundError):
            provider.pull("my-project", Path("/dest"), NullDisplay())

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_sync")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_raises_on_sync_from_remote_permission_error(self, mock_boto3: Mock, mock_sync: Mock) -> None:
        mock_sync.sync_from_remote.side_effect = botocore.exceptions.ClientError(
            cast(Any, {"Error": {"Code": "AccessDenied", "Message": "Forbidden"}}), "GetObject"
        )
        provider = S3DynamoDbTableStoreManager(region="us-east-1", bucket_name="bucket")

        with self.assertRaises(ProviderPermissionError):
            provider.pull("my-project", Path("/dest"), NullDisplay())


class TestListProjects(unittest.TestCase):
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_object")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_bucket")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_lists_projects(self, mock_boto3: Mock, mock_s3_bucket: Mock, mock_s3_object: Mock) -> None:
        now = datetime.now(tz=UTC)
        mock_s3_bucket.list_top_level_prefixes.return_value = ["project-a", "project-b"]
        mock_s3_object.list_objects.side_effect = [
            [_obj("project-a/f.txt", 10, now)],
            [],
        ]
        provider = S3DynamoDbTableStoreManager(region="us-east-1", bucket_name="bucket")

        result = provider.list_projects(NullDisplay())

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].project_id, "project-a")
        self.assertEqual(result[0].file_count, 1)
        self.assertEqual(result[1].project_id, "project-b")
        self.assertEqual(result[1].file_count, 0)

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_raises_when_store_not_initialized(self, mock_boto3: Mock) -> None:
        provider = S3DynamoDbTableStoreManager(region="us-east-1")

        with self.assertRaises(BackupStoreNotFoundError):
            provider.list_projects(NullDisplay())

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_bucket")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_raises_on_list_prefixes_permission_error(self, mock_boto3: Mock, mock_s3_bucket: Mock) -> None:
        mock_s3_bucket.list_top_level_prefixes.side_effect = botocore.exceptions.ClientError(
            cast(Any, {"Error": {"Code": "AccessDenied", "Message": "Forbidden"}}), "ListObjectsV2"
        )
        provider = S3DynamoDbTableStoreManager(region="us-east-1", bucket_name="bucket")

        with self.assertRaises(ProviderPermissionError):
            provider.list_projects(NullDisplay())

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_object")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_bucket")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_raises_on_list_objects_permission_error(
        self, mock_boto3: Mock, mock_s3_bucket: Mock, mock_s3_object: Mock
    ) -> None:
        mock_s3_bucket.list_top_level_prefixes.return_value = ["project-a"]
        mock_s3_object.list_objects.side_effect = botocore.exceptions.ClientError(
            cast(Any, {"Error": {"Code": "AccessDenied", "Message": "Forbidden"}}), "ListObjectsV2"
        )
        provider = S3DynamoDbTableStoreManager(region="us-east-1", bucket_name="bucket")

        with self.assertRaises(ProviderPermissionError):
            provider.list_projects(NullDisplay())


class TestDeleteProject(unittest.TestCase):
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_object")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_deletes_project_objects(self, mock_boto3: Mock, mock_s3_object: Mock) -> None:
        now = datetime.now(tz=UTC)
        mock_s3_object.list_objects.return_value = [
            _obj("proj/a.txt", 10, now),
            _obj("proj/b.txt", 20, now),
        ]
        provider = S3DynamoDbTableStoreManager(region="us-east-1", bucket_name="bucket")

        provider.delete_project("proj", NullDisplay())

        mock_s3_object.delete_objects.assert_called_once()
        call_args = mock_s3_object.delete_objects.call_args
        keys = call_args[1]["keys"] if "keys" in call_args[1] else call_args[0][2]
        self.assertEqual(keys, ["proj/a.txt", "proj/b.txt"])

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_object")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_handles_empty_project(self, mock_boto3: Mock, mock_s3_object: Mock) -> None:
        mock_s3_object.list_objects.return_value = []
        provider = S3DynamoDbTableStoreManager(region="us-east-1", bucket_name="bucket")

        provider.delete_project("proj", NullDisplay())

        mock_s3_object.delete_objects.assert_not_called()

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_raises_when_store_not_initialized(self, mock_boto3: Mock) -> None:
        provider = S3DynamoDbTableStoreManager(region="us-east-1")

        with self.assertRaises(BackupStoreNotFoundError):
            provider.delete_project("proj", NullDisplay())

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_object")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_raises_on_list_objects_permission_error(self, mock_boto3: Mock, mock_s3_object: Mock) -> None:
        mock_s3_object.list_objects.side_effect = botocore.exceptions.ClientError(
            cast(Any, {"Error": {"Code": "AccessDenied", "Message": "Forbidden"}}), "ListObjectsV2"
        )
        provider = S3DynamoDbTableStoreManager(region="us-east-1", bucket_name="bucket")

        with self.assertRaises(ProviderPermissionError):
            provider.delete_project("proj", NullDisplay())

    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.s3_object")
    @patch("jupyter_deploy.provider.aws.store.s3_dynamodb_store.boto3")
    def test_raises_on_delete_objects_permission_error(self, mock_boto3: Mock, mock_s3_object: Mock) -> None:
        now = datetime.now(tz=UTC)
        mock_s3_object.list_objects.return_value = [_obj("proj/a.txt", 10, now)]
        mock_s3_object.delete_objects.side_effect = botocore.exceptions.ClientError(
            cast(Any, {"Error": {"Code": "AccessDenied", "Message": "Forbidden"}}), "DeleteObjects"
        )
        provider = S3DynamoDbTableStoreManager(region="us-east-1", bucket_name="bucket")

        with self.assertRaises(ProviderPermissionError):
            provider.delete_project("proj", NullDisplay())
