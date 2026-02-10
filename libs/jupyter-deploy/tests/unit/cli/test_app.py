import sys
import unittest
from collections.abc import Generator
from contextlib import contextmanager
from unittest.mock import MagicMock, Mock, patch

from typer.testing import CliRunner

from jupyter_deploy.cli.app import JupyterDeployApp, JupyterDeployCliRunner, main
from jupyter_deploy.cli.app import runner as app_runner
from jupyter_deploy.engine.enum import EngineType
from jupyter_deploy.handlers.command_history_handler import LogCleanupError


class TestJupyterDeployCliRunner(unittest.TestCase):
    """Test cases for the JupyterDeployCliRunner class."""

    def test_init(self) -> None:
        """Test the initialization of the JupyterDeployCliRunner class."""
        # Create an instance of the class
        runner = JupyterDeployCliRunner()

        self.assertIsNotNone(runner.app, "attribute app should be set")

        # Check that sub-commands are added

        # At least server, host, users, teams, organization
        self.assertGreaterEqual(len(runner.app.registered_groups), 5)
        registered_group_names = [group.name for group in runner.app.registered_groups]
        self.assertIn("server", registered_group_names)
        self.assertIn("host", registered_group_names)
        self.assertIn("users", registered_group_names)
        self.assertIn("teams", registered_group_names)
        self.assertIn("organization", registered_group_names)

    @patch("jupyter_deploy.cli.app.typer.Typer")
    def test_run(self, mock_typer: MagicMock) -> None:
        """Test the run method."""
        # Create a mock app
        mock_app = MagicMock()
        mock_typer.return_value = mock_app

        runner = JupyterDeployCliRunner()
        runner.run()

        # Check that the app was called
        mock_app.assert_called_once()

    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["--help"])

        # Check that the command ran successfully
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.stdout.index("Jupyter-deploy") >= 0)
        self.assertTrue(result.stdout.index("server") >= 0)
        self.assertTrue(result.stdout.index("host") >= 0)
        self.assertTrue(result.stdout.index("users") >= 0)
        self.assertTrue(result.stdout.index("teams") >= 0)
        self.assertTrue(result.stdout.index("organization") >= 0)

    def test_no_arg_defaults_to_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(app_runner.app, [])

        # Check that the command ran successfully
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.stdout.index("Jupyter-deploy") >= 0)


class TestJupyterDeployApp(unittest.TestCase):
    """Test cases for the JupyterDeployApp class."""

    @patch("jupyter_deploy.cli.app.runner")
    def test_start(self, mock_runner: MagicMock) -> None:
        """Test the start method."""
        app = JupyterDeployApp()

        # Test with normal arguments
        with patch.object(sys, "argv", ["jupyter", "deploy", "--help"]):
            app.start()
            mock_runner.run.assert_called_once()
            mock_runner.reset_mock()

        # Test with no arguments
        with patch.object(sys, "argv", ["jupyter", "deploy"]):
            app.start()
            mock_runner.run.assert_called_once()


class TestMain(unittest.TestCase):
    """Test cases for the main function."""

    @patch("jupyter_deploy.cli.app.runner")
    @patch("jupyter_deploy.cli.app.JupyterDeployApp.launch_instance")
    def test_main_as_jupyter_deploy(self, mock_launch_instance: MagicMock, mock_runner: MagicMock) -> None:
        """Test the main function when called as 'jupyter deploy'."""
        with patch.object(sys, "argv", ["jupyter", "deploy"]):
            main()
            mock_launch_instance.assert_called_once()
            mock_runner.run.assert_not_called()

    @patch("jupyter_deploy.cli.app.runner")
    @patch("jupyter_deploy.cli.app.JupyterDeployApp.launch_instance")
    def test_main_as_jupyter_deploy_command(self, mock_launch_instance: MagicMock, mock_runner: MagicMock) -> None:
        """Test the main function when called as 'jupyter-deploy'."""
        with patch.object(sys, "argv", ["jupyter-deploy"]):
            main()
            mock_launch_instance.assert_not_called()
            mock_runner.run.assert_called_once()


