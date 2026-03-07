"""E2E tests for jd projects commands and jd init --restore-project."""

import subprocess
import tempfile
from pathlib import Path

from pytest_jupyter_deploy.deployment import EndToEndDeployment


def _get_project_id(e2e_deployment: EndToEndDeployment) -> str:
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "show", "--project-id", "--text"])
    project_id = result.stdout.strip()
    assert project_id and project_id != "None", f"Expected a valid project ID, got '{project_id}'"
    return project_id


def _get_store_type(e2e_deployment: EndToEndDeployment) -> str:
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "show", "--store-type", "--text"])
    store_type = result.stdout.strip()
    assert store_type and store_type != "N/A", f"Expected a valid store type, got '{store_type}'"
    return store_type


def test_projects_list_contains_deployed_project(e2e_deployment: EndToEndDeployment) -> None:
    """Test that jd projects list includes the currently deployed project.

    This test:
    1. Ensures deployment exists
    2. Gets the project ID and store type from the deployed project
    3. Runs jd projects list --store-type <type> --text
    4. Verifies the deployed project appears in the list
    """
    e2e_deployment.ensure_deployed()

    project_id = _get_project_id(e2e_deployment)
    store_type = _get_store_type(e2e_deployment)

    result = e2e_deployment.cli.run_command(
        ["jupyter-deploy", "projects", "list", "--store-type", store_type, "--text"]
    )

    project_ids = result.stdout.strip().splitlines()
    assert project_id in project_ids, f"Expected project '{project_id}' in list output. Got: {project_ids}"


def test_projects_show_returns_deployed_project_details(e2e_deployment: EndToEndDeployment) -> None:
    """Test that jd projects show returns details for the deployed project.

    This test:
    1. Ensures deployment exists
    2. Gets the project ID and store type
    3. Runs jd projects show <project-id> --store-type <type> --text
    4. Verifies the output contains expected fields
    """
    e2e_deployment.ensure_deployed()

    project_id = _get_project_id(e2e_deployment)
    store_type = _get_store_type(e2e_deployment)

    result = e2e_deployment.cli.run_command(
        ["jupyter-deploy", "projects", "show", project_id, "--store-type", store_type, "--text"]
    )

    output = result.stdout.strip()
    assert f"project-id: {project_id}" in output, f"Expected project-id in output. Got: {output}"
    assert "template-name:" in output, f"Expected template-name in output. Got: {output}"
    assert "template-version:" in output, f"Expected template-version in output. Got: {output}"
    assert "engine:" in output, f"Expected engine in output. Got: {output}"
    assert "last-modified:" in output, f"Expected last-modified in output. Got: {output}"
    assert "file-count:" in output, f"Expected file-count in output. Got: {output}"


def test_restore_project_and_config(e2e_deployment: EndToEndDeployment) -> None:
    """Test that a project can be restored and reconfigured.

    This test:
    1. Ensures deployment exists
    2. Gets project ID and store type from deployed project
    3. Restores the project to a temp directory via jd init --restore-project
    4. Verifies jd show --info succeeds on the restored project
    5. Verifies jd config --skip-verify succeeds on the restored project
    """
    e2e_deployment.ensure_deployed()

    project_id = _get_project_id(e2e_deployment)
    store_type = _get_store_type(e2e_deployment)

    with tempfile.TemporaryDirectory() as tmpdir:
        restore_dir = Path(tmpdir) / "restored"

        # Restore project
        result = subprocess.run(
            [
                "jupyter-deploy",
                "init",
                str(restore_dir),
                "--restore-project",
                project_id,
                "--store-type",
                store_type,
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Restore failed: {result.stdout}\n{result.stderr}"
        assert restore_dir.exists(), "Restore directory should exist"

        # Verify jd show --info works on restored project
        result = subprocess.run(
            ["jupyter-deploy", "show", "--info"],
            capture_output=True,
            text=True,
            cwd=str(restore_dir),
        )
        assert result.returncode == 0, f"jd show --info failed: {result.stdout}\n{result.stderr}"
        assert "Store Type" in result.stdout, "Restored project should show Store Type"
        assert "Store ID" in result.stdout, "Restored project should show Store ID"

        # Verify jd config --skip-verify works on restored project
        result = subprocess.run(
            ["jupyter-deploy", "config", "--skip-verify"],
            capture_output=True,
            text=True,
            cwd=str(restore_dir),
            timeout=300,
        )
        assert result.returncode == 0, f"jd config --skip-verify failed: {result.stdout}\n{result.stderr}"
