import subprocess
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Annotated

import typer
from jupyter_core.application import JupyterApp
from rich.console import Console

from jupyter_deploy import cmd_utils
from jupyter_deploy.cli.host_app import host_app
from jupyter_deploy.cli.organization_app import organization_app
from jupyter_deploy.cli.progress_display import ProgressDisplayManager
from jupyter_deploy.cli.servers_app import servers_app
from jupyter_deploy.cli.teams_app import teams_app
from jupyter_deploy.cli.users_app import users_app
from jupyter_deploy.cli.variables_decorator import with_project_variables
from jupyter_deploy.engine.engine_config import ReadConfigurationError, WriteConfigurationError
from jupyter_deploy.engine.enum import EngineType
from jupyter_deploy.engine.supervised_execution import ExecutionError
from jupyter_deploy.engine.vardefs import TemplateVariableDefinition
from jupyter_deploy.handlers.init_handler import InitHandler
from jupyter_deploy.handlers.project import config_handler
from jupyter_deploy.handlers.project.config_handler import InvalidPreset
from jupyter_deploy.handlers.project.down_handler import DownAutoApproveRequiredError, DownHandler
from jupyter_deploy.handlers.project.open_handler import OpenHandler
from jupyter_deploy.handlers.project.show_handler import ShowHandler
from jupyter_deploy.handlers.project.up_handler import UpHandler
from jupyter_deploy.infrastructure.enum import AWSInfrastructureType, InfrastructureType
from jupyter_deploy.provider.enum import ProviderType
from jupyter_deploy.verify_utils import ToolRequiredError


class JupyterDeployCliRunner:
    """Wrapper class for Typer app."""

    def __init__(self) -> None:
        """Setup the CLI shell, add sub-commands."""
        self.app = typer.Typer(
            help=("Jupyter-deploy CLI helps you deploy notebooks application to your favorite Cloud provider."),
            no_args_is_help=True,
        )
        self._setup_basic_commands()
        self.app.add_typer(servers_app, name="server")
        self.app.add_typer(users_app, name="users")
        self.app.add_typer(teams_app, name="teams")
        self.app.add_typer(organization_app, name="organization")
        self.app.add_typer(host_app, name="host")

    def _setup_basic_commands(self) -> None:
        """Register the basic commands."""
        pass

    def run(self) -> None:
        """Execute the CLI."""
        self.app()


runner = JupyterDeployCliRunner()


@runner.app.command()
def init(
    path: Annotated[
        str | None,
        typer.Argument(
            help="Path to the directory where jupyter-deploy will create your project files. "
            "Pass '.' to use your current working directory."
        ),
    ] = None,
    engine: Annotated[
        EngineType, typer.Option("--engine", "-E", help="Infrastructure as code software to manage your resources.")
    ] = EngineType.TERRAFORM,
    provider: Annotated[
        ProviderType, typer.Option("--provider", "-P", help="Cloud provider where your resources will be provisioned.")
    ] = ProviderType.AWS,
    infrastructure: Annotated[
        InfrastructureType,
        typer.Option(
            "--infrastructure",
            "-I",
            help="Infrastructure service that your cloud provider will use to provision your resources.",
        ),
    ] = AWSInfrastructureType.EC2,
    template: Annotated[
        str, typer.Option("--template", "-T", help="Base name of the infrastrucuture as code template (e.g., base)")
    ] = "base",
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            "-o",
            help="Overwrite the project directory instead of failing when the directory is not empty.",
        ),
    ] = False,
) -> None:
    """Initialize a project directory containing the specified infrastructure-as-code template.

    Template will be selected based on the provided parameters - the matching
    template package must have already been installed.

    You must specify a project path which must be a directory. If such a directory is not empty,
    the command will fail unless you passed the `--overwrite` or `-o` flag. `--overwrite` will prompt
    for confirmation before deleting existing content.
    """
    if path is None:
        init_help_cmds = ["jupyter", "deploy", "init", "--help"]
        subprocess.run(init_help_cmds)
        return
    project = InitHandler(
        project_dir=path,
        engine=engine,
        provider=provider,
        infrastructure=infrastructure,
        template=template,
    )
    console = Console()

    if not project.may_export_to_project_path():
        if not overwrite:
            console.line()
            console.print(f":x: The directory {project.project_path} is not empty, aborting.", style="red")
            console.line()
            console.print(
                "If you want to overwrite the content of this directory, use the --overwrite option.\n", style="yellow"
            )
            return
        else:
            console.line()
            console.print(f":warning: The target directory {project.abs_project_path} is not empty.", style="yellow")
            console.line()
            console.print(
                "Initiating the project may overwrite your existing files, are you sure you want to proceed?",
                style="yellow",
            )

            overwrite_existing = typer.confirm("")

            if not overwrite_existing:
                console.line()
                console.print(f"Left files under {project.project_path} untouched.\n", style="yellow")
                typer.Abort()
                return

    project.setup()

    console.print(f"Created start-up project files at: {project.project_path.absolute()}", style="bold green")
    console.line()

    if Path.cwd().absolute() != project.project_path.absolute():
        console.print(
            f"Change your working directory to [bold]{project.project_path}[/] "
            "then you can run `[bold cyan]jd config[/]` to configure the project.",
            style="green",
        )
    else:
        console.print("You can now run `[bold cyan]jd config[/]` to configure the project.")
    console.line()
    console.print(
        "This command will use all the defaults specified in the template, unless you override specific variables."
    )
    console.print("The names of the variables depend on the template, use [bold cyan]--help[/] to find them.")
    console.print("To manually set the value of [italic]all[/] variables, use [bold cyan]--defaults none[/].")
    console.line()


