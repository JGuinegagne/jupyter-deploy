"""E2E test utilities for the base template."""

from pytest_jupyter_deploy.oauth2_proxy.github import GitHubOAuth2ProxyApplication


def verify_access_forbidden(github_oauth_app: GitHubOAuth2ProxyApplication) -> None:
    """Verify that the user is authenticated but not authorized.

    This is template-specific verification for the base template.
    The base template displays a custom error page with title "Authorization Failure"
    from the oauth_error_500.html.tftpl template when a user is authenticated
    with GitHub but not in the allowlist.

    Args:
        github_oauth_app: GitHub OAuth2 Proxy application helper

    Raises:
        AssertionError: If the forbidden page is not displayed

    Note:
        This function assumes the user has already been authenticated via
        ensure_authenticated(). It does not navigate or authenticate.
    """
    # Wait for page to load if needed
    github_oauth_app.page.wait_for_load_state("domcontentloaded", timeout=10000)

    # Check for the custom error page title
    # The base template uses oauth_error_500.html.tftpl which has "Authorization Failure" as title
    # Use page.title() instead of locator since title element text content doesn't work reliably with Playwright
    page_title = github_oauth_app.page.title()
    assert "Authorization Failure" in page_title, f"Expected 'Authorization Failure' in page title, got: '{page_title}'"
