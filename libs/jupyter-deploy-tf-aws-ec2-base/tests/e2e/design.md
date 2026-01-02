# E2E Tests Design - Fixture-Based with Pytest Plugin Package

## Overview

End-to-end tests using pytest fixtures provided by a reusable `pytest-jupyter-deploy` PyPI package. Templates import fixtures automatically through the pytest plugin system and write clean test functions without boilerplate deployment logic.

## Architecture

### Two-Package Design

```
┌─────────────────────────────────────────┐
│      pytest-jupyter-deploy (PyPI)      │
│                                         │
│  ├─ Pytest plugin hooks                │
│  ├─ Deployment lifecycle management    │
│  ├─ CLI command helpers                │
│  └─ Config loading (suite.yaml)        │
└────────────┬────────────────────────────┘
             │ pip install
             ▼
┌─────────────────────────────────────────┐
│  Template: jupyter-deploy-tf-aws-ec2   │
│                                         │
│  tests/e2e/                             │
│  ├─ suite.yaml  (template config)      │
│  ├─ conftest.py (optional custom)      │
│  └─ test_*.py   (test functions)       │
└─────────────────────────────────────────┘
```

### Benefits

**For Test Plugin Package:**
- Single source of truth for deployment lifecycle
- Reusable across all templates
- Easy to improve and maintain
- Standard pytest plugin architecture

**For Templates:**
- Zero boilerplate - just write tests
- Focus on template-specific logic
- Clean, readable test files
- Automatic updates when plugin improves

## Test Plugin Package Structure

```
pytest-jupyter-deploy/
├── pytest_jupyter_deploy/
│   ├── __init__.py
│   ├── plugin.py              # Pytest hooks + fixture definitions
│   ├── deployment.py          # Deployment lifecycle
│   ├── config.py              # Suite config loading
│   └── py.typed               # Type hints marker
│
├── tests/
│   └── unit/                  # Test the plugin itself
│
├── pyproject.toml
└── README.md
```

### Key Components

**plugin.py** - Pytest plugin entry point:
- Pytest hooks (`pytest_addoption`, `pytest_configure`)
- Core fixtures (`e2e_config`, `e2e_deployment`, `jd_cli`)
- Plugin registration via `pytest11` entry point

**deployment.py** - Infrastructure lifecycle:
- `EndToEndDeployment` class managing `jd init`, `jd config`, `jd up`, `jd down`
- `ensure_deployed()` method for lazy deployment
- `is_available()` method to check if deployment exists
- Terraform output reading
- Sandbox directory management (defaults to `sandbox-e2e/<template-name>/<timestamp>`)
- Supports `JD_E2E_PROJECT_DIR` environment variable to override sandbox location

**config.py** - Configuration management:
- `SuiteConfig` class loading `suite.yaml`
- Environment variable expansion (`${VAR_NAME}`)
- `.env.test` file loading

### Fixture Definitions (plugin.py)

```python
"""Pytest plugin - defines fixtures for E2E testing."""
import pytest
from pathlib import Path
from datetime import datetime

def pytest_addoption(parser):
    """Add custom command-line options."""
    parser.addoption(
        "--no-cleanup",
        action="store_true",
        help="Skip infrastructure cleanup after tests"
    )


@pytest.fixture(scope="session")
def e2e_config(request):
    """
    Load E2E test configuration from suite.yaml and .env.test.

    Loads from tests/e2e/ directory.
    Expands environment variables in deployment config.
    """
    from .config import SuiteConfig

    suite_yaml_path = request.config.getoption("--suite-config", "tests/e2e/suite.yaml")
    config = SuiteConfig.load(suite_yaml_path)

    return config


@pytest.fixture(scope="session")
def e2e_deployment(e2e_config, request):
    """
    Provide a deployment manager for the test session.

    Creates sandbox-e2e/<template-name>/YYYYMMDD-HHMMSS/
    The deployment is lazy - infrastructure is only deployed when ensure_deployed() is called.
    This allows tests to opt-in to using the deployment.

    Yields EndToEndDeployment instance with:
    - ensure_deployed(): Deploy infrastructure if not already deployed
    - is_available(): Check if deployment exists
    - outputs: Terraform outputs (jupyter_url, instance_id, etc.)

    Cleanup: jd down (based on test results and config)
    """
    from .deployment import EndToEndDeployment, create_sandbox_dir

    # Create timestamped sandbox directory
    template_name = e2e_config.template.get("name", "unknown")
    sandbox_dir = create_sandbox_dir(template_name)

    # Create deployment manager (does not deploy yet)
    deployment = EndToEndDeployment(working_dir=sandbox_dir, config=e2e_config)

    yield deployment

    # Cleanup based on test results
    no_cleanup = request.config.getoption("--no-cleanup")
    tests_failed = request.session.testsfailed
    if not no_cleanup and e2e_config.should_cleanup(tests_failed):
        deployment.down()

```

