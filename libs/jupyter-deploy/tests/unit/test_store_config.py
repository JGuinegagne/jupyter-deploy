import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from jupyter_deploy.enum import StoreType
from jupyter_deploy.exceptions import InvalidStoreTypeError
from jupyter_deploy.handlers.base_project_handler import retrieve_store_config, write_store_config
from jupyter_deploy.handlers.project.config_handler import ConfigHandler
from jupyter_deploy.manifest import JupyterDeployManifestV1, JupyterDeployProjectStoreV1
from jupyter_deploy.store_config import JupyterDeployStoreConfigV1


class TestJupyterDeployStoreConfigV1(unittest.TestCase):
    def test_parse_with_both_fields(self) -> None:
        config = JupyterDeployStoreConfigV1(**{"store-type": "s3-only", "store-id": "my-bucket"})  # type: ignore
        self.assertEqual(config.store_type, "s3-only")
        self.assertEqual(config.store_id, "my-bucket")

    def test_parse_with_store_type_only(self) -> None:
        config = JupyterDeployStoreConfigV1(**{"store-type": "s3-ddb"})  # type: ignore
        self.assertEqual(config.store_type, "s3-ddb")
        self.assertIsNone(config.store_id)

    def test_parse_with_no_fields(self) -> None:
        config = JupyterDeployStoreConfigV1()
        self.assertIsNone(config.store_type)
        self.assertIsNone(config.store_id)

    def test_parse_tolerates_extra_fields(self) -> None:
        config = JupyterDeployStoreConfigV1(**{"store-type": "s3-only", "extra-field": "value"})  # type: ignore
        self.assertEqual(config.store_type, "s3-only")

    def test_get_store_type_s3_only(self) -> None:
        config = JupyterDeployStoreConfigV1(**{"store-type": "s3-only"})  # type: ignore
        self.assertEqual(config.get_store_type(), StoreType.S3_ONLY)

    def test_get_store_type_s3_ddb(self) -> None:
        config = JupyterDeployStoreConfigV1(**{"store-type": "s3-ddb"})  # type: ignore
        self.assertEqual(config.get_store_type(), StoreType.S3_DDB)

    def test_get_store_type_invalid_raises(self) -> None:
        config = JupyterDeployStoreConfigV1(**{"store-type": "invalid"})  # type: ignore
        with self.assertRaises(InvalidStoreTypeError):
            config.get_store_type()

    def test_get_store_type_none_raises_value_error(self) -> None:
        config = JupyterDeployStoreConfigV1()
        with self.assertRaises(ValueError):
            config.get_store_type()

    def test_populate_by_name(self) -> None:
        config = JupyterDeployStoreConfigV1(store_type="s3-only", store_id="my-bucket")
        self.assertEqual(config.store_type, "s3-only")
        self.assertEqual(config.store_id, "my-bucket")


class TestRetrieveStoreConfig(unittest.TestCase):
    @patch("jupyter_deploy.handlers.base_project_handler.fs_utils.file_exists", return_value=False)
    def test_returns_none_when_file_missing(self, mock_exists: Mock) -> None:
        result = retrieve_store_config(Path("/mock/project"))
        self.assertIsNone(result)

    @patch("builtins.open")
    @patch("jupyter_deploy.handlers.base_project_handler.fs_utils.file_exists", return_value=True)
    @patch("jupyter_deploy.handlers.base_project_handler.yaml.safe_load")
    def test_returns_config_when_file_exists(self, mock_yaml_load: Mock, mock_exists: Mock, mock_open: Mock) -> None:
        mock_yaml_load.return_value = {"store-type": "s3-only", "store-id": "my-bucket"}
        result = retrieve_store_config(Path("/mock/project"))
        self.assertIsNotNone(result)
        self.assertEqual(result.store_type, "s3-only")  # type: ignore
        self.assertEqual(result.store_id, "my-bucket")  # type: ignore

    @patch("builtins.open")
    @patch("jupyter_deploy.handlers.base_project_handler.fs_utils.file_exists", return_value=True)
    @patch("jupyter_deploy.handlers.base_project_handler.yaml.safe_load")
    def test_returns_none_for_non_dict_content(self, mock_yaml_load: Mock, mock_exists: Mock, mock_open: Mock) -> None:
        mock_yaml_load.return_value = "not a dict"
        result = retrieve_store_config(Path("/mock/project"))
        self.assertIsNone(result)


class TestWriteStoreConfig(unittest.TestCase):
    @patch("jupyter_deploy.handlers.base_project_handler.fs_utils.write_yaml_file_with_comments")
    @patch("pathlib.Path.mkdir")
    def test_writes_config_with_both_fields(self, mock_mkdir: Mock, mock_write: Mock) -> None:
        write_store_config(Path("/mock/project"), store_type="s3-only", store_id="my-bucket")
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_write.assert_called_once()
        call_args = mock_write.call_args
        content = call_args[1]["content"] if "content" in call_args[1] else call_args[0][1]
        self.assertEqual(content["store-type"], "s3-only")
        self.assertEqual(content["store-id"], "my-bucket")

    @patch("jupyter_deploy.handlers.base_project_handler.fs_utils.write_yaml_file_with_comments")
    @patch("pathlib.Path.mkdir")
    def test_writes_config_excludes_none_fields(self, mock_mkdir: Mock, mock_write: Mock) -> None:
        write_store_config(Path("/mock/project"), store_type="s3-only")
        call_args = mock_write.call_args
        content = call_args[1]["content"] if "content" in call_args[1] else call_args[0][1]
        self.assertEqual(content["store-type"], "s3-only")
        self.assertNotIn("store-id", content)