class TestInitCommand(unittest.TestCase):
    """Test cases for the init command."""

    def get_mock_project(self) -> Mock:
        """Return a mock project."""
        mock_project = Mock()

        self.mock_may_export_to_project_path = Mock()
        self.mock_clear_project_path = Mock()
        self.mock_setup = Mock()

        self.mock_may_export_to_project_path.return_value = True

        mock_project.may_export_to_project_path = self.mock_may_export_to_project_path
        mock_project.clear_project_path = self.mock_clear_project_path
        mock_project.setup = self.mock_setup

        return mock_project

    @patch("jupyter_deploy.cli.app.InitHandler")
    def test_init_command_no_args_default_to_terraform(self, mock_handler_cls: Mock) -> None:
        """Test that the init command picks up defaults."""
        mock_handler_cls.return_value = self.get_mock_project()

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["init", "."])

        # Check that the command ran successfully
        self.assertEqual(result.exit_code, 0, "init command should work")

        mock_handler_cls.assert_called_once_with(
            project_dir=".",
            engine=EngineType.TERRAFORM,
            provider="aws",
            infrastructure="ec2",
            template="base",
        )

    @patch("jupyter_deploy.cli.app.InitHandler")
    def test_init_command_passes_attributes_to_project(self, mock_handler_cls: Mock) -> None:
        """Test that the init command handles optional attributes."""
        mock_handler_cls.return_value = self.get_mock_project()

        runner = CliRunner()
        result = runner.invoke(
            app_runner.app,
            [
                "init",
                "--engine",
                "terraform",
                "--provider",
                "aws",
                "--infrastructure",
                "ec2",
                "--template",
                "other-template",
                "custom-dir",
            ],
        )

        # Check that the command ran successfully
        self.assertEqual(result.exit_code, 0, "init command should work")

        mock_handler_cls.assert_called_once_with(
            project_dir="custom-dir",
            engine=EngineType.TERRAFORM,
            provider="aws",
            infrastructure="ec2",
            template="other-template",
        )

    @patch("jupyter_deploy.cli.app.InitHandler")
    def test_init_command_handles_short_options(self, mock_handler_cls: Mock) -> None:
        """Test that the init command handles short names of optional attributes."""
        mock_handler_cls.return_value = self.get_mock_project()

        runner = CliRunner()
        result = runner.invoke(
            app_runner.app,
            ["init", "-E", "terraform", "-P", "aws", "-I", "ec2", "-T", "a-template", "custom-dir"],
        )

        # Check that the command ran successfully
        self.assertEqual(result.exit_code, 0, "init command should work")

        mock_handler_cls.assert_called_once_with(
            project_dir="custom-dir",
            engine=EngineType.TERRAFORM,
            provider="aws",
            infrastructure="ec2",
            template="a-template",
        )

    @patch("jupyter_deploy.cli.app.InitHandler")
    def test_init_command_calls_project_methods(self, mock_handler_cls: Mock) -> None:
        """Test that the init commands correctly calls project.may_export() and .setup()."""
        mock_handler_cls.return_value = self.get_mock_project()

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["init", "."])

        self.assertEqual(result.exit_code, 0, "init command should work")
        self.mock_may_export_to_project_path.assert_called_once()
        self.mock_setup.assert_called_once()

    @patch("jupyter_deploy.cli.app.InitHandler")
    def test_init_command_exits_on_project_conflict_without_overwrite(self, mock_handler_cls: Mock) -> None:
        """Test that the init command exits on existing project conflict when --overwrite is False."""
        mock_handler_cls.return_value = self.get_mock_project()
        self.mock_may_export_to_project_path.return_value = False

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["init", "."])

        self.assertEqual(result.exit_code, 0, "init command should work")
        self.mock_may_export_to_project_path.assert_called_once()
        self.mock_clear_project_path.assert_not_called()
        self.mock_setup.assert_not_called()

    @patch("jupyter_deploy.cli.app.InitHandler")
    @patch("jupyter_deploy.cli.app.typer.confirm")
    def test_init_command_with_overwrite_and_user_confirms(self, mock_confirm: Mock, mock_handler_cls: Mock) -> None:
        """Test that the init command with --overwrite prompts the user and proceeds when confirmed."""
        mock_handler_cls.return_value = self.get_mock_project()
        self.mock_may_export_to_project_path.return_value = False
        mock_confirm.return_value = True

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["init", "--overwrite", "."])

        self.assertEqual(result.exit_code, 0, "init command should work")
        self.mock_may_export_to_project_path.assert_called_once()
        mock_confirm.assert_called_once()
        self.mock_setup.assert_called_once()

    @patch("jupyter_deploy.cli.app.InitHandler")
    @patch("jupyter_deploy.cli.app.typer.confirm")
    def test_init_command_with_overwrite_and_user_declines(self, mock_confirm: Mock, mock_handler_cls: Mock) -> None:
        """Test that the init command with --overwrite prompts the user and aborts when declined."""
        mock_handler_cls.return_value = self.get_mock_project()
        self.mock_may_export_to_project_path.return_value = False
        mock_confirm.return_value = False

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["init", "--overwrite", "."])

        self.assertEqual(result.exit_code, 0, "init command should work")
        self.mock_may_export_to_project_path.assert_called_once()
        mock_confirm.assert_called_once()
        self.mock_setup.assert_not_called()

    @patch("jupyter_deploy.cli.app.InitHandler")
    @patch("jupyter_deploy.cli.app.typer.confirm")
    def test_init_command_with_overwrite_on_no_conflict(self, mock_confirm: Mock, mock_handler_cls: Mock) -> None:
        """Test that the init command with --overwrite proceeds without confirmation if no project conflict."""
        mock_handler_cls.return_value = self.get_mock_project()
        self.mock_may_export_to_project_path.return_value = True

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["init", "--overwrite", "."])

        self.assertEqual(result.exit_code, 0, "init command should work")
        self.mock_may_export_to_project_path.assert_called_once()
        mock_confirm.assert_not_called()
        self.mock_setup.assert_called_once()

    @patch("subprocess.run")
    def test_init_command_calls_help_when_no_path(self, mock_subprocess_run: Mock) -> None:
        mock_subprocess_run.return_value = Mock(returncode=0)

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["init"])

        self.assertEqual(result.exit_code, 0, "init command should succeed without path")
        mock_subprocess_run.assert_called_once_with(["jupyter", "deploy", "init", "--help"])


