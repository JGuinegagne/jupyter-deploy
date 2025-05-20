import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from jupyter_deploy.template_utils import get_terraform_templates


class TestTemplateUtils(unittest.TestCase):
    """Test class for template_utils module."""

    @patch("importlib.metadata.entry_points")
    def test_get_terraform_templates_success(self, mock_entry_points):
        """Test that get_terraform_templates correctly loads templates from entry points."""
        # Setup
        mock_entry_point1 = MagicMock()
        mock_entry_point1.name = "aws_ec2_tls-via-ngrok"
        mock_entry_point1.load.return_value = Path("/mock/template/path")
        
        mock_entry_point2 = MagicMock()
        mock_entry_point2.name = "aws_lambda_basic"
        mock_entry_point2.load.return_value = Path("/mock/lambda/path")
        
        mock_entry_points.return_value = [mock_entry_point1, mock_entry_point2]
        
        # Mock Path.exists to return True for our mock paths
        with patch("pathlib.Path.exists", return_value=True):
            # Execute
            templates = get_terraform_templates()
            
            # Assert
            self.assertEqual(len(templates), 2)
            self.assertEqual(templates["aws:ec2:tls-via-ngrok"], Path("/mock/template/path"))
            self.assertEqual(templates["aws:lambda:basic"], Path("/mock/lambda/path"))
            mock_entry_points.assert_called_once()
            mock_entry_point1.load.assert_called_once()
            mock_entry_point2.load.assert_called_once()

    @patch("importlib.metadata.entry_points")
    def test_get_terraform_templates_invalid_path(self, mock_entry_points):
        """Test that get_terraform_templates handles invalid paths."""
        # Setup
        mock_entry_point = MagicMock()
        mock_entry_point.name = "aws_ec2_tls-via-ngrok"
        mock_entry_point.load.return_value = "not_a_path"  # Invalid path
        
        mock_entry_points.return_value = [mock_entry_point]
        
        # Execute
        templates = get_terraform_templates()
        
        # Assert
        self.assertEqual(len(templates), 0)
        mock_entry_points.assert_called_once()
        mock_entry_point.load.assert_called_once()

    @patch("importlib.metadata.entry_points")
    def test_get_terraform_templates_nonexistent_path(self, mock_entry_points):
        """Test that get_terraform_templates handles paths that don't exist."""
        # Setup
        mock_entry_point = MagicMock()
        mock_entry_point.name = "aws_ec2_tls-via-ngrok"
        mock_entry_point.load.return_value = Path("/nonexistent/path")
        
        mock_entry_points.return_value = [mock_entry_point]
        
        # Mock Path.exists to return False
        with patch("pathlib.Path.exists", return_value=False):
            # Execute
            templates = get_terraform_templates()
            
            # Assert
            self.assertEqual(len(templates), 0)
            mock_entry_points.assert_called_once()
            mock_entry_point.load.assert_called_once()

    @patch("importlib.metadata.entry_points")
    def test_get_terraform_templates_load_exception(self, mock_entry_points):
        """Test that get_terraform_templates handles exceptions when loading entry points."""
        # Setup
        mock_entry_point = MagicMock()
        mock_entry_point.name = "aws_ec2_tls-via-ngrok"
        mock_entry_point.load.side_effect = Exception("Failed to load")
        
        mock_entry_points.return_value = [mock_entry_point]
        
        # Execute
        templates = get_terraform_templates()
        
        # Assert
        self.assertEqual(len(templates), 0)
        mock_entry_points.assert_called_once()
        mock_entry_point.load.assert_called_once()

    @patch("importlib.metadata.entry_points")
    def test_get_terraform_templates_entry_points_exception(self, mock_entry_points):
        """Test that get_terraform_templates handles exceptions when getting entry points."""
        # Setup
        mock_entry_points.side_effect = Exception("Failed to get entry points")
        
        # Execute
        templates = get_terraform_templates()
        
        # Assert
        self.assertEqual(len(templates), 0)
        mock_entry_points.assert_called_once()
