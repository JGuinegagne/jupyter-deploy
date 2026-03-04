import subprocess
from pathlib import Path

from jupyter_deploy import cmd_utils
from jupyter_deploy.engine.engine_store_access import EngineStoreAccessManager
from jupyter_deploy.engine.supervised_execution import DisplayManager
from jupyter_deploy.engine.terraform.tf_constants import (
    TF_BACKEND_FILENAME,
    TF_INIT_CMD,
    TF_INIT_MIGRATE_CMD_OPTIONS,
)
from jupyter_deploy.exceptions import ProjectStoreAccessConfigurationError
from jupyter_deploy.provider.store.store_manager import StoreInfo

_BACKEND_TEMPLATE = """\
terraform {{
  backend "s3" {{
    bucket         = "{store_id}"
    key            = "{project_id}/terraform.tfstate"
    region         = "{region}"
    dynamodb_table = "jupyter-deploy-projects"
  }}
}}
"""


class TerraformStoreAccessManager(EngineStoreAccessManager):
    def __init__(self, engine_dir_path: Path) -> None:
        self.engine_dir_path = engine_dir_path

    def is_configured(self) -> bool:
        return (self.engine_dir_path / TF_BACKEND_FILENAME).exists()

    def configure(self, store_info: StoreInfo, project_id: str, display_manager: DisplayManager) -> None:
        backend_path = self.engine_dir_path / TF_BACKEND_FILENAME
        content = _BACKEND_TEMPLATE.format(
            store_id=store_info.store_id,
            project_id=project_id,
            region=store_info.location,
        )
        backend_path.write_text(content)

        display_manager.info("Migrating state to remote backend...")
        try:
            migrate_cmd = TF_INIT_CMD + TF_INIT_MIGRATE_CMD_OPTIONS
            cmd_utils.run_cmd_and_capture_output(migrate_cmd, exec_dir=self.engine_dir_path)
        except subprocess.CalledProcessError as e:
            backend_path.unlink(missing_ok=True)
            raise ProjectStoreAccessConfigurationError(
                "Backend state migration failed. Remote store configuration has been rolled back."
            ) from e

    def unconfigure(self) -> None:
        (self.engine_dir_path / TF_BACKEND_FILENAME).unlink(missing_ok=True)
