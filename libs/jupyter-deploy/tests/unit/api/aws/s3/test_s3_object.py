import unittest
from datetime import UTC, datetime
from unittest.mock import Mock

import botocore.exceptions

from jupyter_deploy.api.aws.s3.s3_object import (
    delete_objects,
    download_file,
    list_objects,
    upload_file,
)


class TestListObjects(unittest.TestCase):
    def test_returns_objects_from_single_page(self) -> None:
        mock_s3 = Mock()
        now = datetime.now(tz=UTC)
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": "proj/file.txt", "Size": 100, "LastModified": now}]}
        ]
        mock_s3.get_paginator.return_value = mock_paginator

        result = list_objects(mock_s3, "bucket", "proj/")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Key"], "proj/file.txt")
        self.assertEqual(result[0]["Size"], 100)
        self.assertEqual(result[0]["LastModified"], now)

    def test_returns_objects_from_multiple_pages(self) -> None:
        mock_s3 = Mock()
        now = datetime.now(tz=UTC)
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": "proj/a.txt", "Size": 10, "LastModified": now}]},
            {"Contents": [{"Key": "proj/b.txt", "Size": 20, "LastModified": now}]},
        ]
        mock_s3.get_paginator.return_value = mock_paginator

        result = list_objects(mock_s3, "bucket", "proj/")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["Key"], "proj/a.txt")
        self.assertEqual(result[1]["Key"], "proj/b.txt")

    def test_returns_empty_list_when_no_contents(self) -> None:
        mock_s3 = Mock()
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [{}]
        mock_s3.get_paginator.return_value = mock_paginator

        result = list_objects(mock_s3, "bucket", "proj/")

        self.assertEqual(result, [])


class TestUploadFile(unittest.TestCase):
    def test_calls_upload_file(self) -> None:
        mock_s3 = Mock()

        upload_file(mock_s3, "bucket", "key/file.txt", "/tmp/file.txt")

        mock_s3.upload_file.assert_called_once_with(Filename="/tmp/file.txt", Bucket="bucket", Key="key/file.txt")

    def test_raises_on_client_error(self) -> None:
        mock_s3 = Mock()
        mock_s3.upload_file.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "Not found"}}, "PutObject"
        )

        with self.assertRaises(botocore.exceptions.ClientError):
            upload_file(mock_s3, "bucket", "key/file.txt", "/tmp/file.txt")


class TestDownloadFile(unittest.TestCase):
    def test_calls_download_file(self) -> None:
        mock_s3 = Mock()

        download_file(mock_s3, "bucket", "key/file.txt", "/tmp/file.txt")

        mock_s3.download_file.assert_called_once_with(Bucket="bucket", Key="key/file.txt", Filename="/tmp/file.txt")

    def test_raises_on_client_error(self) -> None:
        mock_s3 = Mock()
        mock_s3.download_file.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}, "GetObject"
        )

        with self.assertRaises(botocore.exceptions.ClientError):
            download_file(mock_s3, "bucket", "key/file.txt", "/tmp/file.txt")


class TestDeleteObjects(unittest.TestCase):
    def test_deletes_single_batch(self) -> None:
        mock_s3 = Mock()
        keys = ["key1", "key2", "key3"]

        delete_objects(mock_s3, "bucket", keys)

        mock_s3.delete_objects.assert_called_once()
        call_args = mock_s3.delete_objects.call_args
        self.assertEqual(call_args[1]["Bucket"], "bucket")
        objects = call_args[1]["Delete"]["Objects"]
        self.assertEqual(len(objects), 3)

    def test_batches_over_1000_keys(self) -> None:
        mock_s3 = Mock()
        keys = [f"key-{i}" for i in range(2500)]

        delete_objects(mock_s3, "bucket", keys)

        self.assertEqual(mock_s3.delete_objects.call_count, 3)
        # First batch: 1000
        first_call = mock_s3.delete_objects.call_args_list[0]
        self.assertEqual(len(first_call[1]["Delete"]["Objects"]), 1000)
        # Second batch: 1000
        second_call = mock_s3.delete_objects.call_args_list[1]
        self.assertEqual(len(second_call[1]["Delete"]["Objects"]), 1000)
        # Third batch: 500
        third_call = mock_s3.delete_objects.call_args_list[2]
        self.assertEqual(len(third_call[1]["Delete"]["Objects"]), 500)

    def test_does_nothing_for_empty_keys(self) -> None:
        mock_s3 = Mock()

        delete_objects(mock_s3, "bucket", [])

        mock_s3.delete_objects.assert_not_called()

    def test_raises_on_client_error(self) -> None:
        mock_s3 = Mock()
        mock_s3.delete_objects.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Forbidden"}}, "DeleteObjects"
        )

        with self.assertRaises(botocore.exceptions.ClientError):
            delete_objects(mock_s3, "bucket", ["key1"])