@runner.app.command()
@with_project_variables()
def config(
    defaults_preset_name: Annotated[
        str,
        typer.Option(
            "--defaults",
            "-d",
            help="Name of the preset defaults to use: 'all', 'none' or template-specific preset names.",
        ),
    ] = "all",
    record_secrets: Annotated[
        bool,
        typer.Option(
            "--record-secrets",
            "-s",
            help="Record the values of variables marked 'sensitive'.",
        ),
    ] = False,
    reset: Annotated[
        bool, typer.Option("--reset", "-r", help="Delete previously recorded variables and secrets.")
    ] = False,
    skip_verify: Annotated[
        bool, typer.Option("--skip-verify", help="Avoid verifying that the project dependencies are configured.")
    ] = False,
    output_filename: Annotated[
        str | None, typer.Option("--output-filename", "-f", help="Name of the file to store the configuration to.")
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", help="Show full output without progress bar.")] = False,
    variables: Annotated[
        dict[str, TemplateVariableDefinition] | None,
        typer.Option("--variables", "-v", help="Will be removed by the decorator."),
    ] = None,
) -> None:
    """Verify the system configuration, prompt inputs and prepare for deployment.

    You must run this command from a jupyter-deploy project directory created with `jd init`.

    The `config` command will remember your variable values so that you do not need to
    specify them again next time you run `config`.

    You can reset these recorded values with `--reset` or `-r`. Sensitive variables do not
    get recorded unless you pass `--record-secrets` or `-s`.

    You can specify where to save the planned change with `--output-file` or `-f`.
    """
    preset_name = None if defaults_preset_name == "none" else defaults_preset_name

    # Create progress display manager (or None if verbose mode)
    progress_display = None if verbose else ProgressDisplayManager()

    handler = config_handler.ConfigHandler(output_filename=output_filename, terminal_handler=progress_display)

    console = Console()

    # Validate and set preset
    # First, verify whether there are recorded variables values from user inputs
    # if yes, do NOT use the preset defaults.
    # `jd config` records values automatically, and we want users to be able to rerun `jd config`
    # without getting prompted again or having their previous choices overridden by defaults.
    if not reset and handler.has_recorded_variables():
        preset_name = None
        if verbose:
            console.rule()
            console.print(
                ":magnifying_glass_tilted_right: Detected variables values that [bold]jupyter-deploy[/] "
                "recorded previously."
            )
            console.print("Recorded values take precedent over any default preset.")
            console.print("You can override any recorded variable value with [bold cyan]--variable-name <value>[/].")

    # Validate preset if provided
    if preset_name is not None:
        try:
            handler.validate_preset(preset_name)
        except InvalidPreset as e:
            console.print(f":x: preset [bold]{e.preset_name}[/] is invalid for this template.", style="red")
            console.print(f"Valid presets: {e.valid_presets}")
            raise typer.Exit(code=1) from None

    # Set the preset, which may have been overridden to None if it detected recorded variables.
    handler.set_preset(preset_name)

    run_verify = not skip_verify
    run_configure = False

    if reset:
        if verbose:
            console.rule("[bold]jupyter-deploy:[/] resetting recorded variables and secrets")
        handler.reset_recorded_variables()
        handler.reset_recorded_secrets()

    if run_verify:
        if verbose:
            console.rule("[bold]jupyter-deploy:[/] verifying requirements")
        try:
            handler.verify_requirements()
            run_configure = True
        except ToolRequiredError as e:
            console.print(f":x: {e}", style="red")
            console.line()
            if e.error_msg:
                console.print(f"Error: {e.error_msg}", style="red")
                console.line()
            if e.installation_url:
                console.print(f"Refer to the installation guide: {e.installation_url}")
            raise typer.Exit(code=1) from None
    else:
        if verbose:
            console.print("[bold]jupyter-deploy:[/] skipping verification of requirements")
        run_configure = True

    if run_configure:
        if verbose:
            console.rule("[bold]jupyter-deploy:[/] configuring the project")

        with progress_display or nullcontext():
            try:
                handler.configure(variable_overrides=variables)
            except ExecutionError as e:
                # Error context already displayed by callback
                console.print(f":x: {e.message}", style="red")
                raise typer.Exit(code=e.retcode) from None

        if verbose:
            console.rule("[bold]jupyter-deploy:[/] recording input values")

        try:
            handler.record(record_vars=True, record_secrets=record_secrets)
        except ReadConfigurationError as e:
            console.print(f":x: {e}", style="red")
            raise typer.Exit(code=1) from None
        except WriteConfigurationError as e:
            console.print(f":x: {e}", style="red")
            raise typer.Exit(code=1) from None

        if verbose:
            if record_secrets:
                console.print(":floppy_disk: Recorded configuration, variables and secrets")
            else:
                console.print(":floppy_disk: Recorded configuration and variables")

        # finally, display a message to the user if config ignored the template defaults
        # in favor of the recorded variables, with instructions on how to change this behavior.
        has_used_preset = handler.has_used_preset(preset_name)
        if verbose and not has_used_preset:
            console.line()
            console.print(
                "[bold]jupyter-deploy[/] reused the variables values that you elected previously "
                f"instead of the template preset: [bold cyan]{preset_name}[/]."
            )
            console.print("You can use `[bold cyan]--reset[/]` to clear your recorded values.")
        if verbose:
            console.rule()

        console.print("Your project is ready.", style="bold green")
        console.line()
        if output_filename:
            console.print(
                f"You can now run `[bold cyan]jd up --config-filename {output_filename}[/]` to create the resources."
            )
        else:
            console.print("You can now run `[bold cyan]jd up[/]` to create or update the resources.")
        console.line()


@runner.app.command()
def up(
    project_dir: Annotated[
        str | None, typer.Option("--path", "-p", help="Directory of the jupyter-deploy project to bring up.")
    ] = None,
    config_filename: Annotated[
        str | None,
        typer.Option(
            "--config-filename", "-f", help="Name of a file in the project_dir containing the execution configuration."
        ),
    ] = None,
    auto_approve: Annotated[
        bool, typer.Option("--answer-yes", "-y", help="Apply changes without confirmation prompt.")
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show full output without progress bar.")] = False,
) -> None:
    """Apply the changes defined in the infrastructure-as-code template.

    Run either from a jupyter-deploy project directory that you created with `jd init`;
    or pass a --path PATH to such a directory. Optionally, you can also pass a --config-file
    argument.

    Call `jd config` first to set the input variables and
    verify the configuration.
    """
    with cmd_utils.project_dir(project_dir):
        console = Console()

        # Create progress display manager (or None if verbose mode)
        progress_display = None if verbose else ProgressDisplayManager()

        # Pass to handler via protocol
        handler = UpHandler(terminal_handler=progress_display)

        if verbose:
            console.rule("[bold]jupyter-deploy:[/] verifying presence of config file")
        try:
            config_file_path = handler.get_config_file_path(config_filename)
        except FileNotFoundError as e:
            console.print(f":x: {e}", style="red")
            raise typer.Exit(1) from None

        if verbose:
            console.rule("[bold]jupyter-deploy:[/] applying infrastructure changes")
        with progress_display or nullcontext():
            try:
                handler.apply(config_file_path, auto_approve)
            except ExecutionError as e:
                console.print(f":x: {e.message}", style="red")
                raise typer.Exit(code=e.retcode) from None

        console.print("Infrastructure changes applied successfully.", style="green")


@runner.app.command()
def down(
    project_dir: Annotated[
        str | None, typer.Option("--path", "-p", help="Directory of the jupyter-deploy project to bring down.")
    ] = None,
    auto_approve: Annotated[
        bool, typer.Option("--answer-yes", "-y", help="Destroy resources without confirmation prompt.")
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show full output without progress bar.")] = False,
) -> None:
    """Destroy the resources defined in the infrastructure-as-code template.

    Run either from a jupyter-deploy project directed that you created with `jd init`;
    or pass a --path PATH to such a directory.

    No-op if you have not already created the infrastructure with `jd up`, or if you
    already ran `jd down`.
    """
    with cmd_utils.project_dir(project_dir):
        console = Console()

        # Create progress display manager (or None if verbose mode)
        progress_display = None if verbose else ProgressDisplayManager()

        # Pass to handler via protocol
        handler = DownHandler(terminal_handler=progress_display)

        # Check for persisting resources and display warning
        persisting_resources = handler.get_persisting_resources()
        if persisting_resources:
            console.print(":warning: The template defines persisting resources:", style="yellow")
            for persisting_resource in persisting_resources:
                console.print(persisting_resource, style="yellow")
            console.rule(style="yellow")

        if verbose:
            console.rule("[bold]jupyter-deploy:[/] destroying infrastructure resources")
        with progress_display or nullcontext():
            try:
                handler.destroy(auto_approve)
            except ExecutionError as e:
                console.print(f":x: {e.message}", style="red")
                raise typer.Exit(code=e.retcode) from None
            except DownAutoApproveRequiredError:
                console.print(
                    (
                        ":x: You must pass [bold]--answer-yes[/] or [bold]-y[/] to proceed.\n"
                        "Proceed carefully: you will need to manage the persisting resources, "
                        "and they may incur cost until you delete them."
                    ),
                    style="red",
                )
                console.line()
                raise typer.Exit(code=1) from None

        console.print("Infrastructure resources destroyed successfully.", style="green")


@runner.app.command()
def open(
    project_dir: Annotated[
        str | None, typer.Option("--path", "-p", help="Directory of the jupyter-deploy project to open.")
    ] = None,
) -> None:
    """Open the Jupyter app in your webbrowser.

    Run either from a jupyter-deploy project directory that you created with `jd init`;
    or pass a --path PATH to such a directory.

    Call `jd config` and `jd up` first.
    """
    with cmd_utils.project_dir(project_dir):
        handler = OpenHandler()
        handler.open()


@runner.app.command()
def show(
    project_dir: Annotated[
        str | None, typer.Option("--path", "-p", help="Directory of the jupyter-deploy project to show information.")
    ] = None,
    info: Annotated[bool, typer.Option("--info", help="Display core project and template information.")] = False,
    outputs: Annotated[bool, typer.Option("--outputs", help="Display outputs information.")] = False,
    variables: Annotated[bool, typer.Option("--variables", help="Display variables information.")] = False,
    variable: Annotated[
        str | None, typer.Option("--variable", "-v", help="Get the value of a specific variable by name.")
    ] = None,
    output: Annotated[
        str | None, typer.Option("--output", "-o", help="Get the value of a specific output by name.")
    ] = None,
    template_name: Annotated[bool, typer.Option("--template-name", help="Display the template name.")] = False,
    template_version: Annotated[bool, typer.Option("--template-version", help="Display the template version.")] = False,
    template_engine: Annotated[bool, typer.Option("--template-engine", help="Display the template engine.")] = False,
    description: Annotated[
        bool,
        typer.Option("--description", "-d", help="Show description instead of value (with --variable or --output)."),
    ] = False,
    list_names: Annotated[
        bool,
        typer.Option("--list", help="List names only (with --variables or --outputs)."),
    ] = False,
    text: Annotated[
        bool,
        typer.Option("--text", help="Output plain text without Rich markup."),
    ] = False,
) -> None:
    """Display information about the jupyter-deploy project.

    Run either from a jupyter-deploy project directory that you created with `jd init`;
    or pass a --path PATH to such a directory.

    If the project is up, shows the values of the output as defined in
    the infrastructure as code project.

    Pass --variable <variable-name> to display the value of a single variable, or
    -v <variable-name> --description to display its description.

    Pass --output <output-name> to display the value of a single output, or
    -o <output-name> --description to display its description.

    Pass --variables --list or --outputs --list to display the list of variable or output names.
    """
    # Validate parameter combinations
    query_flags = [variable, output, template_name, template_version, template_engine]
    query_flags_set = sum([bool(f) for f in query_flags])

    if query_flags_set > 1:
        err_console = Console(stderr=True)
        err_console.print(
            ":x: Cannot use multiple query flags "
            "(--variable, --output, --template-name, --template-version, --template-engine) at the same time.",
            style="red",
        )
        raise typer.Exit(code=1)

    if description and not (variable or output):
        err_console = Console(stderr=True)
        err_console.print(":x: --description can only be used with --variable or --output.", style="red")
        raise typer.Exit(code=1)

    if list_names and not (variables or outputs):
        err_console = Console(stderr=True)
        err_console.print(":x: --list can only be used with --variables or --outputs.", style="red")
        raise typer.Exit(code=1)

    # Validate that display mode flags are not used with query flags
    display_flags_set = info or outputs or variables
    if query_flags_set > 0 and display_flags_set:
        err_console = Console(stderr=True)
        err_console.print(
            ":x: Cannot use display mode flags (--info, --outputs, --variables) "
            "with query flags (--variable, --output, --template-name, --template-version, --template-engine).",
            style="red",
        )
        raise typer.Exit(code=1)

    with cmd_utils.project_dir(project_dir):
        handler = ShowHandler()

        # Handle single variable query
        if variable:
            handler.show_single_variable(variable, show_description=description, plain_text=text)
            return

        # Handle single output query
        if output:
            handler.show_single_output(output, show_description=description, plain_text=text)
            return

        # Handle template queries
        if template_name:
            handler.show_template_name(plain_text=text)
            return

        if template_version:
            handler.show_template_version(plain_text=text)
            return

        if template_engine:
            handler.show_template_engine(plain_text=text)
            return

        # Handle list mode with --variables or --outputs (list names only)
        if list_names:
            if variables and not info and not outputs:
                handler.list_variable_names(plain_text=text)
                return
            if outputs and not info and not variables:
                handler.list_output_names(plain_text=text)
                return

        # Handle normal display mode
        if not info and not outputs and not variables:
            show_info = True
            show_outputs = True
            show_variables = True
        else:
            show_info = info
            show_outputs = outputs
            show_variables = variables

        handler.show_project_info(show_info=show_info, show_outputs=show_outputs, show_variables=show_variables)


class JupyterDeployApp(JupyterApp):
    """Jupyter Deploy application for use with 'jupyter deploy' command."""

    name = "jupyter-deploy"
    description = "Deploy Jupyter notebooks application to your favorite Cloud provider."

    def start(self) -> None:
        """Run the deploy application."""
        args_without_command = sys.argv[2:] if len(sys.argv) > 2 else []
        sys.argv = args_without_command

        runner.run()


def main() -> None:
    if sys.argv[0].endswith("jupyter") and len(sys.argv) > 1 and sys.argv[1] == "deploy":
        JupyterDeployApp.launch_instance()
    else:
        runner.run()
