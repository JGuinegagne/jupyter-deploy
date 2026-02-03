from jupyter_deploy.engine.engine_down import EngineDownHandler
from jupyter_deploy.engine.enum import EngineType
from jupyter_deploy.engine.supervised_execution import TerminalHandler
from jupyter_deploy.engine.terraform import tf_down
from jupyter_deploy.handlers.base_project_handler import BaseProjectHandler


class DownHandler(BaseProjectHandler):
    _handler: EngineDownHandler

    def __init__(self, terminal_handler: TerminalHandler | None = None) -> None:
        """Base class to manage the down command of a jupyter-deploy project."""
        super().__init__()

        if self.engine == EngineType.TERRAFORM:
            self._handler = tf_down.TerraformDownHandler(
                project_path=self.project_path,
                project_manifest=self.project_manifest,
                command_history_handler=self.command_history_handler,
                terminal_handler=terminal_handler,
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
