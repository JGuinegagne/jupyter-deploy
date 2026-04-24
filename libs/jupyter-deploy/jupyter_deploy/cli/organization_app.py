from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from jupyter_deploy import cmd_utils
from jupyter_deploy.cli.error_decorator import handle_cli_errors
from jupyter_deploy.cli.simple_display import SimpleDisplayManager
from jupyter_deploy.handlers.access import organization_handler

organization_app = typer.Typer(
    help="Control access to your app at the organization level.",
    no_args_is_help=True,
)


@organization_app.command()
def set(
    organization: Annotated[str, typer.Argument(help="Name of the organization to allowlist.")],
    project_dir: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Directory of the project."),
    ] = None,
) -> None:
    """Allowlist an organization to access the app.

    Run either from a project directory that you created with <jd init>;
    or pass --path <project-dir>.
    """
    console = Console()
    with handle_cli_errors(console), cmd_utils.project_dir(project_dir):
        simple_display_manager = SimpleDisplayManager(console=console)
        handler = organization_handler.OrganizationHandler(display_manager=simple_display_manager)

        with simple_display_manager.spinner("Setting organization..."):
            handler.set_organization(organization)


@organization_app.command()
def unset(
    project_dir: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Directory of the project."),
    ] = None,
) -> None:
    """Remove organization-based access from the app.

    Run either from a project directory that you created with <jd init>;
    or pass --path <project-dir>.
    """
    console = Console()
    with handle_cli_errors(console), cmd_utils.project_dir(project_dir):
        simple_display_manager = SimpleDisplayManager(console=console)
        handler = organization_handler.OrganizationHandler(display_manager=simple_display_manager)

        with simple_display_manager.spinner("Removing organization..."):
            handler.unset_organization()


@organization_app.command()
def get(
    project_dir: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Directory of the project."),
    ] = None,
) -> None:
    """Show the name of the organization authorized to access the app.

    Run either from a project directory that you created with <jd init>;
    or pass --path <project-dir>.
    """
    console = Console()
    with handle_cli_errors(console), cmd_utils.project_dir(project_dir):
        simple_display_manager = SimpleDisplayManager(console=console)
        handler = organization_handler.OrganizationHandler(display_manager=simple_display_manager)

        with simple_display_manager.spinner("Fetching organization..."):
            organization = handler.get_organization()

        if organization:
            console.print(f"Allowlisted organization: [bold cyan]{organization}[/]")
        else:
            console.print("Allowlisted organization: [bold cyan]None[/]")
