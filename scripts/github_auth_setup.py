#!/usr/bin/env python
"""One-time GitHub OAuth authentication setup for E2E tests.

This script opens a browser window for manual authentication with GitHub OAuth2 Proxy.
After successful authentication (including 2FA/passkey), the browser storage state
is saved to `.auth/github-oauth-state.json` for reuse in automated tests.

Usage:
    uv run python scripts/github_auth_setup.py --project-dir=<path-to-deployed-project>

Example:
    uv run python scripts/github_auth_setup.py --project-dir=sandbox3
"""

import argparse
from urllib.parse import urlparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright
from pytest_jupyter_deploy.cli import JDCli


def setup_github_auth(jupyterlab_url: str, storage_state_path: Path) -> None:
    """One-time GitHub OAuth authentication with manual 2FA/passkey completion.

    Args:
        jupyterlab_url: The JupyterLab URL behind OAuth2 Proxy
        storage_state_path: Path to save the browser storage state
    """
    with sync_playwright() as p:
        print("🌐 Launching browser...")
        # Use Firefox (better X11 support than Chromium)
        browser = p.firefox.launch(headless=False)

        context = browser.new_context(
            ignore_https_errors=True,
        )
        page = context.new_page()

        # Start OAuth flow
        print(f"🔗 Navigating to {jupyterlab_url}")
        try:
            page.goto(jupyterlab_url, timeout=60000)
        except Exception as e:
            print(f"Error navigating to {jupyterlab_url}: {e}")
            print("Checking if page is still alive...")
            try:
                print(f"Current URL: {page.url}")
            except Exception:
                print("Page is closed")
            browser.close()
            sys.exit(1)

        # Click "Sign in with GitHub" button
        print("🔍 Looking for 'Sign in with GitHub' button...")
        try:
            sign_in_button = page.get_by_role("button", name="Sign in with GitHub")
            sign_in_button.wait_for(timeout=10000)
            print("✓ Found sign-in button, clicking...")
            sign_in_button.click()
        except Exception as e:
            print(f"Error: Could not find 'Sign in with GitHub' button: {e}")
            browser.close()
            sys.exit(1)

        # Wait for GitHub login page
        print("⏳ Waiting for GitHub login page...")
        try:
            page.wait_for_url("**/github.com/**", timeout=30000)
            print("✓ Redirected to GitHub")
        except Exception as e:
            print(f"Error: Failed to redirect to GitHub: {e}")
            browser.close()
            sys.exit(1)

        # Manual 2FA/passkey completion
        print("\n" + "=" * 60)
        print("🔐 Please complete GitHub authentication in the browser")
        print("=" * 60)
        print(f"⏳ Waiting for redirect back to {jupyterlab_url}...\n")

        # Wait for successful auth and redirect back to JupyterLab
        # Extract the origin (scheme + host) for URL matching
        parsed_url = urlparse(jupyterlab_url)
        jupyterlab_origin = f"{parsed_url.scheme}://{parsed_url.netloc}"

        try:
            # Use a lambda to check if URL starts with the JupyterLab origin
            # This handles redirects to /lab, /lab?, etc.
            page.wait_for_url(
                lambda url: url.startswith(jupyterlab_origin),
                timeout=300000,
                wait_until="commit",
            )
            print(f"✓ Successfully redirected to JupyterLab: {page.url}")
        except Exception as e:
            print(f"Error: Authentication did not complete: {e}")
            browser.close()
            sys.exit(1)

        # Wait for JupyterLab to initialize (verify it actually loaded)
        print("⏳ Waiting for JupyterLab to initialize...")
        try:
            # Check for JupyterLab-specific elements in the DOM
            # Use state='attached' instead of 'visible' since elements may be hidden during load
            # Try multiple selectors - whichever appears first
            page.locator(
                "#jp-top-panel, #jp-main-dock-panel, #jp-main-content-panel"
            ).first.wait_for(state="attached", timeout=15000)
            print("✓ JupyterLab initialized successfully")
        except Exception as e:
            print(
                f"⚠ Warning: Could not confirm JupyterLab loaded, but continuing: {e}"
            )
            # Don't fail - the auth already worked if we got redirected

        # Save authentication state
        storage_state_path.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(storage_state_path))

        print(f"\n✅ Authentication state saved to {storage_state_path}")
        print("\n💡 You can now run E2E tests without re-authenticating:")
        print("   pytest -m e2e --e2e-existing-project=<project-dir>")

        browser.close()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="One-time GitHub OAuth authentication setup for E2E tests"
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        required=True,
        help="Path to deployed jupyter-deploy project",
    )
    parser.add_argument(
        "--storage-state",
        type=Path,
        default=Path.cwd() / ".auth" / "github-oauth-state.json",
        help="Path to save storage state (default: .auth/github-oauth-state.json)",
    )

    args = parser.parse_args()

    if not args.project_dir.exists():
        print(f"Error: Project directory does not exist: {args.project_dir}")
        sys.exit(1)

    print("=" * 60)
    print("GitHub OAuth2 Authentication Setup")
    print("=" * 60)
    print(f"Project directory: {args.project_dir}")
    print(f"Storage state: {args.storage_state}")
    print("=" * 60 + "\n")

    # Get JupyterLab URL using JDCli
    cli = JDCli(args.project_dir)
    jupyterlab_url = cli.get_jupyterlab_url()

    # Run authentication flow
    setup_github_auth(jupyterlab_url, args.storage_state)


if __name__ == "__main__":
    main()
