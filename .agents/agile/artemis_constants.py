#!/usr/bin/env python3
"""
Artemis Configuration Constants

Centralized constants for paths, timeouts, limits, and other configuration values.
This eliminates hard-coded values and magic numbers throughout the codebase.

Author: Artemis Team
Date: October 23, 2025
"""

import os
from pathlib import Path

# ==================== PATH CONSTANTS ====================

# Repository root - can be overridden via environment variable
REPO_ROOT = Path(os.environ.get(
    "ARTEMIS_REPO_ROOT",
    Path(__file__).parent.parent.parent.absolute()
))

# Agent directories
AGENTS_DIR = REPO_ROOT / ".agents"
AGILE_DIR = AGENTS_DIR / "agile"

# Kanban board
KANBAN_BOARD_PATH = AGILE_DIR / "kanban_board.json"

# Developer prompts
DEVELOPER_A_PROMPT_PATH = AGENTS_DIR / "developer_a_prompt.md"
DEVELOPER_B_PROMPT_PATH = AGENTS_DIR / "developer_b_prompt.md"

# Test executables
PYTEST_PATH = os.environ.get("ARTEMIS_PYTEST_PATH", "pytest")  # Use pytest from PATH by default

# Output directories
DEFAULT_OUTPUT_DIR = Path("/tmp")
DEFAULT_DEVELOPER_A_DIR = DEFAULT_OUTPUT_DIR / "developer-a"
DEFAULT_DEVELOPER_B_DIR = DEFAULT_OUTPUT_DIR / "developer-b"
DEFAULT_RAG_DB_PATH = DEFAULT_OUTPUT_DIR / "rag_db"
DEFAULT_CHECKPOINT_DIR = DEFAULT_OUTPUT_DIR / "artemis_checkpoints"

# ==================== TIMEOUT CONSTANTS ====================

# Retry settings
DEFAULT_RETRY_INTERVAL_SECONDS = 5
MAX_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_FACTOR = 2

# LLM timeouts
LLM_REQUEST_TIMEOUT_SECONDS = 300  # 5 minutes
LLM_STREAM_TIMEOUT_SECONDS = 600   # 10 minutes

# Developer agent timeouts
DEVELOPER_AGENT_TIMEOUT_SECONDS = 3600  # 1 hour
CODE_REVIEW_TIMEOUT_SECONDS = 1800      # 30 minutes

# Pipeline stage timeouts
STAGE_TIMEOUT_SECONDS = 3600  # 1 hour per stage
FULL_PIPELINE_TIMEOUT_SECONDS = 14400  # 4 hours total

# ==================== LLM CONSTANTS ====================

# Token limits
MAX_LLM_PROMPT_LENGTH = 8000
MAX_LLM_RESPONSE_LENGTH = 4000
MAX_CONTEXT_TOKENS = 100000

# Model defaults
DEFAULT_LLM_PROVIDER = "openai"
DEFAULT_LLM_MODEL = "gpt-5"
DEFAULT_LLM_TEMPERATURE = 0.7
DEFAULT_LLM_MAX_TOKENS = 4000

# Cost limits
DEFAULT_COST_LIMIT_USD = 100.0
COST_WARNING_THRESHOLD_USD = 75.0

# Rate limiting
DEFAULT_REQUESTS_PER_MINUTE = 10
DEFAULT_REQUESTS_PER_HOUR = 500

# ==================== PIPELINE CONSTANTS ====================

# Stage names
STAGE_PROJECT_ANALYSIS = "project_analysis"
STAGE_ARCHITECTURE = "architecture"
STAGE_DEPENDENCIES = "dependencies"
STAGE_DEVELOPMENT = "development"
STAGE_CODE_REVIEW = "code_review"
STAGE_VALIDATION = "validation"
STAGE_INTEGRATION = "integration"
STAGE_TESTING = "testing"

# Pipeline configuration
DEFAULT_PIPELINE_STAGES = [
    STAGE_PROJECT_ANALYSIS,
    STAGE_ARCHITECTURE,
    STAGE_DEPENDENCIES,
    STAGE_DEVELOPMENT,
    STAGE_CODE_REVIEW,
    STAGE_VALIDATION,
    STAGE_INTEGRATION,
    STAGE_TESTING
]

