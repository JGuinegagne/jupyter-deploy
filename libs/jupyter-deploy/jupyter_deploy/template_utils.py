"""Template utilities for jupyter-deploy."""

import importlib.metadata
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

# Entry point group for terraform templates
TERRAFORM_TEMPLATES_ENTRY_POINT = "jupyter_deploy.terraform_templates"


def get_terraform_templates() -> Dict[str, Path]:
    """Get all registered terraform templates from entry points.

    Returns:
        Dict[str, Path]: A dictionary mapping template names to their paths.
    """
    templates = {}

    try:
        for entry_point in importlib.metadata.entry_points(group=TERRAFORM_TEMPLATES_ENTRY_POINT):
            try:
                template_path = entry_point.load()
                if isinstance(template_path, Path) and template_path.exists():
                    # Convert entry point name to template format, ex. aws_ec2_tls-via-ngrok -> aws:ec2:tls-via-ngrok
                    template_name = entry_point.name.replace("_", ":")
                    templates[template_name] = template_path
                    logger.debug(f"Loaded template {template_name} from {template_path}")
                else:
                    logger.warning(f"Template path for {entry_point.name} is not a valid Path or does not exist")
            except Exception as e:
                logger.warning(f"Failed to load template from {entry_point.name}: {e}")
    except Exception as e:
        logger.warning(f"Failed to load templates from entry points: {e}")

    return templates


TEMPLATES = get_terraform_templates()
