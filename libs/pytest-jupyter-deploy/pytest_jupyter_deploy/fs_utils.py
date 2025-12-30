"""Filesystem utilities for E2E tests."""

import os
import shutil
from datetime import datetime
from pathlib import Path


def create_sandbox_dir(template_name: str, base_dir: str | None = None) -> Path:
    """Create a timestamped sandbox directory for E2E tests.

    Args:
        template_name: Name of the template (e.g., "aws-ec2-base")
        base_dir: Base directory for sandbox (defaults to JD_E2E_PROJECT_DIR or "sandbox-e2e")

    Returns:
        Path to created sandbox directory
    """
    if base_dir is None:
        base_dir = os.getenv("JD_E2E_PROJECT_DIR", "sandbox-e2e")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    sandbox_path = Path(base_dir) / template_name / timestamp
    sandbox_path.mkdir(parents=True, exist_ok=True)

    return sandbox_path


def cleanup_dir(directory: Path) -> None:
    """Remove a directory and all its contents.

    Args:
        directory: Directory to remove
    """
    if directory.exists():
        shutil.rmtree(directory)
