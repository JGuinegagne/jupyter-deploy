from typing import Annotated

import typer
from rich.console import Console

from jupyter_deploy import cmd_utils
from jupyter_deploy.cli.error_decorator import handle_cli_errors
from jupyter_deploy.cli.simple_display import SimpleDisplayManager
from jupyter_deploy.handlers.access import team_handler

teams_app = typer.Typer(
    help=("""Control access to your jupyter app at team level."""),
    no_args_is_help=True,
)


@teams_app.command()
def add(
    teams: Annotated[list[str], typer.Argument(help="Names of the teams to add to the allowlist.")],
    project_dir: Annotated[
        str | None,
        typer.Option("--path", "-p", help="Directory of the jupyter-deploy project."),
    ] = None,
) -> None:
    """Add team(s) to the list authorized to access the Jupyter app.

    Run either from a jupyter-deploy project directory that you created with `jd init`;
    or pass a --path PATH to such a directory.
    """
    console = Console()
    with handle_cli_errors(console), cmd_utils.project_dir(project_dir):
        simple_display_manager = SimpleDisplayManager(console=console)
        handler = team_handler.TeamsHandler(terminal_handler=simple_display_manager)

        with simple_display_manager.spinner("Adding teams..."):
            handler.add_teams(teams)


@teams_app.command()
def remove(
    teams: Annotated[list[str], typer.Argument(help="Names of the teams to remove from the allowlist.")],
    project_dir: Annotated[
        str | None,
        typer.Option("--path", "-p", help="Directory of the jupyter-deploy project."),
    ] = None,
) -> None:
    """Remove team(s) from the list authorized to access the Jupyter app.

    Run either from a jupyter-deploy project directory that you created with `jd init`;
    or pass a --path PATH to such a directory.
    """
    console = Console()
    with handle_cli_errors(console), cmd_utils.project_dir(project_dir):
        simple_display_manager = SimpleDisplayManager(console=console)
        handler = team_handler.TeamsHandler(terminal_handler=simple_display_manager)

        with simple_display_manager.spinner("Removing teams..."):
            handler.remove_teams(teams)


@teams_app.command()
def set(
    teams: Annotated[list[str], typer.Argument(help="Names of the teams to allowlist.")],
    project_dir: Annotated[
        str | None,
        typer.Option("--path", "-p", help="Directory of the jupyter-deploy project."),
    ] = None,
) -> None:
    """Set the list of team(s) authorized to access the Jupyter app.

    Run either from a jupyter-deploy project directory that you created with `jd init`;
    or pass a --path PATH to such a directory.
    """
    console = Console()
    with handle_cli_errors(console), cmd_utils.project_dir(project_dir):
        simple_display_manager = SimpleDisplayManager(console=console)
        handler = team_handler.TeamsHandler(terminal_handler=simple_display_manager)

        with simple_display_manager.spinner("Setting teams..."):
            handler.set_teams(teams)


# use a cmd alias because mypy shows an 'valid-type' error if we just call the method 'list'
@teams_app.command("list")
def list_teams(
    project_dir: Annotated[
        str | None,
        typer.Option("--path", "-p", help="Directory of the jupyter-deploy project."),
    ] = None,
) -> None:
    """Show the name(s) of the team(s) authorized to access the Jupyter app.

    Run either from a jupyter-deploy project directory that you created with `jd init`;
    or pass a --path PATH to such a directory.
    """
    console = Console()
    with handle_cli_errors(console), cmd_utils.project_dir(project_dir):
        simple_display_manager = SimpleDisplayManager(console=console)
        handler = team_handler.TeamsHandler(terminal_handler=simple_display_manager)

        with simple_display_manager.spinner("Fetching teams..."):
            teams = handler.list_teams()

        if teams:
            console.print(f"Allowlisted teams: [bold cyan]{', '.join(teams)}[/]")
        else:
            console.print("Allowlisted teams: [bold cyan]None[/]")
