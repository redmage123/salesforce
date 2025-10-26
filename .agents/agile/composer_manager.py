#!/usr/bin/env python3
"""
Composer Build Manager (PHP)

Enterprise-grade PHP dependency management using Composer.

Design Patterns:
- Template Method: Inherits from BuildManagerBase
- Exception Wrapper: All errors properly wrapped
- Strategy Pattern: Different installation and update modes
"""

from pathlib import Path
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from enum import Enum
import re
import json as json_lib

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


class DependencyType(Enum):
    """Composer dependency types"""
    REQUIRE = "require"
    REQUIRE_DEV = "require-dev"


class StabilityFlag(Enum):
    """Package stability flags"""
    STABLE = "stable"
    RC = "RC"
    BETA = "beta"
    ALPHA = "alpha"
    DEV = "dev"


@dataclass
class ComposerProjectInfo:
    """composer.json project information"""
    name: str
    description: Optional[str] = None
    type: str = "library"
    license: Optional[str] = None
    php_version: str = ">=7.0"
    require: Dict[str, str] = field(default_factory=dict)
    require_dev: Dict[str, str] = field(default_factory=dict)
    autoload: Dict[str, Any] = field(default_factory=dict)
    scripts: Dict[str, Any] = field(default_factory=dict)
    has_lock_file: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "license": self.license,
            "phpVersion": self.php_version,
            "require": self.require,
            "requireDev": self.require_dev,
            "autoload": self.autoload,
            "scripts": self.scripts,
            "hasLockFile": self.has_lock_file
        }


