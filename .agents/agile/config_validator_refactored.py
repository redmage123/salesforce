#!/usr/bin/env python3
"""
Config Validator - Refactored with Design Patterns

Uses:
- Strategy Pattern: Different validation strategies
- Chain of Responsibility: Validation pipeline
- Configuration Object Pattern: Centralized config
- Factory Pattern: Creating validators

Benefits:
- More testable (dependency injection)
- More maintainable (separated concerns)
- More extensible (easy to add validators)
- Less code duplication
"""

import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Protocol
from dataclasses import dataclass, field
from enum import Enum


# ============================================================================
# CONSTANTS (eliminates magic strings)
# ============================================================================

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"


class MessengerType(Enum):
    FILE = "file"
    RABBITMQ = "rabbitmq"
    MOCK = "mock"


class PersistenceType(Enum):
    SQLITE = "sqlite"
    POSTGRES = "postgres"


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# ============================================================================
# CONFIGURATION OBJECT PATTERN
# ============================================================================

@dataclass
class ArtemisConfig:
    """Centralized configuration object - eliminates scattered os.getenv() calls"""

    # LLM Configuration
    llm_provider: str
    openai_api_key: Optional[str]
    anthropic_api_key: Optional[str]

    # Path Configuration
    temp_dir: str
    adr_dir: str
    developer_dir: str
    rag_db_path: str
    persistence_db: str
    message_dir: str
    checkpoint_dir: str
    state_dir: str

    # Resource Configuration
    max_parallel_developers: int
    daily_budget: Optional[float]

    # Service Configuration
    messenger_type: str
    persistence_type: str
    redis_url: Optional[str]
    rabbitmq_url: Optional[str]

    @classmethod
    def from_env(cls) -> 'ArtemisConfig':
        """Create configuration from environment variables"""
        return cls(
            # LLM
            llm_provider=os.getenv("ARTEMIS_LLM_PROVIDER", "openai"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),

            # Paths (relative to .agents/agile directory)
            temp_dir=os.getenv("ARTEMIS_TEMP_DIR", "../../.artemis_data/temp"),
            adr_dir=os.getenv("ARTEMIS_ADR_DIR", "../../.artemis_data/adrs"),
            developer_dir=os.getenv("ARTEMIS_DEVELOPER_DIR", "../../.artemis_data/developer_output"),
            rag_db_path=os.getenv("ARTEMIS_RAG_DB_PATH", "db"),
            persistence_db=os.getenv("ARTEMIS_PERSISTENCE_DB", "../../.artemis_data/artemis_persistence.db"),
            message_dir=os.getenv("ARTEMIS_MESSAGE_DIR", "../../.artemis_data/agent_messages"),
            checkpoint_dir=os.getenv("ARTEMIS_CHECKPOINT_DIR", "../../.artemis_data/checkpoints"),
            state_dir=os.getenv("ARTEMIS_STATE_DIR", "../../.artemis_data/state"),

            # Resources
            max_parallel_developers=int(os.getenv("ARTEMIS_MAX_PARALLEL_DEVELOPERS", "2")),
            daily_budget=float(os.getenv("ARTEMIS_DAILY_BUDGET")) if os.getenv("ARTEMIS_DAILY_BUDGET") else None,

            # Services
            messenger_type=os.getenv("ARTEMIS_MESSENGER_TYPE", "file"),
            persistence_type=os.getenv("ARTEMIS_PERSISTENCE_TYPE", "sqlite"),
            redis_url=os.getenv("REDIS_URL"),
            rabbitmq_url=os.getenv("ARTEMIS_RABBITMQ_URL", "amqp://localhost"),
        )


# ============================================================================
# VALUE OBJECTS
# ============================================================================

@dataclass
class ValidationResult:
    """Result of a validation check"""
    check_name: str
    passed: bool
    message: str
    severity: Severity = Severity.ERROR
    fix_suggestion: Optional[str] = None


@dataclass
class ValidationReport:
    """Complete validation report"""
    overall_status: str  # pass, warning, fail
    total_checks: int
    passed: int
    warnings: int
    errors: int
    results: List[ValidationResult] = field(default_factory=list)


# ============================================================================
# STRATEGY PATTERN - Validation Strategies
# ============================================================================

