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

    def test_get_url_success(self, mock_manifest: JupyterDeployManifestV1) -> None:
        """Test that get_url returns the correct URL."""
        with patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest") as mock_retrieve_manifest:
            mock_retrieve_manifest.return_value = mock_manifest
            handler = OpenHandler()
            with patch.object(handler._handler, "get_url", return_value="https://example.com/jupyter") as mock_get_url:
                url = handler.get_url()
                mock_get_url.assert_called_once()
                assert url == "https://example.com/jupyter"

    def test_open_success(self, mock_manifest: JupyterDeployManifestV1) -> None:
        """Test that open() successfully opens URL."""
        with patch("jupyter_deploy.handlers.base_project_handler.retrieve_project_manifest") as mock_retrieve_manifest:
            mock_retrieve_manifest.return_value = mock_manifest
            handler = OpenHandler()
            with (
                patch.object(handler._handler, "get_url", return_value="https://example.com/jupyter"),
                patch("jupyter_deploy.handlers.project.open_handler.webbrowser.open", return_value=True) as mock_open,
            ):
                url = handler.open()
                assert url == "https://example.com/jupyter"
                mock_open.assert_called_once_with("https://example.com/jupyter", new=2)
