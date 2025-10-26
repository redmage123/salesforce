#!/usr/bin/env python3
"""
Go Modules Build Manager (Go)

Enterprise-grade Go build system management using Go modules.

Design Patterns:
- Template Method: Inherits from BuildManagerBase
- Exception Wrapper: All errors properly wrapped
- Strategy Pattern: Different build modes and architectures
"""

from pathlib import Path
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from enum import Enum
import re
import json

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


class BuildMode(Enum):
    """Go build modes"""
    DEFAULT = ""
    PIE = "-buildmode=pie"
    C_ARCHIVE = "-buildmode=c-archive"
    C_SHARED = "-buildmode=c-shared"
    PLUGIN = "-buildmode=plugin"


class GoArch(Enum):
    """Common Go architectures"""
    AMD64 = "amd64"
    ARM64 = "arm64"
    ARM = "arm"
    I386 = "386"


class GoOS(Enum):
    """Common Go operating systems"""
    LINUX = "linux"
    DARWIN = "darwin"
    WINDOWS = "windows"
    FREEBSD = "freebsd"


@dataclass
class GoModuleInfo:
    """go.mod module information"""
    module_path: str
    go_version: str
    dependencies: Dict[str, str] = field(default_factory=dict)
    replace_directives: Dict[str, str] = field(default_factory=dict)
    exclude_directives: List[str] = field(default_factory=list)
    has_sum_file: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "modulePath": self.module_path,
            "goVersion": self.go_version,
            "dependencies": self.dependencies,
            "replaceDirectives": self.replace_directives,
            "excludeDirectives": self.exclude_directives,
            "hasSumFile": self.has_sum_file
        }


