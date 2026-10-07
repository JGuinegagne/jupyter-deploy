"""E2E tests for team-isolated workspace namespaces (workspace_namespaces, issue #343).

The module fixture applies one base mapping (see test_utils.base_values) before the
first case and restores the deployment's own values after the last. Cases run in a
pinned order right after test_workspace_single_to_multi_namespace; #409 runs last since
it changes the mapping itself. Only #409 relies on the bot's real membership of
JD_E2E_RBAC_TEAM. All workspaces are CPU-only.
"""

from collections.abc import Generator
from typing import Any

import pytest
from pytest_jupyter_deploy.deployment import EndToEndDeployment
from pytest_jupyter_deploy.kubernetes.kubectl import run_kubectl
from pytest_jupyter_deploy.kubernetes.namespace import temporary_namespace
from pytest_jupyter_deploy.kubernetes.rbac import impersonated_user_can
from pytest_jupyter_deploy.plugin import skip_if_testvars_not_set
from pytest_jupyter_deploy.workspaces.kubectl import (
    kubectl_delete_workspace,
    kubectl_get_workspace,
    kubectl_patch_workspace,
    kubectl_poll_workspace_status,
)
from pytest_jupyter_deploy.workspaces.network_probe import (
    probe_service_allowed,
    probe_workspace,
    workspace_service_host,
)
from pytest_jupyter_deploy.workspaces.web_app import WebAppNavigator

from .constants import ORDER_NAMESPACES
from .test_utils import (
    NAMESPACE_REQUIRED_VARS,
    NS_A,
    NS_B,
    RUNNING_TIMEOUT_S,
    SMALL_TEMPLATE,
    STOP_PATCH,
    apply_values,
    base_values,
    create_workspace,
    entry,
    group,
    jd_config_error,
    only_a,
    only_b,
    rbac_team,
    restored_mapping,
    team,
    template_names,
    user,
    wait_running,
)

pytestmark = [
    pytest.mark.usefixtures("kubernetes_cluster_login"),
    pytest.mark.mutating,
    pytest.mark.full_deployment,
]

ROUTER_NAMESPACE = "jupyter-k8s-router"
PROBE_NAMESPACE = "e2e-ns-probe"


@pytest.fixture(scope="module")
def mapped(e2e_deployment: EndToEndDeployment) -> Generator[dict[str, Any], None, None]:
    """Apply the base mapping once for the module; restore the deployment's values after the last case."""
    e2e_deployment.ensure_deployed()
    values = base_values(e2e_deployment)
    with restored_mapping(e2e_deployment):
        apply_values(e2e_deployment, values)
        yield values


@pytest.mark.order(ORDER_NAMESPACES + 1)
@skip_if_testvars_not_set(NAMESPACE_REQUIRED_VARS)
def test_team_mapped_to_one_namespace(mapped: dict[str, Any]) -> None:
    """A team mapped only to e2e-ns-a works there, is Forbidden in default, and cannot read e2e-ns-b."""
    mine, theirs = "e2e-ns-only-a-ws", "e2e-ns-only-b-ws"
    try:
        created = create_workspace(mine, NS_A, only_a())
        assert created.returncode == 0, f"only-a team cannot create in {NS_A}:\n{created.stderr}"
        wait_running(mine, NS_A)

        for verb in ("list", "create"):
            assert not impersonated_user_can(verb, "workspaces", "default", as_user=user(), as_groups=group(only_a()))

        created = create_workspace(theirs, NS_B, only_b())
        assert created.returncode == 0, f"only-b team cannot create in {NS_B}:\n{created.stderr}"
        read = kubectl_get_workspace(theirs, namespace=NS_B, as_user=user(), as_groups=group(only_a()))
        assert read.returncode != 0 and "forbidden" in read.stderr.lower(), (
            f"only-a team should not read a workspace in {NS_B}:\n{read.stdout}{read.stderr}"
        )
    finally:
        kubectl_delete_workspace(mine, namespace=NS_A)
        kubectl_delete_workspace(theirs, namespace=NS_B)


