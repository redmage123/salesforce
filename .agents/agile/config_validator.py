#!/usr/bin/env python3
"""
Config Validator - Fail-Fast Startup Validation

Validates all configuration at startup to catch errors early:
- LLM API keys present and valid
- Database connections work
- File paths exist and writable
- Messenger backend available
- Resource limits reasonable
- All required services running

Implements "fail-fast" principle: better to fail at startup than mid-pipeline
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of a validation check"""
    check_name: str
    passed: bool
    message: str
    severity: str = "error"  # error, warning, info
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


class ConfigValidator:
    """
    Validates Artemis configuration at startup

    Single Responsibility: Validate all prerequisites before pipeline runs
    """

    def __init__(self, verbose: bool = True):
        """
        Initialize validator

        Args:
            verbose: Print validation progress
        """
        self.verbose = verbose
        self.results: List[ValidationResult] = []

    def validate_all(self) -> ValidationReport:
        """
        Run all validation checks

        Returns:
            ValidationReport with all results
        """
        if self.verbose:
            print("\n" + "=" * 70)
            print("🔍 ARTEMIS CONFIGURATION VALIDATION")
            print("=" * 70 + "\n")

        # Run all checks
        self._check_llm_provider()
        self._check_llm_api_keys()
        self._check_file_paths()
        self._check_database_access()
        self._check_messenger_backend()
        self._check_rag_database()
        self._check_resource_limits()
        self._check_optional_services()

        # Generate report
        report = self._generate_report()

        if self.verbose:
            self._print_report(report)

        return report

    def _add_result(self, check_name: str, passed: bool, message: str,
                    severity: str = "error", fix_suggestion: Optional[str] = None):
        """Add validation result"""
        result = ValidationResult(
            check_name=check_name,
            passed=passed,
            message=message,
            severity=severity,
            fix_suggestion=fix_suggestion
        )
        self.results.append(result)

        if self.verbose:
            symbol = "✅" if passed else ("⚠️" if severity == "warning" else "❌")
            print(f"{symbol} {check_name}: {message}")
            if not passed and fix_suggestion:
                print(f"   💡 Fix: {fix_suggestion}")

    def _check_llm_provider(self):
        """Check LLM provider configuration"""
        provider = os.getenv("ARTEMIS_LLM_PROVIDER", "openai")

        valid_providers = ["openai", "anthropic", "mock"]
        if provider in valid_providers:
            self._add_result(
                "LLM Provider",
                True,
                f"Provider set to '{provider}'"
            )
        else:
            self._add_result(
                "LLM Provider",
                False,
                f"Invalid provider '{provider}'",
                fix_suggestion=f"Set ARTEMIS_LLM_PROVIDER to one of: {', '.join(valid_providers)}"
            )

    def _check_llm_api_keys(self):
        """Check LLM API keys are present"""
        provider = os.getenv("ARTEMIS_LLM_PROVIDER", "openai")

        # Define provider validation configurations
        provider_configs = {
            "openai": {
                "env_var": "OPENAI_API_KEY",
                "name": "OpenAI API Key",
                "validator": lambda key: key.startswith("sk-"),
                "error_msg": "API key has invalid format",
                "fix_suggestion": "export OPENAI_API_KEY=sk-...",
                "validation_msg": "OpenAI keys should start with 'sk-'"
            },
            "anthropic": {
                "env_var": "ANTHROPIC_API_KEY",
                "name": "Anthropic API Key",
                "validator": None,
                "fix_suggestion": "export ANTHROPIC_API_KEY=..."
            },
            "mock": {
                "env_var": None,
                "name": "Mock LLM",
                "is_mock": True
            }
        }

        config = provider_configs.get(provider)
        if not config:
            self._add_result(
                "LLM Provider",
                False,
                f"Unknown provider: {provider}",
                fix_suggestion="Set ARTEMIS_LLM_PROVIDER to 'openai', 'anthropic', or 'mock'"
            )
            return

        # Handle mock provider
        if config.get("is_mock"):
            self._add_result(
                config["name"],
                True,
                "Using mock LLM (no API key needed)",
                severity="warning"
            )
            return

        # Check API key for real providers
        api_key = os.getenv(config["env_var"])
        if api_key:
            # Validate format if validator provided
            if config.get("validator") and not config["validator"](api_key):
                self._add_result(
                    config["name"],
                    False,
                    config["error_msg"],
                    fix_suggestion=config.get("validation_msg", config["fix_suggestion"])
                )
            else:
                self._add_result(
                    config["name"],
                    True,
                    "API key present" + (" and valid format" if config.get("validator") else "")
                )
        else:
            self._add_result(
                config["name"],
                False,
                f"{config['env_var']} not set",
                fix_suggestion=config["fix_suggestion"]
            )

    def _check_file_paths(self):
        """Check important file paths exist and are writable"""
        # Get paths from environment variables (relative to .agents/agile directory)
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))

        temp_dir = os.getenv("ARTEMIS_TEMP_DIR", "../../.artemis_data/temp")
        adr_dir = os.getenv("ARTEMIS_ADR_DIR", "../../.artemis_data/adrs")
        developer_dir = os.getenv("ARTEMIS_DEVELOPER_DIR", "../../.artemis_data/developer_output")

        # Convert relative paths to absolute
        if not os.path.isabs(temp_dir):
            temp_dir = os.path.join(script_dir, temp_dir)
        if not os.path.isabs(adr_dir):
            adr_dir = os.path.join(script_dir, adr_dir)
        if not os.path.isabs(developer_dir):
            developer_dir = os.path.join(script_dir, developer_dir)

        paths_to_check = [
            (temp_dir, "Temp directory"),
            (adr_dir, "ADR directory"),
            (f"{developer_dir}/developer-a", "Developer A output"),
            (f"{developer_dir}/developer-b", "Developer B output"),
        ]

        for path_str, description in paths_to_check:
            path = Path(path_str)

            # Check exists or can be created
            try:
                path.mkdir(parents=True, exist_ok=True)

                # Check writable
                test_file = path / ".test_write"
                test_file.write_text("test")
                test_file.unlink()

                self._add_result(
                    f"Path: {description}",
                    True,
                    f"{path} exists and writable",
                    severity="info"
                )
            except Exception as e:
                self._add_result(
                    f"Path: {description}",
                    False,
                    f"{path} not writable: {e}",
                    fix_suggestion=f"Ensure {path} exists and has write permissions"
                )

    def _check_database_access(self):
        """Check database/persistence access"""
        persistence_type = os.getenv("ARTEMIS_PERSISTENCE_TYPE", "sqlite")

        if persistence_type == "sqlite":
            db_path = os.getenv("ARTEMIS_PERSISTENCE_DB", "../../.artemis_data/artemis_persistence.db")
            # Convert relative path to absolute
            if not os.path.isabs(db_path):
                script_dir = os.path.dirname(os.path.abspath(__file__))
                db_path = os.path.join(script_dir, db_path)
            db_file = Path(db_path)

            try:
                # Try to create/access database
                import sqlite3
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                conn.close()

                self._add_result(
                    "SQLite Database",
                    True,
                    f"Database accessible at {db_path}"
                )
            except Exception as e:
                self._add_result(
                    "SQLite Database",
                    False,
                    f"Cannot access database: {e}",
                    fix_suggestion=f"Check permissions on {db_path}"
                )

        elif persistence_type == "postgres":
            # Check PostgreSQL connection (future implementation)
            self._add_result(
                "PostgreSQL Database",
                False,
                "PostgreSQL persistence not yet implemented",
                severity="warning",
                fix_suggestion="Use ARTEMIS_PERSISTENCE_TYPE=sqlite for now"
            )

    def _check_messenger_backend(self):
        """Check messenger backend availability"""
        messenger_type = os.getenv("ARTEMIS_MESSENGER_TYPE", "file")

        if messenger_type == "file":
            message_dir = os.getenv("ARTEMIS_MESSAGE_DIR", "/tmp/agent_messages")
            try:
                Path(message_dir).mkdir(parents=True, exist_ok=True)
                self._add_result(
                    "File Messenger",
                    True,
                    f"Message directory accessible: {message_dir}"
                )
            except Exception as e:
                self._add_result(
                    "File Messenger",
                    False,
                    f"Cannot create message directory: {e}",
                    fix_suggestion=f"Ensure {message_dir} is writable"
                )

        elif messenger_type == "rabbitmq":
            # Check RabbitMQ connection
            try:
                import pika
                rabbitmq_url = os.getenv("ARTEMIS_RABBITMQ_URL", "amqp://localhost")
                # Try to connect (with short timeout)
                params = pika.URLParameters(rabbitmq_url)
                params.connection_attempts = 1
                params.retry_delay = 1
                conn = pika.BlockingConnection(params)
                conn.close()

                self._add_result(
                    "RabbitMQ Messenger",
                    True,
                    f"Connected to RabbitMQ at {rabbitmq_url}"
                )
            except ImportError:
                self._add_result(
                    "RabbitMQ Messenger",
                    False,
                    "pika library not installed",
                    fix_suggestion="pip install pika"
                )
            except Exception as e:
                self._add_result(
                    "RabbitMQ Messenger",
                    False,
                    f"Cannot connect to RabbitMQ: {e}",
                    fix_suggestion="Ensure RabbitMQ is running: docker run -d -p 5672:5672 rabbitmq"
                )

        elif messenger_type == "mock":
            self._add_result(
                "Mock Messenger",
                True,
                "Using mock messenger (testing mode)",
                severity="warning"
            )

    def _check_rag_database(self):
        """Check RAG database (ChromaDB) access"""
        # Get RAG DB path from env or use default relative to script directory
        rag_db_path = os.getenv("ARTEMIS_RAG_DB_PATH", "db")
        if not os.path.isabs(rag_db_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            rag_db_path = os.path.join(script_dir, rag_db_path)

        try:
            # Try to import chromadb
            import chromadb

            # Try to create/access database
            Path(rag_db_path).mkdir(parents=True, exist_ok=True)

            self._add_result(
                "RAG Database (ChromaDB)",
                True,
                f"ChromaDB accessible at {rag_db_path}"
            )
        except ImportError:
            self._add_result(
                "RAG Database (ChromaDB)",
                False,
                "chromadb library not installed",
                severity="warning",
                fix_suggestion="pip install chromadb (optional but recommended)"
            )
        except Exception as e:
            self._add_result(
                "RAG Database (ChromaDB)",
                False,
                f"Cannot access RAG database: {e}",
                severity="warning",
                fix_suggestion=f"Check permissions on {rag_db_path}"
            )

    def _check_resource_limits(self):
        """Check resource limits are reasonable"""
        # Check max parallel developers
        max_devs = int(os.getenv("ARTEMIS_MAX_PARALLEL_DEVELOPERS", "2"))
        if 1 <= max_devs <= 5:
            self._add_result(
                "Parallel Developers",
                True,
                f"Max parallel developers: {max_devs}",
                severity="info"
            )
        else:
            self._add_result(
                "Parallel Developers",
                False,
                f"Invalid max parallel developers: {max_devs}",
                severity="warning",
                fix_suggestion="Set ARTEMIS_MAX_PARALLEL_DEVELOPERS between 1 and 5"
            )

        # Check budgets if set
        daily_budget = os.getenv("ARTEMIS_DAILY_BUDGET")
        if daily_budget:
            try:
                budget = float(daily_budget)
                if budget > 0:
                    self._add_result(
                        "Daily Budget",
                        True,
                        f"Daily budget: ${budget:.2f}",
                        severity="info"
                    )
                else:
                    self._add_result(
                        "Daily Budget",
                        False,
                        "Daily budget must be positive",
                        severity="warning"
                    )
            except ValueError:
                self._add_result(
                    "Daily Budget",
                    False,
                    f"Invalid daily budget: {daily_budget}",
                    severity="warning",
                    fix_suggestion="Set ARTEMIS_DAILY_BUDGET to a number (e.g., 10.00)"
                )

    def _check_optional_services(self):
        """Check optional services"""
        # Check Redis (optional)
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                import redis
                client = redis.from_url(redis_url, socket_connect_timeout=2)
                client.ping()
                self._add_result(
                    "Redis (Optional)",
                    True,
                    f"Connected to Redis at {redis_url}",
                    severity="info"
                )
            except ImportError:
                self._add_result(
                    "Redis (Optional)",
                    False,
                    "redis library not installed",
                    severity="warning",
                    fix_suggestion="pip install redis (optional)"
                )
            except Exception as e:
                self._add_result(
                    "Redis (Optional)",
                    False,
                    f"Cannot connect to Redis: {e}",
                    severity="warning",
                    fix_suggestion="Ensure Redis is running or unset REDIS_URL"
                )

    def _generate_report(self) -> ValidationReport:
        """Generate validation report"""
        errors = [r for r in self.results if not r.passed and r.severity == "error"]
        warnings = [r for r in self.results if not r.passed and r.severity == "warning"]
        passed = [r for r in self.results if r.passed]

        # Determine overall status
        if errors:
            overall_status = "fail"
        elif warnings:
            overall_status = "warning"
        else:
            overall_status = "pass"

        return ValidationReport(
            overall_status=overall_status,
            total_checks=len(self.results),
            passed=len(passed),
            warnings=len(warnings),
            errors=len(errors),
            results=self.results
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


def validate_config_or_exit(verbose: bool = True) -> ValidationReport:
    """
    Validate configuration or exit

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
