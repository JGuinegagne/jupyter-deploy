import unittest
from unittest.mock import ANY, Mock, patch

from typer.testing import CliRunner

from jupyter_deploy.cli.app import runner as app_runner
from jupyter_deploy.engine.supervised_execution import ExecutionError


class TestConfigCommand(unittest.TestCase):
    """Test cases for the config command."""

    def get_mock_config_handler(self) -> tuple[Mock, dict[str, Mock]]:
        mock_config_handler = Mock()
        mock_has_recorded_variables = Mock()
        mock_verify_preset_exists = Mock()
        mock_validate_preset = Mock()
        mock_list_presets = Mock()
        mock_set_preset = Mock()
        mock_reset_variables = Mock()
        mock_reset_secrets = Mock()
        mock_verify = Mock()
        mock_configure = Mock()
        mock_record = Mock()
        mock_has_used_preset = Mock()

        mock_config_handler.has_recorded_variables = mock_has_recorded_variables
        mock_config_handler.verify_preset_exists = mock_verify_preset_exists
        mock_config_handler.validate_preset = mock_validate_preset
        mock_config_handler.list_presets = mock_list_presets
        mock_config_handler.set_preset = mock_set_preset
        mock_config_handler.reset_recorded_variables = mock_reset_variables
        mock_config_handler.reset_recorded_secrets = mock_reset_secrets
        mock_config_handler.verify_requirements = mock_verify
        mock_config_handler.configure = mock_configure
        mock_config_handler.record = mock_record
        mock_config_handler.has_used_preset = mock_has_used_preset

        mock_has_recorded_variables.return_value = False
        mock_verify_preset_exists.return_value = True
        mock_list_presets.return_value = ["all", "base", "none"]
        mock_verify.return_value = True
        mock_configure.return_value = None
        mock_has_used_preset.return_value = False

        return mock_config_handler, {
            "has_recorded_variables": mock_has_recorded_variables,
            "verify_preset_exists": mock_verify_preset_exists,
            "validate_preset": mock_validate_preset,
            "list_presets": mock_list_presets,
            "set_preset": mock_set_preset,
            "reset_recorded_variables": mock_reset_variables,
            "reset_recorded_secrets": mock_reset_secrets,
            "verify": mock_verify,
            "configure": mock_configure,
            "record": mock_record,
            "has_used_preset": mock_has_used_preset,
        }

    @patch("jupyter_deploy.handlers.project.config_handler.ConfigHandler")
    def test_config_cmd_calls_validate_verify_configure_and_record(self, mock_config_handler: Mock) -> None:
        mock_config_handler_instance, mock_config_fns = self.get_mock_config_handler()
        mock_config_handler.return_value = mock_config_handler_instance

        # Act
        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["config"])

        # Verify
        self.assertEqual(result.exit_code, 0)
        mock_config_handler.assert_called_once()
        mock_config_fns["has_recorded_variables"].assert_called_once()
        mock_config_fns["validate_preset"].assert_called_once_with("all")
        mock_config_fns["set_preset"].assert_called_once_with("all")
        mock_config_fns["verify"].assert_called_once()
        mock_config_fns["configure"].assert_called_with(variable_overrides={})
        mock_config_fns["record"].assert_called_once_with(record_vars=True, record_secrets=False)
        mock_config_fns["reset_recorded_variables"].assert_not_called()
        mock_config_fns["reset_recorded_secrets"].assert_not_called()
        mock_config_fns["has_used_preset"].assert_called_with("all")

    @patch("jupyter_deploy.handlers.project.config_handler.ConfigHandler")
    def test_config_passes_all_as_default_preset(self, mock_config_handler: Mock) -> None:
        mock_config_handler_instance, mock_config_fns = self.get_mock_config_handler()
        mock_config_handler.return_value = mock_config_handler_instance

        # Act
        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["config"])

        # Verify
        self.assertEqual(result.exit_code, 0)
        # Check that ConfigHandler is called with terminal_handler (ProgressDisplayManager instance)
        mock_config_handler.assert_called_once_with(output_filename=None, terminal_handler=ANY)
        mock_config_fns["has_recorded_variables"].assert_called_once()
        mock_config_fns["validate_preset"].assert_called_once_with("all")
        mock_config_fns["set_preset"].assert_called_once_with("all")
        mock_config_fns["has_used_preset"].assert_called_with("all")

    @patch("jupyter_deploy.handlers.project.config_handler.ConfigHandler")
    def test_config_default_uses_progress_display(self, mock_config_handler: Mock) -> None:
        """Test that config command by default creates ProgressDisplayManager for terminal_handler."""
        mock_config_handler_instance, _ = self.get_mock_config_handler()
        mock_config_handler.return_value = mock_config_handler_instance

        # Act
        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["config"])

        # Verify
        self.assertEqual(result.exit_code, 0)
        # terminal_handler should be a ProgressDisplayManager instance (not None)
        call_kwargs = mock_config_handler.call_args.kwargs
        self.assertIsNotNone(call_kwargs["terminal_handler"])

    @patch("jupyter_deploy.handlers.project.config_handler.ConfigHandler")
    def test_config_with_verbose_uses_no_terminal_handler(self, mock_config_handler: Mock) -> None:
        """Test that config with --verbose passes None as terminal_handler."""
        mock_config_handler_instance, _ = self.get_mock_config_handler()
        mock_config_handler.return_value = mock_config_handler_instance

        # Act
        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["config", "--verbose"])

        # Verify
        self.assertEqual(result.exit_code, 0)
        # terminal_handler should be None when verbose is True
        mock_config_handler.assert_called_once_with(output_filename=None, terminal_handler=None)

    @patch("jupyter_deploy.handlers.project.config_handler.ConfigHandler")
    def test_config_passes_no_preset_when_user_passes_none(self, mock_config_handler: Mock) -> None:
        mock_config_handler_instance, mock_config_fns = self.get_mock_config_handler()
        mock_config_handler.return_value = mock_config_handler_instance

        # Act
        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["config", "--defaults", "none"])

        # Verify
        self.assertEqual(result.exit_code, 0)
        mock_config_handler.assert_called_once_with(output_filename=None, terminal_handler=ANY)
        mock_config_fns["has_recorded_variables"].assert_called_once()
        mock_config_fns["validate_preset"].assert_not_called()  # None preset doesn't need validation
        mock_config_fns["set_preset"].assert_called_once_with(None)
        mock_config_fns["has_used_preset"].assert_called_with(None)

    @patch("jupyter_deploy.handlers.project.config_handler.ConfigHandler")
    def test_config_passes_the_preset_name_when_user_provides_a_value(self, mock_config_handler: Mock) -> None:
        mock_config_handler_instance, mock_config_fns = self.get_mock_config_handler()
        mock_config_handler.return_value = mock_config_handler_instance

        # Act
        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["config", "-d", "some-preset"])

        # Verify
        self.assertEqual(result.exit_code, 0)
        mock_config_handler.assert_called_once_with(output_filename=None, terminal_handler=ANY)
        mock_config_fns["has_recorded_variables"].assert_called_once()
        mock_config_fns["validate_preset"].assert_called_once_with("some-preset")
        mock_config_fns["set_preset"].assert_called_once_with("some-preset")
        mock_config_fns["has_used_preset"].assert_called_with("some-preset")

    @patch("jupyter_deploy.handlers.project.config_handler.ConfigHandler")
    def test_config_stops_if_validate_raises_invalid_preset(self, mock_config_handler: Mock) -> None:
        from jupyter_deploy.handlers.project.config_handler import InvalidPreset

        mock_config_handler_instance, mock_config_fns = self.get_mock_config_handler()
        mock_config_handler.return_value = mock_config_handler_instance
        mock_config_fns["validate_preset"].side_effect = InvalidPreset("all", ["base", "none"])

        # Act
        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["config"])

        # Verify
        self.assertEqual(result.exit_code, 1)
        mock_config_handler.assert_called_once()
        mock_config_fns["has_recorded_variables"].assert_called_once()
        mock_config_fns["validate_preset"].assert_called_once_with("all")
        mock_config_fns["set_preset"].assert_not_called()
        mock_config_fns["verify"].assert_not_called()
        mock_config_fns["configure"].assert_not_called()
        mock_config_fns["record"].assert_not_called()
        mock_config_fns["reset_recorded_variables"].assert_not_called()
        mock_config_fns["reset_recorded_secrets"].assert_not_called()
        mock_config_fns["has_used_preset"].assert_not_called()

    @patch("jupyter_deploy.handlers.project.config_handler.ConfigHandler")
    def test_config_stops_if_verify_requirements_raises(self, mock_config_handler: Mock) -> None:
        from jupyter_deploy.verify_utils import ToolRequiredError

        mock_config_handler_instance, mock_config_fns = self.get_mock_config_handler()
        mock_config_handler.return_value = mock_config_handler_instance
        mock_config_fns["verify"].side_effect = ToolRequiredError("terraform", "https://example.com", "not found")

        # Act
        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["config"])

        # Verify
        self.assertEqual(result.exit_code, 1)
        mock_config_handler.assert_called_once()
        mock_config_fns["has_recorded_variables"].assert_called_once()
        mock_config_fns["validate_preset"].assert_called_once()
        mock_config_fns["set_preset"].assert_called_once()
        mock_config_fns["verify"].assert_called_once()
        mock_config_fns["configure"].assert_not_called()
        mock_config_fns["record"].assert_not_called()
        mock_config_fns["reset_recorded_variables"].assert_not_called()
        mock_config_fns["reset_recorded_secrets"].assert_not_called()
        mock_config_fns["has_used_preset"].assert_not_called()

    @patch("jupyter_deploy.handlers.project.config_handler.ConfigHandler")
    def test_config_stops_if_configure_raises_execution_error(self, mock_config_handler: Mock) -> None:
        mock_config_handler_instance, mock_config_fns = self.get_mock_config_handler()
        mock_config_handler.return_value = mock_config_handler_instance
        mock_config_fns["configure"].side_effect = ExecutionError(
            command="config", retcode=1, message="Configuration failed"
        )

        # Act
        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["config"])

        # Verify - should exit with the error retcode
        self.assertEqual(result.exit_code, 1)
        mock_config_handler.assert_called_once()
        mock_config_fns["has_recorded_variables"].assert_called_once()
        mock_config_fns["validate_preset"].assert_called_once()
        mock_config_fns["set_preset"].assert_called_once()
        mock_config_fns["verify"].assert_called_once()
        mock_config_fns["configure"].assert_called_once()
        mock_config_fns["record"].assert_not_called()
        mock_config_fns["reset_recorded_variables"].assert_not_called()
        mock_config_fns["reset_recorded_secrets"].assert_not_called()
        mock_config_fns["has_used_preset"].assert_not_called()

    @patch("jupyter_deploy.handlers.project.config_handler.ConfigHandler")
    def test_config_reset_vars_and_secrets_when_user_asks(self, mock_config_handler: Mock) -> None:
        mock_config_handler_instance, mock_config_fns = self.get_mock_config_handler()
        mock_config_handler.return_value = mock_config_handler_instance

        # Act
        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["config", "--reset"])

        # Verify
        self.assertEqual(result.exit_code, 0)
        # When reset=True, has_recorded_variables is not called
        mock_config_fns["has_recorded_variables"].assert_not_called()
        mock_config_fns["validate_preset"].assert_called_once_with("all")
        mock_config_fns["set_preset"].assert_called_once_with("all")
        mock_config_fns["reset_recorded_variables"].assert_called_once()
        mock_config_fns["reset_recorded_secrets"].assert_called_once()
        mock_config_fns["verify"].assert_called_once()
        mock_config_fns["configure"].assert_called_once()
        mock_config_fns["record"].assert_called_once_with(record_vars=True, record_secrets=False)
        mock_config_fns["has_used_preset"].assert_called_once()

    @patch("jupyter_deploy.handlers.project.config_handler.ConfigHandler")
    def test_config_accepts_r_short_flag_for_reset(self, mock_config_handler: Mock) -> None:
        mock_config_handler_instance, mock_config_fns = self.get_mock_config_handler()
        mock_config_handler.return_value = mock_config_handler_instance

        # Act
        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["config", "-r"])

        # Verify
        self.assertEqual(result.exit_code, 0)
        # When reset=True, has_recorded_variables is not called
        mock_config_fns["has_recorded_variables"].assert_not_called()
        mock_config_fns["validate_preset"].assert_called_once_with("all")
        mock_config_fns["set_preset"].assert_called_once_with("all")
        mock_config_fns["record"].assert_called_once_with(record_vars=True, record_secrets=False)
        mock_config_fns["reset_recorded_variables"].assert_called_once()
        mock_config_fns["reset_recorded_secrets"].assert_called_once()
        mock_config_fns["has_used_preset"].assert_called_once()

    @patch("jupyter_deploy.handlers.project.config_handler.ConfigHandler")
    def test_config_with_reset_flag_calls_reset_before_configure_and_record(self, mock_config_handler: Mock) -> None:
        mock_config_handler_instance, mock_config_fns = self.get_mock_config_handler()
        mock_config_handler.return_value = mock_config_handler_instance

        call_order: list[str] = []

        def configure_mock(*a: list, **kw: dict) -> None:
            call_order.append("configure")
            return None

        mock_config_fns["reset_recorded_variables"].side_effect = lambda *a, **kw: call_order.append("reset_vars")
        mock_config_fns["reset_recorded_secrets"].side_effect = lambda *a, **kw: call_order.append("reset_secrets")
        mock_config_fns["configure"].side_effect = configure_mock
        mock_config_fns["record"].side_effect = lambda *a, **kw: call_order.append("record")

        # Act
        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["config", "-r"])

        # Verify
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(call_order, ["reset_vars", "reset_secrets", "configure", "record"])

    @patch("jupyter_deploy.handlers.project.config_handler.ConfigHandler")
    def test_config_records_secrets_when_the_user_asks(self, mock_config_handler: Mock) -> None:
        mock_config_handler_instance, mock_config_fns = self.get_mock_config_handler()
        mock_config_handler.return_value = mock_config_handler_instance

        # Act
        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["config", "--record-secrets"])

        # Verify
        self.assertEqual(result.exit_code, 0)
        mock_config_fns["record"].assert_called_once_with(record_vars=True, record_secrets=True)
        mock_config_fns["reset_recorded_variables"].assert_not_called()
        mock_config_fns["reset_recorded_secrets"].assert_not_called()

    @patch("jupyter_deploy.handlers.project.config_handler.ConfigHandler")
    def test_config_accept_s_flag_to_record_secrets(self, mock_config_handler: Mock) -> None:
        mock_config_handler_instance, mock_config_fns = self.get_mock_config_handler()
        mock_config_handler.return_value = mock_config_handler_instance

        # Act
        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["config", "-s"])

        # Verify
        self.assertEqual(result.exit_code, 0)
        mock_config_fns["record"].assert_called_once_with(record_vars=True, record_secrets=True)
        mock_config_fns["reset_recorded_variables"].assert_not_called()
        mock_config_fns["reset_recorded_secrets"].assert_not_called()

    @patch("jupyter_deploy.handlers.project.config_handler.ConfigHandler")
    def test_config_skip_verify(self, mock_config_handler: Mock) -> None:
        mock_config_handler_instance, mock_config_fns = self.get_mock_config_handler()
        mock_config_handler.return_value = mock_config_handler_instance

        # Act
        runner = CliRunner()
        result = runner.invoke(app_runner.app, ["config", "--skip-verify"])

        # Verify
        self.assertEqual(result.exit_code, 0)
        mock_config_handler.assert_called_once()
        mock_config_fns["has_recorded_variables"].assert_called_once()
        mock_config_fns["validate_preset"].assert_called_once()
        mock_config_fns["set_preset"].assert_called_once()
        mock_config_fns["verify"].assert_not_called()
        mock_config_fns["configure"].assert_called_once()
        mock_config_fns["record"].assert_called_once()
        mock_config_fns["reset_recorded_variables"].assert_not_called()
        mock_config_fns["reset_recorded_secrets"].assert_not_called()
        mock_config_fns["has_used_preset"].assert_called_once()
