#!/usr/bin/env python3
"""
Test script for Dynamic Workflow Planner

Tests various card scenarios to verify workflow planning logic
"""

import sys
from pathlib import Path

# Add agile directory to path (relative to this file)
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from artemis_orchestrator_solid import WorkflowPlanner


def test_simple_bugfix():
    """Test simple bugfix gets 1 developer, skips arbitration"""
    card = {
        'id': 'test-001',
        'title': 'Fix minor CSS issue',
        'description': 'Small fix for button alignment',
        'priority': 'low',
        'points': 2
    }

    planner = WorkflowPlanner(card, verbose=False)
    plan = planner.create_workflow_plan()

    print("\n=== Test 1: Simple Bugfix ===")
    print(f"Task Type: {plan['task_type']}")
    print(f"Complexity: {plan['complexity']}")
    print(f"Parallel Developers: {plan['parallel_developers']}")
    print(f"Stages: {plan['stages']}")
    print(f"Skipped Stages: {plan['skip_stages']}")

    assert plan['task_type'] == 'bugfix', f"Expected bugfix, got {plan['task_type']}"
    assert plan['complexity'] == 'simple', f"Expected simple, got {plan['complexity']}"
    assert plan['parallel_developers'] == 1, f"Expected 1 developer, got {plan['parallel_developers']}"
    assert 'arbitration' in plan['skip_stages'], "Should skip arbitration"
    print("✅ PASSED")


def test_medium_feature():
    """Test medium feature gets 2 developers, includes arbitration"""
    card = {
        'id': 'test-002',
        'title': 'Add user profile feature',
        'description': 'Implement new user profile page with avatar upload',
        'priority': 'medium',
        'points': 8
    }

    planner = WorkflowPlanner(card, verbose=False)
    plan = planner.create_workflow_plan()

    print("\n=== Test 2: Medium Feature ===")
    print(f"Task Type: {plan['task_type']}")
    print(f"Complexity: {plan['complexity']}")
    print(f"Parallel Developers: {plan['parallel_developers']}")
    print(f"Stages: {plan['stages']}")
    print(f"Skipped Stages: {plan['skip_stages']}")

    assert plan['task_type'] == 'feature', f"Expected feature, got {plan['task_type']}"
    assert plan['complexity'] == 'medium', f"Expected medium, got {plan['complexity']}"
    assert plan['parallel_developers'] == 2, f"Expected 2 developers, got {plan['parallel_developers']}"
    assert 'arbitration' in plan['stages'], "Should include arbitration"
    assert 'arbitration' not in plan['skip_stages'], "Should not skip arbitration"
    print("✅ PASSED")


def test_complex_integration():
    """Test complex integration gets 3 developers"""
    card = {
        'id': 'test-003',
        'title': 'Integrate payment gateway API',
        'description': 'Integrate Stripe API for payment processing with scalability and performance optimization',
        'priority': 'high',
        'points': 13
    }

    planner = WorkflowPlanner(card, verbose=False)
    plan = planner.create_workflow_plan()

    print("\n=== Test 3: Complex Integration ===")
    print(f"Task Type: {plan['task_type']}")
    print(f"Complexity: {plan['complexity']}")
    print(f"Parallel Developers: {plan['parallel_developers']}")
    print(f"Stages: {plan['stages']}")
    print(f"Skipped Stages: {plan['skip_stages']}")
    print(f"Reasoning: {plan['reasoning']}")

    assert plan['task_type'] == 'feature', f"Expected feature, got {plan['task_type']}"
    assert plan['complexity'] == 'complex', f"Expected complex, got {plan['complexity']}"
    assert plan['parallel_developers'] == 3, f"Expected 3 developers, got {plan['parallel_developers']}"
    assert 'arbitration' in plan['stages'], "Should include arbitration"
    print("✅ PASSED")


def test_documentation_task():
    """Test documentation task skips testing"""
    card = {
        'id': 'test-004',
        'title': 'Update API documentation',
        'description': 'Add documentation for new endpoints',
        'priority': 'medium',
        'points': 3
    }

    planner = WorkflowPlanner(card, verbose=False)
    plan = planner.create_workflow_plan()

    print("\n=== Test 4: Documentation Task ===")
    print(f"Task Type: {plan['task_type']}")
    print(f"Complexity: {plan['complexity']}")
    print(f"Parallel Developers: {plan['parallel_developers']}")
    print(f"Stages: {plan['stages']}")
    print(f"Skipped Stages: {plan['skip_stages']}")

    assert plan['task_type'] == 'documentation', f"Expected documentation, got {plan['task_type']}"
    assert 'testing' in plan['skip_stages'], "Should skip testing for docs"
    assert 'arbitration' in plan['skip_stages'], "Should skip arbitration (simple task)"
    print("✅ PASSED")


def test_refactor_task():
    """Test refactor gets proper classification"""
    card = {
        'id': 'test-005',
        'title': 'Refactor database layer',
        'description': 'Refactor and restructure database access code for better performance',
        'priority': 'high',
        'points': 10
    }

    planner = WorkflowPlanner(card, verbose=False)
    plan = planner.create_workflow_plan()

    print("\n=== Test 5: Refactor Task ===")
    print(f"Task Type: {plan['task_type']}")
    print(f"Complexity: {plan['complexity']}")
    print(f"Parallel Developers: {plan['parallel_developers']}")
    print(f"Stages: {plan['stages']}")
    print(f"Skipped Stages: {plan['skip_stages']}")

    assert plan['task_type'] == 'refactor', f"Expected refactor, got {plan['task_type']}"
    assert plan['complexity'] in ['medium', 'complex'], f"Expected medium/complex for high priority refactor"
    assert plan['parallel_developers'] >= 2, f"Expected 2+ developers for high priority task"
    print("✅ PASSED")


if __name__ == "__main__":
    print("🧪 Testing Dynamic Workflow Planner")
    print("=" * 60)

    try:
        test_simple_bugfix()
        test_medium_feature()
        test_complex_integration()
        test_documentation_task()
        test_refactor_task()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nDynamic Workflow Planner is working correctly!")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
