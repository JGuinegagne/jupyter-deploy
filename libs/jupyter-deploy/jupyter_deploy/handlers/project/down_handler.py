from dataclasses import dataclass
from datetime import UTC, datetime

import yaml

from jupyter_deploy import constants
from jupyter_deploy.engine.engine_down import EngineDownHandler
from jupyter_deploy.engine.enum import EngineType
from jupyter_deploy.engine.supervised_execution import DisplayManager
from jupyter_deploy.engine.terraform import tf_down
from jupyter_deploy.handlers.base_project_handler import BaseProjectHandler
from jupyter_deploy.provider.store.store_manager_factory import StoreManagerFactory


@dataclass
class StorePushResult:
    project_id: str
    store_type: str
    store_id: str | None


class DownHandler(BaseProjectHandler):
    _handler: EngineDownHandler

    def __init__(self, display_manager: DisplayManager) -> None:
        """Base class to manage the down command of a jupyter-deploy project."""
        super().__init__(display_manager=display_manager)

        if self.engine == EngineType.TERRAFORM:
            self._handler = tf_down.TerraformDownHandler(
                project_path=self.project_path,
                project_manifest=self.project_manifest,
                command_history_handler=self.command_history_handler,
                display_manager=display_manager,
            )
        else:
            raise NotImplementedError(f"DownHandler implementation not found for engine: {self.engine}")

    def get_persisting_resources(self) -> list[str]:
        """Return the list of resource identifiers that will persist after destroy."""
        return self._handler.get_persisting_resources()

    def destroy(self, auto_approve: bool = False) -> None:
        """Destroy the infrastructure resources.

        Args:
            auto_approve: Whether to auto-approve the destruction without prompting.
        """
        return self._handler.destroy(auto_approve)

    def push_to_store(self) -> StorePushResult | None:
        """Push a final snapshot with a deletion marker to the remote store.

        Reads store-type, store-id, and project-id from .jd/store.yaml.
        If any are missing, skips silently (no-op).

        Returns:
            StorePushResult if the push succeeded, or None if skipped.
        """
        store_type = self.get_store_type_from_config_or_manifest()
        if not store_type:
            return None

        project_id = self.get_project_id_from_config()
        if not project_id:
            return None

        store_id = self.get_store_id_from_config()

        store_manager = StoreManagerFactory.get_manager(store_type=store_type, store_id=store_id)

        # Write deletion marker with user identity
        user_identity = store_manager.get_user_identity()
        self._write_deletion_marker(user_identity)

        store_info = store_manager.resolve_store()
        store_manager.push(self.project_path, project_id, self.display_manager)
        return StorePushResult(project_id=project_id, store_type=store_type.value, store_id=store_info.store_id)

    def _write_deletion_marker(self, user: str) -> None:
        """Write .jd/deletion.yaml with user identity and timestamp."""
        jd_dir = self.project_path / constants.JD_DIR
        jd_dir.mkdir(parents=True, exist_ok=True)
        marker_path = jd_dir / constants.DELETION_MARKER_FILENAME
        content = {
            "user": user,
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        marker_path.write_text(yaml.dump(content, default_flow_style=False))
