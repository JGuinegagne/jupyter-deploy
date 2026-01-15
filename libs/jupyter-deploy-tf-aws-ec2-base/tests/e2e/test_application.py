"""E2E tests for application functionality - notebook execution in Jupyter."""

from pathlib import Path

from pytest_jupyter_deploy.deployment import EndToEndDeployment
from pytest_jupyter_deploy.notebook import delete_notebook, run_notebook_in_jupyterlab, upload_notebook
from pytest_jupyter_deploy.oauth2_proxy.github import GitHubOAuth2ProxyApplication


def test_application_simple_python(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    logged_user: str,
) -> None:
    """Test simple Python execution with no external dependencies."""
    # Ensure server is running and user is authorized
    e2e_deployment.ensure_server_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Ensure authenticated in browser
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Get path to the notebook
    notebook_dir = Path(__file__).parent / "notebooks"
    notebook_path = notebook_dir / "application_simple.ipynb"

    # Upload the notebook
    upload_notebook(e2e_deployment, notebook_path, "e2e-test/application_simple.ipynb")

    # Restart server to ensure clean session (prevents "Document session error" dialogs)
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "restart"])

    # Re-authenticate after server restart
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Run the notebook in the UI
    run_notebook_in_jupyterlab(github_oauth_app.page, "e2e-test/application_simple.ipynb", timeout_ms=120000)

    # Clean up - delete the notebook
    delete_notebook(e2e_deployment, "e2e-test/application_simple.ipynb")


def test_application_home_file_ops(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    logged_user: str,
) -> None:
    """Test home directory file operations."""
    # Ensure server is running and user is authorized
    e2e_deployment.ensure_server_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Ensure authenticated in browser
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Get path to the notebook
    notebook_dir = Path(__file__).parent / "notebooks"
    notebook_path = notebook_dir / "application_home_files.ipynb"

    # Upload the notebook
    upload_notebook(e2e_deployment, notebook_path, "e2e-test/application_home_files.ipynb")

    # Restart server to ensure clean session (prevents "Document session error" dialogs)
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "restart"])

    # Re-authenticate after server restart
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Run the notebook in the UI
    run_notebook_in_jupyterlab(github_oauth_app.page, "e2e-test/application_home_files.ipynb", timeout_ms=120000)

    # Clean up - delete the notebook
    delete_notebook(e2e_deployment, "e2e-test/application_home_files.ipynb")


def test_application_home_dir_ops(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    logged_user: str,
) -> None:
    """Test home directory operations (create/remove directories)."""
    # Ensure server is running and user is authorized
    e2e_deployment.ensure_server_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Ensure authenticated in browser
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Get path to the notebook
    notebook_dir = Path(__file__).parent / "notebooks"
    notebook_path = notebook_dir / "application_home_dirs.ipynb"

    # Upload the notebook
    upload_notebook(e2e_deployment, notebook_path, "e2e-test/application_home_dirs.ipynb")

    # Restart server to ensure clean session (prevents "Document session error" dialogs)
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "restart"])

    # Re-authenticate after server restart
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Run the notebook in the UI
    run_notebook_in_jupyterlab(github_oauth_app.page, "e2e-test/application_home_dirs.ipynb", timeout_ms=120000)

    # Clean up - delete the notebook
    delete_notebook(e2e_deployment, "e2e-test/application_home_dirs.ipynb")
