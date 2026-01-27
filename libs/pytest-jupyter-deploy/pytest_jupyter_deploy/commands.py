"""Command execution utilities for E2E tests."""

import subprocess

from pytest_jupyter_deploy.cli import JDCliError
from pytest_jupyter_deploy.deployment import EndToEndDeployment


def verify_server_command_fails(
    e2e_deployment: EndToEndDeployment,
    command_args: list[str],
    expected_returncode: int,
    stderr_contains: str,
) -> None:
    """Verify that a server command fails with expected error.

    Args:
        e2e_deployment: The deployment instance
        command_args: Full command arguments (e.g., ["jupyter-deploy", "server", "exec", "--", "false"])
        expected_returncode: Expected return code (e.g., 1, 126, 127)
        stderr_contains: Substring that should appear in stderr (case-insensitive)

    Raises:
        AssertionError: If command succeeds or fails with unexpected error
    """
    try:
        result = e2e_deployment.cli.run_command(command_args)
        # If we reach here, the command succeeded unexpectedly
        raise AssertionError(f"Expected command {command_args} to fail, but it succeeded with output: {result.stdout}")
    except JDCliError as e:
        # Command failed as expected - now verify it failed for the right reason
        if not (e.__cause__ and isinstance(e.__cause__, subprocess.CalledProcessError)):
            raise AssertionError(f"Expected CalledProcessError, but got unexpected error type: {e}") from e

        # Check return code
        actual_returncode = e.__cause__.returncode
        if actual_returncode != expected_returncode:
            raise AssertionError(
                f"Expected return code {expected_returncode}, but got {actual_returncode}. Error: {e}"
            ) from e

        # Check error message in stderr
        error_output = str(e).lower()
        if stderr_contains.lower() not in error_output:
            raise AssertionError(f"Expected stderr to contain '{stderr_contains}', but got: {e}") from e
