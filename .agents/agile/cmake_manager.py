#!/usr/bin/env python3
"""
CMake Build Manager

Enterprise-grade C/C++ build system management using CMake.

Design Patterns:
- Template Method: Inherits from BuildManagerBase
- Strategy Pattern: Different generators (Unix Makefiles, Ninja, etc.)
- Exception Wrapper: All errors properly wrapped
"""

from pathlib import Path
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from enum import Enum
import re

from artemis_exceptions import wrap_exception
from build_system_exceptions import (
    BuildSystemNotFoundError,
    ProjectConfigurationError,
    BuildExecutionError,
    TestExecutionError
)
from build_manager_base import BuildManagerBase, BuildResult
from build_manager_factory import register_build_manager, BuildSystem


class CMakeGenerator(Enum):
    """CMake generators"""
    UNIX_MAKEFILES = "Unix Makefiles"
    NINJA = "Ninja"
    VISUAL_STUDIO = "Visual Studio"
    XCODE = "Xcode"


class BuildType(Enum):
    """CMake build types"""
    DEBUG = "Debug"
    RELEASE = "Release"
    REL_WITH_DEB_INFO = "RelWithDebInfo"
    MIN_SIZE_REL = "MinSizeRel"


@dataclass
class CMakeProjectInfo:
    """CMake project information"""
    project_name: str
    version: str
    languages: List[str]
    build_dir: Path
    source_dir: Path
    generator: str
    build_type: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.project_name,
            "version": self.version,
            "languages": self.languages,
            "buildDir": str(self.build_dir),
            "sourceDir": str(self.source_dir),
            "generator": self.generator,
            "buildType": self.build_type
        }


