"""Tests for CommandHistoryHandler."""

import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

from jupyter_deploy.cmd_history import LogFileDescriptor, LogFilesCleanupResult
from jupyter_deploy.constants import HISTORY_DIR
from jupyter_deploy.enum import HistoryEnabledCommandType
from jupyter_deploy.exceptions import LogCleanupError, LogNotFoundError
from jupyter_deploy.handlers.command_history_handler import CommandHistoryHandler


class TestCommandHistoryHandler(unittest.TestCase):
    """Test cases for CommandHistoryHandler class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.project_path = Path("/fake/path")
        self.handler = CommandHistoryHandler(self.project_path)

    def test_class_can_instantiate(self) -> None:
        """Test that CommandHistoryHandler can be instantiated."""
        project_path = Path("/fake/path")
        handler = CommandHistoryHandler(project_path)

        self.assertIsNotNone(handler)
        self.assertEqual(handler.project_path, project_path)
        self.assertEqual(handler.history_dir, project_path / HISTORY_DIR)

    @patch("pathlib.Path.touch")
    @patch("pathlib.Path.mkdir")
    @patch("jupyter_deploy.handlers.command_history_handler.datetime")
    def test_create_log_file_generates_timestamped_path(
        self, mock_datetime_module: Mock, mock_mkdir: Mock, mock_touch: Mock
    ) -> None:
        """Test that create_log_file generates correct timestamped path and creates file."""
        # Mock datetime.now(UTC)
        mock_utc_datetime = Mock()
        mock_utc_datetime.strftime.return_value = "20260129-143022"
        mock_datetime_module.now.return_value = mock_utc_datetime

        # Act
        log_file = self.handler.create_log_file(HistoryEnabledCommandType.CONFIG)

        # Assert
        expected_path = self.project_path / HISTORY_DIR / "config" / "20260129-143022.log"
        self.assertEqual(log_file, expected_path)
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_touch.assert_called_once_with(exist_ok=True)
        mock_utc_datetime.strftime.assert_called_once_with("%Y%m%d-%H%M%S")
        # Verify datetime.now was called with UTC
        mock_datetime_module.now.assert_called_once_with(UTC)

    @patch("pathlib.Path.touch")
    @patch("pathlib.Path.mkdir")
    def test_create_log_file_does_not_auto_cleanup(self, _mock_mkdir: Mock, _mock_touch: Mock) -> None:
        """Test that create_log_file does NOT auto-cleanup (caller must explicitly cleanup)."""
        with patch.object(self.handler, "_cleanup_log_files") as mock_cleanup:
            self.handler.create_log_file(HistoryEnabledCommandType.CONFIG)
            mock_cleanup.assert_not_called()

    @patch("jupyter_deploy.handlers.command_history_handler.list_files_sorted")
    def test_list_logs_returns_empty_when_dir_not_exists(self, mock_list_files: Mock) -> None:
        """Test that list_logs returns empty list when command directory doesn't exist."""
        mock_list_files.side_effect = FileNotFoundError("Directory does not exist")

        result = self.handler.list_logs(command=HistoryEnabledCommandType.CONFIG)

        self.assertEqual(result, [])

    @patch("jupyter_deploy.handlers.command_history_handler.list_files_sorted")
    def test_list_logs_returns_descriptors_for_valid_logs(self, mock_list_files: Mock) -> None:
        """Test that list_logs returns LogFileDescriptor objects for valid log files."""
        # Mock list_files_sorted to return paths in sorted order (newest first)
        mock_list_files.return_value = [
            Path("/fake/path/.jd-history/config/20260129-143023.log"),
            Path("/fake/path/.jd-history/config/20260129-143022.log"),
        ]

        # Act
        result = self.handler.list_logs(command=HistoryEnabledCommandType.CONFIG)

        # Assert
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], LogFileDescriptor)
        self.assertEqual(result[0].command, "config")
        self.assertEqual(result[0].storage_type, "file")
        # Most recent (20260129-143023) should be first
        self.assertEqual(result[0].id, "config/20260129-143023.log")
        mock_list_files.assert_called_once_with(
            self.project_path / HISTORY_DIR / "config", "*.log", max_files=None, reverse=True
        )

    @patch("jupyter_deploy.handlers.command_history_handler.list_files_sorted")
    def test_list_logs_raises_on_malformed_filenames(self, mock_list_files: Mock) -> None:
        """Test that list_logs raises ValueError for malformed log filenames."""
        # Mock list_files_sorted to return a path with invalid timestamp format
        mock_list_files.return_value = [
            Path("/fake/path/.jd-history/config/invalid-timestamp.log"),
        ]

        # Act & Assert - should raise ValueError from strptime
        with self.assertRaises(ValueError):
            self.handler.list_logs(command=HistoryEnabledCommandType.CONFIG)

    @patch("pathlib.Path.exists")
    def test_get_latest_log_returns_none_when_no_logs(self, mock_exists: Mock) -> None:
        """Test that get_latest_log returns None when no logs exist."""
        mock_exists.return_value = False

        result = self.handler.get_latest_log()

        self.assertIsNone(result)

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.iterdir")
    def test_get_latest_log_returns_most_recent_across_commands(self, mock_iterdir: Mock, mock_exists: Mock) -> None:
        """Test that get_latest_log returns most recent log across all commands."""
        mock_exists.return_value = True

        # Mock command directories
        config_dir = Mock(spec=Path)
        config_dir.name = "config"
        config_dir.is_dir.return_value = True

        up_dir = Mock(spec=Path)
        up_dir.name = "up"
        up_dir.is_dir.return_value = True

        mock_iterdir.return_value = [config_dir, up_dir]

        # Mock list_logs to return descriptors with different timestamps
        config_log = LogFileDescriptor(
            id="config/20260129-143022.log",
            command="config",
            timestamp=datetime(2026, 1, 29, 14, 30, 22, tzinfo=UTC),
            path=Path("/fake/path/.jd-history/config/20260129-143022.log"),
        )

        up_log = LogFileDescriptor(
            id="up/20260129-150000.log",
            command="up",
            timestamp=datetime(2026, 1, 29, 15, 0, 0, tzinfo=UTC),  # Most recent
            path=Path("/fake/path/.jd-history/up/20260129-150000.log"),
        )

        def mock_list_logs_side_effect(command: str, max_logs: int | None = None) -> list[LogFileDescriptor]:
            if command == "config":
                return [config_log]
            elif command == "up":
                return [up_log]
            return []

        with patch.object(self.handler, "list_logs", side_effect=mock_list_logs_side_effect):
            result = self.handler.get_latest_log()

            self.assertIsNotNone(result)
            assert result is not None  # Type narrowing for mypy
            self.assertEqual(result.command, "up")
            self.assertEqual(result.timestamp, up_log.timestamp)

    def test_get_log_lines_raises_for_missing_file(self) -> None:
        """Test that get_log_lines raises LogNotFoundError when file doesn't exist."""
        log_descriptor = LogFileDescriptor(
            id="config/20260129-143022.log",
            command="config",
            timestamp=datetime(2026, 1, 29, 14, 30, 22, tzinfo=UTC),
            path=Path("/nonexistent/file.log"),
        )

        with self.assertRaises(LogNotFoundError):
            self.handler.get_log_lines(log_descriptor)

    def test_get_log_lines_returns_all_lines(self) -> None:
        """Test that get_log_lines returns all lines from the log file (up to 1000 default)."""
        log_descriptor = LogFileDescriptor(
            id="config/20260129-143022.log",
            command="config",
            timestamp=datetime(2026, 1, 29, 14, 30, 22, tzinfo=UTC),
            path=Path("/fake/file.log"),
        )

        log_content = "Line 1\nLine 2\nLine 3\n"
        m_open = mock_open(read_data=log_content)

        with patch("builtins.open", m_open):
            result = self.handler.get_log_lines(log_descriptor)

            self.assertIsNotNone(result)
            self.assertEqual(result, ["Line 1\n", "Line 2\n", "Line 3\n"])

    def test_get_log_lines_respects_max_lines(self) -> None:
        """Test that get_log_lines returns only last N lines when max_lines is specified."""
        log_descriptor = LogFileDescriptor(
            id="config/20260129-143022.log",
            command="config",
            timestamp=datetime(2026, 1, 29, 14, 30, 22, tzinfo=UTC),
            path=Path("/fake/file.log"),
        )

        log_content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
        m_open = mock_open(read_data=log_content)

        with patch("builtins.open", m_open):
            result = self.handler.get_log_lines(log_descriptor, max_lines=2)

            self.assertIsNotNone(result)
            self.assertEqual(result, ["Line 4\n", "Line 5\n"])

    def test_get_log_lines_respects_skip(self) -> None:
        """Test that get_log_lines skips lines from end when skip is specified."""
        log_descriptor = LogFileDescriptor(
            id="config/20260129-143022.log",
            command="config",
            timestamp=datetime(2026, 1, 29, 14, 30, 22, tzinfo=UTC),
            path=Path("/fake/file.log"),
        )

        log_content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
        m_open = mock_open(read_data=log_content)

        with patch("builtins.open", m_open):
            # Get 2 lines, skipping the last 2 (should get lines 2 and 3)
            result = self.handler.get_log_lines(log_descriptor, max_lines=2, skip=2)

            self.assertIsNotNone(result)
            self.assertEqual(result, ["Line 2\n", "Line 3\n"])

    def test_stream_log_lines_yields_lines(self) -> None:
        """Test that stream_log_lines yields lines from the log file."""
        log_descriptor = LogFileDescriptor(
            id="config/20260129-143022.log",
            command="config",
            timestamp=datetime(2026, 1, 29, 14, 30, 22, tzinfo=UTC),
            path=Path("/fake/file.log"),
        )

        log_content = "Line 1\nLine 2\nLine 3\n"
        m_open = mock_open(read_data=log_content)

        with patch("builtins.open", m_open):
            result = list(self.handler.stream_log_lines(log_descriptor))

            self.assertEqual(result, ["Line 1\n", "Line 2\n", "Line 3\n"])

    def test_stream_log_lines_raises_for_missing_file(self) -> None:
        """Test that stream_log_lines raises LogNotFoundError when file doesn't exist."""
        log_descriptor = LogFileDescriptor(
            id="config/20260129-143022.log",
            command="config",
            timestamp=datetime(2026, 1, 29, 14, 30, 22, tzinfo=UTC),
            path=Path("/nonexistent/file.log"),
        )

        with self.assertRaises(LogNotFoundError):
            list(self.handler.stream_log_lines(log_descriptor))

    @patch("jupyter_deploy.handlers.command_history_handler.list_files_sorted")
    def test_cleanup_log_files_returns_empty_result_when_dir_not_exists(self, mock_list_files: Mock) -> None:
        """Test that _cleanup_log_files returns empty result when directory doesn't exist."""
        mock_list_files.side_effect = FileNotFoundError("Directory does not exist")

        result = self.handler._cleanup_log_files(HistoryEnabledCommandType.CONFIG, keep=5)

        self.assertIsInstance(result, LogFilesCleanupResult)
        self.assertEqual(result.total_cleaned, 0)
        self.assertEqual(result.total_kept, 0)
        self.assertEqual(result.total_failed, 0)

    @patch("jupyter_deploy.handlers.command_history_handler.list_files_sorted")
    def test_cleanup_log_files_deletes_old_logs_beyond_keep_limit(self, mock_list_files: Mock) -> None:
        """Test that _cleanup_log_files deletes logs beyond the keep limit."""
        # Create 8 mock log paths (already in sorted order, newest first)
        logs = []
        for _ in range(8):
            log = Mock(spec=Path)
            log.unlink = Mock()
            logs.append(log)

        mock_list_files.return_value = logs

        # Act - keep only 5 most recent
        result = self.handler._cleanup_log_files(HistoryEnabledCommandType.CONFIG, keep=5)

        # Assert - should delete 3 oldest logs
        self.assertIsInstance(result, LogFilesCleanupResult)
        self.assertEqual(result.total_cleaned, 3)
        self.assertEqual(result.total_kept, 5)
        self.assertEqual(result.total_failed, 0)
        self.assertEqual(result.cleaned, logs[5:])
        self.assertEqual(result.kept, logs[:5])
        # Verify unlink was called on the 3 oldest logs (indices 5, 6, 7)
        for log in logs[5:]:
            log.unlink.assert_called_once()
        # Verify unlink was NOT called on the 5 newest logs (indices 0-4)
        for log in logs[:5]:
            log.unlink.assert_not_called()

    @patch("jupyter_deploy.handlers.command_history_handler.list_files_sorted")
    def test_cleanup_log_files_handles_unlink_errors_gracefully(self, mock_list_files: Mock) -> None:
        """Test that _cleanup_log_files handles unlink errors gracefully."""
        # Create 7 mock log paths (already in sorted order, newest first)
        logs = []
        for i in range(7):
            log = Mock(spec=Path)
            if i == 5:
                # First old log (index 5 after keep=5) fails to delete
                log.unlink.side_effect = OSError("Permission denied")
            else:
                log.unlink = Mock()
            logs.append(log)

        mock_list_files.return_value = logs

        # Act - keep only 5 most recent
        result = self.handler._cleanup_log_files(HistoryEnabledCommandType.CONFIG, keep=5)

        # Assert - should delete only 1 (the second old log at index 6), track failure on the first (index 5)
        self.assertIsInstance(result, LogFilesCleanupResult)
        self.assertEqual(result.total_cleaned, 1)
        self.assertEqual(result.total_kept, 5)
        self.assertEqual(result.total_failed, 1)
        self.assertEqual(result.cleaned, [logs[6]])
        self.assertEqual(result.kept, logs[:5])
        self.assertEqual(len(result.failed), 1)
        self.assertEqual(result.failed[0][0], logs[5])
        self.assertIsInstance(result.failed[0][1], OSError)

    def test_clear_logs_clears_specific_command(self) -> None:
        """Test that clear_logs clears logs for a specific command."""
        mock_result = LogFilesCleanupResult(
            cleaned=[Path("/fake/log1.log"), Path("/fake/log2.log"), Path("/fake/log3.log")],
            kept=[Path("/fake/log4.log"), Path("/fake/log5.log")],
        )
        with patch.object(self.handler, "_cleanup_log_files", return_value=mock_result) as mock_cleanup:
            result = self.handler.clear_logs(command=HistoryEnabledCommandType.CONFIG, keep=20)

            self.assertIsInstance(result, LogFilesCleanupResult)
            self.assertEqual(result.total_cleaned, 3)
            mock_cleanup.assert_called_once_with("config", keep=20)

    def test_clear_logs_uses_default_keep_value(self) -> None:
        """Test that clear_logs uses default keep value of 20."""
        mock_result = LogFilesCleanupResult(
            cleaned=[Path("/fake/log1.log"), Path("/fake/log2.log")],
            kept=[Path("/fake/log3.log")],
        )
        with patch.object(self.handler, "_cleanup_log_files", return_value=mock_result) as mock_cleanup:
            result = self.handler.clear_logs(command=HistoryEnabledCommandType.CONFIG)

            self.assertIsInstance(result, LogFilesCleanupResult)
            self.assertEqual(result.total_cleaned, 2)
            mock_cleanup.assert_called_once_with("config", keep=20)

    def test_clear_logs_raises_exception_on_failures(self) -> None:
        """Test that clear_logs raises LogCleanupError when deletions fail."""
        mock_result = LogFilesCleanupResult(
            cleaned=[Path("/fake/log1.log")],
            kept=[Path("/fake/log2.log")],
            failed=[(Path("/fake/log3.log"), OSError("Permission denied"))],
        )
        with patch.object(self.handler, "_cleanup_log_files", return_value=mock_result):
            with self.assertRaises(LogCleanupError) as context:
                self.handler.clear_logs(command=HistoryEnabledCommandType.CONFIG, keep=20)

            self.assertEqual(str(context.exception), "Failed to delete 1 log file(s)")
