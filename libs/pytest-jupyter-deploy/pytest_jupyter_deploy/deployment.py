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
        self._cli: JDCli | None = None
        self._is_deployed = False
        self._owns_project_resources = False

    @property
    def cli(self) -> JDCli:
        """Get the CLI instance, initializing it if needed.

        The CLI is initialized with the project directory after suite_config is loaded.
        """
        if self._cli is None:
            # Ensure suite_config is loaded so project_dir is available
            self.suite_config.load()
            self._cli = JDCli(self.suite_config.project_dir)
        return self._cli

    def prepare_sandbox_dir(self) -> None:
        """Retrieve the project, create a timestamp dir.

        The dir name will be '{cwd}/{SANDBOX_E2E_DIR}/template-name/YYYYMMDD-HHMMSS

        Raises:
            ValueError if the dir already exists
        """
        self.suite_config.load()
        project_dir = self.suite_config.project_dir

        if project_dir.exists():
            raise ValueError(f"Project directory already exists: {project_dir.absolute()}")

        project_dir.mkdir(parents=True, exist_ok=False)

    def ensure_deployed(self) -> None:
        """Ensure that the project is deployed."""
        self.suite_config.load()

        # first, ensure the project exists at the target dir
        if self.suite_config.references_existing_project():
            if not self.suite_config.project_dir.exists():
                raise RuntimeError(
                    "Cannot run integration tests; referenced project does not exist "
                    f"at path: {self.suite_config.project_dir.absolute()}"
                )
        else:
            if not self.suite_config.project_dir.exists():
                self._deploy_e2e_project()

    def ensure_host_running(self) -> None:
        """Call host status, attempts to call host start if not running."""

        if not self._is_host_running():
            # TODO: attempt to start host
            raise RuntimeError("Host is not running")

    def ensure_host_stopped(self) -> None:
        """Call host status, attempts to call host stop if running"""

        if not self._is_host_stopped():
            # TODO: attempt to stop host
            raise RuntimeError("Host is not stopped")

    def ensure_server_running(self) -> None:
        """Call server status, attempts to call server start if it indicates not available."""

        if not self._is_server_available():
            # attempts to restart
            self.cli.run_command(["jupyter-deploy", "server", "restart"])

            if not self._is_server_available():
                raise RuntimeError("Jupyter Server is not running")

    def ensure_server_stopped(self) -> None:
        """Call server status, attempts to call server stop if it indicates running."""

        if not self._is_server_stopped():
            # TODO: attempt to stop server
            raise RuntimeError("Jupyter Server is not stopped")

    def _deploy_e2e_project(self) -> None:
        """Calls jd init, jd config, jd up."""

        # Initialize project
        engine = self.suite_config.template_engine.value
        provider = self.suite_config.template_provider
        infrastructure = self.suite_config.template_infrastructure
        base_name = self.suite_config.template_base_name

        self.cli.run_command(
            [
                "jupyter-deploy",
                "init",
                "--engine",
                engine,
                "--provider",
                provider,
                "--infrastructure",
                infrastructure,
                "--template",
                base_name,
            ]
        )

        # Copy the variables.yaml
        self.suite_config.prepare_configuration()

        # Call the CLI commands
        self.cli.run_command(["jupyter-deploy", "config"])
        self.cli.run_command(["jupyter-deploy", "up", "-y"])
        self._is_deployed = True

    def ensure_destroyed(self) -> None:
        """Ensure the deployment is torn down."""
        if not self._is_deployed:
            return

        try:
            self.cli.run_command(["jupyter-deploy", "down", "-y"])
        finally:
            self._is_deployed = False

    def _is_host_running(self) -> bool:
        """Return True if the host is running, False otherwise."""
        status = self.cli.get_host_status()
        return status == "running"

    def _is_host_stopped(self) -> bool:
        """Return True if the host is stopped, False otherwise."""
        status = self.cli.get_host_status()
        return status == "stopped"

    def _is_server_available(self) -> bool:
        """Return True if the server is available (IN_SERVICE), False otherwise."""
        status = self.cli.get_server_status()
        return status == "IN_SERVICE"

    def _is_server_stopped(self) -> bool:
        """Return True if the server is stopped (STOPPED), False otherwise."""
        status = self.cli.get_server_status()
        return status == "STOPPED"
