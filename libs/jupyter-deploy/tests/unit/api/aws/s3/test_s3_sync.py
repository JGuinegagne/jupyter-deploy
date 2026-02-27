import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch

import botocore.exceptions
from mypy_boto3_s3.type_defs import ObjectTypeDef

from jupyter_deploy.api.aws.s3.s3_sync import (
    _compute_diff,
    sync_from_remote,
    sync_to_remote,
)


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


class TestSyncToRemote(unittest.TestCase):
    @patch("jupyter_deploy.api.aws.s3.s3_sync.delete_objects")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.upload_file")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.list_objects")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.walk_local_files_with_gitignore_rules")
    def test_uploads_new_files(self, mock_walk: Mock, mock_list: Mock, mock_upload: Mock, mock_delete: Mock) -> None:
        local_path = Path("/project")
        file_a = local_path / "a.txt"
        mock_walk.return_value = [file_a]
        mock_list.return_value = []

        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value = Mock(st_size=100, st_mtime=1000.0)
            result = sync_to_remote(Mock(), "bucket", "proj/", local_path)

        self.assertEqual(result.uploaded, 1)
        self.assertEqual(result.deleted, 0)
        mock_upload.assert_called_once()

    @patch("jupyter_deploy.api.aws.s3.s3_sync.delete_objects")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.upload_file")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.list_objects")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.walk_local_files_with_gitignore_rules")
    def test_deletes_stale_remote_files(
        self, mock_walk: Mock, mock_list: Mock, mock_upload: Mock, mock_delete: Mock
    ) -> None:
        local_path = Path("/project")
        mock_walk.return_value = []
        mock_list.return_value = [_obj("proj/stale.txt", 50, datetime.now(tz=UTC))]

        result = sync_to_remote(Mock(), "bucket", "proj/", local_path)

        self.assertEqual(result.deleted, 1)
        mock_delete.assert_called_once()

    @patch("jupyter_deploy.api.aws.s3.s3_sync.delete_objects")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.upload_file")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.list_objects")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.walk_local_files_with_gitignore_rules")
    def test_skips_unchanged_files(
        self, mock_walk: Mock, mock_list: Mock, mock_upload: Mock, mock_delete: Mock
    ) -> None:
        local_path = Path("/project")
        file_a = local_path / "a.txt"
        mock_walk.return_value = [file_a]
        remote_ts = datetime(2025, 1, 1, tzinfo=UTC)
        mock_list.return_value = [_obj("proj/a.txt", 100, remote_ts)]

        with patch.object(Path, "stat") as mock_stat:
            # Same size, local mtime older than remote
            mock_stat.return_value = Mock(st_size=100, st_mtime=remote_ts.timestamp() - 100)
            result = sync_to_remote(Mock(), "bucket", "proj/", local_path)

        self.assertEqual(result.uploaded, 0)
        self.assertEqual(result.unchanged, 1)
        mock_upload.assert_not_called()

    @patch("jupyter_deploy.api.aws.s3.s3_sync.delete_objects")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.upload_file")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.list_objects")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.walk_local_files_with_gitignore_rules")
    def test_uploads_files_with_different_size(
        self, mock_walk: Mock, mock_list: Mock, mock_upload: Mock, mock_delete: Mock
    ) -> None:
        local_path = Path("/project")
        file_a = local_path / "a.txt"
        mock_walk.return_value = [file_a]
        remote_ts = datetime(2025, 1, 1, tzinfo=UTC)
        mock_list.return_value = [_obj("proj/a.txt", 50, remote_ts)]

        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value = Mock(st_size=100, st_mtime=remote_ts.timestamp() - 100)
            result = sync_to_remote(Mock(), "bucket", "proj/", local_path)

        self.assertEqual(result.uploaded, 1)
        mock_upload.assert_called_once()

    @patch("jupyter_deploy.api.aws.s3.s3_sync.delete_objects")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.upload_file")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.list_objects")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.walk_local_files_with_gitignore_rules")
    def test_uploads_when_local_newer_same_size(
        self, mock_walk: Mock, mock_list: Mock, mock_upload: Mock, mock_delete: Mock
    ) -> None:
        local_path = Path("/project")
        file_a = local_path / "a.txt"
        mock_walk.return_value = [file_a]
        remote_ts = datetime(2025, 1, 1, tzinfo=UTC)
        mock_list.return_value = [_obj("proj/a.txt", 100, remote_ts)]

        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value = Mock(st_size=100, st_mtime=remote_ts.timestamp() + 3600)
            result = sync_to_remote(Mock(), "bucket", "proj/", local_path)

        self.assertEqual(result.uploaded, 1)
        self.assertEqual(result.unchanged, 0)
        mock_upload.assert_called_once()

    @patch("jupyter_deploy.api.aws.s3.s3_sync.delete_objects")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.upload_file")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.list_objects")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.walk_local_files_with_gitignore_rules")
    def test_skips_when_remote_newer_same_size(
        self, mock_walk: Mock, mock_list: Mock, mock_upload: Mock, mock_delete: Mock
    ) -> None:
        local_path = Path("/project")
        file_a = local_path / "a.txt"
        mock_walk.return_value = [file_a]
        remote_ts = datetime(2025, 6, 1, tzinfo=UTC)
        mock_list.return_value = [_obj("proj/a.txt", 100, remote_ts)]

        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value = Mock(st_size=100, st_mtime=remote_ts.timestamp() - 3600)
            result = sync_to_remote(Mock(), "bucket", "proj/", local_path)

        self.assertEqual(result.uploaded, 0)
        self.assertEqual(result.unchanged, 1)
        mock_upload.assert_not_called()

    @patch("jupyter_deploy.api.aws.s3.s3_sync.walk_local_files_with_gitignore_rules")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.list_objects")
    def test_raises_when_list_objects_fails(self, mock_list: Mock, mock_walk: Mock) -> None:
        mock_walk.return_value = []
        mock_list.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "Not found"}}, "ListObjectsV2"
        )

        with self.assertRaises(botocore.exceptions.ClientError):
            sync_to_remote(Mock(), "bucket", "proj/", Path("/project"))

    @patch("jupyter_deploy.api.aws.s3.s3_sync.upload_file")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.list_objects")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.walk_local_files_with_gitignore_rules")
    def test_raises_when_upload_fails(self, mock_walk: Mock, mock_list: Mock, mock_upload: Mock) -> None:
        local_path = Path("/project")
        mock_walk.return_value = [local_path / "a.txt"]
        mock_list.return_value = []
        mock_upload.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Forbidden"}}, "PutObject"
        )

        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value = Mock(st_size=100, st_mtime=1000.0)
            with self.assertRaises(botocore.exceptions.ClientError):
                sync_to_remote(Mock(), "bucket", "proj/", local_path)

    @patch("jupyter_deploy.api.aws.s3.s3_sync.delete_objects")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.upload_file")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.list_objects")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.walk_local_files_with_gitignore_rules")
    def test_raises_when_delete_fails(
        self, mock_walk: Mock, mock_list: Mock, mock_upload: Mock, mock_delete: Mock
    ) -> None:
        mock_walk.return_value = []
        mock_list.return_value = [_obj("proj/stale.txt", 50, datetime.now(tz=UTC))]
        mock_delete.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Forbidden"}}, "DeleteObjects"
        )

        with self.assertRaises(botocore.exceptions.ClientError):
            sync_to_remote(Mock(), "bucket", "proj/", Path("/project"))


