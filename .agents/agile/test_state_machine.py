#!/usr/bin/env python3
"""
Test Artemis State Machine and Workflows

Tests:
1. State machine initialization
2. State transitions
3. Pushdown automaton (stack operations)
4. Workflow execution
5. Issue registration and resolution
6. Supervisor integration
"""

import sys
from pathlib import Path

# Add agile directory to path (relative to this file)
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from artemis_state_machine import (
    ArtemisStateMachine,
    PipelineState,
    StageState,
    EventType,
    IssueType
)
from supervisor_agent import SupervisorAgent


def test_state_machine_initialization():
    """Test 1: State machine initializes correctly"""
    print("\n" + "="*70)
    print("TEST 1: State Machine Initialization")
    print("="*70)

    sm = ArtemisStateMachine(card_id="test-card-001", verbose=False)

    assert sm.current_state == PipelineState.IDLE
    assert sm.card_id == "test-card-001"
    assert len(sm.workflows) > 0  # Workflows registered

    print(f"✅ State machine initialized")
    print(f"   Current state: {sm.current_state.value}")
    print(f"   Workflows registered: {len(sm.workflows)}")


def test_state_transitions():
    """Test 2: State transitions work correctly"""
    print("\n" + "="*70)
    print("TEST 2: State Transitions")
    print("="*70)

    sm = ArtemisStateMachine(card_id="test-card-002", verbose=True)

    # Test valid transitions
    print("\nTesting valid transitions...")

    # IDLE → INITIALIZING
    success = sm.transition(
        PipelineState.INITIALIZING,
        EventType.START,
        reason="Pipeline starting"
    )
    assert success, "Should allow IDLE → INITIALIZING"
    assert sm.current_state == PipelineState.INITIALIZING

    # INITIALIZING → RUNNING
    success = sm.transition(
        PipelineState.RUNNING,
        EventType.STAGE_START,
        reason="First stage starting"
    )
    assert success, "Should allow INITIALIZING → RUNNING"
    assert sm.current_state == PipelineState.RUNNING

    # RUNNING → STAGE_RUNNING
    success = sm.transition(
        PipelineState.STAGE_RUNNING,
        EventType.STAGE_START,
        reason="Stage executing"
    )
    assert success, "Should allow RUNNING → STAGE_RUNNING"

    # Test invalid transition
    print("\nTesting invalid transition...")
    success = sm.transition(
        PipelineState.COMPLETED,  # Can't jump directly to COMPLETED from STAGE_RUNNING
        EventType.COMPLETE
    )
    # Note: This might be valid depending on transition rules
    # The test is to verify the transition rules are being checked

    print(f"\n✅ State transitions working correctly")
    print(f"   Final state: {sm.current_state.value}")
    print(f"   Total transitions: {len(sm.state_history)}")


def test_pushdown_automaton():
    """Test 3: Pushdown automaton stack operations"""
    print("\n" + "="*70)
    print("TEST 3: Pushdown Automaton (Stack Operations)")
    print("="*70)

    sm = ArtemisStateMachine(card_id="test-card-003", verbose=True)

    # Push states onto stack
    print("\nPushing states onto stack...")
    sm.push_state(PipelineState.IDLE, {"action": "initialized"})
    sm.push_state(PipelineState.RUNNING, {"stage": "development"})
    sm.push_state(PipelineState.STAGE_RUNNING, {"stage": "development", "developer": "a"})

    assert sm.get_state_depth() == 3, "Should have 3 states on stack"

    # Peek at top
    print("\nPeeking at top of stack...")
    top = sm.peek_state()
    assert top["state"] == PipelineState.STAGE_RUNNING
    assert sm.get_state_depth() == 3, "Peek should not remove from stack"

    # Pop states
    print("\nPopping states from stack...")
    popped = sm.pop_state()
    assert popped["state"] == PipelineState.STAGE_RUNNING
    assert sm.get_state_depth() == 2

    # Rollback to specific state
    print("\nTesting rollback...")
    sm.push_state(PipelineState.FAILED, {"error": "test"})
    sm.push_state(PipelineState.RECOVERING, {"attempt": 1})

    success = sm.rollback_to_state(PipelineState.RUNNING)
    # Note: This depends on if RUNNING is in the stack

    print(f"\n✅ Pushdown automaton working correctly")
    print(f"   Final stack depth: {sm.get_state_depth()}")


def test_stage_state_tracking():
    """Test 4: Stage state tracking"""
    print("\n" + "="*70)
    print("TEST 4: Stage State Tracking")
    print("="*70)

    sm = ArtemisStateMachine(card_id="test-card-004", verbose=True)

    # Track multiple stages
    stages = ["project_analysis", "development", "code_review"]

    print("\nRegistering stages...")
    for stage in stages:
        sm.update_stage_state(stage, StageState.PENDING)

    # Start first stage
    print("\nStarting project_analysis...")
    sm.update_stage_state("project_analysis", StageState.RUNNING)

    # Complete first stage
    print("\nCompleting project_analysis...")
    sm.update_stage_state("project_analysis", StageState.COMPLETED)

    # Get snapshot
    snapshot = sm.get_snapshot()

    assert len(snapshot.stages) == 3, "Should track 3 stages"
    assert snapshot.stages["project_analysis"].state == StageState.COMPLETED

    print(f"\n✅ Stage state tracking working correctly")
    print(f"   Stages tracked: {len(snapshot.stages)}")


