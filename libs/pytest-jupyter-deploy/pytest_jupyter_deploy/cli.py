"""CLI wrapper for jupyter-deploy commands."""

import subprocess
from pathlib import Path


class JDCli:
    """Wrapper for jupyter-deploy CLI commands."""

    def __init__(self, working_dir: Path) -> None:
        """Initialize CLI wrapper.

        Args:
            working_dir: Working directory for CLI commands
        """
        self.working_dir = working_dir

    def init(self, dir_name: Path | str, engine: str, provider: str, infra: str, name: str) -> None:
        """Initialize a deployment project.

        Args:
            dir_name: Directory to initialize
            engine: Engine type (e.g., "terraform")
            provider: Cloud provider (e.g., "aws")
            infra: Infrastructure type (e.g., "ec2")
            name: Template name (e.g., "base")
        """
        cmd = [
            "jd",
            "init",
            "-E",
            engine,
            "-P",
            provider,
            "-I",
            infra,
            "-T",
            name,
            str(dir_name),
        ]
        self._run_command(cmd, cwd=None, description="Initialize deployment project")

    def config(self) -> None:
        """Configure the deployment."""
        cmd = ["jd", "config"]
        self._run_command(cmd, cwd=self.working_dir, description="Configure deployment")

    def up(self, timeout: int | None = None) -> None:
        """Deploy infrastructure.

        Args:
            timeout: Command timeout in seconds
        """
        cmd = ["jd", "up"]
        self._run_command(cmd, cwd=self.working_dir, description="Deploy infrastructure", timeout=timeout)

    def down(self, timeout: int | None = None) -> None:
        """Tear down infrastructure.

        Args:
            timeout: Command timeout in seconds
        """
        cmd = ["jd", "down"]
        self._run_command(cmd, cwd=self.working_dir, description="Tear down infrastructure", timeout=timeout)

    def show(self) -> None:
        """Display deployment information.

        Args:
            info: Display core project and template information
            outputs: Display outputs information
            variables: Display variables information
        """
        cmd = ["jd", "show"]
        self._run_command(cmd, cwd=self.working_dir, description="Display deployment info")

    def _run_command(
        self,
        cmd: list[str],
        cwd: Path | None,
        description: str,
        timeout: int | None = None,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        """Run a command and handle errors.

        Args:
            cmd: Command to run
            cwd: Working directory for command
            description: Human-readable description for error messages
            timeout: Command timeout in seconds
            capture_output: Whether to capture stdout/stderr

        Returns:
            CompletedProcess instance

        Raises:
            subprocess.CalledProcessError: If command fails
            subprocess.TimeoutExpired: If command times out
        """
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                check=True,
                timeout=timeout,
                capture_output=capture_output,
                text=True,
            )
            return result
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to {description}: {e}") from e
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Timeout while trying to {description}") from e
