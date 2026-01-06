# List all available commands
default:
    @just --list

# Detect container tool (finch or docker)
container-tool := `command -v finch >/dev/null 2>&1 && echo "finch" || echo "docker"`

# E2E image configuration
e2e-compose-file := "libs/jupyter-deploy-tf-aws-ec2-base/tests/e2e/image/docker-compose.yml"
e2e-image-name := "jupyter-deploy-e2e-aws-ec2-base"
e2e-image-tag := "latest"

# Build E2E test image (optional - docker compose will build automatically on first up)
e2e-build:
    @echo "Building E2E test image with {{container-tool}}..."
    @mkdir -p {{justfile_directory()}}/sandbox-e2e
    {{container-tool}} compose --project-directory {{justfile_directory()}} -f {{e2e-compose-file}} build --no-cache

# Start E2E container in background (builds image if needed)
e2e-up:
    @echo "Starting E2E container (will build image if needed)..."
    @mkdir -p {{justfile_directory()}}/sandbox-e2e
    {{container-tool}} compose --project-directory {{justfile_directory()}} -f {{e2e-compose-file}} up -d e2e
    @echo "E2E container started. Syncing latest code..."
    @just e2e-sync
    @echo "✓ E2E container ready"

# Stop E2E container
e2e-down:
    @echo "Stopping E2E container..."
    {{container-tool}} compose --project-directory {{justfile_directory()}} -f {{e2e-compose-file}} down

# Sync project files to E2E container (for iterating without rebuilding image)
# NOTE: If you're not seeing your changes, use 'just e2e-rebuild' instead
e2e-sync:
    #!/usr/bin/env bash
    set -euo pipefail

    # Check if container is running
    if ! ({{container-tool}} compose --project-directory {{justfile_directory()}} -f {{e2e-compose-file}} ps e2e) | grep -qE "(Up|running)"; then
        echo "Error: E2E container is not running. Start it with: just e2e-up"
        exit 1
    fi

    echo "Syncing project files to E2E container..."

    # Copy project files to container (excluding .venv, project directories, and build artifacts)
    {{container-tool}} exec jupyter-deploy-e2e-aws-ec2-base bash -c "
        echo 'Removing old .venv...'
        rm -rf /workspace/.venv

        echo 'Copying project files...'
        # We'll use the container tool to copy files
    "

    # Use tar to copy files efficiently (excluding project directories which are mounted)
    echo "Copying files from host to container..."
    cd {{justfile_directory()}} && \
    tar --exclude='.venv' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.pytest_cache' \
        --exclude='test-results' \
        --exclude='.git' \
        --exclude='.ruff_cache' \
        --exclude='.mypy_cache' \
        --exclude='sandbox*' \
        -cf - . | \
    {{container-tool}} exec -i jupyter-deploy-e2e-aws-ec2-base tar -xf - -C /workspace

    echo "Running uv sync..."
    {{container-tool}} compose --project-directory {{justfile_directory()}} -f {{e2e-compose-file}} exec e2e bash -c "cd /workspace && uv sync --all-packages"

    echo "Installing Playwright browsers..."
    {{container-tool}} compose --project-directory {{justfile_directory()}} -f {{e2e-compose-file}} exec e2e bash -c "cd /workspace && uv run playwright install firefox"

    echo "✓ E2E container synced successfully"

