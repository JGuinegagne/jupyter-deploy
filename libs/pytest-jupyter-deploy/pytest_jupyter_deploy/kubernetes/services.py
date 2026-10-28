"""Service inspection helpers for E2E tests."""

from pytest_jupyter_deploy.kubernetes.kubectl import run_kubectl


def get_service_port(name: str, namespace: str) -> int:
    """The single port a Service exposes; raises ValueError if it exposes none or several."""
    result = run_kubectl("get", "service", name, "-n", namespace, "-o", "jsonpath={.spec.ports[*].port}", check=True)
    ports = result.stdout.split()
    if len(ports) != 1:
        raise ValueError(f"expected exactly one port on Service '{namespace}/{name}', got {ports}")
    return int(ports[0])
