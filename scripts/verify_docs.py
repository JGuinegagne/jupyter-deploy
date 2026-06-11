#!/usr/bin/env python3
"""Verify that the generated CLI reference docs are in sync with the CLI.

Regenerates the per-command reference pages under docs/source/reference/ from
the Typer app and fails if the result differs from what is committed. This
catches the easy-to-forget case where the CLI changes but the docs were not
rebuilt with `just docs-build`.

Usage: python scripts/verify_docs.py
"""

import subprocess
import sys
from pathlib import Path

from rich.console import Console

REFERENCE_DIR = Path("docs/source/reference")
GENERATE_SCRIPT = Path("scripts/generate_cli_ref.py")


def main() -> int:
    console = Console()
    repo_root = Path(__file__).resolve().parent.parent

    gen_result = subprocess.run(
        ["uv", "run", "python", str(GENERATE_SCRIPT), str(REFERENCE_DIR)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if gen_result.returncode != 0:
        console.print("Failed to regenerate CLI reference docs:", style="bold red")
        console.print(gen_result.stderr)
        return 1

    diff_result = subprocess.run(
        ["git", "diff", "--exit-code", "--", str(REFERENCE_DIR)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    if diff_result.returncode != 0:
        console.print(
            f"CLI reference docs under '{REFERENCE_DIR}' are out of date with the CLI.",
            style="bold red",
        )
        console.print(
            "The CLI changed but the generated reference pages were not rebuilt. "
            "Run [bold]just docs-build[/bold] and commit the changes under "
            f"'{REFERENCE_DIR}'.",
            style="bold red",
        )
        console.print("\nDiff:", style="bold red")
        console.print(diff_result.stdout)
        return 1

    console.print(
        f"All good, the CLI reference docs under '{REFERENCE_DIR}' are in sync with the CLI.",
        style="bold green",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
