#!/usr/bin/env python3
"""
npm/yarn/pnpm Package Manager

Enterprise-grade JavaScript/TypeScript package management.

Supports:
- npm (Node Package Manager)
- yarn (Facebook's npm alternative)
- pnpm (Performant npm)

Design Patterns:
- Strategy Pattern: Different package managers, same interface
- Factory Pattern: Auto-detect which manager to use
- Exception Wrapper: All errors properly wrapped
- Template Method: Inherits from BuildManagerBase
"""

from pathlib import Path
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import re

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


class PackageManager(Enum):
    """JavaScript package managers"""
    NPM = "npm"
    YARN = "yarn"
    PNPM = "pnpm"


@dataclass
class NpmProjectInfo:
    """npm/package.json project information"""
    name: str
    version: str
    description: Optional[str] = None
    dependencies: Dict[str, str] = field(default_factory=dict)
    dev_dependencies: Dict[str, str] = field(default_factory=dict)
    scripts: Dict[str, str] = field(default_factory=dict)
    package_manager: PackageManager = PackageManager.NPM
    engines: Dict[str, str] = field(default_factory=dict)
    license: Optional[str] = None
    repository: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "dependencies": self.dependencies,
            "devDependencies": self.dev_dependencies,
            "scripts": self.scripts,
            "packageManager": self.package_manager.value,
            "engines": self.engines,
            "license": self.license,
            "repository": self.repository
        }


