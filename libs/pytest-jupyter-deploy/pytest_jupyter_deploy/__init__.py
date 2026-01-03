"""Pytest plugin for E2E testing of jupyter-deploy templates."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    # Package is not installed (development mode)
    __version__ = "0.1.0"
