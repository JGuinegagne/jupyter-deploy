"""Pytest plugin - defines fixtures for E2E testing."""

import os
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from pytest_jupyter_deploy.cli import JDCli
from pytest_jupyter_deploy.deployment import EndToEndDeployment
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
        default="tests/e2e",
        help="Path to E2E tests directory",
    )
    parser.addoption(
        "--e2e-config-name",
        action="store",
        default="base",
        help="Configuration name to use from configurations/ directory",
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
        "--cleanup-on-success",
        action="store_true",
        default=True,
        help="Cleanup infrastructure after successful tests (default: True)",
    )
    parser.addoption(
        "--cleanup-on-failure",
        action="store_true",
        default=False,
        help="Cleanup infrastructure after failed tests (default: False)",
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
        # implement: use the PATH pytest was called with, e.g. uv run pytest PATH
        return Path(os.getcwd())


@pytest.fixture(scope="session")
def e2e_config(e2e_suite_dir: Path) -> SuiteConfig:
    """Load E2E test configuration from suite.yaml.

    Args:
        e2e_suite_dir: E2E tests directory path

    Returns:
        SuiteConfig instance with loaded configuration
    """
    return SuiteConfig(suite_dir=e2e_suite_dir)


@pytest.fixture(scope="session")
def e2e_deployment(
    e2e_config: SuiteConfig, request: pytest.FixtureRequest
) -> Generator[EndToEndDeployment, None, None]:
    """Deploy infrastructure once per test session.

    This fixture:
    1. Creates a sandbox directory (sandbox-e2e/<template-name>/<timestamp>/)
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

    # Cleanup based on test results
    no_cleanup = request.config.getoption("--no-cleanup")
    cleanup_on_success = request.config.getoption("--cleanup-on-success")
    cleanup_on_failure = request.config.getoption("--cleanup-on-failure")
    tests_failed = request.session.testsfailed

    should_cleanup = cleanup_on_failure if tests_failed > 0 else cleanup_on_success

    if not no_cleanup and should_cleanup:
        deployment.ensure_destroyed()


@pytest.fixture
def jd_cli(e2e_deployment: EndToEndDeployment) -> JDCli:
    """Provide CLI helper for jd commands.

    Returns the JDCli instance from the deployment for running jd commands.

    Args:
        e2e_deployment: E2E deployment fixture

    Returns:
        JDCli instance
    """
    return e2e_deployment.cli
