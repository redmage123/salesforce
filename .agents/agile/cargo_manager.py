#!/usr/bin/env python3
"""
Cargo Build Manager (Rust)

Enterprise-grade Rust build system management using Cargo.

Design Patterns:
- Template Method: Inherits from BuildManagerBase
- Exception Wrapper: All errors properly wrapped
- Strategy Pattern: Different build modes (debug, release)
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


class BuildProfile(Enum):
    """Cargo build profiles"""
    DEBUG = "debug"
    RELEASE = "release"


class CargoFeature(Enum):
    """Common Cargo features"""
    DEFAULT = "default"
    FULL = "full"
    MINIMAL = "minimal"


@dataclass
class CargoProjectInfo:
    """Cargo.toml project information"""
    name: str
    version: str
    edition: str  # 2015, 2018, 2021
    authors: List[str] = field(default_factory=list)
    description: Optional[str] = None
    license: Optional[str] = None
    repository: Optional[str] = None
    dependencies: Dict[str, Any] = field(default_factory=dict)
    dev_dependencies: Dict[str, Any] = field(default_factory=dict)
    features: Dict[str, List[str]] = field(default_factory=dict)
    workspace_members: List[str] = field(default_factory=list)
    is_workspace: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "version": self.version,
            "edition": self.edition,
            "authors": self.authors,
            "description": self.description,
            "license": self.license,
            "repository": self.repository,
            "dependencies": self.dependencies,
            "devDependencies": self.dev_dependencies,
            "features": self.features,
            "workspaceMembers": self.workspace_members,
            "isWorkspace": self.is_workspace
        }


@register_build_manager(BuildSystem.CARGO)
class CargoManager(BuildManagerBase):
    """
    Enterprise-grade Cargo manager for Rust projects.

    Example:
        cargo = CargoManager(project_dir="/path/to/project")
        result = cargo.build(release=True)
        test_result = cargo.test()
    """

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        logger: Optional['logging.Logger'] = None
    ):
        """
        Initialize Cargo manager.

        Args:
            project_dir: Project directory (contains Cargo.toml)
            logger: Logger instance

        Raises:
            BuildSystemNotFoundError: If Cargo not found
            ProjectConfigurationError: If Cargo.toml invalid
        """
        self.cargo_toml_path = None
        self.cargo_lock_path = None

        super().__init__(project_dir, logger)

        self.cargo_lock_path = self.project_dir / "Cargo.lock"

    @wrap_exception(BuildSystemNotFoundError, "Cargo not found")
    def _validate_installation(self) -> None:
        """
        Validate Cargo is installed.

        Raises:
            BuildSystemNotFoundError: If Cargo not in PATH
        """
        result = self._execute_command(
            ["cargo", "--version"],
            timeout=10,
            error_type=BuildSystemNotFoundError,
            error_message="Cargo not installed or not in PATH"
        )

        # Extract version
        version_match = re.search(r"cargo ([\d.]+)", result.output)
        if version_match:
            version = version_match.group(1)
            self.logger.info(f"Using Cargo version: {version}")

    @wrap_exception(ProjectConfigurationError, "Invalid Cargo project")
    def _validate_project(self) -> None:
        """
        Validate Cargo.toml exists.

        Raises:
            ProjectConfigurationError: If Cargo.toml missing
        """
        self.cargo_toml_path = self.project_dir / "Cargo.toml"

        if not self.cargo_toml_path.exists():
            raise ProjectConfigurationError(
                "Cargo.toml not found",
                {"project_dir": str(self.project_dir)}
            )

    @wrap_exception(ProjectConfigurationError, "Failed to parse Cargo.toml")
    def get_project_info(self) -> Dict[str, Any]:
        """
        Parse Cargo.toml for project information.

        Returns:
            Dict with project information

        Raises:
            ProjectConfigurationError: If Cargo.toml malformed
        """
        with open(self.cargo_toml_path, 'r') as f:
            data = toml.load(f)

        # Check if workspace
        is_workspace = "workspace" in data
        workspace_members = data.get("workspace", {}).get("members", [])

        # Package info (might be in workspace root or package)
        package = data.get("package", {})

        info = CargoProjectInfo(
            name=package.get("name", ""),
            version=package.get("version", "0.1.0"),
            edition=package.get("edition", "2021"),
            authors=package.get("authors", []),
            description=package.get("description"),
            license=package.get("license"),
            repository=package.get("repository"),
            dependencies=data.get("dependencies", {}),
            dev_dependencies=data.get("dev-dependencies", {}),
            features=data.get("features", {}),
            workspace_members=workspace_members,
            is_workspace=is_workspace
        )

        return info.to_dict()

    @wrap_exception(BuildExecutionError, "Cargo build failed")
    def build(
        self,
        release: bool = False,
        features: Optional[List[str]] = None,
        all_features: bool = False,
        no_default_features: bool = False,
        target: Optional[str] = None,
        **kwargs
    ) -> BuildResult:
        """
        Build Rust project with Cargo.

        Args:
            release: Build in release mode (optimized)
            features: List of features to enable
            all_features: Enable all features
            no_default_features: Disable default features
            target: Target triple (e.g., "x86_64-unknown-linux-gnu")

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If build fails

        Example:
            result = cargo.build(release=True, features=["full"])
        """
        cmd = ["cargo", "build"]

        # Release mode
        if release:
            cmd.append("--release")

        # Features
        if all_features:
            cmd.append("--all-features")
        elif no_default_features:
            cmd.append("--no-default-features")
        if features:
            cmd.extend(["--features", ",".join(features)])

        # Target
        if target:
            cmd.extend(["--target", target])

        return self._execute_command(
            cmd,
            timeout=600,
            error_type=BuildExecutionError,
            error_message="Cargo build failed"
        )

    @wrap_exception(TestExecutionError, "Cargo tests failed")
    def test(
        self,
        release: bool = False,
        test_name: Optional[str] = None,
        no_fail_fast: bool = False,
        **kwargs
    ) -> BuildResult:
        """
        Run Cargo tests.

        Args:
            release: Test release build
            test_name: Specific test to run
            no_fail_fast: Run all tests regardless of failures

        Returns:
            BuildResult with test statistics

        Raises:
            TestExecutionError: If tests fail

        Example:
            result = cargo.test(test_name="integration_tests")
        """
        cmd = ["cargo", "test"]

        if release:
            cmd.append("--release")

        if no_fail_fast:
            cmd.append("--no-fail-fast")

        if test_name:
            cmd.append(test_name)

        return self._execute_command(
            cmd,
            timeout=300,
            error_type=TestExecutionError,
            error_message="Cargo test execution failed"
        )

    @wrap_exception(DependencyInstallError, "Failed to add dependency")
    def install_dependency(
        self,
        crate: str,
        version: Optional[str] = None,
        dev: bool = False,
        **kwargs
    ) -> bool:
        """
        Add a dependency to Cargo.toml.

        Args:
            crate: Crate name
            version: Crate version (optional)
            dev: Add as dev dependency

        Returns:
            True if successful

        Raises:
            DependencyInstallError: If installation fails

        Example:
            cargo.install_dependency("serde", version="1.0")
            cargo.install_dependency("tokio", dev=True)
        """
        cmd = ["cargo", "add", crate]

        if version:
            cmd.extend(["--vers", version])

        if dev:
            cmd.append("--dev")

        result = self._execute_command(
            cmd,
            timeout=60,
            error_type=DependencyInstallError,
            error_message=f"Failed to add crate {crate}"
        )

        self.logger.info(f"Added crate {crate}")
        return True

    @wrap_exception(BuildExecutionError, "Failed to check project")
    def check(self, all_features: bool = False) -> BuildResult:
        """
        Check project for errors without building.

        Args:
            all_features: Check with all features enabled

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If check fails

        Example:
            result = cargo.check(all_features=True)
        """
        cmd = ["cargo", "check"]

        if all_features:
            cmd.append("--all-features")

        return self._execute_command(
            cmd,
            timeout=120,
            error_type=BuildExecutionError,
            error_message="Cargo check failed"
        )

    @wrap_exception(BuildExecutionError, "Failed to run clippy")
    def clippy(self, fix: bool = False) -> BuildResult:
        """
        Run Clippy linter.

        Args:
            fix: Automatically fix warnings

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If clippy fails

        Example:
            result = cargo.clippy(fix=True)
        """
        cmd = ["cargo", "clippy"]

        if fix:
            cmd.append("--fix")

        return self._execute_command(
            cmd,
            timeout=120,
            error_type=BuildExecutionError,
            error_message="Cargo clippy failed"
        )

    @wrap_exception(BuildExecutionError, "Failed to format code")
    def fmt(self, check: bool = False) -> BuildResult:
        """
        Format code with rustfmt.

        Args:
            check: Check formatting without applying

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If formatting fails

        Example:
            result = cargo.fmt(check=True)
        """
        cmd = ["cargo", "fmt"]

        if check:
            cmd.append("--check")

        return self._execute_command(
            cmd,
            timeout=60,
            error_type=BuildExecutionError,
            error_message="Cargo fmt failed"
        )

    def clean(self) -> BuildResult:
        """
        Clean build artifacts.

        Returns:
            BuildResult
        """
        cmd = ["cargo", "clean"]

        try:
            return self._execute_command(
                cmd,
                timeout=30,
                error_type=BuildExecutionError,
                error_message="Cargo clean failed"
            )
        except BuildExecutionError as e:
            self.logger.warning(f"Clean failed: {e}")
            return BuildResult(
                success=False,
                exit_code=1,
                duration=0.0,
                output=str(e),
                build_system="cargo"
            )

    def _extract_test_stats(self, output: str) -> Dict[str, int]:
        """
        Extract test statistics from Cargo test output.

        Args:
            output: Cargo test output

        Returns:
            Dict with test statistics
        """
        stats = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'tests_skipped': 0
        }

        # Cargo test summary: "test result: ok. 15 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out"
        summary_match = re.search(
            r"test result: (\w+)\.\s+(\d+) passed;\s+(\d+) failed;\s+(\d+) ignored",
            output
        )

        if summary_match:
            passed = int(summary_match.group(2))
            failed = int(summary_match.group(3))
            ignored = int(summary_match.group(4))

            stats['tests_passed'] = passed
            stats['tests_failed'] = failed
            stats['tests_skipped'] = ignored
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

    parser = argparse.ArgumentParser(description="Cargo Manager")
    parser.add_argument("--project-dir", default=".", help="Project directory")
    parser.add_argument("command", choices=["info", "build", "test", "check", "clippy", "fmt", "clean", "add"],
                       help="Command to execute")
    parser.add_argument("--release", action="store_true", help="Release build")
    parser.add_argument("--features", help="Features to enable (comma-separated)")
    parser.add_argument("--crate", help="Crate to add")
    parser.add_argument("--version", help="Crate version")
    parser.add_argument("--dev", action="store_true", help="Add as dev dependency")

    args = parser.parse_args()

    try:
        cargo = CargoManager(project_dir=args.project_dir)

        if args.command == "info":
            info = cargo.get_project_info()
            print(json.dumps(info, indent=2))

        elif args.command == "build":
            features = args.features.split(",") if args.features else None
            result = cargo.build(release=args.release, features=features)
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "test":
            result = cargo.test(release=args.release)
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "check":
            result = cargo.check()
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "clippy":
            result = cargo.clippy()
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "fmt":
            result = cargo.fmt()
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "clean":
            result = cargo.clean()
            print(result)

        elif args.command == "add":
            if not args.crate:
                print("Error: --crate required for add command")
                sys.exit(1)
            cargo.install_dependency(args.crate, version=args.version, dev=args.dev)
            print(f"Added {args.crate}")

    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)
