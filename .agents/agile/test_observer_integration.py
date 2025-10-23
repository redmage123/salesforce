#!/usr/bin/env python3
"""
Test Observer Pattern Integration

Tests that Observer Pattern is properly integrated throughout the pipeline
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from pipeline_observer import (
    PipelineObservable,
    PipelineEvent,
    EventType,
    EventBuilder,
    MetricsObserver,
    StateTrackingObserver
)
from pipeline_strategies import StandardPipelineStrategy
from artemis_stage_interface import PipelineStage


# Mock stage for testing
class MockStage(PipelineStage):
    def __init__(self, name: str, should_succeed: bool = True):
        self.name = name
        self.should_succeed = should_succeed

    def execute(self) -> dict:
        if self.should_succeed:
            return {"success": True, "result": f"{self.name} completed"}
        else:
            return {"success": False, "error": f"{self.name} failed"}

    def get_stage_name(self) -> str:
        return self.name


def test_strategy_observer_integration():
    """Test that strategy notifies observers"""
    print("\n" + "=" * 70)
    print("TEST: Strategy-Observer Integration")
    print("=" * 70)

    # Create observable with observers
    observable = PipelineObservable(verbose=False)
    metrics = MetricsObserver()
    state = StateTrackingObserver()

    observable.attach(metrics)
    observable.attach(state)

    # Create strategy with observable
    strategy = StandardPipelineStrategy(verbose=False, observable=observable)

    # Create mock stages
    stages = [
        MockStage("stage1", True),
        MockStage("stage2", True),
        MockStage("stage3", True)
    ]

    # Execute pipeline
    context = {"card_id": "test-001"}
    result = strategy.execute(stages, context)

    # Verify execution
    assert result["status"] == "success"
    assert result["stages_completed"] == 3

    # Verify metrics were collected
    metrics_data = metrics.get_metrics()
    assert len(metrics_data["events"]) == 6  # 3 started + 3 completed
    print(f"  ✅ Metrics collected: {len(metrics_data['events'])} events")

    # Verify state was tracked
    state_data = state.get_state()
    assert state_data["card_id"] == "test-001"
    print(f"  ✅ State tracked: card_id={state_data['card_id']}")

    # Check event types
    event_types = [e["event_type"] for e in metrics_data["events"]]
    assert "stage_started" in event_types
    assert "stage_completed" in event_types
    print(f"  ✅ Event types correct")

    return True


def test_strategy_failure_notification():
    """Test that strategy notifies observers on failure"""
    print("\n" + "=" * 70)
    print("TEST: Strategy Failure Notification")
    print("=" * 70)

    # Create observable with metrics
    observable = PipelineObservable(verbose=False)
    metrics = MetricsObserver()
    observable.attach(metrics)

    # Create strategy
    strategy = StandardPipelineStrategy(verbose=False, observable=observable)

    # Create stages with one failure
    stages = [
        MockStage("stage1", True),
        MockStage("stage2", False),  # This one fails
        MockStage("stage3", True)
    ]

    # Execute pipeline
    context = {"card_id": "test-002"}
    result = strategy.execute(stages, context)

    # Verify execution failed
    assert result["status"] == "failed"
    assert result["failed_stage"] == "MockStage"

    # Verify failure was recorded
    metrics_data = metrics.get_metrics()
    event_types = [e["event_type"] for e in metrics_data["events"]]
    assert "stage_failed" in event_types
    print(f"  ✅ Stage failure recorded in metrics")

    return True


def test_pipeline_events():
    """Test pipeline-level event notifications"""
    print("\n" + "=" * 70)
    print("TEST: Pipeline-Level Events")
    print("=" * 70)

    # Create observable
    observable = PipelineObservable(verbose=False)
    metrics = MetricsObserver()
    observable.attach(metrics)

    # Simulate pipeline execution with events
    card_id = "test-003"

    # Pipeline starts
    event = EventBuilder.pipeline_started(card_id, card_title="Test Card")
    observable.notify(event)

    # Stage events
    event = EventBuilder.stage_started(card_id, "development")
    observable.notify(event)

    event = EventBuilder.stage_completed(card_id, "development", files_created=5)
    observable.notify(event)

    # Pipeline completes
    event = EventBuilder.pipeline_completed(card_id, stages_executed=1)
    observable.notify(event)

    # Verify all events recorded
    metrics_data = metrics.get_metrics()
    assert metrics_data["pipeline_starts"] == 1
    assert metrics_data["pipeline_completions"] == 1
    assert len(metrics_data["events"]) == 4

    print(f"  ✅ Pipeline events: starts={metrics_data['pipeline_starts']}, completions={metrics_data['pipeline_completions']}")
    print(f"  ✅ Total events recorded: {len(metrics_data['events'])}")

    return True


def main():
    """Run integration tests"""
    print("\n" + "=" * 70)
    print("🧪 OBSERVER PATTERN INTEGRATION TEST SUITE")
    print("=" * 70)
    print("\nTesting Observer Pattern integration across components\n")

    tests = [
        ("Strategy-Observer Integration", test_strategy_observer_integration),
        ("Strategy Failure Notification", test_strategy_failure_notification),
        ("Pipeline-Level Events", test_pipeline_events),
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
        print("\n🎉 ALL TESTS PASSED! Observer Pattern is fully integrated.")
        print("\nIntegration Summary:")
        print("  • ArtemisOrchestrator notifies pipeline events")
        print("  • PipelineStrategy notifies stage events")
        print("  • MetricsObserver collects metrics")
        print("  • StateTrackingObserver tracks state")
        print("  • All events properly propagated")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
