import unittest

from jupyter_deploy.engine.supervised_phase import SupervisedDefaultPhase, SupervisedPhase, SupervisedSubPhase
from jupyter_deploy.manifest import (
    JupyterDeploySupervisedExecutionDefaultPhaseV1,
    JupyterDeploySupervisedExecutionPhaseV1,
    JupyterDeploySupervisedExecutionSubPhaseV1,
)


class TestSupervisedSubPhase(unittest.TestCase):
    """Test cases for SupervisedSubPhase."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = JupyterDeploySupervisedExecutionSubPhaseV1(
            enter_pattern=r"Starting step \d+",
            label="Test SubPhase",
            weight=50,
        )
        self.phase_scale_factor = 0.5
        self.subphase = SupervisedSubPhase(config=self.config, phase_scale_factor=self.phase_scale_factor)

    def test_instantiates_correctly(self) -> None:
        """Test that SupervisedSubPhase instantiates with correct attributes."""
        self.assertEqual(self.subphase.config, self.config)
        self.assertEqual(self.subphase.reward, 25)  # 50 * 0.5

    def test_labels_is_correct(self) -> None:
        """Test that label property returns correct value."""
        self.assertEqual(self.subphase.label, "Test SubPhase")

    def test_evaluate_returns_true_on_regex_match(self) -> None:
        """Test that evaluate_enter returns True when pattern matches."""
        line = "Starting step 5"
        result = self.subphase.evaluate_enter(line)
        self.assertTrue(result)

    def test_evaluate_return_false_on_regex_no_match(self) -> None:
        """Test that evaluate_enter returns False when pattern doesn't match."""
        line = "Something else"
        result = self.subphase.evaluate_enter(line)
        self.assertFalse(result)

    def test_evaluate_does_not_crash_on_unexpected_values(self) -> None:
        """Test that evaluate_enter handles unexpected input gracefully."""
        # Empty string
        result = self.subphase.evaluate_enter("")
        self.assertFalse(result)

        # String with special characters
        result = self.subphase.evaluate_enter("!@#$%^&*()")
        self.assertFalse(result)

        # Very long string
        result = self.subphase.evaluate_enter("x" * 10000)
        self.assertFalse(result)


