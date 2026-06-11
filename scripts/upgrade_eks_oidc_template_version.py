#!/usr/bin/env python3
"""
Script to upgrade version information across all files in the jupyter-deploy-tf-aws-eks-oidc template.

Usage:
    python scripts/upgrade_eks_oidc_template_version.py NEW_VERSION
"""

import argparse
import re
import sys
import tomllib
from pathlib import Path

import tomli_w


def pep440_to_semver(version: str) -> str:
    """Convert PEP 440 pre-release to SemVer (e.g. '0.1.0rc1' -> '0.1.0-rc.1')."""
    match = re.match(r"^(\d+\.\d+\.\d+)(rc|a|b)(\d+)$", version)
    if match:
        base, pre_type, pre_num = match.groups()
        return f"{base}-{pre_type}.{pre_num}"
    return version


def update_pyproject_toml(file_path: Path, new_version: str) -> None:
    """Update version in pyproject.toml file."""
    with open(file_path, "rb") as f:
        data = tomllib.load(f)

    data["project"]["version"] = new_version

    with open(file_path, "wb") as f:
        tomli_w.dump(data, f)

    print(f"✓ Updated version in {file_path}")


def update_init_py(file_path: Path, new_version: str) -> None:
    """Update __version__ in __init__.py file."""
    content = file_path.read_text()
    updated_content = re.sub(
        r'__version__\s*=\s*["\']([^"\']+)["\']',
        f'__version__ = "{new_version}"',
        content,
    )

    if content == updated_content:
        print(f"! Warning: No version pattern found in {file_path}")
    else:
        file_path.write_text(updated_content)
        print(f"✓ Updated version in {file_path}")


def update_manifest_yaml(file_path: Path, new_version: str) -> None:
    """Update version in manifest.yaml file (regex to preserve formatting)."""
    content = file_path.read_text()
    updated_content = re.sub(
        r"^(\s+version:\s*).+$",
        rf"\g<1>{new_version}",
        content,
        count=1,
        flags=re.MULTILINE,
    )

    if content == updated_content:
        print(f"! Warning: No version pattern found in {file_path}")
    else:
        file_path.write_text(updated_content)
        print(f"✓ Updated version in {file_path}")


def update_main_tf(file_path: Path, new_version: str) -> None:
    """Update template_version in main.tf file."""
    content = file_path.read_text()
    updated_content = re.sub(
        r'template_version\s*=\s*["\']([^"\']+)["\']',
        f'template_version = "{new_version}"',
        content,
    )

    if content == updated_content:
        print(f"! Warning: No template_version pattern found in {file_path}")
    else:
        file_path.write_text(updated_content)
        print(f"✓ Updated version in {file_path}")


def update_chart_yaml(file_path: Path, new_version: str) -> None:
    """Update version in a Helm Chart.yaml file (regex to preserve formatting)."""
    content = file_path.read_text()
    updated_content = re.sub(
        r"^(version:\s*).+$",
        rf"\g<1>{new_version}",
        content,
        count=1,
        flags=re.MULTILINE,
    )

    if content == updated_content:
        print(f"! Warning: No version pattern found in {file_path}")
    else:
        file_path.write_text(updated_content)
        print(f"✓ Updated version in {file_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Update version across all EKS OIDC template files.")
    parser.add_argument("new_version", help="New version string in PEP 440 format (e.g., '0.1.0rc1', '0.1.0')")

    args = parser.parse_args()
    pep440_version = args.new_version
    semver_version = pep440_to_semver(pep440_version)

    project_path = Path(__file__).parent.parent / "libs" / "jupyter-deploy-tf-aws-eks-oidc"

    if not project_path.exists():
        print(f"Error: Project path {project_path} not found")
        sys.exit(1)

    print(f"Updating versions: PEP 440 = {pep440_version}, SemVer = {semver_version}\n")

    template_path = project_path / "jupyter_deploy_tf_aws_eks_oidc" / "template"

    # Python files use PEP 440
    update_pyproject_toml(project_path / "pyproject.toml", pep440_version)
    update_init_py(project_path / "jupyter_deploy_tf_aws_eks_oidc" / "__init__.py", pep440_version)

    # Template files use SemVer (Helm requires it)
    update_manifest_yaml(template_path / "manifest.yaml", semver_version)
    update_main_tf(template_path / "engine" / "main.tf", semver_version)

    chart_dirs = ["workspace-defaults", "github-rbac"]
    for chart_dir in chart_dirs:
        update_chart_yaml(template_path / "charts" / chart_dir / "Chart.yaml", semver_version)

    print("\nVersion update completed successfully!")


if __name__ == "__main__":
    main()
