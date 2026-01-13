from typing import Annotated

import typer
from rich.console import Console

from jupyter_deploy import cmd_utils
from jupyter_deploy.handlers.resource import host_handler

host_app = typer.Typer(
    help=("""Interact with the host running your Jupyter server."""),
    no_args_is_help=True,
)


@host_app.command()
def status(
    project_dir: Annotated[
        str | None,
        typer.Option("--path", "-p", help="Directory of the jupyter-deploy project whose host to check status."),
    ] = None,
) -> None:
    """Check the status of the host machine.

    Run either from a jupyter-deploy project directory that you created with `jd init`;
    or pass a --path PATH to such a directory.
    """
    with cmd_utils.project_dir(project_dir):
        handler = host_handler.HostHandler()
        console = handler.get_console()
        status = handler.get_host_status()

        console.print(f"Jupyter host status: [bold cyan]{status}[/]")


@host_app.command()
def stop(
    project_dir: Annotated[
        str | None,
        typer.Option("--path", "-p", help="Directory of the jupyter-deploy project whose host to stop."),
    ] = None,
) -> None:
    """Stop the host machine.

    Run either from a jupyter-deploy project directory that you created with `jd init`;
    or pass a --path PATH to such a directory.
    """
    with cmd_utils.project_dir(project_dir):
        handler = host_handler.HostHandler()
        handler.stop_host()


@host_app.command()
def start(
    project_dir: Annotated[
        str | None,
        typer.Option("--path", "-p", help="Directory of the jupyter-deploy project whose host to start."),
    ] = None,
) -> None:
    """Start the host machine.

    Run either from a jupyter-deploy project directory that you created with `jd init`;
    or pass a --path PATH to such a directory.
    """
    with cmd_utils.project_dir(project_dir):
        handler = host_handler.HostHandler()
        handler.start_host()


@host_app.command()
def restart(
    project_dir: Annotated[
        str | None,
        typer.Option("--path", "-p", help="Directory of the jupyter-deploy project whose host to restart."),
    ] = None,
) -> None:
    """Restart the host machine.

    Run either from a jupyter-deploy project directory that you created with `jd init`;
    or pass a --path PATH to such a directory.
    """
    with cmd_utils.project_dir(project_dir):
        handler = host_handler.HostHandler()
        handler.restart_host()


@host_app.command()
def connect(
    project_dir: Annotated[
        str | None,
        typer.Option("--path", "-p", help="Directory of the jupyter-deploy project whose host to restart."),
    ] = None,
) -> None:
    """Start an SSH-style connection to the host machine.

    Run either from a jupyter-deploy project directory that you created with `jd init`;
    or pass a --path PATH to such a directory.
    """
    with cmd_utils.project_dir(project_dir):
        handler = host_handler.HostHandler()
        handler.connect()


@host_app.command(context_settings={"allow_extra_args": True, "allow_interspersed_args": False})
def exec(
    ctx: typer.Context,
    project_dir: Annotated[
        str | None,
        typer.Option("--path", "-p", help="Directory of the jupyter-deploy project."),
    ] = None,
) -> None:
    """Execute a non-interactive command on the host machine.

    Run either from a jupyter-deploy project directory that you created with `jd init`;
    or pass a --path PATH to such a directory.

    Pass the command after '--', for example:

    jd host exec -- df -h

    jd host exec -- "docker container list | grep jupyter"
    """
    # Arguments after -- are in ctx.args
    command_args = ctx.args

    if not command_args:
        console = Console()
        console.print(":x: No command provided. Pass a command after '--'", style="red")
        console.print("Example: jd host exec -- df -h", style="red")
        raise typer.Exit(code=1)

    with cmd_utils.project_dir(project_dir):
        handler = host_handler.HostHandler()
        console = handler.get_console()

        stdout, stderr = handler.exec_command(command_args)

        if stdout:
            console.rule("stdout")
            console.print(stdout)
            if not stderr:
                console.rule()

        if stderr:
            console.rule("stderr")
            console.print(stderr)
            console.rule()
