#!/usr/bin/env python3
"""
Poetry Package Manager (Python)

Enterprise-grade Python package management using Poetry.

Design Patterns:
- Template Method: Inherits from BuildManagerBase
- Exception Wrapper: All errors properly wrapped
- Strategy Pattern: Modern Python dependency management
"""

from pathlib import Path
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from enum import Enum
import re
import toml

from artemis_exceptions import wrap_exception
from build_system_exceptions import (
    BuildSystemNotFoundError,
    ProjectConfigurationError,
    BuildExecutionError,
    TestExecutionError,
    DependencyInstallError
)
from build_manager_base import BuildManagerBase, BuildResult
from build_manager_factory import register_build_manager, BuildSystem


class DependencyGroup(Enum):
    """Poetry dependency groups"""
    MAIN = "main"
    DEV = "dev"
    TEST = "test"
    DOCS = "docs"


@dataclass
class PoetryProjectInfo:
    """Poetry pyproject.toml project information"""
    name: str
    version: str
    description: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    license: Optional[str] = None
    readme: Optional[str] = None
    python_version: str = "^3.8"
    dependencies: Dict[str, Any] = field(default_factory=dict)
    dev_dependencies: Dict[str, Any] = field(default_factory=dict)
    scripts: Dict[str, str] = field(default_factory=dict)
    has_lock_file: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "authors": self.authors,
            "license": self.license,
            "readme": self.readme,
            "pythonVersion": self.python_version,
            "dependencies": self.dependencies,
            "devDependencies": self.dev_dependencies,
            "scripts": self.scripts,
            "hasLockFile": self.has_lock_file
        }


