# List all available commands
default:
    @just --list

# Start E2E container in background
e2e-up:
    docker compose up -d e2e
    @echo "E2E container started. Run 'just e2e-setup' to install dependencies."

# Stop E2E container
e2e-down:
    docker compose down

# Setup dependencies in E2E container (run once after e2e-up)
e2e-setup:
    @echo "Installing dependencies in E2E container..."
    docker compose exec e2e bash -c "\
        apt-get update && \
        apt-get install -y wget unzip gnupg software-properties-common curl jq && \
        \
        if ! command -v terraform &> /dev/null; then \
            echo 'Installing Terraform...' && \
            wget -qO- https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg && \
            echo 'deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com bookworm main' | tee /etc/apt/sources.list.d/hashicorp.list && \
            apt-get update && \
            apt-get install -y terraform; \
        else \
            echo 'Terraform already installed'; \
        fi && \
        \
        if ! command -v aws &> /dev/null; then \
            echo 'Installing AWS CLI...' && \
            curl -s 'https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip' -o 'awscliv2.zip' && \
            unzip -q awscliv2.zip && \
            ./aws/install && \
            rm -rf aws awscliv2.zip; \
        else \
            echo 'AWS CLI already installed'; \
        fi && \
        \
        echo 'Installing Python dependencies...' && \
        uv sync --all-packages && \
        \
        echo 'Installing Playwright browsers...' && \
        uv run playwright install firefox --with-deps \
    "
    @echo "Setup complete! You can now run tests with 'just test-e2e <project-dir>'"

# Run E2E tests in containerized environment
# Usage: just test-e2e <project-dir> [test-filter]
# Example: just test-e2e sandbox3
# Example: just test-e2e sandbox3 test_application
test-e2e project_dir test_filter="":
    #!/usr/bin/env bash
    set -euo pipefail

    # Validate project directory exists
    if [ ! -d "{{project_dir}}" ]; then
        echo "Error: Project directory '{{project_dir}}' does not exist"
        exit 1
    fi

    # Check if container is running
    if ! docker compose ps e2e | grep -q "Up"; then
        echo "Error: E2E container is not running. Start it with: just e2e-up"
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

    docker compose exec e2e bash -c "source .venv/bin/activate && uv run pytest $PYTEST_ARGS"

# Setup GitHub OAuth authentication (one-time, requires X11 forwarding)
# Usage: just auth-setup <project-dir> [display]
# Example: just auth-setup sandbox3
# Example: just auth-setup sandbox3 localhost:10.0
auth-setup project_dir display="${DISPLAY:-}":
    #!/usr/bin/env bash
    set -euo pipefail

    if [ ! -d "{{project_dir}}" ]; then
        echo "Error: Project directory '{{project_dir}}' does not exist"
        exit 1
    fi

    # Check if container is running
    if ! docker compose ps e2e | grep -q "Up"; then
        echo "Error: E2E container is not running. Start it with: just e2e-up"
        exit 1
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
    docker cp ~/.Xauthority jupyter-deploy-e2e:/root/.Xauthority
    docker compose exec e2e chmod 600 /root/.Xauthority

    echo "✓ X11 authentication cookies copied to container"

    echo ""
    echo "Verifying X11 setup..."
    docker compose exec -e DISPLAY={{display}} e2e bash -c "\
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

    docker compose exec -e DISPLAY={{display}} e2e bash -c "\
        export DISPLAY={{display}} && \
        source .venv/bin/activate && \
        uv run python scripts/github_auth_setup.py --project-dir={{project_dir}} \
    "

# Run E2E tests with CI mode (no X11 required, uses GITHUB_USERNAME/GITHUB_PASSWORD)
# Usage: just test-e2e-ci <project-dir> [test-filter]
test-e2e-ci project_dir test_filter="":
    #!/usr/bin/env bash
    set -euo pipefail

    if [ ! -d "{{project_dir}}" ]; then
        echo "Error: Project directory '{{project_dir}}' does not exist"
        exit 1
    fi

    if [ -z "${GITHUB_USERNAME:-}" ] || [ -z "${GITHUB_PASSWORD:-}" ]; then
        echo "Error: GITHUB_USERNAME and GITHUB_PASSWORD environment variables must be set"
        exit 1
    fi

    # Check if container is running
    if ! docker compose ps e2e | grep -q "Up"; then
        echo "Error: E2E container is not running. Start it with: just e2e-up"
        exit 1
    fi

    # Build the pytest command
    PYTEST_ARGS="-m e2e --e2e-existing-project={{project_dir}} --ci"

    if [ -n "{{test_filter}}" ]; then
        PYTEST_ARGS="$PYTEST_ARGS -k {{test_filter}}"
    fi

    PYTEST_ARGS="$PYTEST_ARGS --screenshot only-on-failure --verbose --browser firefox"

    echo "Running E2E tests in CI mode for project: {{project_dir}}"
    echo "================================================"

    docker compose exec e2e bash -c "source .venv/bin/activate && uv run pytest $PYTEST_ARGS"

# Clean up test artifacts
clean-e2e:
    rm -rf test-results .pytest_cache
    docker compose down -v

# Full workflow: start container, setup, run tests
# Usage: just e2e-all <project-dir> [test-filter]
e2e-all project_dir test_filter="":
    @echo "Starting E2E container..."
    @just e2e-up
    @echo ""
    @just e2e-setup
    @echo ""
    @just test-e2e {{project_dir}} {{test_filter}}
