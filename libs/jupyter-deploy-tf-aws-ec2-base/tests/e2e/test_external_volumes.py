"""E2E tests for external volumes (EBS and EFS) functionality."""

from pathlib import Path

import pytest
from pytest_jupyter_deploy.deployment import EndToEndDeployment
from pytest_jupyter_deploy.notebook import delete_notebook, run_notebook_in_jupyterlab, upload_notebook
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
        result = e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "stat", mount_point])
        if "No such file or directory" in result.stdout:
            raise AssertionError(f"Expected mount point {mount_point} to be accessible from jupyterlab")

    # Verify app is accessible
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()


@pytest.mark.order(ORDER_EXTERNAL_VOLUMES + 1)
@pytest.mark.mutating
def test_external_volumes_ebs(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    logged_user: str,
) -> None:
    """Test EBS volumes file and directory operations."""
    # Ensure server is running and user is authorized
    e2e_deployment.ensure_server_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Ensure authenticated in browser
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Get path to the notebook
    notebook_dir = Path(__file__).parent / "notebooks"
    notebook_path = notebook_dir / "external_volumes_ebs.ipynb"

    # Upload the notebook
    upload_notebook(e2e_deployment, notebook_path, "e2e-test/external_volumes_ebs.ipynb")

    # Restart server to ensure clean session (prevents "Document session error" dialogs)
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "restart"])

    # Re-authenticate after server restart
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Run the notebook in the UI
    run_notebook_in_jupyterlab(github_oauth_app.page, "e2e-test/external_volumes_ebs.ipynb", timeout_ms=120000)

    # Clean up - delete the notebook
    delete_notebook(e2e_deployment, "e2e-test/external_volumes_ebs.ipynb")


@pytest.mark.order(ORDER_EXTERNAL_VOLUMES + 2)
@pytest.mark.mutating
def test_external_volumes_efs(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    logged_user: str,
) -> None:
    """Test EFS volume file and directory operations."""
    # Ensure server is running and user is authorized
    e2e_deployment.ensure_server_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Ensure authenticated in browser
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Get path to the notebook
    notebook_dir = Path(__file__).parent / "notebooks"
    notebook_path = notebook_dir / "external_volumes_efs.ipynb"

    # Upload the notebook
    upload_notebook(e2e_deployment, notebook_path, "e2e-test/external_volumes_efs.ipynb")

    # Restart server to ensure clean session (prevents "Document session error" dialogs)
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "restart"])

    # Re-authenticate after server restart
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Run the notebook in the UI
    run_notebook_in_jupyterlab(github_oauth_app.page, "e2e-test/external_volumes_efs.ipynb", timeout_ms=120000)

    # Clean up - delete the notebook
    delete_notebook(e2e_deployment, "e2e-test/external_volumes_efs.ipynb")
