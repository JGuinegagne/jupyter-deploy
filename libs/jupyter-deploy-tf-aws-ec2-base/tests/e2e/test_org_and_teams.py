"""E2E tests for organization and team-level access control."""

from pytest_jupyter_deploy.deployment import EndToEndDeployment
from pytest_jupyter_deploy.oauth2_proxy.github import GitHubOAuth2ProxyApplication
from pytest_jupyter_deploy.plugin import skip_if_testvars_not_set

from .test_utils import verify_access_forbidden


@skip_if_testvars_not_set(["JD_E2E_ORG"])
def test_org_based_admit_positive(
    e2e_deployment: EndToEndDeployment, github_oauth_app: GitHubOAuth2ProxyApplication, logged_org: str
) -> None:
    """Test that setting org to logged user's org allows access."""
    # Prerequisites
    e2e_deployment.ensure_server_running()

    # Set organization to logged user's org
    e2e_deployment.cli.run_command(["jupyter-deploy", "organization", "set", logged_org])

    # Clear users
    e2e_deployment.ensure_no_users_allowlisted()

    # Clear teams
    e2e_deployment.ensure_no_teams_allowlisted()

    # Verify list org is correct
    org = e2e_deployment.get_allowlisted_org()
    assert org == logged_org, f"Expected exactly [{logged_org}], got {org}"

    # Verify logged user can access the app
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()


@skip_if_testvars_not_set(["JD_E2E_SAFE_ORG"])
def test_org_based_admit_negative(
    e2e_deployment: EndToEndDeployment, github_oauth_app: GitHubOAuth2ProxyApplication, safe_org: str
) -> None:
    """Test that setting org to safe org denies access to logged user."""
    # Prerequisites
    e2e_deployment.ensure_server_running()

    # Set organization to safe org
    e2e_deployment.cli.run_command(["jupyter-deploy", "organization", "set", safe_org])

    # Clear users
    e2e_deployment.ensure_no_users_allowlisted()

    # Clear teams
    e2e_deployment.ensure_no_teams_allowlisted()

    # Verify list org is correct
    org = e2e_deployment.get_allowlisted_org()
    assert org == safe_org, f"Expected exactly [{safe_org}], got {org}"

    # Verify logged user gets unauthorized page
    github_oauth_app.ensure_authenticated()
    verify_access_forbidden(github_oauth_app)


@skip_if_testvars_not_set(["JD_E2E_ORG", "JD_E2E_TEAM"])
def test_team_based_admit_positive(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    logged_org: str,
    logged_team: str,
) -> None:
    """Test that setting org and team to logged user's org and team allows access."""
    # Prerequisites
    e2e_deployment.ensure_server_running()

    # Set organization to logged user's org
    e2e_deployment.cli.run_command(["jupyter-deploy", "organization", "set", logged_org])

    # Clear users
    e2e_deployment.ensure_no_users_allowlisted()

    # Clear teams
    e2e_deployment.ensure_no_teams_allowlisted()

    # Add logged user's team
    e2e_deployment.cli.run_command(["jupyter-deploy", "teams", "add", logged_team])

    # Verify list teams includes logged team
    teams = e2e_deployment.get_allowlisted_teams()
    assert set(teams) == {logged_team}, f"Expected exactly [{logged_team}], got {teams}"

    # Verify logged user can access the app
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()


@skip_if_testvars_not_set(["JD_E2E_ORG", "JD_E2E_SAFE_TEAM"])
def test_team_based_admit_negative(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    logged_org: str,
    safe_team: str,
) -> None:
    """Test that setting org to logged org but team to safe team denies access."""
    # Prerequisites
    e2e_deployment.ensure_server_running()

    # Set organization to logged user's org
    e2e_deployment.cli.run_command(["jupyter-deploy", "organization", "set", logged_org])

    # Clear users
    e2e_deployment.ensure_no_users_allowlisted()

    # Clear teams
    e2e_deployment.ensure_no_teams_allowlisted()

    # Set safe team
    e2e_deployment.cli.run_command(["jupyter-deploy", "teams", "set", safe_team])

    # Verify list teams includes safe team
    teams = e2e_deployment.get_allowlisted_teams()
    assert set(teams) == {safe_team}, f"Expected exactly [{safe_team}], got {teams}"

    # Verify logged user gets unauthorized page
    github_oauth_app.ensure_authenticated()
    verify_access_forbidden(github_oauth_app)