# Run E2E tests in containerized environment
# Usage: just test-e2e <project-dir> [test-filter]
# Example: just test-e2e sandbox3
# Example: just test-e2e sandbox3 test_application
test-e2e project_dir test_filter="":
    #!/usr/bin/env bash
    set -euo pipefail

    # Track override file for cleanup
    OVERRIDE_FILE=""

    # Cleanup function
    cleanup() {
        [ -n "$OVERRIDE_FILE" ] && [ -f "$OVERRIDE_FILE" ] && rm -f "$OVERRIDE_FILE"
    }

    # Ensure cleanup on exit
    trap cleanup EXIT

    # Validate project directory exists
    if [ ! -d "{{project_dir}}" ]; then
        echo "Error: Project directory '{{project_dir}}' does not exist"
        exit 1
    fi

    # Mount project directory if it's not sandbox-e2e (which is already mounted)
    if [ "{{project_dir}}" != "sandbox-e2e" ]; then
        echo "Mounting project directory: {{project_dir}}"

        # Create temporary override file to mount the project directory
        OVERRIDE_FILE="{{justfile_directory()}}/docker-compose.e2e-override.yml"
        cat > "$OVERRIDE_FILE" <<EOF
    services:
      e2e:
        volumes:
          - ./{{project_dir}}:/workspace/{{project_dir}}
    EOF

        # Restart container with new mount
        echo "Restarting E2E container with project mount..."
        {{container-tool}} compose --project-directory {{justfile_directory()}} -f {{e2e-compose-file}} -f "$OVERRIDE_FILE" up -d

        # Re-sync files after restart (container loses synced files when restarted)
        echo "Re-syncing project files after mount..."
        just e2e-sync
    fi

    # Check if container is running
    if ! ({{container-tool}} compose --project-directory {{justfile_directory()}} -f {{e2e-compose-file}} ps e2e) | grep -qE "(Up|running)"; then
        echo "Error: E2E container is not running. Start it with: just e2e-up"
        [ -n "$OVERRIDE_FILE" ] && rm -f "$OVERRIDE_FILE"
        exit 1
    fi

    # Build the pytest command
    PYTEST_ARGS="-m e2e --e2e-existing-project={{project_dir}}"

    # Add test filter if provided
    if [ -n "{{test_filter}}" ]; then
        PYTEST_ARGS="$PYTEST_ARGS -k {{test_filter}}"
    fi

    # Add common pytest options
    PYTEST_ARGS="$PYTEST_ARGS --screenshot only-on-failure --verbose --browser firefox"

    echo "Running E2E tests for project: {{project_dir}}"
    echo "Test filter: {{test_filter}}"
    echo "================================================"

    {{container-tool}} compose --project-directory {{justfile_directory()}} -f {{e2e-compose-file}} exec e2e bash -c "cd /workspace && uv run pytest $PYTEST_ARGS"

