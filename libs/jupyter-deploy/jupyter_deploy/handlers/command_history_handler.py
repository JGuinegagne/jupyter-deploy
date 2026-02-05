"""Handler for managing command execution history and log files."""

from collections import deque
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from jupyter_deploy.cmd_history import (
    AnyLogDescriptor,
    LogFileDescriptor,
    LogFilesCleanupResult,
)
from jupyter_deploy.constants import HISTORY_DIR
from jupyter_deploy.enum import HistoryEnabledCommandType
from jupyter_deploy.fs_utils import list_files_sorted


class LogNotFound(ValueError):
    """Raised when a command execution log cannot be found."""

    pass


class LogCleanupError(Exception):
    """Raised when log cleanup fails."""

    pass


class CommandHistoryHandler:
    """Manages command execution history and log records.

    This handler abstracts log storage and provides methods for creating,
    listing, reading, and cleaning up execution logs.
    """

    def __init__(self, project_path: Path) -> None:
        """Initialize the command history handler.

        Args:
            project_path: Root path of the jupyter-deploy project
        """
        self.project_path = project_path
        self.history_dir = project_path / HISTORY_DIR

    def create_log_file(self, command: HistoryEnabledCommandType) -> Path:
        """Create a log file for a command execution, return its path.

        Generates a timestamped log file path organized by command in subdirectories
        and ensures the necessary directories exist.

        Note: Does NOT auto-cleanup. Engine commands should explicitly call clear_logs().

        Args:
            command: The command type (e.g., HistoryEnabledCommandType.CONFIG)

        Returns:
            Path to the created log file where command output should be written
            (e.g., .jd-history/config/20251224-120000.log)
        """
        # Create command-specific subdirectory
        command_dir = self.history_dir / command.value
        command_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamped filename using UTC to avoid TZ edge cases
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        log_file_path = command_dir / f"{timestamp}.log"

        # Create the log file (empty)
        log_file_path.touch(exist_ok=True)

        return log_file_path

    def list_logs(self, command: HistoryEnabledCommandType, max_logs: int | None = None) -> list[AnyLogDescriptor]:
        """Return a list of LogDescriptors for a specific command, newest first.

        Log filenames (YYYYMMDD-HHMMSS.log) are lexicographically sortable, so we can use
        string comparison to find the most recent logs without parsing all timestamps.

        Args:
            command: Command type (e.g., HistoryEnabledCommandType.CONFIG)
            max_logs: Maximum number of logs to return (None = unlimited)

        Returns:
            List of log descriptors, sorted newest first
        """
        command_dir = self.history_dir / command.value

        # Get log files sorted by filename (newest first)
        # If directory doesn't exist, treat as "no logs" (not an error)
        try:
            log_files = list_files_sorted(command_dir, "*.log", max_files=max_logs, reverse=True)
        except (FileNotFoundError, NotADirectoryError):
            return []

        # Convert to LogFileDescriptor objects
        descriptors: list[AnyLogDescriptor] = []
        for log_path in log_files:
            # Parse timestamp from filename (YYYYMMDD-HHMMSS.log)
            timestamp_str = log_path.stem
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d-%H%M%S").replace(tzinfo=UTC)

            descriptor = LogFileDescriptor(
                id=f"{command.value}/{log_path.name}",
                command=command.value,
                timestamp=timestamp,
                path=log_path,
            )
            descriptors.append(descriptor)

        return descriptors

    def get_latest_log(self) -> AnyLogDescriptor | None:
        """Return the LogDescriptor of the most recent log across ALL commands, or None."""
        all_logs: list[AnyLogDescriptor] = []

        # Iterate through known command types only (from enum)
        # Only fetch the most recent log per command for efficiency
        for command_type in HistoryEnabledCommandType:
            logs = self.list_logs(command_type, max_logs=1)
            all_logs.extend(logs)

        if not all_logs:
            return None

        # Sort by timestamp, newest first
        all_logs.sort(key=lambda log: log.timestamp, reverse=True)
        return all_logs[0]

    def get_log_lines(self, log_descriptor: AnyLogDescriptor, max_lines: int = 1000, skip: int = 0) -> list[str]:
        """Return the requested log lines as a list (with newlines).

        Args:
            log_descriptor: Log descriptor identifying the log to read
            max_lines: Maximum number of lines to return (from end of file, like tail -n).
                      Defaults to 1000 for safety.
            skip: Number of lines from end to skip before starting (default 0).
                  Enables pagination through logs.

        Returns:
            List of log lines (with newlines). Returns last N lines, optionally skipping M from end.

        Examples:
            max_lines=1000, skip=0    → Last 1000 lines ([-1000:])
            max_lines=1000, skip=1000 → Lines [-2000:-1000]

        Raises:
            LogNotFound: If the log file does not exist
            NotImplementedError: If the log type is not supported
        """
        if isinstance(log_descriptor, LogFileDescriptor):
            try:
                with open(log_descriptor.path) as f:
                    # Use deque with maxlen for efficient tail-like behavior
                    # Read (skip + max_lines) to get our window
                    total_lines = skip + max_lines
                    all_lines = list(deque(f, maxlen=total_lines))

                    # Return the first max_lines (skipping the last `skip` lines)
                    return all_lines[:max_lines] if skip > 0 else all_lines
            except FileNotFoundError as e:
                raise LogNotFound(f"Log file not found: {log_descriptor.path}") from e
        else:
            raise NotImplementedError(f"Unknown log type: {log_descriptor.__class__}")

    def stream_log_lines(self, log_descriptor: AnyLogDescriptor) -> Iterator[str]:
        """Return iterator yielding log lines (with newlines).

        Raises:
            LogNotFound: If the log file does not exist
            NotImplementedError: If the log type is not supported
        """
        if isinstance(log_descriptor, LogFileDescriptor):
            try:
                with open(log_descriptor.path) as f:
                    yield from f
            except FileNotFoundError as e:
                raise LogNotFound(f"Log file not found: {log_descriptor.path}") from e
        else:
            raise NotImplementedError(f"Unknown log type: {log_descriptor.__class__}")

    def clear_logs(self, command: HistoryEnabledCommandType, keep: int = 20) -> LogFilesCleanupResult:
        """Clear old logs for a specific command, keeping only the most recent N logs.

        Args:
            command: Command type to clear logs for (e.g., HistoryEnabledCommandType.CONFIG)
            keep: Number of most recent logs to keep per command (default: 20)

        Returns:
            LogFilesCleanupResult with details about cleaned, kept, and failed files

        Raises:
            LogCleanupError: If any log files failed to be deleted
        """
        result = self._cleanup_log_files(command, keep=keep)

        # Raise exception if any deletions failed
        if result.has_failures:
            error_summary = f"Failed to delete {result.total_failed} log file(s)"
            raise LogCleanupError(error_summary)

        return result

    def _cleanup_log_files(self, command: HistoryEnabledCommandType, keep: int = 20) -> LogFilesCleanupResult:
        """Clean up log files for a specific command, keeping only the most recent N.

        Uses lexicographic ordering (filename-based) for performance.

        Args:
            command: The command type (e.g., HistoryEnabledCommandType.CONFIG)
            keep: Number of most recent logs to keep (default: 20)

        Returns:
            LogFilesCleanupResult with details about cleaned, kept, and failed files
        """
        result = LogFilesCleanupResult()
        command_dir = self.history_dir / command.value

        # Get all log files sorted by filename (newest first)
        # If directory doesn't exist, treat as "no logs to clean" (not an error)
        try:
            log_files = list_files_sorted(command_dir, "*.log", max_files=None, reverse=True)
        except (FileNotFoundError, NotADirectoryError):
            return result

        if not log_files:
            return result

        # Track files to keep (within the keep limit)
        result.kept = list(log_files[:keep])

        # Delete old logs beyond the keep limit
        for old_path in log_files[keep:]:
            try:
                old_path.unlink()
                result.cleaned.append(old_path)
            except Exception as e:
                # Track errors during cleanup (e.g., permission issues)
                result.failed.append((old_path, e))

        return result