@skip_if_testvars_not_set(["JD_E2E_SAFE_ORG", "JD_E2E_TEAM"])
def test_diff_org_team_admit_negative(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    safe_org: str,
    logged_team: str,
) -> None:
    """Test that setting org to safe org and team to logged team denies access."""
    # Prerequisites
    e2e_deployment.ensure_server_running()

    # Set organization to safe org
    e2e_deployment.cli.run_command(["jupyter-deploy", "organization", "set", safe_org])

    # Clear users
    e2e_deployment.ensure_no_users_allowlisted()

    # Clear teams
    e2e_deployment.ensure_no_teams_allowlisted()

    # Add logged user's team
    e2e_deployment.cli.run_command(["jupyter-deploy", "teams", "set", logged_team])

    # Verify list teams includes logged team
    teams = e2e_deployment.get_allowlisted_teams()
    assert set(teams) == {logged_team}, f"Expected exactly [{logged_team}], got {teams}"

    # Verify logged user gets unauthorized page
    github_oauth_app.ensure_authenticated()
    verify_access_forbidden(github_oauth_app)


@skip_if_testvars_not_set(["JD_E2E_ORG", "JD_E2E_TEAM"])
def test_add_and_remove_multiple_teams(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    logged_org: str,
    logged_team: str,
) -> None:
    """Test adding and removing multiple teams in a single command."""
    # Prerequisites
    e2e_deployment.ensure_server_running()

    # Set allowlisted org
    e2e_deployment.cli.run_command(["jupyter-deploy", "organization", "set", logged_org])

    # Clear users
    e2e_deployment.ensure_no_users_allowlisted()

    # Clear org and teams
    e2e_deployment.ensure_no_teams_allowlisted()

    # Add logged team
    e2e_deployment.cli.run_command(["jupyter-deploy", "teams", "add", logged_team])

    # Verify list teams includes logged team
    teams = e2e_deployment.get_allowlisted_teams()
    assert set(teams) == {logged_team}, f"Expected exactly [{logged_team}], got {teams}"

    # Verify logged user can access the app
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Remove logged team
    e2e_deployment.cli.run_command(["jupyter-deploy", "teams", "remove", logged_team])

    # Verify list teams shows no allowlisted teams
    teams = e2e_deployment.get_allowlisted_teams()
    assert set(teams) == set(), f"Expected empty set, got {teams}"

    # Verify logged user can still access (based on org membership)
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()


@skip_if_testvars_not_set(["JD_E2E_ORG", "JD_E2E_SAFE_USER"])
def test_unset_org_admit_negative(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    logged_org: str,
    safe_user: str,
) -> None:
    """Test unsetting the organization."""
    # Prerequisites
    e2e_deployment.ensure_server_running()

    # Set organization to logged user's org
    e2e_deployment.cli.run_command(["jupyter-deploy", "organization", "set", logged_org])

    # Ensure no users allowlisted
    e2e_deployment.ensure_no_users_allowlisted()

    # Clear teams
    e2e_deployment.ensure_no_teams_allowlisted()

    # Verify org is set
    org = e2e_deployment.get_allowlisted_org()
    assert org == logged_org, f"Expected org to be {logged_org}, got {org}"

    # Add a safe user so we can unset the org (safety check requires at least one user or org)
    e2e_deployment.cli.run_command(["jupyter-deploy", "users", "add", safe_user])

    # Unset organization
    e2e_deployment.cli.run_command(["jupyter-deploy", "organization", "unset"])

    # Verify org is unset
    org = e2e_deployment.get_allowlisted_org()
    assert org is None, f"Expected org to be None after unset, got {org}"

    # Verify logged user gets unauthorized page (no longer admitted via org membership)
    github_oauth_app.ensure_authenticated()
    verify_access_forbidden(github_oauth_app)


