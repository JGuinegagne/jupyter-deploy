import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import yaml

from jupyter_deploy.enum import StoreType
from jupyter_deploy.handlers.project.down_handler import DownHandler, StorePushResult
from jupyter_deploy.manifest import JupyterDeployManifestV1
from jupyter_deploy.provider.store.store_manager import StoreInfo


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


class TestDownHandlerPushToStore(unittest.TestCase):
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

    def _create_handler(self, mock_cwd: Mock, mock_retrieve_manifest: Mock) -> DownHandler:
        mock_cwd.return_value = Path("/mock/cwd")
        mock_retrieve_manifest.return_value = self.mock_manifest
        return DownHandler(display_manager=Mock())

    @patch("jupyter_deploy.handlers.project.down_handler.StoreManagerFactory")
    @patch("jupyter_deploy.engine.terraform.tf_down.TerraformDownHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("pathlib.Path.cwd")
    def test_push_to_store_skips_when_no_store_type(
        self,
        mock_cwd: Mock,
        mock_retrieve_manifest: Mock,
        mock_tf_handler_cls: Mock,
        mock_factory: Mock,
    ) -> None:
        handler = self._create_handler(mock_cwd, mock_retrieve_manifest)
        handler.get_store_type_from_config_or_manifest = Mock(return_value=None)  # type: ignore

        result = handler.push_to_store()

        self.assertIsNone(result)
        mock_factory.get_manager.assert_not_called()

    @patch("jupyter_deploy.handlers.project.down_handler.StoreManagerFactory")
    @patch("jupyter_deploy.engine.terraform.tf_down.TerraformDownHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("pathlib.Path.cwd")
    def test_push_to_store_skips_when_no_project_id(
        self,
        mock_cwd: Mock,
        mock_retrieve_manifest: Mock,
        mock_tf_handler_cls: Mock,
        mock_factory: Mock,
    ) -> None:
        handler = self._create_handler(mock_cwd, mock_retrieve_manifest)
        handler.get_store_type_from_config_or_manifest = Mock(return_value=StoreType.S3_ONLY)  # type: ignore
        handler.get_project_id_from_config = Mock(return_value=None)  # type: ignore

        result = handler.push_to_store()

        self.assertIsNone(result)
        mock_factory.get_manager.assert_not_called()

    @patch("jupyter_deploy.handlers.project.down_handler.StoreManagerFactory")
    @patch("jupyter_deploy.engine.terraform.tf_down.TerraformDownHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("pathlib.Path.cwd")
    def test_push_to_store_writes_marker_and_pushes(
        self,
        mock_cwd: Mock,
        mock_retrieve_manifest: Mock,
        mock_tf_handler_cls: Mock,
        mock_factory: Mock,
    ) -> None:
        handler = self._create_handler(mock_cwd, mock_retrieve_manifest)
        handler.get_store_type_from_config_or_manifest = Mock(return_value=StoreType.S3_ONLY)  # type: ignore
        handler.get_project_id_from_config = Mock(return_value="tpl-abc123")  # type: ignore
        handler.get_store_id_from_config = Mock(return_value="my-bucket")  # type: ignore
        handler._write_deletion_marker = Mock()  # type: ignore

        mock_store_manager = Mock()
        mock_store_manager.get_user_identity.return_value = "arn:aws:iam::123456789:user/jeff"
        mock_store_manager.resolve_store.return_value = StoreInfo(
            store_type=StoreType.S3_ONLY, store_id="my-bucket", location="s3://my-bucket"
        )
        mock_factory.get_manager.return_value = mock_store_manager

        result = handler.push_to_store()

        assert isinstance(result, StorePushResult)
        self.assertEqual(result.project_id, "tpl-abc123")
        self.assertEqual(result.store_type, "s3-only")
        self.assertEqual(result.store_id, "my-bucket")
        handler._write_deletion_marker.assert_called_once_with("arn:aws:iam::123456789:user/jeff")
        mock_factory.get_manager.assert_called_once_with(store_type=StoreType.S3_ONLY, store_id="my-bucket")
        mock_store_manager.push.assert_called_once_with(Path("/mock/cwd"), "tpl-abc123", handler.display_manager)


class TestWriteDeletionMarker(unittest.TestCase):
    @patch("jupyter_deploy.handlers.project.down_handler.datetime")
    @patch("jupyter_deploy.engine.terraform.tf_down.TerraformDownHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    @patch("pathlib.Path.cwd")
    def test_writes_deletion_yaml(
        self, mock_cwd: Mock, mock_retrieve_manifest: Mock, mock_tf_handler_cls: Mock, mock_datetime: Mock
    ) -> None:
        mock_datetime.now.return_value.strftime.return_value = "2026-03-06T12:00:00Z"
        mock_datetime.side_effect = None

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            mock_cwd.return_value = project_path
            mock_retrieve_manifest.return_value = JupyterDeployManifestV1(
                **{  # type: ignore
                    "schema_version": 1,
                    "template": {"name": "mock", "engine": "terraform", "version": "1.0.0"},
                }
            )
            handler = DownHandler(display_manager=Mock())
            handler._write_deletion_marker("arn:aws:iam::123456789:user/jeff")

            marker_path = project_path / ".jd" / "deletion.yaml"
            self.assertTrue(marker_path.exists())

            content = yaml.safe_load(marker_path.read_text())
            self.assertEqual(content["user"], "arn:aws:iam::123456789:user/jeff")
            self.assertEqual(content["timestamp"], "2026-03-06T12:00:00Z")
