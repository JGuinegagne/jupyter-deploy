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
from jupyter_deploy.engine.supervised_execution import DisplayManager
from jupyter_deploy.exceptions import BackupStoreNotFoundError
from jupyter_deploy.provider.aws.aws_error_handler import aws_error_context_manager
from jupyter_deploy.provider.aws.store.constants import (
    BACKUP_BUCKET_NAME_PREFIX,
    BACKUP_DDB_TABLE_NAME,
    BACKUP_TAG_SOURCE_KEY,
    BACKUP_TAG_SOURCE_VALUE,
    BACKUP_TAG_VERSION_KEY,
)
from jupyter_deploy.provider.store.store_manager import ProjectSummary, StoreInfo, StoreManager, SyncResult


class S3DynamoDbTableStoreManager(StoreManager):
    """StoreManager implementation backed by S3 and DynamoDB.

    The S3 bucket acts as:
        - backup for the jupyter-deploy project dir, which includes
            all the files that are not gitignored.
        - for terraform engine: the terraform backend

    The DynamoDB table acts as:
        - for terraform engine: the lock state table preventing concurrent updates
    """

    def __init__(self, region: str, bucket_name: str | None = None) -> None:
        self._region = region
        self._bucket_name = bucket_name
        self._s3_client: S3Client = boto3.client("s3", region_name=region)
        self._dynamodb_client: DynamoDBClient = boto3.client("dynamodb", region_name=region)

    def ensure_store(self, display_manager: DisplayManager) -> StoreInfo:
        with aws_error_context_manager():
            bucket_name = self._bucket_name
            already_exists = True

            if not bucket_name:
                display_manager.info("Looking for existing projects store in your AWS account...")
                matched = s3_bucket.find_buckets_by_tag(self._s3_client, BACKUP_TAG_SOURCE_KEY, BACKUP_TAG_SOURCE_VALUE)
                bucket_name = matched[0].get("Name") if matched else None

            if bucket_name:
                display_manager.info(f"Found existing S3 bucket projects store: {bucket_name}")
                self._bucket_name = bucket_name
            else:
                already_exists = False
                # Random suffix prevents bucket name sniping attacks. 20 hex chars = 80 bits
                # of entropy from os.urandom (CSPRNG); birthday collision at ~2^40 (~1 trillion).
                # Total name length: 24 (prefix) + 1 (dash) + 20 (suffix) = 45 chars (S3 max: 63).
                bucket_name = f"{BACKUP_BUCKET_NAME_PREFIX}-{uuid.uuid4().hex[:20]}"
                display_manager.info(f"Creating S3 bucket projects store: {bucket_name}")
                tags = {
                    BACKUP_TAG_SOURCE_KEY: BACKUP_TAG_SOURCE_VALUE,
                    BACKUP_TAG_VERSION_KEY: "1",
                }
                s3_bucket.create_bucket(self._s3_client, bucket_name, self._region, tags)
                self._bucket_name = bucket_name

            # Ensure DynamoDB lock table exists
            try:
                display_manager.info("Looking for existing dynamoDB table...")
                dynamodb_table.get_table_by_name(self._dynamodb_client, BACKUP_DDB_TABLE_NAME)
                display_manager.info(f"Found existing dynamoDB table: {BACKUP_DDB_TABLE_NAME}")
            except botocore.exceptions.ClientError as e:
                if e.response.get("Error", {}).get("Code") != "ResourceNotFoundException":
                    raise
                already_exists = False
                display_manager.info(f"Creating dynamoDB table: {BACKUP_DDB_TABLE_NAME}")
                tags = {
                    BACKUP_TAG_SOURCE_KEY: BACKUP_TAG_SOURCE_VALUE,
                    BACKUP_TAG_VERSION_KEY: "1",
                }
                dynamodb_table.create_lock_table(self._dynamodb_client, BACKUP_DDB_TABLE_NAME, tags)
                dynamodb_table.wait_for_table_active(self._dynamodb_client, BACKUP_DDB_TABLE_NAME)

            if not already_exists:
                display_manager.success(f"Projects store is configured in your AWS account: {bucket_name}")
            return StoreInfo(store_type="s3-ddb", store_id=self._bucket_name, location=self._region)

    def push(self, project_path: Path, project_id: str, display_manager: DisplayManager) -> SyncResult:
        if not self._bucket_name:
            raise BackupStoreNotFoundError

        with aws_error_context_manager():
            prefix = f"{project_id}/"
            gitignore_path = project_path / ".gitignore"

            display_manager.info(f"Syncing project at '{project_path.absolute()}' to s3://{self._bucket_name}/{prefix}")
            result = s3_sync.sync_to_remote(
                self._s3_client,
                self._bucket_name,
                prefix,
                project_path,
                gitignore_path if gitignore_path.exists() else None,
            )

            display_manager.success(
                f"Push complete: {result.uploaded} uploaded, {result.deleted} deleted, {result.unchanged} unchanged"
            )
            return SyncResult(uploaded=result.uploaded, deleted=result.deleted, unchanged=result.unchanged)

    def pull(self, project_id: str, dest_path: Path, display_manager: DisplayManager) -> SyncResult:
        if not self._bucket_name:
            raise BackupStoreNotFoundError

        with aws_error_context_manager():
            prefix = f"{project_id}/"

            display_manager.info(f"Pulling project from s3://{self._bucket_name}/{prefix} to {dest_path.absolute()}")
            result = s3_sync.sync_from_remote(self._s3_client, self._bucket_name, prefix, dest_path)

            display_manager.success(f"Pull complete: {result.uploaded} files downloaded")
            return SyncResult(uploaded=result.uploaded, deleted=result.deleted, unchanged=result.unchanged)

    def list_projects(self, display_manager: DisplayManager) -> list[ProjectSummary]:
        if not self._bucket_name:
            raise BackupStoreNotFoundError

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
            raise BackupStoreNotFoundError

        with aws_error_context_manager():
            display_manager.info(f"Deleting project '{project_id}' from projects store: {self._bucket_name}")
            objects = s3_object.list_objects(self._s3_client, self._bucket_name, f"{project_id}/")
            if objects:
                keys = [obj["Key"] for obj in objects]
                s3_object.delete_objects(self._s3_client, self._bucket_name, keys)
            display_manager.success(
                f"Deleted {len(objects)} for project '{project_id}' in projects store: {self._bucket_name}"
            )