@register_build_manager(BuildSystem.CMAKE)
class CMakeManager(BuildManagerBase):
    """
    Enterprise-grade CMake manager for C/C++ projects.

    Example:
        cmake = CMakeManager(project_dir="/path/to/project")
        cmake.configure(build_type="Release")
        result = cmake.build(target="all")
        test_result = cmake.test()
    """

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        logger: Optional['logging.Logger'] = None,
        build_dir: Optional[Path] = None
    ):
        """
        Initialize CMake manager.

        Args:
            project_dir: Project directory (contains CMakeLists.txt)
            logger: Logger instance
            build_dir: Build directory (defaults to project_dir/build)

        Raises:
            BuildSystemNotFoundError: If CMake not found
            ProjectConfigurationError: If CMakeLists.txt missing
        """
        self.cmakelists_path = None
        self.build_directory = None

        super().__init__(project_dir, logger)

        # Set build directory after parent init
        if build_dir:
            self.build_directory = Path(build_dir)
        else:
            self.build_directory = self.project_dir / "build"

    @wrap_exception(BuildSystemNotFoundError, "CMake not found")
    def _validate_installation(self) -> None:
        """
        Validate CMake is installed.

        Raises:
            BuildSystemNotFoundError: If CMake not in PATH
        """
        result = self._execute_command(
            ["cmake", "--version"],
            timeout=10,
            error_type=BuildSystemNotFoundError,
            error_message="CMake not installed or not in PATH"
        )

        # Extract version
        version_match = re.search(r"cmake version ([\d.]+)", result.output)
        if version_match:
            version = version_match.group(1)
            self.logger.info(f"Using CMake version: {version}")

    @wrap_exception(ProjectConfigurationError, "Invalid CMake project")
    def _validate_project(self) -> None:
        """
        Validate CMakeLists.txt exists.

        Raises:
            ProjectConfigurationError: If CMakeLists.txt missing
        """
        self.cmakelists_path = self.project_dir / "CMakeLists.txt"

        if not self.cmakelists_path.exists():
            raise ProjectConfigurationError(
                "CMakeLists.txt not found",
                {"project_dir": str(self.project_dir)}
            )

    @wrap_exception(ProjectConfigurationError, "Failed to parse CMakeLists.txt")
    def get_project_info(self) -> Dict[str, Any]:
        """
        Parse CMakeLists.txt for project information.

        Returns:
            Dict with project information

        Raises:
            ProjectConfigurationError: If CMakeLists.txt malformed
        """
        with open(self.cmakelists_path, 'r') as f:
            content = f.read()

        # Extract project name
        project_match = re.search(r"project\s*\(\s*(\w+)", content, re.IGNORECASE)
        project_name = project_match.group(1) if project_match else "Unknown"

        # Extract version
        version_match = re.search(r"VERSION\s+([\d.]+)", content, re.IGNORECASE)
        version = version_match.group(1) if version_match else "0.0.0"

        # Extract languages
        lang_match = re.search(r"LANGUAGES\s+([\w\s]+)", content, re.IGNORECASE)
        languages = lang_match.group(1).split() if lang_match else ["C", "CXX"]

        info = CMakeProjectInfo(
            project_name=project_name,
            version=version,
            languages=languages,
            build_dir=self.build_directory,
            source_dir=self.project_dir,
            generator="Unix Makefiles",  # Default
            build_type="Release"  # Default
        )

        return info.to_dict()

    @wrap_exception(BuildExecutionError, "CMake configuration failed")
    def configure(
        self,
        build_type: str = "Release",
        generator: Optional[str] = None,
        options: Optional[Dict[str, str]] = None
    ) -> BuildResult:
        """
        Configure CMake project.

        Args:
            build_type: Build type (Debug, Release, etc.)
            generator: CMake generator
            options: Additional CMake options

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If configuration fails

        Example:
            cmake.configure(
                build_type="Release",
                options={"BUILD_TESTING": "ON"}
            )
        """
        # Create build directory
        self.build_directory.mkdir(parents=True, exist_ok=True)

        # Build command
        cmd = ["cmake", "-B", str(self.build_directory), "-S", str(self.project_dir)]

        # Build type
        cmd.extend([f"-DCMAKE_BUILD_TYPE={build_type}"])

        # Generator
        if generator:
            cmd.extend(["-G", generator])

        # Additional options
        if options:
            for key, value in options.items():
                cmd.append(f"-D{key}={value}")

        return self._execute_command(
            cmd,
            timeout=120,
            error_type=BuildExecutionError,
            error_message="CMake configuration failed"
        )

    @wrap_exception(BuildExecutionError, "Build failed")
    def build(
        self,
        target: Optional[str] = None,
        parallel: bool = True,
        clean: bool = False,
        **kwargs
    ) -> BuildResult:
        """
        Build CMake project.

        Args:
            target: Specific target to build (None = all)
            parallel: Enable parallel build
            clean: Clean before building

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If build fails

        Example:
            result = cmake.build(target="myapp", parallel=True)
        """
        # Configure if not already done
        if not (self.build_directory / "CMakeCache.txt").exists():
            self.configure()

        # Clean first if requested
        if clean:
            self.clean()

        # Build command
        cmd = ["cmake", "--build", str(self.build_directory)]

        # Target
        if target:
            cmd.extend(["--target", target])

        # Parallel build
        if parallel:
            import multiprocessing
            cpu_count = multiprocessing.cpu_count()
            cmd.extend(["--parallel", str(cpu_count)])

        return self._execute_command(
            cmd,
            timeout=600,
            error_type=BuildExecutionError,
            error_message="CMake build failed"
        )

    @wrap_exception(TestExecutionError, "Tests failed")
    def test(
        self,
        verbose: bool = False,
        parallel: bool = True,
        **kwargs
    ) -> BuildResult:
        """
        Run CMake tests using CTest.

        Args:
            verbose: Verbose output
            parallel: Run tests in parallel

        Returns:
            BuildResult with test statistics

        Raises:
            TestExecutionError: If tests fail

        Example:
            result = cmake.test(verbose=True)
        """
        cmd = ["ctest", "--test-dir", str(self.build_directory)]

        if verbose:
            cmd.append("--verbose")

        if parallel:
            import multiprocessing
            cpu_count = multiprocessing.cpu_count()
            cmd.extend(["--parallel", str(cpu_count)])

        return self._execute_command(
            cmd,
            timeout=300,
            error_type=TestExecutionError,
            error_message="CTest execution failed"
        )

    def clean(self) -> BuildResult:
        """
        Clean build artifacts.

        Returns:
            BuildResult
        """
        if self.build_directory.exists():
            import shutil
            self.logger.info(f"Removing {self.build_directory}...")
            shutil.rmtree(self.build_directory)

        return BuildResult(
            success=True,
            exit_code=0,
            duration=0.0,
            output="Clean completed",
            build_system="cmake"
        )

    def _extract_test_stats(self, output: str) -> Dict[str, int]:
        """
        Extract test statistics from CTest output.

        Args:
            output: CTest output

        Returns:
            Dict with test statistics
        """
        stats = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'tests_skipped': 0
        }

        # CTest summary: "100% tests passed, 0 tests failed out of 10"
        summary_match = re.search(
            r"(\d+)%\s+tests\s+passed,\s+(\d+)\s+tests\s+failed\s+out\s+of\s+(\d+)",
            output
        )

        if summary_match:
            failed = int(summary_match.group(2))
            total = int(summary_match.group(3))
            passed = total - failed

            stats['tests_run'] = total
            stats['tests_passed'] = passed
            stats['tests_failed'] = failed

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

    parser = argparse.ArgumentParser(description="CMake Manager")
    parser.add_argument("--project-dir", default=".", help="Project directory")
    parser.add_argument("--build-dir", help="Build directory")
    parser.add_argument("command", choices=["info", "configure", "build", "test", "clean"],
                       help="Command to execute")
    parser.add_argument("--build-type", default="Release", help="Build type")
    parser.add_argument("--target", help="Build target")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    try:
        cmake = CMakeManager(
            project_dir=args.project_dir,
            build_dir=args.build_dir
        )

        if args.command == "info":
            info = cmake.get_project_info()
            print(json.dumps(info, indent=2))

        elif args.command == "configure":
            result = cmake.configure(build_type=args.build_type)
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "build":
            result = cmake.build(target=args.target)
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "test":
            result = cmake.test(verbose=args.verbose)
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "clean":
            result = cmake.clean()
            print(result)

    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)
