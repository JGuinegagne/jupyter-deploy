"""Terraform implementation of the `down` handler."""

from pathlib import Path
from subprocess import CalledProcessError

from jupyter_deploy import cmd_utils, fs_utils
from jupyter_deploy.engine.engine_down import EngineDownHandler
from jupyter_deploy.engine.supervised_execution import TerminalHandler
from jupyter_deploy.engine.supervised_execution_callback import ExecutionCallbackInterface
from jupyter_deploy.engine.terraform import tf_outputs, tf_supervised_executor_factory
from jupyter_deploy.engine.terraform.tf_constants import (
    TF_AUTO_APPROVE_CMD_OPTION,
    TF_DESTROY_CMD,
    TF_DESTROY_PRESET_FILENAME,
    TF_ENGINE_DIR,
    TF_PRESETS_DIR,
    TF_RM_FROM_STATE_CMD,
)
from jupyter_deploy.engine.terraform.tf_enums import TerraformSequenceId
from jupyter_deploy.engine.terraform.tf_supervised_execution_callback import (
    TerraformNoopExecutionCallback,
    TerraformSupervisedExecutionCallback,
)
from jupyter_deploy.enum import HistoryEnabledCommandType
from jupyter_deploy.exceptions import DownAutoApproveRequiredError, SupervisedExecutionError
from jupyter_deploy.handlers.command_history_handler import CommandHistoryHandler
from jupyter_deploy.manifest import JupyterDeployManifest


class TerraformDownHandler(EngineDownHandler):
    """Down handler implementation for terraform projects."""

    def __init__(
        self,
        project_path: Path,
        project_manifest: JupyterDeployManifest,
        command_history_handler: CommandHistoryHandler,
        terminal_handler: TerminalHandler,
    ) -> None:
        outputs_handler = tf_outputs.TerraformOutputsHandler(
            project_path=project_path,
            project_manifest=project_manifest,
        )

        super().__init__(project_path=project_path, project_manifest=project_manifest, output_handler=outputs_handler)
        self.engine_dir_path = project_path / TF_ENGINE_DIR
        self.command_history_handler = command_history_handler
        self.terminal_handler = terminal_handler
        self._log_file: Path | None = None

    def _get_destroy_tfvars_file_path(self) -> Path:
        return self.engine_dir_path / TF_PRESETS_DIR / TF_DESTROY_PRESET_FILENAME

    def _destroy_tfvars_file_exists(self) -> bool:
        """Return True if special presets for destroy exists."""
        tfvars_file_path = self._get_destroy_tfvars_file_path()
        return fs_utils.file_exists(tfvars_file_path)

    def destroy(self, auto_approve: bool = False) -> None:
        # Create log file using command history handler
        self._log_file = self.command_history_handler.create_log_file(HistoryEnabledCommandType.DOWN)

        # first handle persisting resources: attempt to remove them from state
        persisting_resources = self.get_persisting_resources()
        if persisting_resources:
            # Abort if the user has not set the `-y` flag in `jd down`
            if not auto_approve:
                raise DownAutoApproveRequiredError(persisting_resources)

            self.terminal_handler.info("Running dry-run to detach resources from terraform state...")

            dryrun_rm_cmd = TF_RM_FROM_STATE_CMD.copy()
            dryrun_rm_cmd.append("--dry-run")
            dryrun_rm_cmd.extend([pr for pr in persisting_resources])
            try:
                cmd_utils.run_cmd_and_capture_output(dryrun_rm_cmd, exec_dir=self.engine_dir_path)
            except CalledProcessError as e:
                self.terminal_handler.warning("Error performing dry-run of removing resources from Terraform state.")
                self.terminal_handler.warning(f"Details: {e}")
                return

            self.terminal_handler.success("Dry-run succeeded.")

            # otherwise, remove the resources from the state using supervised execution
            self.terminal_handler.info("Removing persisting resources from the Terraform state...")

            rm_cmd = TF_RM_FROM_STATE_CMD.copy()
            rm_cmd.extend([pr for pr in persisting_resources])

            # Choose callback: full featured with progress tracking, or no-op for pass-through mode
            rm_callback: ExecutionCallbackInterface
            if self.terminal_handler.is_pass_through():
                rm_callback = TerraformNoopExecutionCallback()
            else:
                rm_callback = TerraformSupervisedExecutionCallback(
                    terminal_handler=self.terminal_handler,
                    sequence_id=TerraformSequenceId.down_rm_state,
                )

            rm_executor = tf_supervised_executor_factory.create_terraform_executor(
                sequence_id=TerraformSequenceId.down_rm_state,
                exec_dir=self.engine_dir_path,
                log_file=self._log_file,
                execution_callback=rm_callback,
                manifest=self.project_manifest,
            )

            rm_retcode = rm_executor.execute(rm_cmd)
            if rm_retcode != 0:
                raise SupervisedExecutionError(
                    command="down",
                    retcode=rm_retcode,
                    message="Error removing persisting resources from Terraform state.",
                )

            self.terminal_handler.success("Removed the persisting resources from the Terraform state.")

        # second: run terraform destroy with supervised execution
        destroy_cmd = TF_DESTROY_CMD.copy()
        if auto_approve:
            destroy_cmd.append(TF_AUTO_APPROVE_CMD_OPTION)
        if self._destroy_tfvars_file_exists():
            # jupyter-deploy does not record sensitive values by default,
            # however 'terraform destroy' believes it needs them (not necessarily true).
            # Allow templates to provide mock values in order to avoid prompting the user.
            destroy_tfvars_path = self._get_destroy_tfvars_file_path()
            destroy_cmd.append(f"-var-file={destroy_tfvars_path.absolute()}")

        # Choose callback: full featured with progress tracking, or no-op for pass-through mode
        destroy_callback: ExecutionCallbackInterface
        if self.terminal_handler.is_pass_through():
            destroy_callback = TerraformNoopExecutionCallback()
        else:
            destroy_callback = TerraformSupervisedExecutionCallback(
                terminal_handler=self.terminal_handler,
                sequence_id=TerraformSequenceId.down_destroy,
            )

        # Create executor for terraform destroy
        destroy_executor = tf_supervised_executor_factory.create_terraform_executor(
            sequence_id=TerraformSequenceId.down_destroy,
            exec_dir=self.engine_dir_path,
            log_file=self._log_file,
            execution_callback=destroy_callback,
            manifest=self.project_manifest,
        )

        # Execute terraform destroy
        destroy_retcode = destroy_executor.execute(destroy_cmd)
        if destroy_retcode != 0:
            raise SupervisedExecutionError(
                command="down",
                retcode=destroy_retcode,
                message="Error destroying Terraform infrastructure.",
            )

        # Success - cleanup old logs
        self.command_history_handler.clear_logs(HistoryEnabledCommandType.DOWN)
