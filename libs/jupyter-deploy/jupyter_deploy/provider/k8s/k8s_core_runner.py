from enum import Enum

from kubernetes import client

from jupyter_deploy.api.k8s import core as k8s_core
from jupyter_deploy.engine.supervised_execution import DisplayManager
from jupyter_deploy.exceptions import InstructionNotFoundError
from jupyter_deploy.provider.instruction_runner import InstructionRunner
from jupyter_deploy.provider.resolved_argdefs import (
    ResolvedInstructionArgument,
    StrResolvedInstructionArgument,
    require_arg,
    retrieve_optional_arg,
)
from jupyter_deploy.provider.resolved_resultdefs import (
    ResolvedInstructionResult,
    StrResolvedInstructionResult,
)


class K8sCoreInstruction(str, Enum):
    """K8s Core API instructions accessible from manifest api-name."""

    LIST_NODES = "list-nodes"
    GET_NODE = "get-node"
    LIST_PODS = "list-pods"
    GET_POD = "get-pod"


class K8sCoreRunner(InstructionRunner):
    """Runner class for Kubernetes Core API instructions."""

    def __init__(self, display_manager: DisplayManager, api_client: client.ApiClient) -> None:
        super().__init__(display_manager)
        self.core_api = client.CoreV1Api(api_client)

    def _list_nodes(
        self, resolved_arguments: dict[str, ResolvedInstructionArgument]
    ) -> dict[str, ResolvedInstructionResult]:
        query_arg = retrieve_optional_arg(resolved_arguments, "query", StrResolvedInstructionArgument, "")
        page_size_arg = retrieve_optional_arg(resolved_arguments, "page_size", StrResolvedInstructionArgument, "")
        pagination_token_arg = retrieve_optional_arg(
            resolved_arguments, "pagination_token", StrResolvedInstructionArgument, ""
        )

        self.display_manager.info("Listing nodes")
        nodes, next_token = k8s_core.list_nodes(
            self.core_api,
            label_selector=query_arg.value or None,
            limit=int(page_size_arg.value) if page_size_arg.value else None,
            _continue=pagination_token_arg.value or None,
        )

        node_names = [node.name for node in nodes]
        return {
            "NodeNames": StrResolvedInstructionResult(result_name="NodeNames", value=",".join(node_names)),
            "NextToken": StrResolvedInstructionResult(result_name="NextToken", value=next_token or ""),
        }

    def _get_node(
        self, resolved_arguments: dict[str, ResolvedInstructionArgument]
    ) -> dict[str, ResolvedInstructionResult]:
        name_arg = require_arg(resolved_arguments, "name", StrResolvedInstructionArgument)

        self.display_manager.info(f"Getting node: {name_arg.value}")
        node = k8s_core.get_node(self.core_api, name=name_arg.value)

        return {
            "Name": StrResolvedInstructionResult(result_name="Name", value=node.name),
            "Status": StrResolvedInstructionResult(result_name="Status", value=node.status.value),
        }

    def _list_pods(
        self, resolved_arguments: dict[str, ResolvedInstructionArgument]
    ) -> dict[str, ResolvedInstructionResult]:
        scope_arg = require_arg(resolved_arguments, "scope", StrResolvedInstructionArgument)
        query_arg = retrieve_optional_arg(resolved_arguments, "query", StrResolvedInstructionArgument, "")
        page_size_arg = retrieve_optional_arg(resolved_arguments, "page_size", StrResolvedInstructionArgument, "")
        pagination_token_arg = retrieve_optional_arg(
            resolved_arguments, "pagination_token", StrResolvedInstructionArgument, ""
        )

        self.display_manager.info(f"Listing pods in namespace: {scope_arg.value}")
        pods, next_token = k8s_core.list_pods(
            self.core_api,
            namespace=scope_arg.value,
            label_selector=query_arg.value or None,
            limit=int(page_size_arg.value) if page_size_arg.value else None,
            _continue=pagination_token_arg.value or None,
        )

        pod_names = [pod.name for pod in pods]
        return {
            "PodNames": StrResolvedInstructionResult(result_name="PodNames", value=",".join(pod_names)),
            "NextToken": StrResolvedInstructionResult(result_name="NextToken", value=next_token or ""),
        }

    def _get_pod(
        self, resolved_arguments: dict[str, ResolvedInstructionArgument]
    ) -> dict[str, ResolvedInstructionResult]:
        name_arg = require_arg(resolved_arguments, "name", StrResolvedInstructionArgument)
        scope_arg = require_arg(resolved_arguments, "scope", StrResolvedInstructionArgument)

        self.display_manager.info(f"Getting pod: {name_arg.value}")
        pod = k8s_core.get_pod(self.core_api, name=name_arg.value, namespace=scope_arg.value)

        return {
            "Name": StrResolvedInstructionResult(result_name="Name", value=pod.name),
            "Phase": StrResolvedInstructionResult(result_name="Phase", value=pod.phase.value),
        }

    def execute_instruction(
        self,
        instruction_name: str,
        resolved_arguments: dict[str, ResolvedInstructionArgument],
    ) -> dict[str, ResolvedInstructionResult]:
        try:
            instruction = K8sCoreInstruction(instruction_name)
        except ValueError:
            raise InstructionNotFoundError(f"Unknown K8s core instruction: '{instruction_name}'") from None

        if instruction == K8sCoreInstruction.LIST_NODES:
            return self._list_nodes(resolved_arguments)
        elif instruction == K8sCoreInstruction.GET_NODE:
            return self._get_node(resolved_arguments)
        elif instruction == K8sCoreInstruction.LIST_PODS:
            return self._list_pods(resolved_arguments)
        elif instruction == K8sCoreInstruction.GET_POD:
            return self._get_pod(resolved_arguments)

        raise InstructionNotFoundError(f"Unknown K8s core instruction: '{instruction_name}'")
