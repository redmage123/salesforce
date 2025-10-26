#!/usr/bin/env python3
"""
Configuration Agent - Centralized Environment Configuration Management

Reads and validates all environment variables needed by the Artemis pipeline,
especially API keys for LLM providers, database paths, and service endpoints.

SOLID Principles:
- Single Responsibility: Only manages configuration reading and validation
- Open/Closed: Easy to add new configuration keys
- Dependency Inversion: Other components depend on this abstraction
"""

import os
import tempfile
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
from debug_mixin import DebugMixin

# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)  # Load .env file and override system environment
except ImportError:
    pass  # dotenv not installed, will use system environment variables only


@dataclass
class ConfigValidationResult:
    """Result of configuration validation"""
    is_valid: bool
    missing_keys: List[str]
    invalid_keys: List[str]
    warnings: List[str]
    config_summary: Dict[str, Any]


class ConfigurationAgent(DebugMixin):
    """
    Configuration Agent - Manages all environment configuration

    Responsibilities:
    1. Read environment variables
    2. Validate required keys are present
    3. Provide default values
    4. Mask sensitive values in logs
    5. Generate configuration reports
    """

    # Configuration schema with defaults and requirements
    CONFIG_SCHEMA = {
        # LLM Provider Configuration
        'ARTEMIS_LLM_PROVIDER': {
            'default': 'openai',
            'required': False,
            'sensitive': False,
            'description': 'Primary LLM provider (openai/anthropic)',
            'valid_values': ['openai', 'anthropic']
        },
        'ARTEMIS_LLM_MODEL': {
            'default': None,  # Provider-specific default
            'required': False,
            'sensitive': False,
            'description': 'Specific LLM model to use'
        },

        # API Keys
        'OPENAI_API_KEY': {
            'default': None,
            'required': False,  # Required only if provider is openai
            'sensitive': True,
            'description': 'OpenAI API key'
        },
        'ANTHROPIC_API_KEY': {
            'default': None,
            'required': False,  # Required only if provider is anthropic
            'sensitive': True,
            'description': 'Anthropic API key'
        },

        # Database and Storage
        'ARTEMIS_RAG_DB_PATH': {
            'default': 'db',  # Relative to .agents/agile directory
            'required': False,
            'sensitive': False,
            'description': 'Path to RAG database (ChromaDB, relative to .agents/agile)'
        },
        'ARTEMIS_TEMP_DIR': {
            'default': tempfile.gettempdir(),
            'required': False,
            'sensitive': False,
            'description': 'Temporary directory for pipeline artifacts'
        },

        # Pipeline Configuration
        'ARTEMIS_MAX_PARALLEL_DEVELOPERS': {
            'default': '3',
            'required': False,
            'sensitive': False,
            'description': 'Maximum number of parallel developers'
        },
        'ARTEMIS_ENABLE_CODE_REVIEW': {
            'default': 'true',
            'required': False,
            'sensitive': False,
            'description': 'Enable code review stage (true/false)'
        },
        'ARTEMIS_AUTO_APPROVE_PROJECT_ANALYSIS': {
            'default': 'true',  # Default to auto-approve for non-interactive use
            'required': False,
            'sensitive': False,
            'description': 'Auto-approve project analysis suggestions (true/false)'
        },

        # Logging and Monitoring
        'ARTEMIS_VERBOSE': {
            'default': 'true',
            'required': False,
            'sensitive': False,
            'description': 'Enable verbose logging (true/false)'
        },
        'ARTEMIS_LOG_LEVEL': {
            'default': 'INFO',
            'required': False,
            'sensitive': False,
            'description': 'Log level (DEBUG/INFO/WARNING/ERROR)',
            'valid_values': ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        },

        # Security and Compliance
        'ARTEMIS_ENFORCE_GDPR': {
            'default': 'true',
            'required': False,
            'sensitive': False,
            'description': 'Enforce GDPR compliance checks'
        },
        'ARTEMIS_ENFORCE_WCAG': {
            'default': 'true',
            'required': False,
            'sensitive': False,
            'description': 'Enforce WCAG accessibility checks'
        },

        # Cost Controls
        'ARTEMIS_MAX_TOKENS_PER_REQUEST': {
            'default': '8000',
            'required': False,
            'sensitive': False,
            'description': 'Maximum tokens per LLM request'
        },
        'ARTEMIS_COST_LIMIT_USD': {
            'default': None,
            'required': False,
            'sensitive': False,
            'description': 'Maximum cost limit in USD (optional)'
        }
    }

    def __init__(self, verbose: bool = True):
        """
        Initialize Configuration Agent

        Args:
            verbose: Enable verbose logging
        """
        DebugMixin.__init__(self, component_name="config")
        self.verbose = verbose
        self.config: Dict[str, Any] = {}
        self.load_configuration()
        self.debug_log("ConfigurationAgent initialized", verbose=verbose)

    def load_configuration(self) -> None:
        """Load all configuration from environment variables"""
        self.debug_trace("load_configuration", schema_keys=len(self.CONFIG_SCHEMA))
        for key, schema in self.CONFIG_SCHEMA.items():
            # Read from environment or use default
            value = os.getenv(key, schema['default'])

            # Convert boolean strings
            if value in ('true', 'True', 'TRUE'):
                value = True
            elif value in ('false', 'False', 'FALSE'):
                value = False

            self.config[key] = value

        if self.verbose:
            print("✅ Configuration loaded from environment")

    def validate_configuration(self, require_llm_key: bool = True) -> ConfigValidationResult:
        """
        Validate current configuration

        Args:
            require_llm_key: Require LLM API key based on provider

        Returns:
            ConfigValidationResult with validation status
        """
        self.debug_trace("validate_configuration", require_llm_key=require_llm_key)
        missing_keys = []
        invalid_keys = []
        warnings = []

        # Check provider-specific requirements
        provider = self.get('ARTEMIS_LLM_PROVIDER', 'openai')

        if require_llm_key:
            if provider == 'openai':
                if not self.get('OPENAI_API_KEY'):
                    missing_keys.append('OPENAI_API_KEY')
            elif provider == 'anthropic':
                if not self.get('ANTHROPIC_API_KEY'):
                    missing_keys.append('ANTHROPIC_API_KEY')

        # Validate valid_values constraints
        for key, schema in self.CONFIG_SCHEMA.items():
            value = self.config.get(key)
            if value and 'valid_values' in schema:
                if value not in schema['valid_values']:
                    invalid_keys.append(f"{key}={value} (valid: {schema['valid_values']})")

        # Check for warnings
        if self.get('ARTEMIS_COST_LIMIT_USD'):
            try:
                limit = float(self.get('ARTEMIS_COST_LIMIT_USD'))
                if limit < 1.0:
                    warnings.append(f"Cost limit ${limit:.2f} may be too low for pipeline execution")
            except ValueError:
                invalid_keys.append('ARTEMIS_COST_LIMIT_USD (must be numeric)')

        # Generate summary
        config_summary = {
            'provider': provider,
            'model': self.get('ARTEMIS_LLM_MODEL', 'default'),
            'rag_db_path': self.get('ARTEMIS_RAG_DB_PATH'),
            'code_review_enabled': self.get('ARTEMIS_ENABLE_CODE_REVIEW', True),
            'max_parallel_developers': self.get('ARTEMIS_MAX_PARALLEL_DEVELOPERS', 3),
            'has_openai_key': bool(self.get('OPENAI_API_KEY')),
            'has_anthropic_key': bool(self.get('ANTHROPIC_API_KEY'))
        }

        is_valid = len(missing_keys) == 0 and len(invalid_keys) == 0

        self.debug_if_enabled("validation_results", "Configuration validation completed",
                             is_valid=is_valid, missing=len(missing_keys),
                             invalid=len(invalid_keys), warnings=len(warnings))

        return ConfigValidationResult(
            is_valid=is_valid,
            missing_keys=missing_keys,
            invalid_keys=invalid_keys,
            warnings=warnings,
            config_summary=config_summary
        )

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return self.config.get(key, default)

    def get_masked(self, key: str) -> str:
        """
        Get configuration value with sensitive data masked

        Args:
            key: Configuration key

        Returns:
            Masked value (e.g., "sk-XYZ...ABC")
        """
        value = self.config.get(key)
        if not value:
            return "NOT_SET"

        schema = self.CONFIG_SCHEMA.get(key, {})
        if schema.get('sensitive', False):
            # Mask API keys: show first 6 and last 4 chars
            if len(str(value)) > 10:
                return f"{str(value)[:6]}...{str(value)[-4:]}"
            else:
                return "***"

        return str(value)

    def print_configuration_report(self) -> None:
        """Print comprehensive configuration report"""
        print("\n" + "=" * 80)
        print("🔧 ARTEMIS CONFIGURATION REPORT")
        print("=" * 80)

        validation = self.validate_configuration(require_llm_key=False)

        # Provider configuration
        print("\n📡 LLM Provider Configuration:")
        print(f"  Provider: {self.get('ARTEMIS_LLM_PROVIDER', 'openai')}")
        print(f"  Model: {self.get('ARTEMIS_LLM_MODEL', 'default (provider-specific)')}")
        print(f"  OpenAI API Key: {self.get_masked('OPENAI_API_KEY')}")
        print(f"  Anthropic API Key: {self.get_masked('ANTHROPIC_API_KEY')}")

        # Storage configuration
        print("\n💾 Storage Configuration:")
        print(f"  RAG Database: {self.get('ARTEMIS_RAG_DB_PATH')}")
        print(f"  Temp Directory: {self.get('ARTEMIS_TEMP_DIR')}")

        # Pipeline configuration
        print("\n⚙️  Pipeline Configuration:")
        print(f"  Max Parallel Developers: {self.get('ARTEMIS_MAX_PARALLEL_DEVELOPERS')}")
        print(f"  Code Review Enabled: {self.get('ARTEMIS_ENABLE_CODE_REVIEW')}")
        print(f"  Auto-Approve Analysis: {self.get('ARTEMIS_AUTO_APPROVE_PROJECT_ANALYSIS')}")

        # Security and compliance
        print("\n🔒 Security & Compliance:")
        print(f"  GDPR Enforcement: {self.get('ARTEMIS_ENFORCE_GDPR')}")
        print(f"  WCAG Enforcement: {self.get('ARTEMIS_ENFORCE_WCAG')}")

        # Logging
        print("\n📋 Logging:")
        print(f"  Verbose: {self.get('ARTEMIS_VERBOSE')}")
        print(f"  Log Level: {self.get('ARTEMIS_LOG_LEVEL')}")

        # Cost controls
        print("\n💰 Cost Controls:")
        print(f"  Max Tokens/Request: {self.get('ARTEMIS_MAX_TOKENS_PER_REQUEST')}")
        cost_limit = self.get('ARTEMIS_COST_LIMIT_USD')
        print(f"  Cost Limit: ${cost_limit}/day" if cost_limit else "  Cost Limit: Not set")

        # Validation results
        print("\n✅ Validation Results:")
        if validation.is_valid:
            print("  Status: ✅ VALID")
        else:
            print("  Status: ❌ INVALID")

        if validation.missing_keys:
            print(f"\n  ❌ Missing Required Keys:")
            for key in validation.missing_keys:
                print(f"     - {key}")

        if validation.invalid_keys:
            print(f"\n  ❌ Invalid Values:")
            for key in validation.invalid_keys:
                print(f"     - {key}")

        if validation.warnings:
            print(f"\n  ⚠️  Warnings:")
            for warning in validation.warnings:
                print(f"     - {warning}")

        print("\n" + "=" * 80)

    def export_to_dict(self, mask_sensitive: bool = True) -> Dict[str, Any]:
        """
        Export configuration as dictionary

        Args:
            mask_sensitive: Mask sensitive values

        Returns:
            Configuration dictionary
        """
        if mask_sensitive:
            return {
                key: self.get_masked(key)
                for key in self.config.keys()
            }
        else:
            return self.config.copy()

    def set_defaults_for_testing(self) -> None:
        """Set safe defaults for testing (no real API calls)"""
        self.config['ARTEMIS_LLM_PROVIDER'] = 'mock'
        self.config['OPENAI_API_KEY'] = 'sk-test-key'
        self.config['ARTEMIS_RAG_DB_PATH'] = 'db_test'  # Separate test DB
        self.config['ARTEMIS_ENABLE_CODE_REVIEW'] = False
        print("⚠️  Test mode enabled - using mock LLM provider")


# Singleton instance
_config_instance: Optional[ConfigurationAgent] = None


def get_config(verbose: bool = True) -> ConfigurationAgent:
    """
    Get singleton configuration agent instance

    Args:
        verbose: Enable verbose logging

    Returns:
        ConfigurationAgent instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigurationAgent(verbose=verbose)
    return _config_instance


# CLI for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Artemis Configuration Agent")
    parser.add_argument("--validate", action="store_true", help="Validate configuration")
    parser.add_argument("--report", action="store_true", help="Print configuration report")
    parser.add_argument("--export", action="store_true", help="Export configuration as JSON")
    args = parser.parse_args()

    config = ConfigurationAgent(verbose=True)

    if args.report or (not args.validate and not args.export):
        config.print_configuration_report()

    if args.validate:
        result = config.validate_configuration()
        if result.is_valid:
            print("\n✅ Configuration is VALID")
            exit(0)
        else:
            print("\n❌ Configuration is INVALID")
            exit(1)

    if args.export:
        import json
        print(json.dumps(config.export_to_dict(), indent=2))