class ValidationStrategy(ABC):
    """Abstract base class for validation strategies"""

    def __init__(self, config: ArtemisConfig, verbose: bool = True):
        self.config = config
        self.verbose = verbose

    @abstractmethod
    def validate(self) -> List[ValidationResult]:
        """Execute validation and return results"""
        pass

    def _print_result(self, result: ValidationResult):
        """Print validation result if verbose"""
        if self.verbose:
            symbol = "✅" if result.passed else ("⚠️" if result.severity == Severity.WARNING else "❌")
            print(f"{symbol} {result.check_name}: {result.message}")
            if not result.passed and result.fix_suggestion:
                print(f"   💡 Fix: {result.fix_suggestion}")


class LLMProviderValidator(ValidationStrategy):
    """Validates LLM provider configuration"""

    def validate(self) -> List[ValidationResult]:
        results = []

        # Check provider validity
        valid_providers = [p.value for p in LLMProvider]
        if self.config.llm_provider in valid_providers:
            result = ValidationResult(
                check_name="LLM Provider",
                passed=True,
                message=f"Provider set to '{self.config.llm_provider}'",
                severity=Severity.INFO
            )
        else:
            result = ValidationResult(
                check_name="LLM Provider",
                passed=False,
                message=f"Invalid provider '{self.config.llm_provider}'",
                fix_suggestion=f"Set ARTEMIS_LLM_PROVIDER to one of: {', '.join(valid_providers)}"
            )

        self._print_result(result)
        results.append(result)

        # Check API keys
        if self.config.llm_provider == LLMProvider.OPENAI.value:
            results.extend(self._validate_openai_key())
        elif self.config.llm_provider == LLMProvider.ANTHROPIC.value:
            results.extend(self._validate_anthropic_key())
        elif self.config.llm_provider == LLMProvider.MOCK.value:
            result = ValidationResult(
                check_name="Mock LLM",
                passed=True,
                message="Using mock LLM (no API key needed)",
                severity=Severity.WARNING
            )
            self._print_result(result)
            results.append(result)

        return results

    def _validate_openai_key(self) -> List[ValidationResult]:
        """Validate OpenAI API key"""
        if not self.config.openai_api_key:
            result = ValidationResult(
                check_name="OpenAI API Key",
                passed=False,
                message="OPENAI_API_KEY not set",
                fix_suggestion="export OPENAI_API_KEY=sk-..."
            )
        elif not self.config.openai_api_key.startswith("sk-"):
            result = ValidationResult(
                check_name="OpenAI API Key",
                passed=False,
                message="API key has invalid format",
                fix_suggestion="OpenAI keys should start with 'sk-'"
            )
        else:
            result = ValidationResult(
                check_name="OpenAI API Key",
                passed=True,
                message="API key present and valid format",
                severity=Severity.INFO
            )

        self._print_result(result)
        return [result]

    def _validate_anthropic_key(self) -> List[ValidationResult]:
        """Validate Anthropic API key"""
        if not self.config.anthropic_api_key:
            result = ValidationResult(
                check_name="Anthropic API Key",
                passed=False,
                message="ANTHROPIC_API_KEY not set",
                fix_suggestion="export ANTHROPIC_API_KEY=..."
            )
        else:
            result = ValidationResult(
                check_name="Anthropic API Key",
                passed=True,
                message="API key present",
                severity=Severity.INFO
            )

        self._print_result(result)
        return [result]


class PathValidator(ValidationStrategy):
    """Validates file system paths"""

    def validate(self) -> List[ValidationResult]:
        results = []

        paths_to_check = [
            (self.config.temp_dir, "Temp directory"),
            (self.config.adr_dir, "ADR directory"),
            (f"{self.config.developer_dir}/developer-a", "Developer A output"),
            (f"{self.config.developer_dir}/developer-b", "Developer B output"),
        ]

        for path_str, description in paths_to_check:
            result = self._validate_path(path_str, description)
            self._print_result(result)
            results.append(result)

        return results

    def _validate_path(self, path_str: str, description: str) -> ValidationResult:
        """Validate a single path"""
        path = Path(path_str)

        try:
            path.mkdir(parents=True, exist_ok=True)

            # Check writable
            test_file = path / ".test_write"
            test_file.write_text("test")
            test_file.unlink()

            return ValidationResult(
                check_name=f"Path: {description}",
                passed=True,
                message=f"{path} exists and writable",
                severity=Severity.INFO
            )
        except Exception as e:
            return ValidationResult(
                check_name=f"Path: {description}",
                passed=False,
                message=f"{path} not writable: {e}",
                fix_suggestion=f"Ensure {path} exists and has write permissions"
            )


