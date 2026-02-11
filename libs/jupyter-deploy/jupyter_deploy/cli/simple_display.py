"""Simple terminal handler for SDK-style operations.

This module provides the SimpleDisplayManager class that implements
the TerminalHandler protocol with lightweight display (spinner, info, warnings, success).
No progress bars or complex UI elements.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from rich.console import Console
from rich.status import Status

from jupyter_deploy.engine.supervised_execution import ExecutionProgress, InteractionContext


class SimpleDisplayManager:
    """Lightweight terminal handler for SDK-style operations.

    Implements TerminalHandler protocol with simple display elements:
    spinner, info messages, warnings, and success messages.
    No progress bars or log boxes.

    Behavior:
    - Inside spinner context: info() updates spinner in place
    - Outside spinner context: info() prints directly
    - Warnings/success: Always print immediately and persist (never buffered)
    """

    def __init__(self, console: Console):
        """Initialize the simple display handler.

        Args:
            console: Rich Console instance for output
        """
        self.console = console
        self._in_spinner = False
        self._current_spinner: Status | None = None

    def info(self, message: str) -> None:
        """Display info message.

        Inside spinner context: updates spinner in place.
        Outside spinner context: prints directly.

        Args:
            message: The informational message to display
        """
        if self._in_spinner and self._current_spinner:
            # Inside spinner: update in place
            self._current_spinner.update(message)
        else:
            # Outside spinner: print directly
            self.console.print(message)

    def warning(self, message: str) -> None:
        """Display warning message (always shown, always persists).

        Prints immediately to console regardless of spinner state.

        Args:
            message: The warning message to display
        """
        self.console.print(f":warning: {message}", style="yellow")

    def success(self, message: str) -> None:
        """Display success message (always shown, always persists).

        Prints immediately to console regardless of spinner state.

        Args:
            message: The success message to display
        """
        self.console.print(f":white_check_mark: {message}", style="green")

    def hint(self, message: str) -> None:
        """Display hint message to help users.

        Shows helpful tips or instructions in a dimmed style.

        Args:
            message: The hint message to display
        """
        self.console.print(f":bulb: {message}", style="dim")

    @contextmanager
    def spinner(self, initial_message: str) -> Iterator[Any]:
        """Simple spinner for operations.

        Shows spinner and sets context so info() updates it in place.

        Args:
            initial_message: The initial message to display

        Yields:
            Rich status object with update(message: str) method
        """
        self._in_spinner = True
        try:
            with self.console.status(initial_message) as status:
                self._current_spinner = status
                yield status
        finally:
            self._in_spinner = False
            self._current_spinner = None

    def stop_spinning(self) -> None:
        """Stop the current spinner if one is active.

        This allows stopping the spinner before an operation completes,
        useful for transitioning to interactive commands.
        """
        if self._in_spinner and self._current_spinner:
            # Manually stop the spinner by calling __exit__
            self._current_spinner.__exit__(None, None, None)
            self._in_spinner = False
            self._current_spinner = None

    # Stub implementations for TerminalHandler protocol methods we don't use:

    def on_progress(self, progress: ExecutionProgress) -> None:
        """Stub implementation (not used for SDK-style operations).

        Args:
            progress: The current execution progress state
        """
        pass

    def update_log_box(self, lines: list[str]) -> None:
        """Stub implementation (not used for SDK-style operations).

        Args:
            lines: Lines to display in the log box
        """
        pass

    def on_interaction_start(self, context: InteractionContext) -> None:
        """Stub implementation (not used for SDK-style operations).

        Args:
            context: Context lines to display before the prompt
        """
        pass

    def on_interaction_end(self) -> None:
        """Stub implementation (not used for SDK-style operations)."""
        pass

    def display_error_context(self, lines: list[str]) -> None:
        """Display error context when command execution fails.

        Args:
            lines: Error context lines to display
        """
        for line in lines:
            self.console.print(line, style="red")
