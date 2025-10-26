#!/usr/bin/env python3
"""
Debug Service - Centralized debug mode management

Supports three activation methods (priority order):
1. CLI flag: --debug or --debug-profile=verbose
2. Environment variable: ARTEMIS_DEBUG=1 or ARTEMIS_DEBUG=verbose
3. Hydra config: debug.enabled=true

Usage:
    from debug_service import DebugService

    debug = DebugService.get_instance()

    if debug.is_enabled('validation'):
        debug.log("Test path resolved", path=test_path)
        debug.dump("Test results", test_results)
"""

import os
import json
from typing import Dict, Any, Optional
from datetime import datetime
from omegaconf import DictConfig
from artemis_stage_interface import LoggerInterface


class DebugService:
    """
    Singleton service for managing debug mode across Artemis pipeline.

    Provides:
    - Centralized debug state management
    - Component-specific debug flags
    - Formatted debug output
    - Multiple activation methods (CLI, env var, config)
    """

    _instance: Optional['DebugService'] = None

    def __init__(
        self,
        config: Optional[DictConfig] = None,
        logger: Optional[LoggerInterface] = None,
        cli_debug: Optional[str] = None
    ):
        """
        Initialize debug service (use get_instance() instead).

        Args:
            config: Hydra debug config
            logger: Logger instance for output
            cli_debug: CLI debug flag value (None, 'true', or profile name)
        """
        self.logger = logger
        self.config = config
        self.cli_debug = cli_debug

        # Check environment variable
        self.env_debug = os.environ.get('ARTEMIS_DEBUG', None)

        # Determine if debug is enabled (priority: CLI > ENV > Config)
        self._enabled = self._determine_enabled()

        # Load active profile
        self._profile = self._determine_profile()

        if self._enabled and self.logger:
            self.logger.log(f"🐛 DEBUG MODE ENABLED (profile: {self._profile})", "INFO")

    @classmethod
    def get_instance(cls) -> 'DebugService':
        """Get singleton instance of DebugService"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def initialize(
        cls,
        config: Optional[DictConfig] = None,
        logger: Optional[LoggerInterface] = None,
        cli_debug: Optional[str] = None
    ) -> 'DebugService':
        """
        Initialize the debug service singleton.

        Args:
            config: Hydra debug config
            logger: Logger instance
            cli_debug: CLI debug flag value

        Returns:
            Initialized DebugService instance
        """
        cls._instance = cls(config, logger, cli_debug)
        return cls._instance

    def _determine_enabled(self) -> bool:
        """Determine if debug mode is enabled based on priority order"""
        # Priority 1: CLI flag
        if self.cli_debug is not None:
            return True

        # Priority 2: Environment variable
        if self.env_debug:
            return self.env_debug.lower() in ('1', 'true', 'yes', 'on', 'verbose', 'minimal')

        # Priority 3: Config
        if self.config:
            if hasattr(self.config, 'enabled'):
                return self.config.enabled
            # Log diagnostic if config doesn't have 'enabled'
            if self.logger:
                self.logger.log(f"⚠️  Debug config found but has no 'enabled' field: {self.config}", "WARNING")

        return False

    def _determine_profile(self) -> str:
        """Determine active debug profile"""
        # CLI has highest priority
        if self.cli_debug and self.cli_debug not in ('true', '1', 'yes'):
            return self.cli_debug

        # Then environment
        if self.env_debug and self.env_debug.lower() in ('verbose', 'minimal'):
            return self.env_debug.lower()

        # Default to 'default' profile
        return 'default'

    def is_enabled(self, component: Optional[str] = None) -> bool:
        """
        Check if debug is enabled globally or for a specific component.

        Args:
            component: Component name (e.g., 'validation', 'routing')
                      If None, checks global debug state

        Returns:
            True if debug is enabled for component
        """
        if not self._enabled:
            return False

        if component is None:
            return True

        # Check component-specific flag
        if self.config and hasattr(self.config, 'components'):
            component_config = getattr(self.config.components, component, None)
            if component_config:
                return True

        return True  # If no specific config, use global setting

    def is_feature_enabled(self, component: str, feature: str) -> bool:
        """
        Check if a specific debug feature is enabled.

        Args:
            component: Component name (e.g., 'validation')
            feature: Feature name (e.g., 'verbose_test_output')

        Returns:
            True if feature is enabled
        """
        if not self.is_enabled(component):
            return False

        if not self.config or not hasattr(self.config, 'components'):
            return True  # Default to enabled if no config

        component_config = getattr(self.config.components, component, None)
        if not component_config:
            return True

        return getattr(component_config, feature, False)

    def log(self, message: str, component: str = "DEBUG", **kwargs):
        """
        Log a debug message.

        Args:
            message: Message to log
            component: Component name for filtering
            **kwargs: Additional key-value pairs to log
        """
        if not self.is_enabled():
            return

        if self.logger:
            timestamp = datetime.now().strftime(self._get_timestamp_format())
            prefix = f"[{timestamp}] 🐛 [{component}]"

            if kwargs:
                # Format kwargs
                kwargs_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
                full_message = f"{prefix} {message} ({kwargs_str})"
            else:
                full_message = f"{prefix} {message}"

            self.logger.log(full_message, "DEBUG")

    def dump(self, label: str, data: Any, component: str = "DEBUG"):
        """
        Dump data structure in formatted JSON.

        Args:
            label: Label for the dump
            data: Data to dump
            component: Component name
        """
        if not self.is_enabled():
            return

        if not self.logger:
            return

        indent = self._get_indent()
        truncate = self._get_truncate_limit()

        try:
            json_str = json.dumps(data, indent=indent, default=str)

            if truncate > 0 and len(json_str) > truncate:
                json_str = json_str[:truncate] + f"\n... (truncated, {len(json_str)} total chars)"

            timestamp = datetime.now().strftime(self._get_timestamp_format())
            self.logger.log(f"[{timestamp}] 🐛 [{component}] {label}:", "DEBUG")
            self.logger.log(json_str, "DEBUG")
        except Exception as e:
            self.logger.log(f"Failed to dump {label}: {e}", "WARNING")

    def trace(self, func_name: str, component: str = "TRACE", **kwargs):
        """
        Trace function execution.

        Args:
            func_name: Function name
            component: Component name
            **kwargs: Function arguments to log
        """
        if not self.is_enabled():
            return

        self.log(f"→ {func_name}()", component, **kwargs)

    def _get_timestamp_format(self) -> str:
        """Get timestamp format from config"""
        if self.config and hasattr(self.config, 'formatting'):
            return getattr(self.config.formatting, 'timestamp_format', '%H:%M:%S')
        return '%H:%M:%S'

    def _get_indent(self) -> Optional[int]:
        """Get JSON indent from config"""
        if self.config and hasattr(self.config, 'formatting'):
            indent = getattr(self.config.formatting, 'indent_json', 2)
            return indent if indent > 0 else None
        return 2

    def _get_truncate_limit(self) -> int:
        """Get truncation limit from config"""
        if self.config and hasattr(self.config, 'formatting'):
            return getattr(self.config.formatting, 'truncate_output', 1000)
        return 1000

    def log_section_start(self, section_name: str, component: str = "DEBUG"):
        """Log start of a debug section"""
        if not self.is_enabled():
            return

        if self.logger:
            self.logger.log(f"{'='*60}", "DEBUG")
            self.logger.log(f"🐛 DEBUG: {section_name}", "DEBUG")
            self.logger.log(f"{'='*60}", "DEBUG")

    def log_section_end(self, section_name: str, component: str = "DEBUG"):
        """Log end of a debug section"""
        if not self.is_enabled():
            return

        if self.logger:
            self.logger.log(f"{'='*60}", "DEBUG")
            self.logger.log(f"🐛 END: {section_name}", "DEBUG")
            self.logger.log(f"{'='*60}", "DEBUG")


# Convenience functions for quick access
def is_debug_enabled(component: Optional[str] = None) -> bool:
    """Check if debug is enabled"""
    debug = DebugService.get_instance()
    return debug.is_enabled(component)


def debug_log(message: str, component: str = "DEBUG", **kwargs):
    """Log a debug message"""
    debug = DebugService.get_instance()
    debug.log(message, component, **kwargs)


def debug_dump(label: str, data: Any, component: str = "DEBUG"):
    """Dump data in debug mode"""
    debug = DebugService.get_instance()
    debug.dump(label, data, component)


def debug_trace(func_name: str, component: str = "TRACE", **kwargs):
    """Trace function execution"""
    debug = DebugService.get_instance()
    debug.trace(func_name, component, **kwargs)
