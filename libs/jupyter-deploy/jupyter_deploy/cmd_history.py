"""Command history management - log descriptors and cleanup results."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class LogDescriptor(BaseModel):
    """Base class for log descriptors."""

    id: str = Field(description="Unique identifier for this log")
    command: str = Field(description="Command that generated this log (config/up/down)")
    timestamp: datetime = Field(description="When the log was created")
    storage_type: str = Field(description="Storage backend type (discriminator)")

    class Config:
        frozen = True

    def __repr__(self) -> str:
        """Return string representation for display.

        Implemented by subclasses to return meaningful representation.
        """
        return f"{self.storage_type}:{self.id}"


class LogFileDescriptor(LogDescriptor):
    """Log stored as a local file."""

    storage_type: Literal["file"] = "file"
    path: Path = Field(description="Filesystem path to the log file")

    def __repr__(self) -> str:
        """Return file path as string representation."""
        return str(self.path)


# Discriminated union - Pydantic automatically selects the right type based on storage_type
AnyLogDescriptor = LogFileDescriptor


@dataclass
class LogFilesCleanupResult:
    """Result of a log files cleanup operation.

    Attributes:
        cleaned: List of file paths that were successfully deleted
        kept: List of file paths that were kept (within keep limit)
        failed: List of tuples containing (file_path, exception) for files that failed to delete
    """

    cleaned: list[Path] = field(default_factory=list)
    kept: list[Path] = field(default_factory=list)
    failed: list[tuple[Path, Exception]] = field(default_factory=list)

    @property
    def total_cleaned(self) -> int:
        """Return the number of successfully cleaned files."""
        return len(self.cleaned)

    @property
    def total_kept(self) -> int:
        """Return the number of files kept."""
        return len(self.kept)

    @property
    def total_failed(self) -> int:
        """Return the number of files that failed to delete."""
        return len(self.failed)

    @property
    def has_failures(self) -> bool:
        """Return True if any deletions failed."""
        return len(self.failed) > 0


__all__ = [
    "AnyLogDescriptor",
    "LogDescriptor",
    "LogFileDescriptor",
    "LogFilesCleanupResult",
]
