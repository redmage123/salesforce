#!/usr/bin/env python3
"""
Test Supervisor Learning Capability

Tests the supervisor's ability to:
1. Detect unexpected states
2. Consult LLM for solutions
3. Generate dynamic recovery workflows
4. Store and reuse learned solutions
"""

import sys
import os
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from supervisor_agent import SupervisorAgent
from supervisor_learning import (
    SupervisorLearningEngine,
    LearningStrategy,
    UnexpectedState
)


class MockLLMClient:
    """Mock LLM client for testing"""

    def __init__(self):
        self.calls = []

    def chat(self, prompt: str):
        """Simulate LLM response"""
        self.calls.append(prompt)

        # Return a structured solution
        solution_json = {
            "problem_analysis": "Developer agents are stuck in infinite loop waiting for response",
            "root_cause": "Message queue deadlock between developer-a and developer-b",
            "solution_description": "Clear message queue and restart stuck agents",
            "workflow_steps": [
                {
                    "step": 1,
                    "action": "cleanup_resources",
                    "description": "Clear stuck message queue",
                    "parameters": {"queue_name": "developer_messages"}
                },
                {
                    "step": 2,
                    "action": "restart_process",
                    "description": "Restart developer agents",
                    "parameters": {"agents": ["developer-a", "developer-b"]}
                },
                {
                    "step": 3,
                    "action": "retry_stage",
                    "description": "Retry development stage",
                    "parameters": {"stage": "development"}
                }
            ],
            "confidence": "high",
            "risks": ["May lose in-progress work", "Could take 2-3 minutes"],
            "alternative_approaches": [
                "Manual intervention to debug agents",
                "Rollback to previous checkpoint"
            ]
        }

        # Create mock response object
        class MockResponse:
            def __init__(self, content, model="gpt-4o"):
                self.content = content
                self.model = model

                class Usage:
                    prompt_tokens = 500
                    completion_tokens = 200

                self.usage = Usage()

        return MockResponse(json.dumps(solution_json, indent=2))


class MockRAGAgent:
    """Mock RAG agent for testing"""

    def __init__(self):
        self.artifacts = []

    def store_artifact(self, **kwargs):
        """Store artifact"""
        artifact_id = f"artifact-{len(self.artifacts) + 1}"
        self.artifacts.append({
            "artifact_id": artifact_id,
            **kwargs
        })
        return artifact_id

    def query_similar(self, query_text, artifact_types=None, top_k=5):
        """Query similar artifacts"""
        # Return stored artifacts that match
        matching = [
            a for a in self.artifacts
            if artifact_types is None or a.get("artifact_type") in artifact_types
        ]
        return matching[:top_k]


def test_detect_unexpected_state():
    """Test detecting unexpected states"""
    print("\n" + "=" * 70)
    print("TEST 1: Detect Unexpected States")
    print("=" * 70)

    learning = SupervisorLearningEngine(
        llm_client=None,
        rag_agent=None,
        verbose=True
    )

    print("\n  1. Testing expected state (should not detect)...")
    unexpected = learning.detect_unexpected_state(
        card_id="card-001",
        current_state="STAGE_RUNNING",
        expected_states=["STAGE_RUNNING", "STAGE_COMPLETED"],
        context={"stage_name": "development"}
    )
    assert unexpected is None, "Should not detect expected state"
    print("     ✅ Expected state correctly ignored")

    print("\n  2. Testing unexpected state (should detect)...")
    unexpected = learning.detect_unexpected_state(
        card_id="card-002",
        current_state="STAGE_STUCK",
        expected_states=["STAGE_RUNNING", "STAGE_COMPLETED"],
        context={
            "stage_name": "development",
            "error_message": "Agents not responding",
            "previous_state": "STAGE_RUNNING"
        }
    )
    assert unexpected is not None, "Should detect unexpected state"
    assert unexpected.current_state == "STAGE_STUCK"
    assert unexpected.severity in ["low", "medium", "high", "critical"]
    print(f"     ✅ Unexpected state detected (severity: {unexpected.severity})")

    print("\n  ✅ Unexpected state detection working!")
    return True


