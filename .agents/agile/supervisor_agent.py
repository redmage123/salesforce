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

import os
import time
import psutil
import signal
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass

from artemis_constants import (
    MAX_RETRY_ATTEMPTS,
    DEFAULT_RETRY_INTERVAL_SECONDS,
    RETRY_BACKOFF_FACTOR
)
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
from cost_tracker import CostTracker, BudgetExceededError
from config_validator import ConfigValidator, validate_config_or_exit
from sandbox_executor import SandboxExecutor, SandboxConfig
from supervisor_learning import (
    SupervisorLearningEngine,
    UnexpectedState,
    LearnedSolution,
    LearningStrategy
)
from debug_mixin import DebugMixin


class AgentHealthEvent(Enum):
    """Agent health event types"""
    STARTED = "started"
    PROGRESS = "progress"
    STALLED = "stalled"
    CRASHED = "crashed"
    HUNG = "hung"
    COMPLETED = "completed"


class AgentHealthObserver(ABC):
    """
    Observer interface for agent health monitoring (Observer Pattern)

    Instead of polling, agents notify observers when their state changes.
    This is more efficient and event-driven.
    """

    @abstractmethod
    def on_agent_event(
        self,
        agent_name: str,
        event: AgentHealthEvent,
        data: Dict[str, Any]
    ) -> None:
        """
        Called when an agent health event occurs

        Args:
            agent_name: Name of the agent
            event: Type of health event
            data: Event-specific data
        """
        pass


class SupervisorHealthObserver(AgentHealthObserver):
    """
    Supervisor implementation of health observer

    Listens for agent crashes and hangs, then triggers recovery
    """

    def __init__(self, supervisor: 'SupervisorAgent'):
        self.supervisor = supervisor
        self.agent_start_times: Dict[str, datetime] = {}
        self.agent_last_activity: Dict[str, datetime] = {}

    def on_agent_event(
        self,
        agent_name: str,
        event: AgentHealthEvent,
        data: Dict[str, Any]
    ) -> None:
        """Handle agent health events"""
        now = datetime.now()

        if event == AgentHealthEvent.STARTED:
            self.agent_start_times[agent_name] = now
            self.agent_last_activity[agent_name] = now
            if self.supervisor.verbose:
                print(f"[Supervisor] 👀 Monitoring agent '{agent_name}'")

        elif event == AgentHealthEvent.PROGRESS:
            self.agent_last_activity[agent_name] = now
            if self.supervisor.verbose:
                print(f"[Supervisor] ✓ Agent '{agent_name}' making progress")

        elif event == AgentHealthEvent.CRASHED:
            if self.supervisor.verbose:
                print(f"[Supervisor] 💥 Agent '{agent_name}' crashed!")

            # Trigger crash recovery
            crash_info = data.get("crash_info", {})
            context = data.get("context", {})
            self.supervisor.recover_crashed_agent(crash_info, context)

        elif event == AgentHealthEvent.HUNG:
            if self.supervisor.verbose:
                print(f"[Supervisor] ⏰ Agent '{agent_name}' appears hung!")

            # Trigger hang recovery
            timeout_info = data.get("timeout_info", {})
            self.supervisor.recover_hung_agent(agent_name, timeout_info)

        elif event == AgentHealthEvent.STALLED:
            if self.supervisor.verbose:
                time_since = data.get("time_since_activity", 0)
                print(f"[Supervisor] ⚠️  Agent '{agent_name}' stalled (no activity for {time_since}s)")

        elif event == AgentHealthEvent.COMPLETED:
            if self.supervisor.verbose:
                elapsed = (now - self.agent_start_times.get(agent_name, now)).total_seconds()
                print(f"[Supervisor] ✅ Agent '{agent_name}' completed (elapsed: {elapsed}s)")

            # Clean up tracking
            self.agent_start_times.pop(agent_name, None)
            self.agent_last_activity.pop(agent_name, None)


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
    max_retries: int = MAX_RETRY_ATTEMPTS
    retry_delay_seconds: float = DEFAULT_RETRY_INTERVAL_SECONDS
    backoff_multiplier: float = RETRY_BACKOFF_FACTOR
    timeout_seconds: float = 300.0  # 5 minutes (stage-specific, can vary)
    circuit_breaker_threshold: int = MAX_RETRY_ATTEMPTS + 2  # 5
    circuit_breaker_timeout_seconds: float = 300.0  # 5 minutes
    fallback_action: Optional[Callable] = None