## Template E2E Tests Structure

```
tests/e2e/
├── design.md           # This file (temporary)
├── suite.yaml          # Template-specific configuration
├── .env.test.example   # Example environment variables
│
├── conftest.py         # Optional: custom template fixtures
│
├── test_*.py           # Test cases
```

### Template conftest.py (Optional)

```python
"""E2E test configuration for aws-ec2-base template.

The pytest-jupyter-deploy plugin provides these fixtures automatically:
- e2e_config: Load configuration from suite.yaml
- e2e_deployment: Deploy infrastructure once per session
- jd_cli: CLI command helper

This file can be used to add template-specific fixtures if needed.
"""

# Add template-specific fixtures here if needed
```

### Example Template Test: test_cli_users.py

```python
"""Test user management commands."""

def test_list_users(e2e_deployment, e2e_config):
    """Test listing allowed users."""
    # Ensure infrastructure is deployed
    e2e_deployment.ensure_deployed()

    # Access deployment outputs
    jupyter_url = e2e_deployment.outputs.get("jupyter_url")
    assert jupyter_url is not None

    # TODO: Add CLI helper for running jd commands
    # result = jd_cli.users.list()
    # result.assert_success()
    # result.assert_in_stdout(e2e_config.deployment["oauth_allowed_usernames"][0])
```

## Configuration

### suite.yaml

```yaml
# Template identification
template:
  name: aws-ec2-base
  engine: terraform
  provider: aws

# Deployment configuration (values from environment)
deployment:
  domain: "${JD_E2E_VAR_DOMAIN}"
  subdomain: "${JD_E2E_VAR_SUBDOMAIN}"
  letsencrypt_email: "${JD_E2E_VAR_EMAIL}"
  oauth_app_client_id: "${JD_E2E_VAR_OAUTH_APP_CLIENT_ID}"
  oauth_app_client_secret: "${JD_E2E_VAR_OAUTH_APP_CLIENT_SECRET}"
  oauth_allowed_usernames: "${JD_E2E_VAR_OAUTH_ALLOWED_USERNAMES}"
  oauth_allowed_org: "${JD_E2E_VAR_OAUTH_ALLOWED_ORG}"
  oauth_allowed_teams: "${JD_E2E_VAR_OAUTH_ALLOWED_TEAMS}"
  instance_type: "t3.small"

# Test behavior
test:
  deployment_timeout: 1800
  teardown_timeout: 600
  cleanup_on_success: true
  cleanup_on_failure: false
```

### .env.test.example

```bash
# E2E Test Environment Configuration
# Copy this file to .env.test and fill in your values

# Template variables
JD_E2E_VAR_DOMAIN=example.com
JD_E2E_VAR_SUBDOMAIN=test-e2e
JD_E2E_VAR_EMAIL=test@example.com
JD_E2E_VAR_OAUTH_ALLOWED_USERNAMES=username1,username2
JD_E2E_VAR_OAUTH_ALLOWED_ORG=
JD_E2E_VAR_OAUTH_ALLOWED_TEAMS=
JD_E2E_VAR_OAUTH_APP_CLIENT_ID=00000aaaaa11111bbbbb
JD_E2E_VAR_OAUTH_APP_CLIENT_SECRET=00000aaaaa11111bbbbb22222ccccc
```

## Running Tests

### Development Workflow

```bash
# Create .env.test
cp libs/jupyter-deploy-tf-aws-ec2-base/tests/e2e/.env.test.example libs/jupyter-deploy-tf-aws-ec2-base/tests/e2e/.env.test
# Edit .env.test with your credentials

# Run all E2E tests
uv run pytest tests/e2e/

# Run specific test file
uv run pytest libs/jupyter-deploy-tf-aws-ec2-base/tests/e2e/test_cli_users.py

# Keep infrastructure for debugging
uv run pytest tests/e2e/ --no-cleanup
```

### CI/CD Workflow

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests

on:
  pull_request:
    paths:
      - 'libs/jupyter-deploy-tf-aws-ec2-base/**'
  schedule:
    - cron: '0 2 * * *'
  workflow_dispatch:

