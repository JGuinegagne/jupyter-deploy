from pytest_jupyter_deploy.deployment import EndToEndDeployment
from pytest_jupyter_deploy.oauth2_proxy.github import GitHubOAuth2ProxyApplication


def test_server_running(
    e2e_deployment: EndToEndDeployment, github_oauth_app: GitHubOAuth2ProxyApplication, logged_user: str
) -> None:
    """Test that the Jupyter server is available."""
    # Prerequisites
    e2e_deployment.ensure_server_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Get server status
    server_status = e2e_deployment.cli.get_server_status()
    assert server_status == "IN_SERVICE", f"Expected server status 'IN_SERVICE', got '{server_status}'"

    # Verify application is accessible
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()


def test_stop_server(
    e2e_deployment: EndToEndDeployment, github_oauth_app: GitHubOAuth2ProxyApplication, logged_user: str
) -> None:
    """Test that the Jupyter server can be stopped from command line."""
    # Prerequisites
    e2e_deployment.ensure_server_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Stop server and assert status
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "stop"])
    server_status = e2e_deployment.cli.get_server_status()
    assert server_status == "STOPPED", f"Expected server status 'STOPPED', got '{server_status}'"

    # Verify application is not accessible after stop
    github_oauth_app.verify_server_unaccessible()


def test_start_server(
    e2e_deployment: EndToEndDeployment, github_oauth_app: GitHubOAuth2ProxyApplication, logged_user: str
) -> None:
    """Test that the Jupyter server can be started from command line."""
    # Prerequisites
    e2e_deployment.ensure_server_stopped_and_host_is_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Start server and assert status
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "start"])
    server_status = e2e_deployment.cli.get_server_status()
    assert server_status == "IN_SERVICE", f"Expected server status 'IN_SERVICE', got '{server_status}'"

    # Verify application is accessible after start
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()
