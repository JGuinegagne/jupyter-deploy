"""E2E tests for CLI behavior with undeployed projects."""

from pytest_jupyter_deploy.deployment import EndToEndDeployment
from pytest_jupyter_deploy.undeployed_project import undeployed_project


def test_open_does_not_error(e2e_deployment: EndToEndDeployment) -> None:
    """Test that jd open does not error when project is not deployed.

    This test:
    1. Creates a temporary project directory
    2. Runs `jd init` but NOT `jd config` or `jd up`
    3. Runs `jd open` and verifies it doesn't crash
    4. Verifies the output contains helpful message about URL not being available
    """
    with undeployed_project(e2e_deployment.suite_config) as (project_path, cli):
        # Run jd open (should not crash)
        result = cli.run_command(["jupyter-deploy", "open"])

        # Verify it doesn't error and provides helpful message
        assert result.returncode == 0, f"jd open should not fail, got: {result.stderr}"
        assert "URL not available." in result.stdout, "Expected 'URL not available.' message in output"
        assert "jd config" in result.stdout, "Expected suggestion to run 'jd config'"
        assert "jd up" in result.stdout, "Expected suggestion to run 'jd up'"


def test_show_does_not_error(e2e_deployment: EndToEndDeployment) -> None:
    """Test that jd show does not error when project is not deployed.

    This test:
    1. Creates a temporary project directory
    2. Runs `jd init` but NOT `jd config` or `jd up`
    3. Runs `jd show` and verifies it doesn't crash
    4. Verifies helpful message is displayed
    """
    with undeployed_project(e2e_deployment.suite_config) as (project_path, cli):
        # Run jd show (should not crash)
        result = cli.run_command(["jupyter-deploy", "show"])

        # Verify it doesn't error and provides helpful message
        assert result.returncode == 0, f"jd show should not fail, got: {result.stderr}"
        assert "No outputs available." in result.stdout, "Expected 'No outputs available.' message in output"
