#!/usr/bin/env python3
"""
Research Stage Exception Hierarchy

Custom exceptions for the Research Agent stage with proper exception wrapping.
Follows best practice of wrapping lower-level exceptions with context.
"""

from typing import Optional


class ResearchStageError(Exception):
    """Base exception for Research Stage errors"""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        """
        Initialize with message and optional cause.

        Args:
            message: Error message describing what went wrong
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.cause = cause

    def __str__(self) -> str:
        if self.cause:
            return f"{self.message} (caused by: {type(self.cause).__name__}: {str(self.cause)})"
        return self.message


class ResearchSourceError(ResearchStageError):
    """Exception raised when external research source fails"""

    def __init__(self, source_name: str, message: str, cause: Optional[Exception] = None):
        """
        Initialize with source name, message, and optional cause.

        Args:
            source_name: Name of the research source (GitHub, HuggingFace, etc.)
            message: Error message
            cause: Original exception
        """
        self.source_name = source_name
        super().__init__(f"Research source '{source_name}' failed: {message}", cause)


class ExampleStorageError(ResearchStageError):
    """Exception raised when storing examples to RAG fails"""

    def __init__(self, artifact_id: str, message: str, cause: Optional[Exception] = None):
        """
        Initialize with artifact ID, message, and optional cause.

        Args:
            artifact_id: ID of artifact being stored
            message: Error message
            cause: Original exception
        """
        self.artifact_id = artifact_id
        super().__init__(f"Failed to store artifact '{artifact_id}': {message}", cause)


class ResearchTimeoutError(ResearchStageError):
    """Exception raised when research operation times out"""

    def __init__(self, operation: str, timeout_seconds: int, cause: Optional[Exception] = None):
        """
        Initialize with operation name, timeout duration, and optional cause.

        Args:
            operation: Name of operation that timed out
            timeout_seconds: Timeout duration in seconds
            cause: Original exception
        """
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Research operation '{operation}' timed out after {timeout_seconds}s",
            cause
        )


class ResearchConfigurationError(ResearchStageError):
    """Exception raised when research configuration is invalid"""

    def __init__(self, config_key: str, message: str, cause: Optional[Exception] = None):
        """
        Initialize with config key, message, and optional cause.

        Args:
            config_key: Configuration key that is invalid
            message: Error message
            cause: Original exception
        """
        self.config_key = config_key
        super().__init__(f"Invalid configuration for '{config_key}': {message}", cause)
