"""E2E tests for JupyterLab application accessibility and functionality."""

from pytest_jupyter_deploy.deployment import EndToEndDeployment
from pytest_jupyter_deploy.oauth2_proxy.github import GitHubOAuth2ProxyApplication


def test_application_accessible(
    e2e_deployment: EndToEndDeployment, github_oauth_app: GitHubOAuth2ProxyApplication, logged_user: str
) -> None:
    """Test that the application is accessible from the webbrowser."""
    # Prerequisite
    e2e_deployment.ensure_server_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])
    github_oauth_app.ensure_authenticated()

    # Assert
    github_oauth_app.verify_jupyterlab_accessible()
