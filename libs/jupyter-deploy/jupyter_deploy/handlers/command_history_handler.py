"""Handler for managing command execution history and log files."""

from datetime import UTC, datetime
from pathlib import Path

from jupyter_deploy.constants import HISTORY_DIR


class CommandHistoryHandler:
    """Manages command execution history and log files.

    This handler is responsible for:
    - Creating log file paths for command execution
    - Managing the history directory structure
    - Providing access to historical logs (future: listing, reading, cleanup)
    """

    def __init__(self, project_path: Path) -> None:
        """Initialize the command history handler.

        Args:
            project_path: Root path of the jupyter-deploy project
        """
        self.project_path = project_path
        self.history_dir = project_path / HISTORY_DIR

    def create_log_file(self, command: str) -> Path:
        """Create a log file for a command execution, return its path.

        Generates a timestamped log file path organized by command in subdirectories,
        ensures the necessary directories exist, and creates an empty log file.

        Args:
            command: The command name (e.g., "config", "up", "down")

        Returns:
            Path to the created log file where command output should be written
            (e.g., .jd-history/config/20260129-143022.log)
        """
        # Create command-specific subdirectory
        command_dir = self.history_dir / command
        command_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamped filename using UTC to avoid TZ edge cases
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        log_file_path = command_dir / f"{timestamp}.log"

        # Create the log file (empty)
        log_file_path.touch(exist_ok=True)

        return log_file_path
