"""CLI error handling context manager for jupyter-deploy exceptions."""

from collections.abc import Generator
from contextlib import contextmanager

import typer
from rich.console import Console

from jupyter_deploy.exceptions import (
    CommandNotImplementedError,
    ConfigurationError,
    DownAutoApproveRequiredError,
    HostCommandInstructionError,
    IncompatibleHostStateError,
    InstructionNotFoundError,
    InteractiveSessionError,
    InteractiveSessionTimeoutError,
    InvalidInstructionArgumentError,
    InvalidInstructionResultError,
    InvalidManifestError,
    InvalidPresetError,
    InvalidProjectPathError,
    InvalidProviderCredentialsError,
    InvalidServiceError,
    InvalidVariablesDotYamlError,
    JupyterDeployError,
    LogCleanupError,
    LogNotFoundError,
    ManifestNotFoundError,
    OpenWebBrowserError,
    OutputNotFoundError,
    ProjectIdNotAvailableError,
    ProviderPermissionError,
    ReadConfigurationError,
    ReadManifestError,
    StoreNotFoundError,
    SupervisedExecutionError,
    ToolRequiredError,
    UnreachableHostError,
    UnsupportedProviderRegionError,
    UrlNotAvailableError,
    UrlNotSecureError,
    VariableNotFoundError,
    WriteConfigurationError,
)


