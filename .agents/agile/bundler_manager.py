#!/usr/bin/env python3
"""
Bundler Build Manager (Ruby)

Enterprise-grade Ruby dependency management using Bundler.

Design Patterns:
- Template Method: Inherits from BuildManagerBase
- Exception Wrapper: All errors properly wrapped
- Strategy Pattern: Different deployment and installation modes
"""

from pathlib import Path
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from enum import Enum
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


class DependencyGroup(Enum):
    """Bundler dependency groups"""
    DEFAULT = "default"
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


@dataclass
class BundlerProjectInfo:
    """Gemfile project information"""
    ruby_version: Optional[str] = None
    source: str = "https://rubygems.org"
    gems: Dict[str, str] = field(default_factory=dict)
    groups: Dict[str, List[str]] = field(default_factory=dict)
    has_lock_file: bool = False
    gemspec_file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "rubyVersion": self.ruby_version,
            "source": self.source,
            "gems": self.gems,
            "groups": self.groups,
            "hasLockFile": self.has_lock_file,
            "gemspecFile": self.gemspec_file
        }


@register_build_manager(BuildSystem.BUNDLER)
class BundlerManager(BuildManagerBase):
    """
    Enterprise-grade Bundler manager for Ruby projects.

    Example:
        bundler = BundlerManager(project_dir="/path/to/project")
        result = bundler.install()
        test_result = bundler.test()
    """

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        logger: Optional['logging.Logger'] = None
    ):
        """
        Initialize Bundler manager.

        Args:
            project_dir: Project directory (contains Gemfile)
            logger: Logger instance

        Raises:
            BuildSystemNotFoundError: If Bundler not found
            ProjectConfigurationError: If Gemfile invalid
        """
        self.gemfile_path = None
        self.gemfile_lock_path = None
        self.gemspec_path = None

        super().__init__(project_dir, logger)

        self.gemfile_lock_path = self.project_dir / "Gemfile.lock"

        # Check for gemspec
        gemspec_files = list(self.project_dir.glob("*.gemspec"))
        if gemspec_files:
            self.gemspec_path = gemspec_files[0]

    @wrap_exception(BuildSystemNotFoundError, "Bundler not found")
    def _validate_installation(self) -> None:
        """
        Validate Bundler is installed.

        Raises:
            BuildSystemNotFoundError: If Bundler not in PATH
        """
        result = self._execute_command(
            ["bundle", "--version"],
            timeout=10,
            error_type=BuildSystemNotFoundError,
            error_message="Bundler not installed or not in PATH"
        )

        # Extract version
        version_match = re.search(r"Bundler version ([\d.]+)", result.output)
        if version_match:
            version = version_match.group(1)
            self.logger.info(f"Using Bundler version: {version}")

    @wrap_exception(ProjectConfigurationError, "Invalid Bundler project")
    def _validate_project(self) -> None:
        """
        Validate Gemfile exists.

        Raises:
            ProjectConfigurationError: If Gemfile missing
        """
        self.gemfile_path = self.project_dir / "Gemfile"

        if not self.gemfile_path.exists():
            raise ProjectConfigurationError(
                "Gemfile not found",
                {"project_dir": str(self.project_dir)}
            )

    @wrap_exception(ProjectConfigurationError, "Failed to parse Gemfile")
    def get_project_info(self) -> Dict[str, Any]:
        """
        Parse Gemfile for project information.

        Returns:
            Dict with project information

        Raises:
            ProjectConfigurationError: If Gemfile malformed
        """
        with open(self.gemfile_path, 'r') as f:
            content = f.read()

        # Parse source
        source = "https://rubygems.org"
        source_match = re.search(r"source\s+['\"]([^'\"]+)['\"]", content)
        if source_match:
            source = source_match.group(1)

        # Parse Ruby version
        ruby_version = None
        ruby_match = re.search(r"ruby\s+['\"]([^'\"]+)['\"]", content)
        if ruby_match:
            ruby_version = ruby_match.group(1)

        # Parse gems (simplified - full parsing requires evaluating Ruby code)
        gems = {}
        for gem_match in re.finditer(r"gem\s+['\"]([^'\"]+)['\"](?:,\s*['\"]([^'\"]+)['\"])?", content):
            gem_name = gem_match.group(1)
            gem_version = gem_match.group(2) or "latest"
            gems[gem_name] = gem_version

        # Parse groups
        groups = {}
        group_pattern = r"group\s+:(\w+).*?do(.*?)end"
        for group_match in re.finditer(group_pattern, content, re.DOTALL):
            group_name = group_match.group(1)
            group_content = group_match.group(2)
            group_gems = []
            for gem_match in re.finditer(r"gem\s+['\"]([^'\"]+)['\"]", group_content):
                group_gems.append(gem_match.group(1))
            groups[group_name] = group_gems

        info = BundlerProjectInfo(
            ruby_version=ruby_version,
            source=source,
            gems=gems,
            groups=groups,
            has_lock_file=self.gemfile_lock_path.exists(),
            gemspec_file=self.gemspec_path.name if self.gemspec_path else None
        )

        return info.to_dict()

    @wrap_exception(BuildExecutionError, "Bundler install failed")
    def build(self, **kwargs) -> BuildResult:
        """
        Install dependencies (alias for install).

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If install fails

        Example:
            result = bundler.build()
        """
        return self.install()

    @wrap_exception(DependencyInstallError, "Failed to install dependencies")
    def install(
        self,
        deployment: bool = False,
        without: Optional[List[str]] = None,
        path: Optional[str] = None,
        jobs: Optional[int] = None,
        **kwargs
    ) -> BuildResult:
        """
        Install all dependencies from Gemfile.

        Args:
            deployment: Install for deployment (frozen lockfile)
            without: Groups to exclude
            path: Install path
            jobs: Number of parallel jobs

        Returns:
            BuildResult

        Raises:
            DependencyInstallError: If installation fails

        Example:
            bundler.install(deployment=True, without=["development", "test"])
        """
        cmd = ["bundle", "install"]

        if deployment:
            cmd.append("--deployment")

        if without:
            cmd.extend(["--without", " ".join(without)])

        if path:
            cmd.extend(["--path", path])

        if jobs:
            cmd.extend(["--jobs", str(jobs)])

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
        Run tests with RSpec/Minitest via bundle exec.

        Args:
            test_path: Specific test file or directory
            verbose: Verbose output

        Returns:
            BuildResult with test statistics

        Raises:
            TestExecutionError: If tests fail

        Example:
            result = bundler.test(verbose=True)
        """
        # Try RSpec first, fall back to Minitest
        cmd = ["bundle", "exec", "rspec"]

        if verbose:
            cmd.append("--format", "documentation")

        if test_path:
            cmd.append(test_path)

        try:
            return self._execute_command(
                cmd,
                timeout=300,
                error_type=TestExecutionError,
                error_message="Test execution failed"
            )
        except TestExecutionError:
            # Try Minitest as fallback
            cmd = ["bundle", "exec", "rake", "test"]
            return self._execute_command(
                cmd,
                timeout=300,
                error_type=TestExecutionError,
                error_message="Test execution failed"
            )

    @wrap_exception(DependencyInstallError, "Failed to add gem")
    def install_dependency(
        self,
        gem: str,
        version: Optional[str] = None,
        group: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Add a gem to Gemfile.

        Args:
            gem: Gem name
            version: Gem version (optional)
            group: Dependency group (development, test, etc.)

        Returns:
            True if successful

        Raises:
            DependencyInstallError: If installation fails

        Example:
            bundler.install_dependency("rspec", version="3.12", group="test")
        """
        # Bundler doesn't have a direct 'add' command, so we need to:
        # 1. Manually edit Gemfile, or
        # 2. Use bundle add (Bundler 2.0+)

        cmd = ["bundle", "add", gem]

        if version:
            cmd.extend(["--version", version])

        if group:
            cmd.extend(["--group", group])

        result = self._execute_command(
            cmd,
            timeout=120,
            error_type=DependencyInstallError,
            error_message=f"Failed to add gem {gem}"
        )

        self.logger.info(f"Added gem {gem}")
        return True

    @wrap_exception(BuildExecutionError, "Failed to update dependencies")
    def update(
        self,
        gem: Optional[str] = None,
        conservative: bool = False,
        **kwargs
    ) -> BuildResult:
        """
        Update dependencies.

        Args:
            gem: Specific gem to update (None = all)
            conservative: Only update to meet requirements

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If update fails

        Example:
            bundler.update()  # Update all
            bundler.update(gem="rails")  # Update specific
        """
        cmd = ["bundle", "update"]

        if gem:
            cmd.append(gem)

        if conservative:
            cmd.append("--conservative")

        return self._execute_command(
            cmd,
            timeout=300,
            error_type=BuildExecutionError,
            error_message="Dependency update failed"
        )

    @wrap_exception(BuildExecutionError, "Failed to run bundle exec")
    def exec(self, command: List[str]) -> BuildResult:
        """
        Execute a command in the context of the bundle.

        Args:
            command: Command to execute

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If command fails

        Example:
            bundler.exec(["rake", "db:migrate"])
        """
        cmd = ["bundle", "exec"] + command

        return self._execute_command(
            cmd,
            timeout=600,
            error_type=BuildExecutionError,
            error_message=f"Command '{' '.join(command)}' failed"
        )

    @wrap_exception(BuildExecutionError, "Failed to show gem info")
    def show(self, gem: str) -> BuildResult:
        """
        Show information about a gem.

        Args:
            gem: Gem name

        Returns:
            BuildResult with gem information

        Raises:
            BuildExecutionError: If command fails

        Example:
            result = bundler.show("rails")
        """
        cmd = ["bundle", "show", gem]

        return self._execute_command(
            cmd,
            timeout=30,
            error_type=BuildExecutionError,
            error_message=f"Failed to show info for {gem}"
        )

    @wrap_exception(BuildExecutionError, "Failed to check Gemfile")
    def check(self) -> BuildResult:
        """
        Verify dependencies are satisfied.

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If check fails

        Example:
            bundler.check()
        """
        cmd = ["bundle", "check"]

        return self._execute_command(
            cmd,
            timeout=60,
            error_type=BuildExecutionError,
            error_message="Bundle check failed"
        )

    @wrap_exception(BuildExecutionError, "Failed to clean")
    def clean(self, force: bool = False) -> BuildResult:
        """
        Remove unused gems.

        Args:
            force: Force clean without confirmation

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If clean fails
        """
        cmd = ["bundle", "clean"]

        if force:
            cmd.append("--force")

        try:
            return self._execute_command(
                cmd,
                timeout=60,
                error_type=BuildExecutionError,
                error_message="Bundle clean failed"
            )
        except BuildExecutionError as e:
            self.logger.warning(f"Clean failed: {e}")
            return BuildResult(
                success=False,
                exit_code=1,
                duration=0.0,
                output=str(e),
                build_system="bundler"
            )

    def _extract_test_stats(self, output: str) -> Dict[str, int]:
        """
        Extract test statistics from RSpec/Minitest output.

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

        # RSpec: "15 examples, 2 failures, 1 pending"
        rspec_match = re.search(
            r"(\d+)\s+examples?,\s+(\d+)\s+failures?(?:,\s+(\d+)\s+pending)?",
            output
        )

        if rspec_match:
            total = int(rspec_match.group(1))
            failed = int(rspec_match.group(2))
            pending = int(rspec_match.group(3) or 0)
            passed = total - failed - pending

            stats['tests_run'] = total - pending
            stats['tests_passed'] = passed
            stats['tests_failed'] = failed
            stats['tests_skipped'] = pending
            return stats

        # Minitest: "15 runs, 20 assertions, 2 failures, 0 errors, 1 skips"
        minitest_match = re.search(
            r"(\d+)\s+runs?,\s+\d+\s+assertions?,\s+(\d+)\s+failures?,\s+\d+\s+errors?,\s+(\d+)\s+skips?",
            output
        )

        if minitest_match:
            runs = int(minitest_match.group(1))
            failures = int(minitest_match.group(2))
            skips = int(minitest_match.group(3))

            stats['tests_run'] = runs - skips
            stats['tests_failed'] = failures
            stats['tests_passed'] = runs - failures - skips
            stats['tests_skipped'] = skips

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

    parser = argparse.ArgumentParser(description="Bundler Manager")
    parser.add_argument("--project-dir", default=".", help="Project directory")
    parser.add_argument("command", choices=["info", "install", "test", "update", "add", "exec", "show", "check", "clean"],
                       help="Command to execute")
    parser.add_argument("--gem", help="Gem name")
    parser.add_argument("--version", help="Gem version")
    parser.add_argument("--group", help="Dependency group")
    parser.add_argument("--deployment", action="store_true", help="Deployment mode")
    parser.add_argument("--without", help="Groups to exclude (comma-separated)")
    parser.add_argument("--exec-cmd", help="Command to execute with bundle exec")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    try:
        bundler = BundlerManager(project_dir=args.project_dir)

        if args.command == "info":
            info = bundler.get_project_info()
            print(json.dumps(info, indent=2))

        elif args.command == "install":
            without = args.without.split(",") if args.without else None
            result = bundler.install(deployment=args.deployment, without=without)
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "test":
            result = bundler.test(verbose=args.verbose)
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "update":
            result = bundler.update(gem=args.gem)
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "add":
            if not args.gem:
                print("Error: --gem required for add command")
                sys.exit(1)
            bundler.install_dependency(args.gem, version=args.version, group=args.group)
            print(f"Added {args.gem}")

        elif args.command == "exec":
            if not args.exec_cmd:
                print("Error: --exec-cmd required for exec command")
                sys.exit(1)
            cmd = args.exec_cmd.split()
            result = bundler.exec(cmd)
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "show":
            if not args.gem:
                print("Error: --gem required for show command")
                sys.exit(1)
            result = bundler.show(args.gem)
            print(result.output)

        elif args.command == "check":
            result = bundler.check()
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "clean":
            result = bundler.clean()
            print(result)

    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)
