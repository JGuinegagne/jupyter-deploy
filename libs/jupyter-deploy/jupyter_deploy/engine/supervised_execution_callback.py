"""Abstract base class for engine-specific execution callbacks.

This module provides the base class for implementing engine-specific
callbacks that handle output buffering, prompt detection, and context
extraction while delegating display to a TerminalHandler.
"""

from abc import ABC, abstractmethod
from collections import deque

from jupyter_deploy.engine.supervised_execution import ExecutionProgress, InteractionContext, TerminalHandler


class ExecutionCallbackInterface(ABC):
    """Abstract interface for execution callbacks used by SupervisedExecutor.

    This defines the minimal interface that SupervisedExecutor needs.
    Implementations can be full-featured (with buffering, interaction handling)
    or simple no-ops for verbose mode.
    """

    @abstractmethod
    def should_parse_progress(self) -> bool:
        """Check if the executor should parse lines for progress tracking.

        Returns:
            True if progress parsing is needed, False otherwise
        """
        ...

    @abstractmethod
    def is_waiting_for_interaction(self) -> bool:
        """Check if currently waiting for user interaction.

        Returns:
            True if in the middle of an interaction, False otherwise
        """
        ...

    @abstractmethod
    def is_requesting_user_input(self, line: str) -> bool:
        """Check if the line triggers or continues user interaction.

        Args:
            line: A single line of output (without trailing newline)

        Returns:
            True if this line is part of user interaction
        """
        ...

    @abstractmethod
    def handle_interaction(self, line: str) -> None:
        """Handle a line that is part of user interaction.

        Args:
            line: A single line of output (without trailing newline)
        """
        ...

    @abstractmethod
    def on_log_line(self, line: str) -> None:
        """Handle a normal log line (not part of interaction).

        Args:
            line: A single line of output (without trailing newline)
        """
        ...

    @abstractmethod
    def on_progress(self, progress: ExecutionProgress) -> None:
        """Handle a progress update.

        Args:
            progress: The current execution progress state
        """
        ...

    @abstractmethod
    def on_execution_error(self, retcode: int) -> None:
        """Handle command execution failure.

        Called when the command completes with a non-zero return code.
        The callback should display error context to help the user understand what went wrong.

        Args:
            retcode: The non-zero return code from the failed command
        """
        ...