def test_llm_consultation():
    """Test LLM consultation for solutions"""
    print("\n" + "=" * 70)
    print("TEST 2: LLM Consultation")
    print("=" * 70)

    mock_llm = MockLLMClient()
    learning = SupervisorLearningEngine(
        llm_client=mock_llm,
        rag_agent=MockRAGAgent(),
        verbose=True
    )

    print("\n  1. Creating unexpected state...")
    unexpected = UnexpectedState(
        state_id="test-unexpected-001",
        timestamp="2025-10-23T12:00:00Z",
        card_id="card-003",
        stage_name="development",
        error_message="Developer agents stuck",
        context={"agents": ["developer-a", "developer-b"]},
        stack_trace=None,
        previous_state="STAGE_RUNNING",
        current_state="STAGE_STUCK",
        expected_states=["STAGE_RUNNING", "STAGE_COMPLETED"],
        severity="high"
    )

    print("\n  2. Consulting LLM for solution...")
    solution = learning.learn_solution(
        unexpected,
        strategy=LearningStrategy.LLM_CONSULTATION
    )

    assert solution is not None, "Should learn solution from LLM"
    assert len(solution.workflow_steps) > 0, "Should have workflow steps"
    assert solution.llm_model_used == "gpt-4o"
    print(f"     ✅ Solution learned with {len(solution.workflow_steps)} steps")

    print("\n  3. Verifying workflow steps...")
    for i, step in enumerate(solution.workflow_steps, 1):
        print(f"     Step {i}: {step.get('action')} - {step.get('description')}")

    assert mock_llm.calls, "Should have called LLM"
    print(f"\n  ✅ LLM consultation successful ({len(mock_llm.calls)} calls)")

    return True


def test_apply_learned_solution():
    """Test applying learned solutions"""
    print("\n" + "=" * 70)
    print("TEST 3: Apply Learned Solutions")
    print("=" * 70)

    mock_llm = MockLLMClient()
    mock_rag = MockRAGAgent()
    learning = SupervisorLearningEngine(
        llm_client=mock_llm,
        rag_agent=mock_rag,
        verbose=True
    )

    print("\n  1. Learning solution from LLM...")
    unexpected = UnexpectedState(
        state_id="test-unexpected-002",
        timestamp="2025-10-23T12:00:00Z",
        card_id="card-004",
        stage_name="development",
        error_message="Timeout waiting for agents",
        context={},
        stack_trace=None,
        previous_state="STAGE_RUNNING",
        current_state="STAGE_TIMEOUT",
        expected_states=["STAGE_COMPLETED"],
        severity="high"
    )

    solution = learning.learn_solution(unexpected, LearningStrategy.LLM_CONSULTATION)
    assert solution is not None

    print("\n  2. Applying solution...")
    success = learning.apply_learned_solution(solution, {})

    assert success, "Solution should apply successfully"
    assert solution.times_applied == 1
    assert solution.times_successful == 1
    assert solution.success_rate == 1.0
    print(f"     ✅ Solution applied (success rate: {solution.success_rate*100:.1f}%)")

    print("\n  3. Applying solution again...")
    success2 = learning.apply_learned_solution(solution, {})

    assert solution.times_applied == 2
    assert solution.success_rate == 1.0
    print(f"     ✅ Solution reused (success rate: {solution.success_rate*100:.1f}%)")

    print("\n  ✅ Solution application working!")
    return True


def test_rag_storage_and_retrieval():
    """Test RAG storage and retrieval of solutions"""
    print("\n" + "=" * 70)
    print("TEST 4: RAG Storage & Retrieval")
    print("=" * 70)

    mock_llm = MockLLMClient()
    mock_rag = MockRAGAgent()
    learning = SupervisorLearningEngine(
        llm_client=mock_llm,
        rag_agent=mock_rag,
        verbose=True
    )

    print("\n  1. Learning and storing solution...")
    unexpected = UnexpectedState(
        state_id="test-unexpected-003",
        timestamp="2025-10-23T12:00:00Z",
        card_id="card-005",
        stage_name="code_review",
        error_message="Code review agent crashed",
        context={},
        stack_trace=None,
        previous_state="STAGE_RUNNING",
        current_state="STAGE_FAILED",
        expected_states=["STAGE_COMPLETED"],
        severity="critical"
    )

    solution = learning.learn_solution(unexpected, LearningStrategy.LLM_CONSULTATION)
    assert solution is not None

    print("\n  2. Verifying solution stored in RAG...")
    assert len(mock_rag.artifacts) > 0, "Should store in RAG"
    stored = mock_rag.artifacts[0]
    assert stored["artifact_type"] == "learned_solution"
    print(f"     ✅ Solution stored in RAG (artifact_id: {stored['artifact_id']})")

    print("\n  3. Querying similar solutions...")
    results = mock_rag.query_similar(
        query_text="code review failed",
        artifact_types=["learned_solution"],
        top_k=3
    )
    assert len(results) > 0, "Should find stored solution"
    print(f"     ✅ Found {len(results)} similar solution(s)")

    print("\n  ✅ RAG storage and retrieval working!")
    return True