class DatabaseValidator(ValidationStrategy):
    """Validates database access"""

    def validate(self) -> List[ValidationResult]:
        results = []

        if self.config.persistence_type == PersistenceType.SQLITE.value:
            result = self._validate_sqlite()
        elif self.config.persistence_type == PersistenceType.POSTGRES.value:
            result = self._validate_postgres()
        else:
            result = ValidationResult(
                check_name="Database",
                passed=False,
                message=f"Unknown persistence type: {self.config.persistence_type}"
            )

        self._print_result(result)
        results.append(result)
        return results

    def _validate_sqlite(self) -> ValidationResult:
        """Validate SQLite database"""
        try:
            import sqlite3
            db_file = Path(self.config.persistence_db)
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()

            return ValidationResult(
                check_name="SQLite Database",
                passed=True,
                message=f"Database accessible at {self.config.persistence_db}",
                severity=Severity.INFO
            )
        except Exception as e:
            return ValidationResult(
                check_name="SQLite Database",
                passed=False,
                message=f"Cannot access database: {e}",
                fix_suggestion=f"Check permissions on {self.config.persistence_db}"
            )

    def _validate_postgres(self) -> ValidationResult:
        """Validate PostgreSQL database"""
        return ValidationResult(
            check_name="PostgreSQL Database",
            passed=False,
            message="PostgreSQL persistence not yet implemented",
            severity=Severity.WARNING,
            fix_suggestion="Use ARTEMIS_PERSISTENCE_TYPE=sqlite for now"
        )


class MessengerValidator(ValidationStrategy):
    """Validates messenger backend"""

    def validate(self) -> List[ValidationResult]:
        results = []

        if self.config.messenger_type == MessengerType.FILE.value:
            result = self._validate_file_messenger()
        elif self.config.messenger_type == MessengerType.RABBITMQ.value:
            result = self._validate_rabbitmq()
        elif self.config.messenger_type == MessengerType.MOCK.value:
            result = ValidationResult(
                check_name="Mock Messenger",
                passed=True,
                message="Using mock messenger (testing mode)",
                severity=Severity.WARNING
            )
        else:
            result = ValidationResult(
                check_name="Messenger",
                passed=False,
                message=f"Unknown messenger type: {self.config.messenger_type}"
            )

        self._print_result(result)
        results.append(result)
        return results

    def _validate_file_messenger(self) -> ValidationResult:
        """Validate file-based messenger"""
        try:
            Path(self.config.message_dir).mkdir(parents=True, exist_ok=True)
            return ValidationResult(
                check_name="File Messenger",
                passed=True,
                message=f"Message directory accessible: {self.config.message_dir}",
                severity=Severity.INFO
            )
        except Exception as e:
            return ValidationResult(
                check_name="File Messenger",
                passed=False,
                message=f"Cannot create message directory: {e}",
                fix_suggestion=f"Ensure {self.config.message_dir} is writable"
            )

    def _validate_rabbitmq(self) -> ValidationResult:
        """Validate RabbitMQ connection"""
        try:
            import pika
            params = pika.URLParameters(self.config.rabbitmq_url)
            params.connection_attempts = 1
            params.retry_delay = 1
            conn = pika.BlockingConnection(params)
            conn.close()

            return ValidationResult(
                check_name="RabbitMQ Messenger",
                passed=True,
                message=f"Connected to RabbitMQ at {self.config.rabbitmq_url}",
                severity=Severity.INFO
            )
        except ImportError:
            return ValidationResult(
                check_name="RabbitMQ Messenger",
                passed=False,
                message="pika library not installed",
                fix_suggestion="pip install pika"
            )
        except Exception as e:
            return ValidationResult(
                check_name="RabbitMQ Messenger",
                passed=False,
                message=f"Cannot connect to RabbitMQ: {e}",
                fix_suggestion="Ensure RabbitMQ is running: docker run -d -p 5672:5672 rabbitmq"
            )


