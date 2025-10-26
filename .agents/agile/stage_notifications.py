#!/usr/bin/env python3
"""
Stage Notification Helper - DRY Observer Pattern Integration

Reduces 90+ lines of repetitive Observer pattern boilerplate to ~10 lines
by providing reusable notification helpers and decorators.

Design Patterns:
- DRY (Don't Repeat Yourself)
- Context Manager: Automatic start/complete notifications
- Decorator: Automatic progress notifications
"""

from contextlib import contextmanager
from functools import wraps
from typing import Any, Dict, Optional, Callable
from pipeline_observer import PipelineObservable, PipelineEvent, EventType


class StageNotificationHelper:
    """
    Helper class to reduce Observer pattern boilerplate

    Instead of writing 10 lines of event creation and notification code
    every time, use this helper to do it in 1 line.

    Example:
        # OLD WAY (10 lines):
        if self.observable:
            event = PipelineEvent(
                event_type=EventType.STAGE_STARTED,
                card_id=card_id,
                stage_name="sprint_planning",
                data={"task_title": task_title}
            )
            self.observable.notify(event)

        # NEW WAY (1 line):
        self.notifier.notify(EventType.STAGE_STARTED, card_id, {'task_title': task_title})
    """

    def __init__(self, observable: Optional[PipelineObservable], stage_name: str):
        """
        Initialize notification helper

        Args:
            observable: PipelineObservable instance (or None)
            stage_name: Name of the stage for event identification
        """
        self.observable = observable
        self.stage_name = stage_name

    def notify(
        self,
        event_type: EventType,
        card_id: str,
        data: Dict[str, Any] = None,
        **kwargs
    ):
        """
        Send notification if observable is available

        Args:
            event_type: Type of event (STAGE_STARTED, STAGE_PROGRESS, etc.)
            card_id: Card ID for the event
            data: Event data dictionary
            **kwargs: Additional keyword arguments passed to PipelineEvent
        """
        if not self.observable:
            return

        event = PipelineEvent(
            event_type=event_type,
            card_id=card_id,
            stage_name=self.stage_name,
            data=data or {},
            **kwargs
        )
        self.observable.notify(event)

    @contextmanager
    def stage_lifecycle(self, card_id: str, initial_data: Dict[str, Any] = None):
        """
        Context manager for automatic STAGE_STARTED/COMPLETED notifications

        Automatically sends:
        - STAGE_STARTED when entering context
        - STAGE_COMPLETED when exiting normally
        - STAGE_FAILED when exception occurs

        Usage:
            with self.notifier.stage_lifecycle(card_id, {'task': task_title}):
                # Do work
                # STAGE_STARTED sent automatically at entry
                result = self._do_work()
                # STAGE_COMPLETED sent automatically at exit

        Args:
            card_id: Card ID for notifications
            initial_data: Data for STAGE_STARTED event

        Yields:
            self (for method chaining if needed)
        """
        # Send STAGE_STARTED
        self.notify(EventType.STAGE_STARTED, card_id, initial_data)

        try:
            yield self
        except Exception as e:
            # Send STAGE_FAILED on exception
            self.notify(EventType.STAGE_FAILED, card_id, {
                'error': str(e),
                'error_type': type(e).__name__
            })
            raise
        else:
            # Send STAGE_COMPLETED on success
            self.notify(EventType.STAGE_COMPLETED, card_id)

    def notify_progress(
        self,
        card_id: str,
        step: str,
        progress_percent: int,
        **extra_data
    ):
        """
        Convenience method for progress notifications

        Args:
            card_id: Card ID
            step: Current step name
            progress_percent: Progress percentage (0-100)
            **extra_data: Additional data to include
        """
        data = {
            'step': step,
            'progress_percent': progress_percent,
            **extra_data
        }
        self.notify(EventType.STAGE_PROGRESS, card_id, data)


def notify_on_completion(
    event_type: EventType = EventType.STAGE_COMPLETED,
    data_extractor: Optional[Callable] = None
):
    """
    Decorator to automatically send notifications after method completes

    Usage:
        @notify_on_completion()
        def _process_features(self, card_id, features):
            # Method automatically sends STAGE_COMPLETED with return value
            return {'features_count': len(features)}

        @notify_on_completion(data_extractor=lambda result: {'count': result})
        def _count_items(self, card_id, items):
            return len(items)

    Args:
        event_type: Type of event to send (default: STAGE_COMPLETED)
        data_extractor: Function to extract data from result

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, card_id: str, *args, **kwargs):
            result = func(self, card_id, *args, **kwargs)

            # Send notification if helper is available
            if hasattr(self, 'notifier') and self.notifier:
                # Extract data from result
                if data_extractor:
                    data = data_extractor(result)
                elif isinstance(result, dict):
                    data = result
                else:
                    data = {'result': result}

                self.notifier.notify(event_type, card_id, data)

            return result
        return wrapper
    return decorator


# ============================================================================
# Backward Compatibility Helper
# ============================================================================

def create_notification_helper(
    observable: Optional[PipelineObservable],
    stage_name: str
) -> StageNotificationHelper:
    """
    Factory function to create notification helper

    This function exists for backward compatibility and to provide
    a clear entry point for stage initialization.

    Args:
        observable: PipelineObservable instance (or None)
        stage_name: Name of the stage

    Returns:
        StageNotificationHelper instance
    """
    return StageNotificationHelper(observable, stage_name)
