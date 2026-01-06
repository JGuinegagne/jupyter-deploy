"""E2E tests for deployment."""

from pytest_jupyter_deploy.deployment import EndToEndDeployment


def test_host_running(e2e_deployment: EndToEndDeployment, logged_user: str) -> None:
    """Test that the host is running."""
    # Prerequisites
    e2e_deployment.ensure_host_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Get host status
    host_status = e2e_deployment.cli.get_host_status()
    assert host_status == "running", f"Expected host status 'running', got '{host_status}'"


def test_host_stop(e2e_deployment: EndToEndDeployment, logged_user: str) -> None:
    """Test that the host can be stopped from command line."""
    # Prerequisites
    e2e_deployment.ensure_host_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Stop host and assert status
    e2e_deployment.cli.run_command(["jupyter-deploy", "host", "stop"])
    host_status = e2e_deployment.cli.get_host_status()
    assert host_status == "stopped", f"Expected host status 'stopped', got '{host_status}'"


def test_host_start(e2e_deployment: EndToEndDeployment, logged_user: str) -> None:
    """Test that the host can be started from command line."""
    # Prerequisites
    e2e_deployment.ensure_host_stopped()

    # Start host (this is what we're testing)
    e2e_deployment.cli.run_command(["jupyter-deploy", "host", "start"])

    # Wait for SSM to be ready before setting authorization
    e2e_deployment.wait_for_ssm_ready()

    # Now that host is running and SSM is ready, set authorization
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Assert status
    host_status = e2e_deployment.cli.get_host_status()
    assert host_status == "running", f"Expected host status 'running', got '{host_status}'"
