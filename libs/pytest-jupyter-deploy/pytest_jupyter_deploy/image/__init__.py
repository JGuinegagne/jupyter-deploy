"""E2E test container image definition.

This directory contains the Dockerfile and docker-compose.yml for the E2E test container.
The image is template-independent — it provides the base tooling (Python, Terraform, AWS CLI,
Playwright) while template-specific test files are synced at runtime via `just e2e-sync`.

IMAGE_PATH is used to locate these files and pass them to docker/finch compose.
See https://github.com/jupyter-infra/jupyter-deploy for the full E2E workflow.
"""

from pathlib import Path

IMAGE_PATH: Path = Path(__file__).parent
