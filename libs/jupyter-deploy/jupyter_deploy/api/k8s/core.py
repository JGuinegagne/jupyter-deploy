from dataclasses import dataclass
from enum import Enum

from kubernetes.client import CoreV1Api


class NodeConditionStatus(str, Enum):
    READY = "Ready"
    NOT_READY = "NotReady"
    UNKNOWN = "Unknown"


class PodPhase(str, Enum):
    RUNNING = "Running"
    PENDING = "Pending"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    UNKNOWN = "Unknown"


@dataclass(frozen=True)
class NodeInfo:
    name: str
    status: NodeConditionStatus


@dataclass(frozen=True)
class PodInfo:
    name: str
    phase: PodPhase


def _parse_node_status(node: object) -> NodeConditionStatus:
    status = getattr(node, "status", None)
    conditions = getattr(status, "conditions", None) if status else None
    if conditions:
        for condition in conditions:
            if condition.type == "Ready":
                return NodeConditionStatus.READY if condition.status == "True" else NodeConditionStatus.NOT_READY
    return NodeConditionStatus.UNKNOWN


def _parse_pod_phase(pod: object) -> PodPhase:
    status = getattr(pod, "status", None)
    phase = getattr(status, "phase", None) if status else None
    try:
        return PodPhase(phase) if phase else PodPhase.UNKNOWN
    except ValueError:
        return PodPhase.UNKNOWN


def list_nodes(
    api: CoreV1Api,
    label_selector: str | None = None,
    limit: int | None = None,
    _continue: str | None = None,
) -> tuple[list[NodeInfo], str | None]:
    kwargs: dict[str, str | int] = {}
    if label_selector:
        kwargs["label_selector"] = label_selector
    if limit:
        kwargs["limit"] = limit
    if _continue:
        kwargs["_continue"] = _continue

    node_list = api.list_node(**kwargs)

    nodes = []
    for node in node_list.items:
        name = node.metadata.name if node.metadata else ""
        nodes.append(NodeInfo(name=name, status=_parse_node_status(node)))

    next_token = node_list.metadata._continue if node_list.metadata else None
    return nodes, next_token or None


def get_node(api: CoreV1Api, name: str) -> NodeInfo:
    node = api.read_node(name=name)
    node_name = node.metadata.name if node.metadata else ""
    return NodeInfo(name=node_name, status=_parse_node_status(node))


def list_pods(
    api: CoreV1Api,
    namespace: str,
    label_selector: str | None = None,
    limit: int | None = None,
    _continue: str | None = None,
) -> tuple[list[PodInfo], str | None]:
    kwargs: dict[str, str | int] = {"namespace": namespace}
    if label_selector:
        kwargs["label_selector"] = label_selector
    if limit:
        kwargs["limit"] = limit
    if _continue:
        kwargs["_continue"] = _continue

    pod_list = api.list_namespaced_pod(**kwargs)

    pods = []
    for pod in pod_list.items:
        name = pod.metadata.name if pod.metadata else ""
        pods.append(PodInfo(name=name, phase=_parse_pod_phase(pod)))

    next_token = pod_list.metadata._continue if pod_list.metadata else None
    return pods, next_token or None


def get_pod(api: CoreV1Api, name: str, namespace: str) -> PodInfo:
    pod = api.read_namespaced_pod(name=name, namespace=namespace)
    pod_name = pod.metadata.name if pod.metadata else ""
    return PodInfo(name=pod_name, phase=_parse_pod_phase(pod))
