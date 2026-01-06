# pytest-jupyter-deploy

Pytest plugin for E2E testing of jupyter-deploy templates.

## Overview

This package provides pytest fixtures and utilities for writing end-to-end tests for jupyter-deploy templates. It handles deployment lifecycle management, configuration loading, and provides helpers for testing web applications with Playwright.

## Installation

```bash
pip install pytest-jupyter-deploy
```

For UI testing with Playwright:
```bash
pip install pytest-jupyter-deploy[ui]
playwright install chromium
```

## Fixtures

- **`e2e_deployment`** (session-scoped): Manages deployment lifecycle (init, config, up, down)
- **`e2e_config`** (session-scoped): Provides access to suite configuration
- **`e2e_suite_dir`** (session-scoped): Path to the E2E tests directory
- **`github_oauth_app`** (module-scoped): Helper for GitHub OAuth2 Proxy authentication with passkey support

## Usage

The plugin is automatically loaded by pytest when installed. Use the provided fixtures in your tests.

### Example Test

```python
from pytest_jupyter_deploy.deployment import EndToEndDeployment

def test_host_running(e2e_deployment: EndToEndDeployment) -> None:
    """Test that the host is running."""
    e2e_deployment.ensure_deployed()
    host_status = e2e_deployment.cli.get_host_status()
    assert host_status == "running"
```

### Running Tests

```bash
# Run E2E tests
pytest -m e2e

# Run against existing deployment
pytest -m e2e --e2e-existing-project=sandbox3

# Capture screenshots on failure
pytest -m e2e --screenshot only-on-failure
```

For detailed documentation on running integration tests, see [CONTRIBUTING.md](../../CONTRIBUTING.md#run-integration-tests).

## License

The Pytest plugin for Jupyter Deploy templates is licensed under the [MIT License](LICENSE).