MAX_PARALLEL_DEVELOPERS = 2
DEFAULT_ENABLE_SUPERVISION = True
DEFAULT_ENABLE_CHECKPOINTS = True

# ==================== CODE REVIEW CONSTANTS ====================

# Thresholds
CODE_REVIEW_PASSING_SCORE = 70
CODE_REVIEW_WARNING_SCORE = 50
MAX_CODE_REVIEW_RETRIES = 3

# Review categories
REVIEW_CATEGORY_SECURITY = "security"
REVIEW_CATEGORY_QUALITY = "quality"
REVIEW_CATEGORY_PERFORMANCE = "performance"
REVIEW_CATEGORY_MAINTAINABILITY = "maintainability"

# ==================== KANBAN CONSTANTS ====================

# Columns
KANBAN_COLUMN_BACKLOG = "backlog"
KANBAN_COLUMN_IN_PROGRESS = "in_progress"
KANBAN_COLUMN_REVIEW = "review"
KANBAN_COLUMN_DONE = "done"

# WIP limits
KANBAN_WIP_LIMIT_IN_PROGRESS = 3
KANBAN_WIP_LIMIT_REVIEW = 2

# Priority levels
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

# ==================== RAG CONSTANTS ====================

# ChromaDB configuration
DEFAULT_RAG_COLLECTION_NAME = "artemis_artifacts"
RAG_SIMILARITY_TOP_K = 5
RAG_SIMILARITY_THRESHOLD = 0.7

# Artifact types
ARTIFACT_TYPE_PROJECT_ANALYSIS = "project_analysis"
ARTIFACT_TYPE_ARCHITECTURE = "architecture"
ARTIFACT_TYPE_CODE = "code"
ARTIFACT_TYPE_TEST = "test"
ARTIFACT_TYPE_REVIEW = "code_review"
ARTIFACT_TYPE_ADR = "architecture_decision_record"

# ==================== SUPERVISOR CONSTANTS ====================

# Supervision thresholds
SUPERVISOR_CONFIDENCE_THRESHOLD = 0.8
SUPERVISOR_MAX_INTERVENTIONS = 5

# State machine states
STATE_IDLE = "idle"
STATE_PLANNING = "planning"
STATE_EXECUTING = "executing"
STATE_REVIEWING = "reviewing"
STATE_FAILED = "failed"
STATE_COMPLETED = "completed"

# ==================== FILE PATTERNS ====================

# Source file patterns
PYTHON_FILE_PATTERN = "**/*.py"
JAVASCRIPT_FILE_PATTERN = "**/*.js"
TYPESCRIPT_FILE_PATTERN = "**/*.ts"
TEST_FILE_PATTERN = "**/test_*.py"

# Exclude patterns
EXCLUDE_PATTERNS = [
    "**/__pycache__/**",
    "**/venv/**",
    "**/.venv/**",
    "**/node_modules/**",
    "**/.git/**",
    "**/*.pyc"
]

# ==================== LOGGING CONSTANTS ====================

# Log levels
LOG_LEVEL_DEBUG = "DEBUG"
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"

DEFAULT_LOG_LEVEL = LOG_LEVEL_INFO

# Log formats
LOG_FORMAT_SIMPLE = "%(levelname)s: %(message)s"
LOG_FORMAT_DETAILED = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FORMAT_JSON = "json"

# ==================== NETWORK CONSTANTS ====================

# Memgraph (Knowledge Graph)
DEFAULT_MEMGRAPH_HOST = "localhost"
DEFAULT_MEMGRAPH_PORT = 7687
DEFAULT_MEMGRAPH_LAB_PORT = 7444

# Redis
DEFAULT_REDIS_HOST = "localhost"
DEFAULT_REDIS_PORT = 6379
DEFAULT_REDIS_DB = 0

# ==================== VALIDATION CONSTANTS ====================

# Story points
MIN_STORY_POINTS = 1
MAX_STORY_POINTS = 21

# Code complexity
MAX_CYCLOMATIC_COMPLEXITY = 10
MAX_FUNCTION_LENGTH_LINES = 50
MAX_FILE_LENGTH_LINES = 300
MAX_METHOD_PARAMETERS = 5

