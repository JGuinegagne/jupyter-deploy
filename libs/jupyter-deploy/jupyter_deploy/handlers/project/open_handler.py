import webbrowser

from rich.console import Console

from jupyter_deploy.engine.engine_open import EngineOpenHandler
from jupyter_deploy.engine.enum import EngineType
from jupyter_deploy.engine.terraform import tf_open
from jupyter_deploy.handlers.base_project_handler import BaseProjectHandler


class OpenHandler(BaseProjectHandler):
    _handler: EngineOpenHandler

    def __init__(self) -> None:
        """Base class to manage the open command of a jupyter-deploy project."""
        super().__init__()
        self.console = Console()

        if self.engine == EngineType.TERRAFORM:
            self._handler = tf_open.TerraformOpenHandler(
                project_path=self.project_path,
                project_manifest=self.project_manifest,
            )
        else:
            raise NotImplementedError(f"OpenHandler implementation not found for engine: {self.engine}")

    def open(self) -> None:
        """Launch the Jupyter URL in the default web browser."""
        url = self._handler.get_url()

        if not url:
            return

        if not url.startswith("https://"):
            self.console.print(
                ":x: Insecure URL detected. Only HTTPS URLs are allowed for security reasons.",
                style="red",
            )
            return

        self.console.print(f"\nOpening Jupyter app at: {url}", style="green")
        open_status = webbrowser.open(url, new=2)

        if not open_status:
            self.console.print(
                ":x: Failed to open URL in browser.",
                style="red",
            )
            return

        # show trouble-shooting
        has_host_status = self.project_manifest.has_command("host.status")
        has_server_status = self.project_manifest.has_command("server.status")
        has_host_restart = self.project_manifest.has_command("host.restart")
        has_host_start = self.project_manifest.has_command("host.start")
        has_server_restart = self.project_manifest.has_command("server.restart")
        has_server_start = self.project_manifest.has_command("server.start")
        has_host_connect = self.project_manifest.has_command("host.connect")

        self.console.line()
        self.console.print("[bold]Having trouble?[/]")
        if has_host_status:
            self.console.print("- verify that your host is running: [bold cyan]jd host status[/]")
            if has_host_restart:
                self.console.print("  - if it is, try restarting it: [bold cyan]jd host restart[/]")
            if has_host_start:
                self.console.print("  - if it is not, try starting it: [bold cyan]jd host start[/]")
        if has_server_status:
            self.console.print("- verify that your server is running: [bold cyan]jd server status[/]")
            if has_server_restart:
                self.console.print("  - try restarting it: [bold cyan]jd server restart[/]")
            elif has_server_start:
                self.console.print("  - try starting it: [bold cyan]jd server start[/]")
        if has_host_connect:
            self.console.print("- connect to your host (when host is running): [bold cyan]jd host connect[/]")
        if has_host_status or has_server_status or has_host_connect:
            self.console.line()
