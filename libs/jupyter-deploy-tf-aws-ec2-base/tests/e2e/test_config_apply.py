"""E2E tests for configuration changes and redeployment."""

import pytest
from pytest_jupyter_deploy.deployment import EndToEndDeployment
from pytest_jupyter_deploy.files import verify_file_exists_on_server, verify_file_or_dir_does_not_exist_on_server
from pytest_jupyter_deploy.oauth2_proxy.github import GitHubOAuth2ProxyApplication
from pytest_jupyter_deploy.plugin import skip_if_testvars_not_set

from .constants import ORDER_CONFIG_APPLY


@pytest.mark.order(ORDER_CONFIG_APPLY)
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

    This test verifies that data persists across instance type changes:
    1. Provisions external volumes (EBS + EFS) using ensure_deployed_with
    2. Creates flag files in home volume (main EBS) and external volumes (EBS + EFS)
    3. Updates variables.yaml to set larger log_files_retention_days
    4. Updates the instance type directly with `jd config --instance-type`
    5. Runs `jd config` and `jd up -y` to apply the changes (triggers instance swap)
    6. Restarts the server after change
    7. Verifies the app is still accessible
    8. Confirms all flag files persisted across the instance swap
    9. Cleans up the flag files

    Note: It would be tempting to test raising the volume size
    However AWS EBS has cooldown rate limits between volume modifications (6 hour).
    We use a more innocuous parameter (log_files_retention_days) instead.
    """
    # Provision external volumes first
    e2e_deployment.ensure_deployed_with(
        [
            "--additional-ebs-mounts",
            "name=ebs1,mount_point=external-ebs1,size_gb=50",
            "--additional-efs-mounts",
            "name=efs1,mount_point=external-efs1",
        ]
    )

    # Prerequisites
    e2e_deployment.ensure_server_running()
    e2e_deployment.ensure_authorized([logged_user], "", [])

    # Add flag files to all volumes (home + external)
    e2e_deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", "touch", "e2e_flag_home.txt"])
    e2e_deployment.cli.run_command(
        ["jupyter-deploy", "server", "exec", "--", "touch", "external-ebs1/e2e_flag_ebs.txt"]
    )
    e2e_deployment.cli.run_command(
        ["jupyter-deploy", "server", "exec", "--", "touch", "external-efs1/e2e_flag_efs.txt"]
    )

    # Update one variable value using 'variables.yaml'
    e2e_deployment.update_override_value("log_files_retention_days", larger_log_retention_days)

    # And the other using the CLI directly
    # Note: --instance-type flag is added dynamically at runtime by a decorator
    # based on the template's variables, so it appears only on jd config --help
    # from inside a jupyter-deploy project
    e2e_deployment.cli.run_command(
        [
            "jupyter-deploy",
            "config",
            "--instance-type",
            larger_instance_type,
        ]
    )

    # Apply the changes
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "up", "--verbose"])

    # Ensure the server is running and healthy
    # After instance modifications, SSM agent may need time to register, so we use
    # ensure_server_running() which waits for SSM readiness before attempting restart
    # In practice, users would run `jd open` which handles this automatically
    e2e_deployment.ensure_server_running()

    # Verify app is accessible
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Verify that all flag files persisted across instance swap
    verify_file_exists_on_server(e2e_deployment, "e2e_flag_home.txt")
    verify_file_exists_on_server(e2e_deployment, "external-ebs1/e2e_flag_ebs.txt")
    verify_file_exists_on_server(e2e_deployment, "external-efs1/e2e_flag_efs.txt")

    # Clean up flag files
    e2e_deployment.cli.run_command(
        [
            "jupyter-deploy",
            "server",
            "exec",
            "--",
            "rm",
            "e2e_flag_home.txt",
            "external-ebs1/e2e_flag_ebs.txt",
            "external-efs1/e2e_flag_efs.txt",
        ]
    )

    # Verify cleanup succeeded
    verify_file_or_dir_does_not_exist_on_server(e2e_deployment, "e2e_flag_home.txt")
    verify_file_or_dir_does_not_exist_on_server(e2e_deployment, "external-ebs1/e2e_flag_ebs.txt")
    verify_file_or_dir_does_not_exist_on_server(e2e_deployment, "external-efs1/e2e_flag_efs.txt")

    # Verify terraform output is visible in verbose mode
    assert "Apply complete!" in result.stdout, "Expected 'Apply complete!' in verbose up output"
    assert "Outputs:" in result.stdout, "Expected 'Outputs:' section in verbose up output"

    # Verify up logs are accessible via jd history
    history_result = e2e_deployment.cli.run_command(["jupyter-deploy", "history", "show", "-l", "50"])
    history_content = history_result.stdout
    assert "Apply complete!" in history_content, "Expected 'Apply complete!' in history logs"
    assert "Outputs:" in history_content, "Expected 'Outputs:' section in history logs"
