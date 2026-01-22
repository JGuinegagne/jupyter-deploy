# Project Context
This is a monorepo to deploy Jupyter or IDE types of application to the Cloud.
It consists in several packages, all managed as uv workspace members.

## The CLI package
Code: `./libs/jupyter-deploy`
CLI tool for deploying Jupyter server to the cloud.

It's cloud-provider and infrastructure-as-code agnostic. The CLI code MUST NOT:
- depend directly on any cloud provider-specific libraries (e.g. `boto3` for AWS)
- assume that an infrastructure-as-code engine is selected (e.g. it MUST remain extensible to other engines than `terraform`)

To access cloud-provider specific dependencies, we use optional installs such as `pip install juptyer-deploy[aws]` 
Then module `provider/instruction_runner_factory` handles these optional imports.
You MUST NOT break that pattern with import statements to cloud-provider or infrastructure-as-code specific libraries
outside of the instruction runner code paths.

## Base template package
Code: `./libs/jupyter-deploy-tf-ec2-base`

Primary template used by the CLI, referred to as "base template".
- infrastructure-as-code engine: `terraform`
- cloud provider: `aws`
- identity provider: `github`

All variables MUST be defined in `variables.tf` without default values.
Default values MUST be set in `presets/defaults-all.tfvars`.
There MUST BE be any `variable` blocks in files other than `variables.tf`.

IMPORTANT: Do not copy files to `/home/jovyan` during Docker build time.
The EBS volume for Jupyter data is mounted at runtime, and any files copied during build will be hidden by this mount.
Instead, copy files to a location like `/opt` during build and then copy them to `/home/jovyan` in startup scripts.

## E2E Pytest plugin package
Code: `./libs/pytest-jupyter-deploy`

A set of pytest fixtures to run end-to-end tests for templates, referred to as "pytest plugin".

# Development Workflow

## After code changes
Always run from the root of the repository:
1. Run linting and formatting: `just lint`
   - Runs `ruff format`, `ruff check --fix`, `mypy`, and `terraform fmt`
2. Run unit tests: `just unit-test`
   - Runs `uv run pytest`

## General coding rules
1. you MUST NOT use runtime import in python; only exception is `<cli>/provider/instrauction_runner_factory` module
2. you MUST NOT silence linters without the user's permission
3. you MUST NOT write docstrings that merely repeat a method name

## Writing unit tests
Unit tests are located in `libs/<package-name>/tests/unit`

1. Define `unittest.TestCase` instance for each class, function or major method to be tested
2. you SHOULD NOT use `pytest.fixtures`
3. Use `@patch()` or inline `with patch` when possible
4. Always set `: Mock` typing for `mypy` with patches
5. When mocking boto3 types in tests, use proper type annotations (e.g., `instance_state: InstanceStateTypeDef = {"Code": code}`) rather than casting
6. If you detect inconsistencies between implementation and test assertions (e.g., code raises `KeyError` but test expects `ValueError`), notify the user of the implementation issue rather than modifying the unit tests to pass

## Writing E2E tests
E2E tests are located in `libs/<template-name>/tests/e2e/`

1. Use the pytest plugin for test fixtures and helpers
2. Use `@skip_if_testvars_not_set([...])` decorator to skip tests when required env vars are missing
3. Template-specific utilities should be in `test_utils.py` within the template's e2e directory
4. Template-specific fixtures should be in `conftest.py` within the template's e2e directory

# E2E Testing Workflow
E2E tests validate a complete deployment with actual CLI commands and browser-based interactions using `playwright`.

The E2E tests run in a local container using `pytest` where `playwright` and webbrowsers are installed.
- `just e2e-up` builds and starts the container.
- `just e2e-sync` synchronizes the workspace files with the container.
Look at `./justfile` for more details.
IMPORTANT: you CANNOT run any e2e directly with `uv run pytest E2E-TEST-SELECTOR`, you MUST use a `just` command.

## Prerequisites
1. A deployed project to test against located in a dir relative to the workspace root (e.g., `./sandbox`)
2. Some E2E tests require environment variables to be set:
    - look at `./env.example` in the workspace root
    - the user must have created an `.env` file with values at the workspace root
    - tests will be skipped if the required test environment variables are not set.
3. Most E2E tests for the base template require a specific oauth setup (see Authentication setup)

## Configuration Tests
The configuration test verifies a template project is correctly wired up.
In the case of the base template, this corresponds to the `terraform plan` operation succeeding.

To run the configuration test:
1. ask the user for the `<project-dir>` to use
2. run `just test-e2e <project-dir> test_configuration`

## Authentication Setup for the base template
Before running E2E tests, ask the user to run GitHub OAuth authentication: `just auth-setup <project-dir>`.
This will:
- Launch a browser for the user to authenticate with GitHub (with 2FA presumably)
- Save authentication state to `.auth/github-oauth-state.json`
- Allow automated tests to reuse the session

## Running E2E Tests
Run E2E tests against an existing deployment: `just test-e2e <project-dir> TEST-SELECTOR`

Examples:
- Run all E2E tests without mutating the project: `just test-e2e sandbox3 ""`
- Run all E2E tests: `just test-e2e sandbox3 "" mutate=true`
- Run specific test file: `just test-e2e sandbox3 test_users` (possibly needs `mutate=true`)

**NOTE:** mutate tests are long, pipe to log stream to file: `just test-e2e <project-dir> TEST-SELECTOR mutate=true 2>&1 | tee results.log`   
The test container saves screenshots of failed tests to `./test-results`, use the read image tool.

# Debugging and Investing Deployments

## Useful jd commands
Essential commands for debugging a deployed instance that uses the base template.
- `jd server status` - Check server health status (IN_SERVICE, OUT_OF_SERVICE, etc.)
- `jd server restart` - Restart all services
- `jd host status` - Check EC2 instance status
- `jd host exec -- "command"` - Execute commands on the instance
- `jd server exec -s SERVICE -- CMD` - Execute commands in the container on the instance
- `jd host exec -- tail -50 /var/log/jupyter-deploy/LOG-FILENAME` - View command logs (e.g. `update-server.log` for `jd server restart` logs)
- `jd host exec -- tail -50 /var/log/services/LOG-FILENAME` - View historic service logs (survives container restart)
- `jd server logs -s SERVICE` - View service logs
- `jd config` - Reconfigure deployment (generates terraform plan)
- `jd up` - Apply infrastructure changes
- `jd show --variables --list` - Display list of available variables
- `jd show --outputs --list` - Display list of available outputs
- `jd show -v VARIABLE-NAME --text` - Display the variable value (careful: it does not guarantee it was applied with `jd up`)
- `jd show -o OUTPUT-NAME --text` - Display the output value
- `jd --help` or `jd CMD SUB-CMD --help` - Find out about API shapes 

## Key file locations on instance in the base template

### Deployment scripts (downloaded from S3 by SSM association)
- `/usr/local/bin/check-status-internal.sh` - Status checking logic
- `/usr/local/bin/get-status.sh` - Status code mapping
- `/usr/local/bin/update-server.sh` - Service management (start/stop/restart)
- `/usr/local/bin/update-auth.sh` - OAuth configuration updates
- `/usr/local/bin/sync-acme.sh` - TLS certificate sync from Secrets Manager

### Docker configuration files
- `/opt/docker/docker-compose.yml` - Docker Compose configuration
- `/opt/docker/docker-startup.sh` - Docker services startup script
- `/opt/docker/dockerfile.jupyter` - Jupyter container Dockerfile
- `/opt/docker/traefik.yml` - Traefik reverse proxy configuration
