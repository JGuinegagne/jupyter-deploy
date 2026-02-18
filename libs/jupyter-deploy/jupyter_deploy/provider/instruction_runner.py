from abc import ABC, abstractmethod

from jupyter_deploy.engine.supervised_execution import DisplayManager
from jupyter_deploy.provider.resolved_argdefs import ResolvedInstructionArgument
from jupyter_deploy.provider.resolved_resultdefs import ResolvedInstructionResult


class InstructionRunner(ABC):
    """Abstract class to call provider APIs.

    Each provider should implement a runner class to manage sub-services
    runner classes.
    """

    def __init__(self, display_manager: DisplayManager) -> None:
        """Initialize the instruction runner.

        Args:
            display_manager: Display manager for status updates
        """
        self.display_manager = display_manager

    @abstractmethod
    def execute_instruction(
        self,
        instruction_name: str,
        resolved_arguments: dict[str, ResolvedInstructionArgument],
    ) -> dict[str, ResolvedInstructionResult]:
        """Execute an instruction.

        Args:
            instruction_name: Name of the instruction to execute
            resolved_arguments: Resolved instruction arguments

        Returns:
            Dictionary of resolved instruction results
        """
        return {}
