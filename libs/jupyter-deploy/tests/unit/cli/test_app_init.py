import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from jupyter_deploy.cli.app import runner as app_runner
from jupyter_deploy.engine.enum import EngineType
from jupyter_deploy.exceptions import ProjectStoreNotFoundError

_INIT_HANDLER = "jupyter_deploy.cli.app.InitHandler"


class TestInitCommand(unittest.TestCase):
    def get_mock_project(self) -> Mock:
        mock_project = Mock()

        self.mock_may_export_to_project_path = Mock()
        self.mock_clear_project_path = Mock()
        self.mock_setup = Mock()

        self.mock_may_export_to_project_path.return_value = True

        mock_project.may_export_to_project_path = self.mock_may_export_to_project_path
        mock_project.clear_project_path = self.mock_clear_project_path
        mock_project.setup = self.mock_setup

        return mock_project

    @patch(_INIT_HANDLER)
    def test_init_command_no_args_default_to_terraform(self, mock_handler_cls: Mock) -> None:
        mock_handler_cls.return_value = self.get_mock_project()

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["init", "."])

        self.assertEqual(result.exit_code, 0, "init command should work")

        mock_handler_cls.assert_called_once_with(
            project_dir=Path("."),
            engine=EngineType.TERRAFORM,
            provider="aws",
            infrastructure="ec2",
            template="base",
        )

    @patch(_INIT_HANDLER)
    def test_init_command_passes_attributes_to_project(self, mock_handler_cls: Mock) -> None:
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

        self.assertEqual(result.exit_code, 0, "init command should work")

        mock_handler_cls.assert_called_once_with(
            project_dir=Path("custom-dir"),
            engine=EngineType.TERRAFORM,
            provider="aws",
            infrastructure="ec2",
            template="other-template",
        )

    @patch(_INIT_HANDLER)
    def test_init_command_handles_short_options(self, mock_handler_cls: Mock) -> None:
        mock_handler_cls.return_value = self.get_mock_project()

        runner = CliRunner()
        result = runner.invoke(
            app_runner.app,
            ["init", "-E", "terraform", "-P", "aws", "-I", "ec2", "-T", "a-template", "custom-dir"],
        )

        self.assertEqual(result.exit_code, 0, "init command should work")

        mock_handler_cls.assert_called_once_with(
            project_dir=Path("custom-dir"),
            engine=EngineType.TERRAFORM,
            provider="aws",
            infrastructure="ec2",
            template="a-template",
        )

    @patch(_INIT_HANDLER)
    def test_init_command_calls_project_methods(self, mock_handler_cls: Mock) -> None:
        mock_handler_cls.return_value = self.get_mock_project()

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["init", "."])

        self.assertEqual(result.exit_code, 0, "init command should work")
        self.mock_may_export_to_project_path.assert_called_once()
        self.mock_setup.assert_called_once()

    @patch(_INIT_HANDLER)
    def test_init_command_exits_on_project_conflict_without_overwrite(self, mock_handler_cls: Mock) -> None:
        mock_handler_cls.return_value = self.get_mock_project()
        self.mock_may_export_to_project_path.return_value = False

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["init", "."])

        self.assertEqual(result.exit_code, 0, "init command should work")
        self.mock_may_export_to_project_path.assert_called_once()
        self.mock_clear_project_path.assert_not_called()
        self.mock_setup.assert_not_called()

    @patch(_INIT_HANDLER)
    @patch("jupyter_deploy.cli.app.typer.confirm")
    def test_init_command_with_overwrite_and_user_confirms(self, mock_confirm: Mock, mock_handler_cls: Mock) -> None:
        mock_handler_cls.return_value = self.get_mock_project()
        self.mock_may_export_to_project_path.return_value = False
        mock_confirm.return_value = True

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["init", "--overwrite", "."])

        self.assertEqual(result.exit_code, 0, "init command should work")
        self.mock_may_export_to_project_path.assert_called_once()
        mock_confirm.assert_called_once()
        self.mock_setup.assert_called_once()

    @patch(_INIT_HANDLER)
    @patch("jupyter_deploy.cli.app.typer.confirm")
    def test_init_command_with_overwrite_and_user_declines(self, mock_confirm: Mock, mock_handler_cls: Mock) -> None:
        mock_handler_cls.return_value = self.get_mock_project()
        self.mock_may_export_to_project_path.return_value = False
        mock_confirm.return_value = False

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["init", "--overwrite", "."])

        self.assertEqual(result.exit_code, 0, "init command should work")
        self.mock_may_export_to_project_path.assert_called_once()
        mock_confirm.assert_called_once()
        self.mock_setup.assert_not_called()

    @patch(_INIT_HANDLER)
    @patch("jupyter_deploy.cli.app.typer.confirm")
    def test_init_command_with_overwrite_on_no_conflict(self, mock_confirm: Mock, mock_handler_cls: Mock) -> None:
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

        self.assertEqual(result.exit_code, 1, "init command should exit with error when no path")
        mock_subprocess_run.assert_called_once_with(["jupyter", "deploy", "init", "--help"])


class TestInitRestoreCommand(unittest.TestCase):
    @patch(_INIT_HANDLER)
    def test_restore_from_calls_handler(self, mock_handler_cls: Mock) -> None:
        mock_handler_cls.restore.return_value = Path("/tmp/restored").resolve()

        runner = CliRunner()
        result = runner.invoke(
            app_runner.app,
            ["init", "/tmp/restored", "--restore-project", "tpl-abc123", "--store-type", "s3-only"],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        mock_handler_cls.restore.assert_called_once()
        call_kwargs = mock_handler_cls.restore.call_args.kwargs
        self.assertEqual(call_kwargs["project_dir"], Path("/tmp/restored"))
        self.assertEqual(call_kwargs["project_id"], "tpl-abc123")
        self.assertIsNone(call_kwargs["store_id"])
        self.assertIn("restored", result.output)

    @patch(_INIT_HANDLER)
    def test_restore_from_with_store_id(self, mock_handler_cls: Mock) -> None:
        mock_handler_cls.restore.return_value = Path("/tmp/restored").resolve()

        runner = CliRunner()
        result = runner.invoke(
            app_runner.app,
            [
                "init",
                "/tmp/restored",
                "--restore-project",
                "tpl-abc123",
                "--store-type",
                "s3-only",
                "--store-id",
                "my-bucket",
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        call_kwargs = mock_handler_cls.restore.call_args.kwargs
        self.assertEqual(call_kwargs["store_id"], "my-bucket")

    def test_restore_without_path_exits_nonzero(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            app_runner.app,
            ["init", "--restore-project", "tpl-abc123", "--store-type", "s3-only"],
        )

        self.assertNotEqual(result.exit_code, 0)

    def test_restore_from_without_store_type_fails(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            app_runner.app,
            ["init", "/tmp/restored", "--restore-project", "tpl-abc123"],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--store-type is required with --restore-project", result.output)

    @patch(_INIT_HANDLER)
    def test_restore_from_store_not_found(self, mock_handler_cls: Mock) -> None:
        mock_handler_cls.restore.side_effect = ProjectStoreNotFoundError("No store found")

        runner = CliRunner()
        result = runner.invoke(
            app_runner.app,
            ["init", "/tmp/restored", "--restore-project", "tpl-abc123", "--store-type", "s3-only"],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("No store found", result.output)
