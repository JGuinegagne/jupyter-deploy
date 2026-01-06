"""E2E tests for user-level access control."""

from pytest_jupyter_deploy.deployment import EndToEndDeployment
from pytest_jupyter_deploy.oauth2_proxy.github import GitHubOAuth2ProxyApplication
from pytest_jupyter_deploy.plugin import skip_if_testvars_not_set

from .test_utils import verify_access_forbidden


@skip_if_testvars_not_set(["JD_E2E_USER"])
def test_admit_user_positive(
    e2e_deployment: EndToEndDeployment, github_oauth_app: GitHubOAuth2ProxyApplication, logged_user: str
) -> None:
    """Test that setting users to logged user allows access."""
    # Prerequisites
    e2e_deployment.ensure_server_running()

    # Clear org and teams
    e2e_deployment.ensure_no_org_nor_teams_allowlisted()

    # Set users to logged user
    e2e_deployment.cli.run_command(["jupyter-deploy", "users", "set", logged_user])

    # Verify list users is correct
    users = e2e_deployment.get_allowlisted_users()
    assert set(users) == {logged_user}, f"Expected exactly [{logged_user}], got {users}"

    # Verify logged user can access the app
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()


@skip_if_testvars_not_set(["JD_E2E_SAFE_USER"])
def test_admit_user_negative(
    e2e_deployment: EndToEndDeployment, github_oauth_app: GitHubOAuth2ProxyApplication, safe_user: str
) -> None:
    """Test that setting users to safe user denies access to logged user."""
    # Prerequisites
    e2e_deployment.ensure_server_running()

    # Clear org and teams
    e2e_deployment.ensure_no_org_nor_teams_allowlisted()

    # Set users to safe user only
    e2e_deployment.cli.run_command(["jupyter-deploy", "users", "set", safe_user])

    # Verify list users is correct
    users = e2e_deployment.get_allowlisted_users()
    assert set(users) == {safe_user}, f"Expected exactly [{safe_user}], got {users}"

    # Verify logged user gets unauthorized page
    github_oauth_app.ensure_authenticated()
    verify_access_forbidden(github_oauth_app)


@skip_if_testvars_not_set(["JD_E2E_USER", "JD_E2E_SAFE_USER"])
def test_add_user(
    e2e_deployment: EndToEndDeployment, github_oauth_app: GitHubOAuth2ProxyApplication, logged_user: str, safe_user: str
) -> None:
    """Test that adding logged user grants access."""
    # Prerequisites
    e2e_deployment.ensure_server_running()

    # Clear org and teams
    e2e_deployment.ensure_no_org_nor_teams_allowlisted()

    # Set users to safe user only
    e2e_deployment.cli.run_command(["jupyter-deploy", "users", "set", safe_user])

    # Add logged user
    e2e_deployment.cli.run_command(["jupyter-deploy", "users", "add", logged_user])

    # Verify list users includes both users
    users = e2e_deployment.get_allowlisted_users()
    assert set(users) == {logged_user, safe_user}, f"Expected exactly [{logged_user}, {safe_user}], got {users}"

    # Verify logged user can access the app
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()


@skip_if_testvars_not_set(["JD_E2E_USER", "JD_E2E_SAFE_USER"])
def test_remove_user(
    e2e_deployment: EndToEndDeployment, github_oauth_app: GitHubOAuth2ProxyApplication, logged_user: str, safe_user: str
) -> None:
    """Test that removing logged user denies access."""
    # Prerequisites
    e2e_deployment.ensure_server_running()

    # Clear org and teams
    e2e_deployment.ensure_no_org_nor_teams_allowlisted()

    # Set users to both users
    e2e_deployment.cli.run_command(["jupyter-deploy", "users", "set", logged_user, safe_user])

    # Remove logged user
    e2e_deployment.cli.run_command(["jupyter-deploy", "users", "remove", logged_user])

    # Verify list users only includes safe user
    users = e2e_deployment.get_allowlisted_users()
    assert set(users) == {safe_user}, f"Expected exactly [{safe_user}], got {users}"

    # Verify logged user gets unauthorized page
    github_oauth_app.ensure_authenticated()
    verify_access_forbidden(github_oauth_app)


@skip_if_testvars_not_set(["JD_E2E_USER", "JD_E2E_SAFE_USER", "JD_E2E_SAFE_ORG"])
def test_add_and_remove_multiple_users(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    logged_user: str,
    safe_user: str,
    safe_org: str,
) -> None:
    """Test adding multiple users when organization is set."""
    # Prerequisites
    e2e_deployment.ensure_server_running()

    # Set organization to safe org
    e2e_deployment.ensure_org_allowlisted(safe_org)

    # Clear users
    users = e2e_deployment.get_allowlisted_users()
    if users:
        e2e_deployment.cli.run_command(["jupyter-deploy", "users", "remove"] + users)

    # Add both users
    e2e_deployment.cli.run_command(["jupyter-deploy", "users", "add", logged_user, safe_user])

    # Verify list users includes both users
    users = e2e_deployment.get_allowlisted_users()
    assert set(users) == {logged_user, safe_user}, f"Expected exactly [{logged_user}, {safe_user}], got {users}"

    # Verify logged user can access the app
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Remove both users
    e2e_deployment.cli.run_command(["jupyter-deploy", "users", "remove", safe_user, logged_user])

    # Verify list users shows no allowlisted users
    users = e2e_deployment.get_allowlisted_users()
    assert set(users) == set(), f"Expected empty set, got {users}"

    # Verify logged user gets unauthorized page
    github_oauth_app.ensure_authenticated()
    verify_access_forbidden(github_oauth_app)
