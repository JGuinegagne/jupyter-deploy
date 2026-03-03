from abc import ABC, abstractmethod

from jupyter_deploy.engine.supervised_execution import DisplayManager
from jupyter_deploy.provider.store.store_manager import StoreInfo


class EngineStoreAccessManager(ABC):
    """Abstract interface for managing engine-specific remote store access."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if remote store access is configured for this engine."""

    @abstractmethod
    def configure(self, store_info: StoreInfo, project_id: str, display_manager: DisplayManager) -> None:
        """Configure the engine to use the remote store.

        Raises:
            RuntimeError: If configuration fails.
        """

    @abstractmethod
    def unconfigure(self) -> None:
        """Remove the remote store configuration."""
