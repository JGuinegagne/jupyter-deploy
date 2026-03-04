from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import boto3
import botocore.exceptions
from mypy_boto3_dynamodb.client import DynamoDBClient
from mypy_boto3_s3.client import S3Client

from jupyter_deploy.api.aws.dynamodb import dynamodb_table
from jupyter_deploy.api.aws.s3 import s3_bucket, s3_object, s3_sync
from jupyter_deploy.api.aws.sts import sts_identity
from jupyter_deploy.engine.supervised_execution import DisplayManager
from jupyter_deploy.exceptions import ProjectStoreNotFoundError
from jupyter_deploy.provider.aws.aws_error_handler import aws_error_context_manager
from jupyter_deploy.provider.aws.store.constants import (
    STORE_BUCKET_NAME_PREFIX,
    STORE_DDB_TABLE_NAME,
    STORE_TAG_SOURCE_KEY,
    STORE_TAG_SOURCE_VALUE,
    STORE_TAG_VERSION_KEY,
)
from jupyter_deploy.provider.store.store_manager import ProjectSummary, StoreInfo, StoreManager, SyncResult


class S3DynamoDbTableStoreManager(StoreManager):
    """StoreManager implementation backed by S3 and DynamoDB.

    The S3 bucket acts as the project store for the jupyter-deploy project dir, which includes
    all the files that are not gitignored. In the case of terraform, it includes
    the terraform state.

    The DynamoDB table acts as the lock state table preventing concurrent updates.
    """

    def __init__(self, region: str, bucket_name: str | None = None) -> None:
        self._region = region
        self._bucket_name = bucket_name
        self._s3_client: S3Client = boto3.client("s3", region_name=region)
        self._dynamodb_client: DynamoDBClient = boto3.client("dynamodb", region_name=region)

    @staticmethod
    def resolve_lead_region() -> str:
        """Resolve the partition lead region from the caller's AWS credentials."""
        sts_client = boto3.client("sts")
        return sts_identity.get_partition_lead_region(sts_client)

    def find_store(self) -> StoreInfo:
        with aws_error_context_manager():
            bucket_name = self._bucket_name
            if not bucket_name:
                matched = s3_bucket.find_buckets_by_tag(
                    self._s3_client, STORE_TAG_SOURCE_KEY, STORE_TAG_SOURCE_VALUE, stop_at_first_match=True
                )
                bucket_name = matched[0].get("Name") if matched else None

            if not bucket_name:
                raise ProjectStoreNotFoundError("No S3 bucket project store found in your AWS account.")

            self._bucket_name = bucket_name
            return StoreInfo(store_type="s3-ddb", store_id=bucket_name, location=self._region)

    def ensure_store(self, display_manager: DisplayManager) -> StoreInfo:
        with aws_error_context_manager():
            bucket_name = self._bucket_name
            bucket_created = False
            ddb_table_created = False

            if not bucket_name:
                display_manager.info("Looking for existing projects store in your AWS account...")
                matched = s3_bucket.find_buckets_by_tag(
                    self._s3_client, STORE_TAG_SOURCE_KEY, STORE_TAG_SOURCE_VALUE, stop_at_first_match=True
                )
                bucket_name = matched[0].get("Name") if matched else None

            if bucket_name:
                display_manager.info(f"Found existing S3 bucket projects store: {bucket_name}")
                self._bucket_name = bucket_name
            else:
                # Random suffix prevents bucket name sniping attacks. 20 hex chars = 80 bits
                # of entropy from os.urandom (CSPRNG); birthday collision at ~2^40 (~1 trillion).
                # Total name length: 24 (prefix) + 1 (dash) + 20 (suffix) = 45 chars (S3 max: 63).
                bucket_name = f"{STORE_BUCKET_NAME_PREFIX}-{uuid.uuid4().hex[:20]}"
                display_manager.info(f"Creating S3 bucket projects store: {bucket_name}")
                tags = {
                    STORE_TAG_SOURCE_KEY: STORE_TAG_SOURCE_VALUE,
                    STORE_TAG_VERSION_KEY: "1",
                }
                s3_bucket.create_bucket(self._s3_client, bucket_name, self._region, tags)
                self._bucket_name = bucket_name
                bucket_created = True

            # Ensure DynamoDB lock table exists
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

            if bucket_created:
                display_manager.success(f"S3 project store created: {self._bucket_name}")
            if ddb_table_created:
                display_manager.success(f"State lock DynamoDB table created: {STORE_DDB_TABLE_NAME}")
            if bucket_created or ddb_table_created:
                display_manager.line()
            return StoreInfo(store_type="s3-ddb", store_id=self._bucket_name, location=self._region)

    def push(self, project_path: Path, project_id: str, display_manager: DisplayManager) -> SyncResult:
        if not self._bucket_name:
            raise ProjectStoreNotFoundError

        with aws_error_context_manager():
            # Scope the project snapshot under a "project/" subdirectory so it doesn't overlap
            # with engine state (e.g. terraform.tfstate) stored under the root prefix.
            # The sync deletes stale remote objects, so without this separation it would delete
            # the engine state files, which are gitignored and therefore absent from the local
            # file walk.
            prefix = f"{project_id}/project/"
            gitignore_path = project_path / ".gitignore"

            display_manager.info(f"Updating remote store: {self._bucket_name}, prefix: {prefix}")
            result = s3_sync.sync_to_remote(
                self._s3_client,
                self._bucket_name,
                prefix,
                project_path,
                gitignore_path if gitignore_path.exists() else None,
            )

            display_manager.success(
                f"Updated project store: {result.uploaded} uploaded, "
                f"{result.deleted} deleted, {result.unchanged} unchanged"
            )
            return SyncResult(uploaded=result.uploaded, deleted=result.deleted, unchanged=result.unchanged)

    def pull(self, project_id: str, dest_path: Path, display_manager: DisplayManager) -> SyncResult:
        if not self._bucket_name:
            raise ProjectStoreNotFoundError

        with aws_error_context_manager():
            prefix = f"{project_id}/project/"

            display_manager.info(f"Pulling project from s3://{self._bucket_name}/{prefix} to {dest_path.absolute()}")
            result = s3_sync.sync_from_remote(self._s3_client, self._bucket_name, prefix, dest_path)

            display_manager.success(f"Pull complete: {result.uploaded} files downloaded")
            return SyncResult(uploaded=result.uploaded, deleted=result.deleted, unchanged=result.unchanged)

    def list_projects(self, display_manager: DisplayManager) -> list[ProjectSummary]:
        if not self._bucket_name:
            raise ProjectStoreNotFoundError

        with aws_error_context_manager():
            display_manager.info(f"Listing projects in projects store: {self._bucket_name}")
            prefixes = s3_bucket.list_top_level_prefixes(self._s3_client, self._bucket_name)
            summaries: list[ProjectSummary] = []

            for prefix_name in prefixes:
                objects = s3_object.list_objects(self._s3_client, self._bucket_name, f"{prefix_name}/")
                last_modified = (
                    max(obj["LastModified"] for obj in objects) if objects else datetime.min.replace(tzinfo=UTC)
                )
                summaries.append(
                    ProjectSummary(
                        project_id=prefix_name,
                        last_modified=last_modified,
                        file_count=len(objects),
                    )
                )

            return summaries

    def delete_project(self, project_id: str, display_manager: DisplayManager) -> None:
        if not self._bucket_name:
            raise ProjectStoreNotFoundError

        with aws_error_context_manager():
            display_manager.info(f"Deleting project '{project_id}' from projects store: {self._bucket_name}")
            objects = s3_object.list_objects(self._s3_client, self._bucket_name, f"{project_id}/")
            if objects:
                display_manager.info(f"Found {len(objects)} for the project in projects store: {self._bucket_name}")
                keys = [obj["Key"] for obj in objects]
                s3_object.delete_objects(self._s3_client, self._bucket_name, keys)
            display_manager.success(
                f"Deleted {len(objects)} for project '{project_id}' in projects store: {self._bucket_name}"
            )
