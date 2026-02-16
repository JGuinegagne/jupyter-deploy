from abc import ABC, abstractmethod

from jupyter_deploy.engine.supervised_execution import TerminalHandler
from jupyter_deploy.provider.resolved_argdefs import ResolvedInstructionArgument
from jupyter_deploy.provider.resolved_resultdefs import ResolvedInstructionResult


class InstructionRunner(ABC):
    """Abstract class to call provider APIs.

    Each provider should implement a runner class to manage sub-services
    runner classes.
    """

    @abstractmethod
    def execute_instruction(
        self,
        instruction_name: str,
        resolved_arguments: dict[str, ResolvedInstructionArgument],
        terminal_handler: TerminalHandler | None = None,
    ) -> dict[str, ResolvedInstructionResult]:
        return {}
