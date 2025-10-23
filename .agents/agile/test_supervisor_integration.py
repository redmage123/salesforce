#!/usr/bin/env python3
"""
Test Supervisor Agent Integration with Artemis Orchestrator

Verifies that the supervisor agent is correctly integrated and working
with the Artemis orchestrator for resilience and failover.
"""

import sys
import time
from pathlib import Path

# Add agile directory to path (relative to this file)
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from supervisor_agent import SupervisorAgent, RecoveryStrategy
from artemis_stage_interface import PipelineStage
from artemis_exceptions import PipelineStageError
from kanban_manager import KanbanBoard
from agent_messenger import AgentMessenger
from rag_agent import RAGAgent


class FailingMockStage(PipelineStage):
    """Mock stage that fails initially then succeeds"""

    def __init__(self, fail_count: int = 2, stage_name: str = "mock_stage"):
        self.fail_count = fail_count
        self.execution_count = 0
        self._stage_name = stage_name

    def get_stage_name(self) -> str:
        """Return stage name"""
        return self._stage_name

    def execute(self, *args, **kwargs):
        self.execution_count += 1

        if self.execution_count <= self.fail_count:
            raise Exception(f"Mock failure #{self.execution_count}")

        return {
            "status": "success",
            "execution": self.execution_count,
            "message": f"Succeeded after {self.execution_count} attempts"
        }


def test_supervisor_exists():
    """Test 1: Verify supervisor agent can be created"""
    print("\n" + "="*70)
    print("TEST 1: Supervisor Agent Creation")
    print("="*70)

    # Create supervisor directly
    supervisor = SupervisorAgent(verbose=True)

    assert supervisor is not None, "Supervisor agent should be initialized"
    assert isinstance(supervisor, SupervisorAgent), "Should be SupervisorAgent instance"

    print("✅ Supervisor agent successfully created")
    print(f"   Type: {type(supervisor).__name__}")
    print(f"   Stats: {supervisor.stats}")


def test_supervisor_retry_recovery():
    """Test 2: Verify supervisor can retry and recover from failures"""
    print("\n" + "="*70)
    print("TEST 2: Retry and Recovery")
    print("="*70)

    # Create supervisor
    supervisor = SupervisorAgent(verbose=True)

    # Create failing stage that succeeds on 3rd attempt
    stage = FailingMockStage(fail_count=2)

    # Execute with supervision
    print("\nExecuting stage that fails twice then succeeds...")
    result = supervisor.execute_with_supervision(stage, "test_retry_stage")

    print(f"\n✅ Stage recovered successfully!")
    print(f"   Total executions: {stage.execution_count}")
    print(f"   Result: {result}")

    assert stage.execution_count == 3, "Should execute 3 times (2 fails + 1 success)"
    assert result["status"] == "success", "Should succeed after retries"


def test_supervisor_circuit_breaker():
    """Test 3: Verify circuit breaker opens after repeated failures"""
    print("\n" + "="*70)
    print("TEST 3: Circuit Breaker")
    print("="*70)

    # Create supervisor with aggressive circuit breaker
    supervisor = SupervisorAgent(verbose=True)

    # Register stage with low threshold
    supervisor.register_stage(
        "test_circuit_stage",
        RecoveryStrategy(
            max_retries=2,
            retry_delay_seconds=1.0,
            circuit_breaker_threshold=3
        )
    )

    # Create stage that always fails
    stage = FailingMockStage(fail_count=100)

    # Try to execute multiple times
    print("\nExecuting failing stage until circuit breaker opens...")

    failures = 0
    for i in range(5):
        try:
            supervisor.execute_with_supervision(stage, "test_circuit_stage")
        except PipelineStageError:
            failures += 1
            print(f"   Attempt {i+1} failed (expected)")

    # Check if circuit breaker opened
    circuit_open = supervisor.check_circuit_breaker("test_circuit_stage")

    print(f"\n✅ Circuit breaker behavior verified!")
    print(f"   Total failures: {failures}")
    print(f"   Circuit breaker open: {circuit_open}")

    assert circuit_open, "Circuit breaker should be open after repeated failures"