class TestUpCommand(unittest.TestCase):
    def get_mock_up_handler(self, config_file_exists: bool = False) -> tuple[Mock, dict[str, Mock]]:
        mock_up_handler = Mock()
        mock_get_config_file_path = Mock()
        mock_apply = Mock()
        mock_get_default_filename = Mock()

        mock_up_handler.get_config_file_path = mock_get_config_file_path
        mock_up_handler.apply = mock_apply
        mock_up_handler.get_default_config_filename = mock_get_default_filename

        mock_get_default_filename.return_value = "jdout-tfplan"
        mock_apply.return_value = None

        # If config file doesn't exist, raise FileNotFoundError
        if not config_file_exists:
            mock_get_config_file_path.side_effect = FileNotFoundError("Config file not found")
        else:
            mock_get_config_file_path.return_value = "/path/to/config"

        return mock_up_handler, {
            "get_config_file_path": mock_get_config_file_path,
            "apply": mock_apply,
            "get_default_filename": mock_get_default_filename,
        }

    @contextmanager
    def mock_project_dir(*_args: object, **_kwargs: object) -> Generator[None]:
        yield None

    @patch("jupyter_deploy.cli.app.UpHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_up_command_checks_plan_file_exists(
        self, mock_project_ctx_manager: Mock, mock_up_handler_cls: Mock
    ) -> None:
        mock_project_ctx_manager.side_effect = TestUpCommand.mock_project_dir

        mock_up_handler_instance, mock_up_fns = self.get_mock_up_handler()
        mock_up_handler_cls.return_value = mock_up_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["up"])

        # Should exit with code 1 when config file doesn't exist
        self.assertEqual(result.exit_code, 1)
        mock_project_ctx_manager.assert_called_once_with(None)
        mock_up_fns["get_config_file_path"].assert_called_once_with(None)

    @patch("jupyter_deploy.cli.app.UpHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_up_command_with_custom_path(self, mock_project_ctx_manager: Mock, mock_up_handler_cls: Mock) -> None:
        mock_project_ctx_manager.side_effect = TestUpCommand.mock_project_dir

        mock_up_handler_instance, mock_up_fns = self.get_mock_up_handler()
        mock_up_handler_cls.return_value = mock_up_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["up", "--path", "/custom/path"])

        # Should exit with code 1 when config file doesn't exist
        self.assertEqual(result.exit_code, 1)
        mock_project_ctx_manager.assert_called_once_with("/custom/path")

    @patch("jupyter_deploy.cli.app.UpHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_up_command_with_custom_config_file(
        self, mock_project_ctx_manager: Mock, mock_up_handler_cls: Mock
    ) -> None:
        mock_project_ctx_manager.side_effect = TestUpCommand.mock_project_dir

        mock_up_handler_instance, mock_up_fns = self.get_mock_up_handler()
        mock_up_handler_cls.return_value = mock_up_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["up", "--config-filename", "custom-plan"])

        # Should exit with code 1 when config file doesn't exist
        self.assertEqual(result.exit_code, 1)
        mock_project_ctx_manager.assert_called_once_with(None)
        mock_up_fns["get_config_file_path"].assert_called_once_with("custom-plan")

    @patch("jupyter_deploy.cli.app.UpHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_up_command_runs_apply_when_config_exists(
        self, mock_project_ctx_manager: Mock, mock_up_handler_cls: Mock
    ) -> None:
        mock_project_ctx_manager.side_effect = TestUpCommand.mock_project_dir

        mock_up_handler_instance, mock_up_fns = self.get_mock_up_handler(config_file_exists=True)
        mock_up_handler_cls.return_value = mock_up_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["up"])

        self.assertEqual(result.exit_code, 0)
        mock_project_ctx_manager.assert_called_once_with(None)
        mock_up_fns["get_config_file_path"].assert_called_once_with(None)
        mock_up_fns["apply"].assert_called_once_with("/path/to/config", False)

    @patch("jupyter_deploy.cli.app.UpHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_up_command_with_answer_yes_option(self, mock_project_ctx_manager: Mock, mock_up_handler_cls: Mock) -> None:
        mock_project_ctx_manager.side_effect = TestUpCommand.mock_project_dir

        mock_up_handler_instance, mock_up_fns = self.get_mock_up_handler(config_file_exists=True)
        mock_up_handler_cls.return_value = mock_up_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["up", "--answer-yes"])

        self.assertEqual(result.exit_code, 0)
        mock_up_fns["apply"].assert_called_once_with("/path/to/config", True)

    @patch("jupyter_deploy.cli.app.UpHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_up_command_with_all_args(self, mock_project_ctx_manager: Mock, mock_up_handler_cls: Mock) -> None:
        mock_project_ctx_manager.side_effect = TestUpCommand.mock_project_dir

        mock_up_handler_instance, mock_up_fns = self.get_mock_up_handler(config_file_exists=True)
        mock_up_handler_cls.return_value = mock_up_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["up", "--path", "/custom/path", "--answer-yes"])

        self.assertEqual(result.exit_code, 0)
        mock_project_ctx_manager.assert_called_once_with("/custom/path")
        mock_up_fns["get_config_file_path"].assert_called_once_with(None)
        mock_up_fns["apply"].assert_called_once_with("/path/to/config", True)

    @patch("jupyter_deploy.cli.app.UpHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_up_command_with_verbose_uses_no_terminal_handler(
        self, mock_project_ctx_manager: Mock, mock_up_handler_cls: Mock
    ) -> None:
        """Test that up with --verbose passes None as terminal_handler."""
        mock_project_ctx_manager.side_effect = TestUpCommand.mock_project_dir

        mock_up_handler_instance, mock_up_fns = self.get_mock_up_handler(config_file_exists=True)
        mock_up_handler_cls.return_value = mock_up_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["up", "--verbose"])

        self.assertEqual(result.exit_code, 0)
        # terminal_handler should be None when verbose is True
        call_kwargs = mock_up_handler_cls.call_args.kwargs
        self.assertIsNone(call_kwargs["terminal_handler"])

    @patch("jupyter_deploy.cli.app.UpHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_up_warns_but_succeeds_if_log_cleanup_fails(
        self, mock_project_ctx_manager: Mock, mock_up_handler_cls: Mock
    ) -> None:
        """Test that up shows warning but succeeds when log cleanup fails."""
        mock_project_ctx_manager.side_effect = TestUpCommand.mock_project_dir

        mock_up_handler_instance, mock_up_fns = self.get_mock_up_handler(config_file_exists=True)
        mock_up_handler_cls.return_value = mock_up_handler_instance
        mock_up_fns["apply"].side_effect = LogCleanupError("Failed to delete 2 log file(s)")

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["up"])

        # Verify - should succeed with warning
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Failed to delete 2 log file(s)", result.stdout)
        mock_up_fns["apply"].assert_called_once()