# Setup GitHub OAuth authentication (one-time, requires X11 forwarding)
# Usage: just auth-setup <project-dir> [display]
# Example: just auth-setup sandbox3
# Example: just auth-setup sandbox3 localhost:10.0
auth-setup project_dir display="${DISPLAY:-}":
    #!/usr/bin/env bash
    set -euo pipefail

    # Track override file for cleanup
    OVERRIDE_FILE=""

    # Cleanup function
    cleanup() {
        [ -n "$OVERRIDE_FILE" ] && [ -f "$OVERRIDE_FILE" ] && rm -f "$OVERRIDE_FILE"
    }

    # Ensure cleanup on exit
    trap cleanup EXIT

    if [ ! -d "{{project_dir}}" ]; then
        echo "Error: Project directory '{{project_dir}}' does not exist"
        exit 1
    fi

    # Check if container is running
    if ! ({{container-tool}} compose --project-directory {{justfile_directory()}} -f {{e2e-compose-file}} ps e2e) | grep -qE "(Up|running)"; then
        echo "Error: E2E container is not running. Start it with: just e2e-up"
        exit 1
    fi

    # Mount project directory if it's not sandbox-e2e (which is already mounted)
    if [ "{{project_dir}}" != "sandbox-e2e" ]; then
        echo "Mounting project directory: {{project_dir}}"

        # Create temporary override file to mount the project directory
        OVERRIDE_FILE="{{justfile_directory()}}/docker-compose.e2e-override.yml"
        cat > "$OVERRIDE_FILE" <<EOF
    services:
      e2e:
        volumes:
          - ./{{project_dir}}:/workspace/{{project_dir}}
    EOF

        # Restart container with new mount
        echo "Restarting E2E container with project mount..."
        {{container-tool}} compose --project-directory {{justfile_directory()}} -f {{e2e-compose-file}} -f "$OVERRIDE_FILE" up -d

        # Re-sync files after restart (container loses synced files when restarted)
        echo "Re-syncing project files after mount..."
        just e2e-sync
    fi

    # Check if DISPLAY is set
    if [ -z "{{display}}" ]; then
        echo "Error: DISPLAY environment variable is not set."
        echo ""
        echo "X11 forwarding is required for authentication setup."
        echo ""
        echo "Solutions:"
        echo "  1. SSH with X11 forwarding: ssh -X your-host"
        echo "  2. Set DISPLAY manually: export DISPLAY=localhost:10.0"
        echo "  3. Pass DISPLAY explicitly: just auth-setup {{project_dir}} localhost:10.0"
        exit 1
    fi

    echo "Setting up GitHub OAuth authentication..."
    echo "Using DISPLAY: {{display}}"
    echo "A browser window will open for you to complete authentication."
    echo "================================================"

    # Setup X11 authentication
    echo "Setting up X11 authentication..."

    # Parse DISPLAY to extract the display number (e.g., "localhost:10.0" -> "10")
    DISPLAY_NUM=$(echo "{{display}}" | cut -d':' -f2 | cut -d'.' -f1)

    # Get X11 auth cookie for this display
    COOKIE=$(xauth list 2>/dev/null | grep ":$DISPLAY_NUM" | awk '{print $NF}' | head -1)

    if [ -z "$COOKIE" ]; then
        echo "⚠ Error: Could not find X11 auth cookie for display :$DISPLAY_NUM"
        echo "Make sure X11 forwarding is enabled (ssh -X) and DISPLAY is set"
        exit 1
    fi

    echo "Found X11 cookie: ${COOKIE:0:16}..."

    # Add localhost cookies to host .Xauthority (needed for TCP connections)
    # xauth converts "localhost:10" to "localhost/unix:10", but we need both formats
    xauth list | grep -q "localhost:$DISPLAY_NUM" || xauth add localhost:$DISPLAY_NUM MIT-MAGIC-COOKIE-1 $COOKIE 2>/dev/null || true
    xauth list | grep -q "127.0.0.1:$DISPLAY_NUM" || xauth add 127.0.0.1:$DISPLAY_NUM MIT-MAGIC-COOKIE-1 $COOKIE 2>/dev/null || true

    # Copy the host's .Xauthority file to container (preserves all cookie formats)
    {{container-tool}} cp ~/.Xauthority jupyter-deploy-e2e-aws-ec2-base:/root/.Xauthority
    {{container-tool}} compose --project-directory {{justfile_directory()}} -f {{e2e-compose-file}} exec e2e chmod 600 /root/.Xauthority

    echo "✓ X11 authentication cookies copied to container"

    echo ""
    echo "Verifying X11 setup..."
    {{container-tool}} compose --project-directory {{justfile_directory()}} -f {{e2e-compose-file}} exec -e DISPLAY={{display}} e2e bash -c "\
        echo \"DISPLAY in container: \$DISPLAY\" && \
        echo \"Container hostname: \$(hostname -f)\" && \
        echo \"\" && \
        echo \"Xauthority file:\" && \
        ls -lh /root/.Xauthority 2>&1 || echo 'No .Xauthority' && \
        echo \"\" && \
        echo \"X11 cookies installed:\" && \
        xauth list 2>&1 || echo 'No xauth cookies' \
    "

    echo ""
    echo "Launching browser..."

    # Ensure project files are synced (check if scripts directory exists)
    if ! {{container-tool}} exec jupyter-deploy-e2e-aws-ec2-base test -d /workspace/scripts; then
        echo "Project files not found in container, syncing..."
        just e2e-sync
    fi

    {{container-tool}} compose --project-directory {{justfile_directory()}} -f {{e2e-compose-file}} exec -e DISPLAY={{display}} e2e bash -c "\
        export DISPLAY={{display}} && \
        cd /workspace && \
        uv run python scripts/github_auth_setup.py --project-dir={{project_dir}} \
    "

# Clean up test artifacts and remove image
clean-e2e:
    rm -rf test-results .pytest_cache
    {{container-tool}} compose --project-directory {{justfile_directory()}} -f {{e2e-compose-file}} down -v
    {{container-tool}} rmi {{e2e-image-name}}:{{e2e-image-tag}} || true

# Full workflow: start container (builds if needed) and run tests
# Usage: just e2e-all <project-dir> [test-filter]
e2e-all project_dir test_filter="":
    @echo "Starting E2E container (will build image if needed)..."
    @just e2e-up
    @echo ""
    @just test-e2e {{project_dir}} {{test_filter}}
