"""GitHub OAuth2 Proxy authentication helper for E2E testing."""

import contextlib
import os
from pathlib import Path

from playwright.sync_api import Page, expect


class GitHubOAuth2ProxyApplication:
    """Helper class for authenticating through GitHub OAuth2 Proxy."""

    def __init__(
        self, page: Page, jupyterlab_url: str, storage_state_path: Path | None = None, is_ci: bool = False
    ) -> None:
        """Initialize the GitHub OAuth2 Proxy application helper.

        Args:
            page: Playwright Page instance
            jupyterlab_url: The JupyterLab URL behind OAuth2 Proxy
            storage_state_path: Optional path to save/load browser storage state for auth persistence
            is_ci: Whether running in CI environment (uses GITHUB_USERNAME/GITHUB_PASSWORD)
        """
        self.page = page
        self.jupyterlab_url = jupyterlab_url
        self.storage_state_path = storage_state_path
        self.is_ci = is_ci

    def login_with_auth_session(self) -> None:
        """Login using saved authentication session from storage state.

        This method handles two scenarios:
        1. OAuth2 Proxy session is valid → goes straight to JupyterLab
        2. OAuth2 Proxy session expired but GitHub cookies valid →
           clicks "Sign in with GitHub" and GitHub auto-authenticates

        Raises:
            RuntimeError: If GitHub cookies are also expired (requires manual 2FA)
            FileNotFoundError: If storage state wasn't loaded

        Note: Run scripts/github_auth_setup.py first to create the storage state file.
        """
        # Navigate to the JupyterLab URL
        # Storage state should be loaded by browser context at this point
        self.page.goto(self.jupyterlab_url, timeout=60000)

        # Check if we see the OAuth2 Proxy sign-in page
        sign_in_button = self.page.get_by_role("button", name="Sign in with GitHub")
        try:
            sign_in_visible = sign_in_button.is_visible(timeout=2000)
        except Exception:
            sign_in_visible = False

        if sign_in_visible:
            # OAuth2 Proxy session expired, but GitHub cookies might still be valid
            # Click "Sign in with GitHub" to attempt auto-authentication
            sign_in_button.click()

            # Wait for redirect - either:
            # 1. OAuth authorize page → callback → JupyterLab (GitHub cookies valid)
            # 2. GitHub login page (GitHub cookies expired)

            # Wait for navigation to complete (GitHub OAuth flow)
            # Network might not go idle if there are ongoing requests
            with contextlib.suppress(Exception):
                # Wait for redirect away from OAuth2 Proxy or to complete OAuth flow
                # This handles: OAuth2 Proxy → GitHub OAuth authorize → callback → JupyterLab
                self.page.wait_for_load_state("networkidle", timeout=10000)

            # Check current URL
            current_url = self.page.url

            # Check if we're on GitHub OAuth authorize page
            if "github.com/login/oauth/authorize" in current_url:
                # With valid cookies, GitHub should either:
                # 1. Auto-submit the authorization (approval_prompt=force)
                # 2. Show an "Authorize" button that we need to click

                # Wait a moment for page to load and auto-submit
                try:
                    # Check if we're redirected automatically
                    self.page.wait_for_url(f"{self.jupyterlab_url}**", timeout=5000)
                except Exception:
                    # Still on authorize page - check if there's an authorize button
                    authorize_button = self.page.get_by_role("button", name="Authorize")
                    try:
                        if authorize_button.is_visible(timeout=2000):
                            authorize_button.click()
                            # Wait for redirect after clicking
                            self.page.wait_for_url(f"{self.jupyterlab_url}**", timeout=10000)
                        else:
                            # No authorize button visible, might need manual auth
                            error_msg = (
                                "GitHub OAuth authorization timed out!\n\n"
                                "GitHub cookies may have expired or authorization requires manual approval.\n\n"
                                "For local development:\n"
                                "  1. Run: just auth-setup <project-dir>\n"
                                "  2. Complete authentication in the browser\n"
                                "  3. Re-run tests\n\n"
                                "For CI without 2FA:\n"
                                "  Use --ci flag and set GITHUB_USERNAME and GITHUB_PASSWORD environment variables"
                            )
                            raise RuntimeError(error_msg) from None
                    except Exception as e:
                        if "Authorize button" in str(e):
                            raise
                        # Timeout or other error
                        error_msg = (
                            "GitHub OAuth authorization failed!\n\n"
                            f"Error: {e}\n\n"
                            "For local development:\n"
                            "  1. Run: just auth-setup <project-dir>\n"
                            "  2. Complete authentication in the browser\n"
                            "  3. Re-run tests\n\n"
                            "For CI without 2FA:\n"
                            "  Use --ci flag and set GITHUB_USERNAME and GITHUB_PASSWORD environment variables"
                        )
                        raise RuntimeError(error_msg) from e
            elif "github.com" in current_url and self.jupyterlab_url not in current_url:
                # We're on some GitHub page but not authorize or JupyterLab
                # This could be the login page if cookies expired
                error_msg = (
                    "GitHub authentication required!\n\n"
                    "Redirected to GitHub but not on JupyterLab. GitHub cookies may have expired.\n"
                    f"Current URL: {current_url}\n\n"
                    "For local development:\n"
                    "  1. Run: just auth-setup <project-dir>\n"
                    "  2. Complete authentication in the browser\n"
                    "  3. Re-run tests\n\n"
                    "For CI without 2FA:\n"
                    "  Use --ci flag and set GITHUB_USERNAME and GITHUB_PASSWORD environment variables"
                )
                raise RuntimeError(error_msg) from None

            # Save the new OAuth2 Proxy session for future test runs
            self.save_storage_state()

        # Verify we're authenticated and on JupyterLab
        # Use 'attached' state first to check DOM presence, then check visibility
        main_locator = self.page.locator("#main")
        main_locator.wait_for(state="attached", timeout=30000)
        expect(main_locator).to_be_visible(timeout=30000)

    def login_without_2fa(self) -> None:
        """Login using username/password without 2FA (for CI environments).

        This method:
        1. Navigates to the JupyterLab URL
        2. Clicks "Sign in with GitHub"
        3. Fills in username and password from environment variables
        4. Submits the form
        5. Waits for redirect back to JupyterLab
        6. Saves storage state for future test runs

        Requires environment variables:
        - GITHUB_USERNAME: GitHub username
        - GITHUB_PASSWORD: GitHub password

        Raises:
            ValueError: If environment variables are not set

        Note: Only use this for CI environments with GitHub accounts that have 2FA disabled.
        """
        # Check for required environment variables
        github_username = os.getenv("GITHUB_USERNAME")
        github_password = os.getenv("GITHUB_PASSWORD")

        if not github_username or not github_password:
            raise ValueError(
                "GITHUB_USERNAME and GITHUB_PASSWORD environment variables must be set for CI authentication"
            )

        # Navigate to the JupyterLab URL
        self.page.goto(self.jupyterlab_url, timeout=60000)

        # Should land on OAuth2 Proxy sign-in page
        # Look for the "Sign in with GitHub" button
        sign_in_button = self.page.get_by_role("button", name="Sign in with GitHub")
        expect(sign_in_button).to_be_visible(timeout=10000)

        # Click the sign-in button
        sign_in_button.click()

        # Should redirect to GitHub login page
        self.page.wait_for_url("**/github.com/**", timeout=30000)

        # Fill in GitHub credentials
        self.page.fill('input[name="login"]', github_username)
        self.page.fill('input[name="password"]', github_password)

        # Submit the form
        self.page.click('input[type="submit"]')

        # Wait for authentication to complete and redirect back to JupyterLab
        self.page.wait_for_url(f"{self.jupyterlab_url}**", timeout=60000)

        # Verify we're on JupyterLab by checking for the main work area
        expect(self.page.locator("#main")).to_be_visible(timeout=30000)

        # Save storage state for future test runs in CI
        self.save_storage_state()

    def is_authenticated(self) -> bool:
        """Check if the user is already authenticated.

        Returns:
            True if authenticated (on JupyterLab page), False if on GitHub or OAuth2 Proxy page
        """
        current_url = self.page.url
        # If we're on GitHub or see the OAuth2 sign-in button, not authenticated
        if "github.com" in current_url:
            return False
        if self.page.get_by_role("button", name="Sign in with GitHub").is_visible():
            return False
        # If we see JupyterLab main element, we're authenticated
        return bool(self.page.locator("#main").is_visible())

    def ensure_authenticated(self) -> None:
        """Ensure the user is authenticated, performing login if necessary.

        Uses the appropriate login method based on environment:
        - CI mode (--is-ci): Uses login_without_2fa() with GITHUB_USERNAME/GITHUB_PASSWORD
        - Local mode: Uses login_with_auth_session() with saved storage state
        """
        if self.is_ci:
            self.login_without_2fa()
        else:
            self.login_with_auth_session()

    def save_storage_state(self) -> None:
        """Save the browser storage state (cookies, localStorage) to a file.

        This allows reusing the authentication state across test runs without re-authenticating.
        The storage state is saved to the path specified during initialization.
        """
        if self.storage_state_path:
            # Ensure parent directory exists
            self.storage_state_path.parent.mkdir(parents=True, exist_ok=True)
            # Save storage state from the page's context
            self.page.context.storage_state(path=str(self.storage_state_path))
