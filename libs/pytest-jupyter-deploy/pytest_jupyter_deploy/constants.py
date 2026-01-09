"""Constants for pytest-jupyter-deploy plugin."""

# Directory names
SANDBOX_E2E_DIR = "sandbox-e2e"
CONFIGURATIONS_DIR = "configurations"
TEMPLATE_DIR = "template"
TESTS_DIR = "tests"
E2E_TESTS_DIR = "e2e"
AUTH_DIR = ".auth"

# File names
ENV_FILE = ".env"
GITHUB_OAUTH_STATE_FILE = "github-oauth-state.json"
E2E_UP_LOG_FILE = "e2e-up.log"
E2E_DOWN_LOG_FILE = "e2e-down.log"
E2E_UPGRADE_INSTANCE_LOG_FILE = "e2e-upgrade-instance.log"

# Configuration
CONFIGURATION_DEFAULT_NAME = "base"

# Timeouts (in seconds)
DEPLOY_TIMEOUT_SECONDS = 1800  # 30 minutes
DESTROY_TIMEOUT_SECONDS = 600  # 10 minutes
