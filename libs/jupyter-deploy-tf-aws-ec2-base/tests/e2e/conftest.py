"""E2E test configuration for aws-ec2-base template.

The pytest-jupyter-deploy plugin provides these fixtures automatically:
- e2e_config: Load configuration from suite.yaml
- e2e_deployment: Deploy infrastructure once per session
- github_oauth_app: GitHub OAuth2 Proxy authentication helper
"""

import os
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


@pytest.fixture(scope="session")
def logged_user() -> str:
    """Return GitHub username the browser is logged in as

    Raises:
        ValueError: If JD_E2E_USER is not set
    """
    user = os.getenv("JD_E2E_USER")
    if not user:
        raise ValueError("JD_E2E_USER environment variable must be set")
    return user


@pytest.fixture(scope="session")
def safe_user() -> str:
    """Returns a trusted GitHub username the browser is not logged in as.

    Raises:
        ValueError: If JD_E2E_SAFE_USER is not set
    """
    user = os.getenv("JD_E2E_SAFE_USER")
    if not user:
        raise ValueError("JD_E2E_SAFE_USER environment variable must be set")
    return user


@pytest.fixture(scope="session")
def safe_org() -> str:
    """Returns a safe organization name for testing.

    Raises:
        ValueError: If JD_E2E_SAFE_ORG is not set
    """
    org = os.getenv("JD_E2E_SAFE_ORG")
    if not org:
        raise ValueError("JD_E2E_SAFE_ORG environment variable must be set")
    return org


@pytest.fixture(scope="session")
def logged_org() -> str:
    """Return GitHub organization the browser user belongs to.

    Raises:
        ValueError: If JD_E2E_ORG is not set
    """
    org = os.getenv("JD_E2E_ORG")
    if not org:
        raise ValueError("JD_E2E_ORG environment variable must be set")
    return org


@pytest.fixture(scope="session")
def logged_team() -> str:
    """Return GitHub team the browser user belongs to.

    Raises:
        ValueError: If JD_E2E_TEAM is not set
    """
    team = os.getenv("JD_E2E_TEAM")
    if not team:
        raise ValueError("JD_E2E_TEAM environment variable must be set")
    return team


@pytest.fixture(scope="session")
def safe_team() -> str:
    """Returns a safe team name the logged user does not belong to.

    Raises:
        ValueError: If JD_E2E_SAFE_TEAM is not set
    """
    team = os.getenv("JD_E2E_SAFE_TEAM")
    if not team:
        raise ValueError("JD_E2E_SAFE_TEAM environment variable must be set")
    return team


@pytest.fixture(scope="session")
def larger_instance_type() -> str:
    """Returns a larger instance type for upgrade tests.

    Raises:
        ValueError: If JD_E2E_LARGER_INSTANCE is not set
    """
    larger_instance_type = os.getenv("JD_E2E_LARGER_INSTANCE")
    if not larger_instance_type:
        raise ValueError("JD_E2E_LARGER_INSTANCE environment variable must be set")
    return larger_instance_type


@pytest.fixture(scope="session")
def larger_log_retention_days() -> int:
    """Returns a larger log retention days value for config change tests.

    Raises:
        ValueError: If JD_E2E_LARGER_LOG_RETENTION_DAYS is not set
    """
    larger_log_retention_days = os.getenv("JD_E2E_LARGER_LOG_RETENTION_DAYS")
    if not larger_log_retention_days:
        raise ValueError("JD_E2E_LARGER_LOG_RETENTION_DAYS environment variable must be set")
    return int(larger_log_retention_days)
