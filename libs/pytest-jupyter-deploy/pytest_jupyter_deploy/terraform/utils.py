"""Utilities for parsing Terraform files in E2E tests.

These helpers parse .tf files independently of python-hcl2, providing a
reference implementation that E2E tests can compare CLI output against.
"""

import re
import textwrap
from pathlib import Path

_VARIABLE_HEREDOC_RE = re.compile(
    r'variable\s+"(?P<name>[^"]+)"\s*\{[^}]*?'
    r"description\s*=\s*<<-(?P<marker>[A-Za-z_]\w*)\n(?P<body>.*?)^\s*(?P=marker)",
    re.MULTILINE | re.DOTALL,
)

_OUTPUT_INLINE_DESC_RE = re.compile(
    r'output\s+"(?P<name>[^"]+)"\s*\{[^}]*?description\s*=\s*"(?P<desc>[^"]*)"',
)


def get_variables_dot_tf_path(project_dir: Path) -> Path:
    """Return the default path to variables.tf within a Terraform-based jupyter-deploy project."""
    return project_dir / "engine" / "variables.tf"


def get_outputs_dot_tf_path(project_dir: Path) -> Path:
    """Return the default path to outputs.tf within a Terraform-based jupyter-deploy project."""
    return project_dir / "engine" / "outputs.tf"


def parse_variable_descriptions(variables_tf: Path) -> dict[str, str]:
    """Read variables.tf file, parse using regex, return the dict varname->cleaned-content.

    Only handles ``<<-MARKER`` (indented) heredoc descriptions.
    Returns a dict mapping variable name to the expanded description body.
    """
    content = variables_tf.read_text()
    result: dict[str, str] = {}
    for m in _VARIABLE_HEREDOC_RE.finditer(content):
        body = textwrap.dedent(m.group("body")).strip("\n")
        result[m.group("name")] = body
    return result


def parse_output_descriptions(outputs_tf: Path) -> dict[str, str]:
    """Read outputs.tf file, parse using regex, return the dict outputname->cleaned-content.

    Only handles inline quoted descriptions (``description = "..."``).
    Returns a dict mapping output name to its description string.
    """
    content = outputs_tf.read_text()
    return {m.group("name"): m.group("desc") for m in _OUTPUT_INLINE_DESC_RE.finditer(content)}
