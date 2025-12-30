"""Deployment lifecycle management for E2E tests."""

from pytest_jupyter_deploy.cli import JDCli
from pytest_jupyter_deploy.suite_config import SuiteConfig


class EndToEndDeployment:
    """Represents a Jupyter-Deploy project for end to end testing."""

    def __init__(
        self,
        suite_config: SuiteConfig,
        deployment_timeout_seconds: int = 1800,
        teardown_timeout_seconds: int = 600,
    ) -> None:
        """Initialize the deployment manager.

        Args:
            suite_config: Suite configuration
            config_name: Configuration name to use (default: "base")
            deployment_timeout_seconds: Timeout in seconds for deployment (default: 1800)
            teardown_timeout_seconds: Timeout in seconds for teardown (default: 600)
        """
        self.suite_config = suite_config
        self.deployment_timeout_seconds = deployment_timeout_seconds
        self.teardown_timeout_seconds = teardown_timeout_seconds
        self.cli = JDCli(suite_config.suite_dir)
        self._is_deployed = False

    def prepare_sandbox_dir(self) -> None:
        """Retrieve the project, create a timestamp dir.

        The dir name will be '{cwd}/sandbox-e2e/template-name/YYYYMMDD-HHMMSS

        Raises:
            ValueError if the dir already exists
        """
        self.suite_config.load()
        project_dir = self.suite_config.project_dir

        # implement: remove the print, create the dir or raise an exception
        print(project_dir.absolute())

    def ensure_deployed(self) -> None:
        """Ensure the deployment is available, deploying if necessary."""
        if self._is_available():
            self._is_deployed = True
            return

        self.suite_config.load()

        # Initialize project
        self.cli.init(
            dir_name=self.suite_config.project_dir,
            engine=self.suite_config.template_engine,
            provider=self.suite_config.template_provider,
            infra=self.suite_config.template_infrastructure,
            name=self.suite_config.template_base_name,
        )

        # Copy the variables.yaml
        self.suite_config.prepare_configuration()

        # Call the CLI commands
        self.cli.config()
        self.cli.up(timeout=self.deployment_timeout_seconds)

        self._is_deployed = True

    def ensure_destroyed(self) -> None:
        """Ensure the deployment is torn down."""
        if not self._is_deployed:
            return

        try:
            self.cli.down(timeout=self.teardown_timeout_seconds)
        finally:
            self._is_deployed = False

    def _is_available(self) -> bool:
        """Check if deployment is available and valid.

        Returns:
            True if deployment exists and is valid, False otherwise
        """
        # for now
        return True