class RAGDatabaseValidator(ValidationStrategy):
    """Validates RAG database (ChromaDB)"""

    def validate(self) -> List[ValidationResult]:
        results = []

        try:
            import chromadb
            Path(self.config.rag_db_path).mkdir(parents=True, exist_ok=True)

            result = ValidationResult(
                check_name="RAG Database (ChromaDB)",
                passed=True,
                message=f"ChromaDB accessible at {self.config.rag_db_path}",
                severity=Severity.INFO
            )
        except ImportError:
            result = ValidationResult(
                check_name="RAG Database (ChromaDB)",
                passed=False,
                message="chromadb library not installed",
                severity=Severity.WARNING,
                fix_suggestion="pip install chromadb (optional but recommended)"
            )
        except Exception as e:
            result = ValidationResult(
                check_name="RAG Database (ChromaDB)",
                passed=False,
                message=f"Cannot access RAG database: {e}",
                severity=Severity.WARNING,
                fix_suggestion=f"Check permissions on {self.config.rag_db_path}"
            )

        self._print_result(result)
        results.append(result)
        return results


class ResourceLimitValidator(ValidationStrategy):
    """Validates resource limits"""

    def validate(self) -> List[ValidationResult]:
        results = []

        # Check parallel developers
        if 1 <= self.config.max_parallel_developers <= 5:
            result = ValidationResult(
                check_name="Parallel Developers",
                passed=True,
                message=f"Max parallel developers: {self.config.max_parallel_developers}",
                severity=Severity.INFO
            )
        else:
            result = ValidationResult(
                check_name="Parallel Developers",
                passed=False,
                message=f"Invalid max parallel developers: {self.config.max_parallel_developers}",
                severity=Severity.WARNING,
                fix_suggestion="Set ARTEMIS_MAX_PARALLEL_DEVELOPERS between 1 and 5"
            )

        self._print_result(result)
        results.append(result)

        # Check budget if set
        if self.config.daily_budget is not None:
            if self.config.daily_budget > 0:
                result = ValidationResult(
                    check_name="Daily Budget",
                    passed=True,
                    message=f"Daily budget: ${self.config.daily_budget:.2f}",
                    severity=Severity.INFO
                )
            else:
                result = ValidationResult(
                    check_name="Daily Budget",
                    passed=False,
                    message="Daily budget must be positive",
                    severity=Severity.WARNING
                )

            self._print_result(result)
            results.append(result)

        return results


class OptionalServicesValidator(ValidationStrategy):
    """Validates optional services like Redis"""

    def validate(self) -> List[ValidationResult]:
        results = []

        if self.config.redis_url:
            result = self._validate_redis()
            self._print_result(result)
            results.append(result)

        return results

    def _validate_redis(self) -> ValidationResult:
        """Validate Redis connection"""
        try:
            import redis
            client = redis.from_url(self.config.redis_url, socket_connect_timeout=2)
            client.ping()
            return ValidationResult(
                check_name="Redis (Optional)",
                passed=True,
                message=f"Connected to Redis at {self.config.redis_url}",
                severity=Severity.INFO
            )
        except ImportError:
            return ValidationResult(
                check_name="Redis (Optional)",
                passed=False,
                message="redis library not installed",
                severity=Severity.WARNING,
                fix_suggestion="pip install redis (optional)"
            )
        except Exception as e:
            return ValidationResult(
                check_name="Redis (Optional)",
                passed=False,
                message=f"Cannot connect to Redis: {e}",
                severity=Severity.WARNING,
                fix_suggestion="Ensure Redis is running or unset REDIS_URL"
            )


# ============================================================================
# FACTORY PATTERN - Validator Factory
# ============================================================================

class ValidatorFactory:
    """Factory for creating validators"""

    @staticmethod
    def create_all_validators(config: ArtemisConfig, verbose: bool = True) -> List[ValidationStrategy]:
        """Create all standard validators"""
        return [
            LLMProviderValidator(config, verbose),
            PathValidator(config, verbose),
            DatabaseValidator(config, verbose),
            MessengerValidator(config, verbose),
            RAGDatabaseValidator(config, verbose),
            ResourceLimitValidator(config, verbose),
            OptionalServicesValidator(config, verbose),
        ]


