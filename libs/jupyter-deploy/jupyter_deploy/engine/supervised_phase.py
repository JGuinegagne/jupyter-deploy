"""Phase tracking classes for supervised execution."""

import re

from jupyter_deploy.manifest import (
    JupyterDeploySupervisedExecutionDefaultPhaseV1,
    JupyterDeploySupervisedExecutionPhaseV1,
    JupyterDeploySupervisedExecutionSubPhaseV1,
)


class SupervisedSubPhase:
    """A single sub-phase within an ExecutionPhase.

    Encapsulate the completion regex and reward.
    """

    def __init__(self, config: JupyterDeploySupervisedExecutionSubPhaseV1, phase_scale_factor: float):
        """Initialize the sub-phase.

        Args:
            config: Sub-phase configuration from manifest
            phase_scale_factor: The ratio of how much the parent phase weights in the sum of all
                phase sequences
        """
        self.config = config
        self.reward = self.config.weight * phase_scale_factor

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
    """A single execution phase as declared by the manifest or specified in factory method.

    A SupervisedPhase tracks either a list of SupervisedSubPhase events matching different regex,
    a set of countable events all matching the same regex, or both.

    It keeps track of its own accumulated reward, and grants full reward on complete.

    The life-cycle of a SupervisedPhase follows a set pattern:
    1) enter event: when a log line matches the config.enter-pattern
    2) progress events: either when a log line matches the config.progress-pattern regex
        or matches the regex of the next subphase. Grants the event's reward.
    3) exit event: the phase completes, grants the full reward.
    """

    def __init__(self, config: JupyterDeploySupervisedExecutionPhaseV1, sequence_scale_factor: float):
        """Initialize the phase.

        Args:
            config: Phase configuration from manifest
            sequence_scale_factor: The ratio of the weight of the parent phase sequence,
                represented by a SupervisedExecutor, over the sum of the weights
                of all the phase sequences in the jupyter-deploy command.
        """
        self.config = config
        self.full_reward: float = self.config.weight * sequence_scale_factor
        self.scale_factor: float = self.config.weight * sequence_scale_factor / 100

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
                self.sub_phases.append(SupervisedSubPhase(sp_config, self.scale_factor))

        # Store total subphase weight for later recalculation
        self._total_subphase_weight = total_subphase_weight

        # Initialize countable events (may be updated in evaluate_enter if capture group is set)
        events_estimate = self.config.progress_events_estimate or 50
        self._reward_per_event: float = max(self.scale_factor * (100 - total_subphase_weight) / events_estimate, 0.0)

        self._current_sub_phase_index: int = -1
        self._accumulated_reward: float = 0.0

    @property
    def label(self) -> str:
        """Return the current label (phase or active sub-phase)."""
        if self._current_sub_phase_index > -1:
            return self.sub_phases[self._current_sub_phase_index].label
        return self.config.label

    def evaluate_enter(self, line: str) -> bool:
        """Return True if the line signals the phase is now active, False otherwise.

        Optionally calculate the estimate of countable events for this phase from the line
        based on one of its regex group if progress_events_estimate_capture_group is set
        in the SupervisedPhase config.

        Note: if both a phase.config.progress_events_estimate_capture_group and a
        config.progress_events_estimate are set, config.progress_events_estimate takes precedence.
        """
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
                    captured_count = match.group(self.config.progress_events_estimate_capture_group)
                    extracted_estimate = int(captured_count)
                    # Recalculate event progress percentage with extracted value
                    self._reward_per_event = max(
                        self.scale_factor * (100 - self._total_subphase_weight) / extracted_estimate, 0.0
                    )
                except (IndexError, ValueError):
                    # Fall back to default of 10 if extraction fails
                    self._reward_per_event = max(self.scale_factor * (100 - self._total_subphase_weight) / 50, 0.0)

            return True

        return False

    def evaluate_exit(self, line: str) -> bool:
        """Return True if the line signals the full phase is complete, False otherwise."""
        return bool(self.is_active and self._exit_pattern and self._exit_pattern.search(line))

    def evaluate_progress(self, line: str) -> bool:
        """Return True if the line signals a countable event completed, False otherwise."""
        return bool(self.is_active and self._progress_pattern and self._progress_pattern.search(line))

    def evaluate_next_subphase(self, line: str) -> bool:
        """Returns True if the latest subphase just completed."""
        if not self.is_active or not self.sub_phases:
            return False

        # Determine next sub-phase to check
        next_index = self._current_sub_phase_index + 1

        if next_index >= len(self.sub_phases):
            return False

        next_sub_phase = self.sub_phases[next_index]
        result = next_sub_phase.evaluate_enter(line)

        if result:
            self._current_sub_phase_index += 1
            return True
        return False

    def complete_progress_event(self) -> float:
        """Mark countable event complete, accumulate its reward, return the reward."""
        self._accumulated_reward += self._reward_per_event
        return self._reward_per_event

    def complete_subphase(self) -> float:
        """Mark current subphase complete, accumulate its reward, return the reward."""
        if self._current_sub_phase_index < 0:
            # no subphase active, this is essentially a no-op
            self._current_sub_phase_index += 1
            return self._accumulated_reward

        current_subphase = self.sub_phases[self._current_sub_phase_index]
        subphase_reward = current_subphase.reward
        self._accumulated_reward += subphase_reward

        return subphase_reward

    def complete(self) -> float:
        """Mark this phase as complete, return the full reward."""
        self.is_active = False
        self.is_completed = True
        return max(self.full_reward - self._accumulated_reward, 0.0)


class SupervisedDefaultPhase:
    """Default phase of a phases sequence when no declared phase are active.

    Calculate its reward based on countable, equally weighted events
    that it detects by matching a log line to its pattern.

    It grants its full reward on completion.
    """

    def __init__(
        self,
        config: JupyterDeploySupervisedExecutionDefaultPhaseV1,
        full_reward: float = 100.0,
        estimate_override: int | None = None,
    ):
        """Initialize the default phase.

        A default phase accumulates its reward based on completion of equally-weights
        progress event that it matches to a log line using its config.progress-pattern.

        Args:
            config: Phase configuration from manifest
            full_reward: Reward (0-100 percentage points) associated with all events
            estimate_override: Optional override of the number of events, from which to derive
                the reward per event. The handlers provide such values based on the results
                yielded by previous commands.
        """
        self.full_reward = full_reward
        self.config = config

        # Compile the progress pattern for regex matching
        self._progress_pattern = re.compile(self.config.progress_pattern)

        # Determine events estimate: override > explicit > default
        if estimate_override is not None:
            events_estimate = estimate_override
        elif self.config.progress_events_estimate is not None:
            events_estimate = self.config.progress_events_estimate
        else:
            events_estimate = 50

        self._reward_per_event: float = self.full_reward / events_estimate
        self._accumulated_reward: float = 0.0

    @property
    def label(self) -> str:
        """Return the label for this default phase."""
        return self.config.label

    def evaluate_progress(self, line: str) -> bool:
        """Return True if progress was detected on this line, False otherwise."""
        return bool(self._progress_pattern.search(line))

    def complete_progress_event(self) -> float:
        """Return the accumulated reward up to the point of the latest event."""
        self._accumulated_reward += self._reward_per_event
        return self._reward_per_event

    def complete(self) -> float:
        """Complete the default phase, return its full reward."""
        return max(self.full_reward - self._accumulated_reward, 0.0)
