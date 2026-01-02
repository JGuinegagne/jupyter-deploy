# Contributing guidelines
-----

## Project setup
This project leverages [uv](https://docs.astral.sh/uv/getting-started/) to manage dependencies,
run tools such as linter, type-checker, testing, or publishing.
The monorepo contains multiple packages managed as a `uv` [workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/).

Fork and clone the repository to your local workspace, then install `uv`.

```bash
# Use the sync command to create your python virtual environment,
# download the dependencies and install all packages
uv sync
```

You should see a `.venv` directory under the root of the project.

## Interact with the library
```bash
# Activate the virtual environment
source .venv/bin/activate

# Verify the CLI installation with
jupyter-deploy --help
```

## Run tools
This project uses:
1. [ruff](https://docs.astral.sh/ruff/) for linting, formatting and import sorting
2. [mypy](https://mypy-lang.org/) for type checking enforcement
3. [pytest](https://docs.pytest.org/en/stable/) to run unit and integration tests

You can access each tool with the `uv` commands.

### Lint your code
```bash
# Run the linter
uv run ruff check

# You can attempt to fix linter issues
uv run ruff check --fix
```

### Format your code
`ruff` is a code formatter in addition to a linter

```bash
# Format the code before raising a pull request
uv run ruff format

# When contributing HCL files (.tf), run terraform formatting
terraform fmt -write=true -recursive
```

### Verify formatting
```bash
# Check that you have formatted your Python code
uv run --script scripts/verify_format.py

# and your HCL files
terraform fmt -check -recursive
```

### Enforce type checking
```bash
uv run mypy
```

### Run unit tests
```bash
uv run pytest
```

### Run integration tests

Integration tests (also called E2E tests) verify the entire deployment workflow, including infrastructure provisioning, configuration, and application functionality. These tests use the `pytest-jupyter-deploy` plugin and Playwright for UI testing.

#### Setup

**Option 1: Using Docker (Recommended for reproducibility)**

The repository includes a docker-compose setup for running E2E tests in a containerized environment. This ensures consistent dependencies and avoids GLIBC compatibility issues.

Requirements:
- Docker and docker-compose installed
- `just` command runner: `cargo install just` (or use homebrew/package manager)
- For UI tests with authentication: SSH with X11 forwarding enabled (`ssh -X`)

**Option 2: Local installation**

For UI testing with Playwright, install additional dependencies:
```bash
# Install Playwright dependencies
uv add pytest-playwright --dev
uv run playwright install chromium
```

Note: This requires GLIBC 2.27+ (Amazon Linux 2 is not supported).

#### Running E2E Tests

**Using Docker + Just (Recommended)**

First-time setup:
```bash
# 1. Start E2E container in background
just e2e-up

# 2. Install dependencies (one-time, or after dependency changes)
just e2e-setup
```

Run E2E tests against an existing deployment:
```bash
# Run all E2E tests
just test-e2e sandbox3

# Run only application tests
just test-e2e sandbox3 test_application

# Run only host tests
just test-e2e sandbox3 test_host
```

Full workflow (start container, setup, and run tests in one command):
```bash
just e2e-all sandbox3 [test-filter]
```

Setup authentication (one-time, requires X11 forwarding):
```bash
just auth-setup <project-dir>
```

Stop the E2E container when done:
```bash
just e2e-down
```

CI mode (uses GITHUB_USERNAME/GITHUB_PASSWORD environment variables):
```bash
export GITHUB_USERNAME="ci-account"
export GITHUB_PASSWORD="password"
just test-e2e-ci sandbox3
```

**Using pytest directly**

By default, E2E tests are excluded from regular test runs. Use the `-m e2e` marker to run them explicitly.

**Against an Existing Deployment**

To test against a manually deployed project without creating new infrastructure:

```bash
pytest -m e2e --e2e-existing-project=<path-to-project>
```

Example:
```bash
# Run tests against existing sandbox3 deployment
pytest -m e2e --e2e-existing-project=sandbox3
```

**With Automatic Deployment**

To automatically deploy infrastructure, run tests, and tear down:

```bash
pytest -m e2e
```

**Skip Cleanup (for debugging)**

```bash
pytest -m e2e --no-cleanup
```

Note: Cleanup is automatic when using `--e2e-existing-project` (won't destroy the existing project).

#### Playwright Options

Capture screenshots on test failures:
```bash
pytest -m e2e --screenshot only-on-failure --full-page-screenshot
```

Configure output directory (default: `test-results`):
```bash
pytest -m e2e --screenshot only-on-failure --output=test-results
```

#### Configuration Options

- `--e2e-existing-project=PATH`: Use existing deployment instead of creating new one
- `--e2e-tests-dir=DIR`: E2E tests directory (default: `tests/e2e`)
- `--e2e-config-name=NAME`: Configuration name from `configurations/` directory (default: `base`)
- `--deployment-timeout-seconds=N`: Deployment timeout in seconds (default: 1800)
- `--teardown-timeout-seconds=N`: Teardown timeout in seconds (default: 600)
- `--no-cleanup`: Skip infrastructure cleanup after tests

#### Authentication Setup

E2E tests that interact with the JupyterLab UI require GitHub OAuth2 authentication. Since most GitHub accounts use 2FA/passkeys (which cannot be automated), you need to complete authentication manually once before running UI tests.

**One-Time Setup (Using Docker)**

1. Ensure you're SSH'd with X11 forwarding enabled:
   ```bash
   ssh -X your-host
   ```

2. Verify DISPLAY is set in your terminal:
   ```bash
   echo $DISPLAY  # Should show something like "localhost:10.0"
   ```

   **Note**: If using VS Code's embedded terminal, it won't inherit X11 forwarding. Either:
   - Run commands from a regular SSH terminal, OR
   - Manually export DISPLAY in VS Code terminal: `export DISPLAY=localhost:11.0`

3. Run the authentication setup (a Firefox browser window will open via X11):
   ```bash
   just auth-setup my-project
   ```

   **Note**: The setup uses Firefox for better X11 forwarding compatibility.

4. Complete the GitHub OAuth flow including 2FA/passkey authentication in the browser

5. The authenticated browser state is saved to `.auth/github-oauth-state.json`

6. Run E2E tests - they will reuse the saved authentication:
   ```bash
   just test-e2e my-project
   ```

**Alternative: Direct Script Execution**

If not using Docker:
```bash
uv run python scripts/github_auth_setup.py --project-dir=my-project
```

**CI/CD**

For CI/CD environments, use the `--ci` flag with GITHUB_USERNAME and GITHUB_PASSWORD environment variables:
```bash
export GITHUB_USERNAME="ci-account"
export GITHUB_PASSWORD="password"
just test-e2e-ci my-project
```

**Note**: The `.auth/` directory is excluded from version control to avoid committing sensitive authentication data.

**Session Management**: OAuth2 Proxy stores sessions in memory by default. When the OAuth2 Proxy server restarts (e.g., after running `jd down` and `jd up`), the OAuth2 Proxy session is lost. However, if your GitHub cookies are still valid (they last 7 days by default), tests will automatically re-authenticate by:
1. Detecting the OAuth2 Proxy sign-in page
2. Clicking "Sign in with GitHub"
3. GitHub auto-authenticates using valid cookies (no manual 2FA needed)
4. Redirecting back to JupyterLab

You only need to re-run `just auth-setup` when GitHub cookies have also expired (requiring manual 2FA/passkey authentication).
