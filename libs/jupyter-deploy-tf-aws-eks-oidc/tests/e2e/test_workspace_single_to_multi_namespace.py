"""E2E test for switching a live single-namespace deployment to workspace_namespaces (#343).

Starts from the empty mapping, so it runs just before test_workspace_namespaces, which
applies its own mapping for all its cases. Restores the deployment's values on exit.
"""

import pytest
from pytest_jupyter_deploy.deployment import EndToEndDeployment
from pytest_jupyter_deploy.plugin import skip_if_testvars_not_set
from pytest_jupyter_deploy.workspaces.kubectl import (
    kubectl_delete_workspace,
    kubectl_patch_workspace,
    kubectl_poll_workspace_status,
)

from .constants import ORDER_NAMESPACES
from .test_utils import (
    NAMESPACE_REQUIRED_VARS,
    RUNNING_TIMEOUT_S,
    START_PATCH,
    STOP_PATCH,
    apply_values,
    base_values,
    create_workspace,
    restored_mapping,
    wait_running,
)

pytestmark = [
    pytest.mark.usefixtures("kubernetes_cluster_login"),
    pytest.mark.mutating,
    pytest.mark.full_deployment,
]


@pytest.mark.order(ORDER_NAMESPACES)
@skip_if_testvars_not_set(NAMESPACE_REQUIRED_VARS)
def test_single_to_multi_namespace_keeps_live_workspace(e2e_deployment: EndToEndDeployment) -> None:
    """A workspace created with the mapping empty survives the switch to [default, ...] and still stops and starts."""
    e2e_deployment.ensure_deployed()
    name = "e2e-ns-single-to-multi"
    multi = base_values(e2e_deployment)
    with restored_mapping(e2e_deployment):
        try:
            if e2e_deployment.read_override_value("workspace_namespaces"):
                apply_values(e2e_deployment, {"workspace_namespaces": []})
            created = create_workspace(name, "default", team_name=None)
            assert created.returncode == 0, created.stderr
            wait_running(name, "default")

            apply_values(e2e_deployment, multi)

            wait_running(name, "default")
            for patch, status in ((STOP_PATCH, "Stopped"), (START_PATCH, "Running")):
                patched = kubectl_patch_workspace(name, patch, namespace="default")
                assert patched.returncode == 0, f"patch to {status} rejected after the switch:\n{patched.stderr}"
                kubectl_poll_workspace_status(name, status, namespace="default", timeout_s=RUNNING_TIMEOUT_S)
        finally:
            kubectl_delete_workspace(name, namespace="default")