@register_build_manager(BuildSystem.NPM)
class NpmManager(BuildManagerBase):
    """
    Enterprise-grade npm/yarn/pnpm manager.

    Auto-detects package manager from lock files.
    Provides unified interface for all three.

    Example:
        npm = NpmManager(project_dir="/path/to/project")
        result = npm.build(script_name="build", production=True)
        test_result = npm.test(coverage=True)
    """

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        logger: Optional['logging.Logger'] = None
    ):
        """
        Initialize npm manager.

        Auto-detects npm/yarn/pnpm from lock files.

        Args:
            project_dir: Project directory
            logger: Logger instance

        Raises:
            BuildSystemNotFoundError: If package manager not found
            ProjectConfigurationError: If package.json invalid
        """
        # Auto-detect package manager BEFORE calling super().__init__()
        # because super().__init__() calls _validate_installation()
        project_path = Path(project_dir) if project_dir else Path.cwd()
        self.package_manager = self._detect_package_manager(project_path)
        self.package_json_path = project_path / "package.json"

        # Now call parent constructor
        super().__init__(project_dir, logger)

    def _detect_package_manager(self, project_dir: Path) -> PackageManager:
        """
        Auto-detect package manager from lock files.

        Args:
            project_dir: Project directory

        Returns:
            PackageManager enum
        """
        # Check lock files (most specific first)
        if (project_dir / "pnpm-lock.yaml").exists():
            return PackageManager.PNPM
        elif (project_dir / "yarn.lock").exists():
            return PackageManager.YARN
        else:
            # Default to npm
            return PackageManager.NPM

    @wrap_exception(BuildSystemNotFoundError, "Package manager not found")
    def _validate_installation(self) -> None:
        """
        Validate package manager is installed.

        Raises:
            BuildSystemNotFoundError: If package manager not in PATH
        """
        cmd = self.package_manager.value
        result = self._execute_command(
            [cmd, "--version"],
            timeout=10,
            error_type=BuildSystemNotFoundError,
            error_message=f"{cmd} not installed or not in PATH"
        )

        version = result.output.strip()
        self.logger.info(f"Using {cmd} version: {version}")

    @wrap_exception(ProjectConfigurationError, "Invalid project configuration")
    def _validate_project(self) -> None:
        """
        Validate package.json exists.

        Raises:
            ProjectConfigurationError: If package.json missing
        """
        if not self.package_json_path.exists():
            raise ProjectConfigurationError(
                "package.json not found",
                {"project_dir": str(self.project_dir)}
            )

    @wrap_exception(ProjectConfigurationError, "Failed to parse package.json")
    def get_project_info(self) -> Dict[str, Any]:
        """
        Parse package.json.

        Returns:
            Dict with project information

        Raises:
            ProjectConfigurationError: If package.json malformed
        """
        with open(self.package_json_path, 'r') as f:
            data = json.load(f)

        info = NpmProjectInfo(
            name=data.get("name", ""),
            version=data.get("version", "0.0.0"),
            description=data.get("description"),
            dependencies=data.get("dependencies", {}),
            dev_dependencies=data.get("devDependencies", {}),
            scripts=data.get("scripts", {}),
            package_manager=self.package_manager,
            engines=data.get("engines", {}),
            license=data.get("license"),
            repository=data.get("repository")
        )

        return info.to_dict()

    @wrap_exception(BuildExecutionError, "Build failed")
    def build(
        self,
        script_name: str = "build",
        production: bool = False,
        timeout: int = 600
    ) -> BuildResult:
        """
        Run npm build script.

        Args:
            script_name: Script name from package.json (default: "build")
            production: Build for production
            timeout: Build timeout in seconds

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If build fails

        Example:
            result = npm.build(script_name="build:prod", production=True)
        """
        # Check if script exists
        info = self.get_project_info()
        if script_name not in info.get("scripts", {}):
            self.logger.warning(f"Script '{script_name}' not found in package.json")

        # Build command
        cmd = [self.package_manager.value, "run", script_name]

        # Add production flag for npm
        if production and self.package_manager == PackageManager.NPM:
            cmd.append("--production")

        return self._execute_command(
            cmd,
            timeout=timeout,
            error_type=BuildExecutionError,
            error_message=f"{script_name} script failed"
        )

    @wrap_exception(TestExecutionError, "Tests failed")
    def test(
        self,
        watch: bool = False,
        coverage: bool = False,
        timeout: int = 300
    ) -> BuildResult:
        """
        Run npm test.

        Args:
            watch: Run in watch mode (not supported with subprocess)
            coverage: Generate coverage report
            timeout: Test timeout in seconds

        Returns:
            BuildResult with test statistics

        Raises:
            TestExecutionError: If tests fail

        Example:
            result = npm.test(coverage=True)
        """
        cmd = [self.package_manager.value, "test"]

        # Coverage flag
        if coverage:
            cmd.append("--coverage")

        # Watch mode not supported in subprocess
        if watch:
            self.logger.warning("Watch mode not supported in automated execution")

        return self._execute_command(
            cmd,
            timeout=timeout,
            error_type=TestExecutionError,
            error_message="Test execution failed"
        )

    @wrap_exception(DependencyInstallError, "Failed to install dependency")
    def install_dependency(
        self,
        package: str,
        version: Optional[str] = None,
        dev: bool = False,
        **kwargs
    ) -> bool:
        """
        Install a dependency.

        Args:
            package: Package name
            version: Package version (optional)
            dev: Install as dev dependency

        Returns:
            True if successful

        Raises:
            DependencyInstallError: If installation fails

        Example:
            npm.install_dependency("react", version="18.2.0")
            npm.install_dependency("typescript", dev=True)
        """
        cmd = [self.package_manager.value]

        # Command verb differs by package manager
        if self.package_manager == PackageManager.NPM:
            cmd.append("install")
        elif self.package_manager in [PackageManager.YARN, PackageManager.PNPM]:
            cmd.append("add")

        # Add package with version
        if version:
            cmd.append(f"{package}@{version}")
        else:
            cmd.append(package)

        # Dev dependency flag
        if dev:
            if self.package_manager == PackageManager.NPM:
                cmd.append("--save-dev")
            elif self.package_manager in [PackageManager.YARN, PackageManager.PNPM]:
                cmd.append("--dev")

        result = self._execute_command(
            cmd,
            timeout=120,
            error_type=DependencyInstallError,
            error_message=f"Failed to install {package}"
        )

        self.logger.info(f"Installed {package}")
        return True

    @wrap_exception(BuildExecutionError, "Install failed")
    def install_dependencies(self, production: bool = False) -> BuildResult:
        """
        Install all dependencies from package.json.

        Args:
            production: Install only production dependencies

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If install fails

        Example:
            npm.install_dependencies(production=True)
        """
        cmd = [self.package_manager.value, "install"]

        if production:
            cmd.append("--production")

        return self._execute_command(
            cmd,
            timeout=300,
            error_type=BuildExecutionError,
            error_message="Dependency installation failed"
        )

    def clean(self) -> BuildResult:
        """
        Clean build artifacts and node_modules.

        Returns:
            BuildResult
        """
        import shutil

        # Remove node_modules
        node_modules = self.project_dir / "node_modules"
        if node_modules.exists():
            self.logger.info("Removing node_modules...")
            shutil.rmtree(node_modules)

        # Remove common build directories
        for build_dir in ["dist", "build", "out", ".next", ".nuxt"]:
            path = self.project_dir / build_dir
            if path.exists() and path.is_dir():
                self.logger.info(f"Removing {build_dir}...")
                shutil.rmtree(path)

        return BuildResult(
            success=True,
            exit_code=0,
            duration=0.0,
            output="Clean completed",
            build_system="npm"
        )

    def _extract_test_stats(self, output: str) -> Dict[str, int]:
        """
        Extract test statistics from Jest/Mocha output.

        Args:
            output: Test output

        Returns:
            Dict with test statistics
        """
        stats = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'tests_skipped': 0
        }

        # Jest output patterns
        # "Tests:       5 passed, 5 total"
        jest_pattern = r"Tests:\s+(?:(\d+)\s+failed,\s+)?(?:(\d+)\s+passed,\s+)?(?:(\d+)\s+skipped,\s+)?(\d+)\s+total"
        jest_match = re.search(jest_pattern, output)

        if jest_match:
            failed = int(jest_match.group(1) or 0)
            passed = int(jest_match.group(2) or 0)
            skipped = int(jest_match.group(3) or 0)
            total = int(jest_match.group(4) or 0)

            stats['tests_run'] = total
            stats['tests_passed'] = passed
            stats['tests_failed'] = failed
            stats['tests_skipped'] = skipped

        # Mocha output patterns
        # "5 passing"
        # "2 failing"
        mocha_passing = re.search(r"(\d+)\s+passing", output)
        mocha_failing = re.search(r"(\d+)\s+failing", output)

        if mocha_passing or mocha_failing:
            passed = int(mocha_passing.group(1)) if mocha_passing else 0
            failed = int(mocha_failing.group(1)) if mocha_failing else 0

            stats['tests_passed'] = passed
            stats['tests_failed'] = failed
            stats['tests_run'] = passed + failed

        return stats


# CLI interface
if __name__ == "__main__":
    import argparse
    import logging
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description="npm/yarn/pnpm Manager")
    parser.add_argument("--project-dir", default=".", help="Project directory")
    parser.add_argument("command", choices=["info", "build", "test", "install", "clean"],
                       help="Command to execute")
    parser.add_argument("--script", default="build", help="Script name for build command")
    parser.add_argument("--production", action="store_true", help="Production mode")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage")
    parser.add_argument("--package", help="Package to install")
    parser.add_argument("--version", help="Package version")
    parser.add_argument("--dev", action="store_true", help="Install as dev dependency")

    args = parser.parse_args()

    try:
        npm = NpmManager(project_dir=args.project_dir)

        if args.command == "info":
            info = npm.get_project_info()
            print(json.dumps(info, indent=2))

        elif args.command == "build":
            result = npm.build(script_name=args.script, production=args.production)
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "test":
            result = npm.test(coverage=args.coverage)
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "install":
            if args.package:
                npm.install_dependency(args.package, version=args.version, dev=args.dev)
                print(f"Installed {args.package}")
            else:
                result = npm.install_dependencies(production=args.production)
                print(result)

        elif args.command == "clean":
            result = npm.clean()
            print(result)

    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)
