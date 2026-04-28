from enum import Enum

from kubernetes import client

from jupyter_deploy.engine.supervised_execution import DisplayManager
from jupyter_deploy.exceptions import InstructionNotFoundError
from jupyter_deploy.provider.instruction_runner import InstructionRunner
from jupyter_deploy.provider.k8s.k8s_client_factory import K8sClientFactory
from jupyter_deploy.provider.k8s.k8s_core_runner import K8sCoreRunner
from jupyter_deploy.provider.k8s.k8s_custom_runner import K8sCustomRunner
from jupyter_deploy.provider.resolved_argdefs import ResolvedInstructionArgument
from jupyter_deploy.provider.resolved_resultdefs import ResolvedInstructionResult


class K8sService(str, Enum):
    """K8s services mapped to jupyter-deploy instructions."""

    CORE = "core"
    CUSTOM = "custom"


class K8sApiRunner(InstructionRunner):
    """Routes k8s.{service}.{instruction} to the appropriate sub-runner."""

    def __init__(self, display_manager: DisplayManager, kubeconfig_path: str | None = None) -> None:
        super().__init__(display_manager)
        self.kubeconfig_path = kubeconfig_path
        self._api_client: client.ApiClient | None = None
        self._service_runners: dict[str, InstructionRunner] = {}

    def _get_api_client(self) -> client.ApiClient:
        if self._api_client is None:
            self._api_client = K8sClientFactory.from_kubeconfig(kubeconfig_path=self.kubeconfig_path)
        return self._api_client

    @staticmethod
    def _get_service_and_sub_instruction_name(instruction_name: str) -> tuple[str, str]:
        parts = instruction_name.split(".")
        if len(parts) < 2 or not parts[0] or not parts[1]:
            raise ValueError(
                f"Invalid instruction: {instruction_name}; should be of the form service-name.instruction-name"
            )
        return parts[0], ".".join(parts[1:])

    def _get_service_runner(self, service_name: str) -> InstructionRunner:
        service_runner = self._service_runners.get(service_name)
        if service_runner:
            return service_runner

        api_client = self._get_api_client()

        if service_name == K8sService.CORE:
            service_runner = K8sCoreRunner(self.display_manager, api_client=api_client)
            self._service_runners[service_name] = service_runner
            return service_runner
        elif service_name == K8sService.CUSTOM:
            service_runner = K8sCustomRunner(self.display_manager, api_client=api_client)
            self._service_runners[service_name] = service_runner
            return service_runner

        raise InstructionNotFoundError(f"Unrecognized K8s service name: '{service_name}'")

    def execute_instruction(
        self,
        instruction_name: str,
        resolved_arguments: dict[str, ResolvedInstructionArgument],
    ) -> dict[str, ResolvedInstructionResult]:
        service_name, sub_instruction_name = K8sApiRunner._get_service_and_sub_instruction_name(instruction_name)
        service_runner = self._get_service_runner(service_name)
        return service_runner.execute_instruction(
            instruction_name=sub_instruction_name,
            resolved_arguments=resolved_arguments,
        )
