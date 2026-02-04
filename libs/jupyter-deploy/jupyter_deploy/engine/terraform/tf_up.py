"""Terraform implementation of the `up` handler."""

from pathlib import Path

from jupyter_deploy.engine.engine_up import EngineUpHandler
from jupyter_deploy.engine.enum import EngineType
from jupyter_deploy.engine.supervised_execution import CompletionContext, ExecutionError, TerminalHandler
from jupyter_deploy.engine.supervised_execution_callback import ExecutionCallbackInterface
from jupyter_deploy.engine.terraform import tf_supervised_executor_factory
from jupyter_deploy.engine.terraform.tf_constants import (
    TF_APPLY_CMD,
    TF_AUTO_APPROVE_CMD_OPTION,
    TF_DEFAULT_PLAN_FILENAME,
    TF_ENGINE_DIR,
)
from jupyter_deploy.engine.terraform.tf_enums import TerraformSequenceId
from jupyter_deploy.engine.terraform.tf_supervised_execution_callback import (
    TerraformNoopExecutionCallback,
    TerraformSupervisedExecutionCallback,
)
from jupyter_deploy.handlers.command_history_handler import CommandHistoryHandler
from jupyter_deploy.manifest import JupyterDeployManifest


class TerraformUpHandler(EngineUpHandler):
    """Up handler implementation for terraform projects."""

    def __init__(
        self,
        project_path: Path,
        project_manifest: JupyterDeployManifest,
        command_history_handler: CommandHistoryHandler,
        terminal_handler: TerminalHandler | None = None,
    ) -> None:
        self.engine_dir_path = project_path / TF_ENGINE_DIR
        super().__init__(project_path=project_path, engine=EngineType.TERRAFORM, engine_dir_path=self.engine_dir_path)
        self.project_manifest = project_manifest
        self.command_history_handler = command_history_handler
        self.terminal_handler = terminal_handler
        self._log_file: Path | None = None

    def get_default_config_filename(self) -> str:
        return TF_DEFAULT_PLAN_FILENAME

    def apply(self, config_file_path: Path, auto_approve: bool = False) -> CompletionContext | None:
        # Create log file using command history handler
        self._log_file = self.command_history_handler.create_log_file("up")

        # Build terraform apply command
        apply_cmd = TF_APPLY_CMD.copy()
        if auto_approve:
            apply_cmd.append(TF_AUTO_APPROVE_CMD_OPTION)
        apply_cmd.append(str(config_file_path.absolute()))

        # Choose callback: full featured with progress tracking, or no-op for verbose mode
        apply_callback: ExecutionCallbackInterface
        if self.terminal_handler:
            apply_callback = TerraformSupervisedExecutionCallback(
                terminal_handler=self.terminal_handler,
                sequence_id=TerraformSequenceId.up_apply,
            )
        else:
            apply_callback = TerraformNoopExecutionCallback()

        # Create executor for terraform apply
        apply_executor = tf_supervised_executor_factory.create_terraform_executor(
            sequence_id=TerraformSequenceId.up_apply,
            exec_dir=self.engine_dir_path,
            log_file=self._log_file,
            execution_callback=apply_callback,
            manifest=self.project_manifest,
        )

        # Execute terraform apply
        apply_retcode = apply_executor.execute(apply_cmd)
        if apply_retcode != 0:
            raise ExecutionError(
                command="up",
                retcode=apply_retcode,
                message="Error applying Terraform plan.",
            )

        # Return completion context from callback
        return apply_callback.get_completion_context()
