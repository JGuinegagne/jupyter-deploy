import webbrowser

from jupyter_deploy.engine.engine_open import EngineOpenHandler
from jupyter_deploy.engine.enum import EngineType
from jupyter_deploy.engine.terraform import tf_open
from jupyter_deploy.exceptions import OpenWebBrowserError, UrlNotSecureError
from jupyter_deploy.handlers.base_project_handler import BaseProjectHandler


class OpenHandler(BaseProjectHandler):
    _handler: EngineOpenHandler

    def __init__(self) -> None:
        """Base class to manage the open command of a jupyter-deploy project."""
        super().__init__()

        if self.engine == EngineType.TERRAFORM:
            self._handler = tf_open.TerraformOpenHandler(
                project_path=self.project_path,
                project_manifest=self.project_manifest,
            )
        else:
            raise NotImplementedError(f"OpenHandler implementation not found for engine: {self.engine}")

    def get_url(self) -> str:
        """Return the URL to access the Jupyter app.

        Raises:
            UrlNotAvailableError: If URL cannot be retrieved or is empty
        """
        return self._handler.get_url()

    def open(self) -> str:
        """Open the application with the correct protocol.

        Currently only supports webbrowser protocol.

        Returns:
            str: The URL that was opened

        Raises:
            UrlNotAvailableError: If URL cannot be retrieved or is empty
            UrlNotSecureError: If URL is not HTTPS
            OpenWebBrowserError: If opening URL in browser fails
        """
        url = self.get_url()

        if not url.startswith("https://"):
            raise UrlNotSecureError("Insecure URL detected. Only HTTPS URLs are allowed for security reasons.", url)

        open_status = webbrowser.open(url, new=2)
        if not open_status:
            raise OpenWebBrowserError("Failed to open URL in browser.", url)

        return url
