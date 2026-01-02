"""E2E test configuration for aws-ec2-base template.

The pytest-jupyter-deploy plugin provides these fixtures automatically:
- e2e_config: Load configuration from suite.yaml
- e2e_deployment: Deploy infrastructure once per session
- github_oauth_app: GitHub OAuth2 Proxy authentication helper

This file configures Playwright to load saved authentication state.
"""

from pathlib import Path
from typing import Any

import pytest


def pytest_collection_modifyitems(items: list) -> None:
    """Automatically mark all tests in this directory as e2e tests."""
    for item in items:
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, Any], request: pytest.FixtureRequest) -> dict[str, Any]:
    """Configure browser context to load saved authentication state.

    If .auth/github-oauth-state.json exists, load it to skip authentication.
    To create this file, run: scripts/github_auth_setup.py --project-dir=<project-dir>
    """
    storage_state_path = Path.cwd() / ".auth" / "github-oauth-state.json"

    # Check if running in CI mode
    is_ci = request.config.getoption("--ci", default=False)

    # Skip loading storage state in CI mode (will use username/password login)
    if is_ci:
        return browser_context_args

    if storage_state_path.exists():
        return {
            **browser_context_args,
            "storage_state": str(storage_state_path),
        }

    return browser_context_args
