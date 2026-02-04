from abc import ABC, abstractmethod
from pathlib import Path

from jupyter_deploy.engine.enum import EngineType
from jupyter_deploy.engine.supervised_execution import CompletionContext


class EngineUpHandler(ABC):
    def __init__(self, project_path: Path, engine: EngineType, engine_dir_path: Path) -> None:
        """Instantiate the base handler for `jd up` command."""
        self.project_path = project_path
        self.engine_dir_path = engine_dir_path
        self.engine = engine

    @abstractmethod
    def get_default_config_filename(self) -> str:
        pass

    @abstractmethod
    def apply(self, config_file_path: Path, auto_approve: bool = False) -> CompletionContext | None:
        """Apply the infrastructure changes.

        Returns:
            CompletionContext with completion summary, or None if not available
        """
        pass
