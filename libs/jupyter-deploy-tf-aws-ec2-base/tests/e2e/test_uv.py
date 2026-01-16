"""E2E tests for UV package manager functionality."""

from pathlib import Path

import pytest
from pytest_jupyter_deploy.deployment import EndToEndDeployment
from pytest_jupyter_deploy.notebook import delete_notebook, run_notebook_in_jupyterlab, upload_notebook
from pytest_jupyter_deploy.oauth2_proxy.github import GitHubOAuth2ProxyApplication

from .constants import ORDER_UV


@pytest.mark.order(ORDER_UV)
@pytest.mark.mutating
def test_uv_switch_to_uv(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    logged_user: str,
) -> None:
    """Test switching to UV package manager."""
    # Switch to UV package manager
    e2e_deployment.ensure_server_stopped_and_host_is_running()
    e2e_deployment.ensure_deployed_with(["--jupyter-package-manager", "uv"])

    # Ensure server is running and user is authorized
    e2e_deployment.ensure_server_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Clean up old pixi files (from previous package manager)
    e2e_deployment.cli.run_command(
        ["jupyter-deploy", "server", "exec", "--", "rm", "-f", "/home/jovyan/pixi.toml", "/home/jovyan/pixi.lock"]
    )

    # Verify app is accessible
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()


@pytest.mark.order(ORDER_UV + 1)
@pytest.mark.mutating
def test_uv_install_and_persist(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    logged_user: str,
) -> None:
    """Test installing a library and verifying it persists after restart."""
    # Verify the deployment is using UV package manager
    result = e2e_deployment.cli.run_command(
        ["jupyter-deploy", "show", "--variable", "jupyter_package_manager", "--text"]
    )
    actual_package_manager = result.stdout.strip()

    if actual_package_manager != "uv":
        raise AssertionError(
            f"Expected package manager 'uv', but got '{actual_package_manager}'. "
            "The deployment may not have switched to UV correctly."
        )

    # Ensure server is running and user is authorized
    e2e_deployment.ensure_server_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Ensure authenticated in browser
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Get path to the notebook
    notebook_dir = Path(__file__).parent / "notebooks"
    notebook_path = notebook_dir / "uv_install_ipywidgets.ipynb"

    # Upload the notebook
    upload_notebook(e2e_deployment, notebook_path, "e2e-test/uv_install_ipywidgets.ipynb")

    # Restart server to ensure clean session (prevents "Document session error" dialogs)
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "restart"])

    # Re-authenticate after server restart
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Run the notebook in the UI
    run_notebook_in_jupyterlab(github_oauth_app.page, "e2e-test/uv_install_ipywidgets.ipynb", timeout_ms=120000)

    # Clean up - delete the notebook
    delete_notebook(e2e_deployment, "e2e-test/uv_install_ipywidgets.ipynb")

    # Restart server to verify persistence
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "restart", "-s", "jupyter"])
    e2e_deployment.ensure_server_running()

    # Verify ipywidgets is still installed after restart
    result = e2e_deployment.cli.run_command(
        ["jupyter-deploy", "server", "exec", "--", "uv", "pip", "show", "ipywidgets"]
    )
    if "Name: ipywidgets" not in result.stdout:
        raise AssertionError(f"Expected ipywidgets install to survive server restart: {result.stdout}")


@pytest.mark.order(ORDER_UV + 2)
@pytest.mark.mutating
def test_uv_environment_recovery(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    logged_user: str,
) -> None:
    """Test environment auto-recovery resets to base environment."""
    # Verify the deployment is using UV package manager
    result = e2e_deployment.cli.run_command(
        ["jupyter-deploy", "show", "--variable", "jupyter_package_manager", "--text"]
    )
    actual_package_manager = result.stdout.strip()

    if actual_package_manager != "uv":
        raise AssertionError(
            f"Expected package manager 'uv', but got '{actual_package_manager}'. "
            "The deployment may not have switched to UV correctly."
        )

    # Break environment by removing jupyterlab from dependencies
    # NOTE: Do NOT change this approach - uv remove is the correct way to break the environment
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "uv", "remove", "jupyterlab"])

    # Restart server (should trigger auto-recovery)
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "restart", "-s", "jupyter"])

    # Ensure server is running and user is authorized
    e2e_deployment.ensure_server_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Verify JupyterLab is accessible (auto-recovery worked)
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Verify jupyterlab was reinstalled
    result = e2e_deployment.cli.run_command(
        ["jupyter-deploy", "server", "exec", "--", "uv", "pip", "show", "jupyterlab"]
    )
    if "Name: jupyterlab" not in result.stdout:
        raise AssertionError(f"Expected jupyterlab to be present after recovery: {result.stdout}")

    # Verify ipywidgets is NO LONGER installed (user packages are not preserved during recovery)
    result = e2e_deployment.cli.run_command(
        ["jupyter-deploy", "server", "exec", "--", "uv", "pip", "show", "ipywidgets"]
    )
    if "Package(s) not found" not in result.stdout:
        raise AssertionError(f"Expected ipywidgets to be missing after recovery: {result.stdout}")
