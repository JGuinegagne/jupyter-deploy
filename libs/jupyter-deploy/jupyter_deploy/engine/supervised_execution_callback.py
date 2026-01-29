"""Abstract base class for engine-specific execution callbacks.

This module provides the base class for implementing engine-specific
callbacks that handle output buffering, prompt detection, and context
extraction while delegating display to a TerminalHandler.
"""

from abc import ABC, abstractmethod
from collections import deque

from jupyter_deploy.engine.supervised_execution import ExecutionProgress, InteractionContext, TerminalHandler


class EngineExecutionCallback(ABC):
    """Abstract base for engine-specific execution callbacks.

    This class provides common functionality for handling supervised execution:
    - Buffering output lines for context extraction
    - Delegating display events to terminal handler
    - Tracking interaction state
    - Deciding what lines to display in the log box

    Subclasses must implement engine-specific logic:
    - Prompt detection (when does subprocess need user input?)
    - Context extraction (what buffered lines should be shown?)
    - Interaction completion detection (when is user done responding?)
    - Log display lines (what lines to show in log box during normal operation)
    """

    def __init__(self, terminal_handler: TerminalHandler, buffer_size: int = 200, log_display_lines: int = 2):
        """Initialize the engine callback.

        Args:
            terminal_handler: Handler for terminal display (progress, logs, prompts)
            buffer_size: Number of output lines to keep in buffer for context extraction
            log_display_lines: Number of lines to display in log box during normal operation
        """
        self._terminal_handler = terminal_handler
        self._line_buffer: deque[str] = deque(maxlen=buffer_size)  # For context extraction
        self._display_buffer: deque[str] = deque(maxlen=log_display_lines)  # For display
        self._waiting_for_interaction = False

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
        else:
            # Check if interaction is complete
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