class TestDownCommand(unittest.TestCase):
    def get_mock_down_handler(self) -> tuple[Mock, dict[str, Mock]]:
        mock_down_handler = Mock()
        mock_destroy = Mock()
        mock_get_persisting_resources = Mock(return_value=[])

        mock_down_handler.destroy = mock_destroy
        mock_down_handler.get_persisting_resources = mock_get_persisting_resources

        return mock_down_handler, {"destroy": mock_destroy}

    @contextmanager
    def mock_project_dir(*_args: object, **_kwargs: object) -> Generator[None]:
        yield None

    @patch("jupyter_deploy.cli.app.DownHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_down_command_runs_destroy(self, mock_project_ctx_manager: Mock, mock_down_handler_cls: Mock) -> None:
        mock_project_ctx_manager.side_effect = TestDownCommand.mock_project_dir

        mock_down_handler_instance, mock_down_fns = self.get_mock_down_handler()
        mock_down_handler_cls.return_value = mock_down_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["down"])

        self.assertEqual(result.exit_code, 0)
        mock_project_ctx_manager.assert_called_once_with(None)
        mock_down_fns["destroy"].assert_called_once()

    @patch("jupyter_deploy.cli.app.DownHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_down_command_with_custom_path(self, mock_project_ctx_manager: Mock, mock_down_handler_cls: Mock) -> None:
        mock_project_ctx_manager.side_effect = TestDownCommand.mock_project_dir

        mock_down_handler_instance, mock_down_fns = self.get_mock_down_handler()
        mock_down_handler_cls.return_value = mock_down_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["down", "--path", "/custom/path"])

        self.assertEqual(result.exit_code, 0)
        mock_project_ctx_manager.assert_called_once_with("/custom/path")
        mock_down_fns["destroy"].assert_called_once()

    @patch("jupyter_deploy.cli.app.DownHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_down_command_with_answer_yes_option(
        self, mock_project_ctx_manager: Mock, mock_down_handler_cls: Mock
    ) -> None:
        mock_project_ctx_manager.side_effect = TestDownCommand.mock_project_dir

        mock_down_handler_instance, mock_down_fns = self.get_mock_down_handler()
        mock_down_handler_cls.return_value = mock_down_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["down", "--answer-yes"])

        self.assertEqual(result.exit_code, 0)
        mock_project_ctx_manager.assert_called_once_with(None)
        mock_down_fns["destroy"].assert_called_once_with(True)

    @patch("jupyter_deploy.cli.app.DownHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_down_command_with_verbose_uses_no_terminal_handler(
        self, mock_project_ctx_manager: Mock, mock_down_handler_cls: Mock
    ) -> None:
        """Test that down with --verbose passes None as terminal_handler."""
        mock_project_ctx_manager.side_effect = TestDownCommand.mock_project_dir

        mock_down_handler_instance, _ = self.get_mock_down_handler()
        mock_down_handler_cls.return_value = mock_down_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["down", "--verbose"])

        self.assertEqual(result.exit_code, 0)
        # terminal_handler should be None when verbose is True
        call_kwargs = mock_down_handler_cls.call_args.kwargs
        self.assertIsNone(call_kwargs["terminal_handler"])

    @patch("jupyter_deploy.cli.app.DownHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_down_warns_but_succeeds_if_log_cleanup_fails(
        self, mock_project_ctx_manager: Mock, mock_down_handler_cls: Mock
    ) -> None:
        """Test that down shows warning but succeeds when log cleanup fails."""
        mock_project_ctx_manager.side_effect = TestDownCommand.mock_project_dir

        mock_down_handler_instance, mock_down_fns = self.get_mock_down_handler()
        mock_down_handler_cls.return_value = mock_down_handler_instance
        mock_down_fns["destroy"].side_effect = LogCleanupError("Failed to delete 2 log file(s)")

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["down"])

        # Verify - should succeed with warning
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Failed to delete 2 log file(s)", result.stdout)
        mock_down_fns["destroy"].assert_called_once()
