import unittest
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import yaml

from jupyter_deploy.engine.supervised_executor import SupervisedExecutor
from jupyter_deploy.engine.terraform.tf_constants import TerraformSequenceId
from jupyter_deploy.engine.terraform.tf_plan_metadata import TerraformPlanMetadata
from jupyter_deploy.engine.terraform.tf_supervised_executor import create_terraform_executor
from jupyter_deploy.manifest import JupyterDeployManifestV1


class TestCreateTerraformExecutorNoManifestNorPlan(unittest.TestCase):
    """Test cases for create_terraform_executor factory function."""

    def test_pass_paths_to_executor(self) -> None:
        """Test that paths are passed correctly to executor."""
        exec_dir = Path("/mock/exec")
        log_file = Path("/mock/log.txt")
        execution_cb = Mock()

        executor = create_terraform_executor(
            sequence_id=TerraformSequenceId.config_init,
            exec_dir=exec_dir,
            log_file=log_file,
            execution_callback=execution_cb,
        )

        self.assertEqual(executor.exec_dir, exec_dir)
        self.assertEqual(executor.log_file, log_file)

    def test_pass_callbacks_to_executor(self) -> None:
        """Test that callbacks are passed correctly to executor."""
        exec_dir = Path("/mock/exec")
        log_file = Path("/mock/log.txt")
        execution_cb = Mock()

        executor = create_terraform_executor(
            sequence_id=TerraformSequenceId.config_init,
            exec_dir=exec_dir,
            log_file=log_file,
            execution_callback=execution_cb,
        )

        self.assertIs(executor._execution_callback, execution_cb)

    def test_return_a_supervisor_executor_for_all_terraform_sequence_id(self) -> None:
        """Test that SupervisedExecutor is returned for all sequence IDs."""
        exec_dir = Path("/mock/exec")
        log_file = Path("/mock/log.txt")
        execution_cb = Mock()

        for sequence_id in TerraformSequenceId:
            executor = create_terraform_executor(
                sequence_id=sequence_id,
                exec_dir=exec_dir,
                log_file=log_file,
                execution_callback=execution_cb,
            )
            self.assertIsInstance(executor, SupervisedExecutor)

    def test_return_executor_with_default_phase_for_config_init(self) -> None:
        """Test config_init creates executor with correct default phase."""
        exec_dir = Path("/mock/exec")
        log_file = Path("/mock/log.txt")
        execution_cb = Mock()

        executor = create_terraform_executor(
            sequence_id=TerraformSequenceId.config_init,
            exec_dir=exec_dir,
            log_file=log_file,
            execution_callback=execution_cb,
        )

        self.assertGreaterEqual(len(executor._default_phase.label), 1)
        self.assertEqual(len(executor._declared_phases), 0)

    def test_return_executor_with_default_phase_for_config_plan(self) -> None:
        """Test config_plan creates executor with correct default phase."""
        exec_dir = Path("/mock/exec")
        log_file = Path("/mock/log.txt")
        execution_cb = Mock()

        executor = create_terraform_executor(
            sequence_id=TerraformSequenceId.config_plan,
            exec_dir=exec_dir,
            log_file=log_file,
            execution_callback=execution_cb,
        )

        self.assertGreaterEqual(len(executor._default_phase.label), 1)
        self.assertEqual(len(executor._declared_phases), 0)

    def test_config_sequence_executors_have_consistent_weights(self) -> None:
        """Test that config_init and config_plan have consistent weight distribution."""
        exec_dir = Path("/mock/exec")
        log_file = Path("/mock/log.txt")
        execution_cb = Mock()

        init_executor = create_terraform_executor(
            sequence_id=TerraformSequenceId.config_init,
            exec_dir=exec_dir,
            log_file=log_file,
            execution_callback=execution_cb,
        )

        plan_executor = create_terraform_executor(
            sequence_id=TerraformSequenceId.config_plan,
            exec_dir=exec_dir,
            log_file=log_file,
            execution_callback=execution_cb,
        )

        # init rewards are correct
        self.assertAlmostEqual(init_executor._accumulated_reward, 0)
        self.assertAlmostEqual(init_executor.end_reward, 20)

        # config rewards are correct
        self.assertAlmostEqual(plan_executor._accumulated_reward, 20)
        self.assertAlmostEqual(plan_executor.end_reward, 100)

    def test_return_executor_with_default_phase_for_up_apply(self) -> None:
        """Test up_apply creates executor with correct default phase."""
        exec_dir = Path("/mock/exec")
        log_file = Path("/mock/log.txt")
        execution_cb = Mock()

        executor = create_terraform_executor(
            sequence_id=TerraformSequenceId.up_apply,
            exec_dir=exec_dir,
            log_file=log_file,
            execution_callback=execution_cb,
        )

        self.assertGreaterEqual(len(executor._default_phase.label), 1)
        self.assertEqual(len(executor._declared_phases), 0)

    def test_return_executor_with_a_default_and_a_declared_phase_for_down_destroy(self) -> None:
        """Test down_destroy creates executor with default phase and one declared phase."""
        exec_dir = Path("/mock/exec")
        log_file = Path("/mock/log.txt")
        execution_cb = Mock()

        executor = create_terraform_executor(
            sequence_id=TerraformSequenceId.down_destroy,
            exec_dir=exec_dir,
            log_file=log_file,
            execution_callback=execution_cb,
        )

        self.assertGreaterEqual(len(executor._default_phase.label), 1)
        self.assertEqual(len(executor._declared_phases), 1)
        self.assertGreaterEqual(len(executor._declared_phases[0].label), 1)

    def test_down_destroy_executor_declared_phase_full_reward_in_less_than_hundred(self) -> None:
        """Test down_destroy declared phase has weight less than 100."""
        exec_dir = Path("/mock/exec")
        log_file = Path("/mock/log.txt")
        execution_cb = Mock()

        executor = create_terraform_executor(
            sequence_id=TerraformSequenceId.down_destroy,
            exec_dir=exec_dir,
            log_file=log_file,
            execution_callback=execution_cb,
        )

        self.assertLess(executor._declared_phases[0].full_reward, 100)


