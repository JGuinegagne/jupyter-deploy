import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from jupyter_deploy.engine.enum import EngineType
from jupyter_deploy.handlers.project.project_handler import ProjectHandler


class TestProjectHandler(unittest.TestCase):
    """Test cases for ProjectHandler class."""

    @patch("jupyter_deploy.handlers.project.project_handler.fs_utils")
    @patch("jupyter_deploy.handlers.project.project_handler.TEMPLATES", {"aws:ec2:tls-via-ngrok": Path("/mock/template/path")})
    def test_init_with_default_project_dir(self, mock_fs_utils):
        """Test initialization with default project directory."""
        # Setup
        mock_fs_utils.get_default_project_path.return_value = Path("/default/project/path")
        
        # Execute
        handler = ProjectHandler(project_dir=None)
        
        # Assert
        self.assertEqual(handler.project_path, Path("/default/project/path"))
        self.assertEqual(handler.engine, EngineType.TERRAFORM)
        self.assertEqual(handler.source_path, Path("/mock/template/path"))
        mock_fs_utils.get_default_project_path.assert_called_once()

    @patch("jupyter_deploy.handlers.project.project_handler.TEMPLATES", {"aws:ec2:tls-via-ngrok": Path("/mock/template/path")})
    def test_init_with_custom_project_dir(self):
        """Test initialization with custom project directory."""
        # Execute
        handler = ProjectHandler(project_dir="/custom/project/path")
        
        # Assert
        self.assertEqual(handler.project_path, Path("/custom/project/path"))
        self.assertEqual(handler.engine, EngineType.TERRAFORM)
        self.assertEqual(handler.source_path, Path("/mock/template/path"))

    @patch("jupyter_deploy.handlers.project.project_handler.TEMPLATES", {"aws:ec2:tls-via-ngrok": Path("/mock/template/path")})
    def test_init_with_custom_engine(self):
        """Test initialization with custom engine."""
        # Execute
        handler = ProjectHandler(
            project_dir="/custom/project/path",
            engine=EngineType.TERRAFORM
        )
        
        # Assert
        self.assertEqual(handler.project_path, Path("/custom/project/path"))
        self.assertEqual(handler.engine, EngineType.TERRAFORM)
        self.assertEqual(handler.source_path, Path("/mock/template/path"))

    @patch("jupyter_deploy.handlers.project.project_handler.TEMPLATES", {"custom:infra:template": Path("/custom/template/path")})
    def test_init_with_custom_template(self):
        """Test initialization with custom template parameters."""
        # Execute
        handler = ProjectHandler(
            project_dir="/custom/project/path",
            provider="custom",
            infra="infra",
            template="template"
        )
        
        # Assert
        self.assertEqual(handler.project_path, Path("/custom/project/path"))
        self.assertEqual(handler.source_path, Path("/custom/template/path"))

    @patch("jupyter_deploy.handlers.project.project_handler.TEMPLATES", {"aws:ec2:tls-via-ngrok": Path("/mock/template/path")})
    def test_find_template_path_success(self):
        """Test finding template path with valid template name."""
        # Setup
        handler = ProjectHandler(project_dir="/custom/project/path")
        
        # Execute
        path = handler._find_template_path("aws:ec2:tls-via-ngrok")
        
        # Assert
        self.assertEqual(path, Path("/mock/template/path"))

    @patch("jupyter_deploy.handlers.project.project_handler.TEMPLATES", {"aws:ec2:tls-via-ngrok": Path("/mock/template/path")})
    def test_find_template_path_empty_name(self):
        """Test finding template path with empty template name."""
        # Setup
        handler = ProjectHandler(project_dir="/custom/project/path")
        
        # Execute and Assert
        with self.assertRaises(ValueError) as context:
            handler._find_template_path("")
        
        self.assertEqual(str(context.exception), "Template name cannot be empty")

    @patch("jupyter_deploy.handlers.project.project_handler.TEMPLATES", {"aws:ec2:tls-via-ngrok": Path("/mock/template/path")})
    def test_find_template_path_not_found(self):
        """Test finding template path with non-existent template name."""
        # Setup
        handler = ProjectHandler(project_dir="/custom/project/path")
        
        # Execute and Assert
        with self.assertRaises(ValueError) as context:
            handler._find_template_path("nonexistent:template")
        
        self.assertIn("Template 'nonexistent:template' not found", str(context.exception))
        self.assertIn("['aws:ec2:tls-via-ngrok']", str(context.exception))

    @patch("jupyter_deploy.handlers.project.project_handler.TEMPLATES", {"aws:ec2:tls-via-ngrok": Path("/mock/template/path")})
    def test_may_export_to_project_path_nonexistent(self):
        """Test may_export_to_project_path with non-existent project path."""
        # Setup
        handler = ProjectHandler(project_dir="/nonexistent/path")
        with patch.object(Path, "exists", return_value=False):
            # Execute
            result = handler.may_export_to_project_path()
            
            # Assert
            self.assertTrue(result)

    @patch("jupyter_deploy.handlers.project.project_handler.TEMPLATES", {"aws:ec2:tls-via-ngrok": Path("/mock/template/path")})
    def test_may_export_to_project_path_empty(self):
        """Test may_export_to_project_path with empty project path."""
        # Setup
        handler = ProjectHandler(project_dir="/empty/path")
        with patch.object(Path, "exists", return_value=True):
            with patch("jupyter_deploy.handlers.project.project_handler.fs_utils.is_empty_dir", return_value=True):
                # Execute
                result = handler.may_export_to_project_path()
                
                # Assert
                self.assertTrue(result)

    @patch("jupyter_deploy.handlers.project.project_handler.TEMPLATES", {"aws:ec2:tls-via-ngrok": Path("/mock/template/path")})
    def test_may_export_to_project_path_not_empty(self):
        """Test may_export_to_project_path with non-empty project path."""
        # Setup
        handler = ProjectHandler(project_dir="/nonempty/path")
        with patch.object(Path, "exists", return_value=True):
            with patch("jupyter_deploy.handlers.project.project_handler.fs_utils.is_empty_dir", return_value=False):
                # Execute
                result = handler.may_export_to_project_path()
                
                # Assert
                self.assertFalse(result)

    @patch("jupyter_deploy.handlers.project.project_handler.TEMPLATES", {"aws:ec2:tls-via-ngrok": Path("/mock/template/path")})
    @patch("jupyter_deploy.handlers.project.project_handler.fs_utils.safe_clean_directory")
    def test_clear_project_path(self, mock_safe_clean_directory):
        """Test clear_project_path."""
        # Setup
        handler = ProjectHandler(project_dir="/project/path")
        
        # Execute
        handler.clear_project_path()
        
        # Assert
        mock_safe_clean_directory.assert_called_once_with(Path("/project/path"))

    @patch("jupyter_deploy.handlers.project.project_handler.TEMPLATES", {"aws:ec2:tls-via-ngrok": Path("/mock/template/path")})
    @patch("jupyter_deploy.handlers.project.project_handler.fs_utils.safe_copy_tree")
    def test_setup(self, mock_safe_copy_tree):
        """Test setup."""
        # Setup
        handler = ProjectHandler(project_dir="/project/path")
        handler.source_path = Path("/source/path")
        
        # Execute
        handler.setup()
        
        # Assert
        mock_safe_copy_tree.assert_called_once_with(Path("/source/path"), Path("/project/path"))

    @patch("jupyter_deploy.handlers.project.project_handler.TEMPLATES", {})
    def test_init_with_empty_templates(self):
        """Test initialization with empty templates dictionary."""
        # Execute and Assert
        with self.assertRaises(ValueError) as context:
            ProjectHandler(project_dir="/custom/project/path")
        
        self.assertIn("Template 'aws:ec2:tls-via-ngrok' not found", str(context.exception))
        self.assertIn("[]", str(context.exception))
