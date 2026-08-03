"""Helpers to tune a jupyter-k8s WorkspaceTemplate at test time.

The template's idle-timeout floor (`spec.idleShutdownOverrides.minIdleTimeoutInMinutes`)
is an infrastructure-as-code-managed value: it renders from a deploy-time variable
into the WorkspaceTemplate CR, and the operator's validating webhook rejects any
Workspace whose idle timeout falls below it.

Tests that need a very short idle timeout (to observe idle shutdown quickly) lower
this floor on the live template and restore it on teardown, rather than depending on
the deployment having been created with a low floor. This mirrors the
`operator.py` approach for the poll interval: mutate the live resource for the test,
revert after — so the test is self-contained and runs against any existing deployment.
"""

import json

from pytest_jupyter_deploy.kubernetes.kubectl import run_kubectl

_MIN_IDLE_TIMEOUT_PATH = "spec.idleShutdownOverrides.minIdleTimeoutInMinutes"


def get_min_idle_timeout(template: str, namespace: str) -> int:
    """Return the template's current idleShutdownOverrides.minIdleTimeoutInMinutes."""
    result = run_kubectl(
        "get",
        "workspacetemplate",
        template,
        "-n",
        namespace,
        "-o",
        "jsonpath={.spec.idleShutdownOverrides.minIdleTimeoutInMinutes}",
        check=True,
    )
    raw = result.stdout.strip()
    if not raw:
        raise ValueError(f"WorkspaceTemplate '{template}' in '{namespace}' has no {_MIN_IDLE_TIMEOUT_PATH}")
    return int(raw)


def set_min_idle_timeout(template: str, namespace: str, minutes: int) -> None:
    """Patch the template's idleShutdownOverrides.minIdleTimeoutInMinutes."""
    patch = json.dumps({"spec": {"idleShutdownOverrides": {"minIdleTimeoutInMinutes": minutes}}})
    run_kubectl(
        "patch",
        "workspacetemplate",
        template,
        "-n",
        namespace,
        "--type=merge",
        "-p",
        patch,
        check=True,
    )