@pytest.mark.order(ORDER_NAMESPACES + 2)
@skip_if_testvars_not_set(NAMESPACE_REQUIRED_VARS)
def test_team_mapped_to_two_namespaces(mapped: dict[str, Any]) -> None:
    """A team mapped to both namespaces creates, lists and stops workspaces in each."""
    name = "e2e-ns-two"
    rbac = rbac_team()
    try:
        for ns in (NS_A, NS_B):
            created = create_workspace(name, ns, rbac)
            assert created.returncode == 0, f"cannot create in {ns}:\n{created.stderr}"
        for ns in (NS_A, NS_B):
            wait_running(name, ns)
            listed = run_kubectl("get", "workspaces", "-n", ns, "-o", "name", as_user=user(), as_groups=group(rbac))
            assert listed.returncode == 0 and name in listed.stdout, f"cannot list {name} in {ns}:\n{listed.stderr}"
            stopped = kubectl_patch_workspace(name, STOP_PATCH, namespace=ns, as_user=user(), as_groups=group(rbac))
            assert stopped.returncode == 0, f"cannot stop {name} in {ns}:\n{stopped.stderr}"
            kubectl_poll_workspace_status(name, "Stopped", namespace=ns, timeout_s=RUNNING_TIMEOUT_S)
    finally:
        for ns in (NS_A, NS_B):
            kubectl_delete_workspace(name, namespace=ns)


@pytest.mark.order(ORDER_NAMESPACES + 3)
@skip_if_testvars_not_set(NAMESPACE_REQUIRED_VARS)
def test_team_mapped_to_no_namespace(mapped: dict[str, Any]) -> None:
    """A team of an allowlisted org that no entry lists is Forbidden in every workspace namespace."""
    unmapped = group(team("e2e-ns-unmapped"))
    for ns in ("default", NS_A, NS_B):
        for verb in ("list", "create"):
            assert not impersonated_user_can(verb, "workspaces", ns, as_user=user(), as_groups=unmapped), (
                f"an unmapped team should not {verb} workspaces in {ns}"
            )


@pytest.mark.order(ORDER_NAMESPACES + 4)
@skip_if_testvars_not_set(NAMESPACE_REQUIRED_VARS)
def test_templates_offered_per_namespace(mapped: dict[str, Any]) -> None:
    """e2e-cpu-small is offered and runs in e2e-ns-a only; e2e-ns-b offers just jupyterlab."""
    name = "e2e-ns-small"
    rbac = rbac_team()
    try:
        assert template_names(NS_A, rbac) == {"jupyterlab", SMALL_TEMPLATE}
        assert template_names(NS_B, rbac) == {"jupyterlab"}

        created = create_workspace(name, NS_A, rbac, template=SMALL_TEMPLATE)
        assert created.returncode == 0, f"cannot create from {SMALL_TEMPLATE} in {NS_A}:\n{created.stderr}"
        wait_running(name, NS_A)

        rejected = create_workspace(name, NS_B, rbac, template=SMALL_TEMPLATE)
        assert rejected.returncode != 0 and "not found" in rejected.stderr, (
            f"{SMALL_TEMPLATE} should be rejected at admission in {NS_B}:\n{rejected.stdout}{rejected.stderr}"
        )
    finally:
        for ns in (NS_A, NS_B):
            kubectl_delete_workspace(name, namespace=ns)


@pytest.mark.order(ORDER_NAMESPACES + 5)
@skip_if_testvars_not_set(NAMESPACE_REQUIRED_VARS)
def test_network_policy_in_every_namespace(mapped: dict[str, Any]) -> None:
    """The router reaches workspaces in both namespaces on 8888; an unrelated namespace does not."""
    name = "e2e-ns-netpol"
    try:
        for ns in (NS_A, NS_B):
            created = create_workspace(name, ns, rbac_team())
            assert created.returncode == 0, f"cannot create in {ns}:\n{created.stderr}"
        for ns in (NS_A, NS_B):
            wait_running(name, ns)
            assert probe_service_allowed(workspace_service_host(name, ns), 8888, from_namespace=ROUTER_NAMESPACE), (
                f"router should reach the workspace in {ns}"
            )
        with temporary_namespace(PROBE_NAMESPACE):
            for ns in (NS_A, NS_B):
                assert not probe_workspace(name, from_namespace=PROBE_NAMESPACE, workspace_namespace=ns), (
                    f"an unrelated namespace should be denied the workspace in {ns}"
                )
    finally:
        for ns in (NS_A, NS_B):
            kubectl_delete_workspace(name, namespace=ns)


