import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from jupyter_deploy.engine.terraform.tf_constants import TF_BACKEND_FILENAME, TF_INIT_CMD, TF_INIT_MIGRATE_CMD_OPTIONS
from jupyter_deploy.engine.terraform.tf_store_access import TerraformStoreAccessManager
from jupyter_deploy.exceptions import ProjectStoreAccessConfigurationError
from jupyter_deploy.provider.store.store_manager import StoreInfo


class TestTerraformStoreAccessManager(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.engine_dir = Path(self._tmpdir.name) / "engine"
        self.engine_dir.mkdir()
        self.manager = TerraformStoreAccessManager(
            engine_dir_path=self.engine_dir,
        )
        self.store_info = StoreInfo(
            store_type="s3-ddb",
            store_id="jupyter-deploy-abc123",
            location="us-west-2",
        )

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_is_configured_false(self) -> None:
        self.assertFalse(self.manager.is_configured())

    def test_is_configured_true(self) -> None:
        (self.engine_dir / TF_BACKEND_FILENAME).write_text("backend config")
        self.assertTrue(self.manager.is_configured())

    @patch("jupyter_deploy.engine.terraform.tf_store_access.cmd_utils.run_cmd_and_capture_output")
    def test_configure_writes_backend_file(self, mock_run: Mock) -> None:
        display = Mock()
        self.manager.configure(self.store_info, "tf-aws-ec2-base-dep1", display)

        content = (self.engine_dir / TF_BACKEND_FILENAME).read_text()
        self.assertIn('bucket         = "jupyter-deploy-abc123"', content)
        self.assertIn('key            = "tf-aws-ec2-base-dep1/terraform.tfstate"', content)
        self.assertIn('region         = "us-west-2"', content)
        self.assertIn('dynamodb_table = "jupyter-deploy-projects"', content)
        self.assertIn('backend "s3"', content)

    @patch("jupyter_deploy.engine.terraform.tf_store_access.cmd_utils.run_cmd_and_capture_output")
    def test_configure_uses_store_info_location(self, mock_run: Mock) -> None:
        store_info = StoreInfo(store_type="s3-ddb", store_id="bucket-1", location="eu-west-1")
        display = Mock()
        self.manager.configure(store_info, "proj-1", display)

        content = (self.engine_dir / TF_BACKEND_FILENAME).read_text()
        self.assertIn('region         = "eu-west-1"', content)

    @patch("jupyter_deploy.engine.terraform.tf_store_access.cmd_utils.run_cmd_and_capture_output")
    def test_configure_runs_migrate_command(self, mock_run: Mock) -> None:
        display = Mock()
        self.manager.configure(self.store_info, "proj-1", display)

        expected_cmd = TF_INIT_CMD + TF_INIT_MIGRATE_CMD_OPTIONS
        mock_run.assert_called_once_with(expected_cmd, exec_dir=self.engine_dir)

    @patch("jupyter_deploy.engine.terraform.tf_store_access.cmd_utils.run_cmd_and_capture_output")
    def test_configure_displays_info_message(self, mock_run: Mock) -> None:
        display = Mock()
        self.manager.configure(self.store_info, "proj-1", display)

        display.info.assert_called_once()

    @patch("jupyter_deploy.engine.terraform.tf_store_access.cmd_utils.run_cmd_and_capture_output")
    def test_configure_rollback_on_migration_failure(self, mock_run: Mock) -> None:
        mock_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd="terraform init")
        display = Mock()

        with self.assertRaises(ProjectStoreAccessConfigurationError):
            self.manager.configure(self.store_info, "proj-1", display)

        self.assertFalse((self.engine_dir / TF_BACKEND_FILENAME).exists())

    def test_unconfigure(self) -> None:
        backend_path = self.engine_dir / TF_BACKEND_FILENAME
        backend_path.write_text("backend config")
        self.assertTrue(backend_path.exists())
        self.manager.unconfigure()
        self.assertFalse(backend_path.exists())

    def test_unconfigure_noop(self) -> None:
        self.manager.unconfigure()  # should not raise
