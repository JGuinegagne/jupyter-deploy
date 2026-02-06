"""E2E tests for project configuration validation."""

import re

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
def test_gitignore_generated_after_init(e2e_deployment: EndToEndDeployment) -> None:
    """Test that .gitignore is generated after jd init.

    This test validates that the documentation generator creates a .gitignore file with:
    1. Correct JD internal state patterns (.jd-history/, jdout-*, jdinputs.*)
    2. Engine-specific patterns (terraform: .terraform/, *.tfstate*, .terraform.lock.hcl)
    """
    with undeployed_project(e2e_deployment.suite_config) as (project_path, cli):
        # Check that .gitignore exists
        gitignore_path = project_path / ".gitignore"
        assert gitignore_path.exists(), f".gitignore should exist after init: {gitignore_path}"

        # Read and verify content
        gitignore_content = gitignore_path.read_text()

        # Verify JD internal patterns
        assert ".jd-history/" in gitignore_content, ".gitignore should contain .jd-history/ pattern"
        assert "jdout-" in gitignore_content, ".gitignore should contain jdout-* pattern"
        assert "jdinputs." in gitignore_content, ".gitignore should contain jdinputs.* pattern"

        # Verify terraform-specific patterns (since this is the base template)
        assert ".terraform/" in gitignore_content, ".gitignore should contain .terraform/ pattern"
        assert re.search(r"\*\.tfstate", gitignore_content), ".gitignore should contain *.tfstate pattern"
        assert ".terraform.lock.hcl" in gitignore_content, ".gitignore should contain .terraform.lock.hcl pattern"

        # Verify the template variable was replaced (should not contain the placeholder)
        assert "{{ engine_ignore_patterns }}" not in gitignore_content, (
            ".gitignore should not contain template placeholders"
        )


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
def test_troubleshoot_md_exists_after_init(e2e_deployment: EndToEndDeployment) -> None:
    """Test that TROUBLESHOOT.md exists after jd init.

    This test validates that TROUBLESHOOT.md is copied from the template.
    """
    with undeployed_project(e2e_deployment.suite_config) as (project_path, cli):
        # Check that TROUBLESHOOT.md exists
        troubleshoot_path = project_path / "TROUBLESHOOT.md"
        assert troubleshoot_path.exists(), f"TROUBLESHOOT.md should exist after init: {troubleshoot_path}"

        # Read and verify basic content
        troubleshoot_content = troubleshoot_path.read_text()
        assert "# Troubleshooting Guide" in troubleshoot_content, "Should have main heading"


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
def test_agent_md_generated_after_init(e2e_deployment: EndToEndDeployment) -> None:
    """Test that AGENT.md is generated after jd init with all snippets substituted.

    This test validates that:
    1. AGENT.md is created
    2. AGENT.md.template is removed after generation
    3. All snippet placeholders are substituted
    4. Key sections from template are present
    """
    with undeployed_project(e2e_deployment.suite_config) as (project_path, cli):
        # Check that AGENT.md exists
        agent_path = project_path / "AGENT.md"
        assert agent_path.exists(), f"AGENT.md should exist after init: {agent_path}"

        # Check that AGENT.md.template was removed
        agent_template_path = project_path / "AGENT.md.template"
        assert not agent_template_path.exists(), (
            f"AGENT.md.template should be removed after init: {agent_template_path}"
        )

        # Read and verify content
        agent_content = agent_path.read_text()

        # Verify main sections from template
        assert "# Jupyter-deploy: Terraform AWS EC2 base template" in agent_content, "Should have template heading"
        assert "## Project organization" in agent_content, "Should have project organization section"
        assert "## Usage" in agent_content, "Should have usage section"
        assert "## The terraform project" in agent_content, "Should have terraform project section"
        assert "## The deployed EC2 instance" in agent_content, "Should have EC2 instance section"

        # Verify key commands are documented
        assert "jd config" in agent_content, "Should document config command"
        assert "jd up" in agent_content, "Should document up command"
        assert "jd server status" in agent_content, "Should document server status command"
        assert "jd host status" in agent_content, "Should document host status command"
        assert "jd host exec" in agent_content, "Should document host exec command"
        assert "jd users" in agent_content, "Should document users commands"
        assert "jd organization" in agent_content, "Should document organization commands"
        assert "jd teams" in agent_content, "Should document teams commands"

        # Verify no template placeholders remain
        assert "{{" not in agent_content, "Should not contain template placeholders"
        assert "}}" not in agent_content, "Should not contain template placeholders"
