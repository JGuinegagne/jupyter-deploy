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

The repository includes a containerized setup for running E2E tests. Each template has its own E2E image definition under `libs/<template>/tests/e2e/image/`. This ensures consistent dependencies and avoids GLIBC compatibility issues.

Requirements:
- Docker or Finch installed (automatically detected)
- `just` command runner: `cargo install just` (or use homebrew/package manager)
- For UI tests with authentication: SSH with X11 forwarding enabled (`ssh -X`)


#### Running E2E Tests

**Using Docker + Just (Recommended)**

First-time setup:
```bash
# Start E2E container in background (builds image automatically if needed)
just e2e-up
```

**Note**: The E2E image copies project files and installs dependencies during build (excluding `.venv`). The `.auth/` directory is mounted at runtime to persist authentication state across container restarts. The image is built automatically by docker-compose on first `just e2e-up`.

If you change dependencies in `pyproject.toml` or modify code, run `just e2e-sync`

Run E2E tests against an existing deployment:
```bash
# Run all E2E tests
just test-e2e <project-dir>

# Run only specific application tests
just test-e2e sandbox3 test_application
```

Full workflow (start container and run tests in one command):
```bash
just e2e-all <project-dir> [test-filter]
```


Setup authentication (one-time, requires X11 forwarding):
```bash
just auth-setup <project-dir>
```

Stop the E2E container when done:
```bash
just e2e-down
```


#### Authentication Setup

E2E tests that interact with the JupyterLab UI require GitHub OAuth2 authentication. Since most GitHub accounts use 2FA/passkeys (which cannot be automated), you need to complete authentication manually once before running UI tests.

**One-Time Setup (Using Docker)**

1. Ensure you're SSH'd with X11 forwarding enabled:
   ```bash
   ssh -X your-user@your-host
   ```

2. Verify DISPLAY is set in your terminal:
   ```bash
   echo $DISPLAY  # Should show something like "localhost:10.0"
   ```

   **Note**: If using VS Code's embedded terminal, it won't inherit X11 forwarding. Either:
   - Run commands from a regular SSH terminal, OR
   - Manually export DISPLAY in VS Code terminal: `export DISPLAY=localhost:10.0`

3. Run the authentication setup (a Firefox browser window will open via X11):
   ```bash
   just auth-setup <project-dir>
   ```

   **Note**: The setup uses Firefox for better X11 forwarding compatibility.

4. Complete the GitHub OAuth flow including 2FA/passkey authentication in the browser

5. The authenticated browser state is saved to `.auth/github-oauth-state.json`

6. Run E2E tests - they will reuse the saved authentication:
   ```bash
   just test-e2e <project-dir>
   ```

**Note**: The `.auth/` directory is excluded from version control to avoid committing sensitive authentication data.

**Session Management**: OAuth2 Proxy stores sessions in memory by default. When the OAuth2 Proxy server restarts (e.g., after running `jd down` and `jd up`), the OAuth2 Proxy session is lost. However, if your GitHub cookies are still valid (they last 7 days by default), tests will automatically re-authenticate by:
1. Detecting the OAuth2 Proxy sign-in page
2. Clicking "Sign in with GitHub"
3. GitHub auto-authenticates using valid cookies (no manual 2FA needed)
4. Redirecting back to JupyterLab

You only need to re-run `just auth-setup` when GitHub cookies have also expired (requiring manual 2FA/passkey authentication).

#### Setup on Mac for Amazon cloud desktop
You will need to install `xquartz`: `brew install --cask xquartz`
- Open XQuartz: `Settings > Security > Allow connection from network client`
- reboot XQuartz (or restart your laptop)

Then, update `~/.ssh/config` on your mac as follow:
```
Host your-devdesktop-host
    ForwardX11 yes
    ForwardX11Trusted yes
    XAuthLocation /opt/X11/bin/xauth
```

Open a terminal (on your mac), and run:
```
ssh -X username@your-devdesktop-host
```
Get the port xquartz is listening to: `echo $DISPLAY`

Finally, verify that the xserver is running by running on that same mac terminal: `xset q`

