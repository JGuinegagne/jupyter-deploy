"""Unit tests for pytest-jupyter-deploy plugin."""

from typing import Any

import pytest_jupyter_deploy


def test_version_available() -> None:
    """Test that __version__ is accessible and valid."""
    assert hasattr(pytest_jupyter_deploy, "__version__")
    assert isinstance(pytest_jupyter_deploy.__version__, str)
    assert len(pytest_jupyter_deploy.__version__) > 0


def test_e2e_suite_dir_fixture_available(pytester: Any) -> None:
    """Test that e2e_suite_dir fixture is available in tests."""
    pytester.makepyfile(
        """
        def test_e2e_suite_dir_works(e2e_suite_dir):
            assert e2e_suite_dir is not None
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_e2e_suite_dir_uses_pytestopt(pytester: Any) -> None:
    """Test that e2e_suite_dir uses the --e2e-tests-dir option."""
    pytester.makepyfile(
        """
        from pathlib import Path

        def test_e2e_suite_dir_value(e2e_suite_dir):
            assert e2e_suite_dir == Path("custom/test/path")
        """
    )
    result = pytester.runpytest("--e2e-tests-dir=custom/test/path")
    result.assert_outcomes(passed=1)


def test_e2e_config_fixture_available(pytester: Any) -> None:
    """Test that e2e_config fixture is available in tests."""
    pytester.makepyfile(
        """
        def test_e2e_config_works(e2e_config):
            assert e2e_config is not None
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_e2e_config_fixture_returns_config(pytester: Any) -> None:
    """Test that e2e_config returns a SuiteConfig instance."""
    pytester.makepyfile(
        """
        from pytest_jupyter_deploy.suite_config import SuiteConfig

        def test_e2e_config_value(e2e_config):
            assert isinstance(e2e_config, SuiteConfig)
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_e2e_deployment_fixture_available(pytester: Any) -> None:
    """Test that e2e_deployment fixture is available in tests."""
    pytester.makepyfile(
        """
        def test_e2e_deployment_works(e2e_deployment):
            assert e2e_deployment is not None
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_e2e_deployment_fixture_yields_value(pytester: Any) -> None:
    """Test that e2e_deployment yields an EndToEndDeployment instance."""
    pytester.makepyfile(
        """
        from pytest_jupyter_deploy.deployment import EndToEndDeployment

        def test_e2e_deployment_value(e2e_deployment):
            assert isinstance(e2e_deployment, EndToEndDeployment)
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
