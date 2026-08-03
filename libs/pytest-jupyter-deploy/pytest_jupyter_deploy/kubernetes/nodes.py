"""Node inspection helpers for E2E tests (counting, allocatable CPU, pod placement).

Template-agnostic: callers pass the node label selector that identifies the pool they
care about (e.g. jupyter-deploy/role=platform, inference/role=system), so these work
for any template's node grouping.
"""

import json
import subprocess

from pytest_jupyter_deploy.kubernetes.kubectl import run_kubectl


def get_node_names(label_selector: str) -> list[str]:
    """Names of Ready nodes matching a label selector (e.g. 'jupyter-deploy/role=platform')."""
    result = subprocess.run(
        ["kubectl", "get", "nodes", "-l", label_selector, "-o", "jsonpath={.items[*].metadata.name}"],
        capture_output=True,
        text=True,
        check=False,
    )
    out = result.stdout.strip()
    return out.split() if out else []


def get_tainted_node_names(label_selector: str, taint_key: str) -> list[str]:
    """Names of nodes matching label_selector that carry a taint with the given key.

    Reads taints as JSON and filters in Python — kubectl jsonpath cannot express a
    filter over an array field (`[?(@.spec.taints[*].key==...)]` is unsupported).
    """
    result = run_kubectl("get", "nodes", "-l", label_selector, "-o", "json", check=True)
    items = json.loads(result.stdout).get("items", [])
    return [
        item["metadata"]["name"]
        for item in items
        if any(taint.get("key") == taint_key for taint in item.get("spec", {}).get("taints", []))
    ]


def get_pod_node_names(namespace: str, label_selector: str) -> list[str]:
    """Names of the nodes hosting the pods matching a label selector in a namespace."""
    result = run_kubectl(
        "get", "pods", "-n", namespace, "-l", label_selector, "-o", "jsonpath={.items[*].spec.nodeName}", check=True
    )
    out = result.stdout.strip()
    return out.split() if out else []


def assert_pods_on_node_pool(namespace: str, label_selector: str, node_label: str, description: str) -> None:
    """Assert every pod matching label_selector lands on a node carrying node_label.

    node_label is the JSON label fragment as it appears in a node's `.metadata.labels`.
    Fails if no matching pods are found, so a typo'd selector cannot make the check vacuously pass.
    """
    node_names = get_pod_node_names(namespace, label_selector)
    assert node_names, f"no pods found for {description} in namespace '{namespace}'"
    for node in set(node_names):
        labels = run_kubectl("get", "node", node, "-o", "jsonpath={.metadata.labels}", check=True).stdout.strip()
        assert node_label in labels, (
            f"{description} is on node '{node}', which lacks label {node_label} (labels: {labels[:200]})"
        )


def parse_cpu_to_millicores(quantity: str) -> int:
    """Parse a Kubernetes CPU quantity ('2', '1930m') to integer millicores."""
    quantity = quantity.strip()
    if quantity.endswith("m"):
        return int(quantity[:-1])
    return int(float(quantity) * 1000)


def get_node_allocatable_cpu_millicores(node_name: str) -> int:
    """Allocatable CPU (millicores) of a node — the per-node sizing unit for ballast tests.

    Deriving ballast CPU requests from this keeps a scale-up test independent of the node's
    instance type: a hardcoded request would either never trigger scale-up on a large SKU
    or over-trigger on a small one.
    """
    result = subprocess.run(
        ["kubectl", "get", "node", node_name, "-o", "jsonpath={.status.allocatable.cpu}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return parse_cpu_to_millicores(result.stdout.strip())