class TestSupervisedClassWithoutSubphases(unittest.TestCase):
    """Test cases for SupervisedPhase without subphases."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = JupyterDeploySupervisedExecutionPhaseV1(
            enter_pattern=r"Entering phase",
            exit_pattern=r"Exiting phase",
            progress_pattern=r"Progress: \d+%",
            progress_events_estimate=10,
            label="Test Phase",
            weight=80,
        )
        self.sequence_scale_factor = 0.25
        self.phase = SupervisedPhase(config=self.config, sequence_scale_factor=self.sequence_scale_factor)

    def test_instantiates_correctly(self) -> None:
        """Test that SupervisedPhase instantiates with correct attributes."""
        self.assertEqual(self.phase.config, self.config)
        self.assertFalse(self.phase.is_active)
        self.assertFalse(self.phase.is_completed)
        self.assertEqual(len(self.phase.sub_phases), 0)

    def test_calculates_rewards_correctly(self) -> None:
        self.assertAlmostEqual(self.phase._accumulated_reward, 0)
        self.assertAlmostEqual(self.phase.full_reward, 20)  # 80 * 0.25

    def test_label_is_correct(self) -> None:
        """Test that label property returns correct value."""
        self.assertEqual(self.phase.label, "Test Phase")

    def test_evaluate_enter_return_true_on_match(self) -> None:
        """Test that evaluate_enter returns True when pattern matches."""
        line = "Entering phase"
        result = self.phase.evaluate_enter(line)
        self.assertTrue(result)
        self.assertTrue(self.phase.is_active)
        self.assertAlmostEqual(self.phase._accumulated_reward, 0)

    def test_evaluate_enter_return_false_when_no_match(self) -> None:
        """Test that evaluate_enter returns False when pattern doesn't match."""
        line = "Something else"
        result = self.phase.evaluate_enter(line)
        self.assertFalse(result)
        self.assertFalse(self.phase.is_active)
        self.assertAlmostEqual(self.phase._accumulated_reward, 0)

    def test_evaluate_enter_does_not_crash_unexpected_values(self) -> None:
        """Test that evaluate_enter handles unexpected input gracefully."""
        result = self.phase.evaluate_enter("")
        self.assertFalse(result)

        result = self.phase.evaluate_enter("!@#$%^&*()")
        self.assertFalse(result)

        result = self.phase.evaluate_enter("x" * 10000)
        self.assertFalse(result)

    def test_evaluate_exit_return_true_on_match(self) -> None:
        """Test that evaluate_exit returns True when pattern matches and phase is active."""
        self.phase.is_active = True
        line = "Exiting phase"
        result = self.phase.evaluate_exit(line)
        self.assertTrue(result)
        self.assertAlmostEqual(self.phase._accumulated_reward, 0)

    def test_evaluate_exit_return_false_when_no_match(self) -> None:
        """Test that evaluate_exit returns False when pattern doesn't match."""
        self.phase.is_active = True
        line = "Something else"
        result = self.phase.evaluate_exit(line)
        self.assertFalse(result)
        self.assertAlmostEqual(self.phase._accumulated_reward, 0)

    def test_evaluate_exit_does_not_crash_on_unexpected_values(self) -> None:
        """Test that evaluate_exit handles unexpected input gracefully."""
        self.phase.is_active = True
        result = self.phase.evaluate_exit("")
        self.assertFalse(result)

        result = self.phase.evaluate_exit("!@#$%^&*()")
        self.assertFalse(result)

    def test_evaluate_progress_return_true_on_match(self) -> None:
        """Test that evaluate_progress returns True when pattern matches and phase is active."""
        self.phase.is_active = True
        line = "Progress: 50%"
        result = self.phase.evaluate_progress(line)
        self.assertTrue(result)
        self.assertAlmostEqual(self.phase._accumulated_reward, 0)

    def test_evaluate_progress_return_false_when_no_match(self) -> None:
        """Test that evaluate_progress returns False when pattern doesn't match."""
        self.phase.is_active = True
        line = "Something else"
        result = self.phase.evaluate_progress(line)
        self.assertFalse(result)
        self.assertAlmostEqual(self.phase._accumulated_reward, 0)

    def test_evaluate_progress_does_not_crash_on_unexpected_values(self) -> None:
        """Test that evaluate_progress handles unexpected input gracefully."""
        self.phase.is_active = True
        result = self.phase.evaluate_progress("")
        self.assertFalse(result)

        result = self.phase.evaluate_progress("!@#$%^&*()")
        self.assertFalse(result)

    def test_evaluate_next_subphase_return_false(self) -> None:
        """Test that evaluate_next_subphase returns False when no subphases exist."""
        self.phase.is_active = True
        result = self.phase.evaluate_next_subphase("any line")
        self.assertFalse(result)
        self.assertAlmostEqual(self.phase._accumulated_reward, 0)

    def test_complete_progress_event_return_correct_value(self) -> None:
        """Test that complete_progress_event returns correct percentage."""
        self.phase.is_active = True
        reward = self.phase.complete_progress_event()

        # phase weights 80, sequence 25%, expect 10 events
        # this means each event awards 80 * 0.25 / 10 = 2
        self.assertAlmostEqual(reward, 2)
        self.assertAlmostEqual(self.phase._accumulated_reward, 2)

    def test_complete_subphase_does_not_crash(self) -> None:
        """Test that complete_subphase handles being called without subphases."""
        self.phase.is_active = True
        # Should not crash even without subphases
        reward = self.phase.complete_subphase()
        self.assertAlmostEqual(reward, 0)
        self.assertAlmostEqual(self.phase._accumulated_reward, 0)

    def test_complete_return_full_percentage(self) -> None:
        """Test that complete returns full percentage points."""
        self.phase.is_active = True
        reward = self.phase.complete()

        self.assertAlmostEqual(reward, 20)  # 80 * 0.25
        self.assertFalse(self.phase.is_active)
        self.assertTrue(self.phase.is_completed)


