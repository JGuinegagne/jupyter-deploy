import unittest
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import yaml

from jupyter_deploy.engine.terraform.tf_enums import TerraformPlanMetadataSource, TerraformSequenceId
from jupyter_deploy.manifest import JupyterDeployManifestV1


class TestTerraformSequenceId(unittest.TestCase):
    """Test cases for TerraformSequenceId enum."""

    def test_enum_has_expected_values(self) -> None:
        """Test that enum has all expected sequence IDs."""
        self.assertEqual(TerraformSequenceId.config_init.value, "config.terraform-init")
        self.assertEqual(TerraformSequenceId.config_plan.value, "config.terraform-plan")
        self.assertEqual(TerraformSequenceId.up_apply.value, "up.terraform-apply")
        self.assertEqual(TerraformSequenceId.down_destroy.value, "down.terraform-destroy")

    def test_get_command_config_returns_none_when_no_supervised_execution(self) -> None:
        """Test get_command_config returns None when manifest has no supervised_execution."""
        manifest = Mock()
        manifest.supervised_execution = None

        result = TerraformSequenceId.config_init.get_command_config(manifest)

        self.assertIsNone(result)

    def test_get_command_config_returns_none_when_section_not_found(self) -> None:
        """Test get_command_config returns None when section doesn't exist."""
        manifest = Mock()
        manifest.supervised_execution = Mock()
        manifest.supervised_execution.config = None
        manifest.supervised_execution.up = None
        manifest.supervised_execution.down = None

        result = TerraformSequenceId.config_init.get_command_config(manifest)

        self.assertIsNone(result)

    def test_get_command_config_returns_none_when_key_not_in_section(self) -> None:
        """Test get_command_config returns None when key not found in section."""
        manifest = Mock()
        manifest.supervised_execution = Mock()
        mock_config_section = Mock()
        mock_config_section.get = Mock(return_value=None)
        manifest.supervised_execution.config = mock_config_section

        result = TerraformSequenceId.config_init.get_command_config(manifest)

        self.assertIsNone(result)
        mock_config_section.get.assert_called_once_with("config.terraform-init")


class TestTerraformSequenceIdWithManifest(unittest.TestCase):
    """Test cases for TerraformSequenceId enum with real manifest."""

    manifest: JupyterDeployManifestV1
    manifest_parsed_content: Any

    @classmethod
    def setUpClass(cls) -> None:
        """Load the default manifest."""
        manifest_path = Path(__file__).parent.parent.parent / "mock_manifest.yaml"
        with open(manifest_path) as f:
            cls.manifest_parsed_content = yaml.safe_load(f)
        cls.manifest = JupyterDeployManifestV1(**cls.manifest_parsed_content)

    def test_get_command_config_returns_config_for_config_init(self) -> None:
        """Test get_command_config returns correct config for config_init."""
        result = TerraformSequenceId.config_init.get_command_config(self.manifest)

        self.assertIsNotNone(result)
        assert result is not None  # for mypy
        self.assertIsNotNone(result.default_phase)
        assert result.default_phase is not None  # for mypy
        self.assertEqual(result.default_phase.label, "Configuring terraform dependencies")

    def test_get_command_config_returns_config_for_config_plan(self) -> None:
        """Test get_command_config returns correct config for config_plan."""
        result = TerraformSequenceId.config_plan.get_command_config(self.manifest)

        self.assertIsNotNone(result)
        assert result is not None  # for mypy
        self.assertIsNotNone(result.default_phase)
        assert result.default_phase is not None  # for mypy
        self.assertEqual(result.default_phase.label, "Generating plan")

    def test_get_command_config_returns_config_for_up_apply(self) -> None:
        """Test get_command_config returns correct config for up_apply."""
        result = TerraformSequenceId.up_apply.get_command_config(self.manifest)

        self.assertIsNotNone(result)
        assert result is not None  # for mypy
        self.assertIsNotNone(result.default_phase)
        assert result.default_phase is not None  # for mypy
        self.assertEqual(result.default_phase.label, "Mutating resources")
        self.assertIsNotNone(result.phases)
        assert result.phases is not None  # for mypy
        self.assertEqual(len(result.phases), 1)

    def test_get_command_config_returns_config_for_down_destroy(self) -> None:
        """Test get_command_config returns correct config for down_destroy."""
        result = TerraformSequenceId.down_destroy.get_command_config(self.manifest)

        self.assertIsNotNone(result)
        assert result is not None  # for mypy
        self.assertIsNotNone(result.default_phase)
        assert result.default_phase is not None  # for mypy
        self.assertEqual(result.default_phase.label, "Evaluating resources to destroy")
        self.assertIsNotNone(result.phases)
        assert result.phases is not None  # for mypy
        self.assertEqual(len(result.phases), 1)


class TestTerraformPlanMetadataSource(unittest.TestCase):
    """Test cases for TerraformPlanMetadataSource enum."""

    def test_enum_has_expected_values(self) -> None:
        """Test that enum has all expected metadata sources."""
        self.assertEqual(TerraformPlanMetadataSource.plan_to_add.value, "plan.to_add")
        self.assertEqual(TerraformPlanMetadataSource.plan_to_change.value, "plan.to_change")
        self.assertEqual(TerraformPlanMetadataSource.plan_to_destroy.value, "plan.to_destroy")
        self.assertEqual(TerraformPlanMetadataSource.plan_to_update.value, "plan.to_update")

    def test_from_string_returns_correct_enum_for_valid_values(self) -> None:
        """Test from_string returns correct enum member for valid values."""
        self.assertEqual(
            TerraformPlanMetadataSource.from_string("plan.to_add"), TerraformPlanMetadataSource.plan_to_add
        )
        self.assertEqual(
            TerraformPlanMetadataSource.from_string("plan.to_change"), TerraformPlanMetadataSource.plan_to_change
        )
        self.assertEqual(
            TerraformPlanMetadataSource.from_string("plan.to_destroy"), TerraformPlanMetadataSource.plan_to_destroy
        )
        self.assertEqual(
            TerraformPlanMetadataSource.from_string("plan.to_update"), TerraformPlanMetadataSource.plan_to_update
        )

    def test_from_string_returns_none_for_invalid_value(self) -> None:
        """Test from_string returns None for invalid value."""
        result = TerraformPlanMetadataSource.from_string("invalid.source")

        self.assertIsNone(result)

    def test_from_string_returns_none_for_none_input(self) -> None:
        """Test from_string returns None when input is None."""
        result = TerraformPlanMetadataSource.from_string(None)

        self.assertIsNone(result)

    def test_from_string_returns_none_for_empty_string(self) -> None:
        """Test from_string returns None for empty string."""
        result = TerraformPlanMetadataSource.from_string("")

        self.assertIsNone(result)
