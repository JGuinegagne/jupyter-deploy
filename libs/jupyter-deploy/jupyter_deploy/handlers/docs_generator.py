import re
from pathlib import Path


class DocsGenerator:
    """Generator for documentation files in jupyter-deploy projects."""

    # Path to static init templates relative to this file
    INIT_STATIC_DIR = Path(__file__).parent / "init_static"

    def __init__(
        self,
        project_path: Path,
        engine: str,
    ) -> None:
        """Initialize the documentation generator.

        Args:
            project_path: Path to the project directory where docs will be written
            engine: Infrastructure-as-code engine (e.g., "terraform")
        """
        self.project_path = project_path
        self.engine = engine

    def generate_gitignore(self) -> None:
        """Generate .gitignore file from engine-specific template."""
        # Determine template path based on engine
        template_filename = f".gitignore.{self.engine.lower()}.template"
        template_path = self.INIT_STATIC_DIR / "gitignore" / template_filename

        # If template doesn't exist, skip generation
        if not template_path.exists():
            return

        # Read template and write to project
        template_content = template_path.read_text()
        output_path = self.project_path / ".gitignore"
        output_path.write_text(template_content)

    def generate_agent_md(self) -> None:
        """Generate AGENT.md file from template with CLI snippet substitutions."""
        # Template file in project directory (copied from source)
        template_path = self.project_path / "AGENT.md.template"

        # If template doesn't exist, skip generation
        if not template_path.exists():
            return

        # Read template
        template_content = template_path.read_text()

        # Apply substitutions
        output_content = self._substitute_agent_template_vars(template_content)

        # Write to project
        output_path = self.project_path / "AGENT.md"
        output_path.write_text(output_content)

        # Remove the template file after generation
        template_path.unlink()

    def _substitute_agent_template_vars(self, template_content: str) -> str:
        """Replace template variables in AGENT.md template.

        Args:
            template_content: The template content with placeholders

        Returns:
            Content with all placeholders replaced
        """
        agent_dir = self.INIT_STATIC_DIR / "agent"
        result = template_content

        # Find all placeholders in the template
        placeholders = re.findall(r"\{\{\s*([a-zA-Z0-9_-]+)\s*\}\}", template_content)

        # Load and substitute each snippet
        for placeholder in placeholders:
            snippet_path = agent_dir / f"{placeholder}.md"
            if snippet_path.exists():
                snippet_content = snippet_path.read_text().rstrip()
                result = result.replace(f"{{{{ {placeholder} }}}}", snippet_content)

        return result