class TestSupervisedClassWithSubphases(unittest.TestCase):
    """Test cases for SupervisedPhase with subphases."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = JupyterDeploySupervisedExecutionPhaseV1(
            enter_pattern=r"Entering main phase",
            exit_pattern=r"Exiting main phase",
            label="Main Phase",
            weight=50,
            phases=[
                JupyterDeploySupervisedExecutionSubPhaseV1(
                    enter_pattern=r"SubPhase 1",
                    label="SubPhase 1",
                    weight=20,
                ),
                JupyterDeploySupervisedExecutionSubPhaseV1(
                    enter_pattern=r"SubPhase 2",
                    label="SubPhase 2",
                    weight=80,
                ),
            ],
        )
        self.sequence_scale_factor = 0.5
        self.phase = SupervisedPhase(config=self.config, sequence_scale_factor=self.sequence_scale_factor)

    def test_instantiates_correctly(self) -> None:
        """Test that SupervisedPhase instantiates with subphases correctly."""
        self.assertEqual(self.phase.config, self.config)
        self.assertFalse(self.phase.is_active)
        self.assertFalse(self.phase.is_completed)
        self.assertEqual(len(self.phase.sub_phases), 2)
        self.assertEqual(self.phase._current_sub_phase_index, -1)

    def test_calculates_rewards_correct(self) -> None:
        """Test that SupervisedPhase calculates its rewards correctly."""
        self.assertAlmostEqual(self.phase.full_reward, 25)  # 50 * 0.5
        self.assertAlmostEqual(self.phase._accumulated_reward, 0)

    def test_label_is_correct_when_subphase_inactive(self) -> None:
        """Test that label returns main phase label when no subphase is active."""
        self.assertEqual(self.phase.label, "Main Phase")

    def test_label_is_correct_when_subphase_active(self) -> None:
        """Test that label returns subphase label when subphase is active."""
        self.phase._current_sub_phase_index = 0
        self.assertEqual(self.phase.label, "SubPhase 1")

        self.phase._current_sub_phase_index = 1
        self.assertEqual(self.phase.label, "SubPhase 2")

    def test_evaluate_next_subphase_transitions_correctly(self) -> None:
        """Test that evaluate_next_subphase detects next subphase correctly."""
        self.phase.is_active = True

        # First subphase should match
        result = self.phase.evaluate_next_subphase("SubPhase 1")
        self.assertTrue(result)

        # Complete first subphase to move index forward
        reward1 = self.phase.complete_subphase()
        self.assertAlmostEqual(reward1, 5)  # 20 * 0.5 * 0.5 = 5
        self.assertAlmostEqual(self.phase._accumulated_reward, 5)

        # Second subphase should now match
        result = self.phase.evaluate_next_subphase("SubPhase 2")
        self.assertTrue(result)

        # Complete second subphase
        reward2 = self.phase.complete_subphase()

        self.assertAlmostEqual(reward2, 20)  # 5 + 80 * 0.5 * 0.5 = 20
        self.assertAlmostEqual(self.phase._accumulated_reward, 25)

        # No more subphases
        result = self.phase.evaluate_next_subphase("SubPhase 3")
        self.assertFalse(result)


class TestSupervisedPhaseWithEstimate(unittest.TestCase):
    """Test cases for SupervisedPhase with explicit progress_events_estimate."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = JupyterDeploySupervisedExecutionPhaseV1(
            enter_pattern=r"Starting",
            progress_pattern=r"Item complete",
            progress_events_estimate=5,
            label="Phase with Estimate",
            weight=20,
        )
        self.sequence_scale_factor: float = 0.5
        self.phase = SupervisedPhase(config=self.config, sequence_scale_factor=self.sequence_scale_factor)

    def test_instantiates_correctly(self) -> None:
        """Test that SupervisedPhase instantiates."""
        self.assertEqual(self.phase.config, self.config)

    def test_calculates_reward_correctly(self) -> None:
        """Test that SupervisedPhase instantiates with correct rewards."""
        self.assertAlmostEqual(self.phase.full_reward, 10)  # 20 * 0.5
        self.assertAlmostEqual(self.phase._reward_per_event, 2)  # 20 * 0.5 /10
        self.assertAlmostEqual(self.phase._accumulated_reward, 0)

    def test_label_is_correct(self) -> None:
        """Test that label property returns correct value."""
        self.assertEqual(self.phase.label, "Phase with Estimate")

    def test_complete_progress_event_increments_correctly(self) -> None:
        """Test that progress events increment by correct percentage."""
        self.phase.is_active = True

        # Track progress over multiple events
        reward = self.phase.complete_progress_event()
        self.assertGreaterEqual(reward, 2)

        # After 25 events (the estimate), should be near 100%
        for _ in range(4):
            self.phase.complete_progress_event()

        # Should be complete
        self.assertAlmostEqual(self.phase._accumulated_reward, 10)  # 20 * 0.5


