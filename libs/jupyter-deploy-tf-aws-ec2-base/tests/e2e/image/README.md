# E2E Test Container Image

This directory contains the Docker/Finch image definition for running E2E tests for the `jupyter-deploy-tf-aws-ec2-base` template.

## Overview

The E2E test container is template-specific to ensure each template has the exact dependencies it needs for testing. The container:

- Copies project files during build (excluding `.venv` via `.dockerignore`)
- Mounts `.auth/` directory at runtime to persist authentication state
- Mounts `./sandbox-e2e` directory to persist project state in case tests fail
- Supports both Docker and Finch (automatically detected)
- Includes all necessary tools: Python, Terraform, AWS CLI, Playwright (Firefox)

## Files

- **Dockerfile**: Image definition with all dependencies
- **docker-compose.yml**: Container configuration with volume mounts
- **.dockerignore**: Excludes `.venv` and other files from image

## Usage

All commands should be run from the repository root using `just`:

```bash
# Start the container (builds image automatically if needed)
just e2e-up

# Run tests
just test-e2e <project-dir> [test-filter]

# Stop the container
just e2e-down

# Rebuild the image after code or dependency changes
just e2e-build
```

**Note**: The image is built automatically by docker-compose when you run `just e2e-up` for the first time. Dependencies are installed during the image build, so any changes to `pyproject.toml` or code require rebuilding the image with `just e2e-build`.

## Container Tool Detection

The justfile automatically detects whether to use `docker` or `finch`:

- On AWS Cloud Desktop: uses `finch`
- On other systems: uses `docker` if available

All commands use the `--project-directory` flag to ensure paths in docker-compose.yml are resolved relative to the repository root, keeping configuration clean and simple (no `../../../` relative paths needed).

## Volume Mounts

The container mounts:

- `.auth/`: Persists GitHub OAuth authentication state (read-write)
- `~/.aws`: AWS credentials for infrastructure operations (read-only)
- `/tmp/.X11-unix`: X11 socket for GUI applications like Firefox (for auth setup)

## Why Copy Files Instead of Mount?

The container copies project files during build rather than mounting the repository root because:

1. **Avoid .venv conflicts**: The host's `.venv` (if present) would shadow the container's Python environment
2. **Immutability**: Ensures consistent test environment regardless of host changes
3. **Performance**: Faster file access within the container

Only `.auth/` is mounted at runtime to persist authentication state across container restarts.

## Rebuilding the Image

The docker-compose `build:` directive automatically builds the image on first `just e2e-up`.

Rebuild the image after:
- Changing the Dockerfile
- Adding system dependencies

Since project files and dependencies are baked into the image, changes require either:

### Full Rebuild (for system/Dockerfile changes)
```bash
just e2e-build
```

### Quick Sync (for code/dependency changes)
```bash
just e2e-sync
```

The `e2e-sync` command:
1. Copies updated project files to the running container
2. Removes the container's `.venv`
3. Runs `uv sync --all-packages` to reinstall dependencies

This is much faster than rebuilding the entire image when iterating on code or updating Python dependencies.
