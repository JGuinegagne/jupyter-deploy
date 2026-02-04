"""Terraform implementation of the `config` handler."""

from pathlib import Path
from subprocess import CalledProcessError
from typing import Any

from pydantic import ValidationError

from jupyter_deploy import cmd_utils, fs_utils
from jupyter_deploy.engine.engine_config import (
    EngineConfigHandler,
    ReadConfigurationError,
    WriteConfigurationError,
)
from jupyter_deploy.engine.enum import EngineType
from jupyter_deploy.engine.supervised_execution import CompletionContext, ExecutionError, TerminalHandler
from jupyter_deploy.engine.supervised_execution_callback import ExecutionCallbackInterface
from jupyter_deploy.engine.terraform import (
    tf_plan,
    tf_plan_metadata,
    tf_supervised_executor_factory,
    tf_vardefs,
    tf_variables,
)
from jupyter_deploy.engine.terraform.tf_constants import (
    TF_DEFAULT_PLAN_FILENAME,
    TF_ENGINE_DIR,
    TF_INIT_CMD,
    TF_PARSE_PLAN_CMD,
    TF_PLAN_CMD,
    TF_PLAN_METADATA_FILENAME,
    TF_PRESETS_DIR,
    get_preset_filename,
)
from jupyter_deploy.engine.terraform.tf_enums import TerraformSequenceId
from jupyter_deploy.engine.terraform.tf_supervised_execution_callback import (
    TerraformNoopExecutionCallback,
    TerraformSupervisedExecutionCallback,
)
from jupyter_deploy.engine.vardefs import TemplateVariableDefinition
from jupyter_deploy.handlers.command_history_handler import CommandHistoryHandler
from jupyter_deploy.manifest import JupyterDeployManifest


