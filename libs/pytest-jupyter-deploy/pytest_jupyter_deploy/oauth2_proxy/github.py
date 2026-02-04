"""GitHub OAuth2 Proxy authentication helper for E2E testing."""

import contextlib
import logging
import os
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Page, expect

logger = logging.getLogger(__name__)


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

    def _navigate_with_retry(
        self, url: str, timeout: int = 60000, wait_until: str = "load", max_retries: int = 3
    ) -> None:
        """Navigate to URL with retry logic for DNS propagation delays.

        This method wraps page.goto() with retry logic to handle DNS propagation
        delays that can occur after Route53 records are created or updated.

        Args:
            url: The URL to navigate to
            timeout: Navigation timeout in milliseconds (default: 60000)
            wait_until: When to consider navigation successful (default: "load")
            max_retries: Maximum number of retry attempts (default: 3)

        Raises:
            Exception: If navigation fails after max_retries
        """
        for attempt in range(max_retries):
            try:
                self.page.goto(url, timeout=timeout, wait_until=wait_until)  # type: ignore[arg-type]
                return  # Success - navigation completed
            except Exception as e:
                error_msg = str(e).lower()
                logger.warning(f"Navigation attempt {attempt + 1}/{max_retries} failed: {e}")
                # Check for DNS/connection errors that indicate DNS propagation issues
                is_dns_error = any(
                    err in error_msg
                    for err in [
                        "net::err_name_not_resolved",
                        "ns_error_unknown_host",
                        "getaddrinfo eai_noname",
                        "net::err_connection_refused",
                        "ns_error_connection_refused",
                        "err_connection_refused",
                        "connection refused",
                        "timeout",
                    ]
                )

                if is_dns_error and attempt < max_retries - 1:
                    # Wait with exponential backoff: 2s, 4s, 8s, 16s (max: 30s total)
                    delay = min(2 ** (attempt + 1), 30)
                    logger.debug(f"Retrying navigation in {delay}s (DNS/connection error detected)...")
                    time.sleep(delay)
                else:
                    # Max retries exceeded or non-DNS error - raise original exception
                    raise

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
        self._navigate_with_retry(self.jupyterlab_url, timeout=60000)

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
                    # Check if we're redirected automatically (back to app domain, not GitHub)
                    self.page.wait_for_url(lambda url: "github.com" not in url, timeout=5000)
                except Exception:
                    # Still on authorize page - check if there's an authorize button
                    authorize_button = self.page.get_by_role("button", name="Authorize")
                    try:
                        if authorize_button.is_visible(timeout=2000):
                            authorize_button.click()
                            # Wait for redirect after clicking (back to app domain, not GitHub)
                            self.page.wait_for_url(lambda url: "github.com" not in url, timeout=10000)
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

        # Verify we're back on the application domain (not GitHub)
        # We don't verify JupyterLab is accessible here because the user might be
        # authenticated but not authorized (403 Forbidden)
        current_url = self.page.url
        if "github.com" in current_url:
            raise RuntimeError(f"Authentication did not complete successfully. Still on GitHub: {current_url}")

    def login_without_2fa(self) -> None:
        """Login using username/password without 2FA (for CI environments).

        This method handles three scenarios:
        1. OAuth2 Proxy session is valid (saved cookies) → goes straight to JupyterLab
        2. OAuth2 Proxy session expired but GitHub cookies valid → clicks "Sign in with GitHub",
           GitHub auto-authenticates via OAuth authorize page
        3. Both sessions expired → performs full username/password login

        The method:
        1. Navigates to JupyterLab URL (with any existing cookies from storage state)
        2. Checks if OAuth2 Proxy sign-in page is shown
        3. If sign-in required:
           - Clicks "Sign in with GitHub"
           - If GitHub cookies valid: GitHub auto-authenticates (or clicks Authorize button)
           - If GitHub cookies expired: enters username/password
        4. If already authenticated: skips login (reuses valid OAuth2 Proxy session cookies)
        5. Saves storage state with fresh cookies for future test runs

        After first successful authentication, subsequent test runs will reuse the saved
        session cookies (both OAuth2 Proxy and GitHub), avoiding unnecessary authentication.

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
        # Storage state should be loaded by browser context at this point
        self._navigate_with_retry(self.jupyterlab_url, timeout=60000)

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
            with contextlib.suppress(Exception):
                self.page.wait_for_load_state("networkidle", timeout=10000)

            # Check current URL
            current_url = self.page.url

            # Check if we're on GitHub OAuth authorize page
            if "github.com/login/oauth/authorize" in current_url:
                # With valid cookies, GitHub should either:
                # 1. Auto-submit the authorization
                # 2. Show an "Authorize" button that we need to click

                # Wait a moment for page to load and auto-submit
                try:
                    # Check if we're redirected automatically (back to app domain, not GitHub)
                    self.page.wait_for_url(lambda url: "github.com" not in url, timeout=5000)
                except Exception:
                    # Still on authorize page - check if there's an authorize button
                    authorize_button = self.page.get_by_role("button", name="Authorize")
                    if authorize_button.is_visible(timeout=2000):
                        authorize_button.click()
                        # Wait for redirect after clicking (back to app domain, not GitHub)
                        self.page.wait_for_url(lambda url: "github.com" not in url, timeout=10000)
                    else:
                        # No authorize button - might need username/password
                        # Fall through to check if we're on login page below
                        pass

            # Check if we're on GitHub login page (GitHub cookies expired)
            current_url = self.page.url
            if "github.com/login" in current_url and "oauth" not in current_url:
                # GitHub cookies expired, need to enter username/password
                # Fill in GitHub credentials
                self.page.fill('input[name="login"]', github_username)
                self.page.fill('input[name="password"]', github_password)

                # Submit the form
                self.page.click('input[type="submit"]')

                # Wait for authentication to complete and redirect back to application
                self.page.wait_for_url(f"{self.jupyterlab_url}**", timeout=60000)

        # Save storage state for future test runs (whether we authenticated or used existing session)
        self.save_storage_state()

    def verify_jupyterlab_accessible(self) -> None:
        """Verify that JupyterLab is accessible and loaded.

        This method checks for JupyterLab-specific DOM elements to confirm
        the application has loaded successfully.

        Raises:
            AssertionError: If JupyterLab elements are not found within timeout
        """
        # Check for JupyterLab-specific elements in the DOM
        # Use multiple selectors - whichever appears first
        # These are JupyterLab-specific IDs that won't appear in generic HTML pages
        jupyterlab_locator = self.page.locator("#jp-top-panel, #jp-main-dock-panel, #jp-main-content-panel")

        # Wait for element to be attached to DOM
        jupyterlab_locator.first.wait_for(state="attached", timeout=30000)

        # Verify it's visible
        expect(jupyterlab_locator.first).to_be_visible(timeout=30000)

    def verify_server_unaccessible(self) -> None:
        """Verify that the server is not accessible (connection refused).

        This method attempts to navigate to the JupyterLab URL and expects
        a connection error (NS_ERROR_CONNECTION_REFUSED or similar).

        Raises:
            RuntimeError: If the server is unexpectedly accessible
        """
        try:
            # Attempt to navigate to JupyterLab URL
            # Use a shorter timeout since we expect this to fail quickly
            self.page.goto(self.jupyterlab_url, timeout=10000, wait_until="domcontentloaded")

            # If we get here, the page loaded - server is accessible when it shouldn't be
            raise RuntimeError(
                f"Server is unexpectedly accessible at {self.jupyterlab_url}. Expected connection refused error."
            )
        except Exception as e:
            error_msg = str(e).lower()
            # Check for connection refused errors
            # Playwright throws errors with messages like:
            # - "net::ERR_CONNECTION_REFUSED"
            # - "NS_ERROR_CONNECTION_REFUSED"
            # - "Timeout" (if the connection times out)
            if any(
                indicator in error_msg
                for indicator in [
                    "connection refused",
                    "err_connection_refused",
                    "ns_error_connection_refused",
                    "timeout",
                    "net::err_",
                ]
            ):
                # Expected behavior - server is not accessible
                return

            # Unexpected error - re-raise
            raise RuntimeError(f"Unexpected error while verifying server is unaccessible: {e}") from e

    def verify_oauth_proxy_accessible(self) -> None:
        """Verify that the OAuth2 Proxy page is accessible and responding.

        This method navigates to the JupyterLab URL and verifies that the OAuth2 Proxy
        sign-in page loads successfully (showing the "Sign in with GitHub" button).
        It does NOT authenticate - just confirms the deployment is up and OAuth proxy
        is responding.

        Use in deployment tests to verify a fresh deployment is immediately accessible.

        Raises:
            AssertionError: If OAuth2 Proxy sign-in page does not load within timeout
        """
        # Navigate to the JupyterLab URL
        # Allows higher retry to account for route53 stabilization.
        self._navigate_with_retry(self.jupyterlab_url, timeout=60000, max_retries=10)

        # Verify OAuth2 Proxy sign-in button is visible
        sign_in_button = self.page.get_by_role("button", name="Sign in with GitHub")
        expect(sign_in_button).to_be_visible(timeout=30000)

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
        # If we see JupyterLab-specific elements, we're authenticated
        return bool(self.page.locator("#jp-top-panel, #jp-main-dock-panel, #jp-main-content-panel").first.is_visible())

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

    def login_manually_with_2fa_oauth(self) -> None:
        """One-time manual GitHub OAuth authentication with 2FA/passkey completion.

        This method:
        1. Navigates to the JupyterLab URL
        2. Clicks "Sign in with GitHub"
        3. Waits for user to manually complete authentication (including 2FA/passkey)
        4. Waits for redirect back to JupyterLab
        5. Saves the storage state for future test runs

        This is intended for interactive use to set up authentication once.
        After running this, automated tests can use login_with_auth_session().

        Raises:
            RuntimeError: If navigation fails or authentication doesn't complete
        """
        # Navigate to JupyterLab URL
        print(f"🔗 Navigating to {self.jupyterlab_url}")
        try:
            self._navigate_with_retry(self.jupyterlab_url, timeout=60000)
        except Exception as e:
            error_msg = f"Error navigating to {self.jupyterlab_url}: {e}"
            print(error_msg)
            raise RuntimeError(error_msg) from e

        # Click "Sign in with GitHub" button
        print("🔍 Looking for 'Sign in with GitHub' button...")
        try:
            sign_in_button = self.page.get_by_role("button", name="Sign in with GitHub")
            sign_in_button.wait_for(timeout=10000)
            print("✓ Found sign-in button, clicking...")
            sign_in_button.click()
        except Exception as e:
            error_msg = f"Could not find 'Sign in with GitHub' button: {e}"
            print(f"Error: {error_msg}")
            raise RuntimeError(error_msg) from e

        # Wait for GitHub login page
        print("⏳ Waiting for GitHub login page...")
        try:
            self.page.wait_for_url("**/github.com/**", timeout=30000)
            print("✓ Redirected to GitHub")
        except Exception as e:
            error_msg = f"Failed to redirect to GitHub: {e}"
            print(f"Error: {error_msg}")
            raise RuntimeError(error_msg) from e

        # Manual 2FA/passkey completion
        print("\n" + "=" * 60)
        print("🔐 Please complete GitHub authentication in the browser")
        print("=" * 60)
        print(f"⏳ Waiting for redirect back to {self.jupyterlab_url}...\n")

        # Wait for successful auth and redirect back to JupyterLab
        # Extract the origin (scheme + host) for URL matching
        parsed_url = urlparse(self.jupyterlab_url)
        jupyterlab_origin = f"{parsed_url.scheme}://{parsed_url.netloc}"

        try:
            # Use a lambda to check if URL starts with the JupyterLab origin
            # This handles redirects to /lab, /lab?, etc.
            self.page.wait_for_url(
                lambda url: url.startswith(jupyterlab_origin),
                timeout=300000,
                wait_until="commit",
            )
            print(f"✓ Successfully redirected to JupyterLab: {self.page.url}")
        except Exception as e:
            error_msg = f"Authentication did not complete: {e}"
            print(f"Error: {error_msg}")
            raise RuntimeError(error_msg) from e

        # Wait for JupyterLab to initialize (verify it actually loaded)
        print("⏳ Waiting for JupyterLab to initialize...")
        try:
            # Check for JupyterLab-specific elements in the DOM
            # Use state='attached' instead of 'visible' since elements may be hidden during load
            # Try multiple selectors - whichever appears first
            self.page.locator("#jp-top-panel, #jp-main-dock-panel, #jp-main-content-panel").first.wait_for(
                state="attached", timeout=15000
            )
            print("✓ JupyterLab initialized successfully")
        except Exception as e:
            print(f"⚠ Warning: Could not confirm JupyterLab loaded, but continuing: {e}")
            # Don't fail - the auth already worked if we got redirected

        # Save authentication state
        self.save_storage_state()
        print(f"\n✅ Authentication state saved to {self.storage_state_path}")
