#!/usr/bin/env python3
"""
Test Pipeline Observer Pattern

Tests Observer Pattern implementation for pipeline events
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from pipeline_observer import (
    EventType,
    PipelineEvent,
    PipelineObserver,
    PipelineObservable,
    LoggingObserver,
    MetricsObserver,
    StateTrackingObserver,
    NotificationObserver,
    ObserverFactory,
    EventBuilder
)


# ============================================================================
# TEST OBSERVERS
# ============================================================================

class TestObserver(PipelineObserver):
    """Test observer that records events"""

    def __init__(self):
        self.events = []

    def on_event(self, event: PipelineEvent) -> None:
        self.events.append(event)

    def get_event_count(self) -> int:
        return len(self.events)


# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def test_event_creation():
    """Test creating events"""
    print("\n" + "=" * 70)
    print("TEST 1: Event Creation")
    print("=" * 70)

    event = PipelineEvent(
        event_type=EventType.PIPELINE_STARTED,
        card_id="test-001",
        stage_name="development",
        data={"key": "value"}
    )

    assert event.event_type == EventType.PIPELINE_STARTED
    assert event.card_id == "test-001"
    assert event.stage_name == "development"
    assert event.data["key"] == "value"

    # Test to_dict
    event_dict = event.to_dict()
    assert event_dict["event_type"] == "pipeline_started"
    assert event_dict["card_id"] == "test-001"

    print("  ✅ Event created successfully")
    print(f"  ✅ Event type: {event.event_type.value}")
    return True


def test_observer_attach_detach():
    """Test attaching and detaching observers"""
    print("\n" + "=" * 70)
    print("TEST 2: Observer Attach/Detach")
    print("=" * 70)

    observable = PipelineObservable(verbose=False)
    observer1 = TestObserver()
    observer2 = TestObserver()

    # Attach observers
    observable.attach(observer1)
    observable.attach(observer2)
    assert observable.get_observer_count() == 2

    # Detach observer
    observable.detach(observer1)
    assert observable.get_observer_count() == 1

    print("  ✅ Observers attached/detached correctly")
    print(f"  ✅ Final observer count: {observable.get_observer_count()}")
    return True


def test_event_notification():
    """Test event notification to observers"""
    print("\n" + "=" * 70)
    print("TEST 3: Event Notification")
    print("=" * 70)

    observable = PipelineObservable(verbose=False)
    observer1 = TestObserver()
    observer2 = TestObserver()

    observable.attach(observer1)
    observable.attach(observer2)

    # Notify event
    event = PipelineEvent(
        event_type=EventType.STAGE_STARTED,
        card_id="test-001",
        stage_name="development"
    )
    observable.notify(event)

    # Both observers should have received event
    assert observer1.get_event_count() == 1
    assert observer2.get_event_count() == 1
    assert observer1.events[0].card_id == "test-001"

    print("  ✅ Event notified to all observers")
    print(f"  ✅ Observer1 events: {observer1.get_event_count()}")
    print(f"  ✅ Observer2 events: {observer2.get_event_count()}")
    return True


def test_logging_observer():
    """Test LoggingObserver"""
    print("\n" + "=" * 70)
    print("TEST 4: LoggingObserver")
    print("=" * 70)

    observer = LoggingObserver(verbose=False)

    # Test different event types
    events = [
        PipelineEvent(EventType.PIPELINE_STARTED, card_id="test-001"),
        PipelineEvent(EventType.STAGE_COMPLETED, card_id="test-001", stage_name="dev"),
        PipelineEvent(EventType.STAGE_FAILED, card_id="test-001", stage_name="test", error=Exception("Test error"))
    ]

    for event in events:
        observer.on_event(event)  # Should not raise

    print("  ✅ LoggingObserver handled all events")
    return True


def test_metrics_observer():
    """Test MetricsObserver"""
    print("\n" + "=" * 70)
    print("TEST 5: MetricsObserver")
    print("=" * 70)

    observer = MetricsObserver()

    # Simulate pipeline execution
    observer.on_event(PipelineEvent(EventType.PIPELINE_STARTED, card_id="test-001"))
    observer.on_event(PipelineEvent(EventType.STAGE_STARTED, card_id="test-001", stage_name="dev"))
    observer.on_event(PipelineEvent(EventType.STAGE_COMPLETED, card_id="test-001", stage_name="dev"))
    observer.on_event(PipelineEvent(EventType.PIPELINE_COMPLETED, card_id="test-001"))

    metrics = observer.get_metrics()

    assert metrics["pipeline_starts"] == 1
    assert metrics["pipeline_completions"] == 1
    assert len(metrics["events"]) == 4

    print("  ✅ MetricsObserver collected metrics")
    print(f"  ✅ Pipeline starts: {metrics['pipeline_starts']}")
    print(f"  ✅ Pipeline completions: {metrics['pipeline_completions']}")
    print(f"  ✅ Events tracked: {len(metrics['events'])}")
    return True


def test_state_tracking_observer():
    """Test StateTrackingObserver"""
    print("\n" + "=" * 70)
    print("TEST 6: StateTrackingObserver")
    print("=" * 70)

    observer = StateTrackingObserver()

    # Initial state
    state = observer.get_state()
    assert state["pipeline_status"] == "idle"
    assert state["current_stage"] is None

    # Start pipeline
    observer.on_event(PipelineEvent(EventType.PIPELINE_STARTED, card_id="test-001"))
    state = observer.get_state()
    assert state["pipeline_status"] == "running"
    assert state["card_id"] == "test-001"

    # Start stage
    observer.on_event(PipelineEvent(EventType.STAGE_STARTED, card_id="test-001", stage_name="dev"))
    state = observer.get_state()
    assert state["current_stage"] == "dev"

    # Start developer
    observer.on_event(PipelineEvent(EventType.DEVELOPER_STARTED, card_id="test-001", developer_name="dev-a"))
    state = observer.get_state()
    assert "dev-a" in state["active_developers"]

    # Complete developer
    observer.on_event(PipelineEvent(EventType.DEVELOPER_COMPLETED, card_id="test-001", developer_name="dev-a"))
    state = observer.get_state()
    assert "dev-a" not in state["active_developers"]

    print("  ✅ StateTrackingObserver tracked state correctly")
    print(f"  ✅ Final status: {state['pipeline_status']}")
    return True


def test_notification_observer():
    """Test NotificationObserver"""
    print("\n" + "=" * 70)
    print("TEST 7: NotificationObserver")
    print("=" * 70)

    observer = NotificationObserver(verbose=False)

    # Send various events
    observer.on_event(PipelineEvent(EventType.PIPELINE_STARTED, card_id="test-001"))  # Not important
    observer.on_event(PipelineEvent(EventType.PIPELINE_COMPLETED, card_id="test-001"))  # Important
    observer.on_event(PipelineEvent(EventType.STAGE_FAILED, card_id="test-001", stage_name="dev", error=Exception("Test")))  # Important

    notifications = observer.get_notifications()

    # Should only have 2 notifications (not the STARTED event)
    assert len(notifications) == 2
    assert notifications[0]["type"] == "pipeline_completed"
    assert notifications[1]["type"] == "stage_failed"

    print("  ✅ NotificationObserver sent notifications")
    print(f"  ✅ Notifications sent: {len(notifications)}")
    return True


def test_observer_factory():
    """Test ObserverFactory"""
    print("\n" + "=" * 70)
    print("TEST 8: ObserverFactory")
    print("=" * 70)

    # Default observers
    observers = ObserverFactory.create_default_observers(verbose=False)
    assert len(observers) == 3
    assert isinstance(observers[0], LoggingObserver)
    assert isinstance(observers[1], MetricsObserver)
    assert isinstance(observers[2], StateTrackingObserver)
    print(f"  ✅ Default observers: {len(observers)}")

    # Minimal observers
    observers = ObserverFactory.create_minimal_observers()
    assert len(observers) == 1
    assert isinstance(observers[0], LoggingObserver)
    print(f"  ✅ Minimal observers: {len(observers)}")

    # Full observers
    observers = ObserverFactory.create_full_observers(verbose=False)
    assert len(observers) == 4
    assert isinstance(observers[3], NotificationObserver)
    print(f"  ✅ Full observers: {len(observers)}")

    return True


def test_event_builder():
    """Test EventBuilder"""
    print("\n" + "=" * 70)
    print("TEST 9: EventBuilder")
    print("=" * 70)

    # Test pipeline events
    event = EventBuilder.pipeline_started("test-001", user="alice")
    assert event.event_type == EventType.PIPELINE_STARTED
    assert event.card_id == "test-001"
    assert event.data["user"] == "alice"
    print("  ✅ pipeline_started")

    event = EventBuilder.pipeline_completed("test-001", duration=120)
    assert event.event_type == EventType.PIPELINE_COMPLETED
    print("  ✅ pipeline_completed")

    event = EventBuilder.pipeline_failed("test-001", Exception("Test error"))
    assert event.event_type == EventType.PIPELINE_FAILED
    assert event.error is not None
    print("  ✅ pipeline_failed")

    # Test stage events
    event = EventBuilder.stage_started("test-001", "development")
    assert event.event_type == EventType.STAGE_STARTED
    assert event.stage_name == "development"
    print("  ✅ stage_started")

    event = EventBuilder.stage_completed("test-001", "development", files=5)
    assert event.event_type == EventType.STAGE_COMPLETED
    assert event.data["files"] == 5
    print("  ✅ stage_completed")

    # Test developer events
    event = EventBuilder.developer_started("test-001", "dev-a")
    assert event.event_type == EventType.DEVELOPER_STARTED
    assert event.developer_name == "dev-a"
    print("  ✅ developer_started")

    return True


def test_complete_pipeline_flow():
    """Test complete pipeline flow with observers"""
    print("\n" + "=" * 70)
    print("TEST 10: Complete Pipeline Flow")
    print("=" * 70)

    # Set up observable with all observers
    observable = PipelineObservable(verbose=False)
    metrics = MetricsObserver()
    state = StateTrackingObserver()
    notifications = NotificationObserver(verbose=False)

    observable.attach(metrics)
    observable.attach(state)
    observable.attach(notifications)

    # Simulate complete pipeline execution
    card_id = "test-001"

    # 1. Pipeline starts
    observable.notify(EventBuilder.pipeline_started(card_id))

    # 2. Stage 1: Development
    observable.notify(EventBuilder.stage_started(card_id, "development"))
    observable.notify(EventBuilder.developer_started(card_id, "dev-a"))
    observable.notify(EventBuilder.developer_completed(card_id, "dev-a"))
    observable.notify(EventBuilder.stage_completed(card_id, "development"))

    # 3. Stage 2: Code Review
    observable.notify(EventBuilder.stage_started(card_id, "code_review"))
    observable.notify(EventBuilder.stage_completed(card_id, "code_review"))

    # 4. Pipeline completes
    observable.notify(EventBuilder.pipeline_completed(card_id))

    # Verify metrics
    metrics_data = metrics.get_metrics()
    assert metrics_data["pipeline_starts"] == 1
    assert metrics_data["pipeline_completions"] == 1
    assert len(metrics_data["events"]) == 8

    # Verify state
    state_data = state.get_state()
    assert state_data["pipeline_status"] == "completed"
    assert state_data["card_id"] == card_id
    assert len(state_data["active_developers"]) == 0  # All completed

    # Verify notifications
    notifs = notifications.get_notifications()
    assert len(notifs) == 1  # Only completion notification
    assert notifs[0]["type"] == "pipeline_completed"

    print("  ✅ Complete pipeline flow executed")
    print(f"  ✅ Events processed: {len(metrics_data['events'])}")
    print(f"  ✅ Final status: {state_data['pipeline_status']}")
    print(f"  ✅ Notifications: {len(notifs)}")
    return True


def test_observer_error_handling():
    """Test that observer errors don't break pipeline"""
    print("\n" + "=" * 70)
    print("TEST 11: Observer Error Handling")
    print("=" * 70)

    class BrokenObserver(PipelineObserver):
        def on_event(self, event: PipelineEvent) -> None:
            raise Exception("Observer is broken!")

    observable = PipelineObservable(verbose=False)
    good_observer = TestObserver()
    broken_observer = BrokenObserver()

    observable.attach(good_observer)
    observable.attach(broken_observer)

    # Notify event - broken observer should not prevent good observer from receiving it
    event = PipelineEvent(EventType.PIPELINE_STARTED, card_id="test-001")
    observable.notify(event)

    # Good observer should still have received the event
    assert good_observer.get_event_count() == 1

    print("  ✅ Observer errors handled gracefully")
    print(f"  ✅ Good observer received event: {good_observer.get_event_count()}")
    return True


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("🧪 PIPELINE OBSERVER TEST SUITE")
    print("=" * 70)
    print("\nTesting Observer Pattern implementation for pipeline events\n")

    tests = [
        ("Event Creation", test_event_creation),
        ("Observer Attach/Detach", test_observer_attach_detach),
        ("Event Notification", test_event_notification),
        ("LoggingObserver", test_logging_observer),
        ("MetricsObserver", test_metrics_observer),
        ("StateTrackingObserver", test_state_tracking_observer),
        ("NotificationObserver", test_notification_observer),
        ("ObserverFactory", test_observer_factory),
        ("EventBuilder", test_event_builder),
        ("Complete Pipeline Flow", test_complete_pipeline_flow),
        ("Observer Error Handling", test_observer_error_handling),
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
        print("\n🎉 ALL TESTS PASSED! Observer Pattern implementation is working correctly.")
        print("\nObserver Pattern Benefits:")
        print("  • Decoupled event producers from consumers")
        print("  • Easy to add new observers without modifying pipeline")
        print("  • 4 concrete observers: Logging, Metrics, State, Notifications")
        print("  • Factory for easy observer setup")
        print("  • EventBuilder for convenient event creation")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
