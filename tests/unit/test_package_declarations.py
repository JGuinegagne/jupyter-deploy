"""Guard the repo-level lists that enumerate the workspace packages.

Six places name every package: the uv workspace members, mypy's `files` and `mypy_path`, pytest's
`pythonpath`, the CI change detector's `LIB_PATHS`, and the README package list. Adding a package
means editing all six, and nothing fails when one is missed -- it just silently stops being covered.
`LIB_PATHS` is the costly one: a package it omits never gets linted or tested on its own, so a
dependency the package uses but never declares keeps resolving from the workspace root install and
only surfaces in that package's release workflow.

The source of truth here is the filesystem: `libs/*/pyproject.toml`.
"""

import importlib.util
import re
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
ROOT_PYPROJECT = REPO_ROOT / "pyproject.toml"
MODIFIED_DIRS_SCRIPT = REPO_ROOT / ".github" / "utils" / "get_modified_dirs.py"


def declared_packages() -> set[str]:
    """Return every workspace package as a repo-relative path, discovered from disk."""
    return {f"libs/{path.parent.name}" for path in REPO_ROOT.glob("libs/*/pyproject.toml")}


def root_config() -> dict:
    with open(ROOT_PYPROJECT, "rb") as f:
        return tomllib.load(f)


def lib_paths() -> list[str]:
    """Import LIB_PATHS from the CI change detector, which is not an importable package."""
    spec = importlib.util.spec_from_file_location("get_modified_dirs", MODIFIED_DIRS_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.LIB_PATHS)


class TestDeclaredPackages(unittest.TestCase):
    def test_every_package_dir_has_a_readme(self) -> None:
        for package in sorted(declared_packages()):
            self.assertTrue((REPO_ROOT / package / "README.md").is_file(), f"{package} has no README.md")

    def test_packages_are_discovered(self) -> None:
        # A sanity floor: if the glob silently matched nothing, every assertion below would pass.
        self.assertGreaterEqual(len(declared_packages()), 5)


class TestCiChangeDetectorLibPaths(unittest.TestCase):
    """`.github/utils/get_modified_dirs.py` decides which dirs CI lints and tests per package."""

    def test_lib_paths_match_declared_packages(self) -> None:
        self.assertEqual(sorted(declared_packages()), sorted(lib_paths()))

    def test_lib_paths_has_no_duplicates(self) -> None:
        paths = lib_paths()
        self.assertEqual(len(paths), len(set(paths)))


class TestRootPyprojectPackageLists(unittest.TestCase):
    def test_workspace_members_match_declared_packages(self) -> None:
        members = root_config()["tool"]["uv"]["workspace"]["members"]
        self.assertEqual(sorted(declared_packages()), sorted(members))

    def test_pytest_pythonpath_matches_declared_packages(self) -> None:
        pythonpath = root_config()["tool"]["pytest"]["ini_options"]["pythonpath"]
        self.assertEqual(sorted(declared_packages()), sorted(pythonpath))

    def test_mypy_files_covers_every_package(self) -> None:
        # `files` also lists non-package dirs (scripts, tests), so this is a containment check.
        files = set(root_config()["tool"]["mypy"]["files"])
        self.assertEqual(set(), declared_packages() - files)

    def test_mypy_path_covers_every_package(self) -> None:
        mypy_path = set(root_config()["tool"]["mypy"]["mypy_path"])
        self.assertEqual(set(), declared_packages() - mypy_path)

    def test_mypy_lists_name_only_real_packages(self) -> None:
        mypy = root_config()["tool"]["mypy"]
        # Entries naming a `libs/<package>` directly, as opposed to a path inside one.
        for key in ("files", "mypy_path"):
            for entry in mypy[key]:
                if re.fullmatch(r"libs/[^/]+", entry):
                    self.assertIn(entry, declared_packages(), f"mypy {key} names unknown package {entry}")


class TestReadmePackageList(unittest.TestCase):
    def test_readme_links_every_package(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text()
        for package in sorted(declared_packages()):
            self.assertIn(f"(./{package}/README.md)", readme, f"README.md does not link {package}")
