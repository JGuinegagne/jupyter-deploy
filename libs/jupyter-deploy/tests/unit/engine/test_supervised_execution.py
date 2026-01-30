import unittest
from dataclasses import is_dataclass
from typing import get_type_hints

from jupyter_deploy.engine.supervised_execution import (
    ExecutionError,
    ExecutionProgress,
    LogCallback,
    ProgressCallback,
)


class TestExecutionProgress(unittest.TestCase):
    """Test cases for ExecutionProgress dataclass."""

    def test_init_with_all_fields(self) -> None:
        """Test initialization with all fields."""
        progress = ExecutionProgress(
            label="Creating infrastructure",
            reward=20,
        )

        self.assertEqual(progress.label, "Creating infrastructure")
        self.assertEqual(progress.reward, 20)

    def test_init_with_zero_reward(self) -> None:
        """Test initialization with zero reward (indeterminate progress)."""
        progress = ExecutionProgress(
            label="Initializing",
            reward=0,
        )

        self.assertEqual(progress.label, "Initializing")
        self.assertEqual(progress.reward, 0)

    def test_is_dataclass(self) -> None:
        """Test that ExecutionProgress is a dataclass."""

        self.assertTrue(is_dataclass(ExecutionProgress))


class TestProgressCallback(unittest.TestCase):
    """Test cases for ProgressCallback protocol."""

    def test_protocol_implementation(self) -> None:
        """Test that a class implementing the protocol works correctly."""

        class MockCallback:
            def __init__(self) -> None:
                self.progress_calls: list[ExecutionProgress] = []

            def on_progress(self, progress: ExecutionProgress) -> None:
                self.progress_calls.append(progress)

        # Verify the mock callback works as a ProgressCallback
        callback = MockCallback()

        # Test on_progress
        progress = ExecutionProgress("Test", 50)
        callback.on_progress(progress)
        self.assertEqual(len(callback.progress_calls), 1)
        self.assertEqual(callback.progress_calls[0], progress)

    def test_protocol_type_checking(self) -> None:
        """Test that the protocol is recognized for type checking."""
        # Get the protocol's methods
        hints = get_type_hints(ProgressCallback.on_progress)
        self.assertIn("progress", hints)


class TestLogCallback(unittest.TestCase):
    """Test cases for LogCallback protocol."""

    def test_protocol_implementation(self) -> None:
        """Test that a class implementing the protocol works correctly."""

        class MockCallback:
            def __init__(self) -> None:
                self.log_lines: list[str] = []

            def on_log_line(self, line: str) -> None:
                self.log_lines.append(line)

        # Verify the mock callback works as a LogCallback
        callback = MockCallback()

        # Test on_log_line
        callback.on_log_line("Creating resource...")
        callback.on_log_line("Resource created successfully")
        self.assertEqual(len(callback.log_lines), 2)
        self.assertEqual(callback.log_lines[0], "Creating resource...")
        self.assertEqual(callback.log_lines[1], "Resource created successfully")

    def test_protocol_type_checking(self) -> None:
        """Test that the protocol is recognized for type checking."""
        # Get the protocol's methods
        hints = get_type_hints(LogCallback.on_log_line)
        self.assertIn("line", hints)


class TestExecutionError(unittest.TestCase):
    """Test cases for ExecutionError exception."""

    def test_init_sets_attributes(self) -> None:
        """Test that initialization sets all attributes correctly."""
        error = ExecutionError(
            command="up",
            retcode=1,
            message="Terraform apply failed",
        )

        self.assertEqual(error.command, "up")
        self.assertEqual(error.retcode, 1)
        self.assertEqual(error.message, "Terraform apply failed")

    def test_is_exception(self) -> None:
        """Test that ExecutionError is an Exception."""
        error = ExecutionError(
            command="config",
            retcode=2,
            message="Invalid configuration",
        )

        self.assertIsInstance(error, Exception)

    def test_exception_message(self) -> None:
        """Test that exception message is set correctly."""
        message = "Something went wrong"
        error = ExecutionError(
            command="down",
            retcode=1,
            message=message,
        )

        self.assertEqual(str(error), message)

    def test_can_be_raised_and_caught(self) -> None:
        """Test that the exception can be raised and caught."""
        with self.assertRaises(ExecutionError) as context:
            raise ExecutionError(
                command="up",
                retcode=1,
                message="Test error",
            )

        error = context.exception
        self.assertEqual(error.command, "up")
        self.assertEqual(error.retcode, 1)
        self.assertEqual(error.message, "Test error")

    def test_different_commands(self) -> None:
        """Test ExecutionError with different command types."""
        commands = ["config", "up", "down"]

        for cmd in commands:
            error = ExecutionError(
                command=cmd,
                retcode=1,
                message=f"{cmd} failed",
            )

            self.assertEqual(error.command, cmd)
            self.assertEqual(error.message, f"{cmd} failed")

    def test_different_return_codes(self) -> None:
        """Test ExecutionError with different return codes."""
        for retcode in [1, 2, 127, 255]:
            error = ExecutionError(
                command="test",
                retcode=retcode,
                message="Error",
            )

            self.assertEqual(error.retcode, retcode)