class TestGetStoreTypeFromConfig(unittest.TestCase):
    """Test BaseProjectHandler.get_store_type_from_config_or_manifest via a handler instance."""

    def _make_manifest(self, store_type: str | None = None) -> JupyterDeployManifestV1:
        kwargs: dict = {
            "schema_version": 1,
            "template": {"name": "test", "engine": "terraform", "version": "1.0.0"},
        }
        if store_type is not None:
            kwargs["project_store"] = JupyterDeployProjectStoreV1(**{"store-type": store_type})  # type: ignore
        return JupyterDeployManifestV1(**kwargs)  # type: ignore

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_store_config")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_store_yaml_overrides_manifest(
        self, mock_retrieve_manifest: Mock, mock_tf_handler: Mock, mock_read_config: Mock
    ) -> None:
        mock_retrieve_manifest.return_value = self._make_manifest("s3-only")
        mock_read_config.return_value = JupyterDeployStoreConfigV1(store_type="s3-ddb")

        handler = ConfigHandler(display_manager=Mock())
        result = handler.get_store_type_from_config_or_manifest()
        self.assertEqual(result, StoreType.S3_DDB)

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_store_config")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_manifest_fallback(
        self, mock_retrieve_manifest: Mock, mock_tf_handler: Mock, mock_read_config: Mock
    ) -> None:
        mock_retrieve_manifest.return_value = self._make_manifest("s3-only")
        mock_read_config.return_value = None

        handler = ConfigHandler(display_manager=Mock())
        result = handler.get_store_type_from_config_or_manifest()
        self.assertEqual(result, StoreType.S3_ONLY)

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_store_config")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_returns_none_when_no_store_configured(
        self, mock_retrieve_manifest: Mock, mock_tf_handler: Mock, mock_read_config: Mock
    ) -> None:
        mock_retrieve_manifest.return_value = self._make_manifest()
        mock_read_config.return_value = None

        handler = ConfigHandler(display_manager=Mock())
        result = handler.get_store_type_from_config_or_manifest()
        self.assertIsNone(result)

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_store_config")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_store_yaml_with_none_store_type_falls_through(
        self, mock_retrieve_manifest: Mock, mock_tf_handler: Mock, mock_read_config: Mock
    ) -> None:
        mock_retrieve_manifest.return_value = self._make_manifest("s3-only")
        mock_read_config.return_value = JupyterDeployStoreConfigV1(store_type=None)

        handler = ConfigHandler(display_manager=Mock())
        result = handler.get_store_type_from_config_or_manifest()
        self.assertEqual(result, StoreType.S3_ONLY)


class TestGetStoreIdFromConfig(unittest.TestCase):
    """Test BaseProjectHandler.get_store_id_from_config via a handler instance."""

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_store_config")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_store_yaml_fallback(
        self, mock_retrieve_manifest: Mock, mock_tf_handler: Mock, mock_read_config: Mock
    ) -> None:
        manifest = JupyterDeployManifestV1(
            **{  # type: ignore
                "schema_version": 1,
                "template": {"name": "test", "engine": "terraform", "version": "1.0.0"},
            }
        )
        mock_retrieve_manifest.return_value = manifest
        mock_read_config.return_value = JupyterDeployStoreConfigV1(store_id="yaml-bucket")

        handler = ConfigHandler(display_manager=Mock())
        result = handler.get_store_id_from_config()
        self.assertEqual(result, "yaml-bucket")

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_store_config")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_returns_none_when_no_store_id(
        self, mock_retrieve_manifest: Mock, mock_tf_handler: Mock, mock_read_config: Mock
    ) -> None:
        manifest = JupyterDeployManifestV1(
            **{  # type: ignore
                "schema_version": 1,
                "template": {"name": "test", "engine": "terraform", "version": "1.0.0"},
            }
        )
        mock_retrieve_manifest.return_value = manifest
        mock_read_config.return_value = None

        handler = ConfigHandler(display_manager=Mock())
        result = handler.get_store_id_from_config()
        self.assertIsNone(result)

    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_store_config")
    @patch("jupyter_deploy.engine.terraform.tf_config.TerraformConfigHandler")
    @patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest")
    def test_store_yaml_with_none_store_id_returns_none(
        self, mock_retrieve_manifest: Mock, mock_tf_handler: Mock, mock_read_config: Mock
    ) -> None:
        manifest = JupyterDeployManifestV1(
            **{  # type: ignore
                "schema_version": 1,
                "template": {"name": "test", "engine": "terraform", "version": "1.0.0"},
            }
        )
        mock_retrieve_manifest.return_value = manifest
        mock_read_config.return_value = JupyterDeployStoreConfigV1(store_id=None)

        handler = ConfigHandler(display_manager=Mock())
        result = handler.get_store_id_from_config()
        self.assertIsNone(result)
