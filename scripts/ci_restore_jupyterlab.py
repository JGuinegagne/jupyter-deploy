#!/usr/bin/env python3
"""Find and restore an aws-ec2-jupyterlab e2e project from the S3 store.

Usage:
    scripts/ci_restore_jupyterlab.py <project-dir> [--deployment-id <id>]

The jupyterlab template has no OAuth app / subdomain to look up (unlike the eks-oidc
template, whose ci_restore_eks.py matches by an OAuth-derived subdomain) — access is gated
by the caller's AWS identity. e2e runs are isolated by the deployment id, so several
``tf-aws-ec2-jupyterlab-<deployment_id>`` projects can coexist in the store (parallel
release / canary / PR runs). Pass --deployment-id to restore a specific one; with no id,
restore the single project if exactly one exists (local / manual use).

The template has no masked secrets, so — unlike base/eks — there is no ``jd config
--restore-secrets`` step. Uses scripts/ci_helpers.py to drive the ``jd`` CLI.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from ci_helpers import is_project_deployed, run_jd

JUPYTERLAB_PROJECT_PREFIX = "tf-aws-ec2-jupyterlab-"


def list_jupyterlab_projects() -> list[str]:
    result = run_jd(["projects", "list", "--store-type", "s3-only", "--text"], capture=True)
    return [
        line.strip()
        for line in result.stdout.strip().splitlines()
        if line.strip().startswith(JUPYTERLAB_PROJECT_PREFIX)
    ]


def resolve_project_id(deployment_id: str | None, *, allow_missing: bool = False) -> str | None:
    """Resolve the target project id: the one matching deployment_id, else the sole project."""
    if deployment_id:
        return f"{JUPYTERLAB_PROJECT_PREFIX}{deployment_id}"

    matches = list_jupyterlab_projects()
    if not matches:
        if allow_missing:
            return None
        print(f"Error: No {JUPYTERLAB_PROJECT_PREFIX}* project found in the S3 store")
        sys.exit(1)
    if len(matches) > 1:
        print(f"Error: Multiple {JUPYTERLAB_PROJECT_PREFIX}* projects found — pass --deployment-id to pick one:")
        for m in matches:
            print(f"  {m}")
        sys.exit(1)
    return matches[0]


def restore_project(project_id: str, project_dir: Path) -> None:
    if project_dir.exists():
        shutil.rmtree(project_dir)
    print(f"Restoring project {project_id} to {project_dir}...")
    run_jd(["init", str(project_dir), "--restore-project", project_id, "--store-type", "s3-only"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore a jupyterlab e2e project from the S3 store.")
    parser.add_argument("project_dir", nargs="?", default="sandbox-e2e", help="Directory to restore into")
    parser.add_argument("--deployment-id", default=None, help="Restore the project for this deployment id")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)

    print("Resolving the jupyterlab e2e project in the S3 store...")
    project_id = resolve_project_id(args.deployment_id)
    assert project_id is not None
    print(f"  Target project: {project_id}")

    restore_project(project_id, project_dir)

    if not is_project_deployed(str(project_dir)):
        print(
            f"\nError: Project '{project_id}' exists in the S3 store but has no live infrastructure.",
            file=sys.stderr,
        )
        print(
            "Run the fresh deploy workflow to recreate it, or delete the stale entry with:\n"
            f"  uv run jd projects delete {project_id} --store-type s3-only -y",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"\nJupyterlab e2e project restored at {project_dir}")


if __name__ == "__main__":
    main()
