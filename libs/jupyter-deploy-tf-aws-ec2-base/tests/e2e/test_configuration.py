"""E2E tests for project configuration validation."""

from pytest_jupyter_deploy.deployment import EndToEndDeployment
from pytest_jupyter_deploy.plugin import skip_if_testvars_not_set
from pytest_jupyter_deploy.undeployed_project import undeployed_project


@skip_if_testvars_not_set(
    [
        "JD_E2E_VAR_DOMAIN",
        "JD_E2E_VAR_EMAIL",
        "JD_E2E_VAR_OAUTH_APP_CLIENT_ID",
        "JD_E2E_VAR_OAUTH_ALLOWED_ORG",
        "JD_E2E_VAR_OAUTH_ALLOWED_TEAMS",
        "JD_E2E_VAR_OAUTH_ALLOWED_USERNAMES",
        "JD_E2E_VAR_SUBDOMAIN",
        "JD_E2E_VAR_OAUTH_APP_CLIENT_SECRET",
    ]
)
def test_project_is_configurable(e2e_deployment: EndToEndDeployment) -> None:
    """Test that a project can be successfully configured.

    This test validates that the template is correctly set up and "deployable" by:
    1. Creating a temporary project directory (in /tmp)
    2. Running `jd init` to initialize the project
    3. Copying the test configuration variables
    4. Running `jd config -s` to configure the project
    5. Verifying that configuration completes without errors

    This is particularly useful for LLM-driven template development to ensure
    templates are correctly configured before attempting deployment.

    If configuration fails, the test displays:
    - The temporary project directory path
    - The log file path for debugging
    """
    with undeployed_project(e2e_deployment.suite_config) as (project_path, cli):
        # Run jd config -s and save logs (using the custom cli)
        # This will raise RuntimeError with helpful paths if it fails.
        # Pass the cli from undeployed_project context manager to ensure
        # that any JD calls is made against the /tmp dir.
        e2e_deployment.configure_project(cli=cli)

        # If we reach here, configuration succeeded
        # Verify the engine directory was created (a sign of successful config)
        engine_dir = project_path / "engine"
        assert engine_dir.exists(), f"Engine directory should exist after config: {engine_dir}"