jobs:
  e2e:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_E2E_TEST_ROLE }}
          aws-region: us-west-2

      - name: Install UV
        uses: ./.github/actions/install-uv
        with:
          python-version: '3.13'

      - name: Install dependencies
        working-directory: libs/jupyter-deploy-tf-aws-ec2-base
        run: uv sync

      - name: Create .env.test
        working-directory: libs/jupyter-deploy-tf-aws-ec2-base/tests/e2e
        run: |
          cat > .env.test <<EOF
          JD_E2E_VAR_DOMAIN=${{ secrets.JD_E2E_VAR_DOMAIN }}
          JD_E2E_VAR_SUBDOMAIN=test-${{ github.run_id }}
          JD_E2E_VAR_EMAIL=${{ secrets.JD_E2E_VAR_EMAIL }}
          JD_E2E_VAR_OAUTH_ALLOWED_USERNAMES=${{ secrets.JD_E2E_VAR_OAUTH_ALLOWED_USERNAMES }}
          JD_E2E_VAR_OAUTH_ALLOWED_ORG=${{ secrets.JD_E2E_VAR_OAUTH_ALLOWED_ORG }}
          JD_E2E_VAR_OAUTH_ALLOWED_TEAMS=${{ secrets.JD_E2E_VAR_OAUTH_ALLOWED_TEAMS }}
          JD_E2E_VAR_OAUTH_APP_CLIENT_ID=${{ secrets.JD_E2E_VAR_OAUTH_APP_CLIENT_ID }}
          JD_E2E_VAR_OAUTH_APP_CLIENT_SECRET=${{ secrets.JD_E2E_VAR_OAUTH_APP_CLIENT_SECRET }}
          EOF

      - name: Run E2E tests
        working-directory: libs/jupyter-deploy-tf-aws-ec2-base
        run: |
          uv run pytest tests/e2e/ \
            -v \
            --junitxml=test-results/junit.xml

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: e2e-test-results
          path: |
            libs/jupyter-deploy-tf-aws-ec2-base/test-results/
            libs/jupyter-deploy-tf-aws-ec2-base/sandbox-e2e/*/deployment.log
```

## Development Phases

### Phase 1: Plugin Package Foundation ✅ CURRENT

**pytest-jupyter-deploy package:**
- [x] Package structure and pyproject.toml
- [x] Pytest plugin entry point (`plugin.py`)
- [x] Type hints marker (`py.typed`)
- [x] Core fixtures (e2e_config, e2e_deployment)
- [x] EndToEndDeployment lifecycle class with ensure_deployed()
- [x] Config loading (suite.yaml + .env)
- [ ] CLI command helpers (jd_cli fixture) - Phase 2

**Testing:**
- [x] Unit tests for plugin itself
- [ ] Config loading tests
- [ ] Deployment lifecycle tests
- [ ] CLI helper tests

### Phase 2: CLI Testing Support

**pytest-jupyter-deploy:**
- [ ] Complete CLI helper (all command groups)
- [ ] Command result assertions (assert_success, assert_in_stdout)
- [ ] Timeout handling
- [ ] Error capture

**Template E2E tests:**
- [x] suite.yaml configuration
- [x] conftest.py structure
- [ ] test_cli_project.py
- [ ] test_cli_host.py
- [ ] test_cli_users.py
- [ ] test_cli_teams.py
- [ ] test_cli_organization.py
- [ ] test_cli_server.py

### Phase 3: UI Testing Support (Future)

**pytest-jupyter-deploy:**
- [ ] Browser fixture (Playwright)
- [ ] Page fixture (incognito mode)
- [ ] OAuth automation helpers
- [ ] Jupyter UI interaction helpers
- [ ] Screenshot on failure

**Template E2E tests:**
- [ ] test_oauth_flow.py
- [ ] test_ui_jupyter.py

### Phase 4: Polish & Release (Future)

**pytest-jupyter-deploy:**
- [ ] Documentation (README, API docs)
- [ ] Examples
- [ ] CI/CD for plugin package
- [ ] Publish to PyPI (v0.1.0)

**Template:**
- [ ] CI/CD integration
- [ ] Documentation
- [ ] README with usage examples

## Success Criteria

- [x] Plugin package properly structured
- [ ] All CLI commands tested in template
- [ ] Tests pass consistently (>95%)
- [ ] Full suite runs in <30 minutes
- [ ] CI/CD integrated
- [ ] Zero boilerplate in template tests
- [ ] Documentation complete

## Benefits Summary

### For Test Plugin Package
- ✅ Single source of truth
- ✅ Reusable across templates
- ✅ Easy to improve
- ✅ Standard pytest plugin patterns

### For Templates
- ✅ Zero boilerplate
- ✅ Clean test files
- ✅ Focus on template logic
- ✅ Automatic fixture availability

### For Developers
- ✅ Standard pytest workflow
- ✅ IDE autocomplete on fixtures
- ✅ Composable fixtures
- ✅ Easy to debug