@skip_if_testvars_not_set(["JD_E2E_SAFE_USER"])
def test_disallow_to_unset_org_when_no_user_allowlisted(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    logged_org: str,
) -> None:
    """Test that the organization unset command requires at least one user allowlisted."""
    # Prerequisites
    e2e_deployment.ensure_server_running()

    # Set organization to logged user's org
    e2e_deployment.cli.run_command(["jupyter-deploy", "organization", "set", logged_org])

    # Clear all users
    e2e_deployment.ensure_no_users_allowlisted()

    # Attempt to unset the organization
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "organization", "unset"])
    assert "At least one user or an organization must remain specified." in result.stdout

    # Verify get organization still shows logged org
    allowlisted_org = e2e_deployment.get_allowlisted_org()
    assert allowlisted_org == logged_org, f"expected org to be {logged_org}, got {allowlisted_org}"

    # Verify logged user can still access the app (via org membership)
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()


@skip_if_testvars_not_set(["JD_E2E_ORG", "JD_E2E_SAFE_TEAM"])
def test_add_team_when_there_was_none_restricts_access(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    logged_org: str,
    safe_team: str,
) -> None:
    """Test that allowlisting whole org, then allowlisting only a team scopes down the auth."""
    # Prerequisites
    e2e_deployment.ensure_server_running()

    # Set organization to logged user's org
    e2e_deployment.cli.run_command(["jupyter-deploy", "organization", "set", logged_org])

    # Clear users
    e2e_deployment.ensure_no_users_allowlisted()

    # Clear teams
    e2e_deployment.ensure_no_teams_allowlisted()

    # Verify logged user can access the app
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Allowlist only a team the logged user is not a member of
    e2e_deployment.cli.run_command(["jupyter-deploy", "teams", "add", safe_team])

    # Verify logged user gets unauthorized page (org membership not sufficient)
    github_oauth_app.ensure_authenticated()
    verify_access_forbidden(github_oauth_app)


@skip_if_testvars_not_set(["JD_E2E_ORG", "JD_E2E_TEAM", "JD_E2E_USER"])
def test_org_team_and_user_match_all_grant_access(
    e2e_deployment: EndToEndDeployment,
    github_oauth_app: GitHubOAuth2ProxyApplication,
    logged_org: str,
    logged_team: str,
    logged_user: str,
) -> None:
    """Test that org, org+team and user based auth work together."""

    # Prerequisites
    e2e_deployment.ensure_server_running()

    # Set organization to logged user's org
    e2e_deployment.cli.run_command(["jupyter-deploy", "organization", "set", logged_org])

    # Set team to logged user's team within the org
    e2e_deployment.cli.run_command(["jupyter-deploy", "teams", "set", logged_team])

    # Set user to logged users' username
    e2e_deployment.cli.run_command(["jupyter-deploy", "users", "set", logged_user])

    # Verify logged user can access the app (via user OR org+team)
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Remove user explicit allowlist
    e2e_deployment.cli.run_command(["jupyter-deploy", "users", "remove", logged_user])

    # Verify logged user can still access the app (via org+team)
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Remove team allowlist
    e2e_deployment.cli.run_command(["jupyter-deploy", "teams", "remove", logged_team])

    # Verify logged user can still access the app (via org)
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()

    # Add back the user explicit allowlist
    e2e_deployment.cli.run_command(["jupyter-deploy", "users", "add", logged_user])

    # Unset the organization
    e2e_deployment.cli.run_command(["jupyter-deploy", "organization", "unset"])

    # Verify logged user can still access the app (via user)
    github_oauth_app.ensure_authenticated()
    github_oauth_app.verify_jupyterlab_accessible()
