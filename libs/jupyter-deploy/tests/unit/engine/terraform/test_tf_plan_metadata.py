import json
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

from jupyter_deploy.engine.terraform.tf_constants import TerraformPlanMetadataSource
from jupyter_deploy.engine.terraform.tf_plan_metadata import (
    TerraformPlanMetadata,
    load_plan_metadata,
    save_plan_metadata,
)


class TestTerraformPlanMetadataSource(unittest.TestCase):
    """Test cases for TerraformPlanMetadataSource enum."""

    def test_from_string_valid_values(self) -> None:
        """Test from_string with valid enum values."""
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
        self.assertEqual(
            TerraformPlanMetadataSource.from_string("plan.to_mutate"), TerraformPlanMetadataSource.plan_to_mutate
        )

    def test_from_string_invalid_value(self) -> None:
        """Test from_string with invalid value returns None."""
        self.assertIsNone(TerraformPlanMetadataSource.from_string("invalid.source"))

    def test_from_string_none(self) -> None:
        """Test from_string with None returns None."""
        self.assertIsNone(TerraformPlanMetadataSource.from_string(None))


class TestTerraformPlanMetadata(unittest.TestCase):
    """Test cases for TerraformPlanMetadata model."""

    def test_model_initialization(self) -> None:
        """Test that TerraformPlanMetadata initializes correctly."""
        metadata = TerraformPlanMetadata(to_add=10, to_change=5, to_destroy=2)

        self.assertEqual(metadata.to_add, 10)
        self.assertEqual(metadata.to_change, 5)
        self.assertEqual(metadata.to_destroy, 2)

    def test_to_mutate_property(self) -> None:
        """Test that to_mutate property sums correctly."""
        metadata = TerraformPlanMetadata(to_add=10, to_change=5, to_destroy=2)
        self.assertEqual(metadata.to_mutate, 17)

        metadata2 = TerraformPlanMetadata(to_add=65, to_change=0, to_destroy=0)
        self.assertEqual(metadata2.to_mutate, 65)

    def test_to_update_property(self) -> None:
        """Test that to_update property sums add and change correctly."""
        metadata = TerraformPlanMetadata(to_add=10, to_change=5, to_destroy=2)
        self.assertEqual(metadata.to_update, 15)  # add + change, not destroy

        metadata2 = TerraformPlanMetadata(to_add=50, to_change=15, to_destroy=20)
        self.assertEqual(metadata2.to_update, 65)

    def test_get_value_extracts_correct_values(self) -> None:
        """Test that get_value extracts values based on source enum."""
        metadata = TerraformPlanMetadata(to_add=10, to_change=5, to_destroy=2)

        self.assertEqual(metadata.get_value(TerraformPlanMetadataSource.plan_to_add), 10)
        self.assertEqual(metadata.get_value(TerraformPlanMetadataSource.plan_to_change), 5)
        self.assertEqual(metadata.get_value(TerraformPlanMetadataSource.plan_to_destroy), 2)
        self.assertEqual(metadata.get_value(TerraformPlanMetadataSource.plan_to_update), 15)
        self.assertEqual(metadata.get_value(TerraformPlanMetadataSource.plan_to_mutate), 17)


class TestSavePlanMetadata(unittest.TestCase):
    """Test cases for save_plan_metadata function."""

    def test_saves_metadata_to_file(self) -> None:
        """Test that metadata is saved correctly to file."""
        metadata = TerraformPlanMetadata(to_add=10, to_change=5, to_destroy=2)
        file_path = Path("/mock/metadata.json")

        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", new_callable=mock_open) as mock_file,
        ):
            save_plan_metadata(metadata, file_path)

            # Verify directory creation was attempted
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

            # Verify file was opened for writing
            mock_file.assert_called_once_with(file_path, "w")

            # Verify JSON was written
            handle = mock_file()
            written_data = "".join(call[0][0] for call in handle.write.call_args_list)
            data = json.loads(written_data)

            self.assertEqual(data["to_add"], 10)
            self.assertEqual(data["to_change"], 5)
            self.assertEqual(data["to_destroy"], 2)

    def test_creates_parent_directory(self) -> None:
        """Test that parent directories are created if they don't exist."""
        nested_path = Path("/mock/subdir/nested/metadata.json")
        metadata = TerraformPlanMetadata(to_add=1, to_change=2, to_destroy=3)

        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", new_callable=mock_open),
        ):
            save_plan_metadata(metadata, nested_path)

            # Verify mkdir was called with correct parameters
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


class TestLoadPlanMetadata(unittest.TestCase):
    """Test cases for load_plan_metadata function."""

    def test_loads_metadata_from_file(self) -> None:
        """Test that metadata is loaded correctly from file."""
        file_path = Path("/mock/metadata.json")
        json_content = json.dumps({"to_add": 10, "to_change": 5, "to_destroy": 2})

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=json_content)),
        ):
            # Load it back
            loaded = load_plan_metadata(file_path)

            self.assertIsNotNone(loaded)
            assert loaded is not None  # for mypy
            self.assertEqual(loaded.to_add, 10)
            self.assertEqual(loaded.to_change, 5)
            self.assertEqual(loaded.to_destroy, 2)
            self.assertEqual(loaded.to_mutate, 17)

    def test_returns_none_when_file_does_not_exist(self) -> None:
        """Test that load returns None when file doesn't exist."""
        nonexistent_path = Path("/mock/nonexistent_metadata_file.json")

        with patch("pathlib.Path.exists", return_value=False):
            result = load_plan_metadata(nonexistent_path)
            self.assertIsNone(result)

    def test_returns_none_when_file_has_invalid_json(self) -> None:
        """Test that load returns None when file contains invalid JSON."""
        file_path = Path("/mock/metadata.json")
        invalid_json = "not valid json {"

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=invalid_json)),
        ):
            result = load_plan_metadata(file_path)
            self.assertIsNone(result)

    def test_returns_none_when_file_has_invalid_data(self) -> None:
        """Test that load returns None when file has wrong structure."""
        file_path = Path("/mock/metadata.json")
        invalid_structure = json.dumps({"invalid": "structure"})

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=invalid_structure)),
        ):
            result = load_plan_metadata(file_path)
            self.assertIsNone(result)
