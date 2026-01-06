"""Unit tests for pytest-jupyter-deploy plugin."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest_jupyter_deploy
from pytest_jupyter_deploy import constants
from pytest_jupyter_deploy.plugin import handle_browser_context_args


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


def test_handle_browser_args_noop_with_ci_flag() -> None:
    """Test that handle_browser_context_args returns base args unchanged when --ci flag is set."""
    # Mock request with --ci flag set
    mock_request = Mock()
    mock_request.config.getoption.return_value = True  # CI mode enabled

    base_args = {"viewport": {"width": 1920, "height": 1080}}

    result = handle_browser_context_args(base_args, mock_request)

    # Should return base args unchanged (storage_state not added even if file exists)
    assert result == base_args
    mock_request.config.getoption.assert_called_once_with("--ci", default=False)


def test_handle_browser_args_reads_auth_file_and_return_combined_results(tmp_path: Path) -> None:
    """Test that handle_browser_context_args reads auth file and combines with base args."""
    # Create a mock auth file
    auth_dir = tmp_path / constants.AUTH_DIR
    auth_dir.mkdir()
    auth_file = auth_dir / constants.GITHUB_OAUTH_STATE_FILE
    auth_file.write_text(json.dumps({"cookies": [{"name": "test", "value": "data"}]}))

    # Mock request with CI mode disabled
    mock_request = Mock()
    mock_request.config.getoption.return_value = False  # CI mode disabled

    base_args = {"viewport": {"width": 1920, "height": 1080}}

    # Patch Path.cwd() to return our tmp_path
    with patch("pytest_jupyter_deploy.plugin.Path.cwd", return_value=tmp_path):
        result = handle_browser_context_args(base_args, mock_request)

    # Should return base args combined with storage_state
    assert result == {
        "viewport": {"width": 1920, "height": 1080},
        "storage_state": str(auth_file),
    }
    mock_request.config.getoption.assert_called_once_with("--ci", default=False)


def test_handle_browser_args_noop_when_auth_file_is_missing(tmp_path: Path) -> None:
    """Test that handle_browser_context_args returns base args when auth file doesn't exist."""
    # Mock request with CI mode disabled
    mock_request = Mock()
    mock_request.config.getoption.return_value = False  # CI mode disabled

    base_args = {"viewport": {"width": 1920, "height": 1080}}

    # Patch Path.cwd() to return tmp_path (where auth file doesn't exist)
    with patch("pytest_jupyter_deploy.plugin.Path.cwd", return_value=tmp_path):
        result = handle_browser_context_args(base_args, mock_request)

    # Should return base args unchanged (no storage_state added)
    assert result == base_args
    mock_request.config.getoption.assert_called_once_with("--ci", default=False)
