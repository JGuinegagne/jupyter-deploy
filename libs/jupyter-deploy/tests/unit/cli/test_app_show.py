import unittest
from collections.abc import Generator
from contextlib import contextmanager
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from jupyter_deploy.cli.app import runner as app_runner


class TestShowCommand(unittest.TestCase):
    """Test cases for the show command."""

    @contextmanager
    def mock_project_dir(*_args: object, **_kwargs: object) -> Generator[None]:
        yield None

    def get_mock_show_handler(self) -> tuple[Mock, dict[str, Mock]]:
        mock_show_handler = Mock()
        mock_show_project_info = Mock()
        mock_show_single_variable = Mock()
        mock_show_single_output = Mock()
        mock_list_variable_names = Mock()
        mock_list_output_names = Mock()
        mock_show_template_name = Mock()
        mock_show_template_version = Mock()
        mock_show_template_engine = Mock()

        mock_show_handler.show_project_info = mock_show_project_info
        mock_show_handler.show_single_variable = mock_show_single_variable
        mock_show_handler.show_single_output = mock_show_single_output
        mock_show_handler.list_variable_names = mock_list_variable_names
        mock_show_handler.list_output_names = mock_list_output_names
        mock_show_handler.show_template_name = mock_show_template_name
        mock_show_handler.show_template_version = mock_show_template_version
        mock_show_handler.show_template_engine = mock_show_template_engine

        return mock_show_handler, {
            "show_project_info": mock_show_project_info,
            "show_single_variable": mock_show_single_variable,
            "show_single_output": mock_show_single_output,
            "list_variable_names": mock_list_variable_names,
            "list_output_names": mock_list_output_names,
            "show_template_name": mock_show_template_name,
            "show_template_version": mock_show_template_version,
            "show_template_engine": mock_show_template_engine,
        }

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_default_flags(self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock) -> None:
        """Test that show command with no flags shows all sections."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show"])

        self.assertEqual(result.exit_code, 0)
        mock_project_ctx_manager.assert_called_once_with(None)
        mock_show_fns["show_project_info"].assert_called_once_with(
            show_info=True, show_outputs=True, show_variables=True
        )

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_info_flag(self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock) -> None:
        """Test that show command with --info flag shows only info section."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--info"])

        self.assertEqual(result.exit_code, 0)
        mock_project_ctx_manager.assert_called_once_with(None)
        mock_show_fns["show_project_info"].assert_called_once_with(
            show_info=True, show_outputs=False, show_variables=False
        )

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_outputs_flag(self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock) -> None:
        """Test that show command with --outputs flag shows only outputs section."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--outputs"])

        self.assertEqual(result.exit_code, 0)
        mock_project_ctx_manager.assert_called_once_with(None)
        mock_show_fns["show_project_info"].assert_called_once_with(
            show_info=False, show_outputs=True, show_variables=False
        )

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_variables_flag(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that show command with --variables flag shows only variables section."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--variables"])

        self.assertEqual(result.exit_code, 0)
        mock_project_ctx_manager.assert_called_once_with(None)
        mock_show_fns["show_project_info"].assert_called_once_with(
            show_info=False, show_outputs=False, show_variables=True
        )

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_multiple_flags(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that show command with multiple flags shows only selected sections."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--info", "--outputs"])

        self.assertEqual(result.exit_code, 0)
        mock_project_ctx_manager.assert_called_once_with(None)
        mock_show_fns["show_project_info"].assert_called_once_with(
            show_info=True, show_outputs=True, show_variables=False
        )

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_custom_path(self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock) -> None:
        """Test show command with custom project path."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--path", "/custom/path"])

        self.assertEqual(result.exit_code, 0)
        mock_project_ctx_manager.assert_called_once_with("/custom/path")
        mock_show_fns["show_project_info"].assert_called_once_with(
            show_info=True, show_outputs=True, show_variables=True
        )

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_variable_flag(self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock) -> None:
        """Test show command with --variable flag shows single variable value."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--variable", "instance_type"])

        self.assertEqual(result.exit_code, 0)
        mock_project_ctx_manager.assert_called_once_with(None)
        mock_show_fns["show_single_variable"].assert_called_once_with(
            "instance_type", show_description=False, plain_text=False
        )
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_variable_and_description_flags(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test show command with --variable and --description flags."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--variable", "instance_type", "--description"])

        self.assertEqual(result.exit_code, 0)
        mock_project_ctx_manager.assert_called_once_with(None)
        mock_show_fns["show_single_variable"].assert_called_once_with(
            "instance_type", show_description=True, plain_text=False
        )
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_variable_and_text_flags(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test show command with --variable and --text flags."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--variable", "instance_type", "--text"])

        self.assertEqual(result.exit_code, 0)
        mock_project_ctx_manager.assert_called_once_with(None)
        mock_show_fns["show_single_variable"].assert_called_once_with(
            "instance_type", show_description=False, plain_text=True
        )
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_variable_description_and_text_flags(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test show command with --variable, --description, and --text flags."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "-v", "instance_type", "-d", "--text"])

        self.assertEqual(result.exit_code, 0)
        mock_project_ctx_manager.assert_called_once_with(None)
        mock_show_fns["show_single_variable"].assert_called_once_with(
            "instance_type", show_description=True, plain_text=True
        )
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_output_flag(self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock) -> None:
        """Test show command with --output flag shows single output value."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--output", "jupyter_url"])

        self.assertEqual(result.exit_code, 0)
        mock_project_ctx_manager.assert_called_once_with(None)
        mock_show_fns["show_single_output"].assert_called_once_with(
            "jupyter_url", show_description=False, plain_text=False
        )
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_output_and_description_flags(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test show command with --output and --description flags."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--output", "jupyter_url", "--description"])

        self.assertEqual(result.exit_code, 0)
        mock_project_ctx_manager.assert_called_once_with(None)
        mock_show_fns["show_single_output"].assert_called_once_with(
            "jupyter_url", show_description=True, plain_text=False
        )
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_output_and_text_flags(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test show command with --output and --text flags."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "-o", "jupyter_url", "--text"])

        self.assertEqual(result.exit_code, 0)
        mock_project_ctx_manager.assert_called_once_with(None)
        mock_show_fns["show_single_output"].assert_called_once_with(
            "jupyter_url", show_description=False, plain_text=True
        )
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_output_description_and_text_flags(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test show command with --output, --description, and --text flags."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "-o", "jupyter_url", "-d", "--text"])

        self.assertEqual(result.exit_code, 0)
        mock_project_ctx_manager.assert_called_once_with(None)
        mock_show_fns["show_single_output"].assert_called_once_with(
            "jupyter_url", show_description=True, plain_text=True
        )
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_both_variable_and_output_raises_error(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that using both --variable and --output raises an error."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--variable", "instance_type", "--output", "jupyter_url"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("Cannot use multiple query flags", result.output)
        mock_show_fns["show_single_variable"].assert_not_called()
        mock_show_fns["show_single_output"].assert_not_called()
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_description_without_variable_or_output_raises_error(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that using --description without --variable or --output raises an error."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--description"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("--description can only be used with --variable or --output", result.output)
        mock_show_fns["show_single_variable"].assert_not_called()
        mock_show_fns["show_single_output"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_list_without_variables_or_outputs_raises_error(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that using --list without --variables or --outputs raises an error."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--list"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("--list can only be used with --variables or --outputs", result.output)
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_list_and_info_raises_error(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that using --list with --info (without --variables or --outputs) raises an error."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--list", "--info"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("--list can only be used with --variables or --outputs", result.output)
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_variables_and_list_flags(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test show command with --variables --list flags."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--variables", "--list"])

        self.assertEqual(result.exit_code, 0)
        mock_show_fns["list_variable_names"].assert_called_once_with(plain_text=False)
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_variables_list_and_text_flags(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test show command with --variables --list --text flags."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--variables", "--list", "--text"])

        self.assertEqual(result.exit_code, 0)
        mock_show_fns["list_variable_names"].assert_called_once_with(plain_text=True)
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_outputs_and_list_flags(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test show command with --outputs --list flags."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--outputs", "--list"])

        self.assertEqual(result.exit_code, 0)
        mock_show_fns["list_output_names"].assert_called_once_with(plain_text=False)
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_outputs_list_and_text_flags(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test show command with --outputs --list --text flags."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--outputs", "--list", "--text"])

        self.assertEqual(result.exit_code, 0)
        mock_show_fns["list_output_names"].assert_called_once_with(plain_text=True)
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_template_name_flag(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test show command with --template-name flag."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--template-name"])

        self.assertEqual(result.exit_code, 0)
        mock_show_fns["show_template_name"].assert_called_once_with(plain_text=False)
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_template_name_and_text_flags(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test show command with --template-name and --text flags."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--template-name", "--text"])

        self.assertEqual(result.exit_code, 0)
        mock_show_fns["show_template_name"].assert_called_once_with(plain_text=True)
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_template_version_flag(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test show command with --template-version flag."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--template-version"])

        self.assertEqual(result.exit_code, 0)
        mock_show_fns["show_template_version"].assert_called_once_with(plain_text=False)
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_template_version_and_text_flags(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test show command with --template-version and --text flags."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--template-version", "--text"])

        self.assertEqual(result.exit_code, 0)
        mock_show_fns["show_template_version"].assert_called_once_with(plain_text=True)
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_template_engine_flag(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test show command with --template-engine flag."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--template-engine"])

        self.assertEqual(result.exit_code, 0)
        mock_show_fns["show_template_engine"].assert_called_once_with(plain_text=False)
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_template_engine_and_text_flags(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test show command with --template-engine and --text flags."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--template-engine", "--text"])

        self.assertEqual(result.exit_code, 0)
        mock_show_fns["show_template_engine"].assert_called_once_with(plain_text=True)
        mock_show_fns["show_project_info"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_template_name_and_variable_raises_error(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that using --template-name with --variable raises an error."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--template-name", "--variable", "test_var"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("Cannot use multiple query flags", result.output)
        mock_show_fns["show_template_name"].assert_not_called()
        mock_show_fns["show_single_variable"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_template_version_and_output_raises_error(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that using --template-version with --output raises an error."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--template-version", "--output", "test_out"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("Cannot use multiple query flags", result.output)
        mock_show_fns["show_template_version"].assert_not_called()
        mock_show_fns["show_single_output"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_multiple_template_flags_raises_error(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that using multiple template flags together raises an error."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--template-name", "--template-version"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("Cannot use multiple query flags", result.output)
        mock_show_fns["show_template_name"].assert_not_called()
        mock_show_fns["show_template_version"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_outputs_and_template_name_raises_error(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that using --outputs with --template-name raises an error."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--outputs", "--template-name"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("Cannot use display mode flags", result.output)
        mock_show_fns["show_project_info"].assert_not_called()
        mock_show_fns["show_template_name"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_info_and_variable_raises_error(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that using --info with --variable raises an error."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--info", "--variable", "test_var"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("Cannot use display mode flags", result.output)
        mock_show_fns["show_project_info"].assert_not_called()
        mock_show_fns["show_single_variable"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_variables_and_output_raises_error(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that using --variables with --output raises an error."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--variables", "--output", "test_out"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("Cannot use display mode flags", result.output)
        mock_show_fns["show_project_info"].assert_not_called()
        mock_show_fns["show_single_output"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_info_and_template_version_raises_error(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that using --info with --template-version raises an error."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--info", "--template-version"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("Cannot use display mode flags", result.output)
        mock_show_fns["show_project_info"].assert_not_called()
        mock_show_fns["show_template_version"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_outputs_and_template_engine_raises_error(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that using --outputs with --template-engine raises an error."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--outputs", "--template-engine"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("Cannot use display mode flags", result.output)
        mock_show_fns["show_project_info"].assert_not_called()
        mock_show_fns["show_template_engine"].assert_not_called()

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_with_variables_and_variable_raises_error(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that using --variables with --variable raises an error."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--variables", "--variable", "test_var"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("Cannot use display mode flags", result.output)
        mock_show_fns["show_project_info"].assert_not_called()
        mock_show_fns["show_single_variable"].assert_not_called()
