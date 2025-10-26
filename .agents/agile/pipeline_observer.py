#!/usr/bin/env python3
"""
Pipeline Observer Pattern

Implements Observer Pattern for pipeline events, allowing multiple
observers to react to pipeline events without tight coupling.

Benefits:
- Decouples event producers from consumers (Open/Closed Principle)
- Easy to add new observers without modifying pipeline
- Centralized event handling
- Support for logging, monitoring, notifications, metrics

Event Types:
1. Pipeline events - start, complete, fail
2. Stage events - start, complete, fail, skip
3. Developer events - start, complete, fail
4. Code review events - start, complete, fail
5. Validation events - start, complete, fail
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

from artemis_services import PipelineLogger


# ============================================================================
# EVENT TYPES
# ============================================================================

class EventType(Enum):
    """Types of pipeline events"""

    # Pipeline lifecycle
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_COMPLETED = "pipeline_completed"
    PIPELINE_FAILED = "pipeline_failed"
    PIPELINE_PAUSED = "pipeline_paused"
    PIPELINE_RESUMED = "pipeline_resumed"

    # Stage lifecycle
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    STAGE_FAILED = "stage_failed"
    STAGE_SKIPPED = "stage_skipped"
    STAGE_RETRYING = "stage_retrying"
    STAGE_PROGRESS = "stage_progress"

    # Developer events
    DEVELOPER_STARTED = "developer_started"
    DEVELOPER_COMPLETED = "developer_completed"
    DEVELOPER_FAILED = "developer_failed"

    # Code review events
    CODE_REVIEW_STARTED = "code_review_started"
    CODE_REVIEW_COMPLETED = "code_review_completed"
    CODE_REVIEW_FAILED = "code_review_failed"

    # Validation events
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    VALIDATION_FAILED = "validation_failed"

    # Integration events
    INTEGRATION_STARTED = "integration_started"
    INTEGRATION_COMPLETED = "integration_completed"
    INTEGRATION_CONFLICT = "integration_conflict"

    # Workflow events
    WORKFLOW_TRIGGERED = "workflow_triggered"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"

    # Supervisor command events (bidirectional communication)
    SUPERVISOR_COMMAND_PAUSE = "supervisor_command_pause"
    SUPERVISOR_COMMAND_RESUME = "supervisor_command_resume"
    SUPERVISOR_COMMAND_CANCEL = "supervisor_command_cancel"
    SUPERVISOR_COMMAND_RETRY = "supervisor_command_retry"
    SUPERVISOR_COMMAND_SKIP = "supervisor_command_skip"
    SUPERVISOR_COMMAND_OVERRIDE = "supervisor_command_override"
    SUPERVISOR_COMMAND_FORCE_APPROVAL = "supervisor_command_force_approval"
    SUPERVISOR_COMMAND_FORCE_REJECTION = "supervisor_command_force_rejection"
    SUPERVISOR_COMMAND_SELECT_WINNER = "supervisor_command_select_winner"
    SUPERVISOR_COMMAND_CHANGE_PRIORITY = "supervisor_command_change_priority"
    SUPERVISOR_COMMAND_ADJUST_TIMEOUT = "supervisor_command_adjust_timeout"
    SUPERVISOR_COMMAND_REQUEST_STATUS = "supervisor_command_request_status"
    SUPERVISOR_COMMAND_EMERGENCY_STOP = "supervisor_command_emergency_stop"

    # Agent response events
    AGENT_COMMAND_ACKNOWLEDGED = "agent_command_acknowledged"
    AGENT_COMMAND_COMPLETED = "agent_command_completed"
    AGENT_COMMAND_FAILED = "agent_command_failed"
    AGENT_STATUS_RESPONSE = "agent_status_response"


# ============================================================================
# EVENT DATA
# ============================================================================

@dataclass
class PipelineEvent:
    """
    Represents a pipeline event

    Immutable event object passed to observers
    """
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    card_id: Optional[str] = None
    stage_name: Optional[str] = None
    developer_name: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Exception] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "card_id": self.card_id,
            "stage_name": self.stage_name,
            "developer_name": self.developer_name,
            "data": self.data,
            "error": str(self.error) if self.error else None
        }


# ============================================================================
# OBSERVER INTERFACE
# ============================================================================

class PipelineObserver(ABC):
    """
    Abstract base class for pipeline observers

    Observers implement this interface to receive pipeline events
    """

    @abstractmethod
    def on_event(self, event: PipelineEvent) -> None:
        """
        Handle pipeline event

        Args:
            event: Pipeline event to handle
        """
        pass

    def get_observer_name(self) -> str:
        """Get observer name for logging"""
        return self.__class__.__name__


# ============================================================================
# OBSERVABLE (SUBJECT)
# ============================================================================

class PipelineObservable:
    """
    Observable pipeline subject

    Manages observers and notifies them of events
    """

    def __init__(self, verbose: bool = True):
        self._observers: List[PipelineObserver] = []
        self.verbose = verbose
        self.logger = PipelineLogger(verbose=verbose)

    def attach(self, observer: PipelineObserver) -> None:
        """
        Attach observer to receive events

        Args:
            observer: Observer to attach
        """
        if observer not in self._observers:
            self._observers.append(observer)
            if self.verbose:
                self.logger.log(f"Attached observer: {observer.get_observer_name()}", "INFO")

    def detach(self, observer: PipelineObserver) -> None:
        """
        Detach observer from receiving events

        Args:
            observer: Observer to detach
        """
        if observer in self._observers:
            self._observers.remove(observer)
            if self.verbose:
                self.logger.log(f"Detached observer: {observer.get_observer_name()}", "INFO")

    def notify(self, event: PipelineEvent) -> None:
        """
        Notify all observers of event

        Args:
            event: Event to broadcast
        """
        if self.verbose:
            self.logger.log(
                f"Broadcasting event: {event.event_type.value} "
                f"(card_id={event.card_id}, stage={event.stage_name})",
                "DEBUG"
            )

        for observer in self._observers:
            try:
                observer.on_event(event)
            except Exception as e:
                # Don't let observer errors break the pipeline
                self.logger.log(
                    f"Observer {observer.get_observer_name()} failed to handle event: {e}",
                    "ERROR"
                )

    def get_observer_count(self) -> int:
        """Get number of attached observers"""
        return len(self._observers)


# ============================================================================
# CONCRETE OBSERVERS
# ============================================================================

class LoggingObserver(PipelineObserver):
    """
    Observer that logs all pipeline events

    Provides detailed logging of pipeline execution
    """

    def __init__(self, verbose: bool = True):
        self.logger = PipelineLogger(verbose=verbose)

    def on_event(self, event: PipelineEvent) -> None:
        """Log pipeline event"""

        # Determine log level
        if event.event_type.value.endswith("_failed"):
            level = "ERROR"
        elif event.event_type.value.endswith("_completed"):
            level = "SUCCESS"
        elif event.event_type.value.endswith("_started"):
            level = "INFO"
        else:
            level = "DEBUG"

        # Format message
        parts = [event.event_type.value.upper()]

        if event.card_id:
            parts.append(f"card_id={event.card_id}")

        if event.stage_name:
            parts.append(f"stage={event.stage_name}")

        if event.developer_name:
            parts.append(f"developer={event.developer_name}")

        if event.error:
            parts.append(f"error={event.error}")

        message = " | ".join(parts)
        self.logger.log(message, level)


class MetricsObserver(PipelineObserver):
    """
    Observer that collects pipeline metrics

    Tracks:
    - Stage durations
    - Success/failure rates
    - Retry counts
    - Developer performance
    """

    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "pipeline_starts": 0,
            "pipeline_completions": 0,
            "pipeline_failures": 0,
            "stage_durations": {},
            "stage_failures": {},
            "stage_retries": {},
            "developer_stats": {},
            "events": []
        }
        self.stage_start_times: Dict[str, datetime] = {}

    def on_event(self, event: PipelineEvent) -> None:
        """Collect metrics from event"""

        # Track event
        self.metrics["events"].append(event.to_dict())

        # Pipeline metrics
        if event.event_type == EventType.PIPELINE_STARTED:
            self.metrics["pipeline_starts"] += 1

        elif event.event_type == EventType.PIPELINE_COMPLETED:
            self.metrics["pipeline_completions"] += 1

        elif event.event_type == EventType.PIPELINE_FAILED:
            self.metrics["pipeline_failures"] += 1

        # Stage metrics
        elif event.event_type == EventType.STAGE_STARTED:
            if event.stage_name:
                self.stage_start_times[event.stage_name] = event.timestamp

        elif event.event_type == EventType.STAGE_COMPLETED:
            if event.stage_name and event.stage_name in self.stage_start_times:
                start = self.stage_start_times[event.stage_name]
                duration = (event.timestamp - start).total_seconds()

                if event.stage_name not in self.metrics["stage_durations"]:
                    self.metrics["stage_durations"][event.stage_name] = []

                self.metrics["stage_durations"][event.stage_name].append(duration)

        elif event.event_type == EventType.STAGE_FAILED:
            if event.stage_name:
                self.metrics["stage_failures"][event.stage_name] = \
                    self.metrics["stage_failures"].get(event.stage_name, 0) + 1

        elif event.event_type == EventType.STAGE_RETRYING:
            if event.stage_name:
                self.metrics["stage_retries"][event.stage_name] = \
                    self.metrics["stage_retries"].get(event.stage_name, 0) + 1

        # Developer metrics
        elif event.event_type in [EventType.DEVELOPER_STARTED, EventType.DEVELOPER_COMPLETED, EventType.DEVELOPER_FAILED]:
            if event.developer_name:
                if event.developer_name not in self.metrics["developer_stats"]:
                    self.metrics["developer_stats"][event.developer_name] = {
                        "started": 0,
                        "completed": 0,
                        "failed": 0
                    }

                if event.event_type == EventType.DEVELOPER_STARTED:
                    self.metrics["developer_stats"][event.developer_name]["started"] += 1
                elif event.event_type == EventType.DEVELOPER_COMPLETED:
                    self.metrics["developer_stats"][event.developer_name]["completed"] += 1
                elif event.event_type == EventType.DEVELOPER_FAILED:
                    self.metrics["developer_stats"][event.developer_name]["failed"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics"""
        return self.metrics

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary without full event list"""
        summary = self.metrics.copy()
        summary["event_count"] = len(summary["events"])
        del summary["events"]  # Don't include full event list in summary
        return summary


class StateTrackingObserver(PipelineObserver):
    """
    Observer that tracks current pipeline state

    Maintains:
    - Current stage
    - Active developers
    - Pipeline status
    - Recent errors
    """

    def __init__(self):
        self.current_card_id: Optional[str] = None
        self.current_stage: Optional[str] = None
        # Performance: Use set for O(1) add/remove instead of O(n) list operations
        self.active_developers: Set[str] = set()
        self.pipeline_status: str = "idle"
        self.recent_errors: List[str] = []
        self.max_errors = 10

    def on_event(self, event: PipelineEvent) -> None:
        """Update state based on event"""

        # Update card ID
        if event.card_id:
            self.current_card_id = event.card_id

        # Pipeline state
        if event.event_type == EventType.PIPELINE_STARTED:
            self.pipeline_status = "running"
            self.recent_errors = []

        elif event.event_type == EventType.PIPELINE_COMPLETED:
            self.pipeline_status = "completed"
            self.current_stage = None

        elif event.event_type == EventType.PIPELINE_FAILED:
            self.pipeline_status = "failed"

        elif event.event_type == EventType.PIPELINE_PAUSED:
            self.pipeline_status = "paused"

        # Stage state
        elif event.event_type == EventType.STAGE_STARTED:
            self.current_stage = event.stage_name

        elif event.event_type in [EventType.STAGE_COMPLETED, EventType.STAGE_FAILED, EventType.STAGE_SKIPPED]:
            if event.stage_name == self.current_stage:
                self.current_stage = None

        # Developer state (Performance: O(1) set operations instead of O(n) list)
        elif event.event_type == EventType.DEVELOPER_STARTED:
            if event.developer_name:
                self.active_developers.add(event.developer_name)

        elif event.event_type in [EventType.DEVELOPER_COMPLETED, EventType.DEVELOPER_FAILED]:
            if event.developer_name:
                self.active_developers.discard(event.developer_name)  # discard doesn't raise if not found

        # Error tracking
        if event.error:
            self.recent_errors.append(str(event.error))
            if len(self.recent_errors) > self.max_errors:
                self.recent_errors.pop(0)

    def get_state(self) -> Dict[str, Any]:
        """Get current pipeline state"""
        return {
            "card_id": self.current_card_id,
            "current_stage": self.current_stage,
            "active_developers": self.active_developers.copy(),
            "pipeline_status": self.pipeline_status,
            "recent_errors": self.recent_errors.copy()
        }


class NotificationObserver(PipelineObserver):
    """
    Observer that sends notifications for important events

    Can be extended to send:
    - Slack notifications
    - Email alerts
    - Webhook calls
    - Discord messages
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.notifications: List[Dict[str, Any]] = []

    def on_event(self, event: PipelineEvent) -> None:
        """Send notifications for important events"""

        # Only notify on important events
        important_events = [
            EventType.PIPELINE_COMPLETED,
            EventType.PIPELINE_FAILED,
            EventType.STAGE_FAILED,
            EventType.INTEGRATION_CONFLICT
        ]

        if event.event_type not in important_events:
            return

        notification = {
            "type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "card_id": event.card_id,
            "stage_name": event.stage_name,
            "message": self._format_notification(event)
        }

        self.notifications.append(notification)

        if self.verbose:
            print(f"[Notification] {notification['message']}")

    def _format_notification(self, event: PipelineEvent) -> str:
        """Format notification message"""

        if event.event_type == EventType.PIPELINE_COMPLETED:
            return f"✅ Pipeline completed successfully for {event.card_id}"

        elif event.event_type == EventType.PIPELINE_FAILED:
            return f"❌ Pipeline failed for {event.card_id}: {event.error}"

        elif event.event_type == EventType.STAGE_FAILED:
            return f"⚠️  Stage {event.stage_name} failed for {event.card_id}: {event.error}"

        elif event.event_type == EventType.INTEGRATION_CONFLICT:
            return f"⚠️  Integration conflict in {event.card_id}"

        return f"Event: {event.event_type.value}"

    def get_notifications(self) -> List[Dict[str, Any]]:
        """Get all notifications"""
        return self.notifications.copy()


