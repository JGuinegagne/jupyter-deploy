# mypy: disable-error-code=method-assign

import unittest
from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import Mock, patch

from jupyter_deploy.engine.engine_down import DownAutoApproveRequiredError
from jupyter_deploy.engine.enum import EngineType
from jupyter_deploy.engine.outdefs import ListStrTemplateOutputDefinition
from jupyter_deploy.engine.supervised_execution import ExecutionError
from jupyter_deploy.engine.terraform.tf_down import TerraformDownHandler
from jupyter_deploy.engine.terraform.tf_enums import TerraformSequenceId
from jupyter_deploy.handlers.command_history_handler import LogCleanupError


class TestTerraformDownHandler(unittest.TestCase):
    def get_mock_outputs_handler_and_fns(self) -> tuple[Mock, dict[str, Mock]]:
        """Return the mock outputs handler."""
        mock_handler = Mock()
        mock_get_declared_output_def = Mock()
        mock_handler.get_declared_output_def = mock_get_declared_output_def

        mock_get_declared_output_def.return_value = ListStrTemplateOutputDefinition(
            output_name="persisting_resources", value=[]
        )
        return mock_handler, {"get_declared_output_def": mock_get_declared_output_def}

    def get_mock_manifest_and_fns(self) -> tuple[Mock, dict[str, Mock]]:
        """Return mock manifest with functions defined as mock."""
        mock_manifest = Mock()
        mock_get_engine = Mock()
        mock_get_engine.return_value = EngineType.TERRAFORM
        mock_manifest.get_engine = mock_get_engine
        return mock_manifest, {"get_engine": mock_get_engine}

    def test_init_sets_attributes(self) -> None:
        project_path = Path("/mock/project")
        mock_manifest, _ = self.get_mock_manifest_and_fns()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")
        handler = TerraformDownHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        self.assertEqual(handler.project_path, project_path)
        self.assertEqual(handler.project_manifest, mock_manifest)
        self.assertEqual(handler.engine, EngineType.TERRAFORM)

    @patch("jupyter_deploy.engine.terraform.tf_down.tf_supervised_executor_factory.create_terraform_executor")
    def test_destroy_success_no_persisting_resources(self, mock_create_executor: Mock) -> None:
        """Test successful terraform destroy without persisting resources."""
        project_path = Path("/mock/project")
        mock_manifest, _ = self.get_mock_manifest_and_fns()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")
        handler = TerraformDownHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        # Mock the executor
        mock_executor = Mock()
        mock_executor.execute.return_value = 0
        mock_create_executor.return_value = mock_executor

        handler.destroy()

        # Verify executor was called
        mock_executor.execute.assert_called_once()

    @patch("jupyter_deploy.engine.terraform.tf_down.tf_supervised_executor_factory.create_terraform_executor")
    def test_destroy_handles_error(self, mock_create_executor: Mock) -> None:
        """Test terraform destroy failure."""
        project_path = Path("/mock/project")
        mock_manifest, _ = self.get_mock_manifest_and_fns()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")
        handler = TerraformDownHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        # Mock the executor to return error
        mock_executor = Mock()
        mock_executor.execute.return_value = 1
        mock_create_executor.return_value = mock_executor

        with self.assertRaises(ExecutionError) as context:
            handler.destroy()

        self.assertEqual(context.exception.retcode, 1)
        self.assertEqual(context.exception.command, "down")

    @patch("jupyter_deploy.engine.terraform.tf_down.tf_supervised_executor_factory.create_terraform_executor")
    def test_destroy_propagates_exceptions(self, mock_create_executor: Mock) -> None:
        """Test that exceptions are properly propagated."""
        project_path = Path("/mock/project")
        mock_manifest, _ = self.get_mock_manifest_and_fns()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")
        handler = TerraformDownHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        # Mock the executor to raise an exception
        mock_executor = Mock()
        mock_executor.execute.side_effect = Exception("Command failed")
        mock_create_executor.return_value = mock_executor

        with self.assertRaises(Exception) as context:
            handler.destroy()

        self.assertEqual(str(context.exception), "Command failed")

    @patch("jupyter_deploy.engine.terraform.tf_down.tf_supervised_executor_factory.create_terraform_executor")
    def test_destroy_with_auto_approve(self, mock_create_executor: Mock) -> None:
        """Test that auto_approve flag is properly passed to terraform command."""
        project_path = Path("/mock/project")
        mock_manifest, _ = self.get_mock_manifest_and_fns()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")
        handler = TerraformDownHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        # Mock the executor
        mock_executor = Mock()
        mock_executor.execute.return_value = 0
        mock_create_executor.return_value = mock_executor

        handler.destroy(auto_approve=True)

        # Verify the command passed to executor includes -auto-approve
        mock_executor.execute.assert_called_once()
        cmd_args = mock_executor.execute.call_args[0][0]
        self.assertIn("-auto-approve", cmd_args)

    @patch("jupyter_deploy.engine.terraform.tf_down.cmd_utils")
    @patch("jupyter_deploy.engine.terraform.tf_down.rich_console")
    def test_destroy_with_persisting_resources_raises_error_without_yes_flag(
        self, mock_console: Mock, mock_cmd_utils: Mock
    ) -> None:
        """Test that without auto_approve flag, destroy raises AutoApproveRequiredError immediately."""
        # Setup
        project_path = Path("/mock/project")
        mock_manifest, _ = self.get_mock_manifest_and_fns()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")
        handler = TerraformDownHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        # Mock the get_persisting_resources method to return resources
        persisting_resources = [
            'aws_ebs_volume.additional_volumes["0"]',
            'aws_efs_file_system.additional_file_systems["0"]',
        ]
        handler.get_persisting_resources = Mock(return_value=persisting_resources)

        mock_console_instance = Mock()
        mock_console.Console.return_value = mock_console_instance

        # Act & Assert
        with self.assertRaises(DownAutoApproveRequiredError) as context:
            handler.destroy(auto_approve=False)

        # Verify the error has the persisting resources
        self.assertEqual(context.exception.persisting_resources, persisting_resources)

        # Verify dry-run was NOT called (fail fast)
        mock_cmd_utils.run_cmd_and_capture_output.assert_not_called()

    @patch("jupyter_deploy.engine.terraform.tf_down.tf_supervised_executor_factory.create_terraform_executor")
    @patch("jupyter_deploy.engine.terraform.tf_down.cmd_utils")
    @patch("jupyter_deploy.engine.terraform.tf_down.rich_console")
    def test_destroy_remove_persisting_resources_and_calls_destroy_happy_path(
        self, mock_console: Mock, mock_cmd_utils: Mock, mock_create_executor: Mock
    ) -> None:
        """Test that persisting resources are removed before destroy when auto_approve=True."""
        # Setup
        project_path = Path("/mock/project")
        mock_manifest, _ = self.get_mock_manifest_and_fns()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")
        handler = TerraformDownHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        # Mock the get_persisting_resources method to return resources
        persisting_resources = [
            'aws_ebs_volume.additional_volumes["0"]',
            'aws_efs_file_system.additional_file_systems["0"]',
        ]
        handler.get_persisting_resources = Mock(return_value=persisting_resources)

        mock_console_instance = Mock()
        mock_console.Console.return_value = mock_console_instance

        # Mock successful dry-run
        mock_cmd_utils.run_cmd_and_capture_output.return_value = "dry-run output"

        # Mock the executor for both rm and destroy
        mock_executor = Mock()
        mock_executor.execute.return_value = 0
        mock_create_executor.return_value = mock_executor

        # Act
        handler.destroy(auto_approve=True)

        # Assert
        # Check dry-run call
        mock_cmd_utils.run_cmd_and_capture_output.assert_called_once()
        dryrun_args = mock_cmd_utils.run_cmd_and_capture_output.call_args[0][0]
        self.assertIn("--dry-run", dryrun_args)

        # Check that executor was called twice (once for rm, once for destroy)
        self.assertEqual(2, mock_executor.execute.call_count)

        # Check actual state removal call
        rm_call_args = mock_executor.execute.call_args_list[0][0][0]
        self.assertIn("state", rm_call_args)
        for resource in persisting_resources:
            self.assertIn(resource, rm_call_args)

        # Check destroy call with auto-approve
        destroy_call_args = mock_executor.execute.call_args_list[1][0][0]
        self.assertIn("destroy", destroy_call_args)
        self.assertIn("-auto-approve", destroy_call_args)

    @patch("jupyter_deploy.engine.terraform.tf_down.cmd_utils")
    @patch("jupyter_deploy.engine.terraform.tf_down.rich_console")
    def test_destroy_raises_on_failed_dryrun(self, mock_console: Mock, mock_cmd_utils: Mock) -> None:
        # Setup
        project_path = Path("/mock/project")
        mock_manifest, _ = self.get_mock_manifest_and_fns()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")
        handler = TerraformDownHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        # Mock the get_persisting_resources method to return resources
        persisting_resources = [
            'aws_ebs_volume.additional_volumes["0"]',
            'aws_efs_file_system.additional_file_systems["0"]',
        ]
        handler.get_persisting_resources = Mock(return_value=persisting_resources)

        mock_console_instance = Mock()
        mock_console.Console.return_value = mock_console_instance

        # Mock failed dry-run
        error_msg = "Some terraform error"
        mock_cmd_utils.run_cmd_and_capture_output.side_effect = CalledProcessError(1, "cmd", stderr=error_msg.encode())

        # Act
        handler.destroy(auto_approve=True)

        # Assert
        mock_cmd_utils.run_cmd_and_capture_output.assert_called_once()

        # Verify we don't proceed with terraform state rm or destroy
        mock_cmd_utils.run_cmd_and_pipe_to_terminal.assert_not_called()

    @patch("jupyter_deploy.engine.terraform.tf_down.tf_supervised_executor_factory.create_terraform_executor")
    @patch("jupyter_deploy.engine.terraform.tf_down.cmd_utils")
    @patch("jupyter_deploy.engine.terraform.tf_down.rich_console")
    def test_destroy_raises_on_failed_remove_persisting_resources_without_destroying(
        self, mock_console: Mock, mock_cmd_utils: Mock, mock_create_executor: Mock
    ) -> None:
        """Test that destroy fails if removing persisting resources fails."""
        # Setup
        project_path = Path("/mock/project")
        mock_manifest, _ = self.get_mock_manifest_and_fns()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")
        handler = TerraformDownHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        # Mock the get_persisting_resources method to return resources
        persisting_resources = [
            'aws_ebs_volume.additional_volumes["0"]',
            'aws_efs_file_system.additional_file_systems["0"]',
        ]
        handler.get_persisting_resources = Mock(return_value=persisting_resources)

        mock_console_instance = Mock()
        mock_console.Console.return_value = mock_console_instance

        # Mock successful dry-run
        mock_cmd_utils.run_cmd_and_capture_output.return_value = "dry-run output"

        # Mock failed state removal
        mock_executor = Mock()
        mock_executor.execute.return_value = 1
        mock_create_executor.return_value = mock_executor

        # Act & Assert
        with self.assertRaises(ExecutionError) as context:
            handler.destroy(auto_approve=True)

        # Check dry-run call
        mock_cmd_utils.run_cmd_and_capture_output.assert_called_once()

        # Check that only one executor call was made (for rm, not destroy)
        self.assertEqual(1, mock_executor.execute.call_count)
        self.assertEqual(context.exception.retcode, 1)
        self.assertEqual(context.exception.command, "down")

    @patch("jupyter_deploy.engine.terraform.tf_down.tf_supervised_executor_factory.create_terraform_executor")
    @patch("jupyter_deploy.engine.terraform.tf_down.fs_utils")
    def test_passes_destroy_tfvars_file_when_available(self, mock_fs_utils: Mock, mock_create_executor: Mock) -> None:
        """Test that destroy.tfvars file is passed when available."""
        # Setup
        project_path = Path("/mock/project")
        mock_manifest, _ = self.get_mock_manifest_and_fns()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")
        handler = TerraformDownHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )
        engine_path = project_path / "engine"

        # Mock fs_utils to indicate that destroy.tfvars exists
        mock_fs_utils.file_exists.return_value = True

        # Mock successful command execution
        mock_executor = Mock()
        mock_executor.execute.return_value = 0
        mock_create_executor.return_value = mock_executor

        # Define expected tfvars file path (using tf_constants.TF_DESTROY_PRESET_FILENAME)
        destroy_tfvars_path = engine_path / "presets" / "destroy.tfvars"

        # Act
        handler.destroy(auto_approve=True)

        # Assert
        mock_fs_utils.file_exists.assert_called_once()
        mock_executor.execute.assert_called_once()

        # Check that the var-file option was included in the command
        cmd_args = mock_executor.execute.call_args[0][0]
        var_file_arg = f"-var-file={destroy_tfvars_path.absolute()}"
        self.assertIn(var_file_arg, cmd_args)

    @patch("jupyter_deploy.engine.terraform.tf_down.tf_supervised_executor_factory.create_terraform_executor")
    @patch("jupyter_deploy.engine.terraform.tf_down.fs_utils")
    def test_skips_passing_destroy_tfvars_file_when_unavailable(
        self, mock_fs_utils: Mock, mock_create_executor: Mock
    ) -> None:
        """Test that destroy.tfvars file is not passed when unavailable."""
        # Setup
        project_path = Path("/mock/project")
        mock_manifest, _ = self.get_mock_manifest_and_fns()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")
        handler = TerraformDownHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        # Mock fs_utils to indicate that destroy.tfvars does NOT exist
        mock_fs_utils.file_exists.return_value = False

        # Mock successful command execution
        mock_executor = Mock()
        mock_executor.execute.return_value = 0
        mock_create_executor.return_value = mock_executor

        # Act
        handler.destroy(auto_approve=True)

        # Assert
        mock_fs_utils.file_exists.assert_called_once()
        mock_executor.execute.assert_called_once()

        # Check that the var-file option was NOT included in the command
        cmd_args = mock_executor.execute.call_args[0][0]
        for arg in cmd_args:
            self.assertFalse(arg.startswith("-var-file="))

    @patch("jupyter_deploy.engine.terraform.tf_down.TerraformSupervisedExecutionCallback")
    @patch("jupyter_deploy.engine.terraform.tf_down.tf_supervised_executor_factory.create_terraform_executor")
    def test_destroy_with_terminal_handler_uses_supervised_callback(
        self, mock_create_executor: Mock, mock_callback_cls: Mock
    ) -> None:
        """Test that destroy with terminal_handler uses TerraformSupervisedExecutionCallback."""
        project_path = Path("/mock/project")
        mock_manifest, _ = self.get_mock_manifest_and_fns()
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
        handler = TerraformDownHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
            terminal_handler=mock_terminal_handler,
        )

        # Act
        handler.destroy()

        # Assert
        # Verify TerraformSupervisedExecutionCallback was created (once for destroy)
        mock_callback_cls.assert_called_once_with(
            terminal_handler=mock_terminal_handler,
            sequence_id=TerraformSequenceId.down_destroy,
        )

        # Verify executor was created with the supervised callback
        mock_create_executor.assert_called_once()
        self.assertEqual(mock_create_executor.call_args.kwargs["execution_callback"], mock_callback)

    @patch("jupyter_deploy.engine.terraform.tf_down.TerraformSupervisedExecutionCallback")
    @patch("jupyter_deploy.engine.terraform.tf_down.tf_supervised_executor_factory.create_terraform_executor")
    def test_destroy_with_terminal_handler_handles_error(
        self, mock_create_executor: Mock, mock_callback_cls: Mock
    ) -> None:
        """Test that destroy with terminal_handler properly raises ExecutionError on failure."""
        project_path = Path("/mock/project")
        mock_manifest, _ = self.get_mock_manifest_and_fns()
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
        handler = TerraformDownHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
            terminal_handler=mock_terminal_handler,
        )

        # Act & Assert
        with self.assertRaises(ExecutionError) as context:
            handler.destroy()

        self.assertEqual(context.exception.retcode, 1)
        self.assertEqual(context.exception.command, "down")

        # Verify TerraformSupervisedExecutionCallback was created
        mock_callback_cls.assert_called_once_with(
            terminal_handler=mock_terminal_handler,
            sequence_id=TerraformSequenceId.down_destroy,
        )

        # Verify executor was created and executed
        mock_create_executor.assert_called_once()
        mock_executor.execute.assert_called_once()

    @patch("jupyter_deploy.engine.terraform.tf_down.tf_supervised_executor_factory.create_terraform_executor")
    @patch("jupyter_deploy.engine.terraform.tf_outputs.TerraformOutputsHandler")
    def test_destroy_clears_old_logs_on_success(
        self, mock_outputs_handler_cls: Mock, mock_create_executor: Mock
    ) -> None:
        """Test that destroy calls clear_logs on successful execution."""
        project_path = Path("/mock/project")
        mock_manifest, _ = self.get_mock_manifest_and_fns()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")
        mock_history_handler.clear_logs.return_value = Mock()

        # Mock outputs handler
        mock_outputs_handler, _ = self.get_mock_outputs_handler_and_fns()
        mock_outputs_handler_cls.return_value = mock_outputs_handler

        # Mock executor - success
        mock_executor = Mock()
        mock_executor.execute.return_value = 0
        mock_create_executor.return_value = mock_executor

        handler = TerraformDownHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        # Act
        handler.destroy()

        # Assert - clear_logs should be called after successful execution
        mock_history_handler.clear_logs.assert_called_once_with("down")

    @patch("jupyter_deploy.engine.terraform.tf_down.tf_supervised_executor_factory.create_terraform_executor")
    @patch("jupyter_deploy.engine.terraform.tf_outputs.TerraformOutputsHandler")
    def test_destroy_does_not_clear_logs_on_failure(
        self, mock_outputs_handler_cls: Mock, mock_create_executor: Mock
    ) -> None:
        """Test that destroy does NOT call clear_logs when execution fails."""
        project_path = Path("/mock/project")
        mock_manifest, _ = self.get_mock_manifest_and_fns()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")
        mock_history_handler.clear_logs.return_value = Mock()

        # Mock outputs handler
        mock_outputs_handler, _ = self.get_mock_outputs_handler_and_fns()
        mock_outputs_handler_cls.return_value = mock_outputs_handler

        # Mock executor - failure
        mock_executor = Mock()
        mock_executor.execute.return_value = 1
        mock_create_executor.return_value = mock_executor

        handler = TerraformDownHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        # Act & Assert - should raise ExecutionError
        with self.assertRaises(ExecutionError):
            handler.destroy()

        # Assert - clear_logs should NOT be called on failure
        mock_history_handler.clear_logs.assert_not_called()

    @patch("jupyter_deploy.engine.terraform.tf_down.tf_supervised_executor_factory.create_terraform_executor")
    @patch("jupyter_deploy.engine.terraform.tf_outputs.TerraformOutputsHandler")
    def test_destroy_bubbles_up_clear_logs_exception(
        self, mock_outputs_handler_cls: Mock, mock_create_executor: Mock
    ) -> None:
        """Test that destroy bubbles up LogCleanupError from clear_logs."""
        project_path = Path("/mock/project")
        mock_manifest, _ = self.get_mock_manifest_and_fns()
        mock_history_handler = Mock()
        mock_history_handler.create_log_file.return_value = Path("/mock/log.log")
        mock_history_handler.clear_logs.side_effect = LogCleanupError("Failed to delete 2 log file(s)")

        # Mock outputs handler
        mock_outputs_handler, _ = self.get_mock_outputs_handler_and_fns()
        mock_outputs_handler_cls.return_value = mock_outputs_handler

        # Mock executor - success
        mock_executor = Mock()
        mock_executor.execute.return_value = 0
        mock_create_executor.return_value = mock_executor

        handler = TerraformDownHandler(
            project_path=project_path,
            project_manifest=mock_manifest,
            command_history_handler=mock_history_handler,
        )

        # Act & Assert - should raise LogCleanupError from clear_logs
        with self.assertRaises(LogCleanupError) as context:
            handler.destroy()

        self.assertEqual(str(context.exception), "Failed to delete 2 log file(s)")
        mock_history_handler.clear_logs.assert_called_once_with("down")
