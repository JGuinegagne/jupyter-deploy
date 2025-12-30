"""Unit tests for pytest-jupyter-deploy plugin."""

from typing import Any

import pytest_jupyter_deploy


def test_version_available() -> None:
    """Test that __version__ is accessible and valid."""
    assert hasattr(pytest_jupyter_deploy, "__version__")
    assert isinstance(pytest_jupyter_deploy.__version__, str)
    assert len(pytest_jupyter_deploy.__version__) > 0


def test_test_engine_fixture_available(pytester: Any) -> None:
    """Test that test_engine_fixture is available in tests."""
    pytester.makepyfile(
        """
        def test_fixture_works(test_engine_fixture):
            assert test_engine_fixture == "Hello from test engine plugin!"
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_test_engine_fixture_value(test_engine_fixture: str) -> None:
    """Test that test_engine_fixture returns expected value."""
    assert test_engine_fixture == "Hello from test engine plugin!"
    assert isinstance(test_engine_fixture, str)
