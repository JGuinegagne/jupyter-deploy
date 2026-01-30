"""Progress display manager for CLI commands using Rich.

This module provides the ProgressDisplayManager class that implements
the TerminalHandler protocol for Rich-based terminal display.
"""

from typing import Any

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn

from jupyter_deploy.engine.supervised_execution import ExecutionProgress, InteractionContext


class ProgressDisplayManager:
    """Rich-based terminal display manager for supervised execution.

    Implements the TerminalHandler protocol to provide:
    - Progress bar with spinner and percentage
    - Live log box displaying lines provided by the engine callback
    - Interactive prompt handling:
      * Progress bar freezes (stays visible)
      * Log box expands to show full context (e.g., variable description)
      * Prompt appears below the panel
      * After user responds, log box shrinks back and progress resumes
    """

    def __init__(self) -> None:
        """Initialize the progress display manager."""
        self.console = Console()

        # Rich components
        self._progress: Progress | None = None
        self._task_id: TaskID | None = None
        self._live: Live | None = None

        # State tracking
        self._log_lines: list[str] = []
        self._current_phase_label = ""
        self._is_started = False
        self._in_interaction = False  # Track if we're in an interactive prompt

    def __enter__(self) -> "ProgressDisplayManager":
        """Enter context manager - start the display."""
        self.start()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object) -> None:
        """Exit context manager - stop the display."""
        self.stop()

    def start(self) -> None:
        """Initialize and start the Rich display."""
        if self._is_started:
            return

        # Create Rich Progress with spinner, text, and bar
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[bold green]{task.percentage:>3.0f}%"),
            console=self.console,
            expand=False,
        )

        # Add initial task
        self._task_id = self._progress.add_task("Starting...", total=100)

        # Create Live display (transient=True makes it disappear when stopped)
        self._live = Live(
            self._get_display_panel(),
            console=self.console,
            refresh_per_second=4,
            transient=True,
        )
        self._live.start()
        self._is_started = True

    def stop(self) -> None:
        """Stop the Rich display."""
        if not self._is_started or not self._live:
            return

        self._live.stop()
        self._is_started = False

    def on_progress(self, progress: ExecutionProgress) -> None:
        """Update progress bar with new state.

        Args:
            progress: The current execution progress state
        """
        self._current_phase_label = progress.label

        if self._progress and self._task_id is not None:
            self._progress.update(
                self._task_id,
                description=progress.label,
                completed=progress.reward,
            )

            # Update Live display (restart if stopped after interaction)
            if self._live and not self._in_interaction:
                if not self._is_started:
                    self._live.start()
                    self._is_started = True
                self._live.update(self._get_display_panel())

    def update_log_box(self, lines: list[str]) -> None:
        """Update the log box with the provided lines.

        The engine callback decides what lines to display (e.g., last 2 during
        normal operation, expanded context during interaction).

        Args:
            lines: Lines to display in the log box
        """
        self._log_lines = lines

        # Update Live display (restart if stopped after interaction)
        if self._live and not self._in_interaction:
            if not self._is_started:
                self._live.start()
                self._is_started = True
            self._live.update(self._get_display_panel())

    def on_interaction_start(self, context: InteractionContext) -> None:
        """Stop Live display and print interaction context to console.

        Stops the Live display (which disappears due to transient=True) and prints
        the context to allow terminal to handle user input naturally.

        Args:
            context: Context lines to display before the prompt
        """
        if not self._live or not self._is_started:
            return

        # Stop Live display (box disappears automatically with transient=True)
        self._live.stop()
        self._is_started = False
        self._in_interaction = True

        # Print context lines raw (so terminal interprets ANSI codes from terraform)
        if context.lines:
            print()  # Blank line for spacing
            for i, line in enumerate(context.lines):
                if i < len(context.lines) - 1:
                    # Not the last line - add newline
                    print(line, flush=True)
                else:
                    # Last line (prompt) - no extra newline, but ensure trailing space
                    if not line.endswith(" "):
                        line = line + " "
                    print(line, end="", flush=True)

    def on_interaction_end(self) -> None:
        """Mark interaction as complete.

        Clears the interaction flag. Live display will resume automatically
        on the next progress/log update, avoiding box stacking.
        """
        # Clear interaction mode - next update will restart Live if needed
        self._in_interaction = False

    def display_error_context(self, lines: list[str]) -> None:
        """Display error context when command execution fails.

        Stops the live display and prints error context lines.

        Args:
            lines: Error context lines to display
        """
        # Stop live display if running
        if self._live and self._is_started:
            self._live.stop()

        # Print error context
        if lines:
            self.console.print("[red]Error context:[/red]")
            for line in lines:
                self.console.print(f"  {line}")

    def _get_display_panel(self) -> Panel:
        """Create Rich Panel with progress bar and log box.

        Returns:
            Panel containing progress display and log lines
        """
        # Build content: progress bar + log box
        content_parts: list[Any] = []

        if self._progress:
            content_parts.append(self._progress)

        # Show small log box
        if self._log_lines:
            log_text = "\n".join(self._log_lines)
            content_parts.append(f"\n[dim]{log_text}[/dim]")

        # Combine into single renderable
        content = Group(*content_parts) if content_parts else ""

        return Panel(
            content,
            title="[bold]jupyter-deploy[/bold]",
            border_style="blue",
        )
