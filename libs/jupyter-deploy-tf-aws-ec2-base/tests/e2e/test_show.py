"""E2E tests for jd show command."""

from jupyter_deploy.enum import ValueSource
from pytest_jupyter_deploy.deployment import EndToEndDeployment


def test_show_variables_list_matches_config(e2e_deployment: EndToEndDeployment) -> None:
    """Test that jd show --variables --list matches variables.yaml content.

    This test:
    1. Ensures deployment exists
    2. Reads variables.yaml to get expected variable names
    3. Runs jd show --variables --list --text
    4. Verifies all variables from yaml are present in output (order doesn't matter)
    """
    e2e_deployment.ensure_deployed()

    # Read variables config to get all variable names
    variables_config = e2e_deployment.get_variables_config()

    # Collect all variable names from all sections (required, required_sensitive, overrides, defaults)
    # jd show --variables --list shows ALL template variables
    expected_vars: set[str] = set()
    expected_vars.update(variables_config.required.keys())
    expected_vars.update(variables_config.required_sensitive.keys())
    expected_vars.update(variables_config.overrides.keys())
    expected_vars.update(variables_config.defaults.keys())

    # Run jd show --variables --list --text
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "show", "--variables", "--list", "--text"])

    # Parse comma-separated output (strip newlines that may be inserted by wrapping)
    output_vars = {var.strip().replace("\n", "") for var in result.stdout.strip().split(",") if var.strip()}

    # Verify size matches
    assert len(output_vars) == len(expected_vars), (
        f"Expected {len(expected_vars)} variables, got {len(output_vars)}. "
        f"Missing: {expected_vars - output_vars}, Extra: {output_vars - expected_vars}"
    )

    # Verify all names match (order doesn't matter)
    assert output_vars == expected_vars, (
        f"Variable names don't match. Missing: {expected_vars - output_vars}, Extra: {output_vars - expected_vars}"
    )


def test_show_outputs_list_returns_expected_outputs(e2e_deployment: EndToEndDeployment) -> None:
    """Test that jd show --outputs --list returns expected terraform outputs.

    This test:
    1. Ensures deployment exists
    2. Reads manifest to get all values whose source is "output"
    3. Runs jd show --outputs --list --text
    4. Verifies all manifest output values are present in the command output
    """
    e2e_deployment.ensure_deployed()

    # Read manifest to get expected output names
    manifest = e2e_deployment.get_manifest()

    # Collect all value names where source is "output"
    expected_outputs: set[str] = set()
    if manifest.values:
        for value in manifest.values:
            if value.source == ValueSource.TEMPLATE_OUTPUT:
                expected_outputs.add(value.source_key)

    # Run jd show --outputs --list --text
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "show", "--outputs", "--list", "--text"])

    # Parse comma-separated output (strip newlines that may be inserted by wrapping)
    output_names = {name.strip().replace("\n", "") for name in result.stdout.strip().split(",") if name.strip()}

    # Verify all manifest output values are present
    assert expected_outputs.issubset(output_names), (
        f"Missing expected outputs: {expected_outputs - output_names}. Got outputs: {output_names}"
    )


def test_show_variable_domain_matches_config(e2e_deployment: EndToEndDeployment) -> None:
    """Test that jd show --variable domain returns value from variables.yaml.

    This test:
    1. Ensures deployment exists
    2. Reads domain value from variables.yaml
    3. Queries domain via jd show --variable domain --text
    4. Verifies values match
    """
    e2e_deployment.ensure_deployed()

    # Read domain from variables config
    variables_config = e2e_deployment.get_variables_config()

    # Domain should be in required section
    expected_domain = variables_config.required["domain"]

    # Query domain via jd show
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "show", "--variable", "domain", "--text"])
    actual_domain = result.stdout.strip()

    assert actual_domain == expected_domain, f"Expected domain '{expected_domain}', got '{actual_domain}'"


def test_show_output_jupyter_url_matches_variables(e2e_deployment: EndToEndDeployment) -> None:
    """Test that jd show --output jupyter_url returns URL matching variables.

    This test:
    1. Ensures deployment exists
    2. Reads domain and subdomain from variables.yaml
    3. Constructs expected URL as https://{subdomain}.{domain}
    4. Queries jupyter_url via jd show --output jupyter_url --text
    5. Verifies URLs match
    """
    e2e_deployment.ensure_deployed()

    # Read domain and subdomain from variables config
    variables_config = e2e_deployment.get_variables_config()
    domain = variables_config.required["domain"]
    subdomain = variables_config.required["subdomain"]

    # Construct expected URL
    expected_url = f"https://{subdomain}.{domain}"

    # Query jupyter_url via jd show
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "show", "--output", "jupyter_url", "--text"])
    actual_url = result.stdout.strip()

    assert actual_url == expected_url, f"Expected URL '{expected_url}', got '{actual_url}'"


def test_show_default_does_not_error(e2e_deployment: EndToEndDeployment) -> None:
    """Test that jd show (no flags) executes successfully.

    This test:
    1. Ensures deployment exists
    2. Runs jd show with no flags
    3. Verifies command succeeds
    4. Verifies output contains expected section headers
    """
    e2e_deployment.ensure_deployed()

    # Run jd show with no flags
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "show"])

    # Verify command succeeded (returncode 0 is implicit in run_command)
    assert result.returncode == 0, f"jd show should succeed, got returncode {result.returncode}"

    # Verify output contains expected sections
    assert "Jupyter Deploy Project Information" in result.stdout, "Expected project info section"
    assert "Project Variables" in result.stdout, "Expected variables section"
    assert "Project Outputs" in result.stdout, "Expected outputs section"


def test_show_template_name_matches_manifest(e2e_deployment: EndToEndDeployment) -> None:
    """Test that jd show --template-name returns value from manifest.yaml.

    This test:
    1. Ensures deployment exists
    2. Reads template name from manifest.yaml
    3. Queries template name via jd show --template-name --text
    4. Verifies values match
    """
    e2e_deployment.ensure_deployed()

    # Read template name from manifest
    manifest = e2e_deployment.get_manifest()

    expected_name = manifest.template.name

    # Query template name via jd show
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "show", "--template-name", "--text"])
    actual_name = result.stdout.strip()

    assert actual_name == expected_name, f"Expected template name '{expected_name}', got '{actual_name}'"


def test_show_template_version_matches_manifest(e2e_deployment: EndToEndDeployment) -> None:
    """Test that jd show --template-version returns value from manifest.yaml.

    This test:
    1. Ensures deployment exists
    2. Reads template version from manifest.yaml
    3. Queries template version via jd show --template-version --text
    4. Verifies values match
    """
    e2e_deployment.ensure_deployed()

    # Read template version from manifest
    manifest = e2e_deployment.get_manifest()

    expected_version = manifest.template.version

    # Query template version via jd show
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "show", "--template-version", "--text"])
    actual_version = result.stdout.strip()

    assert actual_version == expected_version, f"Expected template version '{expected_version}', got '{actual_version}'"