# ============================================================================
# CHAIN OF RESPONSIBILITY - Validation Pipeline
# ============================================================================

class ValidationPipeline:
    """Chain of Responsibility for validation"""

    def __init__(self, config: ArtemisConfig, verbose: bool = True):
        self.config = config
        self.verbose = verbose
        self.validators: List[ValidationStrategy] = []

    def add_validator(self, validator: ValidationStrategy) -> 'ValidationPipeline':
        """Add a validator to the chain"""
        self.validators.append(validator)
        return self

    def add_all_standard_validators(self) -> 'ValidationPipeline':
        """Add all standard validators"""
        self.validators = ValidatorFactory.create_all_validators(self.config, self.verbose)
        return self

    def validate_all(self) -> ValidationReport:
        """Execute all validators and generate report"""
        if self.verbose:
            print("\n" + "=" * 70)
            print("🔍 ARTEMIS CONFIGURATION VALIDATION")
            print("=" * 70 + "\n")

        all_results = []
        for validator in self.validators:
            results = validator.validate()
            all_results.extend(results)

        report = self._generate_report(all_results)

        if self.verbose:
            self._print_report(report)

        return report

    def _generate_report(self, results: List[ValidationResult]) -> ValidationReport:
        """Generate validation report from results"""
        # Performance: Single-pass categorization O(n) vs O(3n)
        errors, warnings, passed = [], [], []
        for r in results:
            if r.passed:
                passed.append(r)
            elif r.severity == Severity.ERROR:
                errors.append(r)
            elif r.severity == Severity.WARNING:
                warnings.append(r)

        if errors:
            overall_status = "fail"
        elif warnings:
            overall_status = "warning"
        else:
            overall_status = "pass"

        return ValidationReport(
            overall_status=overall_status,
            total_checks=len(results),
            passed=len(passed),
            warnings=len(warnings),
            errors=len(errors),
            results=results
        )

    def _print_report(self, report: ValidationReport):
        """Print validation report"""
        print("\n" + "=" * 70)
        print("📊 VALIDATION SUMMARY")
        print("=" * 70)

        print(f"\nTotal checks: {report.total_checks}")
        print(f"  ✅ Passed: {report.passed}")
        if report.warnings > 0:
            print(f"  ⚠️  Warnings: {report.warnings}")
        if report.errors > 0:
            print(f"  ❌ Errors: {report.errors}")

        if report.overall_status == "pass":
            print("\n🎉 All validation checks passed!")
            print("Artemis is ready to run.")
        elif report.overall_status == "warning":
            print("\n⚠️  Validation completed with warnings")
            print("Artemis can run but some features may not work.")
        else:
            print("\n❌ Validation failed!")
            print("Fix errors before running Artemis.")

        print("\n" + "=" * 70 + "\n")


# ============================================================================
# FACADE - Simplified Interface
# ============================================================================

class ConfigValidator:
    """
    Facade providing simplified interface (backward compatible)

    Usage:
        validator = ConfigValidator(verbose=True)
        report = validator.validate_all()
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.config = ArtemisConfig.from_env()
        self.pipeline = ValidationPipeline(self.config, verbose)
        self.pipeline.add_all_standard_validators()

    def validate_all(self) -> ValidationReport:
        """Run all validation checks"""
        return self.pipeline.validate_all()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def validate_config_or_exit(verbose: bool = True) -> ValidationReport:
    """
    Validate configuration or exit (fail-fast)

    Args:
        verbose: Print validation progress

    Returns:
        ValidationReport if passed, exits otherwise
    """
    validator = ConfigValidator(verbose=verbose)
    report = validator.validate_all()

    if report.overall_status == "fail":
        print("\n💥 STARTUP ABORTED: Fix configuration errors above")
        sys.exit(1)

    return report


if __name__ == "__main__":
    """Run validation"""
    validator = ConfigValidator(verbose=True)
    report = validator.validate_all()

    # Exit with appropriate code
    if report.overall_status == "fail":
        sys.exit(1)
    elif report.overall_status == "warning":
        sys.exit(2)
    else:
        sys.exit(0)
