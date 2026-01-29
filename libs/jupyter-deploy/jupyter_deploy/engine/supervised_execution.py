"""Core types and protocols for supervised execution with progress tracking."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class ExecutionProgress:
    """Progress update emitted during execution.

    Attributes:
        label: Display label for the current execution state (e.g., "Generating plan", "Creating infrastructure")
        percentage: Progress percentage (0-100). Use 0 when progress is indeterminate.
    """

    label: str
    percentage: int


class ProgressCallback(Protocol):
    """Protocol for receiving progress updates during execution.

    This protocol allows the CLI layer to implement display logic
    without creating a dependency from the engine layer.
    """

    def on_progress(self, progress: ExecutionProgress) -> None:
        """Called when progress is made.

        Args:
            progress: The current execution progress state
        """
        ...


class LogCallback(Protocol):
    """Protocol for receiving live log lines during execution.

    This protocol allows the CLI layer to display live command output
    (e.g., in a log box below a progress bar) without creating a
    dependency from the engine layer.
    """

    def on_log_line(self, line: str) -> None:
        """Called when a new log line is emitted.

        Args:
            line: A single line of output from the command (without trailing newline)
        """
        ...


@runtime_checkable
class ExecutionCallback(Protocol):
    """Protocol for execution callbacks used by SupervisedExecutor.

    This is the minimal interface that SupervisedExecutor needs:
    - Check for user interaction (cheap)
    - Handle interaction lines
    - Handle normal log lines
    - Receive progress updates
    """

    def is_requesting_user_input(self, line: str) -> bool:
        """Check if the line triggers or continues user interaction (cheap check).

        This is called BEFORE on_log_line() to determine if the line should
        be handled as an interactive prompt rather than normal output.

        Args:
            line: A single line of output from the command (without trailing newline)

        Returns:
            True if this line is part of user interaction (skip normal processing)
        """
        ...

    def handle_interaction(self, line: str) -> None:
        """Handle a line that is part of user interaction.

        This is called when check_interaction() returns True. The line should be
        added to the context buffer but NOT the display buffer.

        Args:
            line: A single line of output from the command (without trailing newline)
        """
        ...

    def on_log_line(self, line: str) -> None:
        """Handle a normal log line (not part of interaction).

        Called when check_interaction() returns False.

        Args:
            line: A single line of output from the command (without trailing newline)
        """
        ...

    def on_progress(self, progress: ExecutionProgress) -> None:
        """Called when progress is made.

        Args:
            progress: The current execution progress state
        """
        ...


@dataclass
class InteractionContext:
    """Context to display when user interaction is needed.

    Used when the subprocess requires user input (e.g., terraform prompts).
    Contains buffered output lines that provide context for the prompt.

    Attributes:
        lines: List of output lines to display (e.g., variable description, plan summary)
    """

    lines: list[str]


class TerminalHandler(Protocol):
    """Protocol for terminal interaction during supervised execution.

    This unified protocol handles all terminal display concerns:
    progress updates, live logs, and interactive prompts. It allows
    the CLI layer to implement Rich-based display without creating
    a dependency from the engine layer.
    """

    def on_progress(self, progress: ExecutionProgress) -> None:
        """Called when progress is made.

        Args:
            progress: The current execution progress state
        """
        ...

    def update_log_box(self, lines: list[str]) -> None:
        """Update the log box with the provided lines.

        The engine callback decides what lines to display (e.g., last 2 during
        normal operation, expanded context during interaction).

        Args:
            lines: Lines to display in the log box
        """
        ...

    def on_interaction_start(self, context: InteractionContext) -> None:
        """Called when subprocess needs user input.

        The terminal handler should pause any active display (e.g., progress bar)
        and display the context lines to help the user understand the prompt.

        Args:
            context: Context lines to display before the prompt
        """
        ...

    def on_interaction_end(self) -> None:
        """Called when user interaction is complete.

        The terminal handler should resume any paused display (e.g., progress bar).
        """
        ...


class ExecutionError(Exception):
    """Exception raised when a supervised command execution fails.

    Attributes:
        command: The command that failed (e.g., "config", "up", "down")
        retcode: The non-zero return code from the failed command
        message: Human-readable error message
        log_file: Path to the log file containing full output
    """

    def __init__(self, command: str, retcode: int, message: str, log_file: Path):
        self.command = command
        self.retcode = retcode
        self.message = message
        self.log_file = log_file
        super().__init__(message)
