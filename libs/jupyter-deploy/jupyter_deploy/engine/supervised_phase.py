"""Phase tracking classes for supervised execution."""

import math
import re

from jupyter_deploy.manifest import (
    JupyterDeploySupervisedExecutionDefaultPhaseV1,
    JupyterDeploySupervisedExecutionPhaseV1,
    JupyterDeploySupervisedExecutionSubPhaseV1,
)


class SupervisedSubPhase:
    """Manages a single sub-phase within an execution phase.

    Tracks entry and completion of a sub-phase, calculating weight contribution.
    """

    def __init__(self, config: JupyterDeploySupervisedExecutionSubPhaseV1, total_subphase_weights: int):
        """Initialize the sub-phase.

        Args:
            config: Sub-phase configuration from manifest
            total_subphase_weights: Sum of all the sub phase weights of the phase
        """
        self.config = config
        self.phase_progress_percentage = self.config.weight / total_subphase_weights

        # Compile the enter pattern for regex matching
        self._enter_pattern = re.compile(self.config.enter_pattern)

    @property
    def label(self) -> str:
        """Return the sub-phase label."""
        return self.config.label

    def evaluate_enter(self, line: str) -> bool:
        """True if sub-phase was entered, False otherwise."""
        return bool(self._enter_pattern.search(line))


class SupervisedPhase:
    """Manages a single execution phase with optional sub-phases.

    Tracks phase entry/exit, sub-phase transitions, and calculates weight contributions.
    """

    def __init__(self, config: JupyterDeploySupervisedExecutionPhaseV1):
        """Initialize the phase.

        Args:
            config: Phase configuration from manifest
        """
        self.config = config
        self.progress_bar_ratio: float = min(self.config.weight, 100) / 100

        self.is_active = False
        self.is_completed = False

        # Compile patterns for regex matching
        self._enter_pattern = re.compile(self.config.enter_pattern)
        self._exit_pattern = re.compile(self.config.exit_pattern) if self.config.exit_pattern else None
        self._progress_pattern = re.compile(self.config.progress_pattern) if self.config.progress_pattern else None

        # Initialize sub-phases with scaled weights
        total_subphase_weight = 0
        self.sub_phases: list[SupervisedSubPhase] = []
        if config.phases:
            total_subphase_weight = sum([s.weight for s in config.phases])
            for sp_config in config.phases:
                # Sub phase calculate how much its own completion impacts the parent phase
                self.sub_phases.append(SupervisedSubPhase(sp_config, total_subphase_weight))

        # Store total subphase weight for later recalculation
        self._total_subphase_weight = total_subphase_weight

        # Initialize countable events (may be updated in evaluate_enter if capture group is set)
        events_estimate = self.config.progress_events_estimate or 10
        self._event_progress_percentage: float = (100 - total_subphase_weight) / (100 * events_estimate)

        self._current_sub_phase_index: int = -1
        self._current_progress_percentage: float = 0.0

    @property
    def label(self) -> str:
        """Return the current label (phase or active sub-phase)."""
        if self._current_sub_phase_index > -1:
            return self.sub_phases[self._current_sub_phase_index].label
        return self.config.label

    @property
    def weight(self) -> int:
        """Return the weight as declared in the config."""
        return self.config.weight

    def evaluate_enter(self, line: str) -> bool:
        """Return True if phase just received enter signal, False otherwise."""
        if self.is_active or self.is_completed:
            return False

        match = self._enter_pattern.search(line)
        if match:
            self.is_active = True

            # Extract progress_events_estimate from capture group if configured and not explicitly set
            if (
                self.config.progress_events_estimate is None
                and self.config.progress_events_estimate_capture_group is not None
            ):
                try:
                    captured = match.group(self.config.progress_events_estimate_capture_group)
                    extracted_estimate = int(captured)
                    # Recalculate event progress percentage with extracted value
                    self._event_progress_percentage = (100 - self._total_subphase_weight) / (100 * extracted_estimate)
                except (IndexError, ValueError):
                    # Fall back to default of 10 if extraction fails
                    self._event_progress_percentage = (100 - self._total_subphase_weight) / (100 * 10)

            return True

        return False

    def evaluate_exit(self, line: str) -> bool:
        """Return True if phase just received exit signal, False otherwise."""
        return bool(self.is_active and self._exit_pattern and self._exit_pattern.search(line))

    def evaluate_progress(self, line: str) -> bool:
        """Return True if phase just received a signal of incremental progress, False otherwise."""
        return bool(self.is_active and self._progress_pattern and self._progress_pattern.search(line))

    def evaluate_next_subphase(self, line: str) -> bool:
        """Returns True if any of the subphase completed."""
        if not self.is_active or not self.sub_phases:
            return False

        # Determine next sub-phase to check
        next_index = self._current_sub_phase_index + 1

        if next_index >= len(self.sub_phases):
            return False

        next_sub_phase = self.sub_phases[next_index]
        return next_sub_phase.evaluate_enter(line)

    def complete_progress_event(self) -> int:
        """Mark countable progress event complete, return remaining progress bar percentage points."""
        self._current_progress_percentage += self._event_progress_percentage
        return math.floor(self._current_progress_percentage * self.progress_bar_ratio)

    def complete_subphase(self) -> int:
        """Mark current subphase complete, return remaining progress bar percentage points."""
        if self._current_sub_phase_index < 0:
            # no subphase active, this is essentially a no-op
            self._current_sub_phase_index += 1
            return math.floor(self._current_progress_percentage * self.progress_bar_ratio)

        current_subphase = self.sub_phases[self._current_sub_phase_index]
        self._current_progress_percentage += current_subphase.phase_progress_percentage
        self._current_sub_phase_index += 1

        return math.floor(self._current_progress_percentage * self.progress_bar_ratio)

    def complete(self) -> int:
        """Mark this phase as complete, return full progress percentage."""
        if self.is_completed:
            return math.floor(self.progress_bar_ratio)

        self.is_active = False
        self.is_completed = True
        self._current_progress_percentage = 1.0
        return math.floor(self.progress_bar_ratio)


