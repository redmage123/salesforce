#!/usr/bin/env python3
"""
Build System Exception Hierarchy

Enterprise-grade exception hierarchy for all build system operations.
All exceptions inherit from PipelineStageError for proper integration
with Artemis pipeline error handling.

Design Pattern: Exception Hierarchy with context preservation
"""

from typing import Dict, Any, Optional
from artemis_exceptions import PipelineStageError


class BuildSystemError(PipelineStageError):
    """
    Base exception for all build system errors.

    All build system exceptions inherit from this class and
    provide rich context about what went wrong.
    """

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize build system error.

        Args:
            message: Human-readable error message
            context: Additional context (build system, command, etc.)
            original_exception: Original exception if wrapping
        """
        super().__init__(message, context)
        self.original_exception = original_exception

    def __str__(self) -> str:
        """Enhanced string representation with context"""
        base = super().__str__()
        if self.original_exception:
            base += f"\nCaused by: {type(self.original_exception).__name__}: {self.original_exception}"
        return base


class BuildSystemNotFoundError(BuildSystemError):
    """
    Build system executable not found in PATH.

    Raised when required build tool (maven, gradle, npm, etc.)
    is not installed or not in PATH.

    Example:
        raise BuildSystemNotFoundError(
            "Maven executable not found",
            {"build_system": "maven", "expected_path": "/usr/bin/mvn"}
        )
    """
    pass


class ProjectConfigurationError(BuildSystemError):
    """
    Project configuration file missing or invalid.

    Raised when build configuration file (pom.xml, package.json, etc.)
    is missing, malformed, or contains invalid settings.

    Example:
        raise ProjectConfigurationError(
            "pom.xml is missing required groupId",
            {"config_file": "pom.xml", "project_dir": "/path/to/project"}
        )
    """
    pass


class BuildExecutionError(BuildSystemError):
    """
    Error during build execution.

    Raised when build process fails (compilation errors, missing
    dependencies, etc.).

    Example:
        raise BuildExecutionError(
            "Maven build failed with compilation errors",
            {
                "build_system": "maven",
                "phase": "compile",
                "exit_code": 1,
                "errors": ["Error: Cannot find symbol MyClass"]
            }
        )
    """
    pass


class TestExecutionError(BuildSystemError):
    """
    Error during test execution.

    Raised when test execution fails (test failures, configuration
    issues, missing test dependencies).

    Example:
        raise TestExecutionError(
            "5 tests failed",
            {
                "build_system": "gradle",
                "tests_run": 50,
                "tests_failed": 5,
                "failed_tests": ["UserServiceTest.testCreate"]
            }
        )
    """
    pass


class DependencyInstallError(BuildSystemError):
    """
    Error installing dependency.

    Raised when dependency installation fails (package not found,
    version conflict, network issues).

    Example:
        raise DependencyInstallError(
            "Failed to install package 'react@99.0.0'",
            {
                "build_system": "npm",
                "package": "react",
                "version": "99.0.0",
                "reason": "No matching version found"
            }
        )
    """
    pass


class BuildTimeoutError(BuildSystemError):
    """
    Build operation timed out.

    Raised when build, test, or other operation exceeds
    configured timeout.

    Example:
        raise BuildTimeoutError(
            "Build timed out after 600 seconds",
            {
                "build_system": "cargo",
                "operation": "build",
                "timeout": 600
            }
        )
    """
    pass


class DependencyResolutionError(BuildSystemError):
    """
    Dependency resolution failed.

    Raised when build system cannot resolve dependencies
    (version conflicts, missing transitive dependencies).

    Example:
        raise DependencyResolutionError(
            "Version conflict for 'jackson-databind'",
            {
                "build_system": "maven",
                "package": "jackson-databind",
                "conflicting_versions": ["2.12.0", "2.15.0"]
            }
        )
    """
    pass


class UnsupportedBuildSystemError(BuildSystemError):
    """
    Build system not supported.

    Raised when attempting to use a build system that is not
    yet implemented or is not supported on current platform.

    Example:
        raise UnsupportedBuildSystemError(
            "Bazel build system not yet supported",
            {"requested_system": "bazel", "supported_systems": ["maven", "gradle", "npm"]}
        )
    """
    pass


# Convenience function for quick exception creation
def build_error(
    message: str,
    error_type: type = BuildSystemError,
    **context
) -> BuildSystemError:
    """
    Convenience function to create build system errors.

    Args:
        message: Error message
        error_type: Exception class to instantiate
        **context: Context as keyword arguments

    Returns:
        Initialized exception

    Example:
        raise build_error(
            "Maven not found",
            error_type=BuildSystemNotFoundError,
            build_system="maven",
            expected_path="/usr/bin/mvn"
        )
    """
    return error_type(message, context)
