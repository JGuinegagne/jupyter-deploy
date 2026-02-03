"""Tests for CommandHistoryHandler."""

import unittest
from datetime import UTC
from pathlib import Path
from unittest.mock import Mock, patch

from jupyter_deploy.constants import HISTORY_DIR
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
        log_file = self.handler.create_log_file("config")

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
    def test_create_log_file_ensures_directory_and_file_exist(self, mock_mkdir: Mock, mock_touch: Mock) -> None:
        """Test that create_log_file ensures command subdirectory and file exist."""
        # Act
        self.handler.create_log_file("up")

        # Assert
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_touch.assert_called_once_with(exist_ok=True)

    @patch("pathlib.Path.touch")
    @patch("pathlib.Path.mkdir")
    def test_create_log_file_works_with_different_commands(self, _mock_mkdir: Mock, mock_touch: Mock) -> None:
        """Test that create_log_file works with different command names."""
        # Act
        config_log = self.handler.create_log_file("config")
        up_log = self.handler.create_log_file("up")
        down_log = self.handler.create_log_file("down")

        # Assert
        self.assertTrue(str(config_log).endswith(".log"))
        self.assertIn(f"{HISTORY_DIR}/config/", str(config_log))
        self.assertTrue(str(up_log).endswith(".log"))
        self.assertIn(f"{HISTORY_DIR}/up/", str(up_log))
        self.assertTrue(str(down_log).endswith(".log"))
        self.assertIn(f"{HISTORY_DIR}/down/", str(down_log))
        # Verify touch was called for each log file
        self.assertEqual(mock_touch.call_count, 3)

    @patch("pathlib.Path.touch")
    @patch("pathlib.Path.mkdir")
    @patch("jupyter_deploy.handlers.command_history_handler.datetime")
    def test_create_log_file_uses_utc_timezone(
        self, mock_datetime_module: Mock, _mock_mkdir: Mock, _mock_touch: Mock
    ) -> None:
        """Test that create_log_file uses UTC timezone for timestamps."""
        # Mock datetime
        mock_now = Mock()
        mock_now.strftime.return_value = "20260129-143022"
        mock_datetime_module.now.return_value = mock_now

        # Act
        self.handler.create_log_file("config")

        # Assert
        mock_datetime_module.now.assert_called_once_with(UTC)

    @patch("pathlib.Path.touch")
    @patch("pathlib.Path.mkdir")
    @patch("jupyter_deploy.handlers.command_history_handler.datetime")
    def test_create_log_file_timestamp_format(
        self, mock_datetime_module: Mock, _mock_mkdir: Mock, _mock_touch: Mock
    ) -> None:
        """Test that create_log_file formats timestamp as YYYYMMDD-HHMMSS."""
        # Mock datetime
        mock_now = Mock()
        mock_now.strftime.return_value = "20260129-143022"
        mock_datetime_module.now.return_value = mock_now

        # Act
        self.handler.create_log_file("config")

        # Assert - verify strftime was called with correct format
        mock_now.strftime.assert_called_once_with("%Y%m%d-%H%M%S")

    @patch("pathlib.Path.touch")
    @patch("pathlib.Path.mkdir")
    @patch("jupyter_deploy.handlers.command_history_handler.datetime")
    def test_create_log_file_multiple_calls_different_timestamps(
        self, mock_datetime_module: Mock, _mock_mkdir: Mock, _mock_touch: Mock
    ) -> None:
        """Test that multiple calls generate different timestamps."""
        # Mock datetime to return different timestamps
        mock_now1 = Mock()
        mock_now1.strftime.return_value = "20260129-143022"
        mock_now2 = Mock()
        mock_now2.strftime.return_value = "20260129-143023"

        mock_datetime_module.now.side_effect = [mock_now1, mock_now2]

        # Act
        log_file1 = self.handler.create_log_file("config")
        log_file2 = self.handler.create_log_file("config")

        # Assert
        self.assertNotEqual(log_file1, log_file2)
        self.assertEqual(log_file1.name, "20260129-143022.log")
        self.assertEqual(log_file2.name, "20260129-143023.log")
