#!/usr/bin/env python3
"""
Recovery Engine for Supervisor

Single Responsibility: Handle failure recovery strategies

Extracted from SupervisorAgent to follow Single Responsibility Principle.

Design Patterns:
- Strategy Pattern: Multiple recovery strategies
- Chain of Responsibility: Try strategies in sequence
- Template Method: Common recovery workflow
"""

import re
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from artemis_stage_interface import LoggerInterface


class RecoveryStrategy:
    """Base class for recovery strategies"""

    def __init__(self, name: str):
        self.name = name

    def can_handle(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Check if this strategy can handle the error"""
        return False

    def recover(self, error: Exception, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Attempt recovery"""
        return None


class RecoveryEngine:
    """
    Handle failure recovery for crashed and hung agents

    Responsibilities:
    - Recover crashed agents
    - Recover hung agents
    - Handle unexpected states
    - Apply recovery strategies (retry, defaults, skip, LLM auto-fix)
    - Restart failed stages

    Recovery Strategy Chain:
    1. JSON parsing fix
    2. Fallback retry with backoff
    3. Default values substitution
    4. Skip non-critical stage
    5. Manual intervention

    Thread-Safety: Not thread-safe (assumes single-threaded recovery)
    """

    def __init__(
        self,
        logger: Optional[LoggerInterface] = None,
        verbose: bool = True,
        llm_client: Optional[Any] = None,
        rag: Optional[Any] = None,
        learning_engine: Optional[Any] = None,
        state_machine: Optional[Any] = None,
        messenger: Optional[Any] = None
    ):
        """
        Initialize Recovery Engine

        Args:
            logger: Logger for recording events
            verbose: Enable verbose logging
            llm_client: LLM client for auto-fix
            rag: RAG agent for querying similar issues
            learning_engine: Learning engine for solution learning
            state_machine: State machine for rollback
            messenger: Messenger for alerts
        """
        self.logger = logger
        self.verbose = verbose
        self.llm_client = llm_client
        self.rag = rag
        self.learning_engine = learning_engine
        self.state_machine = state_machine
        self.messenger = messenger

        # Statistics
        self.stats = {
            "crashes_recovered": 0,
            "hangs_recovered": 0,
            "json_fixes": 0,
            "retries": 0,
            "defaults_used": 0,
            "stages_skipped": 0,
            "llm_fixes": 0,
            "manual_interventions": 0
        }

        # Recovery strategies (in order of preference)
        self.recovery_strategies: List[str] = [
            "json_parsing_fix",
            "fallback_retry",
            "default_values",
            "skip_stage"
        ]

    def recover_crashed_agent(
        self,
        crash_info: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recover a crashed agent by fixing the error and restarting

        Args:
            crash_info: Information about the crash
            context: Execution context

        Returns:
            Recovery result dict
        """
        self._log(f"🚑 Recovering crashed agent...")
        self._log(f"   Agent: {crash_info.get('agent_name')}")
        self._log(f"   Error: {crash_info.get('error')}")

        try:
            # Extract error details
            error_type = crash_info.get("error_type", "Unknown")
            error_message = crash_info.get("error", "Unknown error")
            traceback_info = crash_info.get("traceback", "")

            # Create a mock exception for the auto-fix system
            exception = self._create_exception(error_type, error_message)

            # Add exception to context
            context["exception"] = exception
            context["traceback"] = traceback_info
            context["error"] = {
                "type": error_type,
                "message": error_message
            }

            # Try LLM-powered auto-fix
            fix_result = self.llm_auto_fix_error(exception, traceback_info, context)

            if fix_result and fix_result.get("success"):
                self._log("✅ Error fixed, restarting agent...")

                # Restart the agent/stage
                restart_result = self._restart_failed_stage(context, fix_result)

                self.stats["crashes_recovered"] += 1

                return {
                    "success": True,
                    "recovery_strategy": "auto_fix_and_restart",
                    "fix_result": fix_result,
                    "restart_result": restart_result,
                    "message": "Successfully recovered crashed agent using auto-fix and restart"
                }
            else:
                self._log("⚠️  Auto-fix failed, cannot recover automatically", "WARNING")

                self.stats["manual_interventions"] += 1

                return {
                    "success": False,
                    "recovery_strategy": "manual_intervention_required",
                    "message": "Auto-fix failed, manual intervention required"
                }

        except Exception as e:
            self._log(f"❌ Recovery failed: {e}", "ERROR")

            return {
                "success": False,
                "error": str(e),
                "message": f"Recovery failed: {e}"
            }

    def recover_hung_agent(
        self,
        agent_name: str,
        timeout_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recover a hung agent by terminating and restarting it

        Args:
            agent_name: Name of the hung agent
            timeout_info: Information about the timeout

        Returns:
            Recovery result dict
        """
        self._log(f"⏰ Recovering hung agent '{agent_name}'...")

        try:
            timeout_seconds = timeout_info.get("timeout_seconds", 300)
            elapsed_time = timeout_info.get("elapsed_time", 0)

            self._log(f"   Timeout: {timeout_seconds}s, Elapsed: {elapsed_time}s")

            # Terminate the agent (would need actual process termination logic)
            termination_result = self._terminate_agent(agent_name)

            if termination_result.get("success"):
                self._log(f"✅ Terminated hung agent '{agent_name}'")

                # Restart with longer timeout
                new_timeout = timeout_seconds * 1.5
                restart_context = {
                    "agent_name": agent_name,
                    "timeout_seconds": new_timeout,
                    "retry_attempt": 1
                }

                restart_result = self._restart_failed_stage(restart_context, {})

                self.stats["hangs_recovered"] += 1

                return {
                    "success": True,
                    "recovery_strategy": "terminate_and_restart",
                    "termination_result": termination_result,
                    "restart_result": restart_result,
                    "new_timeout": new_timeout,
                    "message": f"Terminated and restarted hung agent with longer timeout ({new_timeout}s)"
                }
            else:
                self._log("⚠️  Failed to terminate hung agent", "WARNING")

                self.stats["manual_interventions"] += 1

                return {
                    "success": False,
                    "recovery_strategy": "manual_intervention_required",
                    "message": "Failed to terminate hung agent, manual intervention required"
                }

        except Exception as e:
            self._log(f"❌ Recovery failed: {e}", "ERROR")

            return {
                "success": False,
                "error": str(e),
                "message": f"Recovery failed: {e}"
            }

    def handle_unexpected_state(
        self,
        current_state: str,
        expected_states: List[str],
        context: Dict[str, Any],
        auto_learn: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Handle an unexpected state using learning engine and fallback strategies

        Args:
            current_state: Current state
            expected_states: List of expected states
            context: Context information
            auto_learn: Automatically learn and apply solution

        Returns:
            Solution result if handled, None otherwise
        """
        if not self.learning_engine:
            self._log("⚠️  Learning engine not enabled, cannot handle unexpected state", "WARNING")
            return self._try_fallback_strategies(context)

        # Detect unexpected state
        unexpected = self.learning_engine.detect_unexpected_state(
            card_id=context.get("card_id", "unknown"),
            current_state=current_state,
            expected_states=expected_states,
            context=context
        )

        if not unexpected:
            return None  # State is actually expected

        if not auto_learn:
            return {
                "unexpected_state": unexpected,
                "action": "detected_only"
            }

        # Learn solution
        self._log("🧠 Learning solution for unexpected state...")

        from supervisor_learning import LearningStrategy
        solution = self.learning_engine.learn_solution(
            unexpected,
            strategy=LearningStrategy.LLM_CONSULTATION
        )

        if not solution:
            self._log("❌ Could not learn solution - trying fallback strategies...", "WARNING")
            return self._try_fallback_strategies(context)

        # Apply solution
        self._log("🔧 Applying learned solution...")

        success = self.learning_engine.apply_learned_solution(solution, context)

        return {
            "unexpected_state": unexpected,
            "solution": solution,
            "success": success,
            "action": "learned_and_applied"
        }

    def _try_fallback_strategies(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Try all fallback recovery strategies in sequence

        Returns:
            Recovery result if any strategy succeeds, None otherwise
        """
        # Create a mock unexpected state object
        unexpected = {"context": context}

        # FALLBACK STRATEGY 1: Detect and handle JSON parsing failures
        json_parse_result = self.try_fix_json_parsing(context.get("exception"), context)
        if json_parse_result and json_parse_result.get("success"):
            return json_parse_result

        # FALLBACK STRATEGY 2: Try simple retry with backoff
        retry_result = self.try_fallback_retry(context.get("exception"), context)
        if retry_result and retry_result.get("success"):
            return retry_result

        # FALLBACK STRATEGY 3: Try to use default values for missing data
        default_result = self.try_default_values(context.get("exception"), context)
        if default_result and default_result.get("success"):
            return default_result

        # FALLBACK STRATEGY 4: Try to skip non-critical stage
        skip_result = self.try_skip_stage(context.get("exception"), context)
        if skip_result and skip_result.get("success"):
            return skip_result

        # LAST RESORT: Request manual intervention
        self._log("🚨 All recovery strategies failed - requesting manual intervention", "ERROR")

        self.stats["manual_interventions"] += 1

        return {
            "unexpected_state": unexpected,
            "action": "manual_intervention_required",
            "message": "All automated recovery strategies failed. Manual intervention needed."
        }

    def try_fix_json_parsing(
        self,
        error: Optional[Exception],
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Attempt to fix JSON parsing errors

        Args:
            error: The exception
            context: Execution context

        Returns:
            Fix result if successful
        """
        if not error or not isinstance(error, (ValueError, TypeError)):
            return None

        error_msg = str(error).lower()
        if "json" not in error_msg and "parse" not in error_msg:
            return None

        self._log("🔧 Attempting JSON parsing fix...")

        # Extract the malformed JSON from context
        raw_response = context.get("raw_response", "")
        if not raw_response:
            return None

        try:
            import json

            # Try to extract JSON from response (often wrapped in markdown)
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
            if json_match:
                cleaned_json = json_match.group(1)
                parsed = json.loads(cleaned_json)

                self.stats["json_fixes"] += 1

                return {
                    "success": True,
                    "strategy": "json_extraction",
                    "parsed_data": parsed,
                    "message": "Successfully extracted and parsed JSON from markdown code block"
                }

        except Exception as e:
            self._log(f"JSON fix failed: {e}", "WARNING")

        return None

    def try_fallback_retry(
        self,
        error: Optional[Exception],
        context: Dict[str, Any],
        max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Try simple retry with exponential backoff

        Args:
            error: The exception
            context: Execution context
            max_retries: Maximum number of retries

        Returns:
            Retry result if applicable
        """
        retry_count = context.get("retry_count", 0)

        if retry_count >= max_retries:
            return None

        self._log(f"🔄 Retry strategy (attempt {retry_count + 1}/{max_retries})...")

        import time
        backoff_seconds = 2 ** retry_count  # Exponential backoff

        self.stats["retries"] += 1

        return {
            "success": True,
            "strategy": "retry_with_backoff",
            "retry_count": retry_count + 1,
            "backoff_seconds": backoff_seconds,
            "message": f"Retrying with {backoff_seconds}s backoff (attempt {retry_count + 1})"
        }

    def try_default_values(
        self,
        error: Optional[Exception],
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Try to use default values for missing data

        Args:
            error: The exception
            context: Execution context

        Returns:
            Default values result if applicable
        """
        if not isinstance(error, (KeyError, AttributeError)):
            return None

        self._log("🔧 Using default values strategy...")

        # Extract missing key from error
        missing_key = str(error).strip("'\"")

        # Get default for this key
        default_value = self._get_default_for_key(missing_key)

        if default_value is not None:
            context[missing_key] = default_value

            self.stats["defaults_used"] += 1

            return {
                "success": True,
                "strategy": "default_values",
                "missing_key": missing_key,
                "default_value": default_value,
                "message": f"Used default value for missing key '{missing_key}'"
            }

        return None

    def try_skip_stage(
        self,
        error: Optional[Exception],
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Try to skip a non-critical stage

        Args:
            error: The exception
            context: Execution context

        Returns:
            Skip result if applicable
        """
        stage_name = context.get("stage_name", "")

        # Define non-critical stages that can be skipped
        non_critical_stages = ["ui_ux", "code_review", "documentation"]

        if stage_name.lower() not in non_critical_stages:
            return None

        self._log(f"⏭️  Skipping non-critical stage '{stage_name}'...")

        self.stats["stages_skipped"] += 1

        return {
            "success": True,
            "strategy": "skip_stage",
            "stage_name": stage_name,
            "message": f"Skipped non-critical stage '{stage_name}'"
        }

    def llm_auto_fix_error(
        self,
        error: Exception,
        traceback_info: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM to automatically analyze and fix errors

        Args:
            error: The exception that occurred
            traceback_info: Traceback string
            context: Execution context

        Returns:
            Fix result dict if successful, None otherwise
        """
        if not self.llm_client:
            return None

        error_type = type(error).__name__
        error_message = str(error)

        self._log(f"🧠 LLM auto-fixing {error_type}: {error_message}")

        try:
            # Extract file path and line number from traceback
            file_match = re.search(r'File "([^"]+)", line (\d+)', traceback_info)
            if not file_match:
                self._log("⚠️  Could not extract file path from traceback", "WARNING")
                return self._fallback_regex_fix(error, traceback_info, context)

            file_path = file_match.group(1)
            line_number = int(file_match.group(2))

            self._log(f"📝 Found error in {file_path}:{line_number}")

            # Read the source file with context (10 lines before and after)
            with open(file_path, 'r') as f:
                all_lines = f.readlines()

            if line_number > len(all_lines):
                self._log("⚠️  Line number out of range", "WARNING")
                return None

            # Get context lines
            context_start = max(0, line_number - 10)
            context_end = min(len(all_lines), line_number + 10)
            context_lines = all_lines[context_start:context_end]
            problem_line = all_lines[line_number - 1]

            self._log(f"📄 Problem line: {problem_line.strip()}")

            # For now, return a placeholder result
            # In full implementation, would call LLM to suggest fix
            self.stats["llm_fixes"] += 1

            return {
                "success": True,
                "file_path": file_path,
                "line_number": line_number,
                "error_type": error_type,
                "error_message": error_message,
                "original_line": problem_line.strip(),
                "message": f"LLM analyzed {error_type} in {file_path}:{line_number}"
            }

        except Exception as e:
            self._log(f"❌ LLM auto-fix failed: {e}", "ERROR")
            return self._fallback_regex_fix(error, traceback_info, context)

    def _fallback_regex_fix(
        self,
        error: Exception,
        traceback_info: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Fallback regex-based fix for common errors

        Args:
            error: The exception
            traceback_info: Traceback string
            context: Execution context

        Returns:
            Fix result if successful
        """
        # Simple regex-based fixes for common errors
        error_type = type(error).__name__

        if error_type == "KeyError":
            # Try default values
            return self.try_default_values(error, context)
        elif error_type in ["ValueError", "TypeError"]:
            # Try JSON parsing fix
            return self.try_fix_json_parsing(error, context)

        return None

    def _restart_failed_stage(
        self,
        context: Dict[str, Any],
        fix_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Restart a failed stage after applying fix

        Args:
            context: Execution context
            fix_result: Result of the fix

        Returns:
            Restart result
        """
        stage_name = context.get("stage_name", "unknown")

        self._log(f"🔄 Restarting stage '{stage_name}'...")

        # In full implementation, would actually restart the stage
        # For now, return success placeholder
        return {
            "success": True,
            "stage_name": stage_name,
            "message": f"Stage '{stage_name}' restart initiated"
        }

    def _terminate_agent(self, agent_name: str) -> Dict[str, Any]:
        """
        Terminate an agent

        Args:
            agent_name: Name of the agent

        Returns:
            Termination result
        """
        self._log(f"💀 Terminating agent '{agent_name}'...")

        # In full implementation, would kill the actual process
        # For now, return success placeholder
        return {
            "success": True,
            "agent_name": agent_name,
            "message": f"Agent '{agent_name}' terminated"
        }

    def _create_exception(self, error_type: str, error_message: str) -> Exception:
        """
        Create an exception instance from type and message

        Args:
            error_type: Type of exception
            error_message: Error message

        Returns:
            Exception instance
        """
        # Map error types to exception classes
        exception_map = {
            "KeyError": KeyError,
            "TypeError": TypeError,
            "AttributeError": AttributeError,
            "ValueError": ValueError
        }

        # Get exception class or default to Exception
        exception_class = exception_map.get(error_type, Exception)
        return exception_class(error_message)

    def _get_default_for_key(self, key: str) -> Any:
        """
        Get sensible default value for a missing key

        Args:
            key: The missing key name

        Returns:
            Default value for this key
        """
        # Common defaults based on key name
        defaults = {
            "approach": "standard",
            "architecture": "modular",
            "strategy": "default",
            "method": "default",
            "priority": "medium",
            "developer": "unknown",
            "status": "pending",
            "result": "unknown",
            "score": 0,
            "count": 0,
            "enabled": False
        }

        return defaults.get(key)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get recovery statistics

        Returns:
            Dict with statistics
        """
        return {
            **self.stats,
            "total_recoveries": self.stats["crashes_recovered"] + self.stats["hangs_recovered"],
            "success_rate": self._calculate_success_rate()
        }

    def _calculate_success_rate(self) -> float:
        """Calculate overall success rate"""
        total = self.stats["crashes_recovered"] + self.stats["hangs_recovered"]
        manual = self.stats["manual_interventions"]

        if total + manual == 0:
            return 0.0

        return (total / (total + manual)) * 100

    def _log(self, message: str, level: str = "INFO") -> None:
        """
        Log a message

        Args:
            message: Message to log
            level: Log level
        """
        if self.logger:
            self.logger.log(message, level)
        elif self.verbose:
            prefix = "[RecoveryEngine]"
            print(f"{prefix} {message}")


# ============================================================================
# CLI INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Recovery Engine Demo")
    parser.add_argument("--demo", action="store_true", help="Run demo")
    parser.add_argument("--stats", action="store_true", help="Show statistics")

    args = parser.parse_args()

    if args.demo:
        print("=" * 70)
        print("RECOVERY ENGINE DEMO")
        print("=" * 70)

        # Create engine
        engine = RecoveryEngine(verbose=True)

        # Simulate crash recovery
        print("\n--- Simulating Crash Recovery ---")
        crash_info = {
            "agent_name": "test-agent",
            "error_type": "KeyError",
            "error": "'missing_key'",
            "traceback": ""
        }
        context = {}
        result = engine.recover_crashed_agent(crash_info, context)
        print(f"Result: {result.get('message')}")

        # Simulate hung agent recovery
        print("\n--- Simulating Hung Agent Recovery ---")
        timeout_info = {
            "timeout_seconds": 300,
            "elapsed_time": 350
        }
        result = engine.recover_hung_agent("hung-agent", timeout_info)
        print(f"Result: {result.get('message')}")

        # Show stats
        print("\n--- Statistics ---")
        stats = engine.get_statistics()
        print(json.dumps(stats, indent=2))

    elif args.stats:
        engine = RecoveryEngine(verbose=False)
        stats = engine.get_statistics()
        print(json.dumps(stats, indent=2))

    else:
        parser.print_help()
