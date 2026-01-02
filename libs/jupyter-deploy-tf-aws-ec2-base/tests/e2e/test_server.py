from pytest_jupyter_deploy.deployment import EndToEndDeployment


def test_server_running(e2e_deployment: EndToEndDeployment) -> None:
    """Test that the Jupyter server is available."""
    # Prerequisites
    e2e_deployment.ensure_deployed()
    e2e_deployment.ensure_host_running()
    e2e_deployment.ensure_server_running()

    # Get server status
    server_status = e2e_deployment.cli.get_server_status()
    assert server_status == "IN_SERVICE", f"Expected server status 'IN_SERVICE', got '{server_status}'"


def test_stop_server(e2e_deployment: EndToEndDeployment) -> None:
    """Test that the Jupyter server can be stopped from command line."""
    # Prerequisites
    e2e_deployment.ensure_deployed()
    e2e_deployment.ensure_host_running()
    e2e_deployment.ensure_server_running()

    # Stop server and assert status
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "stop"])
    server_status = e2e_deployment.cli.get_server_status()
    assert server_status == "STOPPED", f"Expected server status 'STOPPED', got '{server_status}'"


def test_start_server(e2e_deployment: EndToEndDeployment) -> None:
    """Test that the Jupyter server can be started from command line."""
    # Prerequisites
    e2e_deployment.ensure_deployed()
    e2e_deployment.ensure_host_running()
    e2e_deployment.ensure_server_stopped()

    # Start server and assert status
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "start"])
    server_status = e2e_deployment.cli.get_server_status()
    assert server_status == "IN_SERVICE", f"Expected server status 'IN_SERVICE', got '{server_status}'"
