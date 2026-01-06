#!/usr/bin/env python
"""One-time GitHub OAuth authentication setup for E2E tests.

This script opens a browser window for manual authentication with GitHub OAuth2 Proxy.
After successful authentication (including 2FA/passkey), the browser storage state
is saved to `.auth/github-oauth-state.json` for reuse in automated tests.

IMPORTANT: This script is designed to run inside the E2E testing container, not on the host.
It depends on pytest-jupyter-deploy which is available in the containerized environment.

Usage (from host):
    just auth-setup <project-dir>

Example:
    just auth-setup sandbox3

Direct usage (inside container):
    uv run python scripts/github_auth_setup.py --project-dir=<path-to-deployed-project>
"""

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright
from pytest_jupyter_deploy import constants
from pytest_jupyter_deploy.cli import JDCli
from pytest_jupyter_deploy.oauth2_proxy.github import GitHubOAuth2ProxyApplication


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

        context = browser.new_context()
        page = context.new_page()

        # Use the GitHubOAuth2ProxyApplication helper for authentication
        oauth_app = GitHubOAuth2ProxyApplication(
            page=page,
            jupyterlab_url=jupyterlab_url,
            storage_state_path=storage_state_path,
            is_ci=False,
        )

        try:
            oauth_app.login_manually_with_2fa_oauth()
        except RuntimeError as e:
            print(f"\n❌ Error: {e}")
            browser.close()
            sys.exit(1)

        print("\n💡 You can now run E2E tests without re-authenticating:")
        print("   just test-e2e <project-dir>")

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
        default=Path.cwd() / constants.AUTH_DIR / constants.GITHUB_OAUTH_STATE_FILE,
        help=f"Path to save storage state (default: {constants.AUTH_DIR}/{constants.GITHUB_OAUTH_STATE_FILE})",
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
