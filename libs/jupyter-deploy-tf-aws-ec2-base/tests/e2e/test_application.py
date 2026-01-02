"""E2E tests for JupyterLab application accessibility and functionality."""

from playwright.sync_api import expect
from pytest_jupyter_deploy.oauth2_proxy.github import GitHubOAuth2ProxyApplication


def test_application_accessible(github_oauth_app: GitHubOAuth2ProxyApplication) -> None:
    """Test that the application is accessible from the webbrowser."""
    # Ensure authenticated (uses saved session or CI credentials)
    github_oauth_app.ensure_authenticated()

    # Verify we're on JupyterLab by checking for the main work area
    expect(github_oauth_app.page.locator("#main")).to_be_visible(timeout=30000)


# def test_launcher_displayed(github_oauth_app: GitHubOAuth2ProxyApplication) -> None:
#     """Test that the JupyterLab launcher is displayed."""
#     # Ensure we're authenticated
#     github_oauth_app.ensure_authenticated()
#
#     # Wait for JupyterLab to fully load
#     expect(github_oauth_app.page.locator("#main")).to_be_visible(timeout=30000)
#
#     # Look for the launcher
#     # The launcher typically has a class "jp-Launcher"
#     launcher = github_oauth_app.page.locator(".jp-Launcher")
#     expect(launcher).to_be_visible(timeout=10000)
#
#     # Verify launcher has notebook creation options
#     # Look for "Notebook" section in launcher
#     notebook_section = github_oauth_app.page.locator(".jp-Launcher-section").filter(has_text="Notebook")
#     expect(notebook_section).to_be_visible(timeout=5000)
#
#
# def test_notebook_create_and_save(github_oauth_app: GitHubOAuth2ProxyApplication) -> None:
#     """Test that a new notebook can be opened and saved."""
#     # Ensure we're authenticated
#     github_oauth_app.ensure_authenticated()
#
#     # Wait for JupyterLab to fully load
#     expect(github_oauth_app.page.locator("#main")).to_be_visible(timeout=30000)
#
#     # Create a new notebook by clicking on the Python kernel in launcher
#     # Look for launcher items with "Python" in them
#     python_launcher = github_oauth_app.page.locator(".jp-Launcher-item").filter(has_text="Python")
#     expect(python_launcher).to_be_visible(timeout=10000)
#     python_launcher.first.click()
#
#     # Wait for notebook to open
#     # A notebook cell should be visible
#     notebook_cell = github_oauth_app.page.locator(".jp-Cell")
#     expect(notebook_cell).to_be_visible(timeout=10000)
#
#     # Type some code in the first cell
#     code_editor = github_oauth_app.page.locator(".jp-Cell-inputArea .cm-content").first
#     code_editor.click()
#     code_editor.type("print('Hello from E2E test')")
#
#     # Save the notebook using Ctrl+S
#     github_oauth_app.page.keyboard.press("Control+s")
#
#     # Wait a moment for save to complete
#     github_oauth_app.page.wait_for_timeout(2000)
#
#     # Verify the notebook is saved by checking the title doesn't have an asterisk
#     # (unsaved notebooks show "Untitled.ipynb*")
#     tab_label = github_oauth_app.page.locator(".jp-TabBar-tab.jp-mod-current .jp-TabBar-tabLabel")
#     expect(tab_label).to_be_visible(timeout=5000)
#
#     # The tab should show "Untitled.ipynb" without asterisk after save
#     # Check that it contains "Untitled" and doesn't end with "*"
#     tab_text = tab_label.text_content()
#     assert tab_text is not None
#     assert "Untitled" in tab_text
#     assert not tab_text.strip().endswith("*"), f"Notebook not saved: tab shows '{tab_text}'"
