"""Template utilities for jupyter-deploy."""

import importlib.metadata
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

TEMPLATE_ENTRY_POINTS = {
    "terraform": "jupyter_deploy.terraform_templates",
}


def get_templates(engine: str) -> dict[str, Path]:
    """Get all registered templates for a specific engine from entry points.

    Args:
        engine: The engine type (e.g., "terraform")

    Returns:
        Dict[str, Path]: A dictionary mapping template names to their paths.
    """
    templates: dict[str, Path] = {}
    engine_lower = engine.lower()

    if engine_lower not in TEMPLATE_ENTRY_POINTS:
        logger.warning(f"No entry point defined for engine: {engine}")
        return templates

    entry_point_group = TEMPLATE_ENTRY_POINTS[engine_lower]

    try:
        for entry_point in importlib.metadata.entry_points(group=entry_point_group):
            try:
                template_path = entry_point.load()
                if isinstance(template_path, Path) and template_path.exists():
                    # Convert entry point name to template format, ex. aws_ec2_tls-via-ngrok -> aws:ec2:tls-via-ngrok
                    template_name = entry_point.name.replace("_", ":")
                    templates[template_name] = template_path
                    logger.debug(f"Loaded {engine} template {template_name} from {template_path}")
                else:
                    logger.warning(f"Template path for {entry_point.name} is not a valid Path or does not exist")
            except Exception as e:
                logger.warning(f"Failed to load template from {entry_point.name}: {e}")
    except Exception as e:
        logger.warning(f"Failed to load templates from entry points: {e}")

    return templates


TEMPLATES: dict[str, dict[str, Path]] = {engine: {} for engine in TEMPLATE_ENTRY_POINTS}

for engine in TEMPLATE_ENTRY_POINTS:
    TEMPLATES[engine] = get_templates(engine)
