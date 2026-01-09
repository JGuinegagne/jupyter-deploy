"""CLI wrapper for jupyter-deploy commands."""

import re
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import pexpect
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

    def get_allowlisted_users(self) -> list[str]:
        """Return the list of allowlisted users, or empty list if none.

        Raises:
            JDCliError: If command fails
        """
        result = self.run_command(["jupyter-deploy", "users", "list"])

        # Parse output format: "Allowlisted usernames: user1, user2, user3"
        # or "Allowlisted usernames: None"
        # Handle multi-line output by taking the last line with a colon
        lines = result.stdout.strip().split("\n")
        for line in reversed(lines):
            if ":" in line:
                users_str = line.split(":", 1)[1].strip()
                # Check if the value after the colon is exactly "None"
                if users_str == "None":
                    return []
                # Split by comma and strip whitespace
                return [user.strip() for user in users_str.split(",") if user.strip()]

        # No line with colon found
        return []

    def get_allowlisted_teams(self) -> list[str]:
        """Return the list of allowlisted team names, or empty list if none.

        Raises:
            JDCliError: If command fails
        """
        result = self.run_command(["jupyter-deploy", "teams", "list"])

        # Parse output format: "Allowlisted teams: team1, team2, team3"
        # or "Allowlisted teams: None"
        # Handle multi-line output by taking the last line with a colon
        lines = result.stdout.strip().split("\n")
        for line in reversed(lines):
            if ":" in line:
                teams_str = line.split(":", 1)[1].strip()
                # Check if the value after the colon is exactly "None"
                if teams_str == "None":
                    return []
                # Split by comma and strip whitespace
                return [team.strip() for team in teams_str.split(",") if team.strip()]

        # No line with colon found
        return []

    def get_allowlisted_org(self) -> str | None:
        """Return the allowlisted organization, or None if none set.

        Raises:
            JDCliError: If command fails
        """
        result = self.run_command(["jupyter-deploy", "organization", "get"])

        # Parse output format: "Allowlisted organization: org_name"
        # or "Allowlisted organization: None"
        # Handle multi-line output by taking the last line with a colon
        lines = result.stdout.strip().split("\n")
        for line in reversed(lines):
            if ":" in line:
                org_str = line.split(":", 1)[1].strip()
                # Check if the value after the colon is exactly "None"
                if org_str == "None":
                    return None
                return org_str

        # No line with colon found
        return None

    @contextmanager
    def spawn_interactive_session(
        self,
        command: str,
        timeout: int = 30,
        encoding: str = "utf-8",
    ) -> Generator[pexpect.spawn, None, None]:
        """Spawn an interactive command session using pexpect.

        This context manager handles the lifecycle of a pexpect spawned process,
        ensuring proper cleanup even if the test fails.

        Args:
            command: Command to spawn (e.g., "jupyter-deploy host connect")
            timeout: Default timeout in seconds for expect operations
            encoding: Character encoding for the session

        Yields:
            pexpect.spawn instance for interacting with the session

        Example:
            with cli.spawn_interactive_session("jupyter-deploy host connect") as session:
                session.expect("Starting SSM session")
                session.sendline("whoami")
                session.expect("ssm-user")
        """
        child: pexpect.spawn | None = None
        try:
            child = pexpect.spawn(
                command,
                cwd=str(self.project_dir),
                timeout=timeout,
                encoding=encoding,
            )
            yield child
        finally:
            # Ensure the child process is terminated
            if child is not None and child.isalive():
                child.terminate(force=True)

    def parse_log_entries_from_output(self, output: str, line_start_pattern: str = "[") -> list[str]:
        """Return List of log entry lines from jd server logs using a specific line-start pattern.

        The CLI formats logs output with separator lines (e.g., "─── stderr ───").
        This method extracts the actual log entry lines between these separators.

        Args:
            output: The stdout from a logs command (e.g., "jupyter-deploy server logs")
            line_start_pattern: Pattern that log entry lines start with (default: "[")
                               Only lines starting with this pattern are counted as log entries.

        Example:
            result = cli.run_command(["jupyter-deploy", "server", "logs", "--", "--tail", "5"])
            log_entries = cli.parse_log_entries_from_output(result.stdout)
            assert len(log_entries) == 5
        """
        lines = output.splitlines()
        in_log_section = False
        log_entries: list[str] = []

        for line in lines:
            # Check if this is a separator line (contains only dashes, spaces, and optionally "stderr"/"stdout")
            is_separator = line.strip() and all(c in "─ sterdiou" for c in line)

            if is_separator and ("stderr" in line or "stdout" in line):
                # Start of a log section
                in_log_section = True
                continue
            elif is_separator and in_log_section:
                # End of log section (bottom separator)
                break
            elif in_log_section and line.strip():
                # Count lines that start with the specified pattern
                # These are actual log entries (some may be wrapped across multiple lines)
                if line.strip().startswith(line_start_pattern):
                    log_entries.append(line)

        return log_entries