@register_build_manager(BuildSystem.COMPOSER)
class ComposerManager(BuildManagerBase):
    """
    Enterprise-grade Composer manager for PHP projects.

    Example:
        composer = ComposerManager(project_dir="/path/to/project")
        result = composer.install()
        test_result = composer.test()
    """

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        logger: Optional['logging.Logger'] = None
    ):
        """
        Initialize Composer manager.

        Args:
            project_dir: Project directory (contains composer.json)
            logger: Logger instance

        Raises:
            BuildSystemNotFoundError: If Composer not found
            ProjectConfigurationError: If composer.json invalid
        """
        self.composer_json_path = None
        self.composer_lock_path = None

        super().__init__(project_dir, logger)

        self.composer_lock_path = self.project_dir / "composer.lock"

    @wrap_exception(BuildSystemNotFoundError, "Composer not found")
    def _validate_installation(self) -> None:
        """
        Validate Composer is installed.

        Raises:
            BuildSystemNotFoundError: If Composer not in PATH
        """
        result = self._execute_command(
            ["composer", "--version"],
            timeout=10,
            error_type=BuildSystemNotFoundError,
            error_message="Composer not installed or not in PATH"
        )

        # Extract version
        version_match = re.search(r"Composer version ([\d.]+)", result.output)
        if version_match:
            version = version_match.group(1)
            self.logger.info(f"Using Composer version: {version}")

    @wrap_exception(ProjectConfigurationError, "Invalid Composer project")
    def _validate_project(self) -> None:
        """
        Validate composer.json exists.

        Raises:
            ProjectConfigurationError: If composer.json missing
        """
        self.composer_json_path = self.project_dir / "composer.json"

        if not self.composer_json_path.exists():
            raise ProjectConfigurationError(
                "composer.json not found",
                {"project_dir": str(self.project_dir)}
            )

    @wrap_exception(ProjectConfigurationError, "Failed to parse composer.json")
    def get_project_info(self) -> Dict[str, Any]:
        """
        Parse composer.json for project information.

        Returns:
            Dict with project information

        Raises:
            ProjectConfigurationError: If composer.json malformed
        """
        with open(self.composer_json_path, 'r') as f:
            data = json_lib.load(f)

        # Extract PHP version from require
        php_version = data.get("require", {}).get("php", ">=7.0")

        info = ComposerProjectInfo(
            name=data.get("name", ""),
            description=data.get("description"),
            type=data.get("type", "library"),
            license=data.get("license"),
            php_version=php_version,
            require=data.get("require", {}),
            require_dev=data.get("require-dev", {}),
            autoload=data.get("autoload", {}),
            scripts=data.get("scripts", {}),
            has_lock_file=self.composer_lock_path.exists()
        )

        return info.to_dict()

    @wrap_exception(BuildExecutionError, "Composer install failed")
    def build(self, **kwargs) -> BuildResult:
        """
        Install dependencies (alias for install).

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If install fails

        Example:
            result = composer.build()
        """
        return self.install()

    @wrap_exception(DependencyInstallError, "Failed to install dependencies")
    def install(
        self,
        no_dev: bool = False,
        optimize_autoloader: bool = False,
        prefer_dist: bool = False,
        **kwargs
    ) -> BuildResult:
        """
        Install all dependencies from composer.json.

        Args:
            no_dev: Skip dev dependencies
            optimize_autoloader: Optimize autoloader
            prefer_dist: Prefer dist over source

        Returns:
            BuildResult

        Raises:
            DependencyInstallError: If installation fails

        Example:
            composer.install(no_dev=True, optimize_autoloader=True)
        """
        cmd = ["composer", "install"]

        if no_dev:
            cmd.append("--no-dev")

        if optimize_autoloader:
            cmd.append("--optimize-autoloader")

        if prefer_dist:
            cmd.append("--prefer-dist")

        return self._execute_command(
            cmd,
            timeout=300,
            error_type=DependencyInstallError,
            error_message="Dependency installation failed"
        )

    @wrap_exception(TestExecutionError, "Tests failed")
    def test(
        self,
        test_path: Optional[str] = None,
        verbose: bool = False,
        **kwargs
    ) -> BuildResult:
        """
        Run tests with PHPUnit via composer.

        Args:
            test_path: Specific test file or directory
            verbose: Verbose output

        Returns:
            BuildResult with test statistics

        Raises:
            TestExecutionError: If tests fail

        Example:
            result = composer.test(verbose=True)
        """
        # Check if there's a test script defined
        info = self.get_project_info()
        if "test" in info.get("scripts", {}):
            cmd = ["composer", "test"]
        else:
            # Fall back to direct PHPUnit call
            cmd = ["./vendor/bin/phpunit"]

        if verbose:
            cmd.append("--verbose")

        if test_path:
            cmd.append(test_path)

        return self._execute_command(
            cmd,
            timeout=300,
            error_type=TestExecutionError,
            error_message="Test execution failed"
        )

    @wrap_exception(DependencyInstallError, "Failed to add package")
    def install_dependency(
        self,
        package: str,
        version: Optional[str] = None,
        dev: bool = False,
        **kwargs
    ) -> bool:
        """
        Add a package to composer.json.

        Args:
            package: Package name
            version: Package version (optional)
            dev: Add as dev dependency

        Returns:
            True if successful

        Raises:
            DependencyInstallError: If installation fails

        Example:
            composer.install_dependency("symfony/console", version="^6.0")
            composer.install_dependency("phpunit/phpunit", dev=True)
        """
        package_spec = f"{package}:{version}" if version else package

        cmd = ["composer", "require", package_spec]

        if dev:
            cmd.append("--dev")

        result = self._execute_command(
            cmd,
            timeout=120,
            error_type=DependencyInstallError,
            error_message=f"Failed to add package {package}"
        )

        self.logger.info(f"Added package {package}")
        return True

    @wrap_exception(BuildExecutionError, "Failed to update dependencies")
    def update(
        self,
        package: Optional[str] = None,
        with_dependencies: bool = True,
        **kwargs
    ) -> BuildResult:
        """
        Update dependencies.

        Args:
            package: Specific package to update (None = all)
            with_dependencies: Also update dependencies of specified package

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If update fails

        Example:
            composer.update()  # Update all
            composer.update(package="symfony/console")  # Update specific
        """
        cmd = ["composer", "update"]

        if package:
            cmd.append(package)

        if not with_dependencies and package:
            cmd.append("--no-update-with-dependencies")

        return self._execute_command(
            cmd,
            timeout=300,
            error_type=BuildExecutionError,
            error_message="Dependency update failed"
        )

    @wrap_exception(BuildExecutionError, "Failed to run script")
    def run_script(self, script_name: str) -> BuildResult:
        """
        Run a script defined in composer.json.

        Args:
            script_name: Script name from scripts section

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If script fails

        Example:
            composer.run_script("post-install-cmd")
        """
        cmd = ["composer", "run-script", script_name]

        return self._execute_command(
            cmd,
            timeout=600,
            error_type=BuildExecutionError,
            error_message=f"Script '{script_name}' failed"
        )

    @wrap_exception(BuildExecutionError, "Failed to show package info")
    def show(
        self,
        package: Optional[str] = None,
        installed: bool = False
    ) -> BuildResult:
        """
        Show information about packages.

        Args:
            package: Package name (None = all)
            installed: Show only installed packages

        Returns:
            BuildResult with package information

        Raises:
            BuildExecutionError: If command fails

        Example:
            result = composer.show("symfony/console")
        """
        cmd = ["composer", "show"]

        if installed:
            cmd.append("--installed")

        if package:
            cmd.append(package)

        return self._execute_command(
            cmd,
            timeout=30,
            error_type=BuildExecutionError,
            error_message=f"Failed to show package info"
        )

    @wrap_exception(BuildExecutionError, "Failed to validate")
    def validate(self) -> BuildResult:
        """
        Validate composer.json and composer.lock.

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If validation fails

        Example:
            composer.validate()
        """
        cmd = ["composer", "validate"]

        return self._execute_command(
            cmd,
            timeout=30,
            error_type=BuildExecutionError,
            error_message="Validation failed"
        )

    @wrap_exception(BuildExecutionError, "Failed to dump autoload")
    def dump_autoload(self, optimize: bool = False) -> BuildResult:
        """
        Regenerate autoloader.

        Args:
            optimize: Optimize autoloader

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If dump-autoload fails

        Example:
            composer.dump_autoload(optimize=True)
        """
        cmd = ["composer", "dump-autoload"]

        if optimize:
            cmd.append("--optimize")

        return self._execute_command(
            cmd,
            timeout=60,
            error_type=BuildExecutionError,
            error_message="dump-autoload failed"
        )

    @wrap_exception(BuildExecutionError, "Failed to diagnose")
    def diagnose(self) -> BuildResult:
        """
        Run diagnostics.

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If diagnose fails
        """
        cmd = ["composer", "diagnose"]

        return self._execute_command(
            cmd,
            timeout=60,
            error_type=BuildExecutionError,
            error_message="Diagnose failed"
        )

    def clean(self) -> BuildResult:
        """
        Clear Composer cache.

        Returns:
            BuildResult
        """
        cmd = ["composer", "clear-cache"]

        try:
            return self._execute_command(
                cmd,
                timeout=30,
                error_type=BuildExecutionError,
                error_message="Clear cache failed"
            )
        except BuildExecutionError as e:
            self.logger.warning(f"Clean failed: {e}")
            return BuildResult(
                success=False,
                exit_code=1,
                duration=0.0,
                output=str(e),
                build_system="composer"
            )

    def _extract_test_stats(self, output: str) -> Dict[str, int]:
        """
        Extract test statistics from PHPUnit output.

        Args:
            output: PHPUnit output

        Returns:
            Dict with test statistics
        """
        stats = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'tests_skipped': 0
        }

        # PHPUnit: "Tests: 15, Assertions: 42, Failures: 2, Skipped: 1"
        # Or: "OK (15 tests, 42 assertions)"
        summary_match = re.search(
            r'Tests:\s+(\d+),\s+Assertions:\s+\d+(?:,\s+Failures:\s+(\d+))?(?:,\s+(?:Skipped|Incomplete):\s+(\d+))?',
            output
        )

        if summary_match:
            total = int(summary_match.group(1))
            failures = int(summary_match.group(2) or 0)
            skipped = int(summary_match.group(3) or 0)

            stats['tests_run'] = total - skipped
            stats['tests_failed'] = failures
            stats['tests_passed'] = total - failures - skipped
            stats['tests_skipped'] = skipped
            return stats

        # Alternative format: "OK (15 tests, 42 assertions)"
        ok_match = re.search(r'OK\s+\((\d+)\s+tests?,', output)
        if ok_match:
            total = int(ok_match.group(1))
            stats['tests_run'] = total
            stats['tests_passed'] = total

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

    parser = argparse.ArgumentParser(description="Composer Manager")
    parser.add_argument("--project-dir", default=".", help="Project directory")
    parser.add_argument("command", choices=["info", "install", "test", "update", "require", "show", "validate", "dump-autoload", "diagnose", "clean"],
                       help="Command to execute")
    parser.add_argument("--package", help="Package name")
    parser.add_argument("--version", help="Package version")
    parser.add_argument("--dev", action="store_true", help="Dev dependency")
    parser.add_argument("--no-dev", action="store_true", help="Skip dev dependencies")
    parser.add_argument("--optimize", action="store_true", help="Optimize autoloader")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    try:
        composer = ComposerManager(project_dir=args.project_dir)

        if args.command == "info":
            info = composer.get_project_info()
            print(json.dumps(info, indent=2))

        elif args.command == "install":
            result = composer.install(
                no_dev=args.no_dev,
                optimize_autoloader=args.optimize
            )
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "test":
            result = composer.test(verbose=args.verbose)
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "update":
            result = composer.update(package=args.package)
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "require":
            if not args.package:
                print("Error: --package required for require command")
                sys.exit(1)
            composer.install_dependency(args.package, version=args.version, dev=args.dev)
            print(f"Added {args.package}")

        elif args.command == "show":
            result = composer.show(package=args.package)
            print(result.output)

        elif args.command == "validate":
            result = composer.validate()
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "dump-autoload":
            result = composer.dump_autoload(optimize=args.optimize)
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "diagnose":
            result = composer.diagnose()
            print(result)

        elif args.command == "clean":
            result = composer.clean()
            print(result)

    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)
