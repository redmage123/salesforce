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


# Alias for compatibility with AIQueryService
RAGError = RAGException


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


# Alias for compatibility with AIQueryService
LLMError = LLMException


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
# REQUIREMENTS PARSING EXCEPTIONS
# ============================================================================

class RequirementsException(ArtemisException):
    """Base exception for requirements parsing errors"""
    pass


class RequirementsFileError(RequirementsException):
    """Error reading requirements file"""
    pass


class RequirementsParsingError(RequirementsException):
    """Error parsing requirements content"""
    pass


class RequirementsValidationError(RequirementsException):
    """Requirements validation failed"""
    pass


class RequirementsExportError(RequirementsException):
    """Error exporting requirements to YAML/JSON"""
    pass


class UnsupportedDocumentFormatError(RequirementsException):
    """Document format not supported"""
    pass


class DocumentReadError(RequirementsException):
    """Error reading document content"""
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
# KNOWLEDGE GRAPH EXCEPTIONS
# ============================================================================

class KnowledgeGraphError(ArtemisException):
    """Base class for Knowledge Graph errors"""
    pass


class KGQueryError(KnowledgeGraphError):
    """Error executing Knowledge Graph query"""
    pass


class KGConnectionError(KnowledgeGraphError):
    """Error connecting to Knowledge Graph database"""
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
# SPRINT WORKFLOW EXCEPTIONS
# ============================================================================

class SprintException(ArtemisException):
    """Base exception for sprint workflow errors"""
    pass


class SprintPlanningError(SprintException):
    """Error during sprint planning"""
    pass


class FeatureExtractionError(SprintException):
    """Error extracting or parsing features"""
    pass


class PlanningPokerError(SprintException):
    """Error during Planning Poker estimation"""
    pass


class SprintAllocationError(SprintException):
    """Error allocating features to sprints"""
    pass


class ProjectReviewError(SprintException):
    """Error during project review"""
    pass


class RetrospectiveError(SprintException):
    """Error during sprint retrospective"""
    pass


class UIUXEvaluationError(SprintException):
    """Error during UI/UX evaluation"""
    pass


class WCAGEvaluationError(UIUXEvaluationError):
    """Error during WCAG accessibility evaluation"""
    pass


class GDPREvaluationError(UIUXEvaluationError):
    """Error during GDPR compliance evaluation"""
    pass


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_wrapped_exception(
    exception: Exception,
    artemis_exception_class: type[ArtemisException],
    message: str,
    context: Optional[Dict[str, Any]] = None
) -> ArtemisException:
    """
    Wrap a generic exception in an Artemis-specific exception (utility function)

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
            raise create_wrapped_exception(
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


# Decorator factory version for use with @wrap_exception syntax
def wrap_exception(artemis_exception_class: type[ArtemisException], message: str):
    """
    Decorator factory to wrap exceptions raised in a function

    Usage:
        @wrap_exception(PipelineStageError, "Stage execution failed")
        def execute(self, card, context):
            # ... function code

    Args:
        artemis_exception_class: The Artemis exception class to wrap with
        message: Human-readable error message

    Returns:
        Decorator function that wraps exceptions
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ArtemisException:
                # Pattern #10: Early return - don't wrap Artemis exceptions
                raise
            except Exception as e:
                # Wrap non-Artemis exceptions
                raise artemis_exception_class(
                    message=f"{message}: {str(e)}",
                    original_exception=e
                )
        return wrapper
    return decorator
