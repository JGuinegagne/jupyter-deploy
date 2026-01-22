"""E2E tests for home volume file system operations."""

from pathlib import Path

from pytest_jupyter_deploy.deployment import EndToEndDeployment
from pytest_jupyter_deploy.files import (
    upload_file_on_server,
    verify_dir_exists_on_server,
    verify_file_exists_on_server,
    verify_file_or_dir_does_not_exist_on_server,
)


def test_fs_operations(
    e2e_deployment: EndToEndDeployment,
    logged_user: str,
) -> None:
    """Test read/write/exec operations on files and read/write on directories on home volume."""
    # Ensure server is running and user is authorized
    e2e_deployment.ensure_server_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Test file upload and execution
    script_path_home = "test_script.sh"
    test_script = Path(__file__).parent / "files" / "test_script.sh"
    upload_file_on_server(e2e_deployment, test_script, script_path_home)
    verify_file_exists_on_server(e2e_deployment, script_path_home)

    # Test bash script execution
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "sh", script_path_home])
    assert "Script executed successfully" in result.stdout, "Expected script to execute successfully on home volume"

    # Upload a data file to home volume
    data_file_home = "e2e_test_data.txt"
    test_data = Path(__file__).parent / "files" / "data_sample.txt"
    upload_file_on_server(e2e_deployment, test_data, data_file_home)
    verify_file_exists_on_server(e2e_deployment, data_file_home)

    # Verify file content
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "cat", data_file_home])
    assert "This is test data for E2E testing" in result.stdout, "Expected file content to match"

    # Create nested directories on home volume
    test_top_dir_home = "e2e_workspace"
    test_dir_home = f"{test_top_dir_home}/subdir1/nested1"
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "mkdir", "-p", test_dir_home])
    verify_dir_exists_on_server(e2e_deployment, test_dir_home)

    # Create more nested directories
    test_dir_home_2 = f"{test_top_dir_home}/subdir2/nested2/deep2"
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "mkdir", "-p", test_dir_home_2])
    verify_dir_exists_on_server(e2e_deployment, test_dir_home_2)

    # Create a file in the nested directory
    test_file_in_dir = f"{test_dir_home}/test_file.txt"
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "touch", test_file_in_dir])
    verify_file_exists_on_server(e2e_deployment, test_file_in_dir)

    # Remove the file
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "rm", "-f", test_file_in_dir])
    verify_file_or_dir_does_not_exist_on_server(e2e_deployment, test_file_in_dir)

    # Cleanup
    e2e_deployment.cli.run_command(
        ["jupyter-deploy", "server", "exec", "--", "rm", "-rf", script_path_home, data_file_home, test_top_dir_home]
    )

    # Verify cleanup
    verify_file_or_dir_does_not_exist_on_server(e2e_deployment, script_path_home)
    verify_file_or_dir_does_not_exist_on_server(e2e_deployment, data_file_home)
    verify_file_or_dir_does_not_exist_on_server(e2e_deployment, test_top_dir_home)
