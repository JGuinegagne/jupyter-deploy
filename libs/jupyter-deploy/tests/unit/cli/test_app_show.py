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
        mock_get_template_name = Mock(return_value="base")
        mock_get_template_version = Mock(return_value="1.0.0")
        mock_get_template_engine = Mock(return_value="terraform")
        mock_get_full_variables = Mock(return_value={})
        mock_get_full_outputs = Mock(return_value={})
        mock_get_variable_str_value_and_description = Mock(return_value=("test_value", "test description"))
        mock_get_output_str_value_and_description = Mock(return_value=("test_output", "output description"))
        mock_list_variable_names = Mock(return_value=["var1", "var2"])
        mock_list_output_names = Mock(return_value=["out1", "out2"])

        mock_show_handler.project_path = "/test/path"
        mock_show_handler.get_template_name = mock_get_template_name
        mock_show_handler.get_template_version = mock_get_template_version
        mock_show_handler.get_template_engine = mock_get_template_engine
        mock_show_handler.get_full_variables = mock_get_full_variables
        mock_show_handler.get_full_outputs = mock_get_full_outputs
        mock_show_handler.get_variable_str_value_and_description = mock_get_variable_str_value_and_description
        mock_show_handler.get_output_str_value_and_description = mock_get_output_str_value_and_description
        mock_show_handler.list_variable_names = mock_list_variable_names
        mock_show_handler.list_output_names = mock_list_output_names

        return mock_show_handler, {
            "get_template_name": mock_get_template_name,
            "get_template_version": mock_get_template_version,
            "get_template_engine": mock_get_template_engine,
            "get_full_variables": mock_get_full_variables,
            "get_full_outputs": mock_get_full_outputs,
            "get_variable_str_value_and_description": mock_get_variable_str_value_and_description,
            "get_output_str_value_and_description": mock_get_output_str_value_and_description,
            "list_variable_names": mock_list_variable_names,
            "list_output_names": mock_list_output_names,
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
        mock_show_fns["list_variable_names"].assert_called_once()

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
        mock_show_fns["list_variable_names"].assert_called_once()

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
        mock_show_fns["list_output_names"].assert_called_once()

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
        mock_show_fns["list_output_names"].assert_called_once()

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

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_displays_info_table(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that info section displays project information in a table."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--info"])

        self.assertEqual(result.exit_code, 0)
        # Check that info table includes key project details
        self.assertIn("Jupyter Deploy Project Information", result.output)
        self.assertIn("Project Path", result.output)
        self.assertIn("/test/path", result.output)
        self.assertIn("Engine", result.output)
        self.assertIn("terraform", result.output)
        self.assertIn("Template Name", result.output)
        self.assertIn("base", result.output)
        self.assertIn("Template Version", result.output)
        self.assertIn("1.0.0", result.output)

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_displays_variables_table_with_values(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that variables section displays a table with variable data."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()

        # Mock variables with values
        mock_var1 = Mock()
        mock_var1.sensitive = False
        mock_var1.assigned_value = "t2.micro"
        mock_var1.get_cli_description = Mock(return_value="Instance type")

        mock_var2 = Mock()
        mock_var2.sensitive = False
        mock_var2.assigned_value = "us-east-1"
        mock_var2.get_cli_description = Mock(return_value="AWS region")

        mock_show_fns["get_full_variables"].return_value = {
            "instance_type": mock_var1,
            "aws_region": mock_var2,
        }
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--variables"])

        self.assertEqual(result.exit_code, 0)
        # Check that variables table is displayed
        self.assertIn("Project Variables", result.output)
        self.assertIn("instance_type", result.output)
        self.assertIn("t2.micro", result.output)
        self.assertIn("Instance type", result.output)
        self.assertIn("aws_region", result.output)
        self.assertIn("us-east-1", result.output)
        self.assertIn("AWS region", result.output)

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_masks_sensitive_variables(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that sensitive variables are masked with asterisks."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()

        # Mock a sensitive variable
        mock_var_sensitive = Mock()
        mock_var_sensitive.sensitive = True
        mock_var_sensitive.assigned_value = "secret_password_should_not_appear"
        mock_var_sensitive.get_cli_description = Mock(return_value="Database password")

        mock_var_normal = Mock()
        mock_var_normal.sensitive = False
        mock_var_normal.assigned_value = "visible_value"
        mock_var_normal.get_cli_description = Mock(return_value="Normal variable")

        mock_show_fns["get_full_variables"].return_value = {
            "db_password": mock_var_sensitive,
            "normal_var": mock_var_normal,
        }
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--variables"])

        self.assertEqual(result.exit_code, 0)
        # Check that sensitive variable is masked
        self.assertIn("db_password", result.output)
        self.assertIn("****", result.output)
        self.assertNotIn("secret_password_should_not_appear", result.output)
        # Check that normal variable is not masked
        self.assertIn("normal_var", result.output)
        self.assertIn("visible_value", result.output)

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_displays_outputs_table_with_values(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that outputs section displays a table with output data."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()

        # Mock outputs with values
        mock_output1 = Mock()
        mock_output1.value = "https://jupyter.example.com"
        mock_output1.description = "Jupyter server URL"

        mock_output2 = Mock()
        mock_output2.value = "i-1234567890abcdef0"
        mock_output2.description = "EC2 instance ID"

        mock_show_fns["get_full_outputs"].return_value = {
            "jupyter_url": mock_output1,
            "instance_id": mock_output2,
        }
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--outputs"])

        self.assertEqual(result.exit_code, 0)
        # Check that outputs table is displayed
        self.assertIn("Project Outputs", result.output)
        self.assertIn("jupyter_url", result.output)
        self.assertIn("https://jupyter.example.com", result.output)
        self.assertIn("Jupyter server URL", result.output)
        self.assertIn("instance_id", result.output)
        self.assertIn("i-1234567890abcdef0", result.output)
        self.assertIn("EC2 instance ID", result.output)

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_displays_all_sections_by_default(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that default show command displays all sections (info, variables, outputs)."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()

        # Mock variables
        mock_var = Mock()
        mock_var.sensitive = False
        mock_var.assigned_value = "test_value"
        mock_var.get_cli_description = Mock(return_value="Test variable")
        mock_show_fns["get_full_variables"].return_value = {"test_var": mock_var}

        # Mock outputs
        mock_output = Mock()
        mock_output.value = "test_output_value"
        mock_output.description = "Test output"
        mock_show_fns["get_full_outputs"].return_value = {"test_output": mock_output}

        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show"])

        self.assertEqual(result.exit_code, 0)
        # Check that all three sections are displayed
        self.assertIn("Jupyter Deploy Project Information", result.output)
        self.assertIn("Project Variables", result.output)
        self.assertIn("Project Outputs", result.output)
        # Check data from each section
        self.assertIn("base", result.output)
        self.assertIn("test_var", result.output)
        self.assertIn("test_output", result.output)

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_variable_displays_rich_markup(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that --variable displays value with Rich markup (bold cyan)."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_fns["get_variable_str_value_and_description"].return_value = (
            "my_value",
            "my description",
        )
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--variable", "test_var"])

        self.assertEqual(result.exit_code, 0)
        # Rich markup is visible in the output when not using --text
        self.assertIn("my_value", result.output)

    @patch("jupyter_deploy.cli.app.ShowHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_show_command_variable_text_mode_no_markup(
        self, mock_project_ctx_manager: Mock, mock_show_handler_cls: Mock
    ) -> None:
        """Test that --variable with --text displays plain text without Rich markup."""
        mock_project_ctx_manager.side_effect = TestShowCommand.mock_project_dir

        mock_show_handler_instance, mock_show_fns = self.get_mock_show_handler()
        mock_show_fns["get_variable_str_value_and_description"].return_value = (
            "plain_value",
            "plain description",
        )
        mock_show_handler_cls.return_value = mock_show_handler_instance

        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["show", "--variable", "test_var", "--text"])

        self.assertEqual(result.exit_code, 0)
        # Should be plain text
        self.assertIn("plain_value", result.output)
        # Should not include Rich markup tags
        self.assertNotIn("[bold", result.output)
        self.assertNotIn("[cyan", result.output)
