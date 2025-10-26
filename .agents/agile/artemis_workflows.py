#!/usr/bin/env python3
"""
Artemis Recovery Workflows - Automated Issue Resolution

Defines recovery workflows for all possible issues in the Artemis pipeline.
Each workflow contains a sequence of actions to diagnose and fix the issue.

Workflow Categories:
1. Infrastructure Issues (timeout, memory, disk, network)
2. Code Issues (compilation, tests, security, linting)
3. Dependency Issues (missing deps, version conflicts)
4. LLM Issues (API errors, timeouts, rate limits)
5. Stage Issues (architecture, code review, integration)
6. Multi-Agent Issues (arbitration, conflicts)
7. Data Issues (invalid card, corrupted state, RAG)
8. System Issues (zombies, file locks, permissions)
"""

import os
import psutil
import shutil
import subprocess
import time
from typing import Dict, Any, Optional
from pathlib import Path

from artemis_state_machine import (
    IssueType,
    Workflow,
    WorkflowAction,
    PipelineState
)
from artemis_constants import (
    MAX_RETRY_ATTEMPTS,
    DEFAULT_RETRY_INTERVAL_SECONDS,
    RETRY_BACKOFF_FACTOR
)

# Import refactored handlers (with backward compatibility)
from workflow_handlers import WorkflowHandlers


# ============================================================================
# LEGACY HANDLER CLASS (Deprecated - use workflow_handlers.py)
# ============================================================================
# This class is preserved for backward compatibility only
# All handler logic has been moved to workflow_handlers.py
#
# The WorkflowHandlers class in workflow_handlers.py provides the same API
# but with better SOLID compliance (30+ classes instead of 1 god class)
#
# To migrate:
# 1. Replace: from artemis_workflows import WorkflowHandlers
# 2. With: from workflow_handlers import WorkflowHandlers
#
# No code changes needed - API is identical
# ============================================================================