@register_build_manager(BuildSystem.POETRY)
class PoetryManager(BuildManagerBase):
    """
    Enterprise-grade Poetry manager for Python projects.

    Example:
        poetry = PoetryManager(project_dir="/path/to/project")
        result = poetry.build()
        test_result = poetry.test()
    """

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        logger: Optional['logging.Logger'] = None
    ):
        """
        Initialize Poetry manager.

        Args:
            project_dir: Project directory (contains pyproject.toml)
            logger: Logger instance

        Raises:
            BuildSystemNotFoundError: If Poetry not found
            ProjectConfigurationError: If pyproject.toml invalid
        """
        self.pyproject_path = None
        self.poetry_lock_path = None

        super().__init__(project_dir, logger)

        self.poetry_lock_path = self.project_dir / "poetry.lock"

    @wrap_exception(BuildSystemNotFoundError, "Poetry not found")
    def _validate_installation(self) -> None:
        """
        Validate Poetry is installed.

        Raises:
            BuildSystemNotFoundError: If Poetry not in PATH
        """
        result = self._execute_command(
            ["poetry", "--version"],
            timeout=10,
            error_type=BuildSystemNotFoundError,
            error_message="Poetry not installed or not in PATH"
        )

        # Extract version
        version_match = re.search(r"Poetry (?:version )?(\d+\.\d+\.\d+)", result.output)
        if version_match:
            version = version_match.group(1)
            self.logger.info(f"Using Poetry version: {version}")

    @wrap_exception(ProjectConfigurationError, "Invalid Poetry project")
    def _validate_project(self) -> None:
        """
        Validate pyproject.toml exists and contains [tool.poetry] section.

        Raises:
            ProjectConfigurationError: If pyproject.toml missing or invalid
        """
        self.pyproject_path = self.project_dir / "pyproject.toml"

        if not self.pyproject_path.exists():
            raise ProjectConfigurationError(
                "pyproject.toml not found",
                {"project_dir": str(self.project_dir)}
            )

        # Verify it's a Poetry project
        with open(self.pyproject_path, 'r') as f:
            data = toml.load(f)

        if "tool" not in data or "poetry" not in data.get("tool", {}):
            raise ProjectConfigurationError(
                "pyproject.toml is not a Poetry project (missing [tool.poetry])",
                {"project_dir": str(self.project_dir)}
            )

    @wrap_exception(ProjectConfigurationError, "Failed to parse pyproject.toml")
    def get_project_info(self) -> Dict[str, Any]:
        """
        Parse pyproject.toml for project information.

        Returns:
            Dict with project information

        Raises:
            ProjectConfigurationError: If pyproject.toml malformed
        """
        with open(self.pyproject_path, 'r') as f:
            data = toml.load(f)

        poetry_section = data.get("tool", {}).get("poetry", {})

        info = PoetryProjectInfo(
            name=poetry_section.get("name", ""),
            version=poetry_section.get("version", "0.1.0"),
            description=poetry_section.get("description"),
            authors=poetry_section.get("authors", []),
            license=poetry_section.get("license"),
            readme=poetry_section.get("readme"),
            python_version=poetry_section.get("dependencies", {}).get("python", "^3.8"),
            dependencies=poetry_section.get("dependencies", {}),
            dev_dependencies=poetry_section.get("dev-dependencies", {}),
            scripts=poetry_section.get("scripts", {}),
            has_lock_file=self.poetry_lock_path.exists()
        )

        return info.to_dict()

    @wrap_exception(BuildExecutionError, "Poetry build failed")
    def build(self, format: str = "wheel", **kwargs) -> BuildResult:
        """
        Build Python package with Poetry.

        Args:
            format: Build format ("wheel", "sdist", or "all")

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If build fails

        Example:
            result = poetry.build(format="wheel")
        """
        cmd = ["poetry", "build"]

        if format == "wheel":
            cmd.append("--format=wheel")
        elif format == "sdist":
            cmd.append("--format=sdist")
        # "all" builds both by default

        return self._execute_command(
            cmd,
            timeout=300,
            error_type=BuildExecutionError,
            error_message="Poetry build failed"
        )

    @wrap_exception(TestExecutionError, "Poetry tests failed")
    def test(
        self,
        test_path: Optional[str] = None,
        verbose: bool = False,
        **kwargs
    ) -> BuildResult:
        """
        Run tests with Poetry (uses pytest by default).

        Args:
            test_path: Specific test file or directory
            verbose: Verbose output

        Returns:
            BuildResult with test statistics

        Raises:
            TestExecutionError: If tests fail

        Example:
            result = poetry.test(verbose=True)
        """
        cmd = ["poetry", "run", "pytest"]

        if verbose:
            cmd.append("-v")

        if test_path:
            cmd.append(test_path)

        return self._execute_command(
            cmd,
            timeout=300,
            error_type=TestExecutionError,
            error_message="Test execution failed"
        )

    @wrap_exception(DependencyInstallError, "Failed to add dependency")
    def install_dependency(
        self,
        package: str,
        version: Optional[str] = None,
        group: str = "main",
        **kwargs
    ) -> bool:
        """
        Add a dependency to pyproject.toml.

        Args:
            package: Package name
            version: Package version (optional)
            group: Dependency group (main, dev, test, docs)

        Returns:
            True if successful

        Raises:
            DependencyInstallError: If installation fails

        Example:
            poetry.install_dependency("requests", version="^2.28.0")
            poetry.install_dependency("pytest", group="dev")
        """
        cmd = ["poetry", "add", package]

        if version:
            cmd[-1] = f"{package}@{version}"

        if group == "dev":
            cmd.append("--group=dev")
        elif group != "main":
            cmd.append(f"--group={group}")

        result = self._execute_command(
            cmd,
            timeout=120,
            error_type=DependencyInstallError,
            error_message=f"Failed to add package {package}"
        )

        self.logger.info(f"Added package {package}")
        return True

    @wrap_exception(BuildExecutionError, "Failed to install dependencies")
    def install_dependencies(
        self,
        no_dev: bool = False,
        sync: bool = False
    ) -> BuildResult:
        """
        Install all dependencies from pyproject.toml.

        Args:
            no_dev: Skip dev dependencies
            sync: Remove packages not in lock file

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If install fails

        Example:
            poetry.install_dependencies()
        """
        cmd = ["poetry", "install"]

        if no_dev:
            cmd.append("--no-dev")

        if sync:
            cmd.append("--sync")

        return self._execute_command(
            cmd,
            timeout=300,
            error_type=BuildExecutionError,
            error_message="Dependency installation failed"
        )

    @wrap_exception(BuildExecutionError, "Failed to update dependencies")
    def update_dependencies(
        self,
        package: Optional[str] = None,
        dry_run: bool = False
    ) -> BuildResult:
        """
        Update dependencies.

        Args:
            package: Specific package to update (None = all)
            dry_run: Show what would be updated without updating

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If update fails

        Example:
            poetry.update_dependencies()  # Update all
            poetry.update_dependencies(package="requests")  # Update specific
        """
        cmd = ["poetry", "update"]

        if package:
            cmd.append(package)

        if dry_run:
            cmd.append("--dry-run")

        return self._execute_command(
            cmd,
            timeout=300,
            error_type=BuildExecutionError,
            error_message="Dependency update failed"
        )

    @wrap_exception(BuildExecutionError, "Failed to run Poetry command")
    def run_script(self, script_name: str) -> BuildResult:
        """
        Run a script defined in pyproject.toml.

        Args:
            script_name: Script name from [tool.poetry.scripts]

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If script fails

        Example:
            poetry.run_script("serve")
        """
        cmd = ["poetry", "run", script_name]

        return self._execute_command(
            cmd,
            timeout=600,
            error_type=BuildExecutionError,
            error_message=f"Script '{script_name}' failed"
        )

    @wrap_exception(BuildExecutionError, "Failed to show package info")
    def show_package_info(self, package: str) -> BuildResult:
        """
        Show information about a package.

        Args:
            package: Package name

        Returns:
            BuildResult with package information

        Raises:
            BuildExecutionError: If command fails

        Example:
            result = poetry.show_package_info("requests")
        """
        cmd = ["poetry", "show", package]

        return self._execute_command(
            cmd,
            timeout=30,
            error_type=BuildExecutionError,
            error_message=f"Failed to show info for {package}"
        )

    def _extract_test_stats(self, output: str) -> Dict[str, int]:
        """
        Extract test statistics from pytest output.

        Args:
            output: pytest output

        Returns:
            Dict with test statistics
        """
        stats = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'tests_skipped': 0
        }

        # pytest summary: "5 passed, 2 failed, 1 skipped in 2.34s"
        summary_match = re.search(
            r"(\d+)\s+passed(?:,\s+(\d+)\s+failed)?(?:,\s+(\d+)\s+skipped)?",
            output
        )

        if summary_match:
            passed = int(summary_match.group(1))
            failed = int(summary_match.group(2) or 0)
            skipped = int(summary_match.group(3) or 0)

            stats['tests_passed'] = passed
            stats['tests_failed'] = failed
            stats['tests_skipped'] = skipped
            stats['tests_run'] = passed + failed

        return stats


