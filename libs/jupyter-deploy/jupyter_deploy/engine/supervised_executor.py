"""Base class for supervised command execution with progress tracking."""

import subprocess
from pathlib import Path
from typing import IO

from jupyter_deploy.engine.supervised_execution import ExecutionProgress, LogCallback, ProgressCallback
from jupyter_deploy.engine.supervised_phase import SupervisedDefaultPhase, SupervisedPhase
from jupyter_deploy.manifest import (
    JupyterDeploySupervisedExecutionPhaseV1,
    JupyterDeploySupervisedExecutionSubPhaseV1,
)


class SupervisedExecutor:
    """Base class for executing commands with progress tracking and logging.

    This class handles:
    - Streaming command output line by line
    - Writing output to log files
    - Emitting progress updates via callback
    - Managing subprocess execution
    - Phase tracking and transitions
    """

    def __init__(
        self,
        exec_dir: Path,
        log_file: Path,
        progress_callback: ProgressCallback,
        log_callback: LogCallback,
        default_phase: SupervisedDefaultPhase,
        phases: list[SupervisedPhase] | None = None,
        phase_sequence_weight: int = 100,
        phase_sequence_percentage_start: int = 0,
    ):
        """Initialize the executor.

        Args:
            exec_dir: Working directory for command execution
            log_file: Path where logs should be written
            progress_callback: Callback for progress updates
            log_callback: Callback for live log line updates
            default_phase: Default phase instance for progress tracking when not in declared phases
            phases: Optional explicitly declared phases
            phase_sequence_weight: Weight of this command in the overall sequence (0-100)
            phase_sequence_percentage_start: Starting percentage offset for this command
        """
        if not phases:
            phases = []

        self.exec_dir = exec_dir
        self.log_file = log_file
        self._progress_callback = progress_callback
        self._log_callback = log_callback
        self.phase_sequence_weight = phase_sequence_weight
        self.phase_sequence_percentage_start = phase_sequence_percentage_start
        self._log_handle: IO[str] | None = None

        # Initialize declared phases as objects
        self._default_phase = default_phase
        self._declared_phases = phases

        # Track active phase (None = in default phase)
        self._active_declared_phase: SupervisedPhase | None = None
        self._next_declared_phase_index: int = 0  # Index of next phase to check
        self._next_declared_phase: SupervisedPhase | None = self._declared_phases[0] if self._declared_phases else None

        # Accumulated percentage from completed phases
        self._accumulated_percentage = 0.0

        # Helper
        self._last_log_line = ""

    def execute(self, command: list[str]) -> int:
        """Execute a command and track progress, return command retcode"""
        self._current_command = command

        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Open log file for appending (handler may call execute() multiple times)
        with open(self.log_file, "a") as log_handle:
            self._log_handle = log_handle
            retcode = self._execute_command(command)
            self._log_handle = None

        return retcode

    def _execute_command(self, cmd: list[str]) -> int:
        """Execute a single command and stream its output, return retcode.

        Args:
            cmd: The command to execute as a list of strings
        """
        process = subprocess.Popen(
            cmd,
            stdin=None,  # Inherit stdin from parent for interactive prompts
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout
            cwd=self.exec_dir,
            text=True,
            bufsize=1,  # Line buffered
        )

        # Stream output line by line
        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                if not line:
                    break

                # Write to log file
                self._write_to_log(line)

                # Print to stdout for user to see (important for interactive prompts!)
                print(line, end="", flush=True)

                # Track last log line (used for progress updates)
                stripped_line = line.rstrip("\n")
                self._last_log_line = stripped_line

                # Emit log line to callback
                self._log_callback.on_log_line(stripped_line)

                # Parse the line for progress tracking
                self._parse_output_line(stripped_line)

        # Wait for process to complete
        retcode = process.wait()

        # Complete any remaining progress
        if retcode == 0:
            self._complete_execution(self._last_log_line)

        return retcode

    def _write_to_log(self, line: str) -> None:
        """Write a line to the log file.

        Args:
            line: The line to write (should include newline)
        """
        if self._log_handle:
            self._log_handle.write(line)
            self._log_handle.flush()

    def _emit_progress(self, progress: ExecutionProgress) -> None:
        """Emit a progress update via the callback."""
        self._progress_callback.on_progress(progress)

    def get_current_phase_and_subphase(
        self,
    ) -> tuple[JupyterDeploySupervisedExecutionPhaseV1 | None, JupyterDeploySupervisedExecutionSubPhaseV1 | None]:
        """Get the current phase and sub-phase.

        Returns:
            A tuple of (current_phase, current_sub_phase).
            Returns (None, None) if no phases are defined, not in a phase, or if there's no active sub-phase.
        """
        if not self._active_declared_phase:
            return None, None

        current_phase_config = self._active_declared_phase.config
        current_sub_phase_config = None

        # Check if there's an active subphase
        if (
            self._active_declared_phase._current_sub_phase_index >= 0
            and self._active_declared_phase._current_sub_phase_index < len(self._active_declared_phase.sub_phases)
        ):
            current_sub_phase_config = self._active_declared_phase.sub_phases[
                self._active_declared_phase._current_sub_phase_index
            ].config

        return current_phase_config, current_sub_phase_config

    def _parse_output_line(self, line: str) -> None:
        """Parse an output line and emit progress updates.

        Implements the state machine for phase transitions. Subclasses can override
        to add additional parsing logic before or after calling super().

        Args:
            line: A single line of output (without trailing newline)
        """
        if self._active_declared_phase:
            # Case 1: A declared phase is active
            # 1.1: Check for exit
            if self._active_declared_phase.evaluate_exit(line):
                # Complete this phase, move to next declared phase, activate default
                points_earned = self._active_declared_phase.complete()
                self._accumulated_percentage += points_earned
                self._active_declared_phase = None
                self._next_declared_phase_index += 1
                self._next_declared_phase = (
                    self._declared_phases[self._next_declared_phase_index]
                    if self._next_declared_phase_index < len(self._declared_phases)
                    else None
                )
                self._emit_current_progress(line)
                return

            # 1.2: Check for next subphase
            if self._active_declared_phase.evaluate_next_subphase(line):
                # Sub-phase transition - emit progress, keep phase active
                points_earned = self._active_declared_phase.complete_subphase()
                self._accumulated_percentage += points_earned
                self._emit_current_progress(line)
                return

            # 1.3: Check for progress event
            if self._active_declared_phase.evaluate_progress(line):
                # Incremental event detected - emit progress, keep phase active
                points_earned = self._active_declared_phase.complete_progress_event()
                self._accumulated_percentage += points_earned
                self._emit_current_progress(line)
                return

        else:
            # Case 2: No declared phase is active (in default phase)
            # 2.1: Check if next declared phase can be entered
            if self._next_declared_phase and self._next_declared_phase.evaluate_enter(line):
                # Enter declared phase (default phase continues to track in background)
                self._active_declared_phase = self._next_declared_phase
                self._emit_current_progress(line)
                return

            # 2.2: Otherwise evaluate default phase progress
            if self._default_phase.evaluate_progress(line):
                points_earned = self._default_phase.complete_progress_event()
                self._accumulated_percentage += points_earned
                self._emit_current_progress(line)
                return

    def _complete_execution(self, line: str) -> None:
        """Complete execution and emit 100% progress for this command."""
        # Emit final progress at 100% for this command
        overall_percentage = self.phase_sequence_percentage_start + self.phase_sequence_weight
        progress = ExecutionProgress(
            label="",
            percentage=overall_percentage,
        )
        self._emit_progress(progress)

    def _emit_current_progress(self, line: str) -> None:
        """Emit a progress update based on current execution state."""
        # Get label and capped percentage
        label = self._active_declared_phase.label if self._active_declared_phase else self._default_phase.label
        applicable_percentage = min(int(self._accumulated_percentage), 100)

        # Scale to overall percentage based on command sequence position
        overall_percentage = self.phase_sequence_percentage_start + (
            applicable_percentage * self.phase_sequence_weight // 100
        )

        # Emit progress
        progress = ExecutionProgress(
            label=label,
            percentage=overall_percentage,
        )
        self._emit_progress(progress)