class TestSyncFromRemote(unittest.TestCase):
    @patch("jupyter_deploy.api.aws.s3.s3_sync.download_file")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.list_objects")
    def test_downloads_all_remote_files(self, mock_list: Mock, mock_download: Mock) -> None:
        now = datetime.now(tz=UTC)
        mock_list.return_value = [
            _obj("proj/a.txt", 100, now),
            _obj("proj/sub/b.txt", 200, now),
        ]

        with patch.object(Path, "mkdir"):
            result = sync_from_remote(Mock(), "bucket", "proj/", Path("/dest"))

        self.assertEqual(result.uploaded, 2)
        self.assertEqual(mock_download.call_count, 2)

    @patch("jupyter_deploy.api.aws.s3.s3_sync.download_file")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.list_objects")
    def test_skips_empty_relative_key(self, mock_list: Mock, mock_download: Mock) -> None:
        now = datetime.now(tz=UTC)
        # Object whose key equals the prefix exactly (empty relative key)
        mock_list.return_value = [_obj("proj/", 0, now)]

        result = sync_from_remote(Mock(), "bucket", "proj/", Path("/dest"))

        self.assertEqual(result.uploaded, 0)
        mock_download.assert_not_called()

    @patch("jupyter_deploy.api.aws.s3.s3_sync.download_file")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.list_objects")
    def test_returns_zero_when_no_remote_objects(self, mock_list: Mock, mock_download: Mock) -> None:
        mock_list.return_value = []

        result = sync_from_remote(Mock(), "bucket", "proj/", Path("/dest"))

        self.assertEqual(result.uploaded, 0)
        mock_download.assert_not_called()

    @patch("jupyter_deploy.api.aws.s3.s3_sync.list_objects")
    def test_raises_when_list_objects_fails(self, mock_list: Mock) -> None:
        mock_list.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "Not found"}}, "ListObjectsV2"
        )

        with self.assertRaises(botocore.exceptions.ClientError):
            sync_from_remote(Mock(), "bucket", "proj/", Path("/dest"))

    @patch("jupyter_deploy.api.aws.s3.s3_sync.download_file")
    @patch("jupyter_deploy.api.aws.s3.s3_sync.list_objects")
    def test_raises_when_download_fails(self, mock_list: Mock, mock_download: Mock) -> None:
        now = datetime.now(tz=UTC)
        mock_list.return_value = [_obj("proj/a.txt", 100, now)]
        mock_download.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Forbidden"}}, "GetObject"
        )

        with patch.object(Path, "mkdir"), self.assertRaises(botocore.exceptions.ClientError):
            sync_from_remote(Mock(), "bucket", "proj/", Path("/dest"))


