import functools
import importlib
import inspect
import unittest
from collections.abc import Callable
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from jupyter_deploy.cli import app as app_module


class TestDeployCmdWithDecorator(unittest.TestCase):
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
        mock_has_used_preset.return_value = True

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

    def get_mock_decorator(self, mock_variables: dict) -> Callable:
        def mock_decorator() -> Callable:
            def decorator(func: Callable) -> Callable:
                @functools.wraps(func)
                def wrapper(*func_args, **func_kwargs):  # type: ignore
                    # Add empty variables dict
                    func_kwargs["variables"] = mock_variables
                    return func(*func_args, **func_kwargs)

                original_sig = inspect.signature(func)
                original_params = list(original_sig.parameters.values())
                params: list[inspect.Parameter] = [p for p in original_params if p.name != "variables"]

                new_sig = original_sig.replace(parameters=params)
                wrapper.__signature__ = new_sig  # type: ignore

                return wrapper

            return decorator

        return mock_decorator

    def test_config_cmd_calls_passes_on_the_variables(self) -> None:
        with patch("jupyter_deploy.cli.variables_decorator.with_project_variables") as mock_decorator_fn:
            mock_variables = {"variable1": Mock()}
            mock_decorator_fn.side_effect = self.get_mock_decorator(mock_variables)

            # Reload module AFTER patching to pick up the patched decorator
            importlib.reload(app_module)

            with patch("jupyter_deploy.handlers.project.config_handler.ConfigHandler") as mock_config_handler:
                mock_config_handler_instance, mock_config_fns = self.get_mock_config_handler()
                mock_config_handler.return_value = mock_config_handler_instance

                # Act - use the runner that has commands registered
                app_runner = CliRunner()
                result = app_runner.invoke(app_module.runner.app, ["config"])

                # Verify
                self.assertEqual(result.exit_code, 0)
                mock_decorator_fn.assert_called_once()
                mock_config_handler.assert_called_once()
                mock_config_fns["has_recorded_variables"].assert_called_once()
                mock_config_fns["validate_preset"].assert_called_once()
                mock_config_fns["set_preset"].assert_called_once()
                mock_config_fns["verify"].assert_called_once()
                mock_config_fns["configure"].assert_called_once_with(variable_overrides=mock_variables)
                mock_config_fns["record"].assert_called_once_with(record_vars=True, record_secrets=False)
                mock_config_fns["reset_recorded_variables"].assert_not_called()
                mock_config_fns["reset_recorded_secrets"].assert_not_called()
                mock_config_fns["has_used_preset"].assert_called_once_with("all")