# ============================================================================
# SUPERVISOR COMMAND OBSERVER
# ============================================================================

class SupervisorCommandObserver(PipelineObserver):
    """
    Observer that receives and executes supervisor commands

    This observer is attached to the pipeline observable and listens for
    SUPERVISOR_COMMAND_* events, then routes them to the appropriate stage/agent.

    Each stage implements command handlers that are registered with this observer.
    When a command event is received, the observer dispatches it to the registered handler.
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.logger = PipelineLogger(verbose=verbose)
        # Map of (stage_name, command_type) -> handler function
        self.command_handlers: Dict[tuple, callable] = {}
        # Command execution history
        self.command_history: List[Dict[str, Any]] = []

    def register_command_handler(
        self,
        stage_name: str,
        command_type: EventType,
        handler: callable
    ) -> None:
        """
        Register a command handler for a specific stage and command type

        Args:
            stage_name: Name of the stage (e.g., "ValidationStage", "ArbitrationStage")
            command_type: Type of command event to handle
            handler: Callable that takes (event: PipelineEvent) -> Dict
        """
        key = (stage_name, command_type)
        self.command_handlers[key] = handler

        if self.verbose:
            self.logger.log(
                f"Registered command handler: {stage_name} -> {command_type.value}",
                "DEBUG"
            )

    def unregister_command_handler(
        self,
        stage_name: str,
        command_type: EventType
    ) -> None:
        """Unregister a command handler"""
        key = (stage_name, command_type)
        if key in self.command_handlers:
            del self.command_handlers[key]

            if self.verbose:
                self.logger.log(
                    f"Unregistered command handler: {stage_name} -> {command_type.value}",
                    "DEBUG"
                )

    def on_event(self, event: PipelineEvent) -> None:
        """Handle supervisor command events"""

        # Only process supervisor command events
        if not event.event_type.value.startswith("supervisor_command_"):
            return

        stage_name = event.stage_name or event.data.get("target_stage")

        if not stage_name:
            self.logger.log(
                f"⚠️  Command {event.event_type.value} has no target stage",
                "WARNING"
            )
            return

        # Look up handler
        key = (stage_name, event.event_type)
        handler = self.command_handlers.get(key)

        if not handler:
            self.logger.log(
                f"⚠️  No handler registered for {stage_name} -> {event.event_type.value}",
                "WARNING"
            )
            return

        # Execute command
        try:
            self.logger.log(
                f"🎯 Executing command: {event.event_type.value} -> {stage_name}",
                "INFO"
            )

            result = handler(event)

            # Record command execution
            self.command_history.append({
                "timestamp": event.timestamp.isoformat(),
                "command": event.event_type.value,
                "stage": stage_name,
                "card_id": event.card_id,
                "result": result,
                "success": True
            })

            self.logger.log(
                f"✅ Command executed successfully: {event.event_type.value}",
                "SUCCESS"
            )

        except Exception as e:
            self.logger.log(
                f"❌ Command execution failed: {event.event_type.value} -> {e}",
                "ERROR"
            )

            # Record failure
            self.command_history.append({
                "timestamp": event.timestamp.isoformat(),
                "command": event.event_type.value,
                "stage": stage_name,
                "card_id": event.card_id,
                "error": str(e),
                "success": False
            })

    def get_command_history(self) -> List[Dict[str, Any]]:
        """Get command execution history"""
        return self.command_history.copy()

    def clear_command_history(self) -> None:
        """Clear command history"""
        self.command_history = []


# ============================================================================
# FACTORY FOR CREATING OBSERVERS
# ============================================================================

class ObserverFactory:
    """
    Factory for creating standard observers

    Makes it easy to set up common observer configurations
    """

    @staticmethod
    def create_default_observers(verbose: bool = True) -> List[PipelineObserver]:
        """
        Create default set of observers

        Returns:
            List of: LoggingObserver, MetricsObserver, StateTrackingObserver
        """
        return [
            LoggingObserver(verbose=verbose),
            MetricsObserver(),
            StateTrackingObserver()
        ]

    @staticmethod
    def create_minimal_observers() -> List[PipelineObserver]:
        """
        Create minimal set of observers (just logging)

        Returns:
            List with only LoggingObserver
        """
        return [LoggingObserver(verbose=True)]

    @staticmethod
    def create_full_observers(verbose: bool = True) -> List[PipelineObserver]:
        """
        Create full set of observers including notifications

        Returns:
            List of all observer types
        """
        return [
            LoggingObserver(verbose=verbose),
            MetricsObserver(),
            StateTrackingObserver(),
            NotificationObserver(verbose=verbose)
        ]


# ============================================================================
# EVENT BUILDER - Convenience for creating events
# ============================================================================

class EventBuilder:
    """
    Builder for creating pipeline events

    Provides convenient methods for creating common events
    """

    @staticmethod
    def pipeline_started(card_id: str, **data) -> PipelineEvent:
        """Create pipeline started event"""
        return PipelineEvent(
            event_type=EventType.PIPELINE_STARTED,
            card_id=card_id,
            data=data
        )

    @staticmethod
    def pipeline_completed(card_id: str, **data) -> PipelineEvent:
        """Create pipeline completed event"""
        return PipelineEvent(
            event_type=EventType.PIPELINE_COMPLETED,
            card_id=card_id,
            data=data
        )

    @staticmethod
    def pipeline_failed(card_id: str, error: Exception, **data) -> PipelineEvent:
        """Create pipeline failed event"""
        return PipelineEvent(
            event_type=EventType.PIPELINE_FAILED,
            card_id=card_id,
            error=error,
            data=data
        )

    @staticmethod
    def stage_started(card_id: str, stage_name: str, **data) -> PipelineEvent:
        """Create stage started event"""
        return PipelineEvent(
            event_type=EventType.STAGE_STARTED,
            card_id=card_id,
            stage_name=stage_name,
            data=data
        )

    @staticmethod
    def stage_completed(card_id: str, stage_name: str, **data) -> PipelineEvent:
        """Create stage completed event"""
        return PipelineEvent(
            event_type=EventType.STAGE_COMPLETED,
            card_id=card_id,
            stage_name=stage_name,
            data=data
        )

    @staticmethod
    def stage_failed(card_id: str, stage_name: str, error: Exception, **data) -> PipelineEvent:
        """Create stage failed event"""
        return PipelineEvent(
            event_type=EventType.STAGE_FAILED,
            card_id=card_id,
            stage_name=stage_name,
            error=error,
            data=data
        )

    @staticmethod
    def developer_started(card_id: str, developer_name: str, **data) -> PipelineEvent:
        """Create developer started event"""
        return PipelineEvent(
            event_type=EventType.DEVELOPER_STARTED,
            card_id=card_id,
            developer_name=developer_name,
            data=data
        )

    @staticmethod
    def developer_completed(card_id: str, developer_name: str, **data) -> PipelineEvent:
        """Create developer completed event"""
        return PipelineEvent(
            event_type=EventType.DEVELOPER_COMPLETED,
            card_id=card_id,
            developer_name=developer_name,
            data=data
        )