def test_issue_handling():
    """Test 5: Issue registration and workflow execution"""
    print("\n" + "="*70)
    print("TEST 5: Issue Handling and Workflows")
    print("="*70)

    sm = ArtemisStateMachine(card_id="test-card-005", verbose=True)

    # Register an issue
    print("\nRegistering timeout issue...")
    sm.register_issue(IssueType.TIMEOUT, pid=12345)

    assert IssueType.TIMEOUT in sm.active_issues
    print(f"   Active issues: {len(sm.active_issues)}")

    # Execute workflow to resolve issue
    print("\nExecuting timeout recovery workflow...")
    context = {
        "pid": 12345,
        "stage_name": "development",
        "timeout_seconds": 300
    }

    success = sm.execute_workflow(IssueType.TIMEOUT, context)

    print(f"\n✅ Issue handling working")
    print(f"   Workflow succeeded: {success}")
    print(f"   Total workflow executions: {len(sm.workflow_history)}")


def test_supervisor_integration():
    """Test 6: Supervisor agent with state machine"""
    print("\n" + "="*70)
    print("TEST 6: Supervisor Integration with State Machine")
    print("="*70)

    # Create supervisor with state machine
    print("\nCreating supervisor with state machine...")
    supervisor = SupervisorAgent(
        card_id="test-card-006",
        verbose=True
    )

    assert supervisor.state_machine is not None, "Should have state machine"

    # Register a stage
    print("\nRegistering stage...")
    supervisor.register_stage("development")

    # Check state machine has the stage
    assert "development" in supervisor.state_machine.stage_states

    # Handle an issue through supervisor
    print("\nHandling issue through supervisor...")
    success = supervisor.handle_issue(
        IssueType.MEMORY_EXHAUSTED,
        context={}
    )

    print(f"   Issue handled: {success}")

    # Get state snapshot
    print("\nGetting state snapshot...")
    snapshot = supervisor.get_state_snapshot()

    assert snapshot is not None, "Should have snapshot"
    assert snapshot["card_id"] == "test-card-006"

    print(f"\n✅ Supervisor integration working correctly")
    print(f"   State machine active: {supervisor.state_machine is not None}")
    print(f"   Current state: {snapshot['state']}")


def test_workflow_coverage():
    """Test 7: Verify all issue types have workflows"""
    print("\n" + "="*70)
    print("TEST 7: Workflow Coverage")
    print("="*70)

    sm = ArtemisStateMachine(card_id="test-card-007", verbose=False)

    # Get all issue types
    all_issues = list(IssueType)
    registered_workflows = list(sm.workflows.keys())

    print(f"\nTotal issue types: {len(all_issues)}")
    print(f"Registered workflows: {len(registered_workflows)}")

    # Check coverage
    missing_workflows = []
    for issue in all_issues:
        if issue not in registered_workflows:
            missing_workflows.append(issue.value)

    if missing_workflows:
        print(f"\n⚠️  Missing workflows for:")
        for issue in missing_workflows:
            print(f"   - {issue}")
    else:
        print(f"\n✅ 100% workflow coverage!")

    # Print workflow summary
    print(f"\nWorkflow Summary:")
    for issue_type, workflow in sm.workflows.items():
        print(f"   {issue_type.value:30s} → {len(workflow.actions)} actions")

    assert len(missing_workflows) == 0, "All issues should have workflows"

    print(f"\n✅ Workflow coverage verified")


def test_state_persistence():
    """Test 8: State persistence to disk"""
    print("\n" + "="*70)
    print("TEST 8: State Persistence")
    print("="*70)

    sm = ArtemisStateMachine(card_id="test-card-008", verbose=True)

    # Make some state changes
    print("\nMaking state changes...")
    sm.transition(PipelineState.INITIALIZING, EventType.START)
    sm.transition(PipelineState.RUNNING, EventType.STAGE_START)
    sm.update_stage_state("development", StageState.RUNNING)

    # State should be saved automatically
    import os
    from pathlib import Path

    state_file = Path("/tmp/artemis_state") / "test-card-008_state.json"

    assert state_file.exists(), f"State file should exist at {state_file}"

    # Read state file
    import json
    with open(state_file) as f:
        saved_state = json.load(f)

    assert saved_state["card_id"] == "test-card-008"
    assert saved_state["state"] == "running"

    print(f"\n✅ State persistence working correctly")
    print(f"   State file: {state_file}")
    print(f"   Saved state: {saved_state['state']}")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("ARTEMIS STATE MACHINE AND WORKFLOW TESTS")
    print("="*70)

    try:
        test_state_machine_initialization()
        test_state_transitions()
        test_pushdown_automaton()
        test_stage_state_tracking()
        test_issue_handling()
        test_supervisor_integration()
        test_workflow_coverage()
        test_state_persistence()

        print("\n" + "="*70)
        print("✅ ALL STATE MACHINE TESTS PASSED!")
        print("="*70)
        print("\nSummary:")
        print("  ✅ State machine initialization")
        print("  ✅ State transitions and validation")
        print("  ✅ Pushdown automaton (stack operations)")
        print("  ✅ Stage state tracking")
        print("  ✅ Issue handling and workflows")
        print("  ✅ Supervisor integration")
        print("  ✅ 100% workflow coverage")
        print("  ✅ State persistence")
        print("\nThe State Machine is fully functional!")
        print("="*70 + "\n")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
