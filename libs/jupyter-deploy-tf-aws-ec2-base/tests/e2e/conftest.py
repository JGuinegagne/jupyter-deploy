"""E2E test configuration for aws-ec2-base template.

The pytest-jupyter-deploy plugin provides these fixtures automatically:
- e2e_config: Load configuration from suite.yaml
- e2e_deployment: Deploy infrastructure once per session
- github_oauth_app: GitHub OAuth2 Proxy authentication helper
"""

from typing import Any

import pytest
from pytest_jupyter_deploy.plugin import handle_browser_context_args


def pytest_collection_modifyitems(items: list) -> None:
    """Automatically mark all tests in this directory as e2e tests."""
    for item in items:
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, Any], request: pytest.FixtureRequest) -> dict[str, Any]:
    """Configure browser context to load saved authentication state.

    This fixture overrides pytest-playwright's browser_context_args to load
    saved GitHub OAuth cookies from .auth/github-oauth-state.json.
    """
    return handle_browser_context_args(browser_context_args, request)
