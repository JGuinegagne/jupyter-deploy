import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from jupyter_deploy.handlers.project.down_handler import DownHandler
from jupyter_deploy.manifest import JupyterDeployManifestV1


class TestDownHandler(unittest.TestCase):
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

    def get_mock_display_manager(self) -> Mock:
        """Return a mock terminal handler."""
        mock_handler = Mock()
        mock_handler.is_pass_through.return_value = False
        return mock_handler

    @patch("jupyter_deploy.engine.terraform.tf_down.TerraformDownHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("pathlib.Path.cwd")
    def test_init_creates_terraform_handler(
        self, mock_cwd: Mock, mock_retrieve_manifest: Mock, mock_tf_handler_cls: Mock
    ) -> None:
        mock_cwd.return_value = Path("/mock/cwd")
        mock_retrieve_manifest.return_value = self.mock_manifest
        mock_tf_handler = Mock()
        mock_tf_handler_cls.return_value = mock_tf_handler
        mock_display_manager = self.get_mock_display_manager()

        handler = DownHandler(display_manager=mock_display_manager)

        # Verify TerraformDownHandler was called with correct arguments
        call_args = mock_tf_handler_cls.call_args
        self.assertEqual(call_args.kwargs["project_path"], Path("/mock/cwd"))
        self.assertEqual(call_args.kwargs["project_manifest"], self.mock_manifest)
        self.assertIsNotNone(call_args.kwargs["command_history_handler"])
        self.assertEqual(call_args.kwargs["display_manager"], mock_display_manager)
        self.assertEqual(handler._handler, mock_tf_handler)

    @patch("jupyter_deploy.engine.terraform.tf_down.TerraformDownHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("pathlib.Path.cwd")
    def test_init_passes_display_manager_to_terraform_handler(
        self, mock_cwd: Mock, mock_retrieve_manifest: Mock, mock_tf_handler_cls: Mock
    ) -> None:
        """Test that a non-None display_manager is passed through to TerraformDownHandler."""
        mock_cwd.return_value = Path("/mock/cwd")
        mock_retrieve_manifest.return_value = self.mock_manifest
        mock_tf_handler = Mock()
        mock_tf_handler_cls.return_value = mock_tf_handler

        # Create a mock terminal handler
        mock_display_manager = Mock()

        handler = DownHandler(display_manager=mock_display_manager)

        # Verify TerraformDownHandler was called with the display_manager
        call_args = mock_tf_handler_cls.call_args
        self.assertEqual(call_args.kwargs["project_path"], Path("/mock/cwd"))
        self.assertEqual(call_args.kwargs["project_manifest"], self.mock_manifest)
        self.assertIsNotNone(call_args.kwargs["command_history_handler"])
        self.assertEqual(call_args.kwargs["display_manager"], mock_display_manager)
        self.assertEqual(handler._handler, mock_tf_handler)

    @patch("jupyter_deploy.engine.terraform.tf_down.TerraformDownHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("pathlib.Path.cwd")
    def test_destroy_delegates_to_handler(
        self, mock_cwd: Mock, mock_retrieve_manifest: Mock, mock_tf_handler_cls: Mock
    ) -> None:
        mock_cwd.return_value = Path("/mock/cwd")
        mock_retrieve_manifest.return_value = self.mock_manifest
        mock_tf_handler = Mock()
        mock_tf_handler.destroy.return_value = True
        mock_tf_handler_cls.return_value = mock_tf_handler

        handler = DownHandler(display_manager=self.get_mock_display_manager())
        handler.destroy()

        mock_tf_handler.destroy.assert_called_once()

    @patch("jupyter_deploy.engine.terraform.tf_down.TerraformDownHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("pathlib.Path.cwd")
    def test_destroy_propagates_exceptions(
        self, mock_cwd: Mock, mock_retrieve_manifest: Mock, mock_tf_handler_cls: Mock
    ) -> None:
        mock_cwd.return_value = Path("/mock/cwd")
        mock_retrieve_manifest.return_value = self.mock_manifest
        mock_tf_handler = Mock()
        mock_tf_handler.destroy.side_effect = Exception("Destroy failed")
        mock_tf_handler_cls.return_value = mock_tf_handler

        handler = DownHandler(display_manager=self.get_mock_display_manager())

        with self.assertRaises(Exception) as context:
            handler.destroy()

        self.assertEqual(str(context.exception), "Destroy failed")
        mock_tf_handler.destroy.assert_called_once()

    @patch("jupyter_deploy.engine.terraform.tf_down.TerraformDownHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("pathlib.Path.cwd")
    def test_destroy_with_auto_approve(
        self, mock_cwd: Mock, mock_retrieve_manifest: Mock, mock_tf_handler_cls: Mock
    ) -> None:
        mock_cwd.return_value = Path("/mock/cwd")
        mock_retrieve_manifest.return_value = self.mock_manifest
        mock_tf_handler = Mock()
        mock_tf_handler_cls.return_value = mock_tf_handler

        handler = DownHandler(display_manager=self.get_mock_display_manager())
        handler.destroy(True)

        mock_tf_handler.destroy.assert_called_once_with(True)

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("pathlib.Path.cwd")
    def test_init_raises_value_error_for_unsupported_engine(self, mock_cwd: Mock, mock_retrieve_manifest: Mock) -> None:
        mock_cwd.return_value = Path("/mock/cwd")
        mock_manifest = self.mock_manifest
        mock_manifest.template.engine = "UNSUPPORTED_ENGINE"  # type: ignore
        mock_retrieve_manifest.return_value = mock_manifest

        with self.assertRaises(ValueError):
            DownHandler(display_manager=self.get_mock_display_manager())
