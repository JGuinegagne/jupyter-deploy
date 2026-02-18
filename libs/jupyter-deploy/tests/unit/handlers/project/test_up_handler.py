import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from jupyter_deploy.engine.supervised_execution import NullDisplay
from jupyter_deploy.handlers.project.up_handler import UpHandler
from jupyter_deploy.manifest import JupyterDeployManifestV1


class TestUpHandler(unittest.TestCase):
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

    @patch("jupyter_deploy.engine.terraform.tf_up.TerraformUpHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("pathlib.Path.cwd")
    def test_init_creates_terraform_handler(
        self, mock_cwd: Mock, mock_retrieve_manifest: Mock, mock_tf_handler_cls: Mock
    ) -> None:
        mock_cwd.return_value = Path("/mock/cwd")
        mock_retrieve_manifest.return_value = self.mock_manifest
        mock_tf_handler = Mock()
        mock_tf_handler_cls.return_value = mock_tf_handler
        mock_tf_handler.engine_dir_path = Path("/mock/cwd/engine")

        handler = UpHandler(display_manager=NullDisplay())

        # Verify TerraformUpHandler was called with correct arguments
        call_args = mock_tf_handler_cls.call_args
        self.assertEqual(call_args.kwargs["project_path"], Path("/mock/cwd"))
        self.assertEqual(call_args.kwargs["project_manifest"], self.mock_manifest)
        self.assertIsNotNone(call_args.kwargs["command_history_handler"])
        self.assertIsInstance(call_args.kwargs["display_manager"], NullDisplay)
        self.assertEqual(handler._handler, mock_tf_handler)

    @patch("jupyter_deploy.engine.terraform.tf_up.TerraformUpHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("pathlib.Path.cwd")
    def test_init_passes_display_manager_to_terraform_handler(
        self, mock_cwd: Mock, mock_retrieve_manifest: Mock, mock_tf_handler_cls: Mock
    ) -> None:
        """Test that a non-None display_manager is passed through to TerraformUpHandler."""
        mock_cwd.return_value = Path("/mock/cwd")
        mock_retrieve_manifest.return_value = self.mock_manifest
        mock_tf_handler = Mock()
        mock_tf_handler_cls.return_value = mock_tf_handler
        mock_tf_handler.engine_dir_path = Path("/mock/cwd/engine")

        # Create a mock terminal handler
        mock_display_manager = Mock()

        handler = UpHandler(display_manager=mock_display_manager)

        # Verify TerraformUpHandler was called with the display_manager
        call_args = mock_tf_handler_cls.call_args
        self.assertEqual(call_args.kwargs["project_path"], Path("/mock/cwd"))
        self.assertEqual(call_args.kwargs["project_manifest"], self.mock_manifest)
        self.assertIsNotNone(call_args.kwargs["command_history_handler"])
        self.assertEqual(call_args.kwargs["display_manager"], mock_display_manager)
        self.assertEqual(handler._handler, mock_tf_handler)

    @patch("jupyter_deploy.engine.terraform.tf_up.TerraformUpHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("pathlib.Path.cwd")
    def test_apply_delegates_to_handler(
        self, mock_cwd: Mock, mock_retrieve_manifest: Mock, mock_tf_handler_cls: Mock
    ) -> None:
        path = Path("/mock/path")
        mock_cwd.return_value = Path("/mock/cwd")
        mock_retrieve_manifest.return_value = self.mock_manifest
        mock_tf_handler = Mock()
        mock_tf_handler_cls.return_value = mock_tf_handler
        mock_tf_handler.engine_dir_path = Path("/mock/cwd/engine")

        handler = UpHandler(display_manager=NullDisplay())
        handler.apply(path, auto_approve=False)

        mock_tf_handler.apply.assert_called_once_with(path, False)

    @patch("jupyter_deploy.engine.terraform.tf_up.TerraformUpHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("pathlib.Path.cwd")
    def test_apply_propagates_exceptions(
        self, mock_cwd: Mock, mock_retrieve_manifest: Mock, mock_tf_handler_cls: Mock
    ) -> None:
        path = Path("/mock/path")
        mock_cwd.return_value = Path("/mock/cwd")
        mock_retrieve_manifest.return_value = self.mock_manifest
        mock_tf_handler = Mock()
        mock_tf_handler.apply.side_effect = Exception("Apply failed")
        mock_tf_handler.engine_dir_path = Path("/mock/cwd/engine")
        mock_tf_handler_cls.return_value = mock_tf_handler

        handler = UpHandler(display_manager=NullDisplay())

        with self.assertRaises(Exception) as context:
            handler.apply(path)

        self.assertEqual(str(context.exception), "Apply failed")
        mock_tf_handler.apply.assert_called_once()

    @patch("jupyter_deploy.engine.terraform.tf_up.TerraformUpHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("pathlib.Path.cwd")
    def test_get_default_config_filename_delegates_to_handler(
        self, mock_cwd: Mock, mock_retrieve_manifest: Mock, mock_tf_handler_cls: Mock
    ) -> None:
        mock_cwd.return_value = Path("/mock/cwd")
        mock_retrieve_manifest.return_value = self.mock_manifest
        mock_tf_handler = Mock()
        mock_tf_handler.engine_dir_path = Path("/mock/cwd/engine")
        mock_tf_handler.get_default_config_filename.return_value = "jdout-tfplan"
        mock_tf_handler_cls.return_value = mock_tf_handler

        handler = UpHandler(display_manager=NullDisplay())
        result = handler.get_default_config_filename()

        mock_tf_handler.get_default_config_filename.assert_called_once()
        self.assertEqual(result, "jdout-tfplan")

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("pathlib.Path.cwd")
    def test_init_raises_value_error_for_unsupported_engine(self, mock_cwd: Mock, mock_retrieve_manifest: Mock) -> None:
        mock_cwd.return_value = Path("/mock/cwd")
        mock_manifest = self.mock_manifest
        # Change the engine to an unsupported one
        mock_manifest.template.engine = "UNSUPPORTED_ENGINE"  # type: ignore
        mock_retrieve_manifest.return_value = mock_manifest

        with self.assertRaises(ValueError):
            UpHandler(display_manager=NullDisplay())

    @patch("jupyter_deploy.engine.terraform.tf_up.TerraformUpHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("pathlib.Path.cwd")
    def test_get_config_file_path_when_file_exists(
        self,
        mock_cwd: Mock,
        mock_retrieve_manifest: Mock,
        mock_tf_handler_cls: Mock,
    ) -> None:
        mock_cwd.return_value = Path("/mock/cwd")
        mock_retrieve_manifest.return_value = self.mock_manifest
        mock_tf_handler = Mock()
        mock_tf_handler.engine_dir_path = Path("/mock/cwd/engine")
        mock_tf_handler.get_default_config_filename.return_value = "jdout-tfplan"
        mock_tf_handler_cls.return_value = mock_tf_handler

        with patch.object(Path, "exists", return_value=True):
            handler = UpHandler(display_manager=NullDisplay())
            result = handler.get_config_file_path("test-config")

        self.assertEqual(result, Path("/mock/cwd/engine/test-config"))

    @patch("jupyter_deploy.engine.terraform.tf_up.TerraformUpHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("pathlib.Path.cwd")
    def test_get_config_file_path_when_file_does_not_exist(
        self,
        mock_cwd: Mock,
        mock_retrieve_manifest: Mock,
        mock_tf_handler_cls: Mock,
    ) -> None:
        """Test that FileNotFoundError is raised when config file does not exist."""
        mock_cwd.return_value = Path("/mock/cwd")
        mock_retrieve_manifest.return_value = self.mock_manifest

        mock_tf_handler = Mock()
        mock_tf_handler.engine_dir_path = Path("/mock/cwd/engine")
        mock_tf_handler.get_default_config_filename.return_value = "jdout-tfplan"
        mock_tf_handler_cls.return_value = mock_tf_handler

        with patch.object(Path, "exists", return_value=False):
            handler = UpHandler(display_manager=NullDisplay())
            with self.assertRaises(FileNotFoundError) as context:
                handler.get_config_file_path("test-config")

        # Verify error message contains helpful information
        self.assertIn("test-config", str(context.exception))
        self.assertIn("jd config", str(context.exception))