class _LegacyWorkflowHandlers:
    """
    DEPRECATED: Legacy workflow handlers

    This class is no longer used. All functionality has been moved to
    workflow_handlers.py with proper SOLID design.

    Import WorkflowHandlers from workflow_handlers.py instead.
    """

    # ========================================================================
    # ALL METHODS BELOW ARE DEPRECATED - DO NOT USE
    # ========================================================================

    @staticmethod
    def kill_hanging_process(context: Dict[str, Any]) -> bool:
        """Kill hanging process"""
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

    @staticmethod
    def increase_timeout(context: Dict[str, Any]) -> bool:
        """Increase timeout for stage"""
        stage_name = context.get("stage_name")
        current_timeout = context.get("timeout_seconds", 300)
        new_timeout = current_timeout * 2

        context["timeout_seconds"] = new_timeout
        print(f"[Workflow] Increased timeout for {stage_name}: {current_timeout}s → {new_timeout}s")
        return True

    @staticmethod
    def free_memory(context: Dict[str, Any]) -> bool:
        """Free up memory"""
        try:
            # Clear Python caches
            import gc
            gc.collect()

            # TODO: Clear other caches (RAG, LLM, etc.)

            print("[Workflow] Freed memory")
            return True
        except Exception as e:
            print(f"[Workflow] Failed to free memory: {e}")
            return False

    @staticmethod
    def cleanup_temp_files(context: Dict[str, Any]) -> bool:
        """Clean up temporary files"""
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

    @staticmethod
    def check_disk_space(context: Dict[str, Any]) -> bool:
        """Check and report disk space"""
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

    @staticmethod
    def retry_network_request(context: Dict[str, Any]) -> bool:
        """Retry network request with exponential backoff"""
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

    # ========================================================================
    # CODE ISSUE HANDLERS
    # ========================================================================

    @staticmethod
    def run_linter_fix(context: Dict[str, Any]) -> bool:
        """Run linter auto-fix"""
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

    @staticmethod
    def rerun_tests(context: Dict[str, Any]) -> bool:
        """Re-run failed tests"""
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

    @staticmethod
    def fix_security_vulnerability(context: Dict[str, Any]) -> bool:
        """Apply security patch"""
        vulnerability_type = context.get("vulnerability_type")

        # TODO: Implement security patch logic
        print(f"[Workflow] Applying security patch for {vulnerability_type}")

        return True

    @staticmethod
    def retry_compilation(context: Dict[str, Any]) -> bool:
        """Retry compilation"""
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

    # ========================================================================
    # DEPENDENCY ISSUE HANDLERS
    # ========================================================================

    @staticmethod
    def install_missing_dependency(context: Dict[str, Any]) -> bool:
        """Install missing dependency"""
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

    @staticmethod
    def resolve_version_conflict(context: Dict[str, Any]) -> bool:
        """Resolve package version conflict"""
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

    @staticmethod
    def fix_import_error(context: Dict[str, Any]) -> bool:
        """Fix import error"""
        module_name = context.get("module")

        # Try to install the module
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

    # ========================================================================
    # LLM ISSUE HANDLERS
    # ========================================================================

    @staticmethod
    def switch_llm_provider(context: Dict[str, Any]) -> bool:
        """Switch to backup LLM provider"""
        current_provider = context.get("current_provider", "openai")

        if current_provider == "openai":
            context["llm_provider"] = "anthropic"
            print("[Workflow] Switched from OpenAI to Anthropic")
        else:
            context["llm_provider"] = "openai"
            print("[Workflow] Switched from Anthropic to OpenAI")

        return True

    @staticmethod
    def retry_llm_request(context: Dict[str, Any]) -> bool:
        """Retry LLM request with backoff"""
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

    @staticmethod
    def handle_rate_limit(context: Dict[str, Any]) -> bool:
        """Handle LLM rate limit"""
        wait_time = context.get("wait_time", 60)

        print(f"[Workflow] Rate limited, waiting {wait_time}s...")
        time.sleep(wait_time)

        return True

    @staticmethod
    def validate_llm_response(context: Dict[str, Any]) -> bool:
        """Validate and sanitize LLM response"""
        response = context.get("llm_response", "")

        # TODO: Implement response validation
        if len(response) > 0:
            print("[Workflow] LLM response validated")
            return True
        else:
            print("[Workflow] Invalid LLM response")
            return False

    # ========================================================================
    # STAGE-SPECIFIC ISSUE HANDLERS
    # ========================================================================

    @staticmethod
    def regenerate_architecture(context: Dict[str, Any]) -> bool:
        """Regenerate architecture document"""
        print("[Workflow] Regenerating architecture...")

        # TODO: Trigger architecture stage re-run
        return True

    @staticmethod
    def request_code_review_revision(context: Dict[str, Any]) -> bool:
        """Request code review revision"""
        issues = context.get("review_issues", [])

        print(f"[Workflow] Requesting revision for {len(issues)} code review issues")

        # TODO: Send revision request to developer agents
        return True

    @staticmethod
    def resolve_integration_conflict(context: Dict[str, Any]) -> bool:
        """Resolve integration conflict"""
        conflict_files = context.get("conflict_files", [])

        print(f"[Workflow] Resolving conflicts in {len(conflict_files)} files")

        # TODO: Implement conflict resolution (prefer Developer A, B, or manual merge)
        return True

    @staticmethod
    def rerun_validation(context: Dict[str, Any]) -> bool:
        """Re-run validation"""
        print("[Workflow] Re-running validation...")

        # TODO: Trigger validation stage re-run
        return True

    # ========================================================================
    # MULTI-AGENT ISSUE HANDLERS
    # ========================================================================

    @staticmethod
    def break_arbitration_deadlock(context: Dict[str, Any]) -> bool:
        """Break arbitration deadlock"""
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
            import random
            context["chosen_solution"] = random.choice(["developer_a", "developer_b"])
            print(f"[Workflow] Arbitration: Randomly chose {context['chosen_solution']}")

        return True

    @staticmethod
    def merge_developer_solutions(context: Dict[str, Any]) -> bool:
        """Merge conflicting developer solutions"""
        print("[Workflow] Merging developer solutions...")

        # TODO: Implement intelligent merge logic
        return True

    @staticmethod
    def restart_messenger(context: Dict[str, Any]) -> bool:
        """Restart messenger service"""
        print("[Workflow] Restarting messenger...")

        # TODO: Restart messenger
        return True

    # ========================================================================
    # DATA ISSUE HANDLERS
    # ========================================================================

    @staticmethod
    def validate_card_data(context: Dict[str, Any]) -> bool:
        """Validate and sanitize card data"""
        card = context.get("card", {})

        required_fields = ["card_id", "title", "description"]
        for field in required_fields:
            if field not in card:
                print(f"[Workflow] Missing required field: {field}")
                return False

        print("[Workflow] Card data validated")
        return True

    @staticmethod
    def restore_state_from_backup(context: Dict[str, Any]) -> bool:
        """Restore state from backup"""
        backup_file = context.get("backup_file")

        if backup_file and Path(backup_file).exists():
            print(f"[Workflow] Restoring state from {backup_file}")
            # TODO: Implement state restoration
            return True
        else:
            print("[Workflow] No backup file found")
            return False

    @staticmethod
    def rebuild_rag_index(context: Dict[str, Any]) -> bool:
        """Rebuild RAG index"""
        print("[Workflow] Rebuilding RAG index...")

        # TODO: Trigger RAG rebuild
        return True

    # ========================================================================
    # SYSTEM ISSUE HANDLERS
    # ========================================================================

    @staticmethod
    def cleanup_zombie_processes(context: Dict[str, Any]) -> bool:
        """Clean up zombie processes"""
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

    @staticmethod
    def release_file_locks(context: Dict[str, Any]) -> bool:
        """Release file locks"""
        file_path = context.get("file_path")

        # TODO: Implement file lock release
        print(f"[Workflow] Released file lock: {file_path}")
        return True

    @staticmethod
    def fix_permissions(context: Dict[str, Any]) -> bool:
        """Fix file permissions"""
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
# WORKFLOW BUILDER
# ============================================================================

