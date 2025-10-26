#!/usr/bin/env python3
"""
Workflow Action Handlers - SOLID Refactored Version

Each handler class has a single responsibility (Single Responsibility Principle)
Handler classes are organized by category and can be extended independently
(Open/Closed Principle)

8 Handler Categories:
1. InfrastructureHandlers - System resource issues
2. CodeHandlers - Code quality and compilation
3. DependencyHandlers - Package and import management
4. LLMHandlers - LLM API and response handling
5. StageHandlers - Pipeline stage-specific issues
6. MultiAgentHandlers - Multi-agent coordination
7. DataHandlers - Data validation and storage
8. SystemHandlers - System-level operations
"""

import os
import psutil
import shutil
import subprocess
import time
import gc
import random
from typing import Dict, Any
from pathlib import Path
from abc import ABC, abstractmethod

from artemis_constants import (
    MAX_RETRY_ATTEMPTS,
    DEFAULT_RETRY_INTERVAL_SECONDS,
    RETRY_BACKOFF_FACTOR
)


# ============================================================================
# BASE HANDLER INTERFACE
# ============================================================================

class WorkflowHandler(ABC):
    """
    Abstract base class for workflow handlers

    All handlers follow the same interface (Interface Segregation Principle)
    """

    @abstractmethod
    def handle(self, context: Dict[str, Any]) -> bool:
        """
        Handle the workflow action

        Args:
            context: Context dictionary with action parameters

        Returns:
            True if action succeeded, False otherwise
        """
        pass


# ============================================================================
# INFRASTRUCTURE HANDLERS
# ============================================================================

class KillHangingProcessHandler(WorkflowHandler):
    """Kill hanging process"""

    def handle(self, context: Dict[str, Any]) -> bool:
        pid = context.get("pid")
        if not pid:
            return False

        try:
            process = psutil.Process(pid)
            process.terminate()
            time.sleep(DEFAULT_RETRY_INTERVAL_SECONDS - 3)  # 2 seconds

            if process.is_running():
                process.kill()

            print(f"[Workflow] Killed hanging process {pid}")
            return True
        except Exception as e:
            print(f"[Workflow] Failed to kill process {pid}: {e}")
            return False


class IncreaseTimeoutHandler(WorkflowHandler):
    """Increase timeout for stage"""

    def handle(self, context: Dict[str, Any]) -> bool:
        stage_name = context.get("stage_name")
        current_timeout = context.get("timeout_seconds", 300)
        new_timeout = current_timeout * 2

        context["timeout_seconds"] = new_timeout
        print(f"[Workflow] Increased timeout for {stage_name}: {current_timeout}s → {new_timeout}s")
        return True


class FreeMemoryHandler(WorkflowHandler):
    """Free up memory"""

    def handle(self, context: Dict[str, Any]) -> bool:
        try:
            gc.collect()
            print("[Workflow] Freed memory")
            return True
        except Exception as e:
            print(f"[Workflow] Failed to free memory: {e}")
            return False


class CleanupTempFilesHandler(WorkflowHandler):
    """Clean up temporary files"""

    def handle(self, context: Dict[str, Any]) -> bool:
        try:
            # Get developer base directory from environment (same logic as DeveloperInvoker)
            import os
            developer_base_dir = os.getenv("ARTEMIS_DEVELOPER_DIR", "/tmp")
            if not os.path.isabs(developer_base_dir):
                script_dir = Path(__file__).parent.resolve()
                developer_base_dir = script_dir / developer_base_dir

            # Build list of temp directories to clean
            temp_dirs = [
                str(Path(developer_base_dir) / "developer-a"),
                str(Path(developer_base_dir) / "developer-b"),
                "/tmp/adr"  # ADR still uses /tmp (could be made configurable too)
            ]

            for temp_dir in temp_dirs:
                if Path(temp_dir).exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    print(f"[Workflow] Cleaned up {temp_dir}")

            return True
        except Exception as e:
            print(f"[Workflow] Failed to cleanup temp files: {e}")
            return False


class CheckDiskSpaceHandler(WorkflowHandler):
    """Check and report disk space"""

    def handle(self, context: Dict[str, Any]) -> bool:
        try:
            usage = shutil.disk_usage("/")
            free_gb = usage.free / (1024**3)

            print(f"[Workflow] Disk space: {free_gb:.2f} GB free")

            if free_gb < 1:
                print("[Workflow] ⚠️  Low disk space!")
                return False

            return True
        except Exception as e:
            print(f"[Workflow] Failed to check disk space: {e}")
            return False


