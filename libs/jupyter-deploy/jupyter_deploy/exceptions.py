"""Centralized exception definitions for jupyter-deploy.

All custom exceptions inherit from JupyterDeployError for consistent error handling
across interfaces (CLI, API, etc.), while also preserving their original exception
types (ValueError, RuntimeError, etc.) for backwards compatibility.
"""


class JupyterDeployError(Exception):
    """Base exception for all jupyter-deploy errors."""

    pass


# ============================================================================
# Manifest and project errors
# ============================================================================


class ManifestNotFoundError(JupyterDeployError, FileNotFoundError):
    """Raised when manifest file is missing or project cannot be found."""

    pass


class ReadManifestError(JupyterDeployError, OSError):
    """Raised when manifest file cannot be read due to I/O error."""

    pass


class InvalidManifestError(JupyterDeployError, ValueError):
    """Raised when manifest parse or validation fails."""

    pass


class ManifestNotADictError(InvalidManifestError, ValueError):
    """Raised when manifest file doesn't parse as a dictionary."""

    pass


class InvalidVariablesDotYamlError(JupyterDeployError, ValueError):
    """Raised when variables.yaml file is invalid or malformed."""

    pass


# ============================================================================
# Variable and configuration errors
# ============================================================================


class VariableNotFoundError(JupyterDeployError, KeyError):
    """Raised when a variable name is not found in the project.

    Attributes:
        variable_name: The name of the variable that was not found
    """

    def __init__(self, variable_name: str) -> None:
        self.variable_name = variable_name
        super().__init__(f"Variable '{variable_name}' not found.")


class OutputNotFoundError(JupyterDeployError, KeyError):
    """Raised when an output name is not found in the project.

    Attributes:
        output_name: The name of the output that was not found
    """

    def __init__(self, output_name: str) -> None:
        self.output_name = output_name
        super().__init__(f"Output '{output_name}' not found.")


class InvalidPresetError(JupyterDeployError, ValueError):
    """Raised when an invalid preset name is provided.

    Attributes:
        preset_name: The invalid preset name provided
        valid_presets: List of valid preset names for this template
    """

    def __init__(self, preset_name: str, valid_presets: list[str]) -> None:
        self.preset_name = preset_name
        self.valid_presets = valid_presets
        super().__init__(f"Invalid preset: '{preset_name}'")


class InvalidServiceError(JupyterDeployError, ValueError):
    """Raised when an invalid service name is provided.

    Attributes:
        service_name: The invalid service name provided
        valid_services: List of valid service names
    """

    def __init__(self, service_name: str, valid_services: list[str]) -> None:
        self.service_name = service_name
        self.valid_services = valid_services
        super().__init__(f"Invalid service: '{service_name}'")


class InvalidProjectPathError(JupyterDeployError, ValueError):
    """Raised when an invalid project path is provided."""

    pass


class UrlNotAvailableError(JupyterDeployError, ValueError):
    """Raised when URL is not available or empty."""

    pass


class UrlNotSecureError(JupyterDeployError, ValueError):
    """Raised when URL is not HTTPS."""

    def __init__(self, message: str, url: str) -> None:
        self.url = url
        super().__init__(message)


class OpenWebBrowserError(JupyterDeployError, RuntimeError):
    """Raised when opening URL in web browser fails."""

    def __init__(self, message: str, url: str) -> None:
        self.url = url
        super().__init__(message)


class ConfigurationError(JupyterDeployError, RuntimeError):
    """Base exception for configuration errors."""

    pass


class ReadConfigurationError(ConfigurationError, RuntimeError):
    """Raised when reading or parsing the file that captured the results of a config command fails.

    Attributes:
        file_path: Path to the configuration file that failed to read
    """

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        super().__init__(f"Failed to read or parse file at: {file_path}")


