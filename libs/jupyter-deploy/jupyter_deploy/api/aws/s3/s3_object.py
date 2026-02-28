from __future__ import annotations

from mypy_boto3_s3.client import S3Client
from mypy_boto3_s3.type_defs import DeleteTypeDef, ObjectTypeDef


def list_objects(s3_client: S3Client, bucket_name: str, prefix: str) -> list[ObjectTypeDef]:
    """Paginates S3:ListObjectsV2 in a bucket under a prefix.

    Raises:
        botocore.exceptions.ClientError on AWS API errors.
    """
    objects: list[ObjectTypeDef] = []
    paginator = s3_client.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        for obj in page.get("Contents", []):
            objects.append(obj)

    return objects


def upload_file(s3_client: S3Client, bucket_name: str, key: str, file_path: str) -> None:
    """Upload a local file to an S3 bucket at the specified key.

    Raises:
        botocore.exceptions.ClientError on AWS API errors.
    """
    s3_client.upload_file(Filename=file_path, Bucket=bucket_name, Key=key)


def download_file(s3_client: S3Client, bucket_name: str, key: str, file_path: str) -> None:
    """Download an S3 object from a bucket/key to a local path.

    Raises:
        botocore.exceptions.ClientError on AWS API errors.
    """
    s3_client.download_file(Bucket=bucket_name, Key=key, Filename=file_path)


def delete_objects(s3_client: S3Client, bucket_name: str, keys: list[str]) -> None:
    """Paginate batch delete objects.

    Raises:
        botocore.exceptions.ClientError on AWS API errors.
    """
    batch_size = 1000
    for i in range(0, len(keys), batch_size):
        batch = keys[i : i + batch_size]
        delete_request: DeleteTypeDef = {"Objects": [{"Key": k} for k in batch], "Quiet": True}
        s3_client.delete_objects(Bucket=bucket_name, Delete=delete_request)
