"""Pytest plugin - defines fixtures for E2E testing."""

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page

from pytest_jupyter_deploy import constants
from pytest_jupyter_deploy.deployment import EndToEndDeployment
from pytest_jupyter_deploy.oauth2_proxy.github import GitHubOAuth2ProxyApplication
from pytest_jupyter_deploy.suite_config import SuiteConfig


def pytest_addoption(parser: Any) -> None:
    """Add custom command-line options.

    Args:
        parser: Pytest parser object
    """
    parser.addoption(
        "--no-cleanup",
        action="store_true",
        help="Skip infrastructure cleanup after tests",
    )
    parser.addoption(
        "--e2e-tests-dir",
        action="store",
        default=f"{constants.TESTS_DIR}/{constants.E2E_TESTS_DIR}",
        help="Path to E2E tests directory",
    )
    parser.addoption(
        "--e2e-config-name",
        action="store",
        default="base",
        help=f"Configuration name to use from {constants.CONFIGURATIONS_DIR}/ directory",
    )
    parser.addoption(
        "--e2e-existing-project",
        action="store",
        default=None,
        help="Path to existing jupyter-deploy project (skips deployment, uses existing infrastructure)",
    )
    parser.addoption(
        "--deployment-timeout-seconds",
        action="store",
        type=int,
        default=1800,
        help="Timeout in seconds for deployment (default: 1800)",
    )
    parser.addoption(
        "--teardown-timeout-seconds",
        action="store",
        type=int,
        default=600,
        help="Timeout in seconds for teardown (default: 600)",
    )
    parser.addoption(
        "--ci",
        action="store_true",
        default=False,
        help="CI mode: use GITHUB_USERNAME/GITHUB_PASSWORD for authentication without 2FA",
    )


@pytest.fixture(scope="session")
def e2e_suite_dir(request: pytest.FixtureRequest) -> Path:
    """Get E2E tests directory path.

    Args:
        request: Pytest fixture request

    Returns:
        Path to E2E tests directory
    """
    tests_dir = request.config.getoption("--e2e-tests-dir")
    if isinstance(tests_dir, str) and tests_dir:
        return Path(tests_dir)
    else:
        # Fallback: use pytest's invocation directory
        return Path(request.config.invocation_params.dir)


@pytest.fixture(scope="session")
def e2e_config(e2e_suite_dir: Path, request: pytest.FixtureRequest) -> SuiteConfig:
    """Load E2E test configuration from suite.yaml.

    Args:
        e2e_suite_dir: E2E tests directory path
        request: Pytest fixture request

    Returns:
        SuiteConfig instance with loaded configuration
    """
    existing_project = request.config.getoption("--e2e-existing-project")

    existing_project_dir = Path(existing_project) if isinstance(existing_project, str) and existing_project else None
    return SuiteConfig(suite_dir=e2e_suite_dir, existing_project_dir=existing_project_dir)


@pytest.fixture(scope="session")
def e2e_deployment(
    e2e_config: SuiteConfig, request: pytest.FixtureRequest
) -> Generator[EndToEndDeployment, None, None]:
    """Deploy infrastructure once per test session.

    This fixture:
    1. Creates a sandbox directory ({SANDBOX_E2E_DIR}/<template-name>/<timestamp>/)
    2. Manages deployment lifecycle (init, config, up, down)
    3. Yields an EndToEndDeployment instance
    4. Handles cleanup based on test results and configuration

    The deployment is lazy - it only deploys when ensure_deployed() is called.
    This allows tests to opt-in to using the deployment.

    Args:
        e2e_config: E2E configuration fixture
        e2e_suite_dir: E2E tests directory path
        request: Pytest fixture request

    Yields:
        EndToEndDeployment instance
    """
    # Get configuration options
    deployment_timeout = request.config.getoption("--deployment-timeout-seconds")
    teardown_timeout = request.config.getoption("--teardown-timeout-seconds")

    # to keep mypy happy
    deployment_timeout_seconds = deployment_timeout if isinstance(deployment_timeout, int) else 1800
    teardown_timeout_seconds = teardown_timeout if isinstance(teardown_timeout, int) else 600

    # Create deployment manager (does not deploy yet)
    deployment = EndToEndDeployment(
        suite_config=e2e_config,
        deployment_timeout_seconds=deployment_timeout_seconds,
        teardown_timeout_seconds=teardown_timeout_seconds,
    )

    yield deployment

    # Cleanup only projects created by the deployment when --no-cleanup is not set.
    no_cleanup = request.config.getoption("--no-cleanup")

    if no_cleanup or e2e_config.references_existing_project():
        return
    else:
        deployment.ensure_destroyed()


def handle_browser_context_args(browser_context_args: dict[str, Any], request: pytest.FixtureRequest) -> dict[str, Any]:
    """Configure browser context to load saved authentication state.

    This helper function should be called from test suite's conftest.py browser_context_args fixture.
    It loads the saved storage state if available, allowing tests to reuse authentication
    without re-authenticating.

    Args:
        browser_context_args: The base browser context args from pytest-playwright
        request: Pytest fixture request

    Returns:
        Updated browser context args with storage_state if available
    """
    # Check if running in CI mode
    is_ci = request.config.getoption("--ci", default=False)

    # Skip loading storage state in CI mode (will use username/password login)
    if is_ci:
        return {**browser_context_args}

    # Load storage state if file exists
    storage_state_path = Path.cwd() / constants.AUTH_DIR / constants.GITHUB_OAUTH_STATE_FILE

    if storage_state_path.exists():
        return {
            **browser_context_args,
            "storage_state": str(storage_state_path),
        }

    return {**browser_context_args}


@pytest.fixture(scope="function")
def github_oauth_app(
    page: Page, e2e_deployment: EndToEndDeployment, request: pytest.FixtureRequest
) -> GitHubOAuth2ProxyApplication:
    """Create a GitHub OAuth2 Proxy application helper.

    This fixture provides a helper for authenticating through GitHub OAuth2 Proxy
    using passkeys. It requires the 'page' fixture from pytest-playwright.

    The browser storage state (cookies, localStorage) is saved to `.auth/github-oauth-state.json`
    after successful authentication, allowing reuse across test runs.

    Note: This is function-scoped to match the 'page' fixture scope from pytest-playwright.

    Args:
        page: Playwright Page fixture (from pytest-playwright plugin)
        e2e_deployment: E2E deployment fixture
        request: Pytest fixture request

    Returns:
        GitHubOAuth2ProxyApplication instance configured with the JupyterLab URL
    """
    e2e_deployment.ensure_deployed()
    jupyterlab_url = e2e_deployment.cli.get_jupyterlab_url()

    # Define storage state path for persisting authentication
    storage_state_path = Path.cwd() / constants.AUTH_DIR / constants.GITHUB_OAUTH_STATE_FILE

    # Get CI mode from pytest option
    is_ci = request.config.getoption("--ci")

    return GitHubOAuth2ProxyApplication(
        page=page, jupyterlab_url=jupyterlab_url, storage_state_path=storage_state_path, is_ci=is_ci
    )
