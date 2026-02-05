import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from jupyter_deploy.engine.enum import EngineType
from jupyter_deploy.engine.supervised_execution import ExecutionError
from jupyter_deploy.engine.terraform.tf_enums import TerraformSequenceId
from jupyter_deploy.engine.terraform.tf_up import TerraformUpHandler
from jupyter_deploy.handlers.command_history_handler import LogCleanupError


class TestTerraformUpHandler(unittest.TestCase):
    """Test cases for the TerraformUpHandler class."""

    def test_init_sets_attributes(self) -> None:
        project_path = Path("/mock/project")
        mock_manifest = Mock()
        mock_history_handler = Mock()
        handler = TerraformUpHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        self.assertEqual(handler.project_path, project_path)
        self.assertEqual(handler.engine, EngineType.TERRAFORM)

    def test_get_default_config_filename_returns_terraform_default(self) -> None:
        project_path = Path("/mock/project")
        mock_manifest = Mock()
        mock_history_handler = Mock()
        handler = TerraformUpHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        result = handler.get_default_config_filename()

        self.assertEqual(result, "jdout-tfplan")

    @patch("jupyter_deploy.engine.terraform.tf_up.tf_supervised_executor_factory.create_terraform_executor")
    def test_apply_success(self, mock_create_executor: Mock) -> None:
        """Test successful terraform apply."""
        path = Path("/mock/path")
        project_path = Path("/mock/project")
        mock_manifest = Mock()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")

        handler = TerraformUpHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        # Mock the executor
        mock_executor = Mock()
        mock_executor.execute.return_value = 0
        mock_create_executor.return_value = mock_executor

        handler.apply(path)

        # Verify executor was called
        mock_executor.execute.assert_called_once()

    @patch("jupyter_deploy.engine.terraform.tf_up.tf_supervised_executor_factory.create_terraform_executor")
    def test_apply_handles_error(self, mock_create_executor: Mock) -> None:
        """Test terraform apply failure."""
        path = Path("/mock/path")
        project_path = Path("/mock/project")
        mock_manifest = Mock()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")

        handler = TerraformUpHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        # Mock the executor to return error
        mock_executor = Mock()
        mock_executor.execute.return_value = 1
        mock_create_executor.return_value = mock_executor

        with self.assertRaises(ExecutionError) as context:
            handler.apply(path)

        self.assertEqual(context.exception.retcode, 1)
        self.assertEqual(context.exception.command, "up")

    @patch("jupyter_deploy.engine.terraform.tf_up.tf_supervised_executor_factory.create_terraform_executor")
    def test_apply_with_auto_approve(self, mock_create_executor: Mock) -> None:
        """Test that auto_approve flag is properly passed to terraform command."""
        path = Path("/mock/path")
        project_path = Path("/mock/project")
        mock_manifest = Mock()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")

        handler = TerraformUpHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        # Mock the executor
        mock_executor = Mock()
        mock_executor.execute.return_value = 0
        mock_create_executor.return_value = mock_executor

        handler.apply(path, auto_approve=True)

        # Verify the command passed to executor includes -auto-approve
        mock_executor.execute.assert_called_once()
        cmd_args = mock_executor.execute.call_args[0][0]
        self.assertIn("-auto-approve", cmd_args)

    @patch("jupyter_deploy.engine.terraform.tf_up.TerraformSupervisedExecutionCallback")
    @patch("jupyter_deploy.engine.terraform.tf_up.tf_supervised_executor_factory.create_terraform_executor")
    def test_apply_with_terminal_handler_uses_supervised_callback(
        self, mock_create_executor: Mock, mock_callback_cls: Mock
    ) -> None:
        """Test that apply with terminal_handler uses TerraformSupervisedExecutionCallback."""
        path = Path("/mock/path")
        project_path = Path("/mock/project")
        mock_manifest = Mock()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")

        # Mock executor - success
        mock_executor = Mock()
        mock_executor.execute.return_value = 0
        mock_create_executor.return_value = mock_executor

        # Mock callback
        mock_callback = Mock()
        mock_callback_cls.return_value = mock_callback

        # Create handler WITH terminal_handler
        mock_terminal_handler = Mock()
        handler = TerraformUpHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
            terminal_handler=mock_terminal_handler,
        )

        # Act
        handler.apply(path)

        # Assert
        # Verify TerraformSupervisedExecutionCallback was created
        mock_callback_cls.assert_called_once_with(
            terminal_handler=mock_terminal_handler,
            sequence_id=TerraformSequenceId.up_apply,
        )

        # Verify executor was created with the supervised callback
        mock_create_executor.assert_called_once()
        self.assertEqual(mock_create_executor.call_args.kwargs["execution_callback"], mock_callback)

    @patch("jupyter_deploy.engine.terraform.tf_up.TerraformSupervisedExecutionCallback")
    @patch("jupyter_deploy.engine.terraform.tf_up.tf_supervised_executor_factory.create_terraform_executor")
    def test_apply_with_terminal_handler_handles_error(
        self, mock_create_executor: Mock, mock_callback_cls: Mock
    ) -> None:
        """Test that apply with terminal_handler properly raises ExecutionError on failure."""
        path = Path("/mock/path")
        project_path = Path("/mock/project")
        mock_manifest = Mock()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")

        # Mock executor - failure
        mock_executor = Mock()
        mock_executor.execute.return_value = 1
        mock_create_executor.return_value = mock_executor

        # Mock callback
        mock_callback = Mock()
        mock_callback_cls.return_value = mock_callback

        # Create handler WITH terminal_handler
        mock_terminal_handler = Mock()
        handler = TerraformUpHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
            terminal_handler=mock_terminal_handler,
        )

        # Act & Assert
        with self.assertRaises(ExecutionError) as context:
            handler.apply(path)

        self.assertEqual(context.exception.retcode, 1)
        self.assertEqual(context.exception.command, "up")

        # Verify TerraformSupervisedExecutionCallback was created
        mock_callback_cls.assert_called_once_with(
            terminal_handler=mock_terminal_handler,
            sequence_id=TerraformSequenceId.up_apply,
        )

        # Verify executor was created and executed
        mock_create_executor.assert_called_once()
        mock_executor.execute.assert_called_once()

    @patch("jupyter_deploy.engine.terraform.tf_up.tf_supervised_executor_factory.create_terraform_executor")
    def test_apply_clears_old_logs_on_success(self, mock_create_executor: Mock) -> None:
        """Test that apply calls clear_logs on successful execution."""
        path = Path("/mock/path")
        project_path = Path("/mock/project")
        mock_manifest = Mock()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")
        mock_history_handler.clear_logs.return_value = Mock()

        # Mock executor - success
        mock_executor = Mock()
        mock_executor.execute.return_value = 0
        mock_create_executor.return_value = mock_executor

        handler = TerraformUpHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        # Act
        handler.apply(path)

        # Assert - clear_logs should be called after successful execution
        mock_history_handler.clear_logs.assert_called_once_with("up")

    @patch("jupyter_deploy.engine.terraform.tf_up.tf_supervised_executor_factory.create_terraform_executor")
    def test_apply_does_not_clear_logs_on_failure(self, mock_create_executor: Mock) -> None:
        """Test that apply does NOT call clear_logs when execution fails."""
        path = Path("/mock/path")
        project_path = Path("/mock/project")
        mock_manifest = Mock()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")
        mock_history_handler.clear_logs.return_value = Mock()

        # Mock executor - failure
        mock_executor = Mock()
        mock_executor.execute.return_value = 1
        mock_create_executor.return_value = mock_executor

        handler = TerraformUpHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        # Act & Assert - should raise ExecutionError
        with self.assertRaises(ExecutionError):
            handler.apply(path)

        # Assert - clear_logs should NOT be called on failure
        mock_history_handler.clear_logs.assert_not_called()

    @patch("jupyter_deploy.engine.terraform.tf_up.tf_supervised_executor_factory.create_terraform_executor")
    def test_apply_bubbles_up_clear_logs_exception(self, mock_create_executor: Mock) -> None:
        """Test that apply bubbles up LogCleanupError from clear_logs."""
        path = Path("/mock/path")
        project_path = Path("/mock/project")
        mock_manifest = Mock()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")
        mock_history_handler.clear_logs.side_effect = LogCleanupError("Failed to delete 2 log file(s)")

        # Mock executor - success
        mock_executor = Mock()
        mock_executor.execute.return_value = 0
        mock_create_executor.return_value = mock_executor

        handler = TerraformUpHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        # Act & Assert - should raise LogCleanupError from clear_logs
        with self.assertRaises(LogCleanupError) as context:
            handler.apply(path)

        self.assertEqual(str(context.exception), "Failed to delete 2 log file(s)")
        mock_history_handler.clear_logs.assert_called_once_with("up")
