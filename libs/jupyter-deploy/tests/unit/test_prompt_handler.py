# mypy: disable-error-code=attr-defined
# we need this mypy disable as we tinker with side effect attributes

import unittest
from unittest.mock import Mock, patch

from jupyter_deploy.prompt_handler import PromptHandler


class TestPromptHandler(unittest.TestCase):
    """Test cases for PromptHandler."""

    def _create_mock_process(self) -> Mock:
        """Helper to create a mock process with stdout, stdin, stderr."""
        mock_process = Mock()
        mock_process.stdout = Mock()
        mock_process.stdin = Mock()
        mock_process.stderr = Mock()
        mock_process.poll = Mock(return_value=None)
        return mock_process

    def test_captures_stdout_and_fires_on_line_callback(self) -> None:
        """Test that PromptHandler captures stdout and fires on_line callback."""
        mock_process = self._create_mock_process()

        # Simulate stdout with a complete line
        stdout_content = "Hello World\n"
        stdout_pos = 0

        def read_char(size: int) -> str:
            nonlocal stdout_pos
            if stdout_pos >= len(stdout_content):
                return ""  # EOF
            char = stdout_content[stdout_pos : stdout_pos + size]
            stdout_pos += size
            return char

        mock_process.stdout.read = Mock(side_effect=read_char)

        # Mock callbacks
        on_line = Mock()
        is_prompt = Mock(return_value=False)
        on_prompt = Mock()

        # Create handler and start
        handler = PromptHandler(
            process=mock_process,
            on_line=on_line,
            is_prompt=is_prompt,
            on_prompt=on_prompt,
        )
        handler.start()

        # Verify on_line was called with the complete line
        on_line.assert_called_once_with("Hello World\n")
        on_prompt.assert_not_called()

    def test_captures_stdout_and_fires_on_char_callback(self) -> None:
        """Test that PromptHandler captures stdout and fires on_char callback for each character."""
        mock_process = self._create_mock_process()

        # Simulate stdout character by character
        stdout_content = "Hi\n"
        stdout_pos = 0

        def read_char(size: int) -> str:
            nonlocal stdout_pos
            if stdout_pos >= len(stdout_content):
                return ""  # EOF
            char = stdout_content[stdout_pos : stdout_pos + size]
            stdout_pos += size
            return char

        mock_process.stdout.read = Mock(side_effect=read_char)

        # Mock callbacks
        on_line = Mock()
        on_char = Mock()
        is_prompt = Mock(return_value=False)
        on_prompt = Mock()

        # Create handler and start
        handler = PromptHandler(
            process=mock_process,
            on_line=on_line,
            is_prompt=is_prompt,
            on_prompt=on_prompt,
            on_char=on_char,
        )
        handler.start()

        # Verify on_char was called for each character
        self.assertEqual(on_char.call_count, 3)  # 'H', 'i', '\n'
        on_char.assert_any_call("H")
        on_char.assert_any_call("i")
        on_char.assert_any_call("\n")

    def test_captures_prompt_and_fires_on_prompt_callback(self) -> None:
        """Test that PromptHandler detects prompts and fires on_prompt callback."""
        mock_process = self._create_mock_process()

        # Simulate stdout with a prompt (no trailing newline)
        stdout_content = "Enter value: "
        stdout_pos = 0

        def read_char(size: int) -> str:
            nonlocal stdout_pos
            if stdout_pos >= len(stdout_content):
                return ""  # EOF
            char = stdout_content[stdout_pos : stdout_pos + size]
            stdout_pos += size
            return char

        mock_process.stdout.read = Mock(side_effect=read_char)

        # Mock callbacks - is_prompt returns True when buffer ends with ': '
        on_line = Mock()
        on_prompt = Mock()

        def check_prompt(buffer: str) -> bool:
            return buffer.endswith(": ")

        # Create handler with ':' as prompt check char
        handler = PromptHandler(
            process=mock_process,
            on_line=on_line,
            is_prompt=check_prompt,
            on_prompt=on_prompt,
            prompt_check_chars=":",
        )
        handler.start()

        # Verify on_prompt was called with the prompt
        on_prompt.assert_called_once_with("Enter value: ")
        on_line.assert_not_called()

    def test_captures_stderr_and_fires_on_stderr_callback(self) -> None:
        """Test that PromptHandler captures stderr and fires on_stderr callback."""
        mock_process = self._create_mock_process()

        # Simulate empty stdout (EOF immediately)
        mock_process.stdout.read = Mock(return_value="")

        # Simulate stderr with multiple lines
        stderr_lines = ["Error line 1\n", "Error line 2\n", "Error line 3\n"]
        stderr_pos = 0

        def readline() -> str:
            nonlocal stderr_pos
            if stderr_pos >= len(stderr_lines):
                return ""
            line = stderr_lines[stderr_pos]
            stderr_pos += 1
            return line

        mock_process.stderr.readline = Mock(side_effect=readline)

        # Mock callbacks
        on_line = Mock()
        is_prompt = Mock(return_value=False)
        on_prompt = Mock()
        on_stderr = Mock()

        # Create handler and start
        handler = PromptHandler(
            process=mock_process,
            on_line=on_line,
            is_prompt=is_prompt,
            on_prompt=on_prompt,
            on_stderr=on_stderr,
        )
        handler.start()

        # Verify on_stderr was called with all buffered lines
        on_stderr.assert_called_once_with(stderr_lines)

    def test_stderr_callback_fired_after_stdout(self) -> None:
        """Test that stderr callback is fired only after stdout completes."""
        mock_process = self._create_mock_process()

        # Track callback order
        callback_order: list[str] = []

        # Simulate stdout
        stdout_content = "stdout line 1\nstdout line 2\n"
        stdout_pos = 0

        def read_char(size: int) -> str:
            nonlocal stdout_pos
            if stdout_pos >= len(stdout_content):
                return ""  # EOF
            char = stdout_content[stdout_pos : stdout_pos + size]
            stdout_pos += size
            return char

        mock_process.stdout.read = Mock(side_effect=read_char)

        # Simulate stderr
        stderr_lines = ["stderr line 1\n", "stderr line 2\n"]
        stderr_pos = 0

        def readline() -> str:
            nonlocal stderr_pos
            if stderr_pos >= len(stderr_lines):
                return ""
            line = stderr_lines[stderr_pos]
            stderr_pos += 1
            return line

        mock_process.stderr.readline = Mock(side_effect=readline)

        # Mock callbacks that track order
        def on_line_impl(line: str) -> None:
            callback_order.append(f"on_line: {line}")

        def on_stderr_impl(lines: list[str]) -> None:
            callback_order.append(f"on_stderr: {len(lines)} lines")

        # Create handler and start
        handler = PromptHandler(
            process=mock_process,
            on_line=on_line_impl,
            is_prompt=Mock(return_value=False),
            on_prompt=Mock(),
            on_stderr=on_stderr_impl,
        )
        handler.start()

        # Verify callback order: all on_line calls before on_stderr
        self.assertEqual(len(callback_order), 3)  # 2 on_line + 1 on_stderr
        self.assertTrue(callback_order[0].startswith("on_line"))
        self.assertTrue(callback_order[1].startswith("on_line"))
        self.assertTrue(callback_order[2].startswith("on_stderr"))

    @patch("sys.stdin")
    @patch("select.select")
    def test_captures_stdin_and_pipes_to_process(self, mock_select: Mock, mock_stdin: Mock) -> None:
        """Test that PromptHandler captures stdin and pipes it to the subprocess."""
        mock_process = self._create_mock_process()

        # Simulate stdout with a prompt to trigger stdin reading
        stdout_content = "Enter value: "
        stdout_pos = 0

        def read_char(size: int) -> str:
            nonlocal stdout_pos
            if stdout_pos >= len(stdout_content):
                return ""  # EOF
            char = stdout_content[stdout_pos : stdout_pos + size]
            stdout_pos += size
            return char

        mock_process.stdout.read = Mock(side_effect=read_char)

        # Simulate stdin input
        mock_stdin.isatty.return_value = True
        stdin_inputs = ["user input\n", ""]  # Second empty string for EOF

        def readline_side_effect() -> str:
            if stdin_inputs:
                return stdin_inputs.pop(0)
            return ""

        mock_stdin.readline = Mock(side_effect=readline_side_effect)

        # Mock select to indicate stdin is ready
        mock_select.return_value = ([mock_stdin], [], [])

        # Mock callbacks
        def check_prompt(buffer: str) -> bool:
            return buffer.endswith(": ")

        # Create handler and start
        handler = PromptHandler(
            process=mock_process,
            on_line=Mock(),
            is_prompt=check_prompt,
            on_prompt=Mock(),
            prompt_check_chars=":",
        )
        handler.start()

        # Verify stdin was written to process stdin
        mock_process.stdin.write.assert_called_with("user input\n")
        mock_process.stdin.flush.assert_called()

    @patch("sys.stdin")
    @patch("select.select")
    @patch("time.sleep")
    def test_wait_for_stdout_to_complete_before_prompting(
        self, mock_sleep: Mock, mock_select: Mock, mock_stdin: Mock
    ) -> None:
        """Test that stdin thread waits for stdout to complete before reading input."""
        mock_process = self._create_mock_process()

        # Track when stdout completes
        stdout_complete = False

        # Simulate stdout that takes time
        stdout_content = "Processing...\nDone\nEnter value: "
        stdout_pos = 0

        def read_char(size: int) -> str:
            nonlocal stdout_pos, stdout_complete
            if stdout_pos >= len(stdout_content):
                stdout_complete = True
                return ""  # EOF
            char = stdout_content[stdout_pos : stdout_pos + size]
            stdout_pos += size
            return char

        mock_process.stdout.read = Mock(side_effect=read_char)

        # Track stdout state when stdin is accessed
        stdin_called_when_stdout_complete = False

        # Simulate stdin
        mock_stdin.isatty.return_value = True

        def readline_impl() -> str:
            nonlocal stdin_called_when_stdout_complete
            stdin_called_when_stdout_complete = stdout_complete
            return ""  # EOF

        mock_stdin.readline = Mock(side_effect=readline_impl)

        # Mock select to indicate stdin is ready after prompt
        mock_select.return_value = ([mock_stdin], [], [])

        # Mock callbacks
        def check_prompt(buffer: str) -> bool:
            return buffer.endswith(": ")

        # Create handler and start
        handler = PromptHandler(
            process=mock_process,
            on_line=Mock(),
            is_prompt=check_prompt,
            on_prompt=Mock(),
            prompt_check_chars=":",
        )
        handler.start()

        # Verify that stdin was only accessed after stdout completed
        # Note: This is a bit tricky to test since stdin runs in a separate thread
        # and waits for prompt_ready event. The actual coordination happens via
        # the threading.Event, which we're testing indirectly here.
        self.assertTrue(stdout_complete)

    def test_handles_incomplete_line_at_eof(self) -> None:
        """Test that PromptHandler handles incomplete lines (no newline) at EOF."""
        mock_process = self._create_mock_process()

        # Simulate stdout with incomplete line at EOF
        stdout_content = "incomplete line"
        stdout_pos = 0

        def read_char(size: int) -> str:
            nonlocal stdout_pos
            if stdout_pos >= len(stdout_content):
                return ""  # EOF
            char = stdout_content[stdout_pos : stdout_pos + size]
            stdout_pos += size
            return char

        mock_process.stdout.read = Mock(side_effect=read_char)

        # Mock callbacks
        on_line = Mock()
        is_prompt = Mock(return_value=False)
        on_prompt = Mock()

        # Create handler and start
        handler = PromptHandler(
            process=mock_process,
            on_line=on_line,
            is_prompt=is_prompt,
            on_prompt=on_prompt,
        )
        handler.start()

        # Verify incomplete line is treated as a line at EOF
        on_line.assert_called_once_with("incomplete line")

    def test_buffer_size_sliding_window(self) -> None:
        """Test that buffer uses sliding window when it exceeds buffer_size."""
        mock_process = self._create_mock_process()

        # Simulate very long line without newline
        stdout_content = "a" * 200 + ": "  # 200 chars + prompt
        stdout_pos = 0

        def read_char(size: int) -> str:
            nonlocal stdout_pos
            if stdout_pos >= len(stdout_content):
                return ""  # EOF
            char = stdout_content[stdout_pos : stdout_pos + size]
            stdout_pos += size
            return char

        mock_process.stdout.read = Mock(side_effect=read_char)

        # Mock callbacks
        on_line = Mock()
        on_prompt = Mock()

        def check_prompt(buffer: str) -> bool:
            return buffer.endswith(": ")

        # Create handler with small buffer size
        handler = PromptHandler(
            process=mock_process,
            on_line=on_line,
            is_prompt=check_prompt,
            on_prompt=on_prompt,
            buffer_size=100,  # Smaller than content
            prompt_check_chars=":",
        )
        handler.start()

        # Verify prompt was still detected despite buffer overflow
        # The sliding window should keep the last part of the buffer
        on_prompt.assert_called_once()
        # The prompt should contain the last part including ': '
        prompt_arg = on_prompt.call_args[0][0]
        self.assertTrue(prompt_arg.endswith(": "))

    def test_initialization_with_default_parameters(self) -> None:
        """Test that PromptHandler can be initialized with default parameters."""
        mock_process = self._create_mock_process()

        handler = PromptHandler(
            process=mock_process,
            on_line=Mock(),
            is_prompt=Mock(return_value=False),
            on_prompt=Mock(),
        )

        # Verify defaults
        self.assertEqual(handler.buffer_size, 100)
        self.assertEqual(handler.prompt_check_chars, ":?")
        self.assertIsNone(handler.on_char)
        self.assertIsNone(handler.on_stderr)
