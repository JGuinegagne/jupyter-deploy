"""Helpers shared by the workspace-namespace e2e modules (workspace_namespaces, issue #343).

RBAC cases impersonate `github:<org>:<team>` groups, so the synthetic teams need not
exist on GitHub: their org is the allowlisted JD_E2E_ORG.
"""

import ast
import os
import re
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import pytest
from pytest_jupyter_deploy.cli import JDCliError
from pytest_jupyter_deploy.deployment import EndToEndDeployment
from pytest_jupyter_deploy.kubernetes.kubectl import run_kubectl
from pytest_jupyter_deploy.workspaces.kubectl import kubectl_poll_workspace_status

NS_A = "e2e-ns-a"
NS_B = "e2e-ns-b"
SMALL_TEMPLATE = "e2e-cpu-small"
SMALL_TEMPLATE_CONFIG = {"name": SMALL_TEMPLATE, "cpu": "1", "memory": "2Gi", "display_name": "E2E CPU Small"}
MAPPED_VARIABLES = ["workspace_namespaces", "workspace_templates", "workspace_nodepools"]
NAMESPACE_REQUIRED_VARS = ["JD_E2E_USER", "JD_E2E_ORG", "JD_E2E_RBAC_TEAM"]
RUNNING_TIMEOUT_S = 600
STOP_PATCH = '{"spec":{"desiredStatus":"Stopped"}}'
START_PATCH = '{"spec":{"desiredStatus":"Running"}}'


# ── Identities ────────────────────────────────────────────────────────────────


def user() -> str:
    return f"github:{os.environ['JD_E2E_USER']}"


def team(name: str) -> str:
    return f"{os.environ['JD_E2E_ORG']}:{name}"


def rbac_team() -> str:
    return team(os.environ["JD_E2E_RBAC_TEAM"])


def only_a() -> str:
    return team("e2e-ns-only-a")


def only_b() -> str:
    return team("e2e-ns-only-b")


def group(team_name: str) -> list[str]:
    return [f"github:{team_name}"]


# ── Mapping ───────────────────────────────────────────────────────────────────


def entry(name: str, teams: list[str], templates: list[str] | None = None) -> dict[str, str]:
    """One workspace_namespaces entry."""
    out = {"name": name, "teams": ",".join(dict.fromkeys(teams))}
    if templates:
        out["templates"] = ",".join(templates)
    return out


def _show_list_of_maps(e2e_deployment: EndToEndDeployment, variable: str) -> list[dict[str, str]]:
    result = e2e_deployment.cli.run_command(["jupyter-deploy", "show", "--variable", variable, "--text"])
    value = ast.literal_eval(result.stdout.strip())
    assert isinstance(value, list), f"expected a list for {variable}, got {result.stdout!r}"
    return [dict(v) for v in value]


def _with_small_template(pools: list[dict[str, str]]) -> list[dict[str, str]]:
    """Offer the small config from the first CPU pool: a config renders only where a pool offers it."""
    out = [dict(p) for p in pools]
    cpu_pool = next(p for p in out if not p.get("accelerator"))
    offered = [t for t in cpu_pool.get("templates", "").split(",") if t]
    if SMALL_TEMPLATE not in offered:
        offered.append(SMALL_TEMPLATE)
    cpu_pool["templates"] = ",".join(offered)
    return out


def _offered_templates(e2e_deployment: EndToEndDeployment, pools: list[dict[str, str]]) -> list[str]:
    """The configs the pools offer, including the built-in GPU card enable_default_gpu_pool injects."""
    offered = [t for p in pools for t in p.get("templates", "").split(",") if t]
    gpu_flag = e2e_deployment.cli.run_command(
        ["jupyter-deploy", "show", "--variable", "enable_default_gpu_pool", "--text"]
    ).stdout.strip()
    if gpu_flag.lower() == "true":
        offered.append("jupyterlab-gpu")
    return list(dict.fromkeys(offered))


