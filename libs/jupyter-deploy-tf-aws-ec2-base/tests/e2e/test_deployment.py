"""Test to verify pytest plugin is accessible."""

from typing import Any


def test_engine_fixture_accessible(test_engine_fixture: Any) -> None:
    """Verify that test_engine_fixture from plugin is accessible."""
    assert test_engine_fixture == "Hello from test engine plugin!"
