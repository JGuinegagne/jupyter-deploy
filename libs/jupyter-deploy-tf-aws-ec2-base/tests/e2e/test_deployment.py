"""E2E test for full deployment lifecycle from scratch."""

import pytest
from pytest_jupyter_deploy.oauth2_proxy.github import GitHubOAuth2ProxyApplication


@pytest.mark.order(1)  # Run first
@pytest.mark.full_deployment  # Only runs when deploying from scratch
def test_immediately_available_after_deployment(
    github_oauth_app: GitHubOAuth2ProxyApplication,
) -> None:
    """Test complete deployment: init, config, up, verify OAuth proxy accessible.

    This test only runs when deploying from scratch (ie a new sandbox-e2e dir).
    After deployment completes, it verifies:
    1. OAuth2 Proxy is responding and accessible
    2. User can authenticate and access JupyterLab

    The test does NOT ensure the server is running first - it expects that
    after `jd up` completes, everything should be running and accessible.
    """
    # Immediately verify OAuth proxy is accessible
    # This will land on OAuth login page (before authentication)
    github_oauth_app.verify_oauth_proxy_accessible()

    # Now authenticate and verify full JupyterLab access
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()
