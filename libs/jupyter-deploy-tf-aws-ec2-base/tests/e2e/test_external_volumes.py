"""E2E tests for external volumes (EBS and EFS) functionality."""

from pathlib import Path

import pytest
from pytest_jupyter_deploy.deployment import EndToEndDeployment
from pytest_jupyter_deploy.files import (
    upload_file_on_server,
    verify_dir_exists_on_server,
    verify_file_exists_on_server,
    verify_file_or_dir_does_not_exist_on_server,
)
from pytest_jupyter_deploy.oauth2_proxy.github import GitHubOAuth2ProxyApplication

from .constants import ORDER_EXTERNAL_VOLUMES


@pytest.mark.order(ORDER_EXTERNAL_VOLUMES)
@pytest.mark.mutating
def test_external_volumes_provisioning(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    logged_user: str,
) -> None:
    """Test that external volumes are mounted correctly."""
    # Create the EBS/EFS and mount them
    e2e_deployment.ensure_deployed_with(
        [
            "--additional-ebs-mounts",
            "name=ebs1,mount_point=external-ebs1,size_gb=50",
            "--additional-ebs-mounts",
            "name=ebs2,mount_point=external-ebs2",
            "--additional-efs-mounts",
            "name=efs1,mount_point=external-efs1",
        ]
    )

    # Ensure server is running and user is authorized
    e2e_deployment.ensure_server_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Verify all mount points exist
    mount_points = [
        "/home/jovyan/external-ebs1",
        "/home/jovyan/external-ebs2",
        "/home/jovyan/external-efs1",
    ]
    for mount_point in mount_points:
        verify_dir_exists_on_server(e2e_deployment, mount_point)

    # Verify app is accessible
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()


@pytest.mark.order(ORDER_EXTERNAL_VOLUMES + 1)
@pytest.mark.mutating
def test_external_volumes_ebs(
    e2e_deployment: EndToEndDeployment,
    logged_user: str,
) -> None:
    """Test EBS volumes file and directory operations."""
    # Ensure server is running and user is authorized
    e2e_deployment.ensure_server_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Test file upload and execution on EBS1
    script_path_ebs1 = "external-ebs1/test_script.sh"
    test_script = Path(__file__).parent / "files" / "test_script.sh"
    upload_file_on_server(e2e_deployment, test_script, script_path_ebs1)
    verify_file_exists_on_server(e2e_deployment, script_path_ebs1)

    # Test bash script execution
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "sh", script_path_ebs1])
    assert "Script executed successfully" in result.stdout, "Expected script to execute successfully on EBS1"

    # Create nested directories on EBS2
    test_top_dir_ebs2 = "external-ebs2/e2e_test_dir"
    test_dir_ebs2 = f"{test_top_dir_ebs2}/level1/level2/level3"
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "mkdir", "-p", test_dir_ebs2])
    verify_dir_exists_on_server(e2e_deployment, test_dir_ebs2)

    # Create a file in the nested directory on EBS2
    test_file_in_dir = f"{test_dir_ebs2}/test_file.txt"
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "touch", test_file_in_dir])
    verify_file_exists_on_server(e2e_deployment, test_file_in_dir)

    # Remove the file from EBS2
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "rm", "-f", test_file_in_dir])
    verify_file_or_dir_does_not_exist_on_server(e2e_deployment, test_file_in_dir)

    # Cleanup
    e2e_deployment.cli.run_command(
        ["jupyter-deploy", "server", "exec", "--", "rm", "-rf", script_path_ebs1, test_top_dir_ebs2]
    )

    # Verify cleanup
    verify_file_or_dir_does_not_exist_on_server(e2e_deployment, script_path_ebs1)
    verify_file_or_dir_does_not_exist_on_server(e2e_deployment, test_top_dir_ebs2)


@pytest.mark.order(ORDER_EXTERNAL_VOLUMES + 2)
@pytest.mark.mutating
def test_external_volumes_efs(
    e2e_deployment: EndToEndDeployment,
    logged_user: str,
) -> None:
    """Test EFS volume file and directory operations."""
    # Ensure server is running and user is authorized
    e2e_deployment.ensure_server_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Test file upload and execution on EFS1
    script_path_efs1 = "external-efs1/test_script.sh"
    test_script = Path(__file__).parent / "files" / "test_script.sh"
    upload_file_on_server(e2e_deployment, test_script, script_path_efs1)
    verify_file_exists_on_server(e2e_deployment, script_path_efs1)

    # Test bash script execution
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "sh", script_path_efs1])
    assert "Script executed successfully" in result.stdout, "Expected script to execute successfully on EFS1"

    # Test directory operations on EFS1
    test_top_dir_efs1 = "external-efs1/e2e_test_dir"
    test_dir_efs1 = f"{test_top_dir_efs1}/level1/level2/level3"
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "mkdir", "-p", test_dir_efs1])
    verify_dir_exists_on_server(e2e_deployment, test_dir_efs1)

    # Create a file in the nested directory
    test_file_in_dir = f"{test_dir_efs1}/test_file.txt"
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "touch", test_file_in_dir])
    verify_file_exists_on_server(e2e_deployment, test_file_in_dir)

    # Remove the file
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "rm", "-f", test_file_in_dir])
    verify_file_or_dir_does_not_exist_on_server(e2e_deployment, test_file_in_dir)

    # Cleanup
    e2e_deployment.cli.run_command(
        ["jupyter-deploy", "server", "exec", "--", "rm", "-rf", script_path_efs1, test_top_dir_efs1]
    )

    # Verify cleanup
    verify_file_or_dir_does_not_exist_on_server(e2e_deployment, script_path_efs1)
    verify_file_or_dir_does_not_exist_on_server(e2e_deployment, test_top_dir_efs1)