class TerraformConfigHandler(EngineConfigHandler):
    """Config handler implementation for terraform projects."""

    def __init__(
        self,
        project_path: Path,
        project_manifest: JupyterDeployManifest,
        command_history_handler: CommandHistoryHandler,
        output_filename: str | None = None,
        terminal_handler: TerminalHandler | None = None,
    ) -> None:
        variables_handler = tf_variables.TerraformVariablesHandler(
            project_path=project_path, project_manifest=project_manifest
        )
        super().__init__(
            project_path=project_path,
            project_manifest=project_manifest,
            engine=EngineType.TERRAFORM,
            variables_handler=variables_handler,
            command_history_handler=command_history_handler,
        )
        self.engine_dir_path = project_path / TF_ENGINE_DIR
        self.plan_out_path = self.engine_dir_path / (output_filename or TF_DEFAULT_PLAN_FILENAME)
        self.terminal_handler = terminal_handler
        self._log_file: Path | None = None

        # use a different name from parent attribute to not confuse mypy
        self.tf_variables_handler = variables_handler

    def _get_preset_path(self, preset_name: str) -> Path:
        return self.engine_dir_path / TF_PRESETS_DIR / get_preset_filename(preset_name)

    def has_recorded_variables(self) -> bool:
        file_path = self.tf_variables_handler.get_recorded_variables_filepath()
        return fs_utils.file_exists(file_path=file_path)

    def verify_preset_exists(self, preset_name: str) -> bool:
        file_path = self._get_preset_path(preset_name)
        return fs_utils.file_exists(file_path=file_path)

    def list_presets(self) -> list[str]:
        presets = ["none"]

        # Get all files matching the pattern
        matching_filenames = fs_utils.find_matching_filenames(
            dir_path=self.engine_dir_path / TF_PRESETS_DIR,
            file_pattern="defaults-*.tfvars",
        )
        presets.extend([n[len("defaults-") : -len(".tfvars")] for n in matching_filenames])
        return sorted(presets)

    def reset_recorded_variables(self) -> None:
        self.variables_handler.reset_recorded_variables()

    def reset_recorded_secrets(self) -> None:
        self.variables_handler.reset_recorded_secrets()

    def configure(
        self, preset_name: str | None = None, variable_overrides: dict[str, TemplateVariableDefinition] | None = None
    ) -> CompletionContext | None:
        # Create log file using command history handler
        self._log_file = self.command_history_handler.create_log_file("config")

        # 1/ run terraform init with supervised execution
        # Note that it is safe to run several times, see ``terraform init --help``:
        # ``init`` command is always safe to run multiple times. Though subsequent runs
        # may give errors, this command will never delete your configuration or
        # state.

        # Choose callback: full featured with progress tracking, or no-op for verbose mode
        init_callback: ExecutionCallbackInterface
        if self.terminal_handler:
            init_callback = TerraformSupervisedExecutionCallback(
                terminal_handler=self.terminal_handler,
                sequence_id=TerraformSequenceId.config_init,
            )
        else:
            init_callback = TerraformNoopExecutionCallback()
        init_executor = tf_supervised_executor_factory.create_terraform_executor(
            sequence_id=TerraformSequenceId.config_init,
            exec_dir=self.engine_dir_path,
            log_file=self._log_file,
            execution_callback=init_callback,
            manifest=self.project_manifest,
        )

        init_retcode = init_executor.execute(TF_INIT_CMD.copy())
        if init_retcode != 0:
            raise ExecutionError(
                command="config",
                retcode=init_retcode,
                message="Error initializing Terraform project.",
            )

        # 2/ prepare to run terraform plan and save output with ``terraform plan PATH``
        plan_cmds = TF_PLAN_CMD.copy()

        # 2.1/ output plan to disk
        plan_cmds.append(f"-out={self.plan_out_path.absolute()}")

        # 2.2/ sync variables.yaml -> tfvars and create the .tfvars files if necessary
        self.variables_handler.sync_engine_varfiles_with_project_variables_config()

        # 2.3/ using preset
        if preset_name:
            # here we assume the preset path was verified earlier
            base_preset_path = self._get_preset_path(preset_name)

            # if a user i/ runs `jd init`, ii/ set values in variables.yaml,
            # iii/ calls `jd config`, then the `jdinputs.auto.tfvars` file
            # then the preset values may take precedence over the values specified
            # in variables.yaml, which is not desirable.
            filtered_preset_path = self.tf_variables_handler.create_filtered_preset_file(base_preset_path)
            plan_cmds.append(f"-var-file={filtered_preset_path.absolute()}")

        # 2.4/ pass variable overrides
        if variable_overrides:
            for var_def in variable_overrides.values():
                var_option = tf_vardefs.to_tf_var_option(var_def)
                plan_cmds.extend(var_option)

        # 2.5/ call terraform plan with supervised execution
        plan_callback: ExecutionCallbackInterface
        if self.terminal_handler:
            plan_callback = TerraformSupervisedExecutionCallback(
                terminal_handler=self.terminal_handler,
                sequence_id=TerraformSequenceId.config_plan,
            )
        else:
            plan_callback = TerraformNoopExecutionCallback()

        plan_executor = tf_supervised_executor_factory.create_terraform_executor(
            sequence_id=TerraformSequenceId.config_plan,
            exec_dir=self.engine_dir_path,
            log_file=self._log_file,
            execution_callback=plan_callback,
            manifest=self.project_manifest,
        )

        plan_retcode = plan_executor.execute(plan_cmds)
        if plan_retcode != 0:
            raise ExecutionError(
                command="config",
                retcode=plan_retcode,
                message="Error generating Terraform plan.",
            )

        # Success - cleanup old logs
        self.command_history_handler.clear_logs("config")

        # Return completion context from callback
        return plan_callback.get_completion_context()

    def record(self, record_vars: bool = False, record_secrets: bool = False) -> None:
        """Record variables and secrets from the plan file.

        Raises:
            ReadConfigurationError: If reading or parsing the plan fails.
            WriteConfigurationError: If writing configuration files fails.
        """
        cmds = TF_PARSE_PLAN_CMD + [f"{self.plan_out_path.absolute()}"]

        # Parse the plan (needed for both metadata and variables/secrets)
        try:
            plan_content_str = cmd_utils.run_cmd_and_capture_output(cmds, exec_dir=self.engine_dir_path)
        except CalledProcessError as e:
            raise ReadConfigurationError(self.plan_out_path.name) from e

        # Parse JSON once for efficiency
        try:
            plan = tf_plan.extract_plan(plan_content_str)
        except (ValueError, ValidationError) as e:
            raise ReadConfigurationError(self.plan_out_path.name) from e

        # Extract and save plan metadata (resource counts) - always done
        metadata_path = self.engine_dir_path / TF_PLAN_METADATA_FILENAME
        try:
            to_add, to_change, to_destroy = tf_plan.extract_resource_counts_from_plan(plan)
            metadata = tf_plan_metadata.TerraformPlanMetadata(
                to_add=to_add,
                to_change=to_change,
                to_destroy=to_destroy,
            )
            tf_plan_metadata.save_plan_metadata(metadata, metadata_path)
        except (ValueError, ValidationError) as e:
            raise WriteConfigurationError(str(metadata_path)) from e

        # Early return if we don't need to record vars/secrets
        if not record_vars and not record_secrets:
            return

        # Extract variables and secrets for recording
        try:
            variables, secrets = tf_plan.extract_variables_from_plan(plan)
        except (ValueError, ValidationError) as e:
            raise ReadConfigurationError(self.plan_out_path.name) from e

        vardefs: dict[str, Any] = {}

        if record_vars:
            vars_file_path = self.tf_variables_handler.get_recorded_variables_filepath()
            vars_file_lines = ["# generated by jupyter-deploy config command\n"]
            vars_file_lines.extend(tf_plan.format_plan_variables(variables))
            fs_utils.write_inline_file_content(vars_file_path, vars_file_lines)

            vardefs.update({k: v.value for k, v in variables.items()})

        if record_secrets:
            secrets_file_path = self.tf_variables_handler.get_recorded_secrets_filepath()
            secrets_file_lines = ["# generated by jupyter-deploy config command\n"]
            secrets_file_lines.append("# do NOT commit this file\n")
            secrets_file_lines.extend(tf_plan.format_plan_variables(secrets))
            fs_utils.write_inline_file_content(secrets_file_path, secrets_file_lines)

            vardefs.update({k: v.value for k, v in secrets.items()})

        if record_vars or record_secrets:
            self.variables_handler.sync_project_variables_config(vardefs)
