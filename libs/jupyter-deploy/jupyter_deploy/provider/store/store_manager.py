from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from jupyter_deploy.engine.supervised_execution import DisplayManager


class StoreInfo(BaseModel):
    """Information about a backup store."""

    store_type: str
    store_id: str
    location: str


class ProjectSummary(BaseModel):
    """Summary of a project in the backup store."""

    project_id: str
    last_modified: datetime
    file_count: int


class SyncResult(BaseModel):
    """Result of a sync operation."""

    uploaded: int
    deleted: int
    unchanged: int


class StoreManager(ABC):
    """Abstract interface for a remote backup store manager."""

    @abstractmethod
    def ensure_store(self, display_manager: DisplayManager) -> StoreInfo:
        """Ensure all components of the backup store exist, creating them if necessary.

        Returns:
            StoreInfo with details about the store.
        """

    @abstractmethod
    def push(self, project_path: Path, project_id: str, display_manager: DisplayManager) -> SyncResult:
        """Upload local project files to the remote backup store.

        Returns:
            SyncResult with counts of uploaded, deleted, and unchanged files.
        """

    @abstractmethod
    def pull(self, project_id: str, dest_path: Path, display_manager: DisplayManager) -> SyncResult:
        """Download project files from the remote backup store to a local path.

        Returns:
            SyncResult with counts of downloaded files.
        """

    @abstractmethod
    def list_projects(self, display_manager: DisplayManager) -> list[ProjectSummary]:
        """Return a list of ProjectSummaries for all projects in the backup store."""

    @abstractmethod
    def delete_project(self, project_id: str, display_manager: DisplayManager) -> None:
        """Delete all content of a project from the backup store."""
