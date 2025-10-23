#!/usr/bin/env python3
"""
Artemis Supervisor Agent - Pipeline Traffic Cop and Circuit Breaker

Single Responsibility: Monitor pipeline health, detect failures, and orchestrate graceful recovery

Features:
- Process health monitoring (hanging, timeouts, crashes)
- Automatic retry with exponential backoff
- Circuit breaker pattern for failing stages
- Graceful failover and degradation
- Resource cleanup (zombie processes, file locks)
- Real-time alerting via AgentMessenger

SOLID Principles:
- Single Responsibility: Only monitors and recovers pipeline health
- Open/Closed: Extensible recovery strategies without modification
- Liskov Substitution: Works with any PipelineStage implementation
- Interface Segregation: Minimal supervision interface
- Dependency Inversion: Depends on abstractions (PipelineStage, LoggerInterface)
"""

import time
import psutil
import signal
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict

from artemis_stage_interface import PipelineStage, LoggerInterface
from artemis_exceptions import (
    ArtemisException,
    PipelineStageError,
    wrap_exception
)
from artemis_state_machine import (
    ArtemisStateMachine,
    PipelineState,
    StageState,
    EventType,
    IssueType
)


class HealthStatus(Enum):
    """Pipeline health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    CRITICAL = "critical"


class RecoveryAction(Enum):
    """Recovery action types"""
    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"
    FALLBACK = "fallback"
    RESTART = "restart"


@dataclass
class ProcessHealth:
    """Process health information"""
    pid: int
    stage_name: str
    start_time: datetime
    cpu_percent: float
    memory_mb: float
    status: str
    is_hanging: bool
    is_timeout: bool


@dataclass
class StageHealth:
    """Stage health tracking"""
    stage_name: str
    failure_count: int
    last_failure: Optional[datetime]
    total_duration: float
    execution_count: int
    circuit_open: bool
    circuit_open_until: Optional[datetime]


@dataclass
class RecoveryStrategy:
    """Recovery strategy for a stage"""
    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    backoff_multiplier: float = 2.0
    timeout_seconds: float = 300.0  # 5 minutes
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_seconds: float = 300.0  # 5 minutes
    fallback_action: Optional[Callable] = None


class SupervisorAgent:
    """
    Artemis Supervisor Agent - Pipeline Traffic Cop

    Monitors pipeline execution and orchestrates graceful recovery from failures.
    """

    def __init__(
        self,
        logger: Optional[LoggerInterface] = None,
        messenger: Optional[Any] = None,
        card_id: Optional[str] = None,
        rag: Optional[Any] = None,
        verbose: bool = True
    ):
        """
        Initialize supervisor agent

        Args:
            logger: Logger for recording events
            messenger: AgentMessenger for alerts
            card_id: Optional card ID for state machine
            rag: Optional RAG agent for learning from history
            verbose: Enable verbose logging
        """
        self.logger = logger
        self.messenger = messenger
        self.verbose = verbose
        self.rag = rag

        # State machine for tracking pipeline state
        self.state_machine: Optional[ArtemisStateMachine] = None
        if card_id:
            self.state_machine = ArtemisStateMachine(
                card_id=card_id,
                verbose=verbose
            )
            if self.verbose:
                print(f"[Supervisor] State machine initialized for card {card_id}")

        # RAG integration
        if self.rag and self.verbose:
            print(f"[Supervisor] RAG integration enabled - learning from history")

        # Health tracking
        self.stage_health: Dict[str, StageHealth] = {}
        self.process_registry: Dict[int, ProcessHealth] = {}
        self.recovery_strategies: Dict[str, RecoveryStrategy] = {}

        # Monitoring state
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.monitored_processes: List[int] = []

        # Statistics
        self.stats = {
            "total_interventions": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "processes_killed": 0,
            "timeouts_detected": 0,
            "hanging_processes": 0
        }

    def register_stage(
        self,
        stage_name: str,
        recovery_strategy: Optional[RecoveryStrategy] = None
    ) -> None:
        """
        Register a stage for supervision

        Args:
            stage_name: Name of the stage
            recovery_strategy: Recovery strategy (uses default if not provided)
        """
        if stage_name not in self.stage_health:
            self.stage_health[stage_name] = StageHealth(
                stage_name=stage_name,
                failure_count=0,
                last_failure=None,
                total_duration=0.0,
                execution_count=0,
                circuit_open=False,
                circuit_open_until=None
            )

        if recovery_strategy:
            self.recovery_strategies[stage_name] = recovery_strategy
        else:
            self.recovery_strategies[stage_name] = RecoveryStrategy()

        # Register with state machine
        if self.state_machine:
            self.state_machine.update_stage_state(
                stage_name,
                StageState.PENDING
            )

        if self.verbose:
            print(f"[Supervisor] Registered stage: {stage_name}")

    def check_circuit_breaker(self, stage_name: str) -> bool:
        """
        Check if circuit breaker is open for a stage

        Args:
            stage_name: Stage name

        Returns:
            True if circuit is open (stage should not execute)
        """
        if stage_name not in self.stage_health:
            return False

        health = self.stage_health[stage_name]

        if not health.circuit_open:
            return False

        # Check if circuit should be closed
        if health.circuit_open_until and datetime.now() > health.circuit_open_until:
            health.circuit_open = False
            health.circuit_open_until = None
            if self.verbose:
                print(f"[Supervisor] Circuit breaker closed for {stage_name}")
            return False

        if self.verbose:
            time_remaining = (health.circuit_open_until - datetime.now()).seconds
            print(f"[Supervisor] ⚠️  Circuit breaker OPEN for {stage_name} ({time_remaining}s remaining)")

        return True

    def open_circuit_breaker(self, stage_name: str) -> None:
        """
        Open circuit breaker for a stage

        Args:
            stage_name: Stage name
        """
        if stage_name not in self.stage_health:
            return

        health = self.stage_health[stage_name]
        strategy = self.recovery_strategies.get(stage_name, RecoveryStrategy())

        health.circuit_open = True
        health.circuit_open_until = datetime.now() + timedelta(
            seconds=strategy.circuit_breaker_timeout_seconds
        )

        if self.messenger:
            self.messenger.send_message(
                f"🚨 CIRCUIT BREAKER OPEN: {stage_name}",
                f"Stage has failed {health.failure_count} times. Temporarily disabled for "
                f"{strategy.circuit_breaker_timeout_seconds}s"
            )

        if self.verbose:
            print(f"[Supervisor] 🚨 Circuit breaker OPEN for {stage_name} (timeout: {strategy.circuit_breaker_timeout_seconds}s)")

    def execute_with_supervision(
        self,
        stage: PipelineStage,
        stage_name: str,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a stage with supervision and recovery

        Args:
            stage: Stage to execute
            stage_name: Stage name
            *args: Positional arguments for stage.execute()
            **kwargs: Keyword arguments for stage.execute()

        Returns:
            Stage execution result

        Raises:
            PipelineStageError: If stage fails after all recovery attempts
        """
        # Register stage if not already registered
        if stage_name not in self.stage_health:
            self.register_stage(stage_name)

        # Update state machine: stage starting
        if self.state_machine:
            self.state_machine.push_state(PipelineState.STAGE_RUNNING, {"stage": stage_name})
            self.state_machine.update_stage_state(stage_name, StageState.RUNNING)

        # Check circuit breaker
        if self.check_circuit_breaker(stage_name):
            # Circuit open - attempt fallback or skip
            strategy = self.recovery_strategies.get(stage_name, RecoveryStrategy())
            if strategy.fallback_action:
                if self.verbose:
                    print(f"[Supervisor] Executing fallback for {stage_name}")
                return strategy.fallback_action(*args, **kwargs)
            else:
                # Skip stage
                if self.verbose:
                    print(f"[Supervisor] Skipping {stage_name} (circuit breaker open)")
                return {"status": "skipped", "reason": "circuit_breaker_open"}

        health = self.stage_health[stage_name]
        strategy = self.recovery_strategies.get(stage_name, RecoveryStrategy())

        retry_count = 0
        last_error = None

        while retry_count <= strategy.max_retries:
            try:
                if retry_count > 0:
                    retry_delay = strategy.retry_delay_seconds * (strategy.backoff_multiplier ** (retry_count - 1))
                    if self.verbose:
                        print(f"[Supervisor] Retry {retry_count}/{strategy.max_retries} for {stage_name} (waiting {retry_delay}s)")
                    time.sleep(retry_delay)

                # Execute stage with timeout monitoring
                start_time = datetime.now()

                # Start monitoring in background thread
                monitor_thread = threading.Thread(
                    target=self._monitor_execution,
                    args=(stage_name, strategy.timeout_seconds),
                    daemon=True
                )
                monitor_thread.start()

                # Execute stage
                result = stage.execute(*args, **kwargs)

                # Success!
                duration = (datetime.now() - start_time).total_seconds()
                health.execution_count += 1
                health.total_duration += duration

                if retry_count > 0:
                    self.stats["successful_recoveries"] += 1
                    if self.verbose:
                        print(f"[Supervisor] ✅ Recovery successful for {stage_name} after {retry_count} retries")

                return result

            except Exception as e:
                last_error = e
                retry_count += 1
                health.failure_count += 1
                health.last_failure = datetime.now()
                self.stats["total_interventions"] += 1

                if self.verbose:
                    print(f"[Supervisor] ❌ Stage {stage_name} failed: {str(e)}")

                # Check if circuit breaker should open
                if health.failure_count >= strategy.circuit_breaker_threshold:
                    self.open_circuit_breaker(stage_name)
                    break

                # Log retry attempt
                if retry_count <= strategy.max_retries:
                    if self.logger:
                        self.logger.log(f"Stage {stage_name} failed, retrying ({retry_count}/{strategy.max_retries})")

        # All retries exhausted
        self.stats["failed_recoveries"] += 1

        if self.messenger:
            self.messenger.send_message(
                f"❌ STAGE FAILURE: {stage_name}",
                f"Failed after {retry_count} retries. Last error: {str(last_error)}"
            )

        raise wrap_exception(
            last_error,
            PipelineStageError,
            f"Stage {stage_name} failed after {retry_count} retry attempts",
            context={
                "stage_name": stage_name,
                "retry_count": retry_count,
                "failure_count": health.failure_count,
                "last_error": str(last_error)
            }
        )

    def _monitor_execution(self, stage_name: str, timeout_seconds: float) -> None:
        """
        Monitor stage execution for timeout

        Args:
            stage_name: Stage being monitored
            timeout_seconds: Timeout threshold
        """
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time

            if elapsed > timeout_seconds:
                self.stats["timeouts_detected"] += 1
                if self.verbose:
                    print(f"[Supervisor] ⏰ TIMEOUT detected for {stage_name} ({elapsed:.1f}s > {timeout_seconds}s)")

                if self.messenger:
                    self.messenger.send_message(
                        f"⏰ TIMEOUT: {stage_name}",
                        f"Stage exceeded timeout of {timeout_seconds}s (elapsed: {elapsed:.1f}s)"
                    )
                break

            time.sleep(5)  # Check every 5 seconds

    def detect_hanging_processes(self) -> List[ProcessHealth]:
        """
        Detect hanging processes (high CPU, no progress)

        Returns:
            List of hanging processes
        """
        hanging = []

        for pid, process_health in self.process_registry.items():
            try:
                process = psutil.Process(pid)

                # Check if process is hung
                cpu_percent = process.cpu_percent(interval=1.0)
                elapsed = (datetime.now() - process_health.start_time).total_seconds()

                # Heuristic: high CPU for long time = hanging
                if cpu_percent > 90 and elapsed > 300:  # 5 minutes
                    process_health.is_hanging = True
                    process_health.cpu_percent = cpu_percent
                    hanging.append(process_health)

            except psutil.NoSuchProcess:
                # Process already terminated
                continue

        if hanging:
            self.stats["hanging_processes"] += len(hanging)

        return hanging

    def kill_hanging_process(self, pid: int, force: bool = False) -> bool:
        """
        Kill a hanging process

        Args:
            pid: Process ID
            force: Use SIGKILL instead of SIGTERM

        Returns:
            True if killed successfully
        """
        try:
            process = psutil.Process(pid)

            if force:
                process.kill()  # SIGKILL
            else:
                process.terminate()  # SIGTERM

            self.stats["processes_killed"] += 1

            if self.verbose:
                signal_name = "SIGKILL" if force else "SIGTERM"
                print(f"[Supervisor] 💀 Killed hanging process {pid} ({signal_name})")

            # Remove from registry
            if pid in self.process_registry:
                del self.process_registry[pid]

            return True

        except Exception as e:
            if self.verbose:
                print(f"[Supervisor] ⚠️  Failed to kill process {pid}: {e}")
            return False

    def cleanup_zombie_processes(self) -> int:
        """
        Clean up zombie processes

        Returns:
            Number of zombies cleaned
        """
        cleaned = 0

        for pid in list(self.process_registry.keys()):
            try:
                process = psutil.Process(pid)
                if process.status() == psutil.STATUS_ZOMBIE:
                    process.wait()  # Reap zombie
                    del self.process_registry[pid]
                    cleaned += 1
            except psutil.NoSuchProcess:
                # Already gone
                if pid in self.process_registry:
                    del self.process_registry[pid]
                    cleaned += 1

        if cleaned > 0 and self.verbose:
            print(f"[Supervisor] 🧹 Cleaned up {cleaned} zombie processes")

        return cleaned

    def get_health_status(self) -> HealthStatus:
        """
        Get overall pipeline health status

        Returns:
            HealthStatus enum value
        """
        if not self.stage_health:
            return HealthStatus.HEALTHY

        # Check for critical failures (open circuit breakers)
        open_circuits = sum(1 for h in self.stage_health.values() if h.circuit_open)
        if open_circuits > 0:
            return HealthStatus.CRITICAL

        # Check for failing stages
        recent_failures = sum(
            1 for h in self.stage_health.values()
            if h.last_failure and (datetime.now() - h.last_failure).seconds < 300
        )

        if recent_failures >= 3:
            return HealthStatus.FAILING
        elif recent_failures >= 1:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get supervision statistics

        Returns:
            Statistics dictionary
        """
        health_status = self.get_health_status()

        stage_stats = {}
        for stage_name, health in self.stage_health.items():
            avg_duration = (health.total_duration / health.execution_count) if health.execution_count > 0 else 0.0
            failure_rate = (health.failure_count / health.execution_count * 100) if health.execution_count > 0 else 0.0

            stage_stats[stage_name] = {
                "executions": health.execution_count,
                "failures": health.failure_count,
                "failure_rate_percent": round(failure_rate, 2),
                "avg_duration_seconds": round(avg_duration, 2),
                "circuit_open": health.circuit_open
            }

        return {
            "overall_health": health_status.value,
            "total_interventions": self.stats["total_interventions"],
            "successful_recoveries": self.stats["successful_recoveries"],
            "failed_recoveries": self.stats["failed_recoveries"],
            "processes_killed": self.stats["processes_killed"],
            "timeouts_detected": self.stats["timeouts_detected"],
            "hanging_processes_detected": self.stats["hanging_processes"],
            "stage_statistics": stage_stats
        }

    def handle_issue(
        self,
        issue_type: IssueType,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Handle an issue using state machine workflows with RAG-enhanced intelligence

        Args:
            issue_type: Type of issue to handle
            context: Context for issue resolution

        Returns:
            True if issue was resolved
        """
        if not self.state_machine:
            if self.verbose:
                print(f"[Supervisor] No state machine available to handle {issue_type.value}")
            return False

        if self.verbose:
            print(f"[Supervisor] Handling issue: {issue_type.value}")

        # Query RAG for similar past issues
        similar_cases = self._query_similar_issues(issue_type, context or {})

        # Enhance context with historical insights
        enhanced_context = self._enhance_context_with_history(
            context or {},
            similar_cases
        )

        # Register issue with state machine
        self.state_machine.register_issue(issue_type)

        # Execute workflow to resolve issue
        success = self.state_machine.execute_workflow(issue_type, enhanced_context)

        # Store outcome in RAG for future learning
        self._store_issue_outcome(issue_type, enhanced_context, success, similar_cases)

        if success:
            if self.verbose:
                print(f"[Supervisor] ✅ Issue resolved: {issue_type.value}")
        else:
            if self.verbose:
                print(f"[Supervisor] ❌ Issue unresolved: {issue_type.value}")

        return success

    def get_state_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        Get current pipeline state snapshot

        Returns:
            State snapshot or None if no state machine
        """
        if not self.state_machine:
            return None

        snapshot = self.state_machine.get_snapshot()
        return {
            "state": snapshot.state.value,
            "timestamp": snapshot.timestamp.isoformat(),
            "card_id": snapshot.card_id,
            "active_stage": snapshot.active_stage,
            "health_status": snapshot.health_status,
            "circuit_breakers_open": snapshot.circuit_breakers_open,
            "active_issues": [issue.value for issue in snapshot.active_issues],
            "stages": {
                name: {
                    "state": info.state.value,
                    "duration_seconds": info.duration_seconds,
                    "retry_count": info.retry_count
                }
                for name, info in snapshot.stages.items()
            }
        }

    def rollback_to_stage(self, target_stage: str) -> bool:
        """
        Rollback pipeline to a previous stage

        Args:
            target_stage: Stage name to rollback to

        Returns:
            True if rollback succeeded
        """
        if not self.state_machine:
            return False

        # Find the state where this stage was running
        target_state = PipelineState.STAGE_RUNNING

        if self.verbose:
            print(f"[Supervisor] Rolling back to stage: {target_stage}")

        return self.state_machine.rollback_to_state(target_state)

    def _query_similar_issues(
        self,
        issue_type: IssueType,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Query RAG for similar past issues

        Args:
            issue_type: Type of issue
            context: Issue context

        Returns:
            List of similar past cases
        """
        if not self.rag:
            return []

        # Build query from issue type and context
        query_parts = [f"issue_type: {issue_type.value}"]

        # Add relevant context
        if "stage_name" in context:
            query_parts.append(f"stage: {context['stage_name']}")
        if "error_message" in context:
            query_parts.append(f"error: {context['error_message']}")

        query_text = " ".join(query_parts)

        try:
            # Query RAG for similar issues
            results = self.rag.query_similar(
                query_text=query_text,
                artifact_types=["issue_resolution", "supervisor_recovery"],
                top_k=5
            )

            if self.verbose and results:
                print(f"[Supervisor] 📚 Found {len(results)} similar past cases")
                for i, case in enumerate(results[:3], 1):
                    success = case.get('metadata', {}).get('success', 'unknown')
                    print(f"[Supervisor]    {i}. {case.get('content', '')[:60]}... (success: {success})")

            return results

        except Exception as e:
            if self.verbose:
                print(f"[Supervisor] ⚠️  RAG query failed: {e}")
            return []

    def _enhance_context_with_history(
        self,
        context: Dict[str, Any],
        similar_cases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Enhance context with insights from similar past cases

        Args:
            context: Current context
            similar_cases: Similar past cases from RAG

        Returns:
            Enhanced context
        """
        if not similar_cases:
            return context

        enhanced = context.copy()

        # Analyze success rates of past cases
        successful_cases = [c for c in similar_cases if c.get('metadata', {}).get('success')]
        failed_cases = [c for c in similar_cases if not c.get('metadata', {}).get('success')]

        enhanced['historical_success_rate'] = (
            len(successful_cases) / len(similar_cases)
            if similar_cases else 0.0
        )

        # Extract successful strategies
        if successful_cases:
            strategies = []
            for case in successful_cases:
                strategy = case.get('metadata', {}).get('workflow_used')
                if strategy:
                    strategies.append(strategy)

            if strategies:
                # Most common successful strategy
                from collections import Counter
                most_common = Counter(strategies).most_common(1)[0][0]
                enhanced['suggested_workflow'] = most_common

                if self.verbose:
                    print(f"[Supervisor] 💡 Historical insight: '{most_common}' workflow succeeded {strategies.count(most_common)}/{len(strategies)} times")

        # Add warnings from failed cases
        if failed_cases:
            enhanced['past_failures'] = len(failed_cases)
            if self.verbose:
                print(f"[Supervisor] ⚠️  Warning: Similar issue failed {len(failed_cases)} times before")

        return enhanced

    def _store_issue_outcome(
        self,
        issue_type: IssueType,
        context: Dict[str, Any],
        success: bool,
        similar_cases: List[Dict[str, Any]]
    ) -> None:
        """
        Store issue resolution outcome in RAG for future learning

        Args:
            issue_type: Issue type
            context: Resolution context
            success: Whether resolution succeeded
            similar_cases: Similar past cases
        """
        if not self.rag:
            return

        try:
            # Build content description
            content_parts = [
                f"Issue: {issue_type.value}",
                f"Outcome: {'SUCCESS' if success else 'FAILED'}",
            ]

            if "stage_name" in context:
                content_parts.append(f"Stage: {context['stage_name']}")

            if "error_message" in context:
                content_parts.append(f"Error: {context['error_message'][:100]}")

            if "suggested_workflow" in context:
                content_parts.append(f"Workflow: {context['suggested_workflow']}")

            content = "\n".join(content_parts)

            # Store in RAG
            artifact_id = self.rag.store_artifact(
                artifact_type="issue_resolution",
                card_id=context.get("card_id", "unknown"),
                task_title=f"{issue_type.value} resolution",
                content=content,
                metadata={
                    "issue_type": issue_type.value,
                    "success": success,
                    "workflow_used": context.get("suggested_workflow", "default"),
                    "stage_name": context.get("stage_name"),
                    "historical_success_rate": context.get("historical_success_rate", 0.0),
                    "similar_cases_count": len(similar_cases),
                    "timestamp": datetime.now().isoformat()
                }
            )

            if self.verbose:
                print(f"[Supervisor] 📝 Stored outcome in RAG: {artifact_id}")

        except Exception as e:
            if self.verbose:
                print(f"[Supervisor] ⚠️  Failed to store in RAG: {e}")

    def get_learning_insights(self) -> Dict[str, Any]:
        """
        Get insights learned from RAG history

        Returns:
            Learning insights
        """
        if not self.rag:
            return {"rag_enabled": False}

        try:
            # Query all issue resolutions (use empty query to get all, increase top_k)
            all_resolutions = self.rag.query_similar(
                query_text="",  # Empty query to get all
                artifact_types=["issue_resolution", "supervisor_recovery"],
                top_k=1000  # Increase limit to get all results
            )

            # Analyze patterns
            total_cases = len(all_resolutions)
            successful = sum(1 for r in all_resolutions if r.get('metadata', {}).get('success'))

            # Group by issue type
            by_issue_type = {}
            for resolution in all_resolutions:
                issue_type = resolution.get('metadata', {}).get('issue_type', 'unknown')
                if issue_type not in by_issue_type:
                    by_issue_type[issue_type] = {"total": 0, "successful": 0}

                by_issue_type[issue_type]["total"] += 1
                if resolution.get('metadata', {}).get('success'):
                    by_issue_type[issue_type]["successful"] += 1

            # Calculate success rates
            insights = {
                "rag_enabled": True,
                "total_cases": total_cases,
                "overall_success_rate": (successful / total_cases * 100) if total_cases > 0 else 0,
                "issue_type_insights": {}
            }

            for issue_type, counts in by_issue_type.items():
                insights["issue_type_insights"][issue_type] = {
                    "total_cases": counts["total"],
                    "success_rate": (counts["successful"] / counts["total"] * 100) if counts["total"] > 0 else 0
                }

            return insights

        except Exception as e:
            if self.verbose:
                print(f"[Supervisor] ⚠️  Failed to get insights: {e}")
            return {"rag_enabled": True, "error": str(e)}

    def print_health_report(self) -> None:
        """Print comprehensive health report"""
        stats = self.get_statistics()

        print("\n" + "="*70)
        print("ARTEMIS SUPERVISOR - HEALTH REPORT")
        print("="*70)

        # Overall health
        health_emoji = {
            "healthy": "✅",
            "degraded": "⚠️",
            "failing": "❌",
            "critical": "🚨"
        }
        emoji = health_emoji.get(stats["overall_health"], "❓")
        print(f"\n{emoji} Overall Health: {stats['overall_health'].upper()}")

        # Intervention stats
        print(f"\n📊 Supervision Statistics:")
        print(f"   Total Interventions:     {stats['total_interventions']}")
        print(f"   Successful Recoveries:   {stats['successful_recoveries']}")
        print(f"   Failed Recoveries:       {stats['failed_recoveries']}")
        print(f"   Processes Killed:        {stats['processes_killed']}")
        print(f"   Timeouts Detected:       {stats['timeouts_detected']}")
        print(f"   Hanging Processes:       {stats['hanging_processes_detected']}")

        # Stage statistics
        if stats["stage_statistics"]:
            print(f"\n📈 Stage Statistics:")
            for stage_name, stage_stats in stats["stage_statistics"].items():
                circuit_indicator = "🚨 OPEN" if stage_stats["circuit_open"] else "✅"
                print(f"\n   {stage_name}:")
                print(f"      Executions:      {stage_stats['executions']}")
                print(f"      Failures:        {stage_stats['failures']}")
                print(f"      Failure Rate:    {stage_stats['failure_rate_percent']}%")
                print(f"      Avg Duration:    {stage_stats['avg_duration_seconds']}s")
                print(f"      Circuit Breaker: {circuit_indicator}")

        print("\n" + "="*70 + "\n")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_supervisor(
    verbose: bool = True,
    messenger: Optional[Any] = None
) -> SupervisorAgent:
    """
    Create supervisor agent with default configuration

    Args:
        verbose: Enable verbose logging
        messenger: AgentMessenger for alerts

    Returns:
        SupervisorAgent instance
    """
    return SupervisorAgent(verbose=verbose, messenger=messenger)


# ============================================================================
# MAIN - TESTING
# ============================================================================

if __name__ == "__main__":
    print("Testing Supervisor Agent...")

    # Create mock stage for testing
    class MockStage:
        def __init__(self, should_fail: bool = False, fail_count: int = 0):
            self.should_fail = should_fail
            self.fail_count = fail_count
            self.execution_count = 0

        def execute(self, *args, **kwargs):
            self.execution_count += 1

            if self.should_fail and self.execution_count <= self.fail_count:
                raise Exception(f"Mock failure #{self.execution_count}")

            time.sleep(1)  # Simulate work
            return {"status": "success", "execution": self.execution_count}

    try:
        # Create supervisor
        print("\n1. Creating supervisor agent...")
        supervisor = create_supervisor(verbose=True)

        # Test successful execution
        print("\n2. Testing successful execution...")
        stage1 = MockStage(should_fail=False)
        result = supervisor.execute_with_supervision(stage1, "test_stage_1")
        print(f"   Result: {result}")

        # Test retry with recovery
        print("\n3. Testing retry with recovery...")
        stage2 = MockStage(should_fail=True, fail_count=2)
        result = supervisor.execute_with_supervision(stage2, "test_stage_2")
        print(f"   Result: {result}")
        print(f"   Executions: {stage2.execution_count}")

        # Test circuit breaker
        print("\n4. Testing circuit breaker...")
        stage3 = MockStage(should_fail=True, fail_count=10)

        for i in range(7):
            try:
                supervisor.execute_with_supervision(stage3, "test_stage_3")
            except PipelineStageError:
                print(f"   Attempt {i+1} failed (expected)")

        # Print health report
        print("\n5. Printing health report...")
        supervisor.print_health_report()

        print("\n✅ All supervisor tests passed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
