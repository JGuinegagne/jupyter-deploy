"""E2E test configuration for aws-ec2-base template.

The jupyter-deploy-test-engine pytest plugin provides these fixtures automatically:
- e2e_config: Load configuration from suite.yaml
- e2e_deployment: Deploy infrastructure once per session
- jd_cli: CLI command helper
- browser: Playwright browser (if installed)
- browser_context: Browser context with incognito mode
- page: Browser page for UI tests

This file can be used to add template-specific fixtures if needed.
"""

# Add template-specific fixtures here if needed
