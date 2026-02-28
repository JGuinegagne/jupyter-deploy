from __future__ import annotations

from pathlib import Path

from mypy_boto3_s3.client import S3Client
from mypy_boto3_s3.type_defs import ObjectTypeDef
from pydantic import BaseModel, ConfigDict, Field

from jupyter_deploy.api.aws.s3.s3_object import delete_objects, download_file, list_objects, upload_file
from jupyter_deploy.fs_utils import walk_local_files_with_gitignore_rules


class SyncDiff(BaseModel):
    """Result of comparing local files against remote objects."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    to_upload: list[Path] = Field(default_factory=list)
    to_delete: list[str] = Field(default_factory=list)
    unchanged: int = 0


class S3SyncResult(BaseModel):
    """Result of a sync operation."""

    uploaded: int = 0
    deleted: int = 0
    unchanged: int = 0


def sync_to_remote(
    s3_client: S3Client,
    bucket_name: str,
    prefix: str,
    local_path: Path,
    gitignore_path: Path | None = None,
) -> S3SyncResult:
    """Sync local files to S3, uploading changed/new files and deleting stale remote objects.

    Args:
        s3_client: S3 client
        bucket_name: Target bucket
        prefix: S3 key prefix for this project
        local_path: Local directory to sync from
        gitignore_path: Optional path to a .gitignore file for filtering

    Returns:
        S3SyncResult with counts of uploaded, deleted, and unchanged files.
    """
    local_files = walk_local_files_with_gitignore_rules(local_path, gitignore_path)
    remote_objects = list_objects(s3_client, bucket_name, prefix)
    diff = _compute_diff(local_files, remote_objects, local_path, prefix)

    for file_path in diff.to_upload:
        relative = file_path.relative_to(local_path)
        # S3 keys accept any UTF-8 string up to 1024 bytes; safe chars are [0-9a-zA-Z!._*'()-].
        # The main concern is OS path separators: as_posix() normalizes backslashes to forward
        # slashes, which is the same approach the AWS CLI uses via normalize_sort().
        # ref: https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-keys.html
        # ref: https://github.com/aws/aws-cli/tree/develop/awscli/customizations/s3
        key = f"{prefix}{relative.as_posix()}"
        upload_file(s3_client, bucket_name, key, str(file_path))

    if diff.to_delete:
        delete_objects(s3_client, bucket_name, diff.to_delete)

    return S3SyncResult(
        uploaded=len(diff.to_upload),
        deleted=len(diff.to_delete),
        unchanged=diff.unchanged,
    )


def sync_from_remote(
    s3_client: S3Client,
    bucket_name: str,
    prefix: str,
    local_path: Path,
) -> S3SyncResult:
    """Download all remote objects under prefix to the local path.

    Args:
        s3_client: S3 client
        bucket_name: Source bucket
        prefix: S3 key prefix
        local_path: Local directory to download to

    Returns:
        S3SyncResult with count of downloaded files.
    """
    remote_objects = list_objects(s3_client, bucket_name, prefix)

    downloaded = 0
    for obj in remote_objects:
        # Strip the prefix to get the relative path
        relative_key = obj.get("Key", "")[len(prefix) :]
        if not relative_key:
            continue
        dest = local_path / relative_key
        dest.parent.mkdir(parents=True, exist_ok=True)
        download_file(s3_client, bucket_name, obj.get("Key", ""), str(dest))
        downloaded += 1

    return S3SyncResult(uploaded=downloaded, deleted=0, unchanged=0)


def _compute_diff(
    local_files: list[Path],
    remote_objects: list[ObjectTypeDef],
    local_path: Path,
    prefix: str,
) -> SyncDiff:
    """Determine which files to upload and which remote objects to delete."""
    remote_map: dict[str, ObjectTypeDef] = {obj.get("Key", ""): obj for obj in remote_objects}

    diff = SyncDiff()
    seen_keys: set[str] = set()

    for file_path in local_files:
        relative = file_path.relative_to(local_path)
        # S3 keys accept any UTF-8 string up to 1024 bytes; safe chars are [0-9a-zA-Z!._*'()-].
        # The main concern is OS path separators: as_posix() normalizes backslashes to forward
        # slashes, which is the same approach the AWS CLI uses via normalize_sort().
        # ref: https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-keys.html
        # ref: https://github.com/aws/aws-cli/tree/develop/awscli/customizations/s3
        key = f"{prefix}{relative.as_posix()}"
        seen_keys.add(key)

        remote_obj = remote_map.get(key)
        if remote_obj is None:
            # New file
            diff.to_upload.append(file_path)
        elif file_path.stat().st_size != remote_obj.get("Size", ""):
            # Size changed
            diff.to_upload.append(file_path)
        else:
            local_mtime = file_path.stat().st_mtime
            remote_ts = remote_obj["LastModified"].timestamp()
            if local_mtime > remote_ts:
                # Local file is newer
                diff.to_upload.append(file_path)
            else:
                diff.unchanged += 1

    # Remote objects not in local files should be deleted
    for key in remote_map:
        if key not in seen_keys:
            diff.to_delete.append(key)

    return diff
