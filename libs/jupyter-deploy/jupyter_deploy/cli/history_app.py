"""CLI commands for managing execution history and log files."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from jupyter_deploy import cmd_utils
from jupyter_deploy.enum import HistoryEnabledCommandType
from jupyter_deploy.handlers.command_history_handler import (
    CommandHistoryHandler,
    LogNotFound,
)

history_app = typer.Typer(
    help=("View and manage logs emitted by the infrastructure-as-code engine as called by jupyter-deploy commands."),
    no_args_is_help=True,
)


@history_app.command()
def list(
    command: Annotated[
        HistoryEnabledCommandType,
        typer.Argument(help="Command type: config, up, or down."),
    ],
    project_dir: Annotated[
        str | None,
        typer.Option("--path", "-p", help="Directory of the jupyter-deploy project."),
    ] = None,
    n: Annotated[
        int,
        typer.Option("-n", help="Maximum number of logs to display", min=1),
    ] = 20,
    text: Annotated[
        bool,
        typer.Option("--text", help="Output plain text without Rich markup."),
    ] = False,
) -> None:
    """Show the list of execution logs available in the project for a specific command.

    Run either from a jupyter-deploy project directory that you created with `jd init`;
    or pass a --path PATH to such a directory.
    """
    with cmd_utils.project_dir(project_dir):
        project_path = Path.cwd()
        handler = CommandHistoryHandler(project_path)
        logs = handler.list_logs(command.value, max_logs=n)

        console = Console()

        if not logs:
            console.print(f"No execution logs found for command: [bold cyan]{command.value}[/]")
            return

        if text:
            # Plain text mode - just print __repr__ (file paths)
            for log in logs:
                console.print(repr(log))
        else:
            # Table mode - formatted display
            table = Table(title="Execution History Logs", show_header=True, header_style="bold cyan")
            table.add_column("Log Type", style="green")
            table.add_column("Timestamp", style="blue")
            table.add_column("Location", style="dim")

            for log in logs:
                table.add_row(
                    log.storage_type,  # "file", "cloudwatch", etc.
                    log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    repr(log),  # File path or other representation
                )
            console.print(table)


@history_app.command()
def show(
    command: Annotated[
        HistoryEnabledCommandType | None,
        typer.Argument(
            help="Command type: config, up, or down. If omitted, show latest log from any command.",
        ),
    ] = None,
    project_dir: Annotated[
        str | None,
        typer.Option("--path", "-p", help="Directory of the jupyter-deploy project."),
    ] = None,
    n: Annotated[
        int,
        typer.Option("-n", help="Show Nth most recent log for the command.", min=1),
    ] = 1,
    lines: Annotated[
        int | None,
        typer.Option("-l", "--lines", help="Show only last L lines of the log content.", min=1),
    ] = None,
    skip: Annotated[
        int,
        typer.Option("-s", "--skip", help="Skip S lines from end (for pagination).", min=0),
    ] = 0,
) -> None:
    """Display the content of a specific command execution log.

    Run either from a jupyter-deploy project directory that you created with `jd init`;
    or pass a --path PATH to such a directory.

    By default, displays the content of the entire log.

    Use --lines/-l to show only the last N lines.

    Use --skip/-s to offset the first line returned (from the end of the content).
    """
    console = Console()

    with cmd_utils.project_dir(project_dir):
        project_path = Path.cwd()
        handler = CommandHistoryHandler(project_path)

        # Get log descriptor
        if command:
            logs = handler.list_logs(command.value, max_logs=n)
            if len(logs) < n:
                if n == 1 or not logs:
                    console.print(
                        f":x: No log found for command: [bold]{command.value}[/]",
                        style="red",
                    )
                else:
                    console.print(
                        (
                            f":x: [bold]{n}th[/] log not found for command: [bold]{command.value}[/]\n"
                            f"Only {len(logs)} logs are available."
                        ),
                        style="red",
                    )
                raise typer.Exit(code=1)
            log_descriptor = logs[n - 1]
        else:
            maybe_log_descriptor = handler.get_latest_log()
            if not maybe_log_descriptor:
                console.print(":information: No execution logs found.")
                return
            log_descriptor = maybe_log_descriptor

        # Display log content
        try:
            if lines or skip:
                # Tail/pagination mode - use get_log_lines with bounded memory
                max_lines = lines or 1000  # Default to 1000 when skip is used without -l
                log_lines = handler.get_log_lines(log_descriptor, max_lines=max_lines, skip=skip)
                for line in log_lines:
                    # use raw print as the engine may add formatting
                    # end="" because line already includes \n from file
                    print(line, end="")
            else:
                # Default streaming mode - memory-efficient iterator for entire log
                for line in handler.stream_log_lines(log_descriptor):
                    # use raw print as the engine may add formatting
                    # end="" because line already includes \n from file
                    print(line, end="")
        except LogNotFound as e:
            console.print(f":x: Failed to read log content: {e}", style="red")
            raise typer.Exit(code=1) from None


@history_app.command()
def clear(
    command: Annotated[
        HistoryEnabledCommandType,
        typer.Argument(
            help="Command type to clear: config, up, or down.",
        ),
    ],
    project_dir: Annotated[
        str | None,
        typer.Option("--path", "-p", help="Directory of the jupyter-deploy project."),
    ] = None,
    keep: Annotated[
        int,
        typer.Option("--keep", "-k", help="Number of most recent logs to retain.", min=1),
    ] = 20,
) -> None:
    """Delete execution logs for a specific command, keeping only the most recent N logs.

    Run either from a jupyter-deploy project directory that you created with `jd init`;
    or pass a --path PATH to such a directory.
    """
    console = Console()

    with cmd_utils.project_dir(project_dir):
        project_path = Path.cwd()
        handler = CommandHistoryHandler(project_path)
        result = handler.clear_logs(command.value, keep=keep)

        if result.total_cleaned == 0 and result.total_failed == 0:
            console.print(":information: No stale log files to clear.")
        else:
            # Report successful cleanups
            if result.total_cleaned > 0:
                console.print(
                    f":white_check_mark: Cleared {result.total_cleaned} old log file(s) from '{command.value}' logs "
                    f"(kept {result.total_kept} most recent).",
                    style="green",
                )

            # Report failures if any
            if result.has_failures:
                console.print(
                    f":error: Failed to delete {result.total_failed} log file(s):",
                    style="red",
                )
                for failed_path, error in result.failed[:10]:
                    console.print(f"  - {failed_path}: {error}", style="dim")

                # Exit with non-zero code when there are failures
                raise typer.Exit(code=1)
