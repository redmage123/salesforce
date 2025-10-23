#!/usr/bin/env python3
"""
Test Pipeline Strategies

Tests all 4 pipeline execution strategies to ensure they work correctly.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from pipeline_strategies import (
    StandardPipelineStrategy,
    FastPipelineStrategy,
    ParallelPipelineStrategy,
    CheckpointPipelineStrategy,
    get_strategy
)
from artemis_stage_interface import PipelineStage


# ============================================================================
# MOCK STAGES FOR TESTING
# ============================================================================

class MockStage(PipelineStage):
    """Mock stage for testing"""

    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.executed = False

    def execute(self) -> dict:
        """Execute mock stage"""
        self.executed = True

        if self.should_fail:
            return {
                "success": False,
                "error": f"Mock stage {self.name} failed intentionally"
            }

        return {
            "success": True,
            "result": f"Mock stage {self.name} completed"
        }

    def get_stage_name(self) -> str:
        return self.name


# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def test_standard_strategy():
    """Test StandardPipelineStrategy"""
    print("\n" + "=" * 70)
    print("TEST 1: StandardPipelineStrategy")
    print("=" * 70)

    strategy = StandardPipelineStrategy(verbose=True)

    # Create mock stages
    stages = [
        MockStage("project_analysis"),
        MockStage("architecture"),
        MockStage("development"),
    ]

    context = {"card_id": "test-001"}

    # Execute
    result = strategy.execute(stages, context)

    # Verify
    assert result["status"] == "success", f"Expected success, got {result['status']}"
    assert result["stages_completed"] == 3, f"Expected 3 stages, got {result['stages_completed']}"
    assert all(s.executed for s in stages), "All stages should be executed"

    print(f"✅ StandardPipelineStrategy test PASSED")
    print(f"   Stages completed: {result['stages_completed']}")
    print(f"   Duration: {result['duration_seconds']:.2f}s")

    return True


def test_standard_strategy_failure():
    """Test StandardPipelineStrategy with failure"""
    print("\n" + "=" * 70)
    print("TEST 2: StandardPipelineStrategy (with failure)")
    print("=" * 70)

    strategy = StandardPipelineStrategy(verbose=True)

    # Create mock stages with one failure
    stages = [
        MockStage("project_analysis"),
        MockStage("architecture", should_fail=True),  # This one fails
        MockStage("development"),
    ]

    context = {"card_id": "test-002"}

    # Execute
    result = strategy.execute(stages, context)

    # Verify
    assert result["status"] == "failed", f"Expected failed, got {result['status']}"
    assert result["stages_completed"] == 1, f"Expected 1 stage, got {result['stages_completed']}"
    assert result["failed_stage"] == "MockStage", "Should report failed stage"
    assert stages[0].executed, "First stage should execute"
    assert stages[1].executed, "Second stage should execute (and fail)"
    assert not stages[2].executed, "Third stage should NOT execute"

    print(f"✅ StandardPipelineStrategy failure test PASSED")
    print(f"   Failed at stage: {result['failed_stage']}")
    print(f"   Error: {result['error']}")

    return True


def test_fast_strategy():
    """Test FastPipelineStrategy"""
    print("\n" + "=" * 70)
    print("TEST 3: FastPipelineStrategy")
    print("=" * 70)

    # Skip "architecture" stage
    strategy = FastPipelineStrategy(skip_stages=["architecture"], verbose=True)

    stages = [
        MockStage("project_analysis"),
        MockStage("architecture"),
        MockStage("development"),
    ]

    context = {"card_id": "test-003"}

    # Execute
    result = strategy.execute(stages, context)

    # Verify
    assert result["status"] == "success", f"Expected success, got {result['status']}"
    assert result["stages_completed"] == 2, f"Expected 2 stages (1 skipped), got {result['stages_completed']}"
    assert result["stages_skipped"] == 1, f"Expected 1 skipped, got {result['stages_skipped']}"
    assert stages[0].executed, "Project analysis should execute"
    assert not stages[1].executed, "Architecture should be SKIPPED"
    assert stages[2].executed, "Development should execute"

    print(f"✅ FastPipelineStrategy test PASSED")
    print(f"   Stages completed: {result['stages_completed']}")
    print(f"   Stages skipped: {result['stages_skipped']}")

    return True


def test_parallel_strategy():
    """Test ParallelPipelineStrategy"""
    print("\n" + "=" * 70)
    print("TEST 4: ParallelPipelineStrategy")
    print("=" * 70)

    strategy = ParallelPipelineStrategy(max_workers=2, verbose=True)

    stages = [
        MockStage("project_analysis"),
        MockStage("dependencies"),
        MockStage("architecture"),
        MockStage("development"),
    ]

    context = {"card_id": "test-004"}

    # Execute
    result = strategy.execute(stages, context)

    # Verify
    assert result["status"] == "success", f"Expected success, got {result['status']}"
    assert result["stages_completed"] == 4, f"Expected 4 stages, got {result['stages_completed']}"
    assert all(s.executed for s in stages), "All stages should be executed"
    assert "execution_groups" in result, "Should report execution groups"

    print(f"✅ ParallelPipelineStrategy test PASSED")
    print(f"   Stages completed: {result['stages_completed']}")
    print(f"   Execution groups: {result['execution_groups']}")
    print(f"   Duration: {result['duration_seconds']:.2f}s")

    return True


def test_checkpoint_strategy():
    """Test CheckpointPipelineStrategy"""
    print("\n" + "=" * 70)
    print("TEST 5: CheckpointPipelineStrategy")
    print("=" * 70)

    import tempfile
    checkpoint_dir = tempfile.mkdtemp()

    strategy = CheckpointPipelineStrategy(checkpoint_dir=checkpoint_dir, verbose=True)

    stages = [
        MockStage("project_analysis"),
        MockStage("architecture"),
        MockStage("development"),
    ]

    context = {"card_id": "test-005"}

    # Execute
    result = strategy.execute(stages, context)

    # Verify
    assert result["status"] == "success", f"Expected success, got {result['status']}"
    assert result["stages_completed"] == 3, f"Expected 3 stages, got {result['stages_completed']}"
    assert result["resumed"] == False, "First run should not be resumed"
    assert result.get("checkpoint_cleared") == True, "Checkpoint should be cleared on success"
    assert all(s.executed for s in stages), "All stages should be executed"

    print(f"✅ CheckpointPipelineStrategy test PASSED")
    print(f"   Stages completed: {result['stages_completed']}")
    print(f"   Resumed: {result['resumed']}")
    print(f"   Checkpoint cleared: {result.get('checkpoint_cleared')}")

    return True


def test_checkpoint_resume():
    """Test CheckpointPipelineStrategy resume functionality"""
    print("\n" + "=" * 70)
    print("TEST 6: CheckpointPipelineStrategy (resume)")
    print("=" * 70)

    import tempfile
    checkpoint_dir = tempfile.mkdtemp()

    strategy = CheckpointPipelineStrategy(checkpoint_dir=checkpoint_dir, verbose=True)

    # First run - fail at stage 2
    stages_run1 = [
        MockStage("project_analysis"),
        MockStage("architecture", should_fail=True),  # Fails here
        MockStage("development"),
    ]

    context = {"card_id": "test-006"}

    print("\n--- First execution (will fail) ---")
    result1 = strategy.execute(stages_run1, context)

    assert result1["status"] == "failed", "First run should fail"
    assert result1["stages_completed"] == 1, "Should complete 1 stage before failure"
    assert result1.get("checkpoint_saved") == True, "Should save checkpoint"

    # Second run - resume from checkpoint
    stages_run2 = [
        MockStage("project_analysis"),
        MockStage("architecture"),  # Now succeeds
        MockStage("development"),
    ]

    print("\n--- Second execution (resume from checkpoint) ---")
    result2 = strategy.execute(stages_run2, context)

    assert result2["status"] == "success", "Second run should succeed"
    assert result2["resumed"] == True, "Should indicate resumed from checkpoint"
    assert not stages_run2[0].executed, "Stage 1 should be SKIPPED (already completed)"
    assert stages_run2[1].executed, "Stage 2 should execute (previously failed)"
    assert stages_run2[2].executed, "Stage 3 should execute"

    print(f"✅ CheckpointPipelineStrategy resume test PASSED")
    print(f"   Run 1: Failed at stage 2, checkpoint saved")
    print(f"   Run 2: Resumed from checkpoint, completed successfully")

    return True


def test_strategy_factory():
    """Test get_strategy factory function"""
    print("\n" + "=" * 70)
    print("TEST 7: Strategy Factory (get_strategy)")
    print("=" * 70)

    # Test creating each strategy type
    strategies = {
        "standard": StandardPipelineStrategy,
        "fast": FastPipelineStrategy,
        "parallel": ParallelPipelineStrategy,
        "checkpoint": CheckpointPipelineStrategy
    }

    for name, expected_class in strategies.items():
        strategy = get_strategy(name, verbose=False)
        assert isinstance(strategy, expected_class), \
            f"Expected {expected_class.__name__}, got {strategy.__class__.__name__}"
        print(f"   ✅ {name} → {strategy.__class__.__name__}")

    # Test unknown strategy
    try:
        get_strategy("unknown")
        assert False, "Should raise ValueError for unknown strategy"
    except ValueError as e:
        print(f"   ✅ Unknown strategy correctly raises ValueError: {e}")

    print(f"✅ Strategy Factory test PASSED")

    return True


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("🧪 PIPELINE STRATEGY TEST SUITE")
    print("=" * 70)
    print("\nTesting 4 pipeline strategies + factory function")

    tests = [
        ("StandardPipelineStrategy (success)", test_standard_strategy),
        ("StandardPipelineStrategy (failure)", test_standard_strategy_failure),
        ("FastPipelineStrategy", test_fast_strategy),
        ("ParallelPipelineStrategy", test_parallel_strategy),
        ("CheckpointPipelineStrategy", test_checkpoint_strategy),
        ("CheckpointPipelineStrategy (resume)", test_checkpoint_resume),
        ("Strategy Factory", test_strategy_factory),
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
        print("\n🎉 ALL TESTS PASSED! Strategy Pattern implementation is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