class SupervisedDefaultPhase:
    """Abstract base class for default progress tracking when not in a declared phase.

    Subclasses implement command-specific progress tracking (e.g., resource counting
    for terraform apply/destroy, or other metrics for different commands).
    """

    def __init__(
        self,
        config: JupyterDeploySupervisedExecutionDefaultPhaseV1,
        weight: int = 100,
        override_estimate: int | None = None,
    ):
        """Initialize the default phase.

        Args:
            config: Phase configuration from manifest
            weight: Weight allocated to default tracking (0-100 percentage points)
            override_estimate: Optional override for progress_events_estimate from dynamic source
        """
        self._progress_bar_ratio = min(weight, 100) / 100
        self.config = config

        # Compile the progress pattern for regex matching
        self._progress_pattern = re.compile(self.config.progress_pattern)

        # Determine events estimate: override > explicit > default
        if override_estimate is not None:
            events_estimate = override_estimate
        elif self.config.progress_events_estimate is not None:
            events_estimate = self.config.progress_events_estimate
        else:
            events_estimate = 10

        self._events_percentage_increment: float = 1 / max(events_estimate, 1)
        self._current_progress_percentage: float = 0.0

    @property
    def label(self) -> str:
        """Return the label for this default phase."""
        return self.config.label

    def evaluate_progress(self, line: str) -> bool:
        """Return True if progress was detected on this line, False otherwise."""
        return bool(self._progress_pattern.search(line))

    def complete_progress_event(self) -> int:
        """Return progress bar percentage points (0 to progress_bar_weight)."""
        self._current_progress_percentage += self._events_percentage_increment
        return math.floor(self._progress_bar_ratio * self._current_progress_percentage)

    def complete(self) -> int:
        """Complete the default phase, return remaining weight."""
        return math.floor(self._progress_bar_ratio)
