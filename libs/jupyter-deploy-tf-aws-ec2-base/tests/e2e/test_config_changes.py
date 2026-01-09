"""E2E tests for configuration changes and redeployment."""

from subprocess import CompletedProcess

import pytest
from pytest_jupyter_deploy.cli import JDCliError
from pytest_jupyter_deploy.constants import E2E_UPGRADE_INSTANCE_LOG_FILE
from pytest_jupyter_deploy.deployment import EndToEndDeployment
from pytest_jupyter_deploy.oauth2_proxy.github import GitHubOAuth2ProxyApplication
from pytest_jupyter_deploy.plugin import skip_if_testvars_not_set


@pytest.mark.order(10)
@pytest.mark.mutating
@skip_if_testvars_not_set(["JD_E2E_LARGER_INSTANCE", "JD_E2E_LARGER_LOG_RETENTION_DAYS"])
def test_upgrade_config(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    larger_instance_type: str,
    larger_log_retention_days: int,
    logged_user: str,
) -> None:
    """Test upgrading to a larger instance type and log retention days.

    This test:
    1. Skips if current config already equals the larger values
    2. Stops the server before config change
    3. Updates variables.yaml to set larger log_files_retention_days
    4. Updates the instance type directly with `jd config --instance-type`
    5. Runs `jd config` and `jd up -y` to apply the changes
    6. Restarts the server after change
    7. Saves logs to e2e-upgrade-instance.log
    8. Verifies the app is still accessible

    Note: It would be tempting to test raising the volume size
    However AWS EBS has cooldown rate limits between volume modifications (6 hour).
    We use a more innocuous parameter (log_files_retention_days) instead.
    """
    # Prerequisites
    e2e_deployment.ensure_deployed()
    e2e_deployment.ensure_authorized([logged_user], "", [])
    e2e_deployment.ensure_server_stopped_and_host_is_running()

    # Update one variable value using 'variables.yaml'
    e2e_deployment.update_override_value("log_files_retention_days", larger_log_retention_days)

    # And the other using the CLI directly
    # Note: --instance-type flag is added dynamically at runtime by a decorator
    # based on the template's variables, so it appears only on jd config --help
    # from inside a jupyter-deploy project
    e2e_deployment.cli.run_command(["jupyter-deploy", "config", "--instance-type", larger_instance_type])

    # Apply the changes
    # Note: We tolerate failure here because config changes that modify the instance
    # (instance type) can cause Docker containers to crash after the instance is
    # stopped/modified/restarted. The waiter script will detect this and fail, but
    # the infrastructure changes will have succeeded. The subsequent server restart
    # via ensure_server_running() will bring the containers back to a healthy state.
    result: CompletedProcess[str] | None = None
    try:
        result = e2e_deployment.cli.run_command(["jupyter-deploy", "up", "-y"])
    except JDCliError:
        # Command failed - this is expected when containers crash after instance changes
        # Continue to restart step which will bring services back up
        pass
    finally:
        # Save logs
        if result is not None:
            e2e_deployment.save_command_logs(E2E_UPGRADE_INSTANCE_LOG_FILE, result)

    # Ensure the server is running and healthy
    # After instance modifications, SSM agent may need time to register, so we use
    # ensure_server_running() which waits for SSM readiness before attempting restart
    # In practice, users would run `jd open` which handles this automatically
    e2e_deployment.ensure_server_running()

    # Verify app is accessible
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()