@pytest.mark.order(ORDER_NAMESPACES + 6)
@skip_if_testvars_not_set(NAMESPACE_REQUIRED_VARS)
def test_in_use_template_cannot_be_dropped(e2e_deployment: EndToEndDeployment, mapped: dict[str, Any]) -> None:
    """Dropping e2e-cpu-small from e2e-ns-a while a workspace uses it fails `jd config`, naming both."""
    name = "e2e-ns-guard"
    try:
        created = create_workspace(name, NS_A, rbac_team(), template=SMALL_TEMPLATE)
        assert created.returncode == 0, created.stderr
        wait_running(name, NS_A)

        dropped = [
            entry(e["name"], e["teams"].split(",")) if e["name"] == NS_A else e for e in mapped["workspace_namespaces"]
        ]
        e2e_deployment.update_override_value("workspace_namespaces", dropped)
        error = jd_config_error(e2e_deployment)
        assert f"{NS_A}/{SMALL_TEMPLATE} used by {NS_A}/{name}" in error, error
        assert SMALL_TEMPLATE in template_names(NS_A, rbac_team())
    finally:
        e2e_deployment.update_override_value("workspace_namespaces", mapped["workspace_namespaces"])
        kubectl_delete_workspace(name, namespace=NS_A)


@pytest.mark.order(ORDER_NAMESPACES + 7)
@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda m: [*m, m[1]], "workspace_namespaces names must be unique"),
        (
            lambda m: [*m[:2], {**m[2], "templates": "e2e-ns-no-such-config"}],
            f"{NS_B}/e2e-ns-no-such-config",
        ),
        (lambda m: [*m[:2], {**m[2], "teams": "e2e-ns-no-such-org:team"}], "e2e-ns-no-such-org"),
        (lambda m: [*m[:2], {"name": NS_B, "teams": ""}], "must list at least one team"),
    ],
    ids=["duplicate-name", "unknown-template", "unknown-org", "no-team"],
)
@skip_if_testvars_not_set(NAMESPACE_REQUIRED_VARS)
def test_plan_time_validation(
    e2e_deployment: EndToEndDeployment, mapped: dict[str, Any], mutate: Any, message: str
) -> None:
    """`jd config` refuses an invalid mapping at plan, naming the culprit."""
    try:
        e2e_deployment.update_override_value("workspace_namespaces", mutate(mapped["workspace_namespaces"]))
        assert message in jd_config_error(e2e_deployment)
    finally:
        e2e_deployment.update_override_value("workspace_namespaces", mapped["workspace_namespaces"])


@pytest.fixture
def fresh_dex(e2e_deployment: EndToEndDeployment) -> None:
    """Restart dex so it serves the applied allowlist; requested before the browser login.

    Remove once the pinned router chart rolls dex on config changes:
    https://github.com/jupyter-infra/jupyter-k8s-aws/issues/100
    """
    e2e_deployment.cli.run_command(["jupyter-deploy", "component", "restart", "--name", "dex"])
    run_kubectl("rollout", "status", "deployment/dex", "-n", ROUTER_NAMESPACE, "--timeout=300s", check=True)


@pytest.mark.order(ORDER_NAMESPACES + 8)
@skip_if_testvars_not_set(NAMESPACE_REQUIRED_VARS)
def test_web_app_follows_mapping_change(
    e2e_deployment: EndToEndDeployment,
    mapped: dict[str, Any],
    fresh_dex: None,
    dex_oauth_web_app: WebAppNavigator,
) -> None:
    """#409: after `jd up` moves the bot's team from e2e-ns-a to e2e-ns-b, a reload resolves e2e-ns-b alone.

    Each mapping lists the namespace the bot may use first, which makes it the web app's
    default; `default` stays listed (to a team the bot is not in) so live workspaces keep
    their templates. Runs last: the module teardown restores the deployment's values.
    """
    rbac, other = rbac_team(), team("e2e-ns-only-default")
    navigator = dex_oauth_web_app

    def visible() -> tuple[str, list[str]]:
        # The page load drives the same calls; the refreshed scan comes first because the
        # active namespace falls back to the default only once a fresh scan denies it.
        navigator.goto_workspace_list()
        listed = navigator.page.request.get(f"{navigator.base_url}/api/v1/namespaces?refresh=1").json()
        active = navigator.page.request.get(f"{navigator.base_url}/api/v1/my-namespace").json()["active"]
        return active, [item["namespace"] for item in listed["items"]]

    apply_values(
        e2e_deployment,
        {
            "workspace_namespaces": [
                entry(NS_A, [rbac], [SMALL_TEMPLATE]),
                entry(NS_B, [only_b()]),
                entry("default", [other]),
            ]
        },
    )
    assert visible() == (NS_A, [NS_A])

    apply_values(
        e2e_deployment,
        {
            "workspace_namespaces": [
                entry(NS_B, [rbac]),
                entry(NS_A, [only_a()], [SMALL_TEMPLATE]),
                entry("default", [other]),
            ]
        },
    )
    navigator.page.reload()
    assert visible() == (NS_B, [NS_B])
