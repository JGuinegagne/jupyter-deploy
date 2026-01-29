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

        # Create Live display
        self._live = Live(
            self._get_display_panel(),
            console=self.console,
            refresh_per_second=4,
            transient=False,
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
                completed=progress.percentage,
            )

            # Update Live display
            if self._live and self._is_started:
                self._live.update(self._get_display_panel())

    def update_log_box(self, lines: list[str]) -> None:
        """Update the log box with the provided lines.

        The engine callback decides what lines to display (e.g., last 2 during
        normal operation, expanded context during interaction).

        Args:
            lines: Lines to display in the log box
        """
        self._log_lines = lines

        # Update Live display
        if self._live and self._is_started:
            self._live.update(self._get_display_panel())

    def on_interaction_start(self, context: InteractionContext) -> None:
        """Freeze progress bar and expand log box for user interaction.

        The progress bar remains visible but frozen. The log box shows
        all context lines (e.g., full variable description). The prompt appears
        below the panel.

        Args:
            context: Context lines to display before the prompt
        """
        if not self._live or not self._is_started:
            return

        # Mark that we're in interaction mode
        self._in_interaction = True

        # Update log box with all context lines (expand the log box)
        self._log_lines = context.lines.copy()

        # Update display one last time with frozen progress bar + expanded log box
        self._live.update(self._get_display_panel())

        # Stop Live auto-refresh so prompt can appear below
        self._live.stop()

    def on_interaction_end(self) -> None:
        """Resume Rich display after user interaction.

        The engine callback is responsible for updating the log box
        back to its normal size via update_log_box().
        """
        if not self._live or not self._is_started:
            return

        # Clear interaction mode
        self._in_interaction = False

        # Resume Live display (progress bar will continue updating)
        # Engine callback will call update_log_box() to shrink it back
        self._live.start()

    def _get_display_panel(self) -> Panel:
        """Create Rich Panel with progress bar and log box.

        Returns:
            Panel containing progress display and log lines
        """
        # Build content: progress bar + log box
        content_parts: list[Any] = []

        if self._progress:
            content_parts.append(self._progress)

        # Add log box if we have lines to display
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