class TestComputeDiff(unittest.TestCase):
    def test_new_file_marked_for_upload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            f = base / "new.txt"
            f.write_text("content")

            diff = _compute_diff([f], [], base, "proj/")

            self.assertEqual(len(diff.to_upload), 1)
            self.assertEqual(diff.to_upload[0], f)
            self.assertEqual(diff.unchanged, 0)

    def test_changed_size_marked_for_upload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            f = base / "changed.txt"
            f.write_text("new content that is different size")

            remote = [_obj("proj/changed.txt", 5, datetime.now(tz=UTC))]
            diff = _compute_diff([f], remote, base, "proj/")

            self.assertEqual(len(diff.to_upload), 1)

    def test_unchanged_file_not_uploaded(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            f = base / "same.txt"
            f.write_text("same")
            size = f.stat().st_size
            # Remote last_modified is in the future relative to local mtime
            remote_ts = datetime(2099, 1, 1, tzinfo=UTC)
            remote = [_obj("proj/same.txt", size, remote_ts)]

            diff = _compute_diff([f], remote, base, "proj/")

            self.assertEqual(len(diff.to_upload), 0)
            self.assertEqual(diff.unchanged, 1)

    def test_stale_remote_marked_for_delete(self) -> None:
        remote = [_obj("proj/stale.txt", 10, datetime.now(tz=UTC))]

        diff = _compute_diff([], remote, Path("/project"), "proj/")

        self.assertEqual(diff.to_delete, ["proj/stale.txt"])

    def test_newer_local_file_uploaded(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            f = base / "updated.txt"
            f.write_text("updated")
            size = f.stat().st_size
            # Remote is very old
            old_ts = datetime(2000, 1, 1, tzinfo=UTC)
            remote = [_obj("proj/updated.txt", size, old_ts)]

            diff = _compute_diff([f], remote, base, "proj/")

            self.assertEqual(len(diff.to_upload), 1)