class TestSupervisedPhaseWithDynamicEstimate(unittest.TestCase):
    """Test cases for SupervisedPhase with dynamic progress_events_estimate from capture group."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = JupyterDeploySupervisedExecutionPhaseV1(
            enter_pattern=r"Plan: (\d+) to add, (\d+) to change, (\d+) to destroy\.",
            progress_pattern=r"Creation complete",
            progress_events_estimate_capture_group=1,  # Capture "to add"
            label="Dynamic Phase",
            weight=100,
        )
        self.sequence_scale_factor = 0.5
        self.phase = SupervisedPhase(config=self.config, sequence_scale_factor=self.sequence_scale_factor)

    def test_instantiates_correctly(self) -> None:
        """Test that SupervisedPhase instantiates."""
        self.assertEqual(self.phase.config, self.config)

    def test_calculates_reward_correctly(self) -> None:
        """Test that SupervisedPhase instantiates."""
        self.assertAlmostEqual(self.phase.full_reward, 50)  # 100 * 0.5
        self.assertAlmostEqual(self.phase._accumulated_reward, 0)

    def test_label_is_correct(self) -> None:
        """Test that label property returns correct value."""
        self.assertEqual(self.phase.label, "Dynamic Phase")

    def test_evaluate_enter_extracts_dynamic_estimate(self) -> None:
        """Test that evaluate_enter extracts estimate from capture group."""
        line = "Plan: 5 to add, 10 to change, 5 to destroy."
        result = self.phase.evaluate_enter(line)

        self.assertTrue(result)
        self.assertTrue(self.phase.is_active)

        # Should now use extracted value of 1/50th from estimate
        self.assertAlmostEqual(self.phase._reward_per_event, 10)  # 100 * 0.5 / 5

    def test_evaluate_enter_handles_invalid_capture_group(self) -> None:
        """Test that evaluate_enter falls back to default when capture fails."""
        # Create phase with invalid capture group index
        config = JupyterDeploySupervisedExecutionPhaseV1(  # pyright: ignore[reportCallIssue]
            enter_pattern=r"Plan: (\d+) to add",
            progress_pattern=r"Progress",
            progress_events_estimate_capture_group=5,  # Invalid index
            label="Invalid Capture",
            weight=100,
        )
        phase = SupervisedPhase(config=config, sequence_scale_factor=1.0)

        line = "Plan: 100 to add"
        result = phase.evaluate_enter(line)

        self.assertTrue(result)

        # Should fall back to default of 1/50th from estimate
        self.assertAlmostEqual(phase._reward_per_event, 2)  # 100 * 1.0 / 50

    def test_explicit_estimate_not_overridden_by_capture_group(self) -> None:
        """Test that explicit estimate is not overridden by capture group."""
        config = JupyterDeploySupervisedExecutionPhaseV1(
            enter_pattern=r"Plan: (\d+) to add",
            progress_pattern=r"Progress",
            progress_events_estimate=20,  # Explicit value
            progress_events_estimate_capture_group=1,  # Should be ignored
            label="Explicit Estimate",
            weight=100,
        )
        phase = SupervisedPhase(config=config, sequence_scale_factor=1.0)

        # Initial estimate should use explicit value
        self.assertAlmostEqual(phase._reward_per_event, 5)  # 100 * 1.0 / 20

        # Enter with different value in capture group
        line = "Plan: 50 to add"
        phase.evaluate_enter(line)

        # Should still calculate based on explicit value (20), not extracted (50)
        self.assertAlmostEqual(phase._reward_per_event, 5)


class TestSupervisedDefaultPhase(unittest.TestCase):
    """Test cases for SupervisedDefaultPhase."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = JupyterDeploySupervisedExecutionDefaultPhaseV1(
            **{"progress-pattern": r"complete", "progress-events-estimate": 10}, label="Default Phase"
        )
        self.phase = SupervisedDefaultPhase(config=self.config, full_reward=50)

    def test_instantiates_correctly(self) -> None:
        """Test that SupervisedDefaultPhase instantiates with correct attributes."""
        self.assertEqual(self.phase.config, self.config)

    def test_calculate_rewards_correctly(self) -> None:
        """Test that SupervisedDefaultPhase calculates reward correctly."""
        self.assertAlmostEqual(self.phase.full_reward, 50)
        self.assertAlmostEqual(self.phase._reward_per_event, 5)  # 50 / 10
        self.assertAlmostEqual(self.phase._accumulated_reward, 0)

    def test_label_is_correct(self) -> None:
        """Test that label property returns correct value."""
        self.assertEqual(self.phase.label, "Default Phase")

    def test_evaluate_progress_returns_true_on_match(self) -> None:
        """Test that evaluate_progress returns True when pattern matches."""
        line = "Item complete"
        result = self.phase.evaluate_progress(line)
        self.assertTrue(result)

    def test_evaluate_progress_returns_false_on_no_match(self) -> None:
        """Test that evaluate_progress returns False when pattern doesn't match."""
        line = "Something else"
        result = self.phase.evaluate_progress(line)
        self.assertFalse(result)

    def test_complete_progress_event_increments_correctly(self) -> None:
        """Test that complete_progress_event increments percentage."""
        reward = self.phase.complete_progress_event()

        self.assertAlmostEqual(reward, 5)  # 50 / 10
        self.assertAlmostEqual(self.phase._accumulated_reward, 5)

    def test_override_takes_precedence_over_config(self) -> None:
        """Test that estimate_override takes precedence over config estimate."""
        config = JupyterDeploySupervisedExecutionDefaultPhaseV1(
            **{"progress-pattern": r"complete", "progress-events-estimate": 10}, label="Override Test"
        )
        phase = SupervisedDefaultPhase(config=config, full_reward=100.0, estimate_override=50)

        # Should use override (50), not config (10)
        self.assertAlmostEqual(phase._reward_per_event, 2)  # 100 / 50
