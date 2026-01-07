"""E2E tests for deployment."""

import pexpect
from pytest_jupyter_deploy.deployment import EndToEndDeployment


def test_host_running(e2e_deployment: EndToEndDeployment) -> None:
    """Test that the host is running."""
    # Prerequisites
    e2e_deployment.ensure_host_running()

    # Get host status
    host_status = e2e_deployment.cli.get_host_status()
    assert host_status == "running", f"Expected host status 'running', got '{host_status}'"


def test_host_stop(e2e_deployment: EndToEndDeployment) -> None:
    """Test that the host can be stopped from command line."""
    # Prerequisites
    e2e_deployment.ensure_host_running()

    # Stop host and assert status
    e2e_deployment.cli.run_command(["jupyter-deploy", "host", "stop"])
    host_status = e2e_deployment.cli.get_host_status()
    assert host_status == "stopped", f"Expected host status 'stopped', got '{host_status}'"


def test_host_start(e2e_deployment: EndToEndDeployment) -> None:
    """Test that the host can be started from command line."""
    # Prerequisites
    e2e_deployment.ensure_host_stopped()

    # Start host (this is what we're testing)
    e2e_deployment.cli.run_command(["jupyter-deploy", "host", "start"])

    # Assert status
    host_status = e2e_deployment.cli.get_host_status()
    assert host_status == "running", f"Expected host status 'running', got '{host_status}'"


def test_host_connect_whoami(e2e_deployment: EndToEndDeployment) -> None:
    """Test that we can connect to the host via SSM and run a simple command."""
    # Prerequisites
    e2e_deployment.ensure_host_running()
    e2e_deployment.wait_for_ssm_ready()

    # Start an interactive jd host connect session
    with e2e_deployment.cli.spawn_interactive_session("jupyter-deploy host connect") as session:
        # Wait for the session to start
        session.expect("Starting SSM session", timeout=10)

        # Send whoami command
        session.sendline("whoami")

        # Expect ssm-user in the output
        session.expect("ssm-user", timeout=5)

        # Exit the session
        session.sendline("exit")

        # Wait for the session to close
        session.expect(pexpect.EOF, timeout=5)
