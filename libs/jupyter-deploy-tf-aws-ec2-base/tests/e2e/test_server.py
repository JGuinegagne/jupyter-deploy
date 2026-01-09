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


def test_server_logs(e2e_deployment: EndToEndDeployment) -> None:
    """Test that server logs can be retrieved."""
    # Prerequisites
    e2e_deployment.ensure_server_running()

    # Get server logs
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "server", "logs"])

    # Verify we got some output
    assert result.stdout, "Expected non-empty logs output"
    # Logs should contain some indication that this is log output
    # The output contains "stdout" or similar markers
    assert "stdout" in result.stdout or "stderr" in result.stdout, "Expected log output markers"


def test_all_service_logs(
    e2e_deployment: EndToEndDeployment, github_oauth_app: GitHubOAuth2ProxyApplication, logged_user: str
) -> None:
    """Test that logs can be retrieved for each individual service."""
    # Prerequisites
    e2e_deployment.ensure_server_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Visit the application to ensure there are logs for all of the services
    # otherwise, depending on the order of tests, traefik may not have any logs
    # e.g., if the previous ran restarted the host
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Test logs for jupyter service
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "server", "logs", "-s", "jupyter"])
    assert result.stdout, "Expected non-empty logs output for jupyter service"
    assert "stdout" in result.stdout or "stderr" in result.stdout, "Expected log output markers for jupyter"

    # Test logs for traefik service
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "server", "logs", "-s", "traefik"])
    assert result.stdout, "Expected non-empty logs output for traefik service"
    assert "stdout" in result.stdout or "stderr" in result.stdout, "Expected log output markers for traefik"

    # Test logs for oauth service
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "server", "logs", "-s", "oauth"])
    assert result.stdout, "Expected non-empty logs output for oauth service"
    assert "stdout" in result.stdout or "stderr" in result.stdout, "Expected log output markers for oauth"


def test_server_logs_piped_command(e2e_deployment: EndToEndDeployment) -> None:
    """Test that piped commands work with server logs."""
    # Prerequisites
    e2e_deployment.ensure_server_running()

    # Test: --tail 5 returns exactly 5 log entries
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "server", "logs", "--", "--tail", "5"])

    # Verify we got some output
    assert result.stdout, "Expected non-empty logs output with --tail 5"

    # Parse log entries using the utility function
    log_entries = e2e_deployment.cli.parse_log_entries_from_output(result.stdout)

    # Assert we got exactly 5 log entries
    assert len(log_entries) == 5, f"Expected exactly 5 log entries with --tail 5, got {len(log_entries)}"