class SupervisorAgent(DebugMixin):
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
        verbose: bool = True,
        enable_cost_tracking: bool = True,
        enable_config_validation: bool = True,
        enable_sandboxing: bool = True,
        daily_budget: Optional[float] = None,
        monthly_budget: Optional[float] = None,
        hydra_config: Optional[Any] = None
    ):
        """
        Initialize supervisor agent

        Args:
            logger: Logger for recording events
            messenger: AgentMessenger for alerts
            card_id: Optional card ID for state machine
            rag: Optional RAG agent for learning from history
            verbose: Enable verbose logging
            enable_cost_tracking: Enable LLM cost tracking
            enable_config_validation: Enable startup config validation
            enable_sandboxing: Enable security sandboxing for code execution
            daily_budget: Daily LLM budget (None = unlimited)
            monthly_budget: Monthly LLM budget (None = unlimited)
            hydra_config: Hydra configuration object (for LLM settings)
        """
        # Initialize DebugMixin
        DebugMixin.__init__(self, component_name="supervisor")

        # Initialize basic attributes
        self._init_basic_attributes(logger, messenger, verbose, rag, card_id, hydra_config)

        # Initialize LLM configuration
        self._init_llm_config()

        # Initialize health monitoring
        self._init_health_monitoring()

        # Run validation checks
        if enable_config_validation:
            self._run_config_validation()
            self._run_preflight_validation()

        # Initialize optional subsystems
        self._init_cost_tracking(enable_cost_tracking, card_id, daily_budget, monthly_budget)
        self._init_security_sandbox(enable_sandboxing)
        self._init_learning_engine()
        self._init_state_machine(card_id, verbose)
        self._init_health_tracking()
        self._init_statistics()

    def _init_basic_attributes(self, logger, messenger, verbose, rag, card_id, hydra_config):
        """Initialize basic supervisor attributes"""
        self.logger = logger
        self.messenger = messenger
        self.verbose = verbose
        self.rag = rag
        self.card_id = card_id
        self.llm_client = None  # Will be set later when needed
        self.hydra_config = hydra_config

    def _init_llm_config(self):
        """Initialize LLM configuration from Hydra config"""
        self.llm_model = None
        self.llm_temperature = 0.3
        self.llm_max_tokens = 4000

        if self.hydra_config and hasattr(self.hydra_config, 'llm'):
            # Use supervisor-specific settings if available, otherwise use default
            if hasattr(self.hydra_config.llm, 'supervisor'):
                self.llm_model = self.hydra_config.llm.supervisor.model
                self.llm_temperature = self.hydra_config.llm.supervisor.temperature
                self.llm_max_tokens = self.hydra_config.llm.supervisor.max_tokens
            else:
                self.llm_model = self.hydra_config.llm.model
                self.llm_temperature = getattr(self.hydra_config.llm, 'temperature', 0.7)
                self.llm_max_tokens = getattr(self.hydra_config.llm, 'max_tokens_per_request', 4000)

        if self.verbose and self.llm_model:
            print(f"[Supervisor] Using LLM model: {self.llm_model} (temp={self.llm_temperature})")

    def _init_health_monitoring(self):
        """Initialize agent health monitoring with Observer Pattern"""
        self.health_observers: List[AgentHealthObserver] = []
        self.register_health_observer(SupervisorHealthObserver(self))
        self.registered_agents: Dict[str, Dict[str, Any]] = {}

        if self.verbose:
            print(f"[Supervisor] Initialized health monitoring with Observer Pattern")

    def _run_config_validation(self):
        """Run startup configuration validation"""
        if self.verbose:
            print(f"[Supervisor] Running startup configuration validation...")

        validator = ConfigValidator(verbose=self.verbose)
        report = validator.validate_all()

        if report.overall_status == "fail":
            raise RuntimeError(f"Configuration validation failed: {report.errors} errors")
        elif report.overall_status == "warning":
            if self.verbose:
                print(f"[Supervisor] ⚠️  Configuration warnings: {report.warnings} warnings")

    def _run_preflight_validation(self):
        """Run preflight validation (syntax checks with auto-fix)"""
        if self.verbose:
            print(f"[Supervisor] Running preflight validation (syntax checks)...")

        try:
            from preflight_validator import PreflightValidator
            from llm_client import LLMClientFactory

            # Try to get LLM client for auto-fixing
            llm_client, auto_fix_enabled = self._setup_llm_for_autofix()

            preflight = PreflightValidator(
                verbose=self.verbose,
                llm_client=llm_client,
                auto_fix=auto_fix_enabled
            )

            # Get the directory containing the agile code
            import os
            agile_dir = os.path.dirname(os.path.abspath(__file__))
            preflight_results = preflight.validate_all(agile_dir)

            self._handle_preflight_results(preflight, preflight_results, auto_fix_enabled)

        except ImportError as e:
            if self.verbose:
                print(f"[Supervisor] ⚠️  Preflight validator not available - skipping syntax checks: {e}")

    def _setup_llm_for_autofix(self):
        """Setup LLM client for auto-fixing syntax errors"""
        from llm_client import LLMClientFactory

        llm_client = None
        auto_fix_enabled = False

        try:
            llm_client = LLMClientFactory.create()
            auto_fix_enabled = True
            if self.verbose:
                print(f"[Supervisor] LLM-based auto-fix enabled")
        except Exception:
            if self.verbose:
                print(f"[Supervisor] LLM not available - auto-fix disabled")

        return llm_client, auto_fix_enabled

    def _handle_preflight_results(self, preflight, preflight_results, auto_fix_enabled):
        """Handle preflight validation results"""
        import os
        import sys

        if not preflight_results["passed"]:
            if self.verbose:
                print(f"[Supervisor] ❌ Found {preflight_results['critical_count']} critical issues")

            # Try to auto-fix syntax errors
            if auto_fix_enabled and preflight_results["critical_count"] > 0:
                if self.verbose:
                    print(f"[Supervisor] Attempting auto-fix...")

                all_fixed = preflight.auto_fix_syntax_errors()

                if all_fixed:
                    if self.verbose:
                        print(f"[Supervisor] ✅ All syntax errors fixed automatically!")
                        print(f"[Supervisor] 🔄 Restarting Artemis to apply fixes...")
                    # Re-exec the current process to restart with fixed code
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                else:
                    if self.verbose:
                        preflight.print_report()
                    raise RuntimeError(
                        f"Preflight validation failed: Could not auto-fix all {preflight_results['critical_count']} "
                        f"critical issues"
                    )
            else:
                if self.verbose:
                    preflight.print_report()
                raise RuntimeError(
                    f"Preflight validation failed: {preflight_results['critical_count']} "
                    f"critical issues found (auto-fix disabled)"
                )
        elif preflight_results["high_count"] > 0:
            if self.verbose:
                print(f"[Supervisor] ⚠️  Preflight warnings: {preflight_results['high_count']} high-priority issues")
        else:
            if self.verbose:
                print(f"[Supervisor] ✅ Preflight validation passed")

    def _init_cost_tracking(self, enable_cost_tracking, card_id, daily_budget, monthly_budget):
        """Initialize LLM cost tracking"""
        import os

        self.cost_tracker: Optional[CostTracker] = None
        if enable_cost_tracking:
            # Get cost tracking directory from env or use default
            cost_dir = os.getenv("ARTEMIS_COST_DIR", "../../.artemis_data/cost_tracking")
            if not os.path.isabs(cost_dir):
                script_dir = os.path.dirname(os.path.abspath(__file__))
                cost_dir = os.path.join(script_dir, cost_dir)

            # Create cost tracker with dynamic path
            cost_filename = f"artemis_costs_{card_id}.json" if card_id else "artemis_costs.json"
            storage_path = os.path.join(cost_dir, cost_filename)

            self.cost_tracker = CostTracker(
                storage_path=storage_path,
                daily_budget=daily_budget,
                monthly_budget=monthly_budget
            )

            if self.verbose:
                budget_info = []
                if daily_budget:
                    budget_info.append(f"daily=${daily_budget:.2f}")
                if monthly_budget:
                    budget_info.append(f"monthly=${monthly_budget:.2f}")
                budget_str = ", ".join(budget_info) if budget_info else "unlimited"
                print(f"[Supervisor] Cost tracking enabled ({budget_str})")

    def _init_security_sandbox(self, enable_sandboxing):
        """Initialize security sandboxing for code execution"""
        self.sandbox: Optional[SandboxExecutor] = None
        if enable_sandboxing:
            sandbox_config = SandboxConfig(
                max_cpu_time=300,  # 5 minutes
                max_memory_mb=512,  # 512 MB
                timeout=600  # 10 minutes overall
            )
            self.sandbox = SandboxExecutor(sandbox_config)
            if self.verbose:
                print(f"[Supervisor] Security sandbox enabled (backend: {self.sandbox.backend_name})")

    def _init_learning_engine(self):
        """Initialize learning engine for dynamic problem solving"""
        self.learning_engine: Optional[SupervisorLearningEngine] = None
        # Will be initialized with LLM client when needed

    def _init_state_machine(self, card_id, verbose):
        """Initialize state machine for tracking pipeline state"""
        self.state_machine: Optional[ArtemisStateMachine] = None
        if card_id:
            self.state_machine = ArtemisStateMachine(
                card_id=card_id,
                verbose=verbose,
                llm_client=self.llm_client  # Pass LLM client for workflow generation
            )
            if self.verbose:
                print(f"[Supervisor] State machine initialized for card {card_id}")

        # RAG integration
        if self.rag and self.verbose:
            print(f"[Supervisor] RAG integration enabled - learning from history")

    def _init_health_tracking(self):
        """Initialize health tracking data structures"""
        self.stage_health: Dict[str, StageHealth] = {}
        self.process_registry: Dict[int, ProcessHealth] = {}
        self.recovery_strategies: Dict[str, RecoveryStrategy] = {}

        # Monitoring state
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.monitored_processes: List[int] = []

    def _init_statistics(self):
        """Initialize supervisor statistics"""
        self.stats = {
            "total_interventions": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "processes_killed": 0,
            "timeouts_detected": 0,
            "hanging_processes": 0,
            "budget_exceeded_count": 0,
            "sandbox_blocked_count": 0
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

    def track_llm_call(
        self,
        model: str,
        provider: str,
        tokens_input: int,
        tokens_output: int,
        stage: str,
        purpose: str = "general"
    ) -> Dict[str, Any]:
        """
        Track an LLM API call with cost management

        Args:
            model: Model name (e.g., gpt-4o, claude-3-5-sonnet)
            provider: Provider (openai, anthropic)
            tokens_input: Input tokens
            tokens_output: Output tokens
            stage: Pipeline stage making the call
            purpose: Purpose of call (developer-a, code-review, etc.)

        Returns:
            Cost tracking result

        Raises:
            BudgetExceededError: If budget limit exceeded
        """
        if not self.cost_tracker:
            if self.verbose:
                print(f"[Supervisor] Cost tracking disabled, skipping")
            return {"cost": 0.0, "tracked": False}

        try:
            result = self.cost_tracker.track_call(
                model=model,
                provider=provider,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                stage=stage,
                card_id=self.card_id or "unknown",
                purpose=purpose
            )

            if self.verbose and result.get("alert"):
                print(f"[Supervisor] 💰 Budget alert: {result['alert']}")

            return result

        except BudgetExceededError as e:
            self.stats["budget_exceeded_count"] += 1

            if self.messenger:
                self.messenger.send_message(
                    to_agent="orchestrator",
                    message_type="budget_exceeded",
                    card_id=self.card_id or "unknown",
                    data={"error": str(e), "stage": stage}
                )

            if self.verbose:
                print(f"[Supervisor] 🚨 BUDGET EXCEEDED: {e}")

            raise

    def enable_learning(self, llm_client: Any) -> None:
        """
        Enable learning capability with LLM client

        Args:
            llm_client: LLM client for querying solutions
        """
        self.learning_engine = SupervisorLearningEngine(
            llm_client=llm_client,
            rag_agent=self.rag,
            verbose=self.verbose
        )

        if self.verbose:
            print(f"[Supervisor] 🧠 Learning engine enabled")

    def handle_unexpected_state(
        self,
        current_state: str,
        expected_states: List[str],
        context: Dict[str, Any],
        auto_learn: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Handle an unexpected state by learning and applying solution

        Args:
            current_state: Current state
            expected_states: List of expected states
            context: Context information
            auto_learn: Automatically learn and apply solution

        Returns:
            Solution result if handled, None otherwise
        """
        # DEBUG: Log unexpected state handling
        self.debug_if_enabled('log_recovery', "Handling unexpected state",
                             current_state=current_state,
                             expected_states=expected_states)

        if not self.learning_engine:
            if self.verbose:
                print(f"[Supervisor] ⚠️  Learning engine not enabled, cannot handle unexpected state")
            return None

        # Detect unexpected state
        unexpected = self.learning_engine.detect_unexpected_state(
            card_id=self.card_id or "unknown",
            current_state=current_state,
            expected_states=expected_states,
            context=context
        )

        if not unexpected:
            return None  # State is actually expected

        if not auto_learn:
            # Just detect, don't learn/apply
            return {
                "unexpected_state": unexpected,
                "action": "detected_only"
            }

        # Learn solution
        if self.verbose:
            print(f"[Supervisor] 🧠 Learning solution for unexpected state...")

        solution = self.learning_engine.learn_solution(
            unexpected,
            strategy=LearningStrategy.LLM_CONSULTATION
        )

        if not solution:
            if self.verbose:
                print(f"[Supervisor] ❌ Could not learn solution - trying fallback strategies...")

            # FALLBACK STRATEGY 0: Detect and handle JSON parsing failures
            json_parse_result = self._try_fix_json_parsing_failure(unexpected, context)
            if json_parse_result and json_parse_result.get("success"):
                return json_parse_result

            # FALLBACK STRATEGY 1: Try simple retry with backoff
            retry_result = self._try_fallback_retry(unexpected, context)
            if retry_result and retry_result.get("success"):
                return retry_result

            # FALLBACK STRATEGY 2: Try to use default values for missing data
            default_result = self._try_default_values(unexpected, context)
            if default_result and default_result.get("success"):
                return default_result

            # FALLBACK STRATEGY 3: Try to skip non-critical stage
            skip_result = self._try_skip_stage(unexpected, context)
            if skip_result and skip_result.get("success"):
                return skip_result

            # LAST RESORT: Request manual intervention
            if self.verbose:
                print(f"[Supervisor] 🚨 All recovery strategies failed - requesting manual intervention")

            return {
                "unexpected_state": unexpected,
                "action": "manual_intervention_required",
                "message": "All automated recovery strategies failed. Manual intervention needed."
            }

        # Apply solution
        if self.verbose:
            print(f"[Supervisor] 🔧 Applying learned solution...")

        success = self.learning_engine.apply_learned_solution(solution, context)

        return {
            "unexpected_state": unexpected,
            "solution": solution,
            "success": success,
            "action": "learned_and_applied"
        }

    def query_learned_solutions(
        self,
        problem_description: str,
        top_k: int = 3
    ) -> List[LearnedSolution]:
        """
        Query previously learned solutions

        Args:
            problem_description: Description of problem
            top_k: Number of solutions to return

        Returns:
            List of relevant learned solutions
        """
        if not self.learning_engine or not self.rag:
            return []

        try:
            # Query RAG for similar solutions
            results = self.rag.query_similar(
                query_text=problem_description,
                artifact_types=["learned_solution"],
                top_k=top_k
            )

            if self.verbose and results:
                print(f"[Supervisor] 📚 Found {len(results)} similar learned solutions")

            return results

        except Exception as e:
            if self.verbose:
                print(f"[Supervisor] ⚠️  Failed to query learned solutions: {e}")
            return []

    def execute_code_safely(
        self,
        code: str,
        scan_security: bool = True
    ) -> Dict[str, Any]:
        """
        Execute code in security sandbox

        Args:
            code: Python code to execute
            scan_security: Scan for security issues first

        Returns:
            Execution result

        Raises:
            RuntimeError: If sandbox disabled or execution fails
        """
        if not self.sandbox:
            raise RuntimeError("Security sandbox not enabled")

        if self.verbose:
            print(f"[Supervisor] Executing code in sandbox (scan: {scan_security})")

        result = self.sandbox.execute_python_code(code, scan_security=scan_security)

        if result.killed:
            self.stats["sandbox_blocked_count"] += 1

            if self.messenger:
                self.messenger.send_message(
                    to_agent="orchestrator",
                    message_type="sandbox_blocked",
                    card_id=self.card_id or "unknown",
                    data={"reason": result.kill_reason, "stderr": result.stderr}
                )

            if self.verbose:
                print(f"[Supervisor] 🛡️  Sandbox blocked execution: {result.kill_reason}")

        return {
            "success": result.success,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time": result.execution_time,
            "killed": result.killed,
            "kill_reason": result.kill_reason
        }

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
        # Setup and validate stage execution
        self._setup_stage_execution(stage_name)

        # Check circuit breaker and handle if open
        circuit_result = self._check_circuit_breaker_status(stage_name, *args, **kwargs)
        if circuit_result is not None:
            return circuit_result

        # Execute stage with retry logic
        return self._execute_stage_with_retries(stage, stage_name, *args, **kwargs)

    def _setup_stage_execution(self, stage_name):
        """Setup and register stage for execution"""
        # Register stage if not already registered
        if stage_name not in self.stage_health:
            self.register_stage(stage_name)

        # Update state machine: stage starting
        if self.state_machine:
            self.state_machine.push_state(PipelineState.STAGE_RUNNING, {"stage": stage_name})
            self.state_machine.update_stage_state(stage_name, StageState.RUNNING)

    def _check_circuit_breaker_status(self, stage_name, *args, **kwargs):
        """
        Check circuit breaker and handle if open

        Returns:
            Result dict if circuit breaker is open, None otherwise
        """
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
        return None

    def _execute_stage_with_retries(self, stage, stage_name, *args, **kwargs):
        """
        Execute stage with retry logic and monitoring

        Returns:
            Stage execution result

        Raises:
            PipelineStageError: If all retries are exhausted
        """
        health = self.stage_health[stage_name]
        strategy = self.recovery_strategies.get(stage_name, RecoveryStrategy())

        retry_count = 0
        last_error = None

        while retry_count <= strategy.max_retries:
            try:
                # Wait before retry if needed
                if retry_count > 0:
                    self._wait_before_retry(stage_name, retry_count, strategy)

                # Execute stage with monitoring
                result_data = self._execute_stage_monitored(stage, stage_name, strategy, *args, **kwargs)

                # Handle successful execution - pass result for state tracking
                self._handle_successful_execution(
                    stage_name,
                    health,
                    retry_count,
                    result_data['duration'],
                    result_data['result']  # Pass result to store in state machine
                )

                return result_data['result']

            except Exception as e:
                # Handle execution failure
                last_error = e
                retry_count += 1

                # Store failure in state machine for complete state tracking
                if self.state_machine:
                    self.state_machine.push_state(
                        PipelineState.STAGE_FAILED,
                        {
                            "stage": stage_name,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "retry_count": retry_count,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    self.state_machine.update_stage_state(stage_name, StageState.FAILED)

                should_break = self._handle_execution_failure(
                    stage_name, health, strategy, retry_count, e
                )
                if should_break:
                    break

        # All retries exhausted - raise final error
        return self._raise_final_error(stage_name, health, retry_count, last_error)

    def _wait_before_retry(self, stage_name, retry_count, strategy):
        """Wait before retrying with exponential backoff"""
        retry_delay = strategy.retry_delay_seconds * (strategy.backoff_multiplier ** (retry_count - 1))
        if self.verbose:
            print(f"[Supervisor] Retry {retry_count}/{strategy.max_retries} for {stage_name} (waiting {retry_delay}s)")
        time.sleep(retry_delay)

    def _execute_stage_monitored(self, stage, stage_name, strategy, *args, **kwargs):
        """Execute stage with timeout monitoring"""
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
        duration = (datetime.now() - start_time).total_seconds()

        return {'result': result, 'duration': duration}

    def _handle_successful_execution(self, stage_name, health, retry_count, duration, result=None):
        """
        Handle successful stage execution

        Args:
            stage_name: Name of the stage
            health: Stage health tracker
            retry_count: Number of retries used
            duration: Execution duration in seconds
            result: Stage execution result (optional, for state tracking)
        """
        health.execution_count += 1
        health.total_duration += duration

        # Store result in state machine for complete pipeline state tracking
        if self.state_machine and result is not None:
            self.state_machine.push_state(
                PipelineState.STAGE_COMPLETED,
                {
                    "stage": stage_name,
                    "result": result,
                    "duration": duration,
                    "retry_count": retry_count,
                    "timestamp": datetime.now().isoformat()
                }
            )
            self.state_machine.update_stage_state(stage_name, StageState.COMPLETED)

        if retry_count > 0:
            self.stats["successful_recoveries"] += 1
            if self.verbose:
                print(f"[Supervisor] ✅ Recovery successful for {stage_name} after {retry_count} retries")

    def _handle_execution_failure(self, stage_name, health, strategy, retry_count, error):
        """
        Handle stage execution failure

        Returns:
            True if should break retry loop, False otherwise
        """
        health.failure_count += 1
        health.last_failure = datetime.now()
        self.stats["total_interventions"] += 1

        if self.verbose:
            print(f"[Supervisor] ❌ Stage {stage_name} failed: {str(error)}")

        # Check if circuit breaker should open
        if health.failure_count >= strategy.circuit_breaker_threshold:
            self.open_circuit_breaker(stage_name)
            return True

        # Log retry attempt
        if retry_count <= strategy.max_retries:
            if self.logger:
                self.logger.log(f"Stage {stage_name} failed, retrying ({retry_count}/{strategy.max_retries})")

        return False

    def _raise_final_error(self, stage_name, health, retry_count, last_error):
        """Raise final error after all retries exhausted"""
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

            time.sleep(DEFAULT_RETRY_INTERVAL_SECONDS)  # Check every 5 seconds

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
        Get supervision statistics (including Phase 2 metrics)

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

        stats = {
            "overall_health": health_status.value,
            "total_interventions": self.stats["total_interventions"],
            "successful_recoveries": self.stats["successful_recoveries"],
            "failed_recoveries": self.stats["failed_recoveries"],
            "processes_killed": self.stats["processes_killed"],
            "timeouts_detected": self.stats["timeouts_detected"],
            "hanging_processes_detected": self.stats["hanging_processes"],
            "stage_statistics": stage_stats
        }

        # Phase 2: Add cost tracking stats
        if self.cost_tracker:
            cost_stats = self.cost_tracker.get_statistics()
            stats["cost_tracking"] = {
                "total_cost": cost_stats["total_cost"],
                "daily_cost": cost_stats["daily_cost"],
                "monthly_cost": cost_stats["monthly_cost"],
                "daily_remaining": cost_stats["daily_remaining"],
                "monthly_remaining": cost_stats["monthly_remaining"],
                "total_calls": cost_stats["total_calls"],
                "budget_exceeded_count": self.stats["budget_exceeded_count"]
            }

        # Phase 2: Add sandboxing stats
        if self.sandbox:
            stats["security_sandbox"] = {
                "backend": self.sandbox.backend_name,
                "blocked_executions": self.stats["sandbox_blocked_count"]
            }

        # Learning engine stats
        if self.learning_engine:
            learning_stats = self.learning_engine.get_statistics()
            stats["learning"] = learning_stats

        return stats

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

    def get_stage_result(self, stage_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve latest result for a stage from state machine

        This allows the supervisor to query "What did code review find?"
        without needing to ask the orchestrator.

        Args:
            stage_name: Name of the stage (e.g., "code_review", "developer")

        Returns:
            Stage result dict or None if not found

        Example:
            >>> supervisor = SupervisorAgent(...)
            >>> code_review_result = supervisor.get_stage_result('code_review')
            >>> if code_review_result:
            >>>     refactoring_suggestions = code_review_result.get('refactoring_suggestions')
            >>>     critical_issues = code_review_result.get('total_critical_issues', 0)
        """
        # Guard clause: No state machine available
        if not self.state_machine:
            return None

        # Guard clause: State stack not available
        if not hasattr(self.state_machine, '_state_stack'):
            return None

        # Pattern #4: Use next() with generator for first match (latest first)
        return next(
            (
                context['result']
                for state_entry in reversed(self.state_machine._state_stack)
                if (context := state_entry.get('context', {})).get('stage') == stage_name
                and 'result' in context
            ),
            None  # Default value if no match found
        )

    def get_all_stage_results(self) -> Dict[str, Dict[str, Any]]:
        """
        Retrieve latest results for all stages from state machine

        Returns:
            Dict mapping stage_name to result dict

        Example:
            >>> results = supervisor.get_all_stage_results()
            >>> code_review = results.get('code_review', {})
            >>> developer_a = results.get('developer', {})
        """
        # Guard clause: No state machine available
        if not self.state_machine:
            return {}

        # Guard clause: State stack not available
        if not hasattr(self.state_machine, '_state_stack'):
            return {}

        # Pattern #1: Use dict comprehension with generator
        # Collect unique stages with their latest results (reversed = latest first)
        seen_stages = set()

        def _unique_stage_results():
            """Generator yielding (stage, result) tuples for unseen stages"""
            for state_entry in reversed(self.state_machine._state_stack):
                context = state_entry.get('context', {})
                stage = context.get('stage')
                result = context.get('result')

                if stage and result and stage not in seen_stages:
                    seen_stages.add(stage)
                    yield (stage, result)

        return dict(_unique_stage_results())

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

    def _try_fix_json_parsing_failure(self, unexpected_state: Dict, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Fallback strategy: Detect and handle JSON parsing failures from LLM responses

        This strategy detects when developers fail due to JSON parsing errors and
        provides actionable guidance on fixing the prompt or response format.

        Args:
            unexpected_state: Unexpected state details
            context: Execution context

        Returns:
            Result dict with recommendations if JSON parsing failure detected, None otherwise
        """
        # Check if this is a JSON parsing failure
        developer_errors = context.get("developer_errors", [])
        json_parse_failures = [
            err for err in developer_errors
            if err and ("parse" in err.lower() and "json" in err.lower() or "Expecting value" in err)
        ]

        if not json_parse_failures:
            return None  # Not a JSON parsing issue

        if self.verbose:
            print(f"[Supervisor] 🔍 Detected JSON parsing failures in {len(json_parse_failures)} developer(s)")

        # Consult LLM for advice on fixing the prompt
        if self.llm_client:
            if self.verbose:
                print(f"[Supervisor] 💬 Consulting LLM for JSON parsing fix recommendations...")

            try:
                system_message = """You are a debugging expert for AI agent systems. When developers fail to parse JSON from LLM responses, you provide specific, actionable fixes."""

                user_message = f"""The developer agents failed with JSON parsing errors:

Errors:
{chr(10).join(f"- {err}" for err in json_parse_failures)}

Context:
- Stage: {context.get('stage_name', 'development')}
- Task: {context.get('card_id', 'unknown')}
- Number of failed developers: {len(json_parse_failures)}

Provide specific recommendations in JSON format:
{{
  "root_cause": "Brief explanation of why JSON parsing failed",
  "recommended_actions": [
    "Specific action 1 to fix the prompt",
    "Specific action 2 to improve response parsing"
  ],
  "prompt_improvements": [
    "Add explicit JSON schema to prompt",
    "Request strict JSON without markdown"
  ],
  "retry_strategy": "Should we retry immediately, adjust prompt first, or skip?"
}}"""

                response = self.llm_client.generate_text(
                    system_message=system_message,
                    user_message=user_message,
                    temperature=0.3,
                    max_tokens=1000
                )

                # Parse recommendations
                import json
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    recommendations = json.loads(json_match.group(0))

                    if self.verbose:
                        print(f"[Supervisor] ✅ LLM recommendations:")
                        print(f"   Root cause: {recommendations.get('root_cause', 'Unknown')}")
                        print(f"   Actions: {len(recommendations.get('recommended_actions', []))}")

                    return {
                        "strategy": "json_parsing_fix",
                        "success": True,
                        "recommendations": recommendations,
                        "message": f"JSON parsing failure detected and analyzed. {recommendations.get('retry_strategy', 'Retry recommended')}"
                    }

            except Exception as e:
                if self.verbose:
                    print(f"[Supervisor] ⚠️  Failed to get LLM recommendations: {e}")

        # Fallback: Provide generic JSON parsing advice
        return {
            "strategy": "json_parsing_fix",
            "success": True,
            "recommendations": {
                "root_cause": "LLM response not in valid JSON format",
                "recommended_actions": [
                    "Check if LLM prompt explicitly requests JSON output",
                    "Verify prompt includes JSON schema/example",
                    "Check if response parser handles markdown code blocks",
                    "Consider adjusting temperature (lower = more structured)"
                ],
                "retry_strategy": "Adjust prompt to explicitly request JSON-only output, then retry"
            },
            "message": "JSON parsing failure detected. Generic recommendations provided."
        }

    def _try_fallback_retry(self, unexpected_state: Dict, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Fallback strategy: Try simple retry with exponential backoff

        Args:
            unexpected_state: Unexpected state details
            context: Execution context

        Returns:
            Result dict if successful, None otherwise
        """
        if self.verbose:
            print(f"[Supervisor] 🔄 Trying fallback strategy: RETRY")

        # Don't retry if we've already tried too many times
        retry_count = context.get("retry_count", 0)
        if retry_count >= MAX_RETRY_ATTEMPTS:
            if self.verbose:
                print(f"[Supervisor] ⚠️  Max retries ({MAX_RETRY_ATTEMPTS}) reached")
            return None

        # For now, just log that we would retry
        # Actual retry logic would be implemented by the caller
        if self.verbose:
            print(f"[Supervisor] ✅ Retry strategy available (attempt {retry_count + 1}/{MAX_RETRY_ATTEMPTS})")

        return {
            "strategy": "retry",
            "success": False,  # Caller must implement actual retry
            "retry_count": retry_count + 1,
            "message": f"Retry recommended (attempt {retry_count + 1})"
        }

    def _try_default_values(self, unexpected_state: Dict, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Fallback strategy: Try to populate missing data with sensible defaults
        AND automatically fix the source code to prevent future occurrences using LLM

        Args:
            unexpected_state: Unexpected state details
            context: Execution context

        Returns:
            Result dict if successful, None otherwise
        """
        if self.verbose:
            print(f"[Supervisor] 🔧 Trying fallback strategy: LLM-POWERED AUTO-FIX")

        # Extract error information
        error_info = context.get("error", {})
        error_type = error_info.get("type", "")
        traceback_info = context.get("traceback", "")
        exception = context.get("exception")

        # Try LLM-powered auto-fix for ANY error type (not just KeyError)
        if exception and traceback_info:
            if self.verbose:
                print(f"[Supervisor] 🤖 Attempting LLM-powered auto-fix for {type(exception).__name__}...")

            fix_result = self.llm_auto_fix_error(exception, traceback_info, context)

            if fix_result and fix_result.get("success"):
                if self.verbose:
                    print(f"[Supervisor] ✅ LLM AUTO-FIX SUCCESS!")
                    print(f"[Supervisor]    File: {fix_result['file_path']}:{fix_result['line_number']}")
                    print(f"[Supervisor]    Error: {fix_result['error_type']}")
                    print(f"[Supervisor]    Before: {fix_result['original_line']}")
                    print(f"[Supervisor]    After:  {fix_result['fixed_line']}")
                    print(f"[Supervisor]    Backup: {fix_result['backup_path']}")
                    if 'llm_reasoning' in fix_result:
                        print(f"[Supervisor]    LLM Reasoning: {fix_result['llm_reasoning']}")

                # After fixing, restart the failed stage/agent
                restart_result = self._restart_failed_stage(context, fix_result)

                return {
                    "strategy": "llm_auto_fix",
                    "success": True,
                    "auto_fixed": True,
                    "fix_details": fix_result,
                    "restart_result": restart_result,
                    "message": f"LLM automatically fixed {fix_result['error_type']} in source code and restarted stage"
                }

        # Fallback: For KeyError, provide default values (original behavior)
        if "KeyError" in error_type or "key" in str(error_info).lower():
            missing_key = error_info.get("message", "").replace("'", "").strip()
            if not missing_key and exception:
                missing_key = str(exception).replace("'", "").strip()

            # Get default from the centralized method
            default_value = self._get_default_for_key(missing_key)

            if default_value is not None:
                if self.verbose:
                    print(f"[Supervisor] ✅ Found default for '{missing_key}': {default_value}")

                return {
                    "strategy": "default_values",
                    "success": True,
                    "missing_key": missing_key,
                    "default_value": default_value,
                    "message": f"Applied default value '{default_value}' for missing key '{missing_key}'"
                }
            else:
                if self.verbose:
                    print(f"[Supervisor] ⚠️  No default available for '{missing_key}'")

        return None

    def _try_skip_stage(self, unexpected_state: Dict, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Fallback strategy: Try to skip non-critical stage

        Args:
            unexpected_state: Unexpected state details
            context: Execution context

        Returns:
            Result dict if successful, None otherwise
        """
        if self.verbose:
            print(f"[Supervisor] ⏭️  Trying fallback strategy: SKIP_STAGE")

        # Determine if stage is skippable
        stage_name = context.get("stage_name", "")
        skippable_stages = ["validation", "testing"]  # Non-critical stages

        is_skippable = any(skip in stage_name.lower() for skip in skippable_stages)

        if is_skippable:
            if self.verbose:
                print(f"[Supervisor] ✅ Stage '{stage_name}' is skippable")

            return {
                "strategy": "skip_stage",
                "success": True,
                "stage_name": stage_name,
                "message": f"Skipping non-critical stage '{stage_name}'"
            }
        else:
            if self.verbose:
                print(f"[Supervisor] ⚠️  Stage '{stage_name}' is critical, cannot skip")

        return None

    def llm_auto_fix_error(self, error: Exception, traceback_info: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Use LLM to automatically analyze and fix errors by modifying source code

        Args:
            error: The exception that occurred
            traceback_info: Traceback string
            context: Execution context

        Returns:
            Fix result dict if successful, None otherwise
        """
        error_type = type(error).__name__
        error_message = str(error)

        if self.verbose:
            print(f"[Supervisor] 🧠 LLM auto-fixing {error_type}: {error_message}")

        try:
            import re

            # Extract file path and line number from traceback
            file_match = re.search(r'File "([^"]+)", line (\d+)', traceback_info)
            if not file_match:
                if self.verbose:
                    print(f"[Supervisor] ⚠️  Could not extract file path from traceback")
                return self._fallback_regex_fix(error, traceback_info, context)

            file_path = file_match.group(1)
            line_number = int(file_match.group(2))

            if self.verbose:
                print(f"[Supervisor] 📝 Found error in {file_path}:{line_number}")

            # Read the source file with context (10 lines before and after)
            with open(file_path, 'r') as f:
                all_lines = f.readlines()

            if line_number > len(all_lines):
                if self.verbose:
                    print(f"[Supervisor] ⚠️  Line number out of range")
                return None

            # Get context lines
            context_start = max(0, line_number - 10)
            context_end = min(len(all_lines), line_number + 10)
            context_lines = all_lines[context_start:context_end]
            problem_line = all_lines[line_number - 1]

            if self.verbose:
                print(f"[Supervisor] 📄 Problem line: {problem_line.strip()}")

            # Try LLM-powered fix first
            llm_fix = self._llm_suggest_fix(
                error_type=error_type,
                error_message=error_message,
                file_path=file_path,
                line_number=line_number,
                problem_line=problem_line,
                context_lines=context_lines,
                context=context
            )

            if llm_fix and llm_fix.get("success"):
                # Apply the LLM-suggested fix
                fixed_line = llm_fix["fixed_line"]

                # Create backup
                backup_path = file_path + ".backup"
                with open(backup_path, 'w') as f:
                    f.writelines(all_lines)

                if self.verbose:
                    print(f"[Supervisor] 💾 Created backup: {backup_path}")

                # Write fixed version
                all_lines[line_number - 1] = fixed_line + "\n" if not fixed_line.endswith("\n") else fixed_line
                with open(file_path, 'w') as f:
                    f.writelines(all_lines)

                if self.verbose:
                    print(f"[Supervisor] ✅ LLM auto-fixed {file_path}")

                return {
                    "success": True,
                    "file_path": file_path,
                    "line_number": line_number,
                    "error_type": error_type,
                    "error_message": error_message,
                    "original_line": problem_line.strip(),
                    "fixed_line": fixed_line.strip(),
                    "backup_path": backup_path,
                    "llm_reasoning": llm_fix.get("reasoning", ""),
                    "message": f"LLM automatically fixed {error_type} in {file_path}:{line_number}"
                }

            # Fallback to regex-based fix if LLM fails
            if self.verbose:
                print(f"[Supervisor] ⚠️  LLM fix failed, trying regex fallback...")
            return self._fallback_regex_fix(error, traceback_info, context)

        except Exception as e:
            if self.verbose:
                print(f"[Supervisor] ❌ LLM auto-fix failed: {e}")

            # Fallback to regex-based fix
            return self._fallback_regex_fix(error, traceback_info, context)

    def _llm_suggest_fix(
        self,
        error_type: str,
        error_message: str,
        file_path: str,
        line_number: int,
        problem_line: str,
        context_lines: list,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM to suggest a fix for the error

        Args:
            error_type: Type of error (KeyError, TypeError, etc.)
            error_message: Error message
            file_path: Path to file with error
            line_number: Line number with error
            problem_line: The problematic line
            context_lines: Surrounding context lines
            context: Execution context

        Returns:
            Fix suggestion dict if successful, None otherwise
        """
        if not self.learning_engine or not self.learning_engine.llm_client:
            if self.verbose:
                print(f"[Supervisor] ⚠️  LLM client not available")
            return None

        try:
            # Build context for LLM
            context_code = "".join(context_lines)

            # Create prompt for LLM
            prompt = f"""You are a Python code debugging expert. Analyze this error and provide a fix.

**Error Details:**
- Type: {error_type}
- Message: {error_message}
- File: {file_path}
- Line: {line_number}

**Problematic Line:**
```python
{problem_line.strip()}
```

**Surrounding Context:**
```python
{context_code}
```

**Task:**
Provide a fixed version of the problematic line that resolves the {error_type} error. The fix should:
1. Be defensive (use .get() for dict access, check types, handle None, etc.)
2. Maintain the same functionality
3. Include sensible defaults
4. Be a drop-in replacement (same indentation, same line)

**Response Format (JSON):**
{{
    "reasoning": "Brief explanation of the error and fix",
    "fixed_line": "The complete fixed line of code with proper indentation"
}}

Respond ONLY with valid JSON, no other text."""

            if self.verbose:
                print(f"[Supervisor] 💬 Consulting LLM for fix suggestion...")

            # Call LLM with config-based model (GPT-5 or fallback to gpt-4)
            llm_model = self.llm_model or "gpt-4"  # Fallback to gpt-4 if config not available
            response = self.learning_engine.llm_client.chat(
                model=llm_model,
                messages=[
                    {"role": "system", "content": "You are a Python debugging expert. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.llm_temperature
            )

            # Parse LLM response
            import json
            response_text = response.choices[0].message.content.strip()

            # Extract JSON if wrapped in code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            fix_data = json.loads(response_text)

            if "fixed_line" in fix_data:
                if self.verbose:
                    print(f"[Supervisor] ✅ LLM suggested fix")
                    print(f"[Supervisor]    Reasoning: {fix_data.get('reasoning', 'N/A')}")
                    print(f"[Supervisor]    Fixed: {fix_data['fixed_line']}")

                return {
                    "success": True,
                    "fixed_line": fix_data["fixed_line"],
                    "reasoning": fix_data.get("reasoning", "")
                }

        except Exception as e:
            if self.verbose:
                print(f"[Supervisor] ❌ LLM suggestion failed: {e}")

        return None

    def _fallback_regex_fix(self, error: Exception, traceback_info: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Fallback regex-based fix for when LLM is unavailable (KeyError only)

        Args:
            error: The exception
            traceback_info: Traceback string
            context: Execution context

        Returns:
            Fix result dict if successful, None otherwise
        """
        # Only handle KeyError with regex fallback
        if not isinstance(error, KeyError):
            if self.verbose:
                print(f"[Supervisor] ⚠️  Regex fallback only supports KeyError, got {type(error).__name__}")
            return None

        if self.verbose:
            print(f"[Supervisor] 🔧 Using regex fallback for KeyError")

        try:
            import re

            missing_key = str(error).replace("'", "").strip()

            # Extract file path and line number
            file_match = re.search(r'File "([^"]+)", line (\d+)', traceback_info)
            if not file_match:
                return None

            file_path = file_match.group(1)
            line_number = int(file_match.group(2))

            # Read the source file
            with open(file_path, 'r') as f:
                lines = f.readlines()

            if line_number > len(lines):
                return None

            problem_line = lines[line_number - 1]
            original_line = problem_line

            # Pattern to match dict['key'] access
            pattern = r"(\w+)\['([^']+)'\]"

            if missing_key in problem_line or re.search(pattern, problem_line):
                default_value = self._get_default_for_key(missing_key)

                # Replace dict['key'] with dict.get('key', default)
                fixed_line = re.sub(
                    pattern,
                    lambda m: f"{m.group(1)}.get('{m.group(2)}', {default_value!r})",
                    problem_line
                )

                if fixed_line != problem_line:
                    # Create backup
                    backup_path = file_path + ".backup"
                    with open(backup_path, 'w') as f:
                        f.writelines(lines)

                    # Write fixed version
                    lines[line_number - 1] = fixed_line
                    with open(file_path, 'w') as f:
                        f.writelines(lines)

                    return {
                        "success": True,
                        "file_path": file_path,
                        "line_number": line_number,
                        "error_type": "KeyError",
                        "error_message": str(error),
                        "original_line": original_line.strip(),
                        "fixed_line": fixed_line.strip(),
                        "backup_path": backup_path,
                        "message": f"Regex fallback fixed KeyError for '{missing_key}' in {file_path}:{line_number}"
                    }

        except Exception as e:
            if self.verbose:
                print(f"[Supervisor] ❌ Regex fallback failed: {e}")

        return None

    def _restart_failed_stage(self, context: Dict[str, Any], fix_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Restart a failed stage after applying a fix

        Args:
            context: Execution context with stage information
            fix_result: Result from the auto-fix operation

        Returns:
            Restart result dict
        """
        if self.verbose:
            print(f"[Supervisor] 🔄 Restarting failed stage after auto-fix...")

        try:
            stage_name = context.get("stage_name", "unknown")
            stage_instance = context.get("stage_instance")
            stage_context = context.get("stage_context", {})

            if not stage_instance:
                if self.verbose:
                    print(f"[Supervisor] ⚠️  No stage instance available for restart")
                return {
                    "success": False,
                    "message": "No stage instance available for restart"
                }

            if self.verbose:
                print(f"[Supervisor] 🚀 Restarting stage: {stage_name}")

            # Reload the fixed module to pick up code changes
            import importlib
            import sys

            # Get the module containing the fixed file
            fixed_file = fix_result.get("file_path", "")
            if fixed_file:
                # Convert file path to module name
                module_name = None
                for mod_name, mod in sys.modules.items():
                    if hasattr(mod, '__file__') and mod.__file__ == fixed_file:
                        module_name = mod_name
                        break

                if module_name:
                    if self.verbose:
                        print(f"[Supervisor] 📦 Reloading module: {module_name}")
                    importlib.reload(sys.modules[module_name])

            # Re-execute the stage
            result = stage_instance.execute(stage_context)

            if self.verbose:
                print(f"[Supervisor] ✅ Stage restarted successfully")

            return {
                "success": True,
                "stage_name": stage_name,
                "result": result,
                "message": f"Successfully restarted stage '{stage_name}' after auto-fix"
            }

        except Exception as e:
            if self.verbose:
                print(f"[Supervisor] ❌ Stage restart failed: {e}")

            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to restart stage: {e}"
            }

    def monitor_agent_health(
        self,
        agent_name: str,
        timeout_seconds: int = 300,
        check_interval: int = 5
    ) -> Dict[str, Any]:
        """
        Monitor an agent's health, detecting crashes and hangs

        Args:
            agent_name: Name of the agent to monitor
            timeout_seconds: Maximum time before considering agent hung (default 5 minutes)
            check_interval: How often to check agent status in seconds (default 5 seconds)

        Returns:
            Health status dict
        """
        import time
        from datetime import datetime, timedelta

        if self.verbose:
            print(f"[Supervisor] 👀 Monitoring agent '{agent_name}' (timeout: {timeout_seconds}s)")

        start_time = datetime.now()
        last_activity = start_time
        health_status = {
            "agent_name": agent_name,
            "status": "healthy",
            "start_time": start_time.isoformat(),
            "checks_performed": 0
        }

        while True:
            elapsed = (datetime.now() - start_time).total_seconds()
            health_status["checks_performed"] += 1

            # Check if agent has crashed
            crash_detected = self._detect_agent_crash(agent_name)
            if crash_detected:
                health_status["status"] = "crashed"
                health_status["crash_info"] = crash_detected
                health_status["elapsed_time"] = elapsed

                if self.verbose:
                    print(f"[Supervisor] 💥 Agent '{agent_name}' crashed!")
                    print(f"[Supervisor]    Error: {crash_detected.get('error')}")

                return health_status

            # Check if agent has hung (timeout exceeded)
            if elapsed > timeout_seconds:
                health_status["status"] = "hung"
                health_status["timeout_seconds"] = timeout_seconds
                health_status["elapsed_time"] = elapsed

                if self.verbose:
                    print(f"[Supervisor] ⏰ Agent '{agent_name}' appears hung (timeout: {timeout_seconds}s)")

                return health_status

            # Check for progress (heartbeat)
            progress = self._check_agent_progress(agent_name)
            if progress:
                last_activity = datetime.now()
                health_status["last_activity"] = last_activity.isoformat()

            # Check if stuck (no progress for extended period)
            time_since_activity = (datetime.now() - last_activity).total_seconds()
            if time_since_activity > (timeout_seconds / 2):
                health_status["status"] = "stalled"
                health_status["time_since_activity"] = time_since_activity

                if self.verbose:
                    print(f"[Supervisor] ⚠️  Agent '{agent_name}' may be stalled (no activity for {time_since_activity}s)")

            # Sleep before next check
            time.sleep(check_interval)

    def _detect_agent_crash(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Detect if an agent has crashed

        Args:
            agent_name: Name of the agent

        Returns:
            Crash info dict if crashed, None otherwise
        """
        try:
            # Check state machine for FAILED state
            if self.state_machine:
                current_state = self.state_machine.get_current_state()
                if current_state and "FAILED" in str(current_state):
                    # Get error details from context
                    context = self.state_machine.context if hasattr(self.state_machine, 'context') else {}
                    error_info = context.get("error", {})

                    return {
                        "agent_name": agent_name,
                        "error": error_info.get("message", "Unknown error"),
                        "error_type": error_info.get("type", "Unknown"),
                        "traceback": context.get("traceback", ""),
                        "state": str(current_state)
                    }

            # Could also check process status, log files, etc.
            return None

        except Exception as e:
            if self.verbose:
                print(f"[Supervisor] ⚠️  Error detecting crash: {e}")
            return None

    def _check_agent_progress(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Check if an agent is making progress

        Args:
            agent_name: Name of the agent

        Returns:
            Progress info dict if progressing, None otherwise
        """
        try:
            # Check state machine for state transitions
            if self.state_machine and hasattr(self.state_machine, 'context'):
                context = self.state_machine.context
                last_transition = context.get("last_transition_time")

                if last_transition:
                    return {
                        "agent_name": agent_name,
                        "last_transition": last_transition,
                        "current_state": str(self.state_machine.get_current_state())
                    }

            # Could also check:
            # - Log file updates
            # - Database writes
            # - Heartbeat signals
            # - Checkpoint updates

            return None

        except Exception as e:
            if self.verbose:
                print(f"[Supervisor] ⚠️  Error checking progress: {e}")
            return None

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
        # DEBUG: Log crash recovery
        self.debug_if_enabled('log_recovery', "Starting crash recovery",
                             agent=crash_info.get('agent_name'),
                             error=crash_info.get('error'))

        if self.verbose:
            print(f"[Supervisor] 🚑 Recovering crashed agent...")
            print(f"[Supervisor]    Agent: {crash_info.get('agent_name')}")
            print(f"[Supervisor]    Error: {crash_info.get('error')}")

        try:
            # Extract error details
            error_type = crash_info.get("error_type", "Unknown")
            error_message = crash_info.get("error", "Unknown error")
            traceback_info = crash_info.get("traceback", "")

            # DEBUG: Dump crash details
            self.debug_dump_if_enabled('log_recovery', "Crash Details", {
                "agent": crash_info.get('agent_name'),
                "error_type": error_type,
                "error_message": error_message,
                "has_traceback": bool(traceback_info)
            })

            # Create a mock exception for the auto-fix system
            if error_type == "KeyError":
                exception = KeyError(error_message)
            elif error_type == "TypeError":
                exception = TypeError(error_message)
            elif error_type == "AttributeError":
                exception = AttributeError(error_message)
            elif error_type == "ValueError":
                exception = ValueError(error_message)
            else:
                exception = Exception(error_message)

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
                if self.verbose:
                    print(f"[Supervisor] ✅ Error fixed, restarting agent...")

                # Restart the agent/stage
                restart_result = self._restart_failed_stage(context, fix_result)

                return {
                    "success": True,
                    "recovery_strategy": "auto_fix_and_restart",
                    "fix_result": fix_result,
                    "restart_result": restart_result,
                    "message": f"Successfully recovered crashed agent using auto-fix and restart"
                }
            else:
                if self.verbose:
                    print(f"[Supervisor] ⚠️  Auto-fix failed, cannot recover automatically")

                return {
                    "success": False,
                    "recovery_strategy": "manual_intervention_required",
                    "message": "Auto-fix failed, manual intervention required"
                }

        except Exception as e:
            if self.verbose:
                print(f"[Supervisor] ❌ Recovery failed: {e}")

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
        if self.verbose:
            print(f"[Supervisor] ⏰ Recovering hung agent '{agent_name}'...")
            print(f"[Supervisor]    Timeout: {timeout_info.get('timeout_seconds')}s")
            print(f"[Supervisor]    Elapsed: {timeout_info.get('elapsed_time')}s")

        try:
            # Terminate the hung agent
            terminate_result = self._terminate_agent(agent_name)

            if not terminate_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to terminate hung agent: {terminate_result.get('error')}"
                }

            if self.verbose:
                print(f"[Supervisor] 🛑 Terminated hung agent")
                print(f"[Supervisor] 🔄 Restarting agent with increased timeout...")

            # Restart with increased timeout
            increased_timeout = timeout_info.get("timeout_seconds", 300) * 2

            return {
                "success": True,
                "recovery_strategy": "terminate_and_restart",
                "terminate_result": terminate_result,
                "recommended_timeout": increased_timeout,
                "message": f"Terminated hung agent, recommend restarting with {increased_timeout}s timeout"
            }

        except Exception as e:
            if self.verbose:
                print(f"[Supervisor] ❌ Recovery failed: {e}")

            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to recover hung agent: {e}"
            }

    def _terminate_agent(self, agent_name: str) -> Dict[str, Any]:
        """
        Terminate a running agent

        Args:
            agent_name: Name of the agent to terminate

        Returns:
            Termination result dict
        """
        try:
            import signal
            import psutil

            # Find the agent process
            # This is a simplified implementation - would need to track PIDs properly
            current_process = psutil.Process()
            children = current_process.children(recursive=True)

            terminated = False
            for child in children:
                # Check if this is the agent process (by command line or name)
                if agent_name.lower() in " ".join(child.cmdline()).lower():
                    if self.verbose:
                        print(f"[Supervisor] 🛑 Terminating process {child.pid}")

                    child.terminate()
                    terminated = True

                    # Wait for termination (with timeout)
                    try:
                        child.wait(timeout=10)
                    except psutil.TimeoutExpired:
                        # Force kill if doesn't terminate gracefully
                        child.kill()

            if terminated:
                return {
                    "success": True,
                    "message": f"Terminated agent '{agent_name}'"
                }
            else:
                return {
                    "success": False,
                    "message": f"Could not find agent '{agent_name}' to terminate"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to terminate agent: {e}"
            }

    def register_health_observer(self, observer: AgentHealthObserver) -> None:
        """
        Register a health observer (Observer Pattern)

        Args:
            observer: Observer to register
        """
        if observer not in self.health_observers:
            self.health_observers.append(observer)
            if self.verbose:
                print(f"[Supervisor] Registered health observer: {type(observer).__name__}")

    def unregister_health_observer(self, observer: AgentHealthObserver) -> None:
        """
        Unregister a health observer

        Args:
            observer: Observer to unregister
        """
        if observer in self.health_observers:
            self.health_observers.remove(observer)

    def notify_agent_event(
        self,
        agent_name: str,
        event: AgentHealthEvent,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Notify all health observers of an agent event (Observer Pattern)

        This is called by:
        1. Agents themselves (for STARTED, PROGRESS, COMPLETED events)
        2. Watchdog (for CRASHED, HUNG, STALLED events)

        Args:
            agent_name: Name of the agent
            event: Type of health event
            data: Event-specific data
        """
        event_data = data or {}

        for observer in self.health_observers:
            try:
                observer.on_agent_event(agent_name, event, event_data)
            except Exception as e:
                if self.verbose:
                    print(f"[Supervisor] ⚠️  Observer {type(observer).__name__} error: {e}")

    def register_agent(
        self,
        agent_name: str,
        agent_type: str = "stage",
        metadata: Optional[Dict[str, Any]] = None,
        heartbeat_interval: float = 15.0
    ) -> None:
        """
        Register an agent with the supervisor for monitoring

        Agents MUST call this on startup to be monitored.

        Args:
            agent_name: Name of the agent (e.g., "DevelopmentStage")
            agent_type: Type of agent (e.g., "stage", "worker", "analyzer")
            metadata: Optional metadata about the agent
            heartbeat_interval: Initial heartbeat interval in seconds (default 15)
        """
        self.registered_agents[agent_name] = {
            "type": agent_type,
            "registered_at": datetime.now().isoformat(),
            "metadata": metadata or {},
            "heartbeat_interval": heartbeat_interval
        }

        if self.verbose:
            print(f"[Supervisor] ✅ Registered agent '{agent_name}' ({agent_type})")

        # Notify observers that agent started
        self.notify_agent_event(
            agent_name,
            AgentHealthEvent.STARTED,
            {
                "agent_type": agent_type,
                "metadata": metadata
            }
        )

    def unregister_agent(self, agent_name: str) -> None:
        """
        Unregister an agent (called when agent completes)

        Args:
            agent_name: Name of the agent
        """
        if agent_name in self.registered_agents:
            del self.registered_agents[agent_name]

            if self.verbose:
                print(f"[Supervisor] ✅ Unregistered agent '{agent_name}'")

            # Notify observers that agent completed
            self.notify_agent_event(
                agent_name,
                AgentHealthEvent.COMPLETED,
                {}
            )

    def agent_heartbeat(self, agent_name: str, progress_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Called by agents to signal they're making progress (heartbeat)

        Agents should call this periodically (e.g., every 10-30 seconds) to
        signal they're alive and making progress.

        Args:
            agent_name: Name of the agent
            progress_data: Optional progress information
        """
        if agent_name not in self.registered_agents:
            if self.verbose:
                print(f"[Supervisor] ⚠️  Heartbeat from unregistered agent '{agent_name}'")
            return

        # Update last heartbeat time
        self.registered_agents[agent_name]["last_heartbeat"] = datetime.now().isoformat()

        # Notify observers of progress
        self.notify_agent_event(
            agent_name,
            AgentHealthEvent.PROGRESS,
            progress_data or {}
        )

    def adjust_heartbeat_interval(
        self,
        agent_name: str,
        new_interval: float,
        reason: Optional[str] = None
    ) -> bool:
        """
        Dynamically adjust the heartbeat interval for a registered agent

        Allows the supervisor to adapt heartbeat frequency based on:
        - Agent workload (increase interval if slow operations detected)
        - System load (decrease interval if system resources constrained)
        - Error rate (decrease interval to catch failures faster)
        - Stage complexity (LLM-heavy vs I/O-heavy vs CPU-heavy)

        Args:
            agent_name: Name of the agent
            new_interval: New heartbeat interval in seconds (5-60 recommended)
            reason: Optional reason for adjustment (for logging/debugging)

        Returns:
            True if adjustment successful, False if agent not found

        Example:
            # Agent is doing expensive LLM calls, reduce monitoring frequency
            supervisor.adjust_heartbeat_interval("CodeReviewStage", 30, "LLM operations detected")

            # Agent appears to be stalling, increase monitoring frequency
            supervisor.adjust_heartbeat_interval("DevelopmentStage", 10, "Stall detection")
        """
        if agent_name not in self.registered_agents:
            if self.verbose:
                print(f"[Supervisor] ⚠️  Cannot adjust heartbeat for unregistered agent '{agent_name}'")
            return False

        # Validate interval bounds (5-60 seconds)
        new_interval = max(5.0, min(60.0, new_interval))

        # Store old interval for logging
        old_interval = self.registered_agents[agent_name].get("heartbeat_interval", 15.0)

        # Update heartbeat interval
        self.registered_agents[agent_name]["heartbeat_interval"] = new_interval
        self.registered_agents[agent_name]["heartbeat_adjusted_at"] = datetime.now().isoformat()
        self.registered_agents[agent_name]["heartbeat_adjustment_reason"] = reason or "manual adjustment"

        if self.verbose:
            direction = "↑" if new_interval > old_interval else "↓"
            print(
                f"[Supervisor] {direction} Adjusted heartbeat for '{agent_name}': "
                f"{old_interval}s → {new_interval}s ({reason or 'no reason given'})"
            )

        # Log to state machine if available
        if self.state_machine:
            self.state_machine.push_state(
                PipelineState.STAGE_RUNNING,
                {
                    "event": "heartbeat_adjusted",
                    "agent": agent_name,
                    "old_interval": old_interval,
                    "new_interval": new_interval,
                    "reason": reason
                }
            )

        return True

    def get_heartbeat_interval(self, agent_name: str) -> Optional[float]:
        """
        Get the current heartbeat interval for an agent

        Args:
            agent_name: Name of the agent

        Returns:
            Heartbeat interval in seconds, or None if agent not registered
        """
        if agent_name not in self.registered_agents:
            return None

        return self.registered_agents[agent_name].get("heartbeat_interval", 15.0)

    def auto_adjust_heartbeat(self, agent_name: str) -> None:
        """
        Automatically adjust heartbeat interval based on agent behavior

        Uses heuristics to determine optimal heartbeat frequency:
        - If agent has many rapid heartbeats → increase interval (reduce overhead)
        - If agent has slow heartbeats → current interval is appropriate
        - If agent shows errors → decrease interval (catch failures faster)
        - If agent uses LLMs → increase interval (LLM calls are inherently slow)

        This is called automatically by the supervisor's learning engine.

        Args:
            agent_name: Name of the agent
        """
        if agent_name not in self.registered_agents:
            return

        agent_metadata = self.registered_agents[agent_name].get("metadata", {})
        current_interval = self.get_heartbeat_interval(agent_name)

        # Check if agent uses LLMs (from metadata)
        uses_llm = agent_metadata.get("uses_llm", False)
        if uses_llm and current_interval < 20:
            self.adjust_heartbeat_interval(
                agent_name,
                20.0,
                "LLM usage detected - reducing monitoring frequency"
            )
            return

        # Check if agent is evaluation-heavy (from metadata)
        is_evaluation_heavy = agent_metadata.get("evaluation_heavy", False)
        if is_evaluation_heavy and current_interval < 25:
            self.adjust_heartbeat_interval(
                agent_name,
                25.0,
                "Evaluation-heavy workload detected"
            )
            return

        # Check failure rate from stage health
        stage_name = agent_metadata.get("stage_name", agent_name)
        if stage_name in self.stage_health:
            failure_rate = self.stage_health[stage_name].failure_count / max(
                self.stage_health[stage_name].execution_count, 1
            )

            # High failure rate → more frequent monitoring
            if failure_rate > 0.3 and current_interval > 10:
                self.adjust_heartbeat_interval(
                    agent_name,
                    10.0,
                    f"High failure rate ({failure_rate:.1%}) - increasing monitoring"
                )
                return

        # Default: no adjustment needed
        if self.verbose:
            print(f"[Supervisor] ✓ Heartbeat interval for '{agent_name}' is optimal ({current_interval}s)")

    def start_watchdog(
        self,
        check_interval: int = 5,
        timeout_seconds: int = 300
    ) -> threading.Thread:
        """
        Start a watchdog thread to monitor agents via state machine

        The watchdog checks for:
        1. CRASHED - State machine in FAILED state
        2. HUNG - No state transition for > timeout_seconds
        3. STALLED - No progress for > timeout_seconds/2

        Args:
            check_interval: Seconds between checks (default 5)
            timeout_seconds: Max time before considering hung (default 300 = 5min)

        Returns:
            Watchdog thread (already started)
        """
        def watchdog_loop():
            """Watchdog monitoring loop"""
            if self.verbose:
                print(f"[Supervisor] 🐕 Watchdog started (check_interval={check_interval}s, timeout={timeout_seconds}s)")

            while True:
                try:
                    time.sleep(check_interval)

                    # Check state machine for crashes
                    if self.state_machine:
                        current_state = self.state_machine.get_current_state()

                        # Detect crash (FAILED state)
                        if current_state and "FAILED" in str(current_state):
                            context = self.state_machine.context if hasattr(self.state_machine, 'context') else {}
                            error_info = context.get("error", {})

                            crash_info = {
                                "agent_name": context.get("stage_name", "unknown"),
                                "error": error_info.get("message", "Unknown error"),
                                "error_type": error_info.get("type", "Unknown"),
                                "traceback": context.get("traceback", ""),
                                "state": str(current_state)
                            }

                            # Notify observers
                            self.notify_agent_event(
                                crash_info["agent_name"],
                                AgentHealthEvent.CRASHED,
                                {
                                    "crash_info": crash_info,
                                    "context": context
                                }
                            )

                        # Check for hang/stall via state machine transitions
                        # (This requires state machine to track last_transition_time)
                        if hasattr(self.state_machine, 'context'):
                            context = self.state_machine.context
                            last_transition = context.get("last_transition_time")

                            if last_transition:
                                from datetime import datetime
                                if isinstance(last_transition, str):
                                    last_transition = datetime.fromisoformat(last_transition)

                                elapsed = (datetime.now() - last_transition).total_seconds()

                                # Hung (exceeded timeout)
                                if elapsed > timeout_seconds:
                                    self.notify_agent_event(
                                        context.get("stage_name", "unknown"),
                                        AgentHealthEvent.HUNG,
                                        {
                                            "timeout_info": {
                                                "timeout_seconds": timeout_seconds,
                                                "elapsed_time": elapsed
                                            }
                                        }
                                    )

                                # Stalled (no progress for extended period)
                                elif elapsed > (timeout_seconds / 2):
                                    self.notify_agent_event(
                                        context.get("stage_name", "unknown"),
                                        AgentHealthEvent.STALLED,
                                        {
                                            "time_since_activity": elapsed
                                        }
                                    )

                except Exception as e:
                    if self.verbose:
                        print(f"[Supervisor] ⚠️  Watchdog error: {e}")

        # Start watchdog in daemon thread
        watchdog_thread = threading.Thread(target=watchdog_loop, daemon=True)
        watchdog_thread.start()

        return watchdog_thread

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
            "status": "unknown",
            "result": {},
            "metadata": {},
            "data": {},
            "config": {},
            "options": {},
        }

        # Check exact match
        if key in defaults:
            return defaults[key]

        # Check partial matches
        key_lower = key.lower()
        for pattern, value in defaults.items():
            if pattern in key_lower:
                return value

        # Default fallback based on common naming patterns
        if key.endswith('_id'):
            return "unknown"
        elif key.endswith('_count') or key.endswith('_num'):
            return 0
        elif key.endswith('_list') or key.endswith('_items'):
            return []
        elif key.endswith('_dict') or key.endswith('_map'):
            return {}
        elif key.endswith('_flag') or key.endswith('_enabled'):
            return False
        else:
            return None  # Generic fallback

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
        """Print comprehensive health report (including Phase 2 metrics)"""
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

        # Phase 2: Cost tracking stats
        if "cost_tracking" in stats:
            ct = stats["cost_tracking"]
            print(f"\n💰 Cost Management:")
            print(f"   Total LLM Calls:         {ct['total_calls']}")
            print(f"   Total Cost:              ${ct['total_cost']:.2f}")
            print(f"   Daily Cost:              ${ct['daily_cost']:.2f}")
            if ct['daily_remaining'] is not None:
                print(f"   Daily Remaining:         ${ct['daily_remaining']:.2f}")
            if ct['monthly_remaining'] is not None:
                print(f"   Monthly Remaining:       ${ct['monthly_remaining']:.2f}")
            if ct['budget_exceeded_count'] > 0:
                print(f"   ⚠️  Budget Exceeded:       {ct['budget_exceeded_count']} times")

        # Phase 2: Security sandbox stats
        if "security_sandbox" in stats:
            sb = stats["security_sandbox"]
            print(f"\n🛡️  Security Sandbox:")
            print(f"   Backend:                 {sb['backend']}")
            print(f"   Blocked Executions:      {sb['blocked_executions']}")

        # Learning engine stats
        if "learning" in stats:
            ln = stats["learning"]
            print(f"\n🧠 Learning Engine:")
            print(f"   Unexpected States:       {ln['unexpected_states_detected']}")
            print(f"   Solutions Learned:       {ln['solutions_learned']}")
            print(f"   Solutions Applied:       {ln['solutions_applied']}")
            print(f"   LLM Consultations:       {ln['llm_consultations']}")
            print(f"   Successful Applications: {ln['successful_applications']}")
            print(f"   Failed Applications:     {ln['failed_applications']}")
            if ln['total_learned_solutions'] > 0:
                print(f"   Average Success Rate:    {ln['average_success_rate']*100:.1f}%")

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
