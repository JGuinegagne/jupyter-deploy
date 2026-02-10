import unittest
from unittest.mock import Mock, patch

from jupyter_deploy.engine.enum import EngineType
from jupyter_deploy.handlers.project.show_handler import ShowHandler
from jupyter_deploy.manifest import JupyterDeployManifestV1


class TestShowHandler(unittest.TestCase):
    def get_mock_manifest(self) -> JupyterDeployManifestV1:
        """Create a mock manifest."""
        return JupyterDeployManifestV1(
            **{  # type: ignore
                "schema_version": 1,
                "template": {
                    "name": "tf-aws-ec2-base",
                    "engine": "terraform",
                    "version": "1.0.0",
                },
            }
        )

    def get_mock_console_and_fns(self) -> tuple[Mock, dict[str, Mock]]:
        """Return a mocked rich console instance."""
        mock_console = Mock()
        mock_print = Mock()
        mock_line = Mock()
        mock_console.print = mock_print
        mock_console.line = mock_line
        return mock_console, {"print": mock_print, "line": mock_line}

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_init_terraform(self, mock_retrieve_manifest: Mock) -> None:
        mock_manifest = self.get_mock_manifest()
        mock_retrieve_manifest.return_value = mock_manifest
        handler = ShowHandler()

        self.assertIsNotNone(handler._outputs_handler)
        self.assertIsNotNone(handler._variables_handler)
        self.assertEqual(handler.engine, EngineType.TERRAFORM)
        self.assertEqual(handler.project_manifest, mock_manifest)

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_get_template_name(self, mock_retrieve_manifest: Mock) -> None:
        mock_manifest = self.get_mock_manifest()
        mock_manifest.template.name = "base"
        mock_retrieve_manifest.return_value = mock_manifest
        handler = ShowHandler()

        result = handler.get_template_name()
        self.assertEqual(result, "base")

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_get_full_outputs_no_outputs(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        with patch.object(handler._outputs_handler, "get_full_project_outputs", return_value={}):
            result = handler.get_full_outputs()

        self.assertEqual(result, {})

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_get_full_outputs_with_outputs(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        mock_output = Mock()
        mock_output.value = "https://example.com"
        mock_output.description = "Jupyter URL"
        mock_outputs = {"jupyter_url": mock_output}

        with patch.object(handler._outputs_handler, "get_full_project_outputs", return_value=mock_outputs):
            result = handler.get_full_outputs()

        self.assertEqual(result, mock_outputs)
        self.assertEqual(result["jupyter_url"].value, "https://example.com")

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_get_full_outputs_exception(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        with (
            patch.object(handler._outputs_handler, "get_full_project_outputs", side_effect=Exception("Test error")),
            self.assertRaises(Exception),  # noqa: B017
        ):
            handler.get_full_outputs()

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_get_full_variables_no_variables(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        with (
            patch.object(handler._variables_handler, "get_template_variables", return_value={}),
            patch.object(handler._variables_handler, "sync_engine_varfiles_with_project_variables_config"),
        ):
            result = handler.get_full_variables()

        self.assertEqual(result, {})

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_get_full_variables_with_variables(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        mock_normal_var = Mock()
        mock_normal_var.get_cli_description = Mock(return_value="Normal variable")
        mock_normal_var.sensitive = False
        mock_normal_var.assigned_value = "value1"

        mock_sensitive_var = Mock()
        mock_sensitive_var.get_cli_description = Mock(return_value="Sensitive variable")
        mock_sensitive_var.sensitive = True
        mock_sensitive_var.assigned_value = "secret"

        mock_vars = {"normal_var": mock_normal_var, "sensitive_var": mock_sensitive_var}

        with (
            patch.object(handler._variables_handler, "get_template_variables", return_value=mock_vars),
            patch.object(handler._variables_handler, "sync_engine_varfiles_with_project_variables_config"),
        ):
            result = handler.get_full_variables()

        self.assertEqual(result, mock_vars)
        self.assertEqual(result["normal_var"].assigned_value, "value1")
        self.assertEqual(result["sensitive_var"].assigned_value, "secret")

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_sensitive_variables_are_masked(self, mock_retrieve_manifest: Mock) -> None:
        """Test that get_variable masks sensitive variables."""
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        mock_sensitive_var = Mock()
        mock_sensitive_var.get_cli_description = Mock(return_value="Sensitive variable")
        mock_sensitive_var.sensitive = True
        mock_sensitive_var.assigned_value = "secret_value_should_not_be_visible"

        mock_vars = {"sensitive_var": mock_sensitive_var}

        with (
            patch.object(handler._variables_handler, "get_template_variables", return_value=mock_vars),
            patch.object(handler._variables_handler, "sync_engine_varfiles_with_project_variables_config"),
        ):
            value, description = handler.get_variable_str_value_and_description("sensitive_var")

        self.assertEqual(value, "****")
        self.assertNotEqual(value, "secret_value_should_not_be_visible")

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_get_full_variables_exception(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        with (
            patch.object(
                handler._variables_handler,
                "sync_engine_varfiles_with_project_variables_config",
                side_effect=Exception("Test error"),
            ),
            self.assertRaises(Exception),  # noqa: B017
        ):
            handler.get_full_variables()

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_show_single_variable_sensitive(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        mock_var = Mock()
        mock_var.sensitive = True
        mock_var.assigned_value = "secret_value"
        mock_var.get_cli_description = Mock(return_value="Secret variable")
        mock_vars = {"secret_var": mock_var}

        with (
            patch.object(handler._variables_handler, "get_template_variables", return_value=mock_vars),
            patch.object(handler._variables_handler, "sync_engine_varfiles_with_project_variables_config"),
        ):
            value, description = handler.get_variable_str_value_and_description("secret_var")

        self.assertEqual(value, "****")
        self.assertEqual(description, "Secret variable")

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_show_single_variable_not_found(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        mock_vars = {"other_var": Mock()}

        with (
            patch.object(handler._variables_handler, "get_template_variables", return_value=mock_vars),
            patch.object(handler._variables_handler, "sync_engine_varfiles_with_project_variables_config"),
            self.assertRaises(Exception),  # noqa: B017
        ):
            handler.get_variable_str_value_and_description("nonexistent_var")

        # Verify error message contains key components

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_show_single_variable_description(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        mock_var = Mock()
        mock_var.get_cli_description = Mock(return_value="The instance type for the deployment")
        mock_vars = {"instance_type": mock_var}

        with (
            patch.object(handler._variables_handler, "get_template_variables", return_value=mock_vars),
            patch.object(handler._variables_handler, "sync_engine_varfiles_with_project_variables_config"),
        ):
            handler.get_variable_str_value_and_description("instance_type")

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_show_single_variable_exception(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        with (
            patch.object(
                handler._variables_handler,
                "sync_engine_varfiles_with_project_variables_config",
                side_effect=Exception("Test error"),
            ),
            self.assertRaises(Exception),  # noqa: B017
        ):
            handler.get_variable_str_value_and_description("test_var")

        # Verify error message contains key components

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_show_single_output_success(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        mock_output = Mock()
        mock_output.value = "https://example.com"
        mock_outputs = {"jupyter_url": mock_output}

        with patch.object(handler._outputs_handler, "get_full_project_outputs", return_value=mock_outputs):
            handler.get_output_str_value_and_description("jupyter_url")

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_show_single_output_description(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        mock_output = Mock()
        mock_output.description = "URL for accessing Jupyter server"
        mock_outputs = {"jupyter_url": mock_output}

        with patch.object(handler._outputs_handler, "get_full_project_outputs", return_value=mock_outputs):
            handler.get_output_str_value_and_description("jupyter_url")

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_show_single_output_not_found(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        mock_outputs = {"other_output": Mock()}

        with (
            patch.object(handler._outputs_handler, "get_full_project_outputs", return_value=mock_outputs),
            self.assertRaises(Exception),  # noqa: B017
        ):
            handler.get_output_str_value_and_description("nonexistent_output")

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_show_single_output_no_outputs(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        with (
            patch.object(handler._outputs_handler, "get_full_project_outputs", return_value={}),
            self.assertRaises(Exception),  # noqa: B017
        ):
            handler.get_output_str_value_and_description("test_output")

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_show_single_output_exception(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        with (
            patch.object(handler._outputs_handler, "get_full_project_outputs", side_effect=Exception("Test error")),
            self.assertRaises(Exception),  # noqa: B017
        ):
            handler.get_output_str_value_and_description("test_output")

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_show_single_variable_text_mode(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        mock_var = Mock()
        mock_var.sensitive = False
        mock_var.assigned_value = "test_value"
        mock_vars = {"test_var": mock_var}

        with (
            patch.object(handler._variables_handler, "get_template_variables", return_value=mock_vars),
            patch.object(handler._variables_handler, "sync_engine_varfiles_with_project_variables_config"),
        ):
            handler.get_variable_str_value_and_description("test_var")

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_show_single_variable_description_text_mode(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        mock_var = Mock()
        mock_var.get_cli_description = Mock(return_value="The instance type for the deployment")
        mock_vars = {"instance_type": mock_var}

        with (
            patch.object(handler._variables_handler, "get_template_variables", return_value=mock_vars),
            patch.object(handler._variables_handler, "sync_engine_varfiles_with_project_variables_config"),
        ):
            handler.get_variable_str_value_and_description("instance_type")

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_show_single_output_text_mode(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        mock_output = Mock()
        mock_output.value = "https://example.com"
        mock_outputs = {"jupyter_url": mock_output}

        with patch.object(handler._outputs_handler, "get_full_project_outputs", return_value=mock_outputs):
            handler.get_output_str_value_and_description("jupyter_url")

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_show_single_output_description_text_mode(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        mock_output = Mock()
        mock_output.description = "URL for accessing Jupyter server"
        mock_outputs = {"jupyter_url": mock_output}

        with patch.object(handler._outputs_handler, "get_full_project_outputs", return_value=mock_outputs):
            handler.get_output_str_value_and_description("jupyter_url")

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_show_template_name(self, mock_retrieve_manifest: Mock) -> None:
        mock_manifest = self.get_mock_manifest()
        mock_manifest.template.name = "base"
        mock_retrieve_manifest.return_value = mock_manifest
        handler = ShowHandler()

        handler.get_template_name()

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_show_template_name_text_mode(self, mock_retrieve_manifest: Mock) -> None:
        mock_manifest = self.get_mock_manifest()
        mock_manifest.template.name = "base"
        mock_retrieve_manifest.return_value = mock_manifest
        handler = ShowHandler()

        handler.get_template_name()

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_show_template_version(self, mock_retrieve_manifest: Mock) -> None:
        mock_manifest = self.get_mock_manifest()
        mock_manifest.template.version = "0.2.7"
        mock_retrieve_manifest.return_value = mock_manifest
        handler = ShowHandler()

        handler.get_template_version()

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_show_template_version_text_mode(self, mock_retrieve_manifest: Mock) -> None:
        mock_manifest = self.get_mock_manifest()
        mock_manifest.template.version = "0.2.7"
        mock_retrieve_manifest.return_value = mock_manifest
        handler = ShowHandler()

        handler.get_template_version()

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_show_template_engine(self, mock_retrieve_manifest: Mock) -> None:
        mock_manifest = self.get_mock_manifest()
        mock_retrieve_manifest.return_value = mock_manifest
        handler = ShowHandler()

        handler.get_template_engine()

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_show_template_engine_text_mode(self, mock_retrieve_manifest: Mock) -> None:
        mock_manifest = self.get_mock_manifest()
        mock_retrieve_manifest.return_value = mock_manifest
        handler = ShowHandler()

        handler.get_template_engine()

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_list_variable_names(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        mock_var1 = Mock()
        mock_var2 = Mock()
        mock_var3 = Mock()
        mock_vars = {"instance_type": mock_var1, "ami_id": mock_var2, "key_name": mock_var3}

        with (
            patch.object(handler._variables_handler, "get_template_variables", return_value=mock_vars),
            patch.object(handler._variables_handler, "sync_engine_varfiles_with_project_variables_config"),
        ):
            handler.list_variable_names()

        # Should print each name on a separate line with Rich markup

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_list_variable_names_text_mode(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        mock_var1 = Mock()
        mock_var2 = Mock()
        mock_var3 = Mock()
        mock_vars = {"instance_type": mock_var1, "ami_id": mock_var2, "key_name": mock_var3}

        with (
            patch.object(handler._variables_handler, "get_template_variables", return_value=mock_vars),
            patch.object(handler._variables_handler, "sync_engine_varfiles_with_project_variables_config"),
        ):
            result = handler.list_variable_names()

        # Should return a list of variable names
        self.assertIsInstance(result, list)
        self.assertEqual(set(result), {"instance_type", "ami_id", "key_name"})

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_list_output_names(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        mock_output1 = Mock()
        mock_output2 = Mock()
        mock_outputs = {"jupyter_url": mock_output1, "instance_id": mock_output2}

        with patch.object(handler._outputs_handler, "get_full_project_outputs", return_value=mock_outputs):
            handler.list_output_names()

        # Should print each name on a separate line with Rich markup

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_list_output_names_text_mode(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.get_mock_manifest()
        handler = ShowHandler()

        mock_output1 = Mock()
        mock_output2 = Mock()
        mock_outputs = {"jupyter_url": mock_output1, "instance_id": mock_output2}

        with patch.object(handler._outputs_handler, "get_full_project_outputs", return_value=mock_outputs):
            result = handler.list_output_names()

        # Should return a list of output names
        self.assertIsInstance(result, list)
        self.assertEqual(set(result), {"jupyter_url", "instance_id"})