# CLI interface
if __name__ == "__main__":
    import argparse
    import logging
    import sys
    import json

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description="Poetry Manager")
    parser.add_argument("--project-dir", default=".", help="Project directory")
    parser.add_argument("command", choices=["info", "build", "test", "install", "update", "add", "show", "run"],
                       help="Command to execute")
    parser.add_argument("--package", help="Package name")
    parser.add_argument("--version", help="Package version")
    parser.add_argument("--group", default="main", help="Dependency group")
    parser.add_argument("--format", default="wheel", help="Build format")
    parser.add_argument("--script", help="Script name to run")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    try:
        poetry = PoetryManager(project_dir=args.project_dir)

        if args.command == "info":
            info = poetry.get_project_info()
            print(json.dumps(info, indent=2))

        elif args.command == "build":
            result = poetry.build(format=args.format)
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "test":
            result = poetry.test(verbose=args.verbose)
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "install":
            result = poetry.install_dependencies()
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "update":
            result = poetry.update_dependencies(package=args.package)
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "add":
            if not args.package:
                print("Error: --package required for add command")
                sys.exit(1)
            poetry.install_dependency(args.package, version=args.version, group=args.group)
            print(f"Added {args.package}")

        elif args.command == "show":
            if not args.package:
                print("Error: --package required for show command")
                sys.exit(1)
            result = poetry.show_package_info(args.package)
            print(result.output)

        elif args.command == "run":
            if not args.script:
                print("Error: --script required for run command")
                sys.exit(1)
            result = poetry.run_script(args.script)
            print(result)
            sys.exit(0 if result.success else 1)

    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)
