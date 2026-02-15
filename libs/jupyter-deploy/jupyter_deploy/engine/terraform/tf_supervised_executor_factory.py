"""Terraform-specific supervised execution with progress tracking."""

from pathlib import Path

from jupyter_deploy.engine.supervised_execution_callback import ExecutionCallbackInterface
from jupyter_deploy.engine.supervised_executor import SupervisedExecutor
from jupyter_deploy.engine.supervised_phase import SupervisedDefaultPhase, SupervisedPhase

# Import constants for sequence IDs
from jupyter_deploy.engine.terraform.tf_constants import TerraformPlanMetadataSource, TerraformSequenceId
from jupyter_deploy.engine.terraform.tf_plan_metadata import TerraformPlanMetadata
from jupyter_deploy.manifest import (
    JupyterDeployManifest,
    JupyterDeploySupervisedExecutionDefaultPhaseV1,
    JupyterDeploySupervisedExecutionPhaseV1,
)


def create_terraform_executor(
    sequence_id: TerraformSequenceId,
    exec_dir: Path,
    log_file: Path,
    execution_callback: ExecutionCallbackInterface,
    manifest: JupyterDeployManifest | None = None,
    plan_metadata: TerraformPlanMetadata | None = None,
) -> SupervisedExecutor:
    """Return a SupervisedExecutor configured for the specified sequence.

    Applies the configuration defined in the project manifest, or
    its own fallbacks if the manifest does not declare a configuration for
    this specific sequence_id.

    Args:
        sequence_id: Command sequence ID
        exec_dir: Working directory for terraform execution
        log_file: Path where logs should be written
        execution_callback: Callback for execution events (progress, logs)
        manifest: Optional manifest to extract command-specific configuration
        plan_metadata: Optional plan metadata for dynamic progress estimate extraction

    Raises:
        NotImplementedError: If sequence_id is not recognized
    """
    # Extract command config from manifest if available
    command_config = sequence_id.get_command_config(manifest) if manifest else None

    manifest_default_phase_config: JupyterDeploySupervisedExecutionDefaultPhaseV1 | None = (
        command_config.default_phase if command_config else None
    )
    manifest_phases_configs: list[JupyterDeploySupervisedExecutionPhaseV1] | None = (
        command_config.phases if command_config else None
    )

    fallback_default_phase_config: JupyterDeploySupervisedExecutionDefaultPhaseV1
    fallback_phase_configs: list[JupyterDeploySupervisedExecutionPhaseV1] = []
    end_reward: int = 100
    start_reward: int = 0

    if sequence_id == TerraformSequenceId.config_init:
        # Init: count initialization events (backend, modules, plugins) and provider installations
        fallback_default_phase_config = JupyterDeploySupervisedExecutionDefaultPhaseV1(
            label="Configuring terraform",
            **{
                "progress-pattern": r"(Initializing|Installed|Terraform has been successfully initialized)",
                "progress-events-estimate": 8,
            },
        )
        end_reward = 20

    elif sequence_id == TerraformSequenceId.config_plan:
        # Plan: count read/refresh events only
        fallback_default_phase_config = JupyterDeploySupervisedExecutionDefaultPhaseV1(
            label="Reading data sources",
            **{
                "progress-pattern": r"(Read complete after|Refreshing state)",
                "progress-events-estimate": 50,
            },
        )
        start_reward = 20
        end_reward = 100

    elif sequence_id == TerraformSequenceId.up_apply:
        # Apply: count resource creation/modification/destruction events
        # Use plan.to_mutate dynamically if plan_metadata is available
        fallback_default_phase_config = JupyterDeploySupervisedExecutionDefaultPhaseV1(
            label="Mutating resources",
            **{
                "progress-pattern": (
                    r"(Creation complete after|Modifications complete after|"
                    r"Destruction complete after|Refreshing state)"
                ),
                "progress-events-estimate-dynamic-source": "plan.to_mutate",
            },
        )

    elif sequence_id == TerraformSequenceId.down_rm_state:
        # State removal: simple operation with minimal progress tracking
        # Takes 5% of the overall down progress (0-5)
        fallback_default_phase_config = JupyterDeploySupervisedExecutionDefaultPhaseV1(
            label="Persisting resources",
            **{
                "progress-pattern": r"(Successfully removed|Removed)",
            },
        )
        end_reward = 5

    elif sequence_id == TerraformSequenceId.down_destroy:
        # Destroy: count resource destruction events
        # Takes 95% of the overall down progress (5-100)
        fallback_default_phase_config = JupyterDeploySupervisedExecutionDefaultPhaseV1(
            label="Planning",
            **{
                "progress-pattern": r"(Read complete after|Refreshing state\.\.\. \[id=)",
                "progress-events-estimate": 50,
            },
        )
        fallback_phase_configs = [
            JupyterDeploySupervisedExecutionPhaseV1(
                label="Destroying resources",
                weight=80,
                **{
                    "enter-pattern": r"Plan:(?:\x1b\[[0-9;]*m)*\s+\d+ to add, \d+ to change, (\d+) to destroy\.",
                    "progress-events-estimate-capture-group": 1,  # Extract destroy count from capture group
                    "progress-pattern": r"Destruction complete after",
                },
            ),
        ]
        start_reward = 5
        end_reward = 100
    else:
        raise NotImplementedError(f"Unknown sequence_id: {sequence_id}")

    # Scale factor for reward caclulation
    scale_factor: float = (end_reward - start_reward) / 100

    # Create actual phases
    # Use manifest phases if manifest defines command config, otherwise use fallback
    phase_configs = manifest_phases_configs or [] if command_config is not None else fallback_phase_configs

    phases: list[SupervisedPhase] = []
    for phase_config in phase_configs:
        phases.append(SupervisedPhase(config=phase_config, sequence_scale_factor=scale_factor))

    # Create default phase with dynamic override if configured
    default_phase_weight = max(100 - sum([p.config.weight for p in phases]), 0)
    default_phase_reward = default_phase_weight * scale_factor
    default_phase_config = manifest_default_phase_config or fallback_default_phase_config

    # Extract override from plan metadata if dynamic source is configured
    default_phase_estimate_override: int | None = None
    if plan_metadata and default_phase_config.progress_events_estimate_dynamic_source:
        source_enum = TerraformPlanMetadataSource.from_string(
            default_phase_config.progress_events_estimate_dynamic_source
        )
        if source_enum:
            default_phase_estimate_override = plan_metadata.get_value(source_enum)

    default_phase = SupervisedDefaultPhase(
        config=default_phase_config,
        full_reward=default_phase_reward,
        estimate_override=default_phase_estimate_override,
    )

    # Instantiates the supervised executor
    return SupervisedExecutor(
        exec_dir=exec_dir,
        log_file=log_file,
        execution_callback=execution_callback,
        default_phase=default_phase,
        phases=phases,
        start_reward=start_reward,
        end_reward=end_reward,
        prompt_check_chars=":",  # terraform prompts with "Enter a value: "
    )