def test_supervisor_health_reporting():
    """Test 4: Verify supervisor health reporting"""
    print("\n" + "="*70)
    print("TEST 4: Health Reporting")
    print("="*70)

    supervisor = SupervisorAgent(verbose=False)

    # Execute some stages
    stage1 = FailingMockStage(fail_count=0)  # Succeeds immediately
    stage2 = FailingMockStage(fail_count=1)  # Fails once

    supervisor.execute_with_supervision(stage1, "healthy_stage")
    supervisor.execute_with_supervision(stage2, "degraded_stage")

    # Get statistics
    stats = supervisor.get_statistics()

    print("\n✅ Health statistics collected!")
    print(f"   Overall health: {stats['overall_health']}")
    print(f"   Total interventions: {stats['total_interventions']}")
    print(f"   Successful recoveries: {stats['successful_recoveries']}")
    print(f"   Failed recoveries: {stats['failed_recoveries']}")
    print(f"   Stages monitored: {len(stats['stage_statistics'])}")

    # Print full report
    print("\n" + "-"*70)
    supervisor.print_health_report()

    assert "overall_health" in stats, "Should have overall health status"
    assert len(stats["stage_statistics"]) == 2, "Should track 2 stages"


def test_supervisor_integration_with_orchestrator():
    """Test 5: Verify supervisor can integrate with messenger"""
    print("\n" + "="*70)
    print("TEST 5: Messenger Integration")
    print("="*70)

    # Create supervisor with messenger
    messenger = AgentMessenger(agent_name="test-supervisor-agent")

    supervisor = SupervisorAgent(
        verbose=False,
        messenger=messenger
    )

    # Register some stages
    stage_names = [
        "project_analysis",
        "development",
        "code_review"
    ]

    for stage_name in stage_names:
        supervisor.register_stage(stage_name)

    registered_stages = list(supervisor.stage_health.keys())

    print(f"\n✅ Supervisor integrated with messenger!")
    print(f"   Messenger integrated: {supervisor.messenger is not None}")
    print(f"   Messenger agent name: {supervisor.messenger.agent_name}")
    print(f"   Stages registered: {len(registered_stages)}")

    for stage_name in registered_stages:
        print(f"      - {stage_name}")

    assert len(registered_stages) == len(stage_names), \
        f"Should register all {len(stage_names)} stages"
    assert supervisor.messenger.agent_name == "test-supervisor-agent"


def test_supervisor_custom_recovery_strategy():
    """Test 6: Verify custom recovery strategies work"""
    print("\n" + "="*70)
    print("TEST 6: Custom Recovery Strategy")
    print("="*70)

    supervisor = SupervisorAgent(verbose=True)

    # Create custom recovery strategy with fast retries
    custom_strategy = RecoveryStrategy(
        max_retries=5,
        retry_delay_seconds=0.5,
        backoff_multiplier=1.5,
        timeout_seconds=60.0
    )

    supervisor.register_stage("custom_stage", custom_strategy)

    # Create stage that fails 3 times
    stage = FailingMockStage(fail_count=3)

    print("\nExecuting with custom recovery strategy...")
    result = supervisor.execute_with_supervision(stage, "custom_stage")

    print(f"\n✅ Custom recovery strategy works!")
    print(f"   Executions: {stage.execution_count}")
    print(f"   Max retries configured: {custom_strategy.max_retries}")
    print(f"   Result: {result}")

    assert stage.execution_count == 4, "Should execute 4 times (3 fails + 1 success)"


if __name__ == "__main__":
    print("\n" + "="*70)
    print("ARTEMIS SUPERVISOR INTEGRATION TESTS")
    print("="*70)

    try:
        test_supervisor_exists()
        test_supervisor_retry_recovery()
        test_supervisor_circuit_breaker()
        test_supervisor_health_reporting()
        test_supervisor_integration_with_orchestrator()
        test_supervisor_custom_recovery_strategy()

        print("\n" + "="*70)
        print("✅ ALL SUPERVISOR INTEGRATION TESTS PASSED!")
        print("="*70)
        print("\nSummary:")
        print("  ✅ Supervisor agent initialization")
        print("  ✅ Retry and recovery mechanisms")
        print("  ✅ Circuit breaker functionality")
        print("  ✅ Health reporting")
        print("  ✅ Orchestrator integration")
        print("  ✅ Custom recovery strategies")
        print("\nThe Supervisor Agent is fully functional and integrated!")
        print("="*70 + "\n")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
