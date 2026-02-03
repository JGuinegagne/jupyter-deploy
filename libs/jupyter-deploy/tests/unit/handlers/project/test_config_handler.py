import unittest
from pathlib import Path
from unittest.mock import ANY, Mock, patch

from jupyter_deploy.handlers.project.config_handler import ConfigHandler
from jupyter_deploy.manifest import JupyterDeployManifestV1


class TestConfigHandler(unittest.TestCase):
    def get_mock_handler_and_fns(self) -> tuple[Mock, dict[str, Mock]]:
        """Return mocked config handler."""
        mock_handler = Mock()
        mock_has_recorded_variables = Mock()
        mock_verify_preset = Mock()
        mock_list_presets = Mock()
        mock_reset_recorded_variables = Mock()
        mock_reset_recorded_secrets = Mock()
        mock_configure = Mock()
        mock_record = Mock()

        mock_handler.has_recorded_variables = mock_has_recorded_variables
        mock_handler.verify_preset_exists = mock_verify_preset
        mock_handler.list_presets = mock_list_presets
        mock_handler.reset_recorded_variables = mock_reset_recorded_variables
        mock_handler.reset_recorded_secrets = mock_reset_recorded_secrets
        mock_handler.configure = mock_configure
        mock_handler.record = mock_record

        mock_has_recorded_variables.return_value = False
        mock_verify_preset.return_value = True
        mock_configure.return_value = True
        mock_list_presets.return_value = ["all", "base", "none"]

        return (
            mock_handler,
            {
                "has_recorded_variables": mock_has_recorded_variables,
                "verify_preset_exists": mock_verify_preset,
                "list_presets": mock_list_presets,
                "reset_recorded_variables": mock_reset_recorded_variables,
                "reset_recorded_secrets": mock_reset_recorded_secrets,
                "configure": mock_configure,
                "record": mock_record,
            },
        )

    def setUp(self) -> None:
        self.mock_manifest = JupyterDeployManifestV1(
            **{  # type: ignore
                "schema_version": 1,
                "template": {
                    "name": "mock-template-name",
                    "engine": "terraform",
                    "version": "1.0.0",
                },
            }
        )

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_config_handler_reads_the_manifest(self, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.mock_manifest
        handler = ConfigHandler()
        mock_retrieve_manifest.assert_called_once()
        self.assertEqual(handler.project_manifest, self.mock_manifest)
        self.assertEqual(handler.engine, self.mock_manifest.get_engine())

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    @patch("pathlib.Path.cwd")
    def test_config_handler_correctly_implements_tf_engine(
        self, mock_cwd: Mock, mock_tf_handler: Mock, mock_retrieve_manifest: Mock
    ) -> None:
        path = Path("/some/cur/dir")
        mock_cwd.return_value = path
        mock_retrieve_manifest.return_value = self.mock_manifest

        # right now, it defaults to terraform
        # in the future, it should infer it from the project
        handler = ConfigHandler()

        tf_mock_handler_instance, tf_fns = self.get_mock_handler_and_fns()
        tf_mock_configure = tf_fns["configure"]
        mock_tf_handler.return_value = tf_mock_handler_instance

        self.assertIsNone(handler.preset_name)
        mock_tf_handler.assert_called_once_with(
            project_path=path,
            project_manifest=self.mock_manifest,
            command_history_handler=ANY,
            output_filename=None,
            terminal_handler=None,
        )
        tf_mock_configure.assert_not_called()

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    def test_has_recorded_variables_delegates_to_handler(
        self, mock_tf_handler: Mock, mock_retrieve_manifest: Mock
    ) -> None:
        mock_retrieve_manifest.return_value = self.mock_manifest
        tf_mock_handler_instance, tf_fns = self.get_mock_handler_and_fns()
        tf_mock_has_recorded = tf_fns["has_recorded_variables"]
        tf_mock_has_recorded.return_value = True
        mock_tf_handler.return_value = tf_mock_handler_instance

        handler = ConfigHandler()
        result = handler.has_recorded_variables()

        self.assertTrue(result)
        tf_mock_has_recorded.assert_called_once()

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    def test_verify_preset_exists_delegates_to_handler(
        self, mock_tf_handler: Mock, mock_retrieve_manifest: Mock
    ) -> None:
        mock_retrieve_manifest.return_value = self.mock_manifest
        tf_mock_handler_instance, tf_fns = self.get_mock_handler_and_fns()
        tf_mock_verify_preset = tf_fns["verify_preset_exists"]
        tf_mock_verify_preset.return_value = True
        mock_tf_handler.return_value = tf_mock_handler_instance

        handler = ConfigHandler()
        result = handler.verify_preset_exists("all")

        self.assertTrue(result)
        tf_mock_verify_preset.assert_called_once_with("all")

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    def test_list_presets_delegates_to_handler(self, mock_tf_handler: Mock, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.mock_manifest
        tf_mock_handler_instance, tf_fns = self.get_mock_handler_and_fns()
        tf_mock_list_presets = tf_fns["list_presets"]
        tf_mock_list_presets.return_value = ["all", "base", "none"]
        mock_tf_handler.return_value = tf_mock_handler_instance

        handler = ConfigHandler()
        result = handler.list_presets()

        self.assertEqual(result, ["all", "base", "none"])
        tf_mock_list_presets.assert_called_once()

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    def test_set_preset_sets_instance_variable(self, mock_tf_handler: Mock, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.mock_manifest
        tf_mock_handler_instance, _ = self.get_mock_handler_and_fns()
        mock_tf_handler.return_value = tf_mock_handler_instance

        handler = ConfigHandler()
        self.assertIsNone(handler.preset_name)

        handler.set_preset("all")
        self.assertEqual(handler.preset_name, "all")

        handler.set_preset(None)
        self.assertIsNone(handler.preset_name)

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    def test_validate_preset_succeeds_for_valid_preset(
        self, mock_tf_handler: Mock, mock_retrieve_manifest: Mock
    ) -> None:
        mock_retrieve_manifest.return_value = self.mock_manifest
        tf_mock_handler_instance, tf_fns = self.get_mock_handler_and_fns()
        tf_mock_verify_preset = tf_fns["verify_preset_exists"]
        tf_mock_verify_preset.return_value = True
        mock_tf_handler.return_value = tf_mock_handler_instance

        handler = ConfigHandler()
        # Should not raise
        handler.validate_preset("all")
        tf_mock_verify_preset.assert_called_once_with("all")

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    def test_validate_preset_raises_for_invalid_preset(
        self, mock_tf_handler: Mock, mock_retrieve_manifest: Mock
    ) -> None:
        from jupyter_deploy.handlers.project.config_handler import InvalidPreset

        mock_retrieve_manifest.return_value = self.mock_manifest
        tf_mock_handler_instance, tf_fns = self.get_mock_handler_and_fns()
        tf_mock_verify_preset = tf_fns["verify_preset_exists"]
        tf_mock_list_presets = tf_fns["list_presets"]
        tf_mock_verify_preset.return_value = False
        tf_mock_list_presets.return_value = ["all", "base", "none"]
        mock_tf_handler.return_value = tf_mock_handler_instance

        handler = ConfigHandler()
        with self.assertRaises(InvalidPreset) as context:
            handler.validate_preset("invalid")

        self.assertEqual(context.exception.preset_name, "invalid")
        self.assertEqual(context.exception.valid_presets, ["all", "base", "none"])
        tf_mock_verify_preset.assert_called_once_with("invalid")
        tf_mock_list_presets.assert_called_once()

    @patch("jupyter_deploy.verify_utils.verify_tools_installation")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    def test_verify_calls_verify_utils(
        self, mock_tf_handler: Mock, mock_retrieve_manifest: Mock, mock_verify: Mock
    ) -> None:
        mock_req1 = Mock()
        mock_req2 = Mock()

        with patch.object(self.mock_manifest, "get_requirements", return_value=[mock_req1, mock_req2]):
            mock_retrieve_manifest.return_value = self.mock_manifest
            tf_mock_handler_instance, tf_fns = self.get_mock_handler_and_fns()
            tf_mock_configure = tf_fns["configure"]
            mock_tf_handler.return_value = tf_mock_handler_instance

            handler = ConfigHandler()
            handler.verify_requirements()

            mock_verify.assert_called_once_with([mock_req1, mock_req2])
            tf_mock_configure.assert_not_called()

    @patch("jupyter_deploy.verify_utils.verify_tools_installation")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    def test_verify_surfaces_verify_utils_exception(
        self, mock_tf_handler: Mock, mock_retrieve_manifest: Mock, mock_verify: Mock
    ) -> None:
        from jupyter_deploy.verify_utils import ToolRequiredError

        mock_retrieve_manifest.return_value = self.mock_manifest
        tf_mock_handler_instance, _ = self.get_mock_handler_and_fns()
        mock_tf_handler.return_value = tf_mock_handler_instance
        mock_verify.side_effect = ToolRequiredError("terraform", None, None)

        handler = ConfigHandler()
        with self.assertRaises(ToolRequiredError):
            handler.verify_requirements()

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    def test_reset_variables_calls_underlying_handler_method(
        self, mock_tf_handler: Mock, mock_retrieve_manifest: Mock
    ) -> None:
        mock_retrieve_manifest.return_value = self.mock_manifest
        ConfigHandler()

        tf_mock_handler_instance, tf_fns = self.get_mock_handler_and_fns()
        tf_mock_reset_vars = tf_fns["reset_recorded_variables"]
        tf_mock_reset_secrets = tf_fns["reset_recorded_secrets"]
        mock_tf_handler.return_value = tf_mock_handler_instance

        handler = ConfigHandler()
        handler.reset_recorded_variables()

        tf_mock_reset_vars.assert_called_once()
        tf_mock_reset_secrets.assert_not_called()

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    def test_reset_secrets_calls_underlying_handler_method(
        self, mock_tf_handler: Mock, mock_retrieve_manifest: Mock
    ) -> None:
        mock_retrieve_manifest.return_value = self.mock_manifest
        tf_mock_handler_instance, tf_fns = self.get_mock_handler_and_fns()
        tf_mock_reset_vars = tf_fns["reset_recorded_variables"]
        tf_mock_reset_secrets = tf_fns["reset_recorded_secrets"]
        mock_tf_handler.return_value = tf_mock_handler_instance

        handler = ConfigHandler()
        handler.reset_recorded_secrets()

        tf_mock_reset_vars.assert_not_called()
        tf_mock_reset_secrets.assert_called_once()

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    def test_configure_calls_underlying_handler_method(
        self, mock_tf_handler: Mock, mock_retrieve_manifest: Mock
    ) -> None:
        mock_retrieve_manifest.return_value = self.mock_manifest
        tf_mock_handler_instance, tf_fns = self.get_mock_handler_and_fns()
        tf_mock_configure = tf_fns["configure"]
        mock_tf_handler.return_value = tf_mock_handler_instance

        handler = ConfigHandler()
        result = handler.configure()

        self.assertTrue(result)
        tf_mock_configure.assert_called_once_with(preset_name=None, variable_overrides=None)

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    def test_configure_passes_the_preset(self, mock_tf_handler: Mock, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.mock_manifest
        tf_mock_handler_instance, tf_fns = self.get_mock_handler_and_fns()
        tf_mock_configure = tf_fns["configure"]
        mock_tf_handler.return_value = tf_mock_handler_instance

        handler = ConfigHandler()
        handler.set_preset("all")
        result = handler.configure()

        self.assertTrue(result)
        tf_mock_configure.assert_called_once_with(preset_name="all", variable_overrides=None)

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    def test_configure_passes_the_variables(self, mock_tf_handler: Mock, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.mock_manifest
        tf_mock_handler_instance, tf_fns = self.get_mock_handler_and_fns()
        tf_mock_configure = tf_fns["configure"]
        mock_tf_handler.return_value = tf_mock_handler_instance

        handler = ConfigHandler()
        handler.set_preset("all")

        overrides = {"var1": Mock()}
        result = handler.configure(variable_overrides=overrides)  # type: ignore

        self.assertTrue(result)
        tf_mock_configure.assert_called_once_with(preset_name="all", variable_overrides=overrides)

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    def test_configure_surfaces_underlying_method_exception(
        self, mock_tf_handler: Mock, mock_retrieve_manifest: Mock
    ) -> None:
        mock_retrieve_manifest.return_value = self.mock_manifest
        tf_mock_handler_instance, tf_fns = self.get_mock_handler_and_fns()
        tf_mock_configure = tf_fns["configure"]
        mock_tf_handler.return_value = tf_mock_handler_instance

        error = RuntimeError("another-error")
        tf_mock_configure.side_effect = error

        handler = ConfigHandler()

        with self.assertRaisesRegex(RuntimeError, "another-error"):
            handler.configure()

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    def test_record_passes_the_flags_correctly(self, mock_tf_handler: Mock, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.mock_manifest
        tf_mock_handler_instance, tf_fns = self.get_mock_handler_and_fns()
        tf_mock_record = tf_fns["record"]
        mock_tf_handler.return_value = tf_mock_handler_instance

        handler = ConfigHandler()
        handler.record()
        tf_mock_record.assert_called_once_with(record_vars=False, record_secrets=False)

        tf_mock_record.reset_mock()
        handler.record(record_vars=True)
        tf_mock_record.assert_called_once_with(record_vars=True, record_secrets=False)

        tf_mock_record.reset_mock()
        handler.record(record_secrets=True)
        tf_mock_record.assert_called_once_with(record_vars=False, record_secrets=True)

        tf_mock_record.reset_mock()
        handler.record(record_vars=True, record_secrets=True)
        tf_mock_record.assert_called_once_with(record_vars=True, record_secrets=True)

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    def test_record_surfaces_underlying_exception(self, mock_tf_handler: Mock, mock_retrieve_manifest: Mock) -> None:
        mock_retrieve_manifest.return_value = self.mock_manifest
        tf_mock_handler_instance, tf_fns = self.get_mock_handler_and_fns()
        tf_mock_record = tf_fns["record"]
        mock_tf_handler.return_value = tf_mock_handler_instance
        tf_mock_record.side_effect = RuntimeError("Cannot record!")

        handler = ConfigHandler()
        with self.assertRaises(RuntimeError):
            handler.record(record_vars=True)