@register_build_manager(BuildSystem.GO_MOD)
class GoModManager(BuildManagerBase):
    """
    Enterprise-grade Go modules manager for Go projects.

    Example:
        go_mod = GoModManager(project_dir="/path/to/project")
        result = go_mod.build(output="app")
        test_result = go_mod.test()
    """

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        logger: Optional['logging.Logger'] = None
    ):
        """
        Initialize Go modules manager.

        Args:
            project_dir: Project directory (contains go.mod)
            logger: Logger instance

        Raises:
            BuildSystemNotFoundError: If Go not found
            ProjectConfigurationError: If go.mod invalid
        """
        self.go_mod_path = None
        self.go_sum_path = None

        super().__init__(project_dir, logger)

        self.go_sum_path = self.project_dir / "go.sum"

    @wrap_exception(BuildSystemNotFoundError, "Go not found")
    def _validate_installation(self) -> None:
        """
        Validate Go is installed.

        Raises:
            BuildSystemNotFoundError: If Go not in PATH
        """
        result = self._execute_command(
            ["go", "version"],
            timeout=10,
            error_type=BuildSystemNotFoundError,
            error_message="Go not installed or not in PATH"
        )

        # Extract version
        version_match = re.search(r"go version go([\d.]+)", result.output)
        if version_match:
            version = version_match.group(1)
            self.logger.info(f"Using Go version: {version}")

    @wrap_exception(ProjectConfigurationError, "Invalid Go module")
    def _validate_project(self) -> None:
        """
        Validate go.mod exists.

        Raises:
            ProjectConfigurationError: If go.mod missing
        """
        self.go_mod_path = self.project_dir / "go.mod"

        if not self.go_mod_path.exists():
            raise ProjectConfigurationError(
                "go.mod not found",
                {"project_dir": str(self.project_dir)}
            )

    @wrap_exception(ProjectConfigurationError, "Failed to parse go.mod")
    def get_project_info(self) -> Dict[str, Any]:
        """
        Parse go.mod for project information.

        Returns:
            Dict with project information

        Raises:
            ProjectConfigurationError: If go.mod malformed
        """
        with open(self.go_mod_path, 'r') as f:
            content = f.read()

        # Parse module path
        module_match = re.search(r'module\s+(\S+)', content)
        module_path = module_match.group(1) if module_match else ""

        # Parse Go version
        go_version_match = re.search(r'go\s+([\d.]+)', content)
        go_version = go_version_match.group(1) if go_version_match else "1.21"

        # Parse dependencies (simplified - for full parsing use `go list -m all`)
        dependencies = {}
        require_block = re.search(r'require\s*\((.*?)\)', content, re.DOTALL)
        if require_block:
            for line in require_block.group(1).split('\n'):
                dep_match = re.match(r'\s*(\S+)\s+v([\d.]+(?:-[\w.]+)?)', line)
                if dep_match:
                    dependencies[dep_match.group(1)] = f"v{dep_match.group(2)}"

        # Parse replace directives
        replace_directives = {}
        for replace_match in re.finditer(r'replace\s+(\S+)\s+=>\s+(\S+)', content):
            replace_directives[replace_match.group(1)] = replace_match.group(2)

        # Parse exclude directives
        exclude_directives = []
        for exclude_match in re.finditer(r'exclude\s+(\S+)', content):
            exclude_directives.append(exclude_match.group(1))

        info = GoModuleInfo(
            module_path=module_path,
            go_version=go_version,
            dependencies=dependencies,
            replace_directives=replace_directives,
            exclude_directives=exclude_directives,
            has_sum_file=self.go_sum_path.exists()
        )

        return info.to_dict()

    @wrap_exception(BuildExecutionError, "Go build failed")
    def build(
        self,
        output: Optional[str] = None,
        tags: Optional[List[str]] = None,
        ldflags: Optional[str] = None,
        race: bool = False,
        goos: Optional[str] = None,
        goarch: Optional[str] = None,
        **kwargs
    ) -> BuildResult:
        """
        Build Go project.

        Args:
            output: Output binary name
            tags: Build tags
            ldflags: Linker flags
            race: Enable race detector
            goos: Target OS (GOOS)
            goarch: Target architecture (GOARCH)

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If build fails

        Example:
            result = go_mod.build(output="app", tags=["production"])
        """
        cmd = ["go", "build"]

        if output:
            cmd.extend(["-o", output])

        if tags:
            cmd.extend(["-tags", ",".join(tags)])

        if ldflags:
            cmd.extend(["-ldflags", ldflags])

        if race:
            cmd.append("-race")

        # Set environment variables for cross-compilation
        env = {}
        if goos:
            env["GOOS"] = goos
        if goarch:
            env["GOARCH"] = goarch

        return self._execute_command(
            cmd,
            timeout=600,
            error_type=BuildExecutionError,
            error_message="Go build failed",
            env=env if env else None
        )

    @wrap_exception(TestExecutionError, "Go tests failed")
    def test(
        self,
        package: Optional[str] = None,
        verbose: bool = False,
        race: bool = False,
        cover: bool = False,
        bench: bool = False,
        **kwargs
    ) -> BuildResult:
        """
        Run Go tests.

        Args:
            package: Specific package to test (default: ./...)
            verbose: Verbose output
            race: Enable race detector
            cover: Enable coverage
            bench: Run benchmarks

        Returns:
            BuildResult with test statistics

        Raises:
            TestExecutionError: If tests fail

        Example:
            result = go_mod.test(verbose=True, cover=True)
        """
        cmd = ["go", "test"]

        if verbose:
            cmd.append("-v")

        if race:
            cmd.append("-race")

        if cover:
            cmd.append("-cover")

        if bench:
            cmd.append("-bench=.")

        # Default to all packages
        cmd.append(package if package else "./...")

        return self._execute_command(
            cmd,
            timeout=300,
            error_type=TestExecutionError,
            error_message="Go test execution failed"
        )

    @wrap_exception(DependencyInstallError, "Failed to add dependency")
    def install_dependency(
        self,
        module: str,
        version: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Add a dependency to go.mod.

        Args:
            module: Module path
            version: Module version (optional)

        Returns:
            True if successful

        Raises:
            DependencyInstallError: If installation fails

        Example:
            go_mod.install_dependency("github.com/gin-gonic/gin", version="v1.9.0")
        """
        module_spec = f"{module}@{version}" if version else module

        cmd = ["go", "get", module_spec]

        result = self._execute_command(
            cmd,
            timeout=120,
            error_type=DependencyInstallError,
            error_message=f"Failed to add module {module}"
        )

        self.logger.info(f"Added module {module}")
        return True

    @wrap_exception(BuildExecutionError, "Failed to download dependencies")
    def download_dependencies(self) -> BuildResult:
        """
        Download all dependencies.

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If download fails

        Example:
            go_mod.download_dependencies()
        """
        cmd = ["go", "mod", "download"]

        return self._execute_command(
            cmd,
            timeout=300,
            error_type=BuildExecutionError,
            error_message="Dependency download failed"
        )

    @wrap_exception(BuildExecutionError, "Failed to tidy dependencies")
    def tidy(self) -> BuildResult:
        """
        Clean up go.mod and go.sum.

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If tidy fails

        Example:
            go_mod.tidy()
        """
        cmd = ["go", "mod", "tidy"]

        return self._execute_command(
            cmd,
            timeout=120,
            error_type=BuildExecutionError,
            error_message="go mod tidy failed"
        )

    @wrap_exception(BuildExecutionError, "Failed to verify dependencies")
    def verify(self) -> BuildResult:
        """
        Verify dependencies have expected content.

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If verification fails

        Example:
            go_mod.verify()
        """
        cmd = ["go", "mod", "verify"]

        return self._execute_command(
            cmd,
            timeout=60,
            error_type=BuildExecutionError,
            error_message="go mod verify failed"
        )

    @wrap_exception(BuildExecutionError, "Failed to run go fmt")
    def fmt(self) -> BuildResult:
        """
        Format Go code.

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If formatting fails

        Example:
            go_mod.fmt()
        """
        cmd = ["go", "fmt", "./..."]

        return self._execute_command(
            cmd,
            timeout=60,
            error_type=BuildExecutionError,
            error_message="go fmt failed"
        )

    @wrap_exception(BuildExecutionError, "Failed to run go vet")
    def vet(self) -> BuildResult:
        """
        Run go vet for suspicious code.

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If vet fails

        Example:
            go_mod.vet()
        """
        cmd = ["go", "vet", "./..."]

        return self._execute_command(
            cmd,
            timeout=120,
            error_type=BuildExecutionError,
            error_message="go vet failed"
        )

    def clean(self) -> BuildResult:
        """
        Clean build cache.

        Returns:
            BuildResult
        """
        cmd = ["go", "clean", "-cache"]

        try:
            return self._execute_command(
                cmd,
                timeout=30,
                error_type=BuildExecutionError,
                error_message="go clean failed"
            )
        except BuildExecutionError as e:
            self.logger.warning(f"Clean failed: {e}")
            return BuildResult(
                success=False,
                exit_code=1,
                duration=0.0,
                output=str(e),
                build_system="go"
            )

    def _extract_test_stats(self, output: str) -> Dict[str, int]:
        """
        Extract test statistics from Go test output.

        Args:
            output: Go test output

        Returns:
            Dict with test statistics
        """
        stats = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'tests_skipped': 0
        }

        # Go test summary: "PASS" or "FAIL" with test counts
        # Example: "ok  	package	0.123s"
        # Example: "FAIL	package	0.123s"

        # Count test results
        passed = len(re.findall(r'--- PASS:', output))
        failed = len(re.findall(r'--- FAIL:', output))
        skipped = len(re.findall(r'--- SKIP:', output))

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

    parser = argparse.ArgumentParser(description="Go Modules Manager")
    parser.add_argument("--project-dir", default=".", help="Project directory")
    parser.add_argument("command", choices=["info", "build", "test", "get", "download", "tidy", "verify", "fmt", "vet", "clean"],
                       help="Command to execute")
    parser.add_argument("--output", help="Output binary name")
    parser.add_argument("--tags", help="Build tags (comma-separated)")
    parser.add_argument("--module", help="Module to add")
    parser.add_argument("--version", help="Module version")
    parser.add_argument("--package", help="Package to test")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--race", action="store_true", help="Enable race detector")
    parser.add_argument("--cover", action="store_true", help="Enable coverage")

    args = parser.parse_args()

    try:
        go_mod = GoModManager(project_dir=args.project_dir)

        if args.command == "info":
            info = go_mod.get_project_info()
            print(json.dumps(info, indent=2))

        elif args.command == "build":
            tags = args.tags.split(",") if args.tags else None
            result = go_mod.build(output=args.output, tags=tags, race=args.race)
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "test":
            result = go_mod.test(package=args.package, verbose=args.verbose,
                               race=args.race, cover=args.cover)
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "get":
            if not args.module:
                print("Error: --module required for get command")
                sys.exit(1)
            go_mod.install_dependency(args.module, version=args.version)
            print(f"Added {args.module}")

        elif args.command == "download":
            result = go_mod.download_dependencies()
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "tidy":
            result = go_mod.tidy()
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "verify":
            result = go_mod.verify()
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "fmt":
            result = go_mod.fmt()
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "vet":
            result = go_mod.vet()
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "clean":
            result = go_mod.clean()
            print(result)

    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)
