import unittest
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

from jupyter_deploy.engine.supervised_executor import SupervisedExecutor
from jupyter_deploy.engine.supervised_phase import SupervisedDefaultPhase, SupervisedPhase


class TestSupervisedExecutor(unittest.TestCase):
    """Test cases for SupervisedExecutor."""

    def _create_mock_process_with_output(self, retcode: int = 0) -> tuple[Mock, dict[str, Mock]]:
        """Return a mock process, with mocked methods in dict.

        Dict keys: stdout, stdin, stderr, poll, wait
        """
        mock_process = Mock()

        mock_stdout = Mock()
        mock_stdin = Mock()
        mock_stderr = Mock()
        mock_poll = Mock()
        mock_wait = Mock()

        mock_process.stdout = Mock()
        mock_process.stdin = Mock()
        mock_process.stderr = Mock()
        mock_process.poll = Mock(return_value=retcode)
        mock_process.wait = Mock(return_value=retcode)

        return mock_process, {
            "stdout": mock_stdout,
            "stdin": mock_stdin,
            "stderr": mock_stderr,
            "poll": mock_poll,
            "wait": mock_wait,
        }

    def _create_mocked_prompt_handler_with_mocks(self) -> tuple[Mock, dict[str, Mock]]:
        """Helper to create a mocked PromptHandler instance with mocked methods.

        Dict keys: start
        """
        mock_prompt_handler = Mock()

        mock_start = Mock()
        mock_prompt_handler.start = mock_start

        return mock_prompt_handler, {"start": mock_start}

    def _create_mocked_default_phase_and_mocks(self) -> tuple[Mock, dict[str, Mock]]:
        """Helper to create a mocked default phase with all methods.

        Dict keys: evaluate_progress, complete_progress_event
        """
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
        """Helper to create a mocked phase with all methods.

        Dict keys:
            - evaluate_enter
            - evaluate_exit
            - evaluate_progress
            - evaluate_next_subphase
            - complete_progress_event
            - complete_subphase
            - complete
        """
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

    def _create_execution_callback_and_mocks(self) -> tuple[Mock, dict[str, Mock]]:
        """Helper to create an ExecutionCallback with mocked methods.

        Dict keys:
            - should_parse_progress
            - is_waiting_for_interaction
            - on_progress
            - on_log_line
            - is_requesting_user_input
            - handle_interaction
            - on_execution_error
        """
        mock_execution_callback = Mock()

        mock_should_parse_progress = Mock(return_value=True)
        mock_is_waiting_for_interaction = Mock(return_value=False)
        mock_on_progress = Mock()
        mock_on_log_line = Mock()
        mock_is_requesting_user_input = Mock(return_value=False)
        mock_handle_interaction = Mock()
        mock_on_execution_error = Mock()

        return mock_execution_callback, {
            "should_parse_progress": mock_should_parse_progress,
            "is_waiting_for_interaction": mock_is_waiting_for_interaction,
            "on_progress": mock_on_progress,
            "on_log_line": mock_on_log_line,
            "is_requesting_user_input": mock_is_requesting_user_input,
            "handle_interaction": mock_handle_interaction,
            "on_execution_error": mock_on_execution_error,
        }

    def test_init_sets_attributes(self) -> None:
        """Test that initialization sets all attributes correctly."""
        exec_dir = Path("/mock/dir")
        log_file = Path("/mock/log.txt")

        cb, cb_mocks = self._create_execution_callback_and_mocks()
        dft_phase, _ = self._create_mocked_default_phase_and_mocks()

        executor = SupervisedExecutor(
            exec_dir=exec_dir, log_file=log_file, execution_callback=cb, default_phase=dft_phase
        )

        self.assertEqual(executor.exec_dir, exec_dir)
        self.assertEqual(executor.log_file, log_file)
        self.assertEqual(executor._execution_callback, cb)
        self.assertEqual(executor._default_phase, dft_phase)
        self.assertEqual(executor._declared_phases, [])

        cb_mocks["should_parse_progress"].assert_called_once()
        self.assertTrue(executor._should_parse_progress)

    def test_init_stores_should_parse_progress_from_callback(self) -> None:
        """Test that initialization stores should_parse_progress from callback."""
        cb, cb_mocks = self._create_execution_callback_and_mocks()
        dft_phase, _ = self._create_mocked_default_phase_and_mocks()

        executor = SupervisedExecutor(
            exec_dir=Path("/mock/dir"),
            log_file=Path("/mock/log.txt"),
            execution_callback=cb,
            default_phase=dft_phase,
        )

        cb_mocks["should_parse_progress"].assert_called_once()
        self.assertTrue(executor._should_parse_progress)

    # EXECUTE tests: log file handling
    def test_execute_creates_log_dirs_and_file(self) -> None:
        """Test that execute creates log directory if it doesn't exist."""
        # Create a log path in a non-existent directory
        log_file = Path("/mock/logs/nested/test.log")

        cb, cb_mocks = self._create_execution_callback_and_mocks()
        dft_phase, _ = self._create_mocked_default_phase_and_mocks()

        executor = SupervisedExecutor(
            exec_dir=Path("/mock/dir"),
            log_file=log_file,
            execution_callback=cb,
            default_phase=dft_phase,
        )

        # mock inner method _handle_execute_command

        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", new_callable=mock_open) as mock_file,
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_process = self._create_mock_process_with_output(retcode=0)
            mock_popen.return_value = mock_process

            # verify mkdir called w/ right parameter
            # verify file opens in append mode

            executor.execute(["echo", "test"])

    def test_execute_calls_handle_execute_command(self) -> None:
        """Test that execute calls the underlying method."""

        # mock inner method _handle_execute_command

    def test_execute_returns_handle_execute_retcode(self) -> None:
        """Test that execute surfaces the retcode."""

        # mock inner method _handle_execute_command

    # STATE MACHINE tests for _parse_output_line
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
        self.assertEqual(executor._accumulated_reward, 100)

        # Verify progress callback was called
        mocks["execution_callback"].on_progress.assert_called()

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
        mocks["execution_callback"].on_progress.assert_called()

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
        mocks["execution_callback"].on_progress.assert_called()

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
        mocks["execution_callback"].on_progress.assert_called()

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
        mocks["execution_callback"].on_progress.assert_called()

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
        mocks["execution_callback"].on_progress.assert_not_called()

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

    # HANDLE EXECUTION tests
    @patch("jupyter_deploy.prompt_handler.PromptHandler")
    def test_handle_execute_command_starts_process_and_prompt_handler(self, mock_prompt_handler_cls: Mock) -> None:
        mock_prompt_handler, prompt_handler_mocks = self._create_mocked_prompt_handler_with_mocks()
        mock_prompt_handler_cls.return_value = mock_prompt_handler

        # assert on process:
        # - cmd is correct
        # - process working dir
        # - pipe for all stdin, stdout, stderr
        # - call wait

        # assert on prompt handler
        # - process is passed
        # - callback methods are set
        # - buffer size is > 50
        # - prompt check chars is set
        pass

    @patch("jupyter_deploy.prompt_handler.PromptHandler")
    def test_handle_execute_command_calls_on_execution_error_on_failure(self, mock_prompt_handler_cls: Mock) -> None:
        mock_prompt_handler, prompt_handler_mocks = self._create_mocked_prompt_handler_with_mocks()
        mock_prompt_handler_cls.return_value = mock_prompt_handler
        pass

    @patch("jupyter_deploy.prompt_handler.PromptHandler")
    def test_handle_execute_command_does_not_call_on_execution_error_on_success(
        self, mock_prompt_handler_cls: Mock
    ) -> None:
        mock_prompt_handler, prompt_handler_mocks = self._create_mocked_prompt_handler_with_mocks()
        mock_prompt_handler_cls.return_value = mock_prompt_handler
        pass

    def test_handle_execute_calls_callback_on_log_line_when_prompt_handler_on_line_fires(self) -> None:
        # call via the PromptHandler.on_line()
        pass

    def test_handle_execute_calls_parse_output_line_when_prompt_handler_on_line_fires(self) -> None:
        # call via the PromptHandler.on_line()
        pass

    def test_handle_execute_calls_handle_interaction_when_prompt_handler_on_prompt_fires(self) -> None:
        # call via the PromptHandler.on_line()
        pass
