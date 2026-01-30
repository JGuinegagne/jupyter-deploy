"""Tests for CommandHistoryHandler."""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from jupyter_deploy.handlers.command_history_handler import CommandHistoryHandler


class TestCommandHistoryHandler(unittest.TestCase):
    """Test cases for CommandHistoryHandler class."""

    def test_class_can_instantiate(self) -> None:
        """Test that CommandHistoryHandler can be instantiated."""
        project_path = Path("/fake/path")
        handler = CommandHistoryHandler(project_path)

        self.assertIsNotNone(handler)
        self.assertEqual(handler.project_path, project_path)
        self.assertEqual(handler.history_dir, project_path / ".jd-history")

    @patch("pathlib.Path.touch")
    @patch("pathlib.Path.mkdir")
    @patch("jupyter_deploy.handlers.command_history_handler.datetime")
    def test_create_log_file_generates_timestamped_path(
        self, mock_datetime_module: Mock, mock_mkdir: Mock, mock_touch: Mock
    ) -> None:
        """Test that create_log_file generates correct timestamped path and creates file."""
        # Arrange
        project_path = Path("/fake/path")
        handler = CommandHistoryHandler(project_path)

        # Mock datetime.now(timezone.utc)
        mock_utc_datetime = Mock()
        mock_utc_datetime.strftime.return_value = "20260129-143022"
        mock_datetime_module.now.return_value = mock_utc_datetime

        # Act
        log_file = handler.create_log_file("config")

        # Assert
        expected_path = project_path / ".jd-history" / "config" / "20260129-143022.log"
        self.assertEqual(log_file, expected_path)
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_touch.assert_called_once_with(exist_ok=True)
        mock_utc_datetime.strftime.assert_called_once_with("%Y%m%d-%H%M%S")

    @patch("pathlib.Path.touch")
    @patch("pathlib.Path.mkdir")
    def test_create_log_file_ensures_directory_and_file_exist(self, mock_mkdir: Mock, mock_touch: Mock) -> None:
        """Test that create_log_file ensures command subdirectory and file exist."""
        # Arrange
        project_path = Path("/fake/path")
        handler = CommandHistoryHandler(project_path)

        # Act
        handler.create_log_file("up")

        # Assert
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_touch.assert_called_once_with(exist_ok=True)

    @patch("pathlib.Path.touch")
    @patch("pathlib.Path.mkdir")
    def test_create_log_file_works_with_different_commands(self, mock_mkdir: Mock, mock_touch: Mock) -> None:
        """Test that create_log_file works with different command names."""
        # Arrange
        project_path = Path("/fake/path")
        handler = CommandHistoryHandler(project_path)

        # Act
        config_log = handler.create_log_file("config")
        up_log = handler.create_log_file("up")
        down_log = handler.create_log_file("down")

        # Assert
        self.assertTrue(str(config_log).endswith(".log"))
        self.assertIn(".jd-history/config/", str(config_log))
        self.assertTrue(str(up_log).endswith(".log"))
        self.assertIn(".jd-history/up/", str(up_log))
        self.assertTrue(str(down_log).endswith(".log"))
        self.assertIn(".jd-history/down/", str(down_log))
        # Verify touch was called for each log file
        self.assertEqual(mock_touch.call_count, 3)