class TestCreateTerraformExecutorWithManifest(unittest.TestCase):
    """Test cases for create_terraform_executor factory function with manifest."""

    manifest: JupyterDeployManifestV1
    manifest_parsed_content: Any

    @classmethod
    def setUpClass(cls) -> None:
        """Load the default manifest."""
        manifest_path = Path(__file__).parent.parent.parent / "mock_manifest.yaml"
        with open(manifest_path) as f:
            cls.manifest_parsed_content = yaml.safe_load(f)
        cls.manifest = JupyterDeployManifestV1(**cls.manifest_parsed_content)

    def test_return_manifest_based_executor_for_config_init(self) -> None:
        """Test config_init uses manifest configuration."""
        exec_dir = Path("/mock/exec")
        log_file = Path("/mock/log.txt")
        execution_cb = Mock()

        executor = create_terraform_executor(
            sequence_id=TerraformSequenceId.config_init,
            exec_dir=exec_dir,
            log_file=log_file,
            execution_callback=execution_cb,
            manifest=self.manifest,
        )

        # Manifest specifies label and pattern for config.terraform-init
        self.assertEqual(executor._default_phase.label, "Configuring terraform dependencies")

    def test_return_manifest_based_executor_for_config_plan(self) -> None:
        """Test config_plan uses manifest configuration."""
        exec_dir = Path("/mock/exec")
        log_file = Path("/mock/log.txt")
        execution_cb = Mock()

        executor = create_terraform_executor(
            sequence_id=TerraformSequenceId.config_plan,
            exec_dir=exec_dir,
            log_file=log_file,
            execution_callback=execution_cb,
            manifest=self.manifest,
        )

        # Manifest specifies label "Generating plan" for config.terraform-plan
        self.assertEqual(executor._default_phase.label, "Generating plan")

    def test_return_manifest_based_executor_for_up_apply(self) -> None:
        """Test up_apply uses manifest configuration with phases."""
        exec_dir = Path("/mock/exec")
        log_file = Path("/mock/log.txt")
        execution_cb = Mock()

        executor = create_terraform_executor(
            sequence_id=TerraformSequenceId.up_apply,
            exec_dir=exec_dir,
            log_file=log_file,
            execution_callback=execution_cb,
            manifest=self.manifest,
        )

        # Manifest specifies label "Mutating resources" for up.terraform-apply
        self.assertGreaterEqual(executor._default_phase.label, "Mutating resources")

        # Manifest specifies 1 phase with full reward = 40 for up.terraform-apply
        self.assertEqual(len(executor._declared_phases), 1)
        self.assertGreaterEqual(len(executor._declared_phases[0].label), 1)
        self.assertAlmostEqual(executor._declared_phases[0].full_reward, 40)

    def test_return_manifest_based_executor_for_down_apply(self) -> None:
        """Test down_destroy uses manifest configuration."""
        exec_dir = Path("/mock/exec")
        log_file = Path("/mock/log.txt")
        execution_cb = Mock()

        executor = create_terraform_executor(
            sequence_id=TerraformSequenceId.down_destroy,
            exec_dir=exec_dir,
            log_file=log_file,
            execution_callback=execution_cb,
            manifest=self.manifest,
        )

        # Manifest specifies label "Evaluating resources to destroy" for down.terraform-destroy
        self.assertEqual(executor._default_phase.label, "Evaluating resources to destroy")

        # Manifest specifies 1 phase with full reward = 100 for down.terraform-destroy
        self.assertEqual(len(executor._declared_phases), 1)
        self.assertGreaterEqual(len(executor._declared_phases[0].label), 1)
        self.assertAlmostEqual(executor._declared_phases[0].full_reward, 100)

    def test_return_manifest_based_executor_with_overriden_estimate_for_up_apply(self) -> None:
        """Test up_apply with plan metadata overrides estimate dynamically."""
        exec_dir = Path("/mock/exec")
        log_file = Path("/mock/log.txt")
        execution_cb = Mock()

        # Create plan metadata with specific counts
        plan_metadata = TerraformPlanMetadata(to_add=10, to_change=10, to_destroy=2)

        executor = create_terraform_executor(
            sequence_id=TerraformSequenceId.up_apply,
            exec_dir=exec_dir,
            log_file=log_file,
            execution_callback=execution_cb,
            manifest=self.manifest,
            plan_metadata=plan_metadata,
        )

        # Manifest specifies "progress-events-estimate-dynamic-source": "plan.to_update"
        # plan.to_update = to_add + to_change = 10 + 10 = 20
        # default phase weights 60% (since declared phase weights 40%)
        # Reward per event should be 60 / 20 = 3 if using manifest (expected)
        # If using default, reward per event should be 60 / 10 = 6
        self.assertAlmostEqual(executor._default_phase._reward_per_event, 3)
