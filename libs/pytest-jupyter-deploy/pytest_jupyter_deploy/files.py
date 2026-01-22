"""File operation utilities for E2E tests."""

import base64
from pathlib import Path

from pytest_jupyter_deploy.deployment import EndToEndDeployment


def verify_file_exists_on_server(e2e_deployment: EndToEndDeployment, file_path: str) -> None:
    """Verify that a file exists on the server."""
    result = e2e_deployment.cli.run_command(
        ["jupyter-deploy", "server", "exec", "--", "stat", "--format=%F", file_path]
    )
    assert "No such file or directory" not in result.stdout, f"Expected file {file_path} to exist on server"
    assert "file" in result.stdout, f"Expected file {file_path} to be of type file: {result.stdout}"


def verify_dir_exists_on_server(e2e_deployment: EndToEndDeployment, dir_path: str) -> None:
    """Verify that a file exists on the server."""
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "stat", "--format=%F", dir_path])
    assert "No such file or directory" not in result.stdout, f"Expected dir {dir_path} to exist on server"
    assert "directory" in result.stdout, f"Expected directory {dir_path} to be of type dir: {result.stdout}"


def verify_file_or_dir_does_not_exist_on_server(e2e_deployment: EndToEndDeployment, file_path: str) -> None:
    """Verify that a file does not exist on the server."""
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "stat", file_path])
    # When stat fails, the error message appears in stdout (captured by the CLI wrapper)
    # The message may be split across lines, so normalize whitespace before checking
    stdout_normalized = " ".join(result.stdout.split())
    stderr_normalized = " ".join(result.stderr.split())
    assert "No such file or directory" in stdout_normalized or "No such file or directory" in stderr_normalized, (
        f"Expected file {file_path} to not exist on server"
    )


def upload_file_on_server(e2e_deployment: EndToEndDeployment, src_path: str | Path, target_path: str) -> None:
    """Upload a file to the server.

    Args:
        e2e_deployment: The deployment instance
        src_path: Path to the local file
        target_path: Target path on the server

    Raises:
        FileNotFoundError: If the source file doesn't exist
    """
    src_path = Path(src_path)
    if not src_path.exists() or not src_path.is_file():
        raise FileNotFoundError(f"File not found: {src_path}")

    # Read the file content and base64 encode for safe transmission
    with open(src_path, "rb") as f:
        file_content = f.read()
    encoded_content = base64.b64encode(file_content).decode()

    # Upload file using python to decode and write
    # Only create parent directories if target_path contains a directory component
    dir_component = f"os.path.dirname('{target_path}')"
    mkdir_cmd = f"d={dir_component}; d and os.makedirs(d, exist_ok=True); "
    python_cmd = (
        f'python3 -c "import base64, os; '
        f"{mkdir_cmd}"
        f"data=base64.b64decode('{encoded_content}'); "
        f"open('{target_path}', 'wb').write(data)\""
    )

    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", python_cmd])
