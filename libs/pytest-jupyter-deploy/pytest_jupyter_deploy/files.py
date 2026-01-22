"""File operation utilities for E2E tests."""

from pytest_jupyter_deploy.deployment import EndToEndDeployment


def verify_file_exists_on_server(e2e_deployment: EndToEndDeployment, file_path: str) -> None:
    """Verify that a file exists on the server."""
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "stat", file_path])
    assert "No such file or directory" not in result.stdout, f"Expected file {file_path} to exist on server"


def verify_file_does_not_exist_on_server(e2e_deployment: EndToEndDeployment, file_path: str) -> None:
    """Verify that a file does not exist on the server."""
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "stat", file_path])
    assert "No such file or directory" in result.stdout, f"Expected file {file_path} to not exist on server"
