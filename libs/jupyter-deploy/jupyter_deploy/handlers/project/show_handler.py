import typer
from rich.table import Table

from jupyter_deploy.engine.engine_outputs import EngineOutputsHandler
from jupyter_deploy.engine.engine_variables import EngineVariablesHandler
from jupyter_deploy.engine.enum import EngineType
from jupyter_deploy.engine.terraform import tf_outputs, tf_variables
from jupyter_deploy.handlers.base_project_handler import BaseProjectHandler


class ShowHandler(BaseProjectHandler):
    """Handler for displaying project information and outputs."""

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

    def show_project_info(self, show_info: bool = True, show_outputs: bool = True, show_variables: bool = True) -> None:
        """Display comprehensive project information."""
        console = self.get_console()

        if show_info:
            console.line()
            self._show_project_basic_info()
        if show_variables:
            console.line()
            self._show_project_variables()
        if show_outputs:
            console.line()
            self._show_project_outputs()

    def _show_project_basic_info(self) -> None:
        """Display basic project information."""
        console = self.get_console()

        console.print("Jupyter Deploy Project Information", style="bold cyan")
        console.line()

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")

        table.add_row("Project Path", str(self.project_path))
        table.add_row("Engine", self.engine.value)
        table.add_row("Template Name", self.project_manifest.template.name)
        table.add_row("Template Version", self.project_manifest.template.version)

        console.print(table)
        console.line()

    def _show_project_outputs(self) -> None:
        """Display project outputs if they exist."""
        console = self.get_console()
        try:
            outputs = self._outputs_handler.get_full_project_outputs()
        except Exception as e:
            console.print(f":x: Could not retrieve outputs: {str(e)}", style="red")
            console.line()
            return

        if not outputs:
            console.print(":warning: No outputs available.", style="yellow")
            console.print("This is normal if the project has not been deployed yet.", style="yellow")
            console.line()
            return

        console.print("Project Outputs", style="bold cyan")
        console.line()

        output_table = Table(show_header=True, header_style="bold magenta")
        output_table.add_column("Output Name", style="cyan", no_wrap=True)
        output_table.add_column("Value", style="white")
        output_table.add_column("Description", style="dim")

        for output_name, output_def in outputs.items():
            description = getattr(output_def, "description", "") or "No description"
            value = str(output_def.value) if hasattr(output_def, "value") and output_def.value is not None else "N/A"
            output_table.add_row(output_name, value, description)

        console.print(output_table)

    def _show_project_variables(self) -> None:
        """Display project variables based on the values set in 'variables.yaml'."""
        console = self.get_console()
        try:
            self._variables_handler.sync_engine_varfiles_with_project_variables_config()
            variables = self._variables_handler.get_template_variables()
        except Exception as e:
            console.print(f":x: Could not retrieve variables: {str(e)}", style="red")
            return

        if not variables:
            console.print(":x: No variables available.", style="red")
            return

        console.print("Project Variables", style="bold cyan")
        console.line()

        variables_table = Table(show_header=True, header_style="bold magenta")
        variables_table.add_column("Variable Name", style="cyan", no_wrap=True)
        variables_table.add_column("Assigned Value", style="white")
        variables_table.add_column("Description", style="dim")

        for variable_name, variable_def in variables.items():
            description = variable_def.get_cli_description()
            sensitive = variable_def.sensitive
            if not sensitive:
                assigned_value = str(variable_def.assigned_value) if hasattr(variable_def, "assigned_value") else None
            else:
                assigned_value = "****"
            variables_table.add_row(variable_name, assigned_value, description)

        console.print(variables_table)

    def show_single_variable(
        self, variable_name: str, show_description: bool = False, plain_text: bool = False
    ) -> None:
        """Display the value or description of a single variable.

        Args:
            variable_name: The name of the variable to display
            show_description: If True, show description instead of value
            plain_text: If True, output plain text without Rich markup
        """
        console = self.get_console()
        try:
            self._variables_handler.sync_engine_varfiles_with_project_variables_config()
            variables = self._variables_handler.get_template_variables()
        except Exception as e:
            console.print(f":x: Could not retrieve variable '{variable_name}': {str(e)}", style="red")
            raise typer.Exit(code=1) from None

        if variable_name not in variables:
            console.print(f":x: Variable '{variable_name}' not found.", style="red")
            raise typer.Exit(code=1)

        variable_def = variables[variable_name]

        if show_description:
            description = variable_def.get_cli_description()
            if plain_text:
                console.print(description)
            else:
                console.print(f"[bold cyan]{description}[/]")
        else:
            value = (
                "****"
                if variable_def.sensitive
                else str(variable_def.assigned_value)
                if hasattr(variable_def, "assigned_value")
                else "None"
            )
            if plain_text:
                console.print(value)
            else:
                console.print(f"[bold cyan]{value}[/]")

    def show_single_output(self, output_name: str, show_description: bool = False, plain_text: bool = False) -> None:
        """Display the value or description of a single output.

        Args:
            output_name: The name of the output to display
            show_description: If True, show description instead of value
            plain_text: If True, output plain text without Rich markup
        """
        console = self.get_console()
        try:
            outputs = self._outputs_handler.get_full_project_outputs()
        except Exception as e:
            console.print(f":x: Could not retrieve output '{output_name}': {str(e)}", style="red")
            raise typer.Exit(code=1) from None

        if not outputs:
            console.print(":warning: No outputs available.", style="yellow")
            console.print("This is normal if the project has not been deployed yet.", style="yellow")
            raise typer.Exit(code=1)

        if output_name not in outputs:
            console.print(f":x: Output '{output_name}' not found.", style="red")
            raise typer.Exit(code=1)

        output_def = outputs[output_name]

        if show_description:
            description = getattr(output_def, "description", "") or "No description"
            if plain_text:
                console.print(description)
            else:
                console.print(f"[bold cyan]{description}[/]")
        else:
            value = str(output_def.value) if hasattr(output_def, "value") and output_def.value is not None else "None"
            if plain_text:
                console.print(value)
            else:
                console.print(f"[bold cyan]{value}[/]")

    def list_variable_names(self, plain_text: bool = False) -> None:
        """List all variable names.

        Args:
            plain_text: If False, output newline-separated with Rich markup.
                       If True, output comma-separated without Rich markup.
        """
        console = self.get_console()
        try:
            self._variables_handler.sync_engine_varfiles_with_project_variables_config()
            variables = self._variables_handler.get_template_variables()
        except Exception as e:
            console.print(f":x: Could not retrieve variables: {str(e)}", style="red")
            raise typer.Exit(code=1) from None

        if not variables:
            console.print(":x: No variables available.", style="red")
            raise typer.Exit(code=1)

        if plain_text:
            variable_names = ",".join(variables.keys())
            console.print(variable_names)
        else:
            for variable_name in variables:
                console.print(f"[bold cyan]{variable_name}[/]")

    def list_output_names(self, plain_text: bool = False) -> None:
        """List all output names.

        Args:
            plain_text: If False, output newline-separated with Rich markup.
                       If True, output comma-separated without Rich markup.
        """
        console = self.get_console()
        try:
            outputs = self._outputs_handler.get_full_project_outputs()
        except Exception as e:
            console.print(f":x: Could not retrieve outputs: {str(e)}", style="red")
            raise typer.Exit(code=1) from None

        if not outputs:
            console.print(":warning: No outputs available.", style="yellow")
            console.print("This is normal if the project has not been deployed yet.", style="yellow")
            raise typer.Exit(code=1)

        if plain_text:
            output_names = ",".join(outputs.keys())
            console.print(output_names)
        else:
            for output_name in outputs:
                console.print(f"[bold cyan]{output_name}[/]")

    def show_template_name(self, plain_text: bool = False) -> None:
        """Display the template name.

        Args:
            plain_text: If True, output plain text without Rich markup
        """
        console = self.get_console()
        template_name = self.project_manifest.template.name

        if plain_text:
            console.print(template_name)
        else:
            console.print(f"[bold cyan]{template_name}[/]")

    def show_template_version(self, plain_text: bool = False) -> None:
        """Display the template version.

        Args:
            plain_text: If True, output plain text without Rich markup
        """
        console = self.get_console()
        template_version = self.project_manifest.template.version

        if plain_text:
            console.print(template_version)
        else:
            console.print(f"[bold cyan]{template_version}[/]")

    def show_template_engine(self, plain_text: bool = False) -> None:
        """Display the template engine.

        Args:
            plain_text: If True, output plain text without Rich markup
        """
        console = self.get_console()
        engine = self.engine.value

        if plain_text:
            console.print(engine)
        else:
            console.print(f"[bold cyan]{engine}[/]")
