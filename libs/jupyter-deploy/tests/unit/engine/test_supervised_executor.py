import subprocess
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import Mock, mock_open, patch

from jupyter_deploy.engine.supervised_executor import SupervisedExecutor
from jupyter_deploy.engine.supervised_phase import SupervisedDefaultPhase, SupervisedPhase


class TestSupervisedExecutor(unittest.TestCase):
    """Test cases for SupervisedExecutor."""

    def _create_mocked_default_phase_and_mocks(self) -> tuple[Mock, dict[str, Mock]]:
        """Helper to create a mocked default phase with all methods."""
        mock_default_phase = Mock(spec=SupervisedDefaultPhase)

        # Mock property
        mock_default_phase.label = "Test Default Phase"

        # Mock methods
        mock_evaluate_progress = Mock(return_value=False)
        mock_complete_progress_event = Mock(return_value=0)

        mock_default_phase.evaluate_progress = mock_evaluate_progress
        mock_default_phase.complete_progress_event = mock_complete_progress_event

        return mock_default_phase, {
            "evaluate_progress": mock_evaluate_progress,
            "complete_progress_event": mock_complete_progress_event,
        }

    def _create_mocked_phase_and_mocks(self) -> tuple[Mock, dict[str, Mock]]:
        """Helper to create a mocked phase with all methods."""
        mock_phase = Mock(spec=SupervisedPhase)

        # Mock properties
        mock_phase.label = "Test Phase"
        mock_phase.weight = 100

        # Mock attributes
        mock_phase.is_active = False
        mock_phase.is_completed = False

        # Mock methods
        mock_evaluate_enter = Mock(return_value=False)
        mock_evaluate_exit = Mock(return_value=False)
        mock_evaluate_progress = Mock(return_value=False)
        mock_evaluate_next_subphase = Mock(return_value=False)
        mock_complete_progress_event = Mock(return_value=0)
        mock_complete_subphase = Mock(return_value=0)
        mock_complete = Mock(return_value=100)

        mock_phase.evaluate_enter = mock_evaluate_enter
        mock_phase.evaluate_exit = mock_evaluate_exit
        mock_phase.evaluate_progress = mock_evaluate_progress
        mock_phase.evaluate_next_subphase = mock_evaluate_next_subphase
        mock_phase.complete_progress_event = mock_complete_progress_event
        mock_phase.complete_subphase = mock_complete_subphase
        mock_phase.complete = mock_complete

        return mock_phase, {
            "evaluate_enter": mock_evaluate_enter,
            "evaluate_exit": mock_evaluate_exit,
            "evaluate_progress": mock_evaluate_progress,
            "evaluate_next_subphase": mock_evaluate_next_subphase,
            "complete_progress_event": mock_complete_progress_event,
            "complete_subphase": mock_complete_subphase,
            "complete": mock_complete,
        }

    def _create_executor_and_mocks(
        self,
        exec_dir: Path | None = None,
        log_file: Path | None = None,
        phases: list[Mock] | None = None,
    ) -> tuple[SupervisedExecutor, dict[str, Any]]:
        """Helper to create SupervisedExecutor with mocks."""
        # Create mocks
        mock_progress_callback = Mock()
        mock_log_callback = Mock()

        # Create default phase
        default_phase_instance, default_phase_mocks = self._create_mocked_default_phase_and_mocks()

        # Create test phases if not provided
        test_phases: Any
        phases_mocks_list: list[dict[str, Mock]]
        if phases is None:
            mock_phase, phase_mocks = self._create_mocked_phase_and_mocks()
            test_phases = [mock_phase]
            phases_mocks_list = [phase_mocks]
        else:
            test_phases = phases
            phases_mocks_list = []

        mocks_dict: dict[str, Any] = {
            "progress_callback": mock_progress_callback,
            "log_callback": mock_log_callback,
            "default_phase": default_phase_mocks,
            "phases": phases_mocks_list,
        }

        executor = SupervisedExecutor(
            exec_dir=exec_dir or Path("/mock/exec/dir"),
            log_file=log_file or Path("/mock/log.txt"),
            default_phase=default_phase_instance,  # type: ignore[arg-type]
            phases=test_phases,  # type: ignore[arg-type]
            progress_callback=mock_progress_callback,
            log_callback=mock_log_callback,
        )

        return executor, mocks_dict

    def test_init_sets_attributes(self) -> None:
        """Test that initialization sets all attributes correctly."""
        exec_dir = Path("/mock/dir")
        log_file = Path("/mock/log.txt")

        executor, mocks = self._create_executor_and_mocks(
            exec_dir=exec_dir,
            log_file=log_file,
        )

        self.assertEqual(executor.exec_dir, exec_dir)
        self.assertEqual(executor.log_file, log_file)
        self.assertEqual(executor._progress_callback, mocks["progress_callback"])

    def test_execute_creates_log_directory(self) -> None:
        """Test that execute creates log directory if it doesn't exist."""
        # Create a log path in a non-existent directory
        log_file = Path("/mock/logs/nested/test.log")

        executor, mocks = self._create_executor_and_mocks(
            exec_dir=Path("/mock/exec/dir"),
            log_file=log_file,
        )

        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", new_callable=mock_open) as mock_file,
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_process = Mock()
            mock_stdout = Mock()
            mock_stdout.readline = Mock(side_effect=[""])  # EOF immediately
            mock_process.stdout = mock_stdout
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            mocks["mkdir"] = mock_mkdir
            mocks["open"] = mock_file

            executor.execute(["echo", "test"])

            # Verify directory creation was attempted
            mocks["mkdir"].assert_called()

    def test_execute_writes_output_to_log(self) -> None:
        """Test that execute writes command output to log file."""
        executor, mocks = self._create_executor_and_mocks()

        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", new_callable=mock_open) as mock_file,
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_process = Mock()
            mock_stdout = Mock()
            mock_stdout.readline = Mock(
                side_effect=[
                    "Output line 1\n",
                    "Output line 2\n",
                    "Output line 3\n",
                    "",  # EOF
                ]
            )
            mock_process.stdout = mock_stdout
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            mocks["mkdir"] = mock_mkdir
            mocks["open"] = mock_file

            retcode = executor.execute(["echo", "test"])

            self.assertEqual(retcode, 0)

            # Verify log file was opened for writing
            mocks["open"].assert_called()
            handle = mocks["open"]()
            # Verify lines were written
            write_calls = [call[0][0] for call in handle.write.call_args_list]
            self.assertIn("Output line 1\n", write_calls)
            self.assertIn("Output line 2\n", write_calls)
            self.assertIn("Output line 3\n", write_calls)

    def test_execute_calls_parse_output_line(self) -> None:
        """Test that execute calls _parse_output_line for each line."""
        executor, mocks = self._create_executor_and_mocks()

        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", new_callable=mock_open) as mock_file,
            patch("subprocess.Popen") as mock_popen,
            patch.object(executor, "_parse_output_line") as mock_parse,
        ):
            mock_process = Mock()
            mock_stdout = Mock()
            mock_stdout.readline = Mock(
                side_effect=[
                    "Line 1\n",
                    "Line 2\n",
                    "",  # EOF
                ]
            )
            mock_process.stdout = mock_stdout
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            mocks["mkdir"] = mock_mkdir
            mocks["open"] = mock_file

            executor.execute(["echo", "test"])

            # Verify _parse_output_line was called for each line
            self.assertEqual(mock_parse.call_count, 2)
            mock_parse.assert_any_call("Line 1")
            mock_parse.assert_any_call("Line 2")

    def test_execute_emits_progress_via_callback(self) -> None:
        """Test that execute emits progress updates via callback."""
        executor, mocks = self._create_executor_and_mocks()

        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", new_callable=mock_open) as mock_file,
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_process = Mock()
            mock_stdout = Mock()
            mock_stdout.readline = Mock(side_effect=["Test output\n", ""])
            mock_process.stdout = mock_stdout
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            mocks["mkdir"] = mock_mkdir
            mocks["open"] = mock_file

            executor.execute(["echo", "test"])

            # Verify callback was called
            mocks["progress_callback"].on_progress.assert_called()

    def test_execute_returns_zero_on_success(self) -> None:
        """Test that execute returns 0 when all commands succeed."""
        executor, mocks = self._create_executor_and_mocks()

        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", new_callable=mock_open) as mock_file,
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_process = Mock()
            mock_stdout = Mock()
            mock_stdout.readline = Mock(side_effect=[""])  # EOF immediately
            mock_process.stdout = mock_stdout
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            mocks["mkdir"] = mock_mkdir
            mocks["open"] = mock_file

            retcode = executor.execute(["echo", "test"])

            self.assertEqual(retcode, 0)

    def test_execute_returns_non_zero_on_failure(self) -> None:
        """Test that execute returns non-zero return code on failure."""
        executor, mocks = self._create_executor_and_mocks()

        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", new_callable=mock_open) as mock_file,
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_process = Mock()
            mock_stdout = Mock()
            mock_stdout.readline = Mock(side_effect=[""])  # EOF immediately
            mock_process.stdout = mock_stdout
            mock_process.wait.return_value = 1
            mock_popen.return_value = mock_process

            mocks["mkdir"] = mock_mkdir
            mocks["open"] = mock_file

            retcode = executor.execute(["false"])

            self.assertEqual(retcode, 1)

    def test_execute_uses_correct_working_directory(self) -> None:
        """Test that execute uses the specified working directory."""
        exec_dir = Path("/custom/directory")
        executor, mocks = self._create_executor_and_mocks(exec_dir=exec_dir)

        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", new_callable=mock_open) as mock_file,
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_process = Mock()
            mock_stdout = Mock()
            mock_stdout.readline = Mock(side_effect=[""])  # EOF immediately
            mock_process.stdout = mock_stdout
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            mocks["mkdir"] = mock_mkdir
            mocks["open"] = mock_file

            executor.execute(["echo", "test"])

            # Verify cwd parameter was passed correctly
            call_kwargs = mock_popen.call_args[1]
            self.assertEqual(call_kwargs["cwd"], exec_dir)

    def test_execute_merges_stderr_to_stdout(self) -> None:
        """Test that execute merges stderr into stdout."""
        executor, mocks = self._create_executor_and_mocks()

        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", new_callable=mock_open) as mock_file,
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_process = Mock()
            mock_stdout = Mock()
            mock_stdout.readline = Mock(side_effect=[""])  # EOF immediately
            mock_process.stdout = mock_stdout
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            mocks["mkdir"] = mock_mkdir
            mocks["open"] = mock_file

            executor.execute(["echo", "test"])

            # Verify stderr was redirected to stdout
            call_kwargs = mock_popen.call_args[1]
            self.assertEqual(call_kwargs["stderr"], subprocess.STDOUT)

    # State machine tests for _parse_output_line

    def test_parse_output_line_declared_phase_evaluates_exit(self) -> None:
        """Test that _parse_output_line completes phase when exit is detected."""
        mock_phase, phase_mocks = self._create_mocked_phase_and_mocks()
        executor, mocks = self._create_executor_and_mocks(phases=[mock_phase])

        # Set phase as active
        executor._active_declared_phase = mock_phase
        executor._next_declared_phase_index = 0
        mock_phase.is_active = True

        # Configure exit to be detected
        phase_mocks["evaluate_exit"].return_value = True
        phase_mocks["complete"].return_value = 100

        # Parse a line
        executor._parse_output_line("exit signal")

        # Verify phase exit was evaluated
        phase_mocks["evaluate_exit"].assert_called_once_with("exit signal")

        # Verify phase was completed
        phase_mocks["complete"].assert_called_once()

        # Verify phase is no longer active
        self.assertIsNone(executor._active_declared_phase)

        # Verify accumulated percentage updated
        self.assertEqual(executor._accumulated_percentage, 100)

        # Verify progress callback was called
        mocks["progress_callback"].on_progress.assert_called()

    def test_parse_output_line_declared_phase_evaluates_next_subphase(self) -> None:
        """Test that _parse_output_line completes subphase when transition is detected."""
        mock_phase, phase_mocks = self._create_mocked_phase_and_mocks()
        executor, mocks = self._create_executor_and_mocks(phases=[mock_phase])

        # Set phase as active
        executor._active_declared_phase = mock_phase
        mock_phase.is_active = True

        # Configure subphase transition to be detected
        phase_mocks["evaluate_exit"].return_value = False
        phase_mocks["evaluate_next_subphase"].return_value = True
        phase_mocks["complete_subphase"].return_value = 25

        # Parse a line
        executor._parse_output_line("subphase signal")

        # Verify subphase was evaluated
        phase_mocks["evaluate_next_subphase"].assert_called_once_with("subphase signal")

        # Verify subphase was completed
        phase_mocks["complete_subphase"].assert_called_once()

        # Verify phase is still active
        self.assertEqual(executor._active_declared_phase, mock_phase)

        # Verify accumulated percentage updated
        self.assertEqual(executor._accumulated_percentage, 25)

        # Verify progress callback was called
        mocks["progress_callback"].on_progress.assert_called()

    def test_parse_output_line_declared_phase_evaluates_progress(self) -> None:
        """Test that _parse_output_line increments progress when event is detected."""
        mock_phase, phase_mocks = self._create_mocked_phase_and_mocks()
        executor, mocks = self._create_executor_and_mocks(phases=[mock_phase])

        # Set phase as active
        executor._active_declared_phase = mock_phase
        mock_phase.is_active = True

        # Configure progress event to be detected
        phase_mocks["evaluate_exit"].return_value = False
        phase_mocks["evaluate_next_subphase"].return_value = False
        phase_mocks["evaluate_progress"].return_value = True
        phase_mocks["complete_progress_event"].return_value = 5

        # Parse a line
        executor._parse_output_line("progress signal")

        # Verify progress was evaluated
        phase_mocks["evaluate_progress"].assert_called_once_with("progress signal")

        # Verify progress event was completed
        phase_mocks["complete_progress_event"].assert_called_once()

        # Verify phase is still active
        self.assertEqual(executor._active_declared_phase, mock_phase)

        # Verify accumulated percentage updated
        self.assertEqual(executor._accumulated_percentage, 5)

        # Verify progress callback was called
        mocks["progress_callback"].on_progress.assert_called()

    def test_parse_output_line_no_active_phase_enters_declared_phase(self) -> None:
        """Test that _parse_output_line enters declared phase when signal is detected."""
        mock_phase, phase_mocks = self._create_mocked_phase_and_mocks()
        executor, mocks = self._create_executor_and_mocks(phases=[mock_phase])

        # Ensure no phase is active (default phase active)
        executor._active_declared_phase = None
        executor._next_declared_phase = mock_phase
        executor._next_declared_phase_index = 0

        # Configure phase entry to be detected
        phase_mocks["evaluate_enter"].return_value = True

        # Parse a line
        executor._parse_output_line("enter phase signal")

        # Verify phase enter was evaluated
        phase_mocks["evaluate_enter"].assert_called_once_with("enter phase signal")

        # Verify phase is now active
        self.assertEqual(executor._active_declared_phase, mock_phase)

        # Verify progress callback was called
        mocks["progress_callback"].on_progress.assert_called()

    def test_parse_output_line_no_active_phase_evaluates_default_phase_progress(self) -> None:
        """Test that _parse_output_line tracks default phase progress."""
        mock_phase, phase_mocks = self._create_mocked_phase_and_mocks()
        executor, mocks = self._create_executor_and_mocks(phases=[mock_phase])

        # Ensure no phase is active (default phase active)
        executor._active_declared_phase = None
        executor._next_declared_phase = mock_phase

        # Configure default phase progress to be detected
        phase_mocks["evaluate_enter"].return_value = False
        mocks["default_phase"]["evaluate_progress"].return_value = True
        mocks["default_phase"]["complete_progress_event"].return_value = 10

        # Parse a line
        executor._parse_output_line("default progress signal")

        # Verify default phase progress was evaluated
        mocks["default_phase"]["evaluate_progress"].assert_called_once_with("default progress signal")

        # Verify progress event was completed
        mocks["default_phase"]["complete_progress_event"].assert_called_once()

        # Verify no declared phase is active
        self.assertIsNone(executor._active_declared_phase)

        # Verify accumulated percentage updated
        self.assertEqual(executor._accumulated_percentage, 10)

        # Verify progress callback was called
        mocks["progress_callback"].on_progress.assert_called()

    def test_parse_output_line_no_match_does_not_emit_progress(self) -> None:
        """Test that _parse_output_line does not emit progress when no patterns match."""
        mock_phase, phase_mocks = self._create_mocked_phase_and_mocks()
        executor, mocks = self._create_executor_and_mocks(phases=[mock_phase])

        # Ensure no phase is active
        executor._active_declared_phase = None
        executor._next_declared_phase = mock_phase

        # Configure all evaluations to return False
        phase_mocks["evaluate_enter"].return_value = False
        mocks["default_phase"]["evaluate_progress"].return_value = False

        # Parse a line
        executor._parse_output_line("no match")

        # Verify no progress callback was called
        mocks["progress_callback"].on_progress.assert_not_called()

        # Verify accumulated percentage unchanged
        self.assertEqual(executor._accumulated_percentage, 0)

    def test_parse_output_line_phase_exit_moves_to_next_phase(self) -> None:
        """Test that phase exit correctly updates next phase index."""
        mock_phase1, phase1_mocks = self._create_mocked_phase_and_mocks()
        mock_phase2, _ = self._create_mocked_phase_and_mocks()
        executor, _ = self._create_executor_and_mocks(phases=[mock_phase1, mock_phase2])

        # Set first phase as active
        executor._active_declared_phase = mock_phase1
        executor._next_declared_phase_index = 0
        executor._next_declared_phase = mock_phase1

        # Configure exit to be detected
        phase1_mocks["evaluate_exit"].return_value = True
        phase1_mocks["complete"].return_value = 50

        # Parse a line
        executor._parse_output_line("exit phase 1")

        # Verify phase was completed
        phase1_mocks["complete"].assert_called_once()

        # Verify no phase is active now
        self.assertIsNone(executor._active_declared_phase)

        # Verify next phase index incremented
        self.assertEqual(executor._next_declared_phase_index, 1)

        # Verify next phase is phase 2
        self.assertEqual(executor._next_declared_phase, mock_phase2)
