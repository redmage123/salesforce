#!/usr/bin/env python3
"""
Build Manager Base Class

Abstract base class for all build managers using Template Method pattern.
Provides common functionality and enforces consistent interface.

Design Patterns:
- Template Method: Common build flow
- Dependency Injection: Logger injection
- Abstract Base Class: Interface enforcement
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import subprocess
import logging
import time

from artemis_exceptions import wrap_exception
from build_system_exceptions import (
    BuildSystemNotFoundError,
    ProjectConfigurationError,
    BuildExecutionError,
    TestExecutionError,
    BuildTimeoutError
)


@dataclass
class BuildResult:
    """
    Unified build result structure for all build systems.

    All build managers return this standardized result format,
    enabling consistent handling regardless of underlying build system.
    """
    success: bool
    exit_code: int
    duration: float
    output: str
    build_system: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """Human-readable summary"""
        status = "✓ SUCCESS" if self.success else "✗ FAILED"
        result = f"{status} [{self.build_system}] in {self.duration:.2f}s\n"

        if self.tests_run > 0:
            result += f"Tests: {self.tests_passed}/{self.tests_run} passed"
            if self.tests_failed > 0:
                result += f", {self.tests_failed} failed"
            if self.tests_skipped > 0:
                result += f", {self.tests_skipped} skipped"
            result += "\n"

        if self.errors:
            result += f"Errors: {len(self.errors)}\n"
        if self.warnings:
            result += f"Warnings: {len(self.warnings)}\n"

        return result


class BuildManagerBase(ABC):
    """
    Abstract base class for all build managers.

    Implements Template Method pattern to ensure consistent behavior
    across all build systems while allowing customization.

    All subclasses must implement:
    - _validate_installation()
    - _validate_project()
    - build()
    - test()
    - get_project_info()
    """

    # Performance: Pre-define keyword sets for O(1) membership testing
    # instead of creating lists repeatedly in hot paths
    ERROR_KEYWORDS = {'error:', '[error]', 'failed:', 'failure:'}
    WARNING_KEYWORDS = {'warning:', '[warning]', 'warn:'}

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize build manager.

        Args:
            project_dir: Project directory (defaults to current directory)
            logger: Logger instance (dependency injection)

        Raises:
            BuildSystemNotFoundError: If build system not installed
            ProjectConfigurationError: If project configuration invalid
        """
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        # Template method: Validate installation and project
        self._validate_installation()
        self._validate_project()

    @abstractmethod
    def _validate_installation(self) -> None:
        """
        Validate build system is installed.

        Must check that required executables are available in PATH.

        Raises:
            BuildSystemNotFoundError: If build system not found

        Example:
            result = subprocess.run(['mvn', '--version'], capture_output=True)
            if result.returncode != 0:
                raise BuildSystemNotFoundError("Maven not found")
        """
        pass

    @abstractmethod
    def _validate_project(self) -> None:
        """
        Validate project configuration.

        Must check that required configuration files exist and are valid.

        Raises:
            ProjectConfigurationError: If configuration invalid

        Example:
            if not (self.project_dir / 'pom.xml').exists():
                raise ProjectConfigurationError("pom.xml not found")
        """
        pass

    @abstractmethod
    def build(self, **kwargs) -> BuildResult:
        """
        Build the project.

        Args:
            **kwargs: Build system specific options

        Returns:
            BuildResult with build outcome

        Raises:
            BuildExecutionError: If build fails
            BuildTimeoutError: If build times out

        Example:
            def build(self, clean: bool = True, skip_tests: bool = False) -> BuildResult:
                cmd = ['mvn', 'package']
                if clean:
                    cmd.insert(1, 'clean')
                if skip_tests:
                    cmd.append('-DskipTests')
                return self._execute_command(cmd, timeout=600)
        """
        pass

    @abstractmethod
    def test(self, **kwargs) -> BuildResult:
        """
        Run tests.

        Args:
            **kwargs: Test system specific options

        Returns:
            BuildResult with test results

        Raises:
            TestExecutionError: If test execution fails
            BuildTimeoutError: If tests time out

        Example:
            def test(self, test_class: Optional[str] = None) -> BuildResult:
                cmd = ['mvn', 'test']
                if test_class:
                    cmd.append(f'-Dtest={test_class}')
                return self._execute_command(cmd, timeout=300)
        """
        pass

    @abstractmethod
    def get_project_info(self) -> Dict[str, Any]:
        """
        Get project information.

        Returns:
            Dict with project metadata (name, version, dependencies, etc.)

        Raises:
            ProjectConfigurationError: If cannot parse project info

        Example:
            def get_project_info(self) -> Dict[str, Any]:
                pom = self._parse_pom()
                return {
                    'name': pom.artifact_id,
                    'version': pom.version,
                    'group': pom.group_id
                }
        """
        pass

    def _execute_command(
        self,
        cmd: List[str],
        timeout: int = 300,
        error_type: type = BuildExecutionError,
        error_message: str = "Command execution failed"
    ) -> BuildResult:
        """
        Template method for executing build commands.

        Provides consistent error handling, timeout management,
        and result formatting across all build systems.

        Args:
            cmd: Command to execute as list
            timeout: Timeout in seconds
            error_type: Exception type to raise on failure
            error_message: Error message prefix

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If command fails
            BuildTimeoutError: If command times out
        """
        start_time = time.time()
        build_system = self.__class__.__name__.replace('Manager', '').lower()

        self.logger.info(f"Executing: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )

            duration = time.time() - start_time
            output = result.stdout + result.stderr

            # Parse errors and warnings
            errors = self._extract_errors(output)
            warnings = self._extract_warnings(output)

            # Parse test results if applicable
            test_stats = self._extract_test_stats(output)

            build_result = BuildResult(
                success=result.returncode == 0,
                exit_code=result.returncode,
                duration=duration,
                output=output,
                build_system=build_system,
                errors=errors[:20],  # Limit to 20 errors
                warnings=warnings[:20],  # Limit to 20 warnings
                **test_stats
            )

            if not build_result.success:
                self.logger.error(f"Command failed with exit code {result.returncode}")
                raise error_type(
                    f"{error_message}: exit code {result.returncode}",
                    {
                        "command": " ".join(cmd),
                        "exit_code": result.returncode,
                        "errors": errors[:5],
                        "duration": duration
                    }
                )

            self.logger.info(f"Command succeeded in {duration:.2f}s")
            return build_result

        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            self.logger.error(f"Command timed out after {timeout}s")
            raise BuildTimeoutError(
                f"Command timed out after {timeout}s",
                {
                    "command": " ".join(cmd),
                    "timeout": timeout,
                    "duration": duration
                },
                original_exception=e
            )

        except FileNotFoundError as e:
            self.logger.error(f"Command not found: {cmd[0]}")
            raise BuildSystemNotFoundError(
                f"Build system executable not found: {cmd[0]}",
                {"command": cmd[0], "full_command": " ".join(cmd)},
                original_exception=e
            )

    def _extract_errors(self, output: str) -> List[str]:
        """
        Extract error messages from build output.

        Can be overridden by subclasses for build-system-specific parsing.

        Args:
            output: Build output

        Returns:
            List of error messages
        """
        errors = []
        for line in output.splitlines():
            line_lower = line.lower()
            # Use class-level set instead of creating list every iteration
            if any(keyword in line_lower for keyword in self.ERROR_KEYWORDS):
                errors.append(line.strip())
        return errors

    def _extract_warnings(self, output: str) -> List[str]:
        """
        Extract warning messages from build output.

        Can be overridden by subclasses for build-system-specific parsing.

        Args:
            output: Build output

        Returns:
            List of warning messages
        """
        warnings = []
        for line in output.splitlines():
            line_lower = line.lower()
            # Use class-level set instead of creating list every iteration
            if any(keyword in line_lower for keyword in self.WARNING_KEYWORDS):
                warnings.append(line.strip())
        return warnings

    def _extract_test_stats(self, output: str) -> Dict[str, int]:
        """
        Extract test statistics from build output.

        Can be overridden by subclasses for build-system-specific parsing.

        Args:
            output: Build output

        Returns:
            Dict with tests_run, tests_passed, tests_failed, tests_skipped
        """
        # Default implementation returns zeros
        # Subclasses should override with specific parsing logic
        return {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'tests_skipped': 0
        }

    def clean(self) -> BuildResult:
        """
        Clean build artifacts.

        Default implementation that can be overridden.

        Returns:
            BuildResult
        """
        self.logger.info("No clean implementation for this build system")
        return BuildResult(
            success=True,
            exit_code=0,
            duration=0.0,
            output="Clean not implemented",
            build_system=self.__class__.__name__
        )

    def install_dependency(
        self,
        package: str,
        version: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Install a dependency.

        Default implementation that can be overridden.

        Args:
            package: Package name
            version: Package version (optional)
            **kwargs: Build system specific options

        Returns:
            True if successful

        Raises:
            DependencyInstallError: If installation fails
        """
        raise NotImplementedError(
            f"Dependency installation not implemented for {self.__class__.__name__}"
        )
