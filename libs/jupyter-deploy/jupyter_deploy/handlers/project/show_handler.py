from jupyter_deploy.engine import outdefs
from jupyter_deploy.engine.engine_outputs import EngineOutputsHandler
from jupyter_deploy.engine.engine_variables import EngineVariablesHandler
from jupyter_deploy.engine.enum import EngineType
from jupyter_deploy.engine.terraform import tf_outputs, tf_variables
from jupyter_deploy.engine.vardefs import TemplateVariableDefinition
from jupyter_deploy.exceptions import OutputNotFoundError, VariableNotFoundError
from jupyter_deploy.handlers.base_project_handler import BaseProjectHandler


class ShowHandler(BaseProjectHandler):
    """Handler for retrieving project information."""

    _outputs_handler: EngineOutputsHandler
    _variables_handler: EngineVariablesHandler

    def __init__(self) -> None:
        """Initialize the show handler."""
        super().__init__()

        if self.engine == EngineType.TERRAFORM:
            self._outputs_handler = tf_outputs.TerraformOutputsHandler(
                project_path=self.project_path,
                project_manifest=self.project_manifest,
            )
            self._variables_handler = tf_variables.TerraformVariablesHandler(
                project_path=self.project_path,
                project_manifest=self.project_manifest,
            )
        else:
            raise NotImplementedError(f"ShowHandler implementation not found for engine: {self.engine}")

    def get_template_name(self) -> str:
        """Return the name of the template."""
        return self.project_manifest.template.name

    def get_template_version(self) -> str:
        """Return the version of the template."""
        return self.project_manifest.template.version

    def get_template_engine(self) -> str:
        """Return the engine of template."""
        return self.engine.value

    def get_full_outputs(self) -> dict[str, outdefs.TemplateOutputDefinition]:
        """Return the full dict of output name to output definition."""
        return self._outputs_handler.get_full_project_outputs()

    def get_full_variables(self) -> dict[str, TemplateVariableDefinition]:
        """Return the full dict of project variables to variable definition."""
        self._variables_handler.sync_engine_varfiles_with_project_variables_config()
        return self._variables_handler.get_template_variables()

    def list_output_names(self) -> list[str]:
        """Return the list of output names."""
        outputs = self._outputs_handler.get_full_project_outputs()
        if not outputs:
            raise Exception("No outputs available. This is normal if the project has not been deployed yet.")
        return list(outputs.keys())

    def list_variable_names(self) -> list[str]:
        """Return the list of variable names."""
        self._variables_handler.sync_engine_varfiles_with_project_variables_config()
        variables = self._variables_handler.get_template_variables()
        if not variables:
            raise ValueError("No variables available.")
        return list(variables.keys())

    def get_output_str_value_and_description(self, output_name: str) -> tuple[str, str]:
        """Return a tuple of str(value) and description of a single output.

        Raises:
            OutputNotFoundError: If output name is not found
        """
        outputs = self._outputs_handler.get_full_project_outputs()

        if not outputs:
            raise Exception("No outputs available. This is normal if the project has not been deployed yet.")

        if output_name not in outputs:
            raise OutputNotFoundError(output_name)

        output_def = outputs[output_name]
        description = getattr(output_def, "description", "") or "No description"
        value = str(output_def.value) if hasattr(output_def, "value") and output_def.value is not None else "None"
        return value, description

    def get_variable_str_value_and_description(self, variable_name: str) -> tuple[str, str]:
        """Return a tuple of str(value) and description of a single variable.

        Raises:
            VariableNotFoundError: If variable name is not found
        """
        self._variables_handler.sync_engine_varfiles_with_project_variables_config()
        variables = self._variables_handler.get_template_variables()

        if variable_name not in variables:
            raise VariableNotFoundError(variable_name)

        variable_def = variables[variable_name]
        description = variable_def.get_cli_description()
        value = (
            "****"
            if variable_def.sensitive
            else str(variable_def.assigned_value)
            if hasattr(variable_def, "assigned_value")
            else "None"
        )

        return value, description
