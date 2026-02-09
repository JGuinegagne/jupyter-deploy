import unittest
from dataclasses import is_dataclass

from jupyter_deploy.engine.supervised_execution import ExecutionProgress
from jupyter_deploy.exceptions import SupervisedExecutionError


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


class TestSupervisedExecutionError(unittest.TestCase):
    """Test cases for ExecutionError exception."""

    def test_init_sets_attributes(self) -> None:
        """Test that initialization sets all attributes correctly."""
        error = SupervisedExecutionError(
            command="up",
            retcode=1,
            message="Terraform apply failed",
        )

        self.assertEqual(error.command, "up")
        self.assertEqual(error.retcode, 1)
        self.assertEqual(str(error), "Terraform apply failed")

    def test_is_exception(self) -> None:
        """Test that ExecutionError is an Exception."""
        error = SupervisedExecutionError(
            command="config",
            retcode=2,
            message="Invalid configuration",
        )

        self.assertIsInstance(error, Exception)

    def test_exception_message(self) -> None:
        """Test that exception message is set correctly."""
        message = "Something went wrong"
        error = SupervisedExecutionError(
            command="down",
            retcode=1,
            message=message,
        )

        self.assertEqual(str(error), message)

    def test_can_be_raised_and_caught(self) -> None:
        """Test that the exception can be raised and caught."""
        with self.assertRaises(SupervisedExecutionError) as context:
            raise SupervisedExecutionError(
                command="up",
                retcode=1,
                message="Test error",
            )

        error = context.exception
        self.assertEqual(error.command, "up")
        self.assertEqual(error.retcode, 1)
        self.assertEqual(str(error), "Test error")

    def test_different_commands(self) -> None:
        """Test ExecutionError with different command types."""
        commands = ["config", "up", "down"]

        for cmd in commands:
            error = SupervisedExecutionError(
                command=cmd,
                retcode=1,
                message=f"{cmd} failed",
            )

            self.assertEqual(error.command, cmd)
            self.assertEqual(str(error), f"{cmd} failed")

    def test_different_return_codes(self) -> None:
        """Test ExecutionError with different return codes."""
        for retcode in [1, 2, 127, 255]:
            error = SupervisedExecutionError(
                command="test",
                retcode=retcode,
                message="Error",
            )

            self.assertEqual(error.retcode, retcode)