class EngineExecutionCallback(ExecutionCallbackInterface):
    """Abstract base for engine-specific execution callbacks.

    This class provides common functionality for handling supervised execution:
    - Buffering output lines efficiently for context extraction
    - Delegating display events to terminal handler
    - Tracking interaction state
    - Deciding what lines to display in the log box

    Subclasses must implement engine-specific logic:
    - Prompt detection (when does subprocess need user input?)
    - Context extraction (what buffered lines should be shown?)
    - Interaction completion detection (when is user done responding?)
    - Log display lines (what lines to show in log box during normal operation)
    """

    def __init__(
        self,
        terminal_handler: TerminalHandler,
        buffer_size: int = 200,
        log_display_lines: int = 2,
        error_display_lines: int = 50,
    ):
        """Initialize the engine callback.

        Args:
            terminal_handler: Handler for terminal display (progress, logs, prompts)
            buffer_size: Number of output lines to keep in buffer for context extraction
            log_display_lines: Number of lines to display in log box during normal operation
            error_display_lines: Number of lines to display when execution fails

        Raises:
            ValueError: If buffer_size is smaller than log_display_lines or error_display_lines
        """
        if buffer_size < log_display_lines:
            raise ValueError(f"buffer_size ({buffer_size}) must be >= log_display_lines ({log_display_lines})")
        if buffer_size < error_display_lines:
            raise ValueError(f"buffer_size ({buffer_size}) must be >= error_display_lines ({error_display_lines})")

        self._terminal_handler = terminal_handler
        self._line_buffer: deque[str] = deque(maxlen=buffer_size)  # For context extraction
        self._display_buffer: deque[str] = deque(maxlen=log_display_lines)  # For display
        self._error_display_lines = error_display_lines
        self._waiting_for_interaction = False

    def should_parse_progress(self) -> bool:
        """Progress parsing is enabled for EngineExecutionCallback."""
        return True

    def is_waiting_for_interaction(self) -> bool:
        """Check if currently waiting for user interaction."""
        return self._waiting_for_interaction

    def is_requesting_user_input(self, line: str) -> bool:
        """Check if the line is part of user interaction (cheap check).

        This is called BEFORE on_log_line() to determine if the line should
        be handled as an interactive prompt rather than normal output.

        Args:
            line: A single line of output (without trailing newline)

        Returns:
            True if this line is part of user interaction
        """
        if not self._waiting_for_interaction:
            # Cheap check: does this line trigger a prompt?
            return self._detect_interaction(line)
        else:
            # We're in interaction mode - all lines are interaction lines
            return True

    def handle_interaction(self, line: str) -> None:
        """Handle a line that is part of user interaction.

        This is called when check_interaction() returns True. The line is added
        to the context buffer for potential display, but NOT to the display buffer.

        Args:
            line: A single line of output (without trailing newline)
        """
        # Add to context buffer only (NOT display buffer)
        self._line_buffer.append(line)

        if not self._waiting_for_interaction:
            # This line triggered the interaction - extract context and notify
            context = self._extract_interaction_context(line)
            self._waiting_for_interaction = True
            self._terminal_handler.on_interaction_start(context)
            # Don't check for completion on the same line that started interaction
        else:
            # We're in interaction mode - check if interaction is complete
            if self._is_interaction_complete(line):
                self._waiting_for_interaction = False
                self._terminal_handler.on_interaction_end()

                # Update log box back to normal size using display buffer
                self._terminal_handler.update_log_box(list(self._display_buffer))

    def on_log_line(self, line: str) -> None:
        """Handle a normal log line (not part of interaction).

        Called when check_interaction() returns False.

        Args:
            line: A single line of output (without trailing newline)
        """
        # Add to both buffers (deques automatically drop oldest when full)
        self._line_buffer.append(line)  # For context extraction (e.g. 200 lines)
        self._display_buffer.append(line)  # For normal display (e.g. 2 lines)

        # Update log box with display buffer
        self._terminal_handler.update_log_box(list(self._display_buffer))

    def on_progress(self, progress: ExecutionProgress) -> None:
        """Handle a progress update.

        Delegates directly to terminal handler.
        """
        self._terminal_handler.on_progress(progress)

    def on_execution_error(self, retcode: int) -> None:
        """Handle command execution failure.

        Extracts error context from the line buffer and displays it via terminal handler.

        Args:
            retcode: The non-zero return code from the failed command
        """
        # Extract error context from buffer using configured line count
        error_context_lines = list(self._line_buffer)[-self._error_display_lines :]
        self._terminal_handler.display_error_context(error_context_lines)

    @abstractmethod
    def _detect_interaction(self, line: str) -> bool:
        """Detect if a line triggers user interaction (cheap check).

        Subclasses implement engine-specific prompt detection logic.
        For example, terraform prompts end with "Enter a value:".

        Args:
            line: The current output line to check

        Returns:
            True if this line triggers a prompt, False otherwise
        """
        ...

    @abstractmethod
    def _extract_interaction_context(self, line: str) -> InteractionContext:
        """Extract context to display when interaction is detected.

        Called when _detect_interaction() returns True. Subclasses implement
        engine-specific logic to extract relevant context from the buffer.

        Args:
            line: The line that triggered the interaction

        Returns:
            InteractionContext with buffered lines to display
        """
        ...

    @abstractmethod
    def _is_interaction_complete(self, line: str) -> bool:
        """Detect if user interaction is complete.

        Subclasses implement engine-specific logic to determine when
        the user has finished responding to a prompt.
        For example, terraform prompts complete when any new line arrives.

        Args:
            line: The current output line to check

        Returns:
            True if interaction is complete, False otherwise
        """
        ...


class NoopExecutionCallback(ExecutionCallbackInterface, ABC):
    """Abstract base class for no-op execution callbacks in verbose mode.

    This callback provides default no-op implementations for most methods, but requires
    subclasses to implement engine-specific prompt detection for stdin coordination.
    Used when terminal_handler is None (verbose mode).
    SupervisedExecutor will still print to stdout and write to log file.
    """

    def should_parse_progress(self) -> bool:
        """Progress parsing is disabled for NoopExecutionCallback."""
        return False

    def is_waiting_for_interaction(self) -> bool:
        """No interaction handling in verbose mode."""
        return False

    @abstractmethod
    def is_requesting_user_input(self, line: str) -> bool:
        """Detect engine-specific prompts for stdin coordination.

        Subclasses must implement this to detect prompts (e.g., terraform's "Enter a value:").
        This allows PromptHandler to coordinate stdin/stdout properly even in verbose mode.

        Args:
            line: The current output line to check

        Returns:
            True if this line is a prompt, False otherwise
        """
        ...

    def handle_interaction(self, line: str) -> None:
        """No-op - no interaction handling in verbose mode."""
        pass

    def on_log_line(self, line: str) -> None:
        """Print to stdout for verbose mode."""
        print(line, flush=True)

    def on_progress(self, progress: ExecutionProgress) -> None:
        """No-op - no progress tracking in verbose mode."""
        pass

    def on_execution_error(self, retcode: int) -> None:
        """No-op - error already displayed to stdout in verbose mode."""
        pass