def base_values(e2e_deployment: EndToEndDeployment) -> dict[str, Any]:
    """The base mapping both modules apply.

    - default:  every team in oauth_allowed_teams, keeping the cards the empty mapping
                gives it, so its live workspaces keep their templates
    - e2e-ns-a: JD_E2E_RBAC_TEAM + a synthetic "only-a" team, also offering e2e-cpu-small
    - e2e-ns-b: JD_E2E_RBAC_TEAM + a synthetic "only-b" team
    """
    templates = [t for t in _show_list_of_maps(e2e_deployment, "workspace_templates") if t["name"] != SMALL_TEMPLATE]
    pools = _show_list_of_maps(e2e_deployment, "workspace_nodepools")
    allowed_teams = e2e_deployment.get_list_str_variable_value("oauth_allowed_teams")
    return {
        "workspace_templates": [*templates, SMALL_TEMPLATE_CONFIG],
        "workspace_nodepools": _with_small_template(pools),
        "workspace_namespaces": [
            entry("default", allowed_teams, _offered_templates(e2e_deployment, pools)),
            entry(NS_A, [rbac_team(), only_a()], [SMALL_TEMPLATE]),
            entry(NS_B, [rbac_team(), only_b()]),
        ],
    }


def apply_values(e2e_deployment: EndToEndDeployment, values: dict[str, Any]) -> None:
    """Write the overrides, then `jd config` + `jd up`."""
    for key, value in values.items():
        e2e_deployment.update_override_value(key, value)
    e2e_deployment.ensure_deployed_with([])


@contextmanager
def restored_mapping(e2e_deployment: EndToEndDeployment) -> Generator[None, None, None]:
    """Snapshot the mapping variables; on exit restore them and redeploy."""
    snapshot = {key: e2e_deployment.read_override_value(key) for key in MAPPED_VARIABLES}
    try:
        yield
    finally:
        reset_args: list[str] = []
        for key, value in snapshot.items():
            if value is None:
                reset_args += ["--reset-variable", key]
            else:
                e2e_deployment.update_override_value(key, value)
        e2e_deployment.ensure_deployed_with(reset_args)


def jd_config_error(e2e_deployment: EndToEndDeployment) -> str:
    """Run `jd config`, which must fail at plan; return its output with box-drawing and wrapping removed."""
    with pytest.raises(JDCliError) as exc_info:
        e2e_deployment.cli.run_command(["jupyter-deploy", "config"])
    text = re.sub(r"\x1b\[[0-9;]*m", "", str(exc_info.value))
    return " ".join(text.replace("│", " ").split())


# ── Workspaces ────────────────────────────────────────────────────────────────


def _workspace_manifest(name: str, namespace: str, template: str | None) -> str:
    template_ref = f"  templateRef:\n    name: {template}\n" if template else ""
    return (
        "apiVersion: workspace.jupyter.org/v1alpha1\n"
        "kind: Workspace\n"
        f"metadata:\n  name: {name}\n  namespace: {namespace}\n"
        "spec:\n"
        f'  displayName: "{name}"\n'
        "  desiredStatus: Running\n"
        "  ownershipType: Public\n"
        "  accessType: Public\n" + template_ref
    )


def create_workspace(
    name: str, namespace: str, team_name: str | None, template: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Create a workspace, impersonating the team's group (or as the admin when team_name is None)."""
    cmd = ["kubectl", "create", "-f", "-"]
    if team_name:
        cmd += ["--as", user(), *[arg for g in group(team_name) for arg in ("--as-group", g)]]
    return subprocess.run(
        cmd, input=_workspace_manifest(name, namespace, template), capture_output=True, text=True, check=False
    )


def wait_running(name: str, namespace: str) -> None:
    kubectl_poll_workspace_status(name, "Running", namespace=namespace, timeout_s=RUNNING_TIMEOUT_S)


def template_names(namespace: str, team_name: str) -> set[str]:
    result = run_kubectl(
        "get",
        "workspacetemplates",
        "-n",
        namespace,
        "-o",
        "jsonpath={.items[*].metadata.name}",
        as_user=user(),
        as_groups=group(team_name),
        check=True,
    )
    return set(result.stdout.split())
