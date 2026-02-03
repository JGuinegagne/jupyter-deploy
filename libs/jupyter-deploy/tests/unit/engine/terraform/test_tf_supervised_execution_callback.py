import unittest
from collections import deque
from unittest.mock import Mock

from jupyter_deploy.engine.terraform.tf_enums import TerraformSequenceId
from jupyter_deploy.engine.terraform.tf_supervised_execution_callback import (
    ANSI_ESCAPE,
    TerraformNoopExecutionCallback,
    TerraformSupervisedExecutionCallback,
)


class TestTerraformSupervisedExecutionCallback(unittest.TestCase):
    """Test cases for TerraformSupervisedExecutionCallback."""

    # _detect_interaction tests
    def test_detect_interaction_positive_simple_prompt(self) -> None:
        """Test that _detect_interaction detects simple 'Enter a value:' prompt."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        line = "  Enter a value:"
        result = callback._detect_interaction(line)

        self.assertTrue(result)

    def test_detect_interaction_positive_with_ansi_codes(self) -> None:
        """Test that _detect_interaction detects prompt with ANSI codes."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        # Terraform wraps prompts with ANSI codes
        line = "  \x1b[1mEnter a value:\x1b[0m \x1b[0m"
        result = callback._detect_interaction(line)

        self.assertTrue(result)

    def test_detect_interaction_positive_prompt_with_leading_whitespace(self) -> None:
        """Test that _detect_interaction detects prompt with leading whitespace."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        line = "    Enter a value:   "
        result = callback._detect_interaction(line)

        self.assertTrue(result)

    def test_detect_interaction_positive_prompt_with_ansi_and_spaces(self) -> None:
        """Test that _detect_interaction detects prompt with ANSI codes and spaces."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        line = "  \x1b[1m  Enter a value:  \x1b[0m"
        result = callback._detect_interaction(line)

        self.assertTrue(result)

    def test_detect_interaction_negative_no_prompt(self) -> None:
        """Test that _detect_interaction returns False for normal output."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        line = "Initializing the backend..."
        result = callback._detect_interaction(line)

        self.assertFalse(result)

    def test_detect_interaction_negative_prompt_in_middle(self) -> None:
        """Test that _detect_interaction returns False when prompt is not at end."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        line = "Enter a value: should not match"
        result = callback._detect_interaction(line)

        self.assertFalse(result)

    def test_detect_interaction_negative_partial_prompt(self) -> None:
        """Test that _detect_interaction returns False for partial prompt text."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        line = "Enter a value"
        result = callback._detect_interaction(line)

        self.assertFalse(result)

    def test_detect_interaction_negative_similar_text(self) -> None:
        """Test that _detect_interaction returns False for similar but different text."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        line = "Please enter the value:"
        result = callback._detect_interaction(line)

        self.assertFalse(result)

    def test_detect_interaction_negative_empty_line(self) -> None:
        """Test that _detect_interaction returns False for empty line."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        line = ""
        result = callback._detect_interaction(line)

        self.assertFalse(result)

    def test_detect_interaction_negative_whitespace_only(self) -> None:
        """Test that _detect_interaction returns False for whitespace-only line."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        line = "    "
        result = callback._detect_interaction(line)

        self.assertFalse(result)

    # _extract_variable_context tests
    def test_extract_variable_context_positive_finds_var(self) -> None:
        """Test that _extract_variable_context finds and extracts variable description."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        # Simulate terraform output buffer
        callback._line_buffer = deque(
            [
                "Initializing...",
                "var.instance_type",
                "  The EC2 instance type",
                "  ",
                "  Enter a value:",
            ],
            maxlen=100,
        )

        context = callback._extract_variable_context()

        # Should return lines from var. onwards
        self.assertEqual(len(context.lines), 4)
        self.assertEqual(context.lines[0], "var.instance_type")
        self.assertEqual(context.lines[1], "  The EC2 instance type")
        self.assertEqual(context.lines[-1], "  Enter a value:")

    def test_extract_variable_context_positive_finds_var_with_ansi(self) -> None:
        """Test that _extract_variable_context finds variable with ANSI codes."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        # Terraform wraps var names in ANSI codes
        callback._line_buffer = deque(
            [
                "Initializing...",
                "\x1b[1mvar.region\x1b[0m",
                "  AWS region",
                "  Enter a value:",
            ],
            maxlen=100,
        )

        context = callback._extract_variable_context()

        # Should return lines from var. onwards (with ANSI codes preserved)
        self.assertEqual(len(context.lines), 3)
        self.assertIn("var.region", ANSI_ESCAPE.sub("", context.lines[0]))
        self.assertEqual(context.lines[-1], "  Enter a value:")

    def test_extract_variable_context_positive_multiple_vars_finds_most_recent(self) -> None:
        """Test that _extract_variable_context finds the most recent var when multiple exist."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        callback._line_buffer = deque(
            [
                "var.old_variable",
                "  Old description",
                "Previous output...",
                "var.new_variable",
                "  New description",
                "  Enter a value:",
            ],
            maxlen=100,
        )

        context = callback._extract_variable_context()

        # Should return lines from most recent var. onwards
        self.assertEqual(len(context.lines), 3)
        self.assertEqual(context.lines[0], "var.new_variable")
        self.assertEqual(context.lines[1], "  New description")

    def test_extract_variable_context_positive_var_at_beginning_of_buffer(self) -> None:
        """Test that _extract_variable_context handles var at start of buffer."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        callback._line_buffer = deque(
            [
                "var.first_var",
                "  Description",
                "  Enter a value:",
            ],
            maxlen=100,
        )

        context = callback._extract_variable_context()

        # Should return all lines
        self.assertEqual(len(context.lines), 3)
        self.assertEqual(context.lines[0], "var.first_var")

    def test_extract_variable_context_negative_no_var_found(self) -> None:
        """Test that _extract_variable_context falls back when no var. found."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        callback._line_buffer = deque(
            [
                "Some output line 1",
                "Some output line 2",
                "Some output line 3",
                "  Enter a value:",
            ],
            maxlen=100,
        )

        context = callback._extract_variable_context()

        # Should return last 10 lines as fallback (or all lines if < 10)
        self.assertEqual(len(context.lines), 4)  # All 4 lines since < 10
        self.assertEqual(context.lines[-1], "  Enter a value:")

    def test_extract_variable_context_negative_empty_buffer(self) -> None:
        """Test that _extract_variable_context handles empty buffer gracefully."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        callback._line_buffer = deque([], maxlen=100)

        context = callback._extract_variable_context()

        # Should return empty lines
        self.assertEqual(len(context.lines), 0)

    def test_extract_variable_context_negative_large_buffer_fallback(self) -> None:
        """Test that _extract_variable_context caps fallback at 10 lines."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        # Create buffer with 20 lines, none starting with var.
        lines = [f"Line {i}" for i in range(20)]
        callback._line_buffer = deque(lines, maxlen=100)

        context = callback._extract_variable_context()

        # Should return last 10 lines as fallback
        self.assertEqual(len(context.lines), 10)
        self.assertEqual(context.lines[0], "Line 10")
        self.assertEqual(context.lines[-1], "Line 19")

    def test_extract_variable_context_negative_var_in_middle_of_line(self) -> None:
        """Test that _extract_variable_context ignores 'var.' in middle of line."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        callback._line_buffer = deque(
            [
                "Setting up var.foo internally",  # var. not at start
                "Some output",
                "  Enter a value:",
            ],
            maxlen=100,
        )

        context = callback._extract_variable_context()

        # Should fall back since "var." is not at line start
        self.assertEqual(len(context.lines), 3)  # All lines as fallback

    def test_extract_variable_context_positive_preserves_ansi_codes(self) -> None:
        """Test that _extract_variable_context preserves ANSI codes in returned lines."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        ansi_line = "\x1b[1mvar.color_var\x1b[0m"
        callback._line_buffer = deque(
            [
                ansi_line,
                "  Description with \x1b[32mgreen text\x1b[0m",
                "  Enter a value:",
            ],
            maxlen=100,
        )

        context = callback._extract_variable_context()

        # ANSI codes should be preserved in the output
        self.assertEqual(context.lines[0], ansi_line)
        self.assertIn("\x1b[32m", context.lines[1])

    def test_extract_variable_context_negative_var_with_special_characters(self) -> None:
        """Test that _extract_variable_context handles lines with var-like patterns."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        callback._line_buffer = deque(
            [
                "variable declaration in code",  # Not "var."
                "vars.something",  # Not "var."
                "  Enter a value:",
            ],
            maxlen=100,
        )

        context = callback._extract_variable_context()

        # Should fall back since no line starts with "var."
        self.assertEqual(len(context.lines), 3)  # All lines as fallback

    def test_extract_variable_context_positive_buffer_maxlen_respected(self) -> None:
        """Test that _extract_variable_context respects buffer maxlen in fallback."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_init,
        )

        # Set maxlen to 5
        callback._line_buffer = deque(
            ["Line 1", "Line 2", "Line 3", "Line 4", "Line 5"],
            maxlen=5,
        )

        context = callback._extract_variable_context()

        # Should return all 5 lines (min(10, 5) = 5)
        self.assertEqual(len(context.lines), 5)

    def test_extract_variable_context_negative_none_maxlen_uses_default(self) -> None:
        """Test that _extract_variable_context handles None maxlen."""
        callback = TerraformSupervisedExecutionCallback(
            terminal_handler=Mock(),  # type: ignore[arg-type]
            sequence_id=TerraformSequenceId.config_plan,
        )

        # Create deque without maxlen (maxlen=None)
        lines = [f"Line {i}" for i in range(15)]
        callback._line_buffer = deque(lines)  # No maxlen specified

        context = callback._extract_variable_context()

        # Should cap at 10 lines (min(10, None) = 10)
        self.assertEqual(len(context.lines), 10)
        self.assertEqual(context.lines[0], "Line 5")

    # ANSI_ESCAPE regex tests
    def test_ansi_escape_regex_removes_color_codes(self) -> None:
        """Test that ANSI_ESCAPE regex removes color codes."""
        text_with_ansi = "\x1b[32mGreen text\x1b[0m"
        cleaned = ANSI_ESCAPE.sub("", text_with_ansi)

        self.assertEqual(cleaned, "Green text")

    def test_ansi_escape_regex_removes_bold_codes(self) -> None:
        """Test that ANSI_ESCAPE regex removes bold codes."""
        text_with_ansi = "\x1b[1mBold text\x1b[0m"
        cleaned = ANSI_ESCAPE.sub("", text_with_ansi)

        self.assertEqual(cleaned, "Bold text")

    def test_ansi_escape_regex_removes_multiple_codes(self) -> None:
        """Test that ANSI_ESCAPE regex removes multiple ANSI codes."""
        text_with_ansi = "\x1b[1m\x1b[32mBold green\x1b[0m\x1b[0m"
        cleaned = ANSI_ESCAPE.sub("", text_with_ansi)

        self.assertEqual(cleaned, "Bold green")

    def test_ansi_escape_regex_handles_no_ansi(self) -> None:
        """Test that ANSI_ESCAPE regex handles text without ANSI codes."""
        text_without_ansi = "Plain text"
        cleaned = ANSI_ESCAPE.sub("", text_without_ansi)

        self.assertEqual(cleaned, "Plain text")

    def test_ansi_escape_regex_handles_complex_codes(self) -> None:
        """Test that ANSI_ESCAPE regex handles complex ANSI codes."""
        text_with_ansi = "\x1b[38;5;214mOrange text\x1b[0m"
        cleaned = ANSI_ESCAPE.sub("", text_with_ansi)

        self.assertEqual(cleaned, "Orange text")


class TestTerraformNoopExecutionCallback(unittest.TestCase):
    """Test cases for TerraformNoopExecutionCallback."""

    def test_is_requesting_user_input_detects_terraform_prompts(self) -> None:
        """Test that is_requesting_user_input detects terraform prompts."""
        callback = TerraformNoopExecutionCallback()

        # Should detect terraform prompts
        self.assertTrue(callback.is_requesting_user_input("Enter a value:"))
        self.assertTrue(callback.is_requesting_user_input("  Enter a value:"))
        self.assertTrue(callback.is_requesting_user_input("  Enter a value:  "))

    def test_is_requesting_user_input_handles_ansi_codes(self) -> None:
        """Test that is_requesting_user_input handles ANSI codes in prompts."""
        callback = TerraformNoopExecutionCallback()

        # Terraform wraps prompts with ANSI codes
        ansi_prompt = "\x1b[1m  Enter a value:\x1b[0m"
        self.assertTrue(callback.is_requesting_user_input(ansi_prompt))

    def test_is_requesting_user_input_rejects_non_prompts(self) -> None:
        """Test that is_requesting_user_input rejects non-prompt patterns."""
        callback = TerraformNoopExecutionCallback()

        # Should not detect other patterns
        self.assertFalse(callback.is_requesting_user_input("PROMPT:"))
        self.assertFalse(callback.is_requesting_user_input("Some random text"))
        self.assertFalse(callback.is_requesting_user_input("Enter a value"))  # Missing colon
        self.assertFalse(callback.is_requesting_user_input("Please enter the value:"))
        self.assertFalse(callback.is_requesting_user_input("Enter a value: should not match"))  # Not at end

    def test_is_requesting_user_input_handles_empty_input(self) -> None:
        """Test that is_requesting_user_input handles empty/whitespace input."""
        callback = TerraformNoopExecutionCallback()

        self.assertFalse(callback.is_requesting_user_input(""))
        self.assertFalse(callback.is_requesting_user_input("   "))

    def test_handle_interaction_prints_to_stdout(self) -> None:
        """Test that handle_interaction prints prompt lines to stdout without newline."""
        import io
        import sys

        callback = TerraformNoopExecutionCallback()

        # Capture stdout
        captured_output = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            callback.handle_interaction("  Enter a value:")
            output = captured_output.getvalue()
            # Should print with trailing space but no newline
            self.assertEqual(output, "  Enter a value: ")
        finally:
            sys.stdout = old_stdout

    def test_handle_interaction_adds_trailing_space(self) -> None:
        """Test that handle_interaction adds trailing space if not present."""
        import io
        import sys

        callback = TerraformNoopExecutionCallback()

        # Capture stdout
        captured_output = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            # Prompt already has trailing space
            callback.handle_interaction("Enter a value: ")
            output = captured_output.getvalue()
            self.assertEqual(output, "Enter a value: ")
        finally:
            sys.stdout = old_stdout
