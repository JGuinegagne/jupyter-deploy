from pathlib import Path

import yaml
from pydantic import ValidationError
from rich import console as rich_console
from yaml.parser import ParserError
from yaml.scanner import ScannerError

from jupyter_deploy import constants, fs_utils, manifest, variables_config
from jupyter_deploy.exceptions import (
    InvalidManifestError,
    InvalidVariableError,
    ManifestNotADictError,
    ManifestNotFoundError,
    ReadManifestError,
)
from jupyter_deploy.handlers.command_history_handler import CommandHistoryHandler


class BaseProjectHandler:
    """Abstract class responsible for identifying the type of project.

    The current working directory MUST be a jupyter-deploy directory,
    otherwise this class will raise a typer.Exit().
    """

    def __init__(self) -> None:
        """Attempts to identify the engine associated with the project.

        Raises:
            ManifestNotFoundError: If project manifest not found
            ReadManifestError: If manifest cannot be read due to I/O error
            InvalidManifestError: If manifest cannot be parsed or validated
        """
        self._console: rich_console.Console | None = None
        self.project_path = Path.cwd()
        self.command_history_handler = CommandHistoryHandler(self.project_path)
        manifest_path = self.project_path / constants.MANIFEST_FILENAME

        project_manifest = retrieve_project_manifest(manifest_path)
        self.engine = project_manifest.get_engine()
        self.project_manifest = project_manifest

    def get_console(self) -> rich_console.Console:
        """Return the instance's rich console."""
        if self._console:
            return self._console
        self._console = rich_console.Console()
        return self._console


def retrieve_project_manifest(manifest_path: Path) -> manifest.JupyterDeployManifest:
    """Read the manifest file on disk, parse, validate and return it.

    Raises:
        ManifestNotFoundError: If manifest file not found
        ReadManifestError: If manifest file cannot be read due to I/O error
        InvalidManifestError: If manifest cannot be parsed or validated
    """
    if not fs_utils.file_exists(manifest_path):
        raise ManifestNotFoundError(f"Could not find manifest file at: {manifest_path.absolute()}")

    try:
        with open(manifest_path) as manifest_file:
            content = yaml.safe_load(manifest_file)
    except OSError as e:
        raise ReadManifestError(f"Cannot access manifest file at: {manifest_path.absolute()}. {e}") from e
    except (ParserError, ScannerError) as e:
        raise InvalidManifestError(f"Cannot parse manifest as YAML: {manifest_path.absolute()}. {e}") from e

    if not isinstance(content, dict):
        raise ManifestNotADictError(f"Manifest file must be a YAML dictionary: {manifest_path.absolute()}")

    try:
        return manifest.JupyterDeployManifest(**content)
    except ValidationError as e:
        error_details = "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
        raise InvalidManifestError(
            f"Manifest validation failed: {manifest_path.absolute()}. Errors: {error_details}"
        ) from e


def retrieve_project_manifest_if_available(project_path: Path) -> manifest.JupyterDeployManifest | None:
    """Attempts to read the manifest file on disk, parse, and return.

    Return None if the file is not found, cannot be parsed or fails any of the validation.
    """

    manifest_path = project_path / constants.MANIFEST_FILENAME
    try:
        return retrieve_project_manifest(manifest_path)
    except ManifestNotFoundError:
        # Silently return None when manifest doesn't exist (expected in some contexts)
        return None
    except ReadManifestError as e:
        # Print errors for I/O issues (indicates actual problems)
        print(e)
        return None
    except InvalidManifestError as e:
        # Print errors for malformed manifests (indicates actual problems)
        print(e)
        return None


def retrieve_variables_config(variables_config_path: Path) -> variables_config.JupyterDeployVariablesConfig:
    """Read the variables confign file on disk, parse, validate and return it."""

    if not fs_utils.file_exists(variables_config_path):
        raise FileNotFoundError("Missing jupyter-deploy variables config file.")

    with open(variables_config_path) as variables_manifest_file:
        content = yaml.safe_load(variables_manifest_file)

    if not isinstance(content, dict):
        raise InvalidVariableError("Invalid variables config file: jupyter-deploy variables config is not a dict.")

    return variables_config.JupyterDeployVariablesConfig(**content)
