from unittest.mock import patch

import pytest

from jupyter_deploy.engine.enum import EngineType
from jupyter_deploy.handlers.project.open_handler import OpenHandler
from jupyter_deploy.manifest import JupyterDeployManifestV1


@pytest.fixture
def mock_manifest() -> JupyterDeployManifestV1:
    """Create a mock manifest."""
    return JupyterDeployManifestV1(
        **{  # type: ignore
            "schema_version": 1,
            "template": {
                "name": "mock-template-name",
                "engine": "terraform",
                "version": "1.0.0",
            },
            "values": [{"name": "open_url", "source": "output", "source-key": "jupyter_url"}],
        }
    )


class TestOpenHandler:
    def test_init(self, mock_manifest: JupyterDeployManifestV1) -> None:
        """Test that the OpenHandler initializes correctly."""
        with patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest") as mock_retrieve_manifest:
            mock_retrieve_manifest.return_value = mock_manifest
            handler = OpenHandler()
            assert handler._handler is not None
            assert handler.engine == EngineType.TERRAFORM
            assert handler.project_manifest == mock_manifest

    def test_open_success(self, mock_manifest: JupyterDeployManifestV1) -> None:
        """Test that open opens the URL in a web browser, and outputs the URL and cookies help message."""
        with patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest") as mock_retrieve_manifest:
            mock_retrieve_manifest.return_value = mock_manifest
            handler = OpenHandler()
            with (
                patch.object(handler._handler, "get_url", return_value="https://example.com/jupyter") as mock_get_url,
                patch("webbrowser.open", return_value=True) as mock_open,
                patch.object(handler.console, "print") as mock_print,
            ):
                handler.open()
                mock_get_url.assert_called_once()
                mock_open.assert_called_once_with("https://example.com/jupyter", new=2)
                assert mock_print.call_count >= 2
                assert "Opening Jupyter" in mock_print.call_args_list[0][0][0]

    def test_open_url_error(self, mock_manifest: JupyterDeployManifestV1) -> None:
        """Test that open_url handles errors when opening the URL."""
        with patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest") as mock_retrieve_manifest:
            mock_retrieve_manifest.return_value = mock_manifest
            handler = OpenHandler()

            with (
                patch.object(handler._handler, "get_url", return_value="https://example.com/jupyter") as mock_get_url,
                patch("webbrowser.open", return_value=False) as mock_open,
                patch.object(handler.console, "print") as mock_print,
            ):
                handler.open()
                mock_get_url.assert_called_once()
                mock_open.assert_called_once_with("https://example.com/jupyter", new=2)
                assert mock_print.call_count == 2
                assert "Failed to open URL" in mock_print.call_args_list[1][0][0]

    def test_open_url_insecure(self, mock_manifest: JupyterDeployManifestV1) -> None:
        """Test that open_url doesn't open non-HTTPS urls."""
        with patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest") as mock_retrieve_manifest:
            mock_retrieve_manifest.return_value = mock_manifest
            handler = OpenHandler()
            with (
                patch.object(handler._handler, "get_url", return_value="http://example.com/jupyter") as mock_get_url,
                patch("webbrowser.open") as mock_open,
                patch.object(handler.console, "print") as mock_print,
            ):
                handler.open()
                mock_get_url.assert_called_once()
                mock_open.assert_not_called()
                mock_print.assert_called_once()
                assert "Insecure URL detected" in mock_print.call_args[0][0]
