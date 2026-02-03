"""Enums for Terraform operations."""

from enum import Enum

from jupyter_deploy.manifest import JupyterDeployManifest, JupyterDeploySupervisedCommandExecutionV1


class TerraformSequenceId(Enum):
    """Command sequence IDs for supervised execution.

    Format: {jd-command}.{CMD1}-{CMD2}-...

    Example: config.terraform-init
    """

    config_init = "config.terraform-init"
    config_plan = "config.terraform-plan"
    up_apply = "up.terraform-apply"
    down_rm_state = "down.terraform-state-rm"
    down_destroy = "down.terraform-destroy"

    def get_command_config(self, manifest: JupyterDeployManifest) -> JupyterDeploySupervisedCommandExecutionV1 | None:
        """Return command execution config from manifest for this sequence if found, None otherwise."""
        if not hasattr(manifest, "supervised_execution") or not manifest.supervised_execution:
            return None

        # Map sequence ID to manifest section and key
        if self == TerraformSequenceId.config_init or self == TerraformSequenceId.config_plan:
            section = manifest.supervised_execution.config
        elif self == TerraformSequenceId.up_apply:
            section = manifest.supervised_execution.up
        elif self == TerraformSequenceId.down_rm_state or self == TerraformSequenceId.down_destroy:
            section = manifest.supervised_execution.down
        else:
            return None

        if not section:
            return None

        return section.get(self.value)


class TerraformPlanMetadataSource(Enum):
    """Sources for extracting values from terraform plan metadata."""

    plan_to_add = "plan.to_add"
    plan_to_change = "plan.to_change"
    plan_to_destroy = "plan.to_destroy"
    plan_to_update = "plan.to_update"  # to_add + to_change

    @classmethod
    def from_string(cls, value: str | None) -> "TerraformPlanMetadataSource | None":
        """Return the enum member matching the string value.

        Args:
            value: The string value to match

        Returns:
            The matching enum member or None if not found
        """
        if not value:
            return None

        for member in cls:
            if member.value == value:
                return member
        return None
