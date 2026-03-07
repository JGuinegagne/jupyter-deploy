from jupyter_deploy.engine.supervised_execution import DisplayManager
from jupyter_deploy.enum import StoreType
from jupyter_deploy.provider.store.store_manager import ProjectDetails, ProjectSummary
from jupyter_deploy.provider.store.store_manager_factory import StoreManagerFactory


class ProjectsHandler:
    """Handler for managing projects in a remote store.

    Operates at the account level (not project-specific), so it does NOT
    extend BaseProjectHandler.
    """

    def __init__(self, display_manager: DisplayManager, store_type: StoreType, store_id: str | None = None) -> None:
        self.display_manager = display_manager
        self._store_manager = StoreManagerFactory.get_manager(store_type=store_type, store_id=store_id)

    @property
    def store_id(self) -> str:
        """Return the resolved store ID. Triggers discovery if not yet resolved."""
        return self._store_manager.resolve_store().store_id

    def list_projects(self) -> list[ProjectSummary]:
        """Return the list of project summaries in the store."""
        return self._store_manager.list_projects(self.display_manager)

    def show_project(self, project_id: str) -> ProjectDetails:
        """Return the details for a specific project as saved in the store.

        Raises:
            ProjectNotFoundInStoreError: If the project is not found in the store.
        """
        return self._store_manager.get_project(project_id, self.display_manager)

    def delete_project(self, project_id: str) -> None:
        """Removes a project from the store."""
        self._store_manager.delete_project(project_id, self.display_manager)
