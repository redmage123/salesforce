#!/usr/bin/env python3
"""
Artemis Exception Hierarchy

Custom exception classes for the Artemis pipeline system.
All exceptions inherit from ArtemisException base class.

This follows best practices:
- Never use bare 'except Exception' - always use specific exceptions
- Provides clear error context and debugging information
- Enables proper error handling and recovery strategies
"""

from typing import Optional, Dict, Any


class ArtemisException(Exception):
    """
    Base exception for all Artemis errors

    All custom Artemis exceptions should inherit from this class.
    This allows catching all Artemis-specific errors with a single handler.
    """

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize Artemis exception

        Args:
            message: Human-readable error message
            context: Additional context about the error (card_id, stage, etc.)
            original_exception: Original exception that was wrapped
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.original_exception = original_exception

    def __str__(self) -> str:
        """Format exception message with context"""
        msg = self.message
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            msg = f"{msg} (Context: {context_str})"
        if self.original_exception:
            msg = f"{msg} | Caused by: {type(self.original_exception).__name__}: {self.original_exception}"
        return msg


# ============================================================================
# DATABASE / RAG EXCEPTIONS
# ============================================================================

class RAGException(ArtemisException):
    """Base exception for RAG-related errors"""
    pass


class RAGQueryError(RAGException):
    """Error querying RAG database"""
    pass


class RAGStorageError(RAGException):
    """Error storing data in RAG database"""
    pass


class RAGConnectionError(RAGException):
    """Error connecting to RAG database (ChromaDB)"""
    pass


# ============================================================================
# REDIS EXCEPTIONS
# ============================================================================

class RedisException(ArtemisException):
    """Base exception for Redis-related errors"""
    pass


class RedisConnectionError(RedisException):
    """Error connecting to Redis"""
    pass


class RedisCacheError(RedisException):
    """Error performing Redis cache operation"""
    pass


# ============================================================================
# LLM / API EXCEPTIONS
# ============================================================================

class LLMException(ArtemisException):
    """Base exception for LLM-related errors"""
    pass


class LLMClientError(LLMException):
    """Error initializing or using LLM client"""
    pass


class LLMAPIError(LLMException):
    """Error calling LLM API (OpenAI, Anthropic, etc.)"""
    pass


class LLMResponseParsingError(LLMException):
    """Error parsing LLM response (invalid JSON, etc.)"""
    pass


class LLMRateLimitError(LLMException):
    """LLM API rate limit exceeded"""
    pass


class LLMAuthenticationError(LLMException):
    """LLM API authentication failed (invalid API key, etc.)"""
    pass


# ============================================================================
# DEVELOPER / EXECUTION EXCEPTIONS
# ============================================================================

class DeveloperException(ArtemisException):
    """Base exception for developer agent errors"""
    pass


class DeveloperExecutionError(DeveloperException):
    """Error during developer agent execution"""
    pass


class DeveloperPromptError(DeveloperException):
    """Error building or loading developer prompt"""
    pass


class DeveloperOutputError(DeveloperException):
    """Error writing developer output files"""
    pass


#============================================================================
# CODE REVIEW EXCEPTIONS
# ============================================================================

class CodeReviewException(ArtemisException):
    """Base exception for code review errors"""
    pass


class CodeReviewExecutionError(CodeReviewException):
    """Error during code review execution"""
    pass


class CodeReviewScoringError(CodeReviewException):
    """Error calculating code review score"""
    pass


class CodeReviewFeedbackError(CodeReviewException):
    """Error extracting or processing code review feedback"""
    pass


# ============================================================================
# PIPELINE / ORCHESTRATION EXCEPTIONS
# ============================================================================

class PipelineException(ArtemisException):
    """Base exception for pipeline orchestration errors"""
    pass


class PipelineStageError(PipelineException):
    """Error during pipeline stage execution"""
    pass


class PipelineValidationError(PipelineException):
    """Pipeline validation failed (missing dependencies, etc.)"""
    pass


class PipelineConfigurationError(PipelineException):
    """Pipeline configuration error (missing env vars, etc.)"""
    pass


class ConfigurationError(ArtemisException):
    """Base exception for configuration errors (API keys, env vars, etc.)"""
    pass


# ============================================================================
# KANBAN / TASK MANAGEMENT EXCEPTIONS
# ============================================================================

class KanbanException(ArtemisException):
    """Base exception for Kanban board errors"""
    pass


class KanbanCardNotFoundError(KanbanException):
    """Kanban card not found"""
    pass


class KanbanBoardError(KanbanException):
    """Error loading or saving Kanban board"""
    pass


class KanbanWIPLimitError(KanbanException):
    """WIP limit exceeded"""
    pass


# ============================================================================
# FILE / IO EXCEPTIONS
# ============================================================================

class ArtemisFileError(ArtemisException):
    """Base exception for file operations"""
    pass


class FileNotFoundError(ArtemisFileError):
    """Required file not found"""
    pass


class FileWriteError(ArtemisFileError):
    """Error writing file"""
    pass


class FileReadError(ArtemisFileError):
    """Error reading file"""
    pass


# ============================================================================
# PROJECT ANALYSIS EXCEPTIONS
# ============================================================================

class ProjectAnalysisException(ArtemisException):
    """Base exception for project analysis errors"""
    pass


class ADRGenerationError(ProjectAnalysisException):
    """Error generating ADR (Architectural Decision Record)"""
    pass


class DependencyAnalysisError(ProjectAnalysisException):
    """Error analyzing project dependencies"""
    pass


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def wrap_exception(
    exception: Exception,
    artemis_exception_class: type[ArtemisException],
    message: str,
    context: Optional[Dict[str, Any]] = None
) -> ArtemisException:
    """
    Wrap a generic exception in an Artemis-specific exception

    Args:
        exception: Original exception
        artemis_exception_class: Artemis exception class to wrap with
        message: Human-readable error message
        context: Additional context

    Returns:
        Wrapped Artemis exception

    Example:
        try:
            some_operation()
        except Exception as e:
            raise wrap_exception(
                e,
                RAGQueryError,
                "Failed to query RAG database",
                {"card_id": "123", "query": "test"}
            )
    """
    return artemis_exception_class(
        message=message,
        context=context,
        original_exception=exception
    )
