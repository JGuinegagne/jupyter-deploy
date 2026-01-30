"""Terraform-specific execution callback for prompt detection and context extraction."""

import re

from jupyter_deploy.engine.supervised_execution import InteractionContext, TerminalHandler
from jupyter_deploy.engine.supervised_execution_callback import EngineExecutionCallback, NoopExecutionCallback
from jupyter_deploy.engine.terraform.tf_enums import TerraformSequenceId

# Regex to strip ANSI escape codes from terraform output
# Example raw line: "  \x1b[1mEnter a value:\x1b[0m \x1b[0m"
# After stripping: "Enter a value:"
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


class TerraformSupervisedExecutionCallback(EngineExecutionCallback):
    """Terraform-specific implementation of EngineExecutionCallback.

    Handles terraform-specific prompt detection and context extraction:
    - Detects "Enter a value:" prompts
    - Extracts variable descriptions for CONFIG commands
    - Extracts plan summaries for UP/DOWN commands
    """

    def __init__(self, terminal_handler: TerminalHandler, sequence_id: TerraformSequenceId):
        """Initialize the terraform callback.

        Args:
            terminal_handler: Handler for terminal display
            sequence_id: The terraform command sequence being executed (CONFIG_INIT, UP_APPLY, etc.)
        """
        super().__init__(terminal_handler)
        self.sequence_id = sequence_id

    def _detect_interaction(self, line: str) -> bool:
        """Detect terraform prompts (cheap check).

        Terraform prompts for user input end with "Enter a value:".
        This applies to both variable prompts and confirmation prompts.

        Args:
            line: The current output line to check

        Returns:
            True if this line is a prompt, False otherwise
        """
        # Cheap check first: does the line contain the prompt text?
        if "Enter a value:" not in line:
            return False

        # Line contains prompt text - strip ANSI codes and confirm it ends with prompt
        clean_line = ANSI_ESCAPE.sub("", line).strip()
        return clean_line.endswith("Enter a value:")

    def _extract_interaction_context(self, line: str) -> InteractionContext:
        """Extract context to display for terraform prompts.

        Called when a prompt is detected. Extracts relevant context based
        on the command being executed.

        Args:
            line: The line that triggered the interaction (the prompt line)

        Returns:
            InteractionContext with relevant buffered lines
        """
        # Command-specific context extraction
        if self.sequence_id in [TerraformSequenceId.config_init, TerraformSequenceId.config_plan]:
            return self._extract_variable_context()
        elif self.sequence_id in [TerraformSequenceId.up_apply, TerraformSequenceId.down_destroy]:
            return self._extract_plan_summary_context()

        # Fallback: return last few lines (including prompt line)
        # Cap at buffer size to be defensive
        buffer_list = list(self._line_buffer)
        fallback_lines = min(10, self._line_buffer.maxlen or 10)
        return InteractionContext(lines=buffer_list[-fallback_lines:])

    def _extract_variable_context(self) -> InteractionContext:
        """Extract context for variable prompts.

        Looks backward in buffer for the most recent line starting with "var."
        and returns all lines from that point including the "Enter a value:"
        prompt line. This captures the full variable description that terraform
        displays before prompting.

        Returns:
            InteractionContext with variable description lines (including prompt line)
        """
        # Note: list() conversion is O(n) but acceptable here because:
        # 1. This method is only called when _detect_interaction() finds a prompt (rare)
        # 2. We need backwards search + slicing which deque doesn't efficiently support
        buffer_list = list(self._line_buffer)
        for i in range(len(buffer_list) - 1, -1, -1):
            # Strip ANSI codes before checking (terraform wraps var names in ANSI codes)
            clean_line = ANSI_ESCAPE.sub("", buffer_list[i])
            if clean_line.startswith("var."):
                # Return lines from var. including the prompt line
                return InteractionContext(lines=buffer_list[i:])

        # Fallback: return last 10 lines (including prompt line) if no var. found
        # Cap at buffer size to be defensive
        fallback_lines = min(10, self._line_buffer.maxlen or 10)
        return InteractionContext(lines=buffer_list[-fallback_lines:])

    def _extract_plan_summary_context(self) -> InteractionContext:
        """Extract context for confirmation prompts (up/down commands).

        Looks backward in buffer for the most recent line containing terraform's
        plan summary (e.g., "Plan: 5 to add, 0 to change, 3 to destroy") and
        returns all lines from that point including the "Enter a value:"
        prompt line.

        Returns:
            InteractionContext with plan summary lines (including prompt line)
        """
        # Note: list() conversion is O(n) but acceptable here because:
        # 1. This method is only called when _detect_interaction() finds a prompt (rare)
        # 2. We need backwards search + slicing which deque doesn't efficiently support
        buffer_list = list(self._line_buffer)
        for i in range(len(buffer_list) - 1, -1, -1):
            # Strip ANSI codes before checking (terraform wraps plan summary in ANSI codes)
            clean_line = ANSI_ESCAPE.sub("", buffer_list[i])
            if "Plan:" in clean_line and ("to add" in clean_line or "to destroy" in clean_line):
                # Return lines from Plan: including the prompt line
                return InteractionContext(lines=buffer_list[i:])

        # Fallback: return last 20 lines (including prompt line) if no Plan: found
        # Cap at buffer size to be defensive
        fallback_lines = min(20, self._line_buffer.maxlen or 20)
        return InteractionContext(lines=buffer_list[-fallback_lines:])

    def _is_interaction_complete(self, line: str) -> bool:
        """Detect if terraform interaction is complete.

        For terraform, interaction is complete when we receive any new line
        after a prompt. This indicates the user has responded and terraform
        has continued execution.

        Args:
            line: The current output line to check

        Returns:
            True (interaction always completes on next line after prompt)
        """
        # Any new line after a prompt means user has responded
        return True


class TerraformNoopExecutionCallback(NoopExecutionCallback):
    """No-op execution callback with terraform-specific prompt detection for verbose mode.

    Extends NoopExecutionCallback to add terraform prompt detection for stdin coordination.
    Used when terminal_handler is None (verbose mode) but we still need prompts to work.
    """

    def is_requesting_user_input(self, line: str) -> bool:
        """Detect terraform prompts for stdin coordination.

        Returns True if line ends with terraform's "Enter a value:" prompt,
        allowing PromptHandler to coordinate stdin/stdout properly.

        Args:
            line: The current output line to check

        Returns:
            True if this line is a terraform prompt, False otherwise
        """
        # Cheap check first: does the line contain the prompt text?
        if "Enter a value:" not in line:
            return False

        # Line contains prompt text - strip ANSI codes and confirm it ends with prompt
        clean_line = ANSI_ESCAPE.sub("", line).strip()
        return clean_line.endswith("Enter a value:")

    def handle_interaction(self, line: str) -> None:
        """Print prompt lines to stdout for verbose mode.

        When prompts are detected, they skip on_log_line() and go directly to
        handle_interaction(). We need to print them so they're visible.

        Args:
            line: The prompt line to display
        """
        if not line.endswith(" "):
            line = line + " "
        print(line, end="", flush=True)
