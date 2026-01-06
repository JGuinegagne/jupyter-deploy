"""CLI wrapper for jupyter-deploy commands."""

import re
import subprocess
from pathlib import Path

from jupyter_deploy import cmd_utils as jd_cmd_utils


class JDCliError(RuntimeError):
    pass


class JDCliTimeoutError(RuntimeError):
    pass


class JDCli:
    """Wrapper for jupyter-deploy CLI commands."""

    def __init__(self, project_dir: Path) -> None:
        """Initialize CLI wrapper."""
        self.project_dir = project_dir

    def run_command(
        self,
        cmd: list[str],
        timeout_seconds: int | None = None,
        capture_output: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run a command from the project directory.

        Args:
            cmd: Command to run
            cwd: Working directory for command
            timeout_seconds: Command timeout in seconds
            capture_output: Whether to capture stdout/stderr

        Returns:
            CompletedProcess instance

        Raises:
            JDCliError: If command fails
            JDCliTimeoutError: If command times out
        """
        with jd_cmd_utils.switch_dir(self.project_dir):
            try:
                result = subprocess.run(
                    cmd,
                    check=True,
                    timeout=timeout_seconds,
                    capture_output=capture_output,
                    text=True,
                )
                return result
            except subprocess.CalledProcessError as e:
                error_msg = f"Failed to run '{cmd}': Command '{e.cmd}' returned non-zero exit status {e.returncode}."
                if e.stdout:
                    error_msg += f"\nStdout: {e.stdout}"
                if e.stderr:
                    error_msg += f"\nStderr: {e.stderr}"
                raise JDCliError(error_msg) from e
            except subprocess.TimeoutExpired as e:
                raise JDCliTimeoutError(f"Timeout while trying to run '{cmd}") from e

    def get_host_status(self) -> str:
        """Get the host status string.

        Returns:
            Host status string (e.g., "running", "stopped", "pending")

        Raises:
            JDCliError: If command fails
            ValueError: If status cannot be parsed
        """
        result = self.run_command(["jupyter-deploy", "host", "status"])

        # Parse output for line "Jupyter host status: <status>"
        for line in result.stdout.splitlines():
            if line.startswith("Jupyter host status:"):
                # Extract status after the colon and color codes
                status = line.split(":", 1)[1].strip()
                # Remove ANSI color codes if present
                status = re.sub(r"\x1b\[[0-9;]*m", "", status)
                return status.lower()

        raise ValueError("Could not parse host status from command output")

    def get_server_status(self) -> str:
        """Get the server status string.

        Returns:
            Server status string (e.g., "IN_SERVICE", "STOPPED", "INITIALIZING")

        Raises:
            JDCliError: If command fails
            ValueError: If status cannot be parsed
        """
        result = self.run_command(["jupyter-deploy", "server", "status"])

        # Parse output for line "Jupyter server status: <status>"
        for line in result.stdout.splitlines():
            if line.startswith("Jupyter server status:"):
                # Extract status after the colon and color codes
                status = line.split(":", 1)[1].strip()
                # Remove ANSI color codes if present
                status = re.sub(r"\x1b\[[0-9;]*m", "", status)
                return status

        raise ValueError("Could not parse server status from command output")

    def get_jupyterlab_url(self) -> str:
        """Get the JupyterLab URL from the 'jd open' command output.

        This does not actually open the browser, but captures the URL that would be opened.

        Returns:
            JupyterLab URL string

        Raises:
            JDCliError: If command fails
            ValueError: If URL cannot be parsed
        """
        # Run the open command but don't actually open the browser
        # The output contains: "Opening Jupyter app at: {url}"
        result = self.run_command(["jupyter-deploy", "open"])

        # Parse output for the URL line
        for line in result.stdout.splitlines():
            if "Opening Jupyter app at:" in line:
                # Extract URL after "Opening Jupyter app at:"
                url = line.split("Opening Jupyter app at:", 1)[1].strip()
                # Remove ANSI color codes if present
                url = re.sub(r"\x1b\[[0-9;]*m", "", url)
                if url.startswith("http"):
                    return url

        raise ValueError("Could not parse JupyterLab URL from command output")
