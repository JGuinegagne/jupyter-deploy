"""Suite configuration models using Pydantic."""

import os
from datetime import datetime
from functools import cached_property
from pathlib import Path

import yaml
from dotenv import load_dotenv
from jupyter_deploy import constants as jd_constants
from jupyter_deploy import fs_utils as jd_fs_utils
from jupyter_deploy.engine.enum import EngineType
from jupyter_deploy.handlers.base_project_handler import retrieve_project_manifest, retrieve_variables_config
from jupyter_deploy.manifest import JupyterDeployManifest
from jupyter_deploy.variables_config import (
    VARIABLES_CONFIG_V1_COMMENTS,
    VARIABLES_CONFIG_V1_KEYS_ORDER,
    JupyterDeployVariablesConfig,
)


class SuiteConfig:
    """E2E test suite configuration."""

    manifest: JupyterDeployManifest
    variables_config: JupyterDeployVariablesConfig

    def __init__(self, suite_dir: Path, existing_project_dir: Path | None = None) -> None:
        """Instantiate the suite config.

        Args:
            suite_dir (Path): base directory of the e2e test suite
            existing_project_dir (Path): directory where the jupyter-deploy is deployed.
        """

        self.suite_dir = suite_dir
        self._existing_project_dir = existing_project_dir
        self._loaded = False

    def load(self) -> None:
        """Locate, read and parse manifest, variable and env vars.

        Raises:
            FileNotFoundError: If manifest.yaml does not exist
        """
        if self._loaded:
            return

        template_dir_path = self.find_template_dir_path()
        self.manifest = retrieve_project_manifest(template_dir_path / jd_constants.MANIFEST_FILENAME)
        self.variables_config = retrieve_variables_config(template_dir_path / jd_constants.VARIABLES_FILENAME)

        if self._existing_project_dir:
            self.project_dir = self._existing_project_dir
        else:
            full_name = self.manifest.template.name
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            self.project_dir = Path(os.getcwd()) / "sandbox-e2e" / full_name / timestamp
        self._loaded = True

    def find_template_dir_path(self) -> Path:
        """Return the path to the directory of the template.

        A template project is structured as follows:
        project-name
        |_project_name
        |__template
        |___manifest.yaml
        |___variables.yaml
        |_tests
        |__e2e
        |__unit
        """
        # implement this
        return Path(os.getcwd())

    @cached_property
    def template_engine(self) -> EngineType:
        """Template engine as listed in the manifest."""
        return self.manifest.get_engine()

    @cached_property
    def template_provider(self) -> str:
        """Template cloud provider derived from the template name"""
        template_name = self.manifest.template.name
        parts = template_name.split("-")
        if len(parts) < 4:
            raise ValueError(
                f"Invalid manifest template name: {template_name}. "
                f"Expected format: {{engine}}-{{provider}}-{{infrastructure}}-{{name}}"
            )
        provider = parts[1]
        return provider

    @cached_property
    def template_infrastructure(self) -> str:
        """Template infrastructure derived from the template name."""
        template_name = self.manifest.template.name
        parts = template_name.split("-")
        if len(parts) < 4:
            raise ValueError(
                f"Invalid manifest template name: {template_name}. "
                f"Expected format: {{engine}}-{{provider}}-{{infrastructure}}-{{name}}"
            )
        infrastructure = parts[2]
        return infrastructure

    @cached_property
    def template_base_name(self) -> str:
        """Template base name derived from the template name."""
        template_name = self.manifest.template.name
        parts = template_name.split("-")
        if len(parts) < 4:
            raise ValueError(
                f"Invalid manifest template name: {template_name}. "
                f"Expected format: {{engine}}-{{provider}}-{{infrastructure}}-{{name}}"
            )
        base_name = parts[3:]
        return "-".join(base_name)

    def prepare_configuration(self, config_name: str = "base") -> None:
        """Load variables yaml of specific configuration, applies substitution, copies to project dir."""
        # first load the configuration file and dotenv file(s)
        resolved_variables = self._load_configuration(config_name)

        # second, write file to project dir
        variables_config_path = self.project_dir / jd_constants.VARIABLES_FILENAME
        jd_fs_utils.write_yaml_file_with_comments(
            variables_config_path,
            resolved_variables.model_dump(),
            key_order=VARIABLES_CONFIG_V1_KEYS_ORDER,
            comments=VARIABLES_CONFIG_V1_COMMENTS,
        )

    def _load_configuration(self, config_name: str) -> JupyterDeployVariablesConfig:
        """Load a deployment configuration to the target directory.

        This function:
        1. Loads configurations/{config_name}.yaml
        2. Loads env.{config_name} if it exists
        3. Expands environment variables in the configuration
        4. Validates the result using the CLI's JupyterDeployVariablesConfig model
        5. Returns the validated config

        Args:
            config_name: Configuration name (e.g., "base")

        Returns:
            Validated variables configuration

        Raises:
            FileNotFoundError: If configuration file does not exist
            ValidationError: If configuration is invalid
        """
        # Load environment file first if it exists
        env_file_path = self.suite_dir / f"env.{config_name}"
        if env_file_path.exists():
            load_dotenv(env_file_path)

        # Load configuration file
        config_file = self.suite_dir / "configurations" / f"{config_name}.yaml"
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration not found at path: {config_file.absolute()}")

        with open(config_file) as f:
            resolved_content = os.path.expandvars(f.read())
            data = yaml.safe_load(resolved_content)

        if not isinstance(data, dict):
            raise ValueError("Invalid variables config file: jupyter-deploy variables config is not a dict.")

        return JupyterDeployVariablesConfig(**data)