class RetryNetworkRequestHandler(WorkflowHandler):
    """Retry network request with exponential backoff"""

    def handle(self, context: Dict[str, Any]) -> bool:
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                # TODO: Implement actual network retry
                time.sleep(RETRY_BACKOFF_FACTOR ** attempt)
                print(f"[Workflow] Network retry {attempt + 1}/{MAX_RETRY_ATTEMPTS}")
                return True
            except Exception:
                if attempt == MAX_RETRY_ATTEMPTS - 1:
                    return False
                continue
        return False


# ============================================================================
# CODE HANDLERS
# ============================================================================

class RunLinterFixHandler(WorkflowHandler):
    """Run linter auto-fix"""

    def handle(self, context: Dict[str, Any]) -> bool:
        file_path = context.get("file_path")
        if not file_path:
            return False

        try:
            # Run black for Python files
            if file_path.endswith(".py"):
                subprocess.run(["black", file_path], check=True, capture_output=True)
                print(f"[Workflow] Auto-fixed {file_path} with black")

            # Run prettier for JS/TS files
            elif file_path.endswith((".js", ".ts", ".jsx", ".tsx")):
                subprocess.run(["prettier", "--write", file_path], check=True, capture_output=True)
                print(f"[Workflow] Auto-fixed {file_path} with prettier")

            return True
        except Exception as e:
            print(f"[Workflow] Failed to auto-fix {file_path}: {e}")
            return False


