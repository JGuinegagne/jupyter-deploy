"""Terraform-specific supervised execution with progress tracking."""

from pathlib import Path

from jupyter_deploy.engine.supervised_execution import LogCallback, ProgressCallback
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
    progress_callback: ProgressCallback,
    log_callback: LogCallback,
    manifest: JupyterDeployManifest | None = None,
    plan_metadata: TerraformPlanMetadata | None = None,
) -> SupervisedExecutor:
    """Return a SupervisedExecutor configured for the specified sequence.

    Args:
        sequence_id: Command sequence ID
        exec_dir: Working directory for terraform execution
        log_file: Path where logs should be written
        progress_callback: Callback for progress updates
        log_callback: Callback for live log line updates
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
    phase_sequence_weight: int = 100
    phase_sequence_start: int = 0

    if sequence_id == TerraformSequenceId.config_init:
        # Init: no event counting, relies on explicit phases
        fallback_default_phase_config = JupyterDeploySupervisedExecutionDefaultPhaseV1(
            label="Configuring terraform dependencies",
            **{"progress-pattern": "Initializing", "progress-events-estimate": 5},
        )
        phase_sequence_weight = 20

    elif sequence_id == TerraformSequenceId.config_plan:
        # Plan: count read/refresh events using estimates
        fallback_default_phase_config = JupyterDeploySupervisedExecutionDefaultPhaseV1(
            label="Configuring terraform dependencies",
            **{
                "progress-pattern": r"(Read complete after|Refreshing state\.\.\. \[id=)",
                "progress-events-estimate": 10,
            },
        )
        phase_sequence_start = 20
        phase_sequence_weight = 80

    elif sequence_id == TerraformSequenceId.up_apply:
        # Apply: count resource creation/modification events
        # Use plan.to_update dynamically if plan_metadata is available
        fallback_default_phase_config = JupyterDeploySupervisedExecutionDefaultPhaseV1(
            label="Configuring terraform dependencies",
            **{
                "progress-pattern": (
                    r"(Creation complete after|Modifications complete after|Refreshing state\.\.\. \[id=)"
                ),
                "progress-events-estimate-dynamic-source": "plan.to_update",
            },
        )

    elif sequence_id == TerraformSequenceId.down_destroy:
        # Destroy: count resource destruction events
        fallback_default_phase_config = JupyterDeploySupervisedExecutionDefaultPhaseV1(
            label="Evaluating resources to destroy",
            **{
                "progress-pattern": r"(Read complete after|Refreshing state\.\.\. \[id=)",
                "progress-events-estimate": 50,
            },
        )
        fallback_phase_configs = [
            JupyterDeploySupervisedExecutionPhaseV1(
                label="Destroying resources",
                weight=80,
                enter_pattern=r"Plan: \d+ to add, \d+ to change, (\d+) to destroy\.",
                progress_events_estimate_capture_group=1,  # Extract destroy count from capture group
                progress_pattern="Destruction complete after",
            ),
        ]
    else:
        raise NotImplementedError(f"Unknown sequence_id: {sequence_id}")

    # Create actual phases
    phase_configs = manifest_phases_configs or fallback_phase_configs
    phases: list[SupervisedPhase] = []
    for phase_config in phase_configs:
        phases.append(SupervisedPhase(config=phase_config))

    # Create default phase with dynamic override if configured
    effective_default_weight = max(100 - sum([p.weight for p in phases]), 0)
    default_phase_config = manifest_default_phase_config or fallback_default_phase_config

    # Extract override from plan metadata if dynamic source is configured
    override_estimate: int | None = None
    if plan_metadata and default_phase_config.progress_events_estimate_dynamic_source:
        source_enum = TerraformPlanMetadataSource.from_string(
            default_phase_config.progress_events_estimate_dynamic_source
        )
        if source_enum:
            override_estimate = plan_metadata.get_value(source_enum)

    default_phase = SupervisedDefaultPhase(
        config=default_phase_config, weight=effective_default_weight, override_estimate=override_estimate
    )

    # Instantiates the supervised executor
    return SupervisedExecutor(
        exec_dir=exec_dir,
        log_file=log_file,
        progress_callback=progress_callback,
        log_callback=log_callback,
        default_phase=default_phase,
        phases=phases,
        phase_sequence_weight=phase_sequence_weight,
        phase_sequence_percentage_start=phase_sequence_start,
    )
