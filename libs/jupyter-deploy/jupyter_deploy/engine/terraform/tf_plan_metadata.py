"""Terraform plan metadata management."""

import json
from pathlib import Path

from pydantic import BaseModel

from jupyter_deploy.engine.terraform.tf_constants import TerraformPlanMetadataSource


class TerraformPlanMetadata(BaseModel):
    """Metadata extracted from a terraform plan.

    Attributes:
        to_add: Number of resources to be added
        to_change: Number of resources to be changed
        to_destroy: Number of resources to be destroyed
        to_mutate: Number of resources to be mutated
    """

    to_add: int
    to_change: int
    to_destroy: int

    @property
    def to_mutate(self) -> int:
        """Total number of resources that will be modified."""
        return self.to_add + self.to_change + self.to_destroy

    @property
    def to_update(self) -> int:
        """Total number of resources to be added or changed (not destroyed)."""
        return self.to_add + self.to_change

    def get_value(self, source: TerraformPlanMetadataSource) -> int | None:
        """Extract value from plan metadata based on source enum.

        Args:
            source: The source enum indicating which value to extract

        Returns:
            The extracted value or None if source is not recognized
        """
        if source == TerraformPlanMetadataSource.plan_to_add:
            return self.to_add
        elif source == TerraformPlanMetadataSource.plan_to_change:
            return self.to_change
        elif source == TerraformPlanMetadataSource.plan_to_destroy:
            return self.to_destroy
        elif source == TerraformPlanMetadataSource.plan_to_update:
            return self.to_update
        elif source == TerraformPlanMetadataSource.plan_to_mutate:
            return self.to_mutate
        return None


def save_plan_metadata(metadata: TerraformPlanMetadata, file_path: Path) -> None:
    """Save plan metadata to a JSON file.

    Args:
        metadata: The metadata to save
        file_path: Path where metadata should be written
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(metadata.model_dump(), f, indent=2)


def load_plan_metadata(file_path: Path) -> TerraformPlanMetadata | None:
    """Load plan metadata from a JSON file.

    Args:
        file_path: Path to the metadata file

    Returns:
        TerraformPlanMetadata if file exists and is valid, None otherwise
    """
    if not file_path.exists():
        return None

    try:
        with open(file_path) as f:
            data = json.load(f)
        return TerraformPlanMetadata(**data)
    except (json.JSONDecodeError, ValueError):
        return None