class WriteConfigurationError(ConfigurationError, RuntimeError):
    """Raised when writing the results of a config command to disk fails.

    Attributes:
        file_path: Path to the configuration file that failed to write
    """

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        super().__init__(f"Failed to write configuration to: {file_path}")


# ============================================================================
# Supervised execution errors
# ============================================================================


class SupervisedExecutionError(JupyterDeployError, Exception):
    """Raised when a supervised command execution fails.

    These errors generate history logs that can be viewed with 'jd history show'.

    Attributes:
        command: The command that failed (e.g., "config", "up", "down")
        retcode: The non-zero return code from the failed command
    """

    def __init__(self, command: str, retcode: int, message: str) -> None:
        self.command = command
        self.retcode = retcode
        super().__init__(message)


# ============================================================================
# Instruction execution errors
# ============================================================================


class InstructionError(JupyterDeployError, RuntimeError):
    """Base exception for instruction execution errors."""

    pass


class InteractiveSessionError(InstructionError, RuntimeError):
    """Raised when an interactive session fails."""

    pass


class InteractiveSessionTimeoutError(InteractiveSessionError, TimeoutError):
    """Raised when an interactive session times out."""

    pass


class UnreachableHostError(InstructionError, ConnectionError):
    """Raised when host cannot be reached (e.g., SSM agent offline).

    Attributes:
        hint: Optional helpful hint for resolving the error
    """

    def __init__(self, message: str, hint: str | None = None) -> None:
        self.hint = hint
        super().__init__(message)


class IncompatibleHostStateError(InstructionError, RuntimeError):
    """Raised when host is in wrong state for the requested operation.

    Attributes:
        hint: Optional helpful hint for resolving the error
    """

    def __init__(self, message: str, hint: str | None = None) -> None:
        self.hint = hint
        super().__init__(message)


class HostCommandInstructionError(InstructionError, RuntimeError):
    """Raised when a command execution fails on a host.

    Attributes:
        retcode: The exit code from the command
        stdout: Standard output content from the command
        stderr: Standard error content from the command
    """

    def __init__(self, message: str, retcode: int, stdout: str, stderr: str) -> None:
        self.retcode = retcode
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(message)


class InstructionNotFoundError(InstructionError, RuntimeError):
    """Raised when an instruction cannot be found or is not implemented."""

    pass


class InvalidInstructionArgumentError(InstructionError, ValueError):
    """Raised when an instruction argument is invalid or missing."""

    pass


class InvalidInstructionResultError(InstructionError, ValueError):
    """Raised when an instruction result is invalid or cannot be resolved."""

    pass


# ============================================================================
# Tool and requirement errors
# ============================================================================


class ToolRequiredError(JupyterDeployError, RuntimeError):
    """Raised when a required tool is not installed or has an incorrect version.

    Attributes:
        tool_name: Name of the required tool
        installation_url: Optional URL with installation instructions
        error_msg: Optional detailed error message from the check
    """

    def __init__(
        self,
        tool_name: str,
        installation_url: str | None = None,
        error_msg: str | None = None,
    ) -> None:
        self.tool_name = tool_name
        self.installation_url = installation_url
        self.error_msg = error_msg
        super().__init__(f"This operation requires {tool_name} to be installed in your system.")


# ============================================================================
# Resource management errors
# ============================================================================


class DownAutoApproveRequiredError(JupyterDeployError, ValueError):
    """Raised when auto-approve is required but not provided.

    Attributes:
        persisting_resources: List of resources that would persist after down
    """

    def __init__(self, persisting_resources: list[str]) -> None:
        self.persisting_resources = persisting_resources
        super().__init__(
            "Auto-approve is required when there are persisting resources. Pass --answer-yes or -y to proceed."
        )


# ============================================================================
# History and logging errors
# ============================================================================


class LogNotFoundError(JupyterDeployError, ValueError):
    """Raised when a command execution log cannot be found."""

    pass


class LogCleanupError(JupyterDeployError, Exception):
    """Raised when log cleanup fails."""

    pass
