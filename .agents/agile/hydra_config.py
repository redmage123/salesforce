#!/usr/bin/env python3
"""
Hydra Structured Configurations for Artemis

Type-safe configuration dataclasses that work with Hydra.
Provides IDE autocomplete, validation, and better error messages.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from hydra.core.config_store import ConfigStore


@dataclass
class LLMConfig:
    """
    LLM Provider Configuration

    Controls which LLM provider and model to use for code generation.
    """
    provider: str = "openai"  # openai, anthropic, or mock
    model: Optional[str] = None  # Specific model (e.g., gpt-4o, claude-3-opus)
    api_key: Optional[str] = None  # API key (read from env typically)
    max_tokens_per_request: int = 8000
    temperature: float = 0.7
    cost_limit_usd: Optional[float] = None  # Daily cost limit


@dataclass
class StorageConfig:
    """
    Storage Configuration

    Controls where Artemis stores RAG database, checkpoints, and temporary files.
    Paths are relative to .agents/agile directory unless overridden by env vars.
    """
    rag_db_type: str = "sqlite"  # sqlite or postgres
    rag_db_path: Optional[str] = "db"  # Path for SQLite (relative to .agents/agile)
    chromadb_host: Optional[str] = None  # Host for PostgreSQL-backed ChromaDB
    chromadb_port: Optional[int] = None  # Port for PostgreSQL-backed ChromaDB
    temp_dir: str = "../../.artemis_data/temp"
    checkpoint_dir: str = "../../.artemis_data/checkpoints"
    state_dir: str = "../../.artemis_data/state"


@dataclass
class PipelineConfig:
    """
    Pipeline Execution Configuration

    Controls how the Artemis pipeline executes stages.
    """
    max_parallel_developers: int = 3  # Number of parallel developer agents
    enable_code_review: bool = True  # Enable code review stage
    auto_approve_project_analysis: bool = False  # Auto-approve project analysis
    enable_supervision: bool = True  # Enable supervisor agent
    max_retries: int = 2  # Max retries for failed code reviews
    stages: List[str] = field(default_factory=lambda: [
        "project_analysis",
        "architecture",
        "dependencies",
        "development",
        "code_review",
        "validation",
        "integration",
        "testing"
    ])


@dataclass
class SecurityConfig:
    """
    Security and Compliance Configuration

    Controls security checks and compliance enforcement.
    """
    enforce_gdpr: bool = True  # Enforce GDPR compliance
    enforce_wcag: bool = True  # Enforce WCAG accessibility
    require_security_review: bool = True  # Require security review
    min_code_review_score: int = 80  # Minimum acceptable code review score


@dataclass
class LoggingConfig:
    """
    Logging Configuration

    Controls logging verbosity and output.
    """
    verbose: bool = True  # Enable verbose logging
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR


@dataclass
class ArtemisConfig:
    """
    Complete Artemis Configuration

    Top-level configuration containing all sub-configurations.
    This is the root config object used throughout Artemis.
    """
    # Card ID (required - must be provided via CLI)
    card_id: str = "???"  # ??? means required by Hydra

    # Sub-configurations
    llm: LLMConfig = field(default_factory=LLMConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def register_configs():
    """
    Register all configs with Hydra ConfigStore

    This allows Hydra to provide type-safe config composition.
    """
    cs = ConfigStore.instance()

    # Register main config
    cs.store(name="artemis_config", node=ArtemisConfig)

    # Register config groups
    cs.store(group="llm", name="base_llm", node=LLMConfig)
    cs.store(group="storage", name="base_storage", node=StorageConfig)
    cs.store(group="pipeline", name="base_pipeline", node=PipelineConfig)
    cs.store(group="security", name="base_security", node=SecurityConfig)
    cs.store(group="logging", name="base_logging", node=LoggingConfig)


# Register configs when module is imported
register_configs()