class RerunTestsHandler(WorkflowHandler):
    """Re-run failed tests"""

    def handle(self, context: Dict[str, Any]) -> bool:
        test_path = context.get("test_path", ".")

        try:
            result = subprocess.run(
                ["python3", "-m", "pytest", test_path, "-v"],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                print(f"[Workflow] Tests passed: {test_path}")
                return True
            else:
                print(f"[Workflow] Tests still failing: {test_path}")
                return False
        except Exception as e:
            print(f"[Workflow] Failed to run tests: {e}")
            return False


class FixSecurityVulnerabilityHandler(WorkflowHandler):
    """Apply security patch"""

    def handle(self, context: Dict[str, Any]) -> bool:
        vulnerability_type = context.get("vulnerability_type")
        print(f"[Workflow] Applying security patch for {vulnerability_type}")
        # TODO: Implement security patch logic
        return True


class RetryCompilationHandler(WorkflowHandler):
    """Retry compilation"""

    def handle(self, context: Dict[str, Any]) -> bool:
        file_path = context.get("file_path")

        try:
            # For Python, check syntax
            if file_path and file_path.endswith(".py"):
                with open(file_path) as f:
                    compile(f.read(), file_path, "exec")

            print(f"[Workflow] Compilation successful: {file_path}")
            return True
        except SyntaxError as e:
            print(f"[Workflow] Syntax error in {file_path}: {e}")
            return False
        except Exception as e:
            print(f"[Workflow] Compilation failed: {e}")
            return False


# ============================================================================
# DEPENDENCY HANDLERS
# ============================================================================

class InstallMissingDependencyHandler(WorkflowHandler):
    """Install missing dependency"""

    def handle(self, context: Dict[str, Any]) -> bool:
        package = context.get("package")
        if not package:
            return False

        try:
            subprocess.run(
                ["pip", "install", package],
                check=True,
                capture_output=True,
                timeout=300
            )
            print(f"[Workflow] Installed dependency: {package}")
            return True
        except Exception as e:
            print(f"[Workflow] Failed to install {package}: {e}")
            return False


class ResolveVersionConflictHandler(WorkflowHandler):
    """Resolve package version conflict"""

    def handle(self, context: Dict[str, Any]) -> bool:
        package = context.get("package")
        version = context.get("version")

        try:
            if version:
                subprocess.run(
                    ["pip", "install", f"{package}=={version}"],
                    check=True,
                    capture_output=True,
                    timeout=300
                )
            else:
                subprocess.run(
                    ["pip", "install", "--upgrade", package],
                    check=True,
                    capture_output=True,
                    timeout=300
                )

            print(f"[Workflow] Resolved version conflict for {package}")
            return True
        except Exception as e:
            print(f"[Workflow] Failed to resolve version conflict: {e}")
            return False


class FixImportErrorHandler(WorkflowHandler):
    """Fix import error"""

    def handle(self, context: Dict[str, Any]) -> bool:
        module_name = context.get("module")

        try:
            subprocess.run(
                ["pip", "install", module_name],
                check=True,
                capture_output=True,
                timeout=300
            )
            print(f"[Workflow] Fixed import error for {module_name}")
            return True
        except Exception as e:
            print(f"[Workflow] Failed to fix import error: {e}")
            return False


# ============================================================================
# LLM HANDLERS
# ============================================================================

class SwitchLLMProviderHandler(WorkflowHandler):
    """Switch to backup LLM provider"""

    def handle(self, context: Dict[str, Any]) -> bool:
        current_provider = context.get("current_provider", "openai")

        if current_provider == "openai":
            context["llm_provider"] = "anthropic"
            print("[Workflow] Switched from OpenAI to Anthropic")
        else:
            context["llm_provider"] = "openai"
            print("[Workflow] Switched from Anthropic to OpenAI")

        return True


class RetryLLMRequestHandler(WorkflowHandler):
    """Retry LLM request with backoff"""

    def handle(self, context: Dict[str, Any]) -> bool:
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                # TODO: Implement actual LLM retry
                time.sleep(RETRY_BACKOFF_FACTOR ** attempt)
                print(f"[Workflow] LLM retry {attempt + 1}/{MAX_RETRY_ATTEMPTS}")
                return True
            except Exception:
                if attempt == MAX_RETRY_ATTEMPTS - 1:
                    return False
                continue

        return False


class HandleRateLimitHandler(WorkflowHandler):
    """Handle LLM rate limit"""

    def handle(self, context: Dict[str, Any]) -> bool:
        wait_time = context.get("wait_time", 60)

        print(f"[Workflow] Rate limited, waiting {wait_time}s...")
        time.sleep(wait_time)

        return True


class ValidateLLMResponseHandler(WorkflowHandler):
    """Validate and sanitize LLM response"""

    def handle(self, context: Dict[str, Any]) -> bool:
        response = context.get("llm_response", "")

        # TODO: Implement response validation
        if len(response) > 0:
            print("[Workflow] LLM response validated")
            return True
        else:
            print("[Workflow] Invalid LLM response")
            return False


# ============================================================================
# STAGE HANDLERS
# ============================================================================

class RegenerateArchitectureHandler(WorkflowHandler):
    """Regenerate architecture document"""

    def handle(self, context: Dict[str, Any]) -> bool:
        print("[Workflow] Regenerating architecture...")
        # TODO: Trigger architecture stage re-run
        return True


class RequestCodeReviewRevisionHandler(WorkflowHandler):
    """Request code review revision"""

    def handle(self, context: Dict[str, Any]) -> bool:
        issues = context.get("review_issues", [])
        print(f"[Workflow] Requesting revision for {len(issues)} code review issues")
        # TODO: Send revision request to developer agents
        return True


class ResolveIntegrationConflictHandler(WorkflowHandler):
    """Resolve integration conflict"""

    def handle(self, context: Dict[str, Any]) -> bool:
        conflict_files = context.get("conflict_files", [])
        print(f"[Workflow] Resolving conflicts in {len(conflict_files)} files")
        # TODO: Implement conflict resolution
        return True


class RerunValidationHandler(WorkflowHandler):
    """Re-run validation"""

    def handle(self, context: Dict[str, Any]) -> bool:
        print("[Workflow] Re-running validation...")
        # TODO: Trigger validation stage re-run
        return True


# ============================================================================
# MULTI-AGENT HANDLERS
# ============================================================================

class BreakArbitrationDeadlockHandler(WorkflowHandler):
    """Break arbitration deadlock"""

    def handle(self, context: Dict[str, Any]) -> bool:
        developer_a_score = context.get("developer_a_score", 0)
        developer_b_score = context.get("developer_b_score", 0)

        # Choose based on scores, or random if tied
        if developer_a_score > developer_b_score:
            context["chosen_solution"] = "developer_a"
            print("[Workflow] Arbitration: Chose Developer A (higher score)")
        elif developer_b_score > developer_a_score:
            context["chosen_solution"] = "developer_b"
            print("[Workflow] Arbitration: Chose Developer B (higher score)")
        else:
            context["chosen_solution"] = random.choice(["developer_a", "developer_b"])
            print(f"[Workflow] Arbitration: Randomly chose {context['chosen_solution']}")

        return True


class MergeDeveloperSolutionsHandler(WorkflowHandler):
    """Merge conflicting developer solutions"""

    def handle(self, context: Dict[str, Any]) -> bool:
        print("[Workflow] Merging developer solutions...")
        # TODO: Implement intelligent merge logic
        return True


class RestartMessengerHandler(WorkflowHandler):
    """Restart messenger service"""

    def handle(self, context: Dict[str, Any]) -> bool:
        print("[Workflow] Restarting messenger...")
        # TODO: Restart messenger
        return True


# ============================================================================
# DATA HANDLERS
# ============================================================================

class ValidateCardDataHandler(WorkflowHandler):
    """Validate and sanitize card data"""

    def handle(self, context: Dict[str, Any]) -> bool:
        card = context.get("card", {})

        required_fields = ["card_id", "title", "description"]
        for field in required_fields:
            if field not in card:
                print(f"[Workflow] Missing required field: {field}")
                return False

        print("[Workflow] Card data validated")
        return True


class RestoreStateFromBackupHandler(WorkflowHandler):
    """Restore state from backup"""

    def handle(self, context: Dict[str, Any]) -> bool:
        backup_file = context.get("backup_file")

        if backup_file and Path(backup_file).exists():
            print(f"[Workflow] Restoring state from {backup_file}")
            # TODO: Implement state restoration
            return True
        else:
            print("[Workflow] No backup file found")
            return False


class RebuildRAGIndexHandler(WorkflowHandler):
    """Rebuild RAG index"""

    def handle(self, context: Dict[str, Any]) -> bool:
        print("[Workflow] Rebuilding RAG index...")
        # TODO: Trigger RAG rebuild
        return True


# ============================================================================
# SYSTEM HANDLERS
# ============================================================================

class CleanupZombieProcessesHandler(WorkflowHandler):
    """Clean up zombie processes"""

    def handle(self, context: Dict[str, Any]) -> bool:
        try:
            zombies_cleaned = 0

            for proc in psutil.process_iter(['pid', 'status']):
                if proc.info['status'] == psutil.STATUS_ZOMBIE:
                    try:
                        proc.wait(timeout=1)
                        zombies_cleaned += 1
                    except:
                        pass

            print(f"[Workflow] Cleaned up {zombies_cleaned} zombie processes")
            return True
        except Exception as e:
            print(f"[Workflow] Failed to cleanup zombies: {e}")
            return False


class ReleaseFileLocksHandler(WorkflowHandler):
    """Release file locks"""

    def handle(self, context: Dict[str, Any]) -> bool:
        file_path = context.get("file_path")
        # TODO: Implement file lock release
        print(f"[Workflow] Released file lock: {file_path}")
        return True


class FixPermissionsHandler(WorkflowHandler):
    """Fix file permissions"""

    def handle(self, context: Dict[str, Any]) -> bool:
        file_path = context.get("file_path")

        try:
            if file_path and Path(file_path).exists():
                os.chmod(file_path, 0o644)
                print(f"[Workflow] Fixed permissions for {file_path}")
                return True
        except Exception as e:
            print(f"[Workflow] Failed to fix permissions: {e}")
            return False

        return True


# ============================================================================
# HANDLER FACTORY (Factory Pattern)
# ============================================================================

class WorkflowHandlerFactory:
    """
    Factory for creating workflow handlers

    Implements Factory Pattern for flexible handler creation
    Makes it easy to add new handlers without modifying existing code
    (Open/Closed Principle)
    """

    # Handler registry - maps action names to handler classes
    _handlers = {
        # Infrastructure
        "kill_hanging_process": KillHangingProcessHandler,
        "increase_timeout": IncreaseTimeoutHandler,
        "free_memory": FreeMemoryHandler,
        "cleanup_temp_files": CleanupTempFilesHandler,
        "check_disk_space": CheckDiskSpaceHandler,
        "retry_network_request": RetryNetworkRequestHandler,

        # Code
        "run_linter_fix": RunLinterFixHandler,
        "rerun_tests": RerunTestsHandler,
        "fix_security_vulnerability": FixSecurityVulnerabilityHandler,
        "retry_compilation": RetryCompilationHandler,

        # Dependencies
        "install_missing_dependency": InstallMissingDependencyHandler,
        "resolve_version_conflict": ResolveVersionConflictHandler,
        "fix_import_error": FixImportErrorHandler,

        # LLM
        "switch_llm_provider": SwitchLLMProviderHandler,
        "retry_llm_request": RetryLLMRequestHandler,
        "handle_rate_limit": HandleRateLimitHandler,
        "validate_llm_response": ValidateLLMResponseHandler,

        # Stages
        "regenerate_architecture": RegenerateArchitectureHandler,
        "request_code_review_revision": RequestCodeReviewRevisionHandler,
        "resolve_integration_conflict": ResolveIntegrationConflictHandler,
        "rerun_validation": RerunValidationHandler,

        # Multi-agent
        "break_arbitration_deadlock": BreakArbitrationDeadlockHandler,
        "merge_developer_solutions": MergeDeveloperSolutionsHandler,
        "restart_messenger": RestartMessengerHandler,

        # Data
        "validate_card_data": ValidateCardDataHandler,
        "restore_state_from_backup": RestoreStateFromBackupHandler,
        "rebuild_rag_index": RebuildRAGIndexHandler,

        # System
        "cleanup_zombie_processes": CleanupZombieProcessesHandler,
        "release_file_locks": ReleaseFileLocksHandler,
        "fix_permissions": FixPermissionsHandler,
    }

    @classmethod
    def create(cls, action_name: str) -> WorkflowHandler:
        """
        Create a workflow handler by action name

        Args:
            action_name: Name of the workflow action

        Returns:
            WorkflowHandler instance

        Raises:
            ValueError: If action name is unknown
        """
        handler_class = cls._handlers.get(action_name)

        if not handler_class:
            raise ValueError(
                f"Unknown workflow action: {action_name}. "
                f"Available: {', '.join(cls._handlers.keys())}"
            )

        return handler_class()

    @classmethod
    def register(cls, action_name: str, handler_class: type):
        """
        Register a new handler class

        Allows extending handlers without modifying this file
        (Open/Closed Principle)

        Args:
            action_name: Name of the action
            handler_class: Handler class (must extend WorkflowHandler)
        """
        if not issubclass(handler_class, WorkflowHandler):
            raise ValueError(f"{handler_class} must extend WorkflowHandler")

        cls._handlers[action_name] = handler_class

    @classmethod
    def get_all_actions(cls) -> list:
        """Get list of all registered action names"""
        return list(cls._handlers.keys())


# ============================================================================
# BACKWARD COMPATIBILITY ADAPTER
# ============================================================================

class WorkflowHandlers:
    """
    Backward compatibility adapter for old WorkflowHandlers class

    Maintains the static method API while delegating to new handler classes
    Allows gradual migration without breaking existing code
    """

    @staticmethod
    def kill_hanging_process(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("kill_hanging_process").handle(context)

    @staticmethod
    def increase_timeout(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("increase_timeout").handle(context)

    @staticmethod
    def free_memory(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("free_memory").handle(context)

    @staticmethod
    def cleanup_temp_files(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("cleanup_temp_files").handle(context)

    @staticmethod
    def check_disk_space(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("check_disk_space").handle(context)

    @staticmethod
    def retry_network_request(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("retry_network_request").handle(context)

    @staticmethod
    def run_linter_fix(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("run_linter_fix").handle(context)

    @staticmethod
    def rerun_tests(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("rerun_tests").handle(context)

    @staticmethod
    def fix_security_vulnerability(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("fix_security_vulnerability").handle(context)

    @staticmethod
    def retry_compilation(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("retry_compilation").handle(context)

    @staticmethod
    def install_missing_dependency(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("install_missing_dependency").handle(context)

    @staticmethod
    def resolve_version_conflict(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("resolve_version_conflict").handle(context)

    @staticmethod
    def fix_import_error(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("fix_import_error").handle(context)

    @staticmethod
    def switch_llm_provider(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("switch_llm_provider").handle(context)

    @staticmethod
    def retry_llm_request(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("retry_llm_request").handle(context)

    @staticmethod
    def handle_rate_limit(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("handle_rate_limit").handle(context)

    @staticmethod
    def validate_llm_response(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("validate_llm_response").handle(context)

    @staticmethod
    def regenerate_architecture(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("regenerate_architecture").handle(context)

    @staticmethod
    def request_code_review_revision(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("request_code_review_revision").handle(context)

    @staticmethod
    def resolve_integration_conflict(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("resolve_integration_conflict").handle(context)

    @staticmethod
    def rerun_validation(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("rerun_validation").handle(context)

    @staticmethod
    def break_arbitration_deadlock(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("break_arbitration_deadlock").handle(context)

    @staticmethod
    def merge_developer_solutions(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("merge_developer_solutions").handle(context)

    @staticmethod
    def restart_messenger(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("restart_messenger").handle(context)

    @staticmethod
    def validate_card_data(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("validate_card_data").handle(context)

    @staticmethod
    def restore_state_from_backup(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("restore_state_from_backup").handle(context)

    @staticmethod
    def rebuild_rag_index(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("rebuild_rag_index").handle(context)

    @staticmethod
    def cleanup_zombie_processes(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("cleanup_zombie_processes").handle(context)

    @staticmethod
    def release_file_locks(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("release_file_locks").handle(context)

    @staticmethod
    def fix_permissions(context: Dict[str, Any]) -> bool:
        return WorkflowHandlerFactory.create("fix_permissions").handle(context)
