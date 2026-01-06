"""Deployment lifecycle management for E2E tests."""

import time

from pytest_jupyter_deploy.cli import JDCli, JDCliError
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

        self.ensure_deployed()

        if not self._is_host_running():
            self.cli.run_command(["jupyter-deploy", "host", "start"])

            if not self._is_host_running():
                raise RuntimeError("Host failed to start")

    def ensure_host_stopped(self) -> None:
        """Call host status, attempts to call host stop if running"""

        self.ensure_deployed()

        if not self._is_host_stopped():
            self.cli.run_command(["jupyter-deploy", "host", "stop"])

            if not self._is_host_stopped():
                raise RuntimeError("Host is not stopped")

    def ensure_server_running(self) -> None:
        """Ensure the Jupyter server is running.

        This method attempts to get the server into a running state by:
        1. Checking if server is already available (fast path)
        2. If server check fails (host not running), start the host first
        3. If server is not available but host is running, restart the server

        Raises:
            RuntimeError: If the server cannot be made available
        """
        self.ensure_deployed()

        # Step 1: Try to check if server is already available (fast path)
        try:
            if self._is_server_available():
                return
        except JDCliError:
            # Step 2: Check if host is running and start it if needed
            if not self._is_host_running():
                self.cli.run_command(["jupyter-deploy", "host", "start"])

                if not self._is_host_running():
                    raise RuntimeError("Host failed to start") from None

            # Wait for SSM agent to register after host start
            # TODO: this is too aws-specific, we should gate by a flag
            self._wait_for_ssm_ready()

        # Step 3: Attempt to restart the server
        self.cli.run_command(["jupyter-deploy", "server", "restart"])
        if not self._is_server_available():
            raise RuntimeError("Jupyter Server failed to start after restart")

    def ensure_server_stopped_and_host_is_running(self) -> None:
        """Ensure the host is running and the Jupyter server is stopped.

        This method attempts to ensure the server is stopped by:
        1. Checking if server is already stopped (fast path)
        2. If server check fails (host not running), ensure host is running and retry
        3. If server is not stopped, stop it

        Raises:
            RuntimeError: If the host cannot be started or server cannot be stopped
        """
        self.ensure_deployed()

        # Step 1: Try to check if server is already stopped (fast path)
        try:
            if self._is_server_stopped():
                return
        except JDCliError:
            # Server status check failed - likely host is not running
            # Ensure host is running
            self.ensure_host_running()

            # Retry server status check
            if self._is_server_stopped():
                return

        # Step 2: Server is not stopped - attempt to stop it
        self.cli.run_command(["jupyter-deploy", "server", "stop"])

        # Step 3: Verify server stopped successfully
        if not self._is_server_stopped():
            raise RuntimeError("Jupyter Server failed to stop")

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

    def _wait_for_ssm_ready(self, max_retries: int = 3) -> None:
        """Wait for SSM agent to be ready after host state change.

        SSM agent needs time to register with AWS Systems Manager after
        the EC2 instance starts or restarts. This method polls until SSM
        is ready or max retries is reached.

        Args:
            max_retries: Maximum number of retry attempts (default: 3)

        Raises:
            JDCliError: If SSM doesn't become ready within max_retries
        """
        for attempt in range(max_retries):
            try:
                # Try a simple server status check to verify SSM is ready
                self.cli.get_server_status()
                return  # Success - SSM is ready
            except JDCliError as e:
                error_str = str(e)
                if "SSM:DescribeInstanceInformation returned an empty list" in error_str:
                    if attempt < max_retries - 1:
                        # Wait with linear backoff: 1s, 2s, 3s (total: 6s)
                        delay = 1 + attempt
                        time.sleep(delay)
                    else:
                        # Max retries exceeded
                        raise
                else:
                    # Different error - don't retry
                    raise