@contextmanager
def handle_cli_errors(console: Console) -> Generator[None, None, None]:
    """Catch core exceptions and display user-friendly messages.

    This context manager should wrap CLI command execution to provide consistent
    error handling across all commands. It catches JupyterDeployError exceptions
    and formats them appropriately for CLI display, hiding stack traces for
    expected errors while preserving them for unexpected ones.

    Args:
        console: Rich Console instance for formatted output

    Yields:
        None

    Example:
        with handle_cli_errors(console):
            result = handler.some_operation()
            console.print(f"Success: {result}")
    """
    try:
        yield

    except ManifestNotFoundError as e:
        console.print(f":x: {e}", style="bold red")
        console.line()
        console.print(
            ":bulb: Change your working directory to a jupyter-deploy project "
            "or create one with [bold cyan]jd init PATH[/]"
        )
        raise typer.Exit(code=1) from None

    except ReadManifestError as e:
        console.print(f":x: {e}", style="bold red")
        console.line()
        console.print(":bulb: Check file permissions or disk space for the manifest file")
        raise typer.Exit(code=1) from None

    except InvalidManifestError as e:
        console.print(f":x: {e}", style="bold red")
        console.line()
        console.print(":bulb: Review your manifest.yaml file for syntax errors or missing required fields")
        raise typer.Exit(code=1) from None

    except CommandNotImplementedError as e:
        console.print(f":x: {e}", style="bold red")
        raise typer.Exit(code=1) from None

    except InvalidProviderCredentialsError as e:
        console.print(f":x: {e}", style="bold red")
        if e.original_message:
            console.line()
            console.print(e.original_message, style="dim")
        raise typer.Exit(code=1) from None

    except ProviderPermissionError as e:
        console.print(f":x: {e}", style="bold red")
        if e.original_message:
            console.line()
            console.print(e.original_message, style="dim")
        raise typer.Exit(code=1) from None

    except ToolRequiredError as e:
        console.print(f":x: {e}", style="bold red")
        if e.error_msg or e.installation_url:
            console.line()

        if e.error_msg:
            console.print(f"  Details: {e.error_msg}", style="dim")
        if e.installation_url:
            console.print(f":bulb: Installation instructions: {e.installation_url}")
        raise typer.Exit(code=1) from None

    except SupervisedExecutionError as e:
        console.print(f":x: {e}", style="bold red")
        console.line()
        console.print(":bulb: To view the full logs, run: [bold cyan]jd history show[/]")
        raise typer.Exit(code=e.retcode) from None

    except InvalidPresetError as e:
        console.print(f":x: {e}", style="bold red")
        console.line()
        console.print(f"Available presets: {', '.join(e.valid_presets)}")
        raise typer.Exit(code=1) from None

    except InvalidServiceError as e:
        console.print(f":x: {e}", style="bold red")
        console.line()
        console.print(f"Available services: {', '.join(e.valid_services)}")
        raise typer.Exit(code=1) from None

    except (UnreachableHostError, IncompatibleHostStateError) as e:
        console.print(f":x: {e}", style="bold red")
        console.line()
        if e.hint:
            # Use the specific hint if provided (e.g., from IncompatibleHostStateError)
            console.print(f":bulb: {e.hint}")
        else:
            # Generic hint for accessibility issues (e.g., UnreachableHostError with no hint)
            console.print(":bulb: verify that your host is running: [bold cyan]jd host status[/]")
            console.print(":wrench: or try restarting it: [bold cyan]jd host restart[/]")
        raise typer.Exit(code=1) from None

    except HostCommandInstructionError as e:
        console.print(f":x: {e}", style="bold red")
        if e.stdout:
            console.rule("stdout")
            console.print(e.stdout)
            if not e.stderr:
                console.rule()
        if e.stderr:
            console.rule("stderr")
            console.print(e.stderr)
            console.rule()
        raise typer.Exit(code=e.retcode) from None

    except InvalidVariablesDotYamlError as e:
        console.print(f":x: {e}", style="bold red")
        console.line()
        console.print(":bulb: Review your variables.yaml file for syntax errors")
        raise typer.Exit(code=1) from None

    except LogNotFoundError as e:
        console.print(f":x: {e}", style="bold red")
        console.line()
        console.print(":bulb: To see available logs: [bold cyan]jd history list CMD[/]")
        raise typer.Exit(code=1) from None

    except (
        InvalidProjectPathError,
        InteractiveSessionTimeoutError,
        InteractiveSessionError,
        InstructionNotFoundError,
        InvalidInstructionArgumentError,
        InvalidInstructionResultError,
        LogCleanupError,
    ) as e:
        console.print(f":x: {e}", style="bold red")
        raise typer.Exit(code=1) from None

    except DownAutoApproveRequiredError as e:
        console.print(f":x: {e}", style="bold red")
        if e.persisting_resources:
            console.print("  Persisting resources:")
            for resource in e.persisting_resources:
                console.print(f"    - {resource}")
        raise typer.Exit(code=1) from None

    except (VariableNotFoundError, OutputNotFoundError) as e:
        console.print(f":x: {e}", style="bold red")
        # check if next steps provided, if so print them
        raise typer.Exit(code=1) from None

    except UrlNotAvailableError as e:
        console.print(f":x: {e}", style="bold red")
        console.line()
        console.print("Make sure you have configured and deployed your project.")
        console.print(":bulb: To configure the project, run: [bold cyan]jd config[/]")
        console.print(":bulb: To deploy it, run: [bold cyan]jd up[/]")
        raise typer.Exit(code=1) from None

    except UrlNotSecureError as e:
        console.print(f":x: {e}", style="bold red")
        console.line()
        console.print("Only HTTPS URLs are allowed for security reasons.", style="red")
        raise typer.Exit(code=1) from None

    except OpenWebBrowserError as e:
        console.print(f":x: {e}", style="bold red")
        console.line()
        console.print(f"URL: [bold cyan]{e.url}[/]")
        console.print(":bulb: Copy the URL and open it manually in your browser.")
        raise typer.Exit(code=1) from None

    except (ReadConfigurationError, WriteConfigurationError) as e:
        console.print(f":x: {e}", style="bold red")
        console.print(f"  File: {e.file_path}", style="dim")
        raise typer.Exit(code=1) from None

    except ProjectIdNotAvailableError as e:
        console.print(f":x: {e}", style="bold red")
        console.line()
        console.print(":bulb: Run [bold cyan]jd up[/] to deploy first, then retry.")
        raise typer.Exit(code=1) from None

    except StoreNotFoundError as e:
        console.print(f":x: {e}", style="bold red")
        console.line()
        console.print(":bulb: Run [bold cyan]jd config[/] to set up the remote store first.")
        raise typer.Exit(code=1) from None

    except UnsupportedProviderRegionError as e:
        console.print(f":x: {e}", style="bold red")
        if e.hint:
            console.line()
            console.print(f":bulb: {e.hint}")
        raise typer.Exit(code=1) from None

    # Keep base classes below so that child classes special handling take precedence
    except ConfigurationError as e:
        console.print(f":x: {e}", style="bold red")
        raise typer.Exit(code=1) from None

    except JupyterDeployError as e:
        # Catch-all for any JupyterDeployError not specifically handled above
        console.print(f":x: {e}", style="bold red")
        raise typer.Exit(code=1) from None

    # Let all other exceptions bubble up naturally - they will be caught by Typer's default handler