# Test requirements
MIN_TEST_COVERAGE_PERCENT = 80
MIN_TESTS_PER_FEATURE = 3

# ==================== HELPER FUNCTIONS ====================

def get_developer_prompt_path(agent_name: str) -> Path:
    """
    Get the prompt file path for a developer agent.

    Args:
        agent_name: Name of the developer agent (e.g., "developer-a")

    Returns:
        Path to the prompt file

    Raises:
        ValueError: If agent_name is not recognized
    """
    if agent_name.lower() in ["developer-a", "dev-a", "a"]:
        return DEVELOPER_A_PROMPT_PATH
    elif agent_name.lower() in ["developer-b", "dev-b", "b"]:
        return DEVELOPER_B_PROMPT_PATH
    else:
        # Default to developer-a for unknown agents
        return DEVELOPER_A_PROMPT_PATH


def get_developer_output_dir(agent_name: str) -> Path:
    """
    Get the output directory for a developer agent.

    Args:
        agent_name: Name of the developer agent

    Returns:
        Path to the output directory
    """
    if agent_name.lower() in ["developer-a", "dev-a", "a"]:
        return DEFAULT_DEVELOPER_A_DIR
    elif agent_name.lower() in ["developer-b", "dev-b", "b"]:
        return DEFAULT_DEVELOPER_B_DIR
    else:
        return DEFAULT_OUTPUT_DIR / agent_name.lower()


def ensure_directory_exists(path: Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Path to the directory

    Returns:
        The path (for chaining)
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_config():
    """
    Validate that all required paths and configurations are accessible.

    Raises:
        FileNotFoundError: If required files are missing
        ValueError: If configuration is invalid
    """
    # Check critical paths exist
    if not REPO_ROOT.exists():
        raise FileNotFoundError(f"Repository root not found: {REPO_ROOT}")

    if not AGILE_DIR.exists():
        raise FileNotFoundError(f"Agile directory not found: {AGILE_DIR}")

    # Developer prompts are optional - will be created if needed
    # Kanban board will be created if it doesn't exist

    # Validate numeric constants
    if MAX_RETRY_ATTEMPTS < 1:
        raise ValueError(f"MAX_RETRY_ATTEMPTS must be >= 1, got {MAX_RETRY_ATTEMPTS}")

    if CODE_REVIEW_PASSING_SCORE < 0 or CODE_REVIEW_PASSING_SCORE > 100:
        raise ValueError(f"CODE_REVIEW_PASSING_SCORE must be 0-100, got {CODE_REVIEW_PASSING_SCORE}")

    return True


# ==================== MODULE INITIALIZATION ====================

if __name__ == "__main__":
    # When run as a script, print all constants
    print("=" * 70)
    print("ARTEMIS CONFIGURATION CONSTANTS")
    print("=" * 70)
    print(f"\nRepository Root: {REPO_ROOT}")
    print(f"Agents Directory: {AGENTS_DIR}")
    print(f"Agile Directory: {AGILE_DIR}")
    print(f"\nKanban Board: {KANBAN_BOARD_PATH}")
    print(f"Developer A Prompt: {DEVELOPER_A_PROMPT_PATH}")
    print(f"Developer B Prompt: {DEVELOPER_B_PROMPT_PATH}")
    print(f"\nPytest Path: {PYTEST_PATH}")
    print(f"RAG Database: {DEFAULT_RAG_DB_PATH}")
    print(f"Checkpoint Dir: {DEFAULT_CHECKPOINT_DIR}")
    print(f"\nMax Retry Attempts: {MAX_RETRY_ATTEMPTS}")
    print(f"Retry Interval: {DEFAULT_RETRY_INTERVAL_SECONDS}s")
    print(f"Code Review Passing Score: {CODE_REVIEW_PASSING_SCORE}")
    print(f"Max Parallel Developers: {MAX_PARALLEL_DEVELOPERS}")

    print("\n" + "=" * 70)
    print("VALIDATION")
    print("=" * 70)

    try:
        validate_config()
        print("✅ Configuration is valid")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        exit(1)
