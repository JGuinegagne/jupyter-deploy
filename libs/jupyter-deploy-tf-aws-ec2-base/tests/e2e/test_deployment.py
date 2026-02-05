"""E2E test for full deployment lifecycle from scratch."""

import pytest
from pytest_jupyter_deploy.deployment import EndToEndDeployment
from pytest_jupyter_deploy.oauth2_proxy.github import GitHubOAuth2ProxyApplication

from .constants import ORDER_DEPLOYMENT


@pytest.mark.order(ORDER_DEPLOYMENT)
@pytest.mark.full_deployment  # Only runs when deploying from scratch
def test_immediately_available_after_deployment(
    github_oauth_app: GitHubOAuth2ProxyApplication,
) -> None:
    """Test complete deployment: init, config, up, verify OAuth proxy accessible.

    This test only runs when deploying from scratch (ie a new sandbox-e2e dir).
    After deployment completes, it verifies:
    1. OAuth2 Proxy is responding and accessible
    2. User can authenticate and access JupyterLab

    The test does NOT ensure the server is running first - it expects that
    after `jd up` completes, everything should be running and accessible.
    """
    # Immediately verify OAuth proxy is accessible
    # This will land on OAuth login page (before authentication)
    github_oauth_app.verify_oauth_proxy_accessible()

    # Now authenticate and verify full JupyterLab access
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()


@pytest.mark.order(ORDER_DEPLOYMENT + 1)
@pytest.mark.full_deployment  # Only runs when deploying from scratch
def test_deployment_history_captured(e2e_deployment: EndToEndDeployment) -> None:
    """Test that config and up logs are captured in jd history after deployment.

    This test runs after test_immediately_available_after_deployment and verifies:
    1. Exactly 1 config log exists
    2. Exactly 1 up log exists
    3. Config log contains terraform initialization output
    4. Up log contains terraform apply output
    """
    # Verify exactly 1 config log exists
    config_list_result = e2e_deployment.cli.run_command(["jupyter-deploy", "history", "list", "config", "--text"])
    config_logs = [line for line in config_list_result.stdout.strip().split("\n") if line.strip()]
    assert len(config_logs) == 1, f"Expected exactly 1 config log, found {len(config_logs)}"

    # Verify exactly 1 up log exists
    up_list_result = e2e_deployment.cli.run_command(["jupyter-deploy", "history", "list", "up", "--text"])
    up_logs = [line for line in up_list_result.stdout.strip().split("\n") if line.strip()]
    assert len(up_logs) == 1, f"Expected exactly 1 up log, found {len(up_logs)}"

    # Retrieve and verify config log content
    config_show_result = e2e_deployment.cli.run_command(["jupyter-deploy", "history", "show", "config"])
    config_content = config_show_result.stdout
    assert "Terraform has been successfully initialized!" in config_content, (
        "Expected 'Terraform has been successfully initialized!' in config log"
    )

    # Retrieve and verify up log content
    up_show_result = e2e_deployment.cli.run_command(["jupyter-deploy", "history", "show", "up"])
    up_content = up_show_result.stdout
    assert "Apply complete!" in up_content, "Expected 'Apply complete!' in up log"
    assert "Outputs:" in up_content, "Expected 'Outputs:' section in up log"
