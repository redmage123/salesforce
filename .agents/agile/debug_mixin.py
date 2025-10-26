#!/usr/bin/env python3
"""
Debug Mixin - Reusable debug logging for all stages and agents

Provides consistent debug logging methods that can be mixed into any class.
Uses DebugService singleton for centralized debug configuration.

Usage:
    class MyStage(PipelineStage, DebugMixin):
        def __init__(self, ...):
            DebugMixin.__init__(self, component_name="my_stage")

        def execute(self, card, context):
            self.debug_log("Starting execution", card_id=card['card_id'])
            self.debug_dump("Context", context)
            self.debug_trace("execute", card_id=card['card_id'], context_keys=list(context.keys()))

            with self.debug_section("Processing features"):
                # Your code here
                pass
"""

from typing import Any, Dict, Optional
from contextlib import contextmanager
from debug_service import DebugService


class DebugMixin:
    """
    Mixin providing debug logging methods

    Automatically integrates with DebugService singleton.
    """

    def __init__(self, component_name: str, **kwargs):
        """
        Initialize debug mixin

        Args:
            component_name: Name of component for debug output (e.g., "validation", "sprint_planning")
        """
        # Call super().__init__() to support cooperative multiple inheritance
        if hasattr(super(), '__init__'):
            super().__init__(**kwargs)

        self._debug_component_name = component_name
        self._debug_service = DebugService.get_instance()

    def debug_log(self, message: str, **kwargs):
        """
        Log a debug message with component context

        Args:
            message: Debug message
            **kwargs: Additional key-value pairs to log

        Example:
            self.debug_log("Processing features", feature_count=10)
        """
        self._debug_service.log(message, self._debug_component_name.upper(), **kwargs)

    def debug_dump(self, label: str, data: Any):
        """
        Dump a data structure in formatted JSON

        Args:
            label: Description of the data
            data: Data to dump

        Example:
            self.debug_dump("Routing Decision", decision_dict)
        """
        self._debug_service.dump(label, data, self._debug_component_name.upper())

    def debug_trace(self, function_name: str, **kwargs):
        """
        Trace function execution with parameters

        Args:
            function_name: Name of the function being traced
            **kwargs: Function parameters to log

        Example:
            self.debug_trace("_validate_developer", dev_name="developer-a", test_path="/tmp/tests")
        """
        self._debug_service.trace(function_name, self._debug_component_name.upper(), **kwargs)

    def is_debug_enabled(self) -> bool:
        """
        Check if debug is enabled for this component

        Returns:
            True if debug enabled
        """
        return self._debug_service.is_enabled(self._debug_component_name)

    def is_debug_feature_enabled(self, feature: str) -> bool:
        """
        Check if a specific debug feature is enabled for this component

        Args:
            feature: Feature name (e.g., "verbose_test_output")

        Returns:
            True if feature enabled

        Example:
            if self.is_debug_feature_enabled('verbose_test_output'):
                print(test_output)
        """
        return self._debug_service.is_feature_enabled(self._debug_component_name, feature)

    @contextmanager
    def debug_section(self, section_name: str, **kwargs):
        """
        Context manager for debugging a section of code

        Automatically logs entry/exit with timing

        Args:
            section_name: Name of the section
            **kwargs: Additional context to log

        Example:
            with self.debug_section("Planning Poker", feature_count=10):
                # Your code here
                pass
        """
        import time

        # Log entry
        self.debug_log(f"→ Entering {section_name}", **kwargs)
        start_time = time.time()

        try:
            yield
        finally:
            # Log exit with timing
            elapsed = time.time() - start_time
            self.debug_log(f"← Exiting {section_name}", elapsed_seconds=f"{elapsed:.2f}")

    def debug_if_enabled(self, feature: str, message: str, **kwargs):
        """
        Log only if specific feature is enabled

        Args:
            feature: Feature name to check
            message: Debug message
            **kwargs: Additional key-value pairs

        Example:
            self.debug_if_enabled('verbose_test_output', "Test stdout", output=stdout)
        """
        if self.is_debug_feature_enabled(feature):
            self.debug_log(message, **kwargs)

    def debug_dump_if_enabled(self, feature: str, label: str, data: Any):
        """
        Dump data only if specific feature is enabled

        Args:
            feature: Feature name to check
            label: Description of the data
            data: Data to dump

        Example:
            self.debug_dump_if_enabled('dump_test_results', "Test Results", test_results)
        """
        if self.is_debug_feature_enabled(feature):
            self.debug_dump(label, data)
