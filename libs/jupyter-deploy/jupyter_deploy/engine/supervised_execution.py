"""Core types and protocols for supervised execution with progress tracking."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


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