class WorkflowBuilder:
    """Build recovery workflows for all issue types"""

    @staticmethod
    def build_all_workflows() -> Dict[IssueType, Workflow]:
        """
        Build all recovery workflows

        Returns:
            Map of issue type → workflow
        """
        return {
            # Infrastructure issues
            IssueType.TIMEOUT: WorkflowBuilder.build_timeout_workflow(),
            IssueType.HANGING_PROCESS: WorkflowBuilder.build_hanging_process_workflow(),
            IssueType.MEMORY_EXHAUSTED: WorkflowBuilder.build_memory_exhausted_workflow(),
            IssueType.DISK_FULL: WorkflowBuilder.build_disk_full_workflow(),
            IssueType.NETWORK_ERROR: WorkflowBuilder.build_network_error_workflow(),

            # Code issues
            IssueType.COMPILATION_ERROR: WorkflowBuilder.build_compilation_error_workflow(),
            IssueType.TEST_FAILURE: WorkflowBuilder.build_test_failure_workflow(),
            IssueType.SECURITY_VULNERABILITY: WorkflowBuilder.build_security_vulnerability_workflow(),
            IssueType.LINTING_ERROR: WorkflowBuilder.build_linting_error_workflow(),

            # Dependency issues
            IssueType.MISSING_DEPENDENCY: WorkflowBuilder.build_missing_dependency_workflow(),
            IssueType.VERSION_CONFLICT: WorkflowBuilder.build_version_conflict_workflow(),
            IssueType.IMPORT_ERROR: WorkflowBuilder.build_import_error_workflow(),

            # LLM issues
            IssueType.LLM_API_ERROR: WorkflowBuilder.build_llm_api_error_workflow(),
            IssueType.LLM_TIMEOUT: WorkflowBuilder.build_llm_timeout_workflow(),
            IssueType.LLM_RATE_LIMIT: WorkflowBuilder.build_llm_rate_limit_workflow(),
            IssueType.INVALID_LLM_RESPONSE: WorkflowBuilder.build_invalid_llm_response_workflow(),

            # Stage-specific issues
            IssueType.ARCHITECTURE_INVALID: WorkflowBuilder.build_architecture_invalid_workflow(),
            IssueType.CODE_REVIEW_FAILED: WorkflowBuilder.build_code_review_failed_workflow(),
            IssueType.INTEGRATION_CONFLICT: WorkflowBuilder.build_integration_conflict_workflow(),
            IssueType.VALIDATION_FAILED: WorkflowBuilder.build_validation_failed_workflow(),

            # Multi-agent issues
            IssueType.ARBITRATION_DEADLOCK: WorkflowBuilder.build_arbitration_deadlock_workflow(),
            IssueType.DEVELOPER_CONFLICT: WorkflowBuilder.build_developer_conflict_workflow(),
            IssueType.MESSENGER_ERROR: WorkflowBuilder.build_messenger_error_workflow(),

            # Data issues
            IssueType.INVALID_CARD: WorkflowBuilder.build_invalid_card_workflow(),
            IssueType.CORRUPTED_STATE: WorkflowBuilder.build_corrupted_state_workflow(),
            IssueType.RAG_ERROR: WorkflowBuilder.build_rag_error_workflow(),

            # System issues
            IssueType.ZOMBIE_PROCESS: WorkflowBuilder.build_zombie_process_workflow(),
            IssueType.FILE_LOCK: WorkflowBuilder.build_file_lock_workflow(),
            IssueType.PERMISSION_DENIED: WorkflowBuilder.build_permission_denied_workflow(),
        }

    # ========================================================================
    # INFRASTRUCTURE WORKFLOWS
    # ========================================================================

    @staticmethod
    def build_timeout_workflow() -> Workflow:
        """Workflow for timeout issues"""
        return Workflow(
            name="Timeout Recovery",
            issue_type=IssueType.TIMEOUT,
            actions=[
                WorkflowAction(
                    action_name="Increase timeout",
                    handler=WorkflowHandlers.increase_timeout,
                    retry_on_failure=False
                ),
                WorkflowAction(
                    action_name="Kill hanging process",
                    handler=WorkflowHandlers.kill_hanging_process,
                    retry_on_failure=True,
                    max_retries=2
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.FAILED,
            rollback_on_failure=False
        )

    @staticmethod
    def build_hanging_process_workflow() -> Workflow:
        """Workflow for hanging process issues"""
        return Workflow(
            name="Hanging Process Recovery",
            issue_type=IssueType.HANGING_PROCESS,
            actions=[
                WorkflowAction(
                    action_name="Kill hanging process",
                    handler=WorkflowHandlers.kill_hanging_process,
                    retry_on_failure=True,
                    max_retries=3
                ),
                WorkflowAction(
                    action_name="Cleanup temp files",
                    handler=WorkflowHandlers.cleanup_temp_files
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.FAILED
        )

    @staticmethod
    def build_memory_exhausted_workflow() -> Workflow:
        """Workflow for memory exhaustion issues"""
        return Workflow(
            name="Memory Recovery",
            issue_type=IssueType.MEMORY_EXHAUSTED,
            actions=[
                WorkflowAction(
                    action_name="Free memory",
                    handler=WorkflowHandlers.free_memory
                ),
                WorkflowAction(
                    action_name="Cleanup temp files",
                    handler=WorkflowHandlers.cleanup_temp_files
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.FAILED
        )

    @staticmethod
    def build_disk_full_workflow() -> Workflow:
        """Workflow for disk full issues"""
        return Workflow(
            name="Disk Space Recovery",
            issue_type=IssueType.DISK_FULL,
            actions=[
                WorkflowAction(
                    action_name="Cleanup temp files",
                    handler=WorkflowHandlers.cleanup_temp_files
                ),
                WorkflowAction(
                    action_name="Check disk space",
                    handler=WorkflowHandlers.check_disk_space
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.FAILED
        )

    @staticmethod
    def build_network_error_workflow() -> Workflow:
        """Workflow for network error issues"""
        return Workflow(
            name="Network Error Recovery",
            issue_type=IssueType.NETWORK_ERROR,
            actions=[
                WorkflowAction(
                    action_name="Retry network request",
                    handler=WorkflowHandlers.retry_network_request,
                    retry_on_failure=True,
                    max_retries=3
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.DEGRADED
        )

    # ========================================================================
    # CODE ISSUE WORKFLOWS
    # ========================================================================

    @staticmethod
    def build_compilation_error_workflow() -> Workflow:
        """Workflow for compilation error issues"""
        return Workflow(
            name="Compilation Error Recovery",
            issue_type=IssueType.COMPILATION_ERROR,
            actions=[
                WorkflowAction(
                    action_name="Retry compilation",
                    handler=WorkflowHandlers.retry_compilation,
                    retry_on_failure=True,
                    max_retries=2
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.FAILED
        )

    @staticmethod
    def build_test_failure_workflow() -> Workflow:
        """Workflow for test failure issues"""
        return Workflow(
            name="Test Failure Recovery",
            issue_type=IssueType.TEST_FAILURE,
            actions=[
                WorkflowAction(
                    action_name="Rerun tests",
                    handler=WorkflowHandlers.rerun_tests,
                    retry_on_failure=True,
                    max_retries=2
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.FAILED
        )

    @staticmethod
    def build_security_vulnerability_workflow() -> Workflow:
        """Workflow for security vulnerability issues"""
        return Workflow(
            name="Security Vulnerability Fix",
            issue_type=IssueType.SECURITY_VULNERABILITY,
            actions=[
                WorkflowAction(
                    action_name="Apply security patch",
                    handler=WorkflowHandlers.fix_security_vulnerability
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.FAILED
        )

    @staticmethod
    def build_linting_error_workflow() -> Workflow:
        """Workflow for linting error issues"""
        return Workflow(
            name="Linting Error Fix",
            issue_type=IssueType.LINTING_ERROR,
            actions=[
                WorkflowAction(
                    action_name="Run linter auto-fix",
                    handler=WorkflowHandlers.run_linter_fix
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.DEGRADED
        )

    # ========================================================================
    # DEPENDENCY ISSUE WORKFLOWS
    # ========================================================================

    @staticmethod
    def build_missing_dependency_workflow() -> Workflow:
        """Workflow for missing dependency issues"""
        return Workflow(
            name="Missing Dependency Fix",
            issue_type=IssueType.MISSING_DEPENDENCY,
            actions=[
                WorkflowAction(
                    action_name="Install missing dependency",
                    handler=WorkflowHandlers.install_missing_dependency,
                    retry_on_failure=True,
                    max_retries=3
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.FAILED
        )

    @staticmethod
    def build_version_conflict_workflow() -> Workflow:
        """Workflow for version conflict issues"""
        return Workflow(
            name="Version Conflict Resolution",
            issue_type=IssueType.VERSION_CONFLICT,
            actions=[
                WorkflowAction(
                    action_name="Resolve version conflict",
                    handler=WorkflowHandlers.resolve_version_conflict,
                    retry_on_failure=True,
                    max_retries=2
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.FAILED
        )

    @staticmethod
    def build_import_error_workflow() -> Workflow:
        """Workflow for import error issues"""
        return Workflow(
            name="Import Error Fix",
            issue_type=IssueType.IMPORT_ERROR,
            actions=[
                WorkflowAction(
                    action_name="Fix import error",
                    handler=WorkflowHandlers.fix_import_error,
                    retry_on_failure=True,
                    max_retries=2
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.FAILED
        )

    # ========================================================================
    # LLM ISSUE WORKFLOWS
    # ========================================================================

    @staticmethod
    def build_llm_api_error_workflow() -> Workflow:
        """Workflow for LLM API error issues"""
        return Workflow(
            name="LLM API Error Recovery",
            issue_type=IssueType.LLM_API_ERROR,
            actions=[
                WorkflowAction(
                    action_name="Retry LLM request",
                    handler=WorkflowHandlers.retry_llm_request,
                    retry_on_failure=True,
                    max_retries=3
                ),
                WorkflowAction(
                    action_name="Switch LLM provider",
                    handler=WorkflowHandlers.switch_llm_provider
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.DEGRADED
        )

    @staticmethod
    def build_llm_timeout_workflow() -> Workflow:
        """Workflow for LLM timeout issues"""
        return Workflow(
            name="LLM Timeout Recovery",
            issue_type=IssueType.LLM_TIMEOUT,
            actions=[
                WorkflowAction(
                    action_name="Retry LLM request",
                    handler=WorkflowHandlers.retry_llm_request,
                    retry_on_failure=True,
                    max_retries=2
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.DEGRADED
        )

    @staticmethod
    def build_llm_rate_limit_workflow() -> Workflow:
        """Workflow for LLM rate limit issues"""
        return Workflow(
            name="LLM Rate Limit Handling",
            issue_type=IssueType.LLM_RATE_LIMIT,
            actions=[
                WorkflowAction(
                    action_name="Handle rate limit",
                    handler=WorkflowHandlers.handle_rate_limit,
                    retry_on_failure=False
                ),
                WorkflowAction(
                    action_name="Switch LLM provider",
                    handler=WorkflowHandlers.switch_llm_provider
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.DEGRADED
        )

    @staticmethod
    def build_invalid_llm_response_workflow() -> Workflow:
        """Workflow for invalid LLM response issues"""
        return Workflow(
            name="LLM Response Validation",
            issue_type=IssueType.INVALID_LLM_RESPONSE,
            actions=[
                WorkflowAction(
                    action_name="Validate LLM response",
                    handler=WorkflowHandlers.validate_llm_response
                ),
                WorkflowAction(
                    action_name="Retry LLM request",
                    handler=WorkflowHandlers.retry_llm_request,
                    retry_on_failure=True,
                    max_retries=2
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.FAILED
        )

    # ========================================================================
    # STAGE-SPECIFIC WORKFLOWS
    # ========================================================================

    @staticmethod
    def build_architecture_invalid_workflow() -> Workflow:
        """Workflow for invalid architecture issues"""
        return Workflow(
            name="Architecture Regeneration",
            issue_type=IssueType.ARCHITECTURE_INVALID,
            actions=[
                WorkflowAction(
                    action_name="Regenerate architecture",
                    handler=WorkflowHandlers.regenerate_architecture,
                    retry_on_failure=True,
                    max_retries=2
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.FAILED
        )

    @staticmethod
    def build_code_review_failed_workflow() -> Workflow:
        """Workflow for code review failure issues"""
        return Workflow(
            name="Code Review Revision",
            issue_type=IssueType.CODE_REVIEW_FAILED,
            actions=[
                WorkflowAction(
                    action_name="Request code review revision",
                    handler=WorkflowHandlers.request_code_review_revision
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.DEGRADED
        )

    @staticmethod
    def build_integration_conflict_workflow() -> Workflow:
        """Workflow for integration conflict issues"""
        return Workflow(
            name="Integration Conflict Resolution",
            issue_type=IssueType.INTEGRATION_CONFLICT,
            actions=[
                WorkflowAction(
                    action_name="Resolve integration conflict",
                    handler=WorkflowHandlers.resolve_integration_conflict
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.FAILED
        )

    @staticmethod
    def build_validation_failed_workflow() -> Workflow:
        """Workflow for validation failure issues"""
        return Workflow(
            name="Validation Retry",
            issue_type=IssueType.VALIDATION_FAILED,
            actions=[
                WorkflowAction(
                    action_name="Rerun validation",
                    handler=WorkflowHandlers.rerun_validation,
                    retry_on_failure=True,
                    max_retries=2
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.DEGRADED
        )

    # ========================================================================
    # MULTI-AGENT WORKFLOWS
    # ========================================================================

    @staticmethod
    def build_arbitration_deadlock_workflow() -> Workflow:
        """Workflow for arbitration deadlock issues"""
        return Workflow(
            name="Arbitration Deadlock Resolution",
            issue_type=IssueType.ARBITRATION_DEADLOCK,
            actions=[
                WorkflowAction(
                    action_name="Break arbitration deadlock",
                    handler=WorkflowHandlers.break_arbitration_deadlock
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.FAILED
        )

    @staticmethod
    def build_developer_conflict_workflow() -> Workflow:
        """Workflow for developer conflict issues"""
        return Workflow(
            name="Developer Conflict Merge",
            issue_type=IssueType.DEVELOPER_CONFLICT,
            actions=[
                WorkflowAction(
                    action_name="Merge developer solutions",
                    handler=WorkflowHandlers.merge_developer_solutions
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.DEGRADED
        )

    @staticmethod
    def build_messenger_error_workflow() -> Workflow:
        """Workflow for messenger error issues"""
        return Workflow(
            name="Messenger Restart",
            issue_type=IssueType.MESSENGER_ERROR,
            actions=[
                WorkflowAction(
                    action_name="Restart messenger",
                    handler=WorkflowHandlers.restart_messenger
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.DEGRADED
        )

    # ========================================================================
    # DATA ISSUE WORKFLOWS
    # ========================================================================

    @staticmethod
    def build_invalid_card_workflow() -> Workflow:
        """Workflow for invalid card issues"""
        return Workflow(
            name="Card Validation",
            issue_type=IssueType.INVALID_CARD,
            actions=[
                WorkflowAction(
                    action_name="Validate card data",
                    handler=WorkflowHandlers.validate_card_data
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.FAILED
        )

    @staticmethod
    def build_corrupted_state_workflow() -> Workflow:
        """Workflow for corrupted state issues"""
        return Workflow(
            name="State Restoration",
            issue_type=IssueType.CORRUPTED_STATE,
            actions=[
                WorkflowAction(
                    action_name="Restore state from backup",
                    handler=WorkflowHandlers.restore_state_from_backup
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.FAILED,
            rollback_on_failure=False
        )

    @staticmethod
    def build_rag_error_workflow() -> Workflow:
        """Workflow for RAG error issues"""
        return Workflow(
            name="RAG Index Rebuild",
            issue_type=IssueType.RAG_ERROR,
            actions=[
                WorkflowAction(
                    action_name="Rebuild RAG index",
                    handler=WorkflowHandlers.rebuild_rag_index
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.DEGRADED
        )

    # ========================================================================
    # SYSTEM ISSUE WORKFLOWS
    # ========================================================================

    @staticmethod
    def build_zombie_process_workflow() -> Workflow:
        """Workflow for zombie process issues"""
        return Workflow(
            name="Zombie Process Cleanup",
            issue_type=IssueType.ZOMBIE_PROCESS,
            actions=[
                WorkflowAction(
                    action_name="Cleanup zombie processes",
                    handler=WorkflowHandlers.cleanup_zombie_processes
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.DEGRADED
        )

    @staticmethod
    def build_file_lock_workflow() -> Workflow:
        """Workflow for file lock issues"""
        return Workflow(
            name="File Lock Release",
            issue_type=IssueType.FILE_LOCK,
            actions=[
                WorkflowAction(
                    action_name="Release file locks",
                    handler=WorkflowHandlers.release_file_locks
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.FAILED
        )

    @staticmethod
    def build_permission_denied_workflow() -> Workflow:
        """Workflow for permission denied issues"""
        return Workflow(
            name="Permission Fix",
            issue_type=IssueType.PERMISSION_DENIED,
            actions=[
                WorkflowAction(
                    action_name="Fix permissions",
                    handler=WorkflowHandlers.fix_permissions
                )
            ],
            success_state=PipelineState.RUNNING,
            failure_state=PipelineState.FAILED
        )
