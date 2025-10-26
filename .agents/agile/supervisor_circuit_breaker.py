#!/usr/bin/env python3
"""
Circuit Breaker Manager for Supervisor

Single Responsibility: Manage circuit breaker state for pipeline stages

Extracted from SupervisorAgent to follow Single Responsibility Principle.

Design Patterns:
- Circuit Breaker: Prevent cascading failures
- Strategy Pattern: Configurable recovery strategies per stage
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from enum import Enum

from artemis_stage_interface import LoggerInterface
from artemis_constants import (
    MAX_RETRY_ATTEMPTS,
    DEFAULT_RETRY_INTERVAL_SECONDS,
    RETRY_BACKOFF_FACTOR
)


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
    fallback_action: Optional[Any] = None


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failures detected, blocking requests
    HALF_OPEN = "half_open"  # Testing if recovery succeeded


class CircuitBreakerManager:
    """
    Manage circuit breaker state for pipeline stages

    Responsibilities:
    - Track stage health (failure counts, execution times)
    - Open/close circuit breakers based on failure thresholds
    - Store and retrieve recovery strategies per stage
    - Provide health status for stages

    Thread-Safety: Not thread-safe (assumes single-threaded pipeline execution)
    """

    def __init__(
        self,
        logger: Optional[LoggerInterface] = None,
        verbose: bool = True
    ):
        """
        Initialize Circuit Breaker Manager

        Args:
            logger: Logger for recording events
            verbose: Enable verbose logging
        """
        self.logger = logger
        self.verbose = verbose

        # Track stage health
        self.stage_health: Dict[str, StageHealth] = {}

        # Store recovery strategies per stage
        self.recovery_strategies: Dict[str, RecoveryStrategy] = {}

    def register_stage(
        self,
        stage_name: str,
        recovery_strategy: Optional[RecoveryStrategy] = None
    ) -> None:
        """
        Register a stage for circuit breaker management

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

        # Set recovery strategy
        if recovery_strategy:
            self.recovery_strategies[stage_name] = recovery_strategy
        else:
            self.recovery_strategies[stage_name] = RecoveryStrategy()

        self._log(f"Registered stage: {stage_name}")

    def check_circuit(self, stage_name: str) -> bool:
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

        # Check if circuit timeout has expired (auto-close)
        if health.circuit_open_until and datetime.now() > health.circuit_open_until:
            health.circuit_open = False
            health.circuit_open_until = None
            self._log(f"Circuit breaker auto-closed for {stage_name}")
            return False

        # Circuit still open
        if health.circuit_open_until:
            time_remaining = (health.circuit_open_until - datetime.now()).seconds
            self._log(f"⚠️  Circuit breaker OPEN for {stage_name} ({time_remaining}s remaining)")

        return True

    def open_circuit(self, stage_name: str) -> None:
        """
        Open circuit breaker for a stage (block future executions)

        Args:
            stage_name: Stage name
        """
        if stage_name not in self.stage_health:
            self._log(f"Cannot open circuit for unregistered stage: {stage_name}", level="WARNING")
            return

        health = self.stage_health[stage_name]
        strategy = self.recovery_strategies.get(stage_name, RecoveryStrategy())

        # Open circuit
        health.circuit_open = True
        health.circuit_open_until = datetime.now() + timedelta(
            seconds=strategy.circuit_breaker_timeout_seconds
        )

        self._log(
            f"🚨 Circuit breaker OPEN for {stage_name} "
            f"(timeout: {strategy.circuit_breaker_timeout_seconds}s, "
            f"failures: {health.failure_count})"
        )

    def close_circuit(self, stage_name: str) -> None:
        """
        Manually close circuit breaker for a stage

        Args:
            stage_name: Stage name
        """
        if stage_name not in self.stage_health:
            return

        health = self.stage_health[stage_name]
        health.circuit_open = False
        health.circuit_open_until = None

        self._log(f"Circuit breaker manually closed for {stage_name}")

    def record_failure(self, stage_name: str) -> None:
        """
        Record a stage failure and check circuit breaker threshold

        Args:
            stage_name: Stage name
        """
        if stage_name not in self.stage_health:
            self.register_stage(stage_name)

        health = self.stage_health[stage_name]
        strategy = self.recovery_strategies.get(stage_name, RecoveryStrategy())

        # Increment failure count
        health.failure_count += 1
        health.last_failure = datetime.now()

        self._log(
            f"Stage {stage_name} failed "
            f"({health.failure_count}/{strategy.circuit_breaker_threshold})"
        )

        # Check if circuit should open
        if health.failure_count >= strategy.circuit_breaker_threshold:
            self.open_circuit(stage_name)

    def record_success(self, stage_name: str, duration: float = 0.0) -> None:
        """
        Record a successful stage execution

        Args:
            stage_name: Stage name
            duration: Execution duration in seconds
        """
        if stage_name not in self.stage_health:
            self.register_stage(stage_name)

        health = self.stage_health[stage_name]

        # Reset failure count on success
        health.failure_count = 0
        health.last_failure = None
        health.execution_count += 1
        health.total_duration += duration

        # If circuit was open, close it
        if health.circuit_open:
            self.close_circuit(stage_name)

    def get_stage_health(self, stage_name: str) -> Optional[StageHealth]:
        """
        Get health info for a stage

        Args:
            stage_name: Stage name

        Returns:
            StageHealth object or None if stage not registered
        """
        return self.stage_health.get(stage_name)

    def get_all_health(self) -> Dict[str, StageHealth]:
        """
        Get health info for all stages

        Returns:
            Dict mapping stage name to StageHealth
        """
        return self.stage_health.copy()

    def get_recovery_strategy(self, stage_name: str) -> Optional[RecoveryStrategy]:
        """
        Get recovery strategy for a stage

        Args:
            stage_name: Stage name

        Returns:
            RecoveryStrategy or None if not registered
        """
        return self.recovery_strategies.get(stage_name)

    def get_open_circuits(self) -> list[str]:
        """
        Get list of stages with open circuit breakers

        Returns:
            List of stage names
        """
        return [
            name for name, health in self.stage_health.items()
            if health.circuit_open
        ]

    def reset_all(self) -> None:
        """
        Reset all circuit breakers (close all circuits)
        """
        for stage_name in self.stage_health:
            self.close_circuit(stage_name)
            self.stage_health[stage_name].failure_count = 0

        self._log("Reset all circuit breakers")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get circuit breaker statistics

        Returns:
            Dict with statistics
        """
        total_stages = len(self.stage_health)
        open_circuits = len(self.get_open_circuits())
        total_failures = sum(h.failure_count for h in self.stage_health.values())
        total_executions = sum(h.execution_count for h in self.stage_health.values())

        return {
            "total_stages": total_stages,
            "open_circuits": open_circuits,
            "closed_circuits": total_stages - open_circuits,
            "total_failures": total_failures,
            "total_executions": total_executions,
            "stages": {
                name: {
                    "failure_count": health.failure_count,
                    "execution_count": health.execution_count,
                    "circuit_open": health.circuit_open,
                    "avg_duration": health.total_duration / max(health.execution_count, 1)
                }
                for name, health in self.stage_health.items()
            }
        }

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
            prefix = "[CircuitBreakerManager]"
            print(f"{prefix} {message}")


# ============================================================================
# CLI INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Circuit Breaker Manager Demo")
    parser.add_argument("--demo", action="store_true", help="Run demo")
    parser.add_argument("--stats", action="store_true", help="Show statistics")

    args = parser.parse_args()

    if args.demo:
        print("=" * 70)
        print("CIRCUIT BREAKER MANAGER DEMO")
        print("=" * 70)

        # Create manager
        manager = CircuitBreakerManager(verbose=True)

        # Register stages
        manager.register_stage("stage1", RecoveryStrategy(circuit_breaker_threshold=3))
        manager.register_stage("stage2")

        # Simulate failures
        print("\n--- Simulating stage1 failures ---")
        for i in range(5):
            manager.record_failure("stage1")
            is_open = manager.check_circuit("stage1")
            print(f"Attempt {i+1}: Circuit open = {is_open}")

        # Simulate success
        print("\n--- Simulating stage1 success ---")
        manager.record_success("stage1", duration=1.5)
        is_open = manager.check_circuit("stage1")
        print(f"After success: Circuit open = {is_open}")

        # Show stats
        print("\n--- Statistics ---")
        stats = manager.get_statistics()
        print(json.dumps(stats, indent=2))

    elif args.stats:
        manager = CircuitBreakerManager(verbose=False)
        stats = manager.get_statistics()
        print(json.dumps(stats, indent=2))

    else:
        parser.print_help()
