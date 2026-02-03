from pathlib import Path

from jupyter_deploy.engine.engine_up import EngineUpHandler
from jupyter_deploy.engine.enum import EngineType
from jupyter_deploy.engine.supervised_execution import CompletionContext, TerminalHandler
from jupyter_deploy.engine.terraform import tf_up
from jupyter_deploy.handlers.base_project_handler import BaseProjectHandler


class UpHandler(BaseProjectHandler):
    _handler: EngineUpHandler

    def __init__(self, terminal_handler: TerminalHandler | None = None) -> None:
        """Base class to manage the up command of a jupyter-deploy project."""
        super().__init__()

        if self.engine == EngineType.TERRAFORM:
            self._handler = tf_up.TerraformUpHandler(
                project_path=self.project_path,
                project_manifest=self.project_manifest,
                command_history_handler=self.command_history_handler,
                terminal_handler=terminal_handler,
            )
        else:
            raise NotImplementedError(f"UpHandler implementation not found for engine: {self.engine}")

    def get_default_config_filename(self) -> str:
        """Get the default config file name for the current engine."""
        return self._handler.get_default_config_filename()

    def get_config_file_path(self, config_filename: str | None = None) -> Path:
        """Return the full path to the config file.

        Raises:
            FileNotFoundError: If the config file does not exist.
        """
        if config_filename is None:
            config_filename = self.get_default_config_filename()

        config_file_path = self._handler.engine_dir_path / config_filename

        if not config_file_path.exists():
            raise FileNotFoundError(
                f"Config file '{config_filename}' not found in {self.project_path}. "
                f"If you have not yet generated a config file for your current project, "
                f'please run "jd config" from the project directory first.'
            )

        return config_file_path

    def apply(self, config_file_path: Path, auto_approve: bool = False) -> CompletionContext | None:
        """Apply the infrastructure changes defined in the config file.

        Args:
            config_file_path: The path to the config file.
            auto_approve: Whether to auto-approve the changes without prompting.

        Returns:
            CompletionContext with completion summary, or None if not available.
        """
        return self._handler.apply(config_file_path, auto_approve)
