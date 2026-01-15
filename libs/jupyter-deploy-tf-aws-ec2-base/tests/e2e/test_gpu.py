"""E2E tests for GPU instance deployment."""

from pathlib import Path

import pytest
from pytest_jupyter_deploy.deployment import EndToEndDeployment
from pytest_jupyter_deploy.notebook import delete_notebook, run_notebook_in_jupyterlab, upload_notebook
from pytest_jupyter_deploy.oauth2_proxy.github import GitHubOAuth2ProxyApplication
from pytest_jupyter_deploy.plugin import skip_if_testvars_not_set

from .constants import ORDER_GPU


@pytest.mark.order(ORDER_GPU)
@pytest.mark.mutating
@skip_if_testvars_not_set(["JD_E2E_CPU_INSTANCE", "JD_E2E_GPU_INSTANCE"])
def test_gpu_1_switch_to_gpu(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    gpu_instance_type: str,
    logged_user: str,
) -> None:
    """Test switching to GPU instance."""
    # Prerequisites
    e2e_deployment.ensure_server_stopped_and_host_is_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Switch to GPU instance
    e2e_deployment.ensure_deployed_with(["--instance-type", gpu_instance_type])

    # Ensure the server is running and healthy
    e2e_deployment.ensure_server_running()

    # Verify app is accessible
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()


@pytest.mark.order(ORDER_GPU + 1)
@pytest.mark.mutating
@skip_if_testvars_not_set(["JD_E2E_GPU_INSTANCE"])
def test_gpu_2_run_gpu_notebook(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    gpu_instance_type: str,
    logged_user: str,
) -> None:
    """Test running a GPU verification notebook."""
    # Verify the deployment is using the GPU instance type
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "show", "--variable", "instance_type", "--text"])
    actual_instance_type = result.stdout.strip()

    if actual_instance_type != gpu_instance_type:
        raise AssertionError(
            f"Expected instance type {gpu_instance_type}, but got {actual_instance_type}. "
            "The deployment may not have switched to GPU correctly."
        )

    # Prerequisite,
    e2e_deployment.ensure_server_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Ensure authenticated in browser
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Get path to the gpu_check notebook
    notebook_dir = Path(__file__).parent / "notebooks"
    gpu_notebook = notebook_dir / "gpu_check.ipynb"

    # Upload the notebook
    upload_notebook(e2e_deployment, gpu_notebook, "e2e-test/gpu_check.ipynb")

    # Restart server to ensure clean session (prevents "Document session error" dialogs)
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "restart", "-s", "jupyter"])

    # Re-authenticate after server restart
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Run the notebook in the UI
    run_notebook_in_jupyterlab(github_oauth_app.page, "e2e-test/gpu_check.ipynb", timeout_ms=120000)

    # Clean up - delete the notebook
    delete_notebook(e2e_deployment, "e2e-test/gpu_check.ipynb")


@pytest.mark.order(ORDER_GPU + 2)
@pytest.mark.mutating
@skip_if_testvars_not_set(["JD_E2E_CPU_INSTANCE"])
def test_gpu_3_switch_back_to_cpu(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    cpu_instance_type: str,
    logged_user: str,
) -> None:
    """Test switching back to CPU instance."""
    # Switch back to CPU instance
    e2e_deployment.ensure_server_stopped_and_host_is_running()
    e2e_deployment.ensure_deployed_with(["--instance-type", cpu_instance_type])

    # Prerequisites
    e2e_deployment.ensure_server_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Verify app is still accessible after switching back
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()