def test_supervisor_integration():
    """Test integration with supervisor agent"""
    print("\n" + "=" * 70)
    print("TEST 5: Supervisor Integration")
    print("=" * 70)

    # Set mock environment
    os.environ["ARTEMIS_LLM_PROVIDER"] = "mock"
    os.environ["ARTEMIS_MESSENGER_TYPE"] = "mock"

    print("\n  1. Creating supervisor with learning disabled...")
    supervisor = SupervisorAgent(
        card_id="test-learning-001",
        verbose=True,
        enable_config_validation=False,
        enable_cost_tracking=False,
        enable_sandboxing=False
    )

    print("\n  2. Enabling learning capability...")
    mock_llm = MockLLMClient()
    supervisor.enable_learning(mock_llm)

    assert supervisor.learning_engine is not None
    print("     ✅ Learning engine enabled")

    print("\n  3. Handling unexpected state...")
    result = supervisor.handle_unexpected_state(
        current_state="STAGE_STUCK",
        expected_states=["STAGE_RUNNING", "STAGE_COMPLETED"],
        context={
            "stage_name": "development",
            "error_message": "Agents deadlocked"
        },
        auto_learn=True
    )

    assert result is not None
    assert result["action"] == "learned_and_applied"
    assert result["success"] is True
    print(f"     ✅ Unexpected state handled (action: {result['action']})")

    print("\n  4. Checking learning statistics...")
    stats = supervisor.get_statistics()

    assert "learning" in stats
    assert stats["learning"]["unexpected_states_detected"] == 1
    assert stats["learning"]["solutions_learned"] == 1
    assert stats["learning"]["solutions_applied"] == 1
    print(f"     ✅ Learning stats:")
    print(f"        Unexpected states: {stats['learning']['unexpected_states_detected']}")
    print(f"        Solutions learned: {stats['learning']['solutions_learned']}")
    print(f"        Solutions applied: {stats['learning']['solutions_applied']}")

    print("\n  5. Printing health report with learning stats...")
    supervisor.print_health_report()

    print("\n  ✅ Supervisor integration working!")
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("🧪 SUPERVISOR LEARNING - TEST SUITE")
    print("=" * 70)
    print("\nTesting supervisor learning capability:\n")
    print("  1. Detect Unexpected States")
    print("  2. LLM Consultation")
    print("  3. Apply Learned Solutions")
    print("  4. RAG Storage & Retrieval")
    print("  5. Supervisor Integration")
    print()

    tests = [
        ("Detect Unexpected States", test_detect_unexpected_state),
        ("LLM Consultation", test_llm_consultation),
        ("Apply Learned Solutions", test_apply_learned_solution),
        ("RAG Storage & Retrieval", test_rag_storage_and_retrieval),
        ("Supervisor Integration", test_supervisor_integration),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ TEST FAILED WITH EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Print summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")

    print(f"\n🎯 Result: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n🎉 SUPERVISOR LEARNING COMPLETE!")
        print("\n✨ Learning Capabilities:")
        print("\n  1️⃣  Unexpected State Detection")
        print("      • Detects when pipeline enters unexpected states")
        print("      • Assesses severity automatically")
        print("      • Captures full context for analysis")
        print("\n  2️⃣  LLM-Powered Solution Learning")
        print("      • Consults LLM (GPT-4o/Claude) for solutions")
        print("      • Generates structured recovery workflows")
        print("      • Extracts actionable steps from LLM response")
        print("\n  3️⃣  Dynamic Workflow Generation")
        print("      • Creates new recovery workflows on-the-fly")
        print("      • Applies workflows automatically")
        print("      • Tracks success rates over time")
        print("\n  4️⃣  Knowledge Retention (RAG)")
        print("      • Stores learned solutions in RAG")
        print("      • Retrieves similar past solutions")
        print("      • Improves over time through experience")
        print("\n  5️⃣  Supervisor Integration")
        print("      • enable_learning() to activate")
        print("      • handle_unexpected_state() for auto-recovery")
        print("      • query_learned_solutions() for lookup")
        print("      • Learning stats in health reports")
        print("\n🚀 Supervisor can now learn and adapt autonomously!")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
