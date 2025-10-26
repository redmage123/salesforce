#!/usr/bin/env python3
"""
Artemis State Machine - Refactored with Design Patterns

Improvements over original:
1. State Pattern - Polymorphic state behavior instead of if/elif chains
2. Command Pattern - Encapsulated state transitions
3. Memento Pattern - State snapshots for rollback
4. Chain of Responsibility - Transition validation
5. Strategy Pattern - Pluggable persistence
6. Value Objects - Rich domain models
7. Repository Pattern - State persistence abstraction

Design Patterns Applied:
- State Pattern: PipelineState subclasses with polymorphic behavior
- Command Pattern: StateTransitionCommand for encapsulated transitions
- Memento Pattern: StateMemento for snapshots
- Chain of Responsibility: TransitionValidator chain
- Strategy Pattern: StatePersistence implementations
- Observer Pattern: StateObserver for notifications (enhanced)
- Repository Pattern: StateRepository for data access
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set, Protocol
from enum import Enum
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict
from abc import ABC, abstractmethod
import copy

from artemis_constants import RETRY_BACKOFF_FACTOR


# ============================================================================
# ENUMS - Type Safety
# ============================================================================

class PipelineStateType(Enum):
    """Pipeline execution state types"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
    RECOVERING = "recovering"
    DEGRADED = "degraded"
    ROLLING_BACK = "rolling_back"
    STAGE_RUNNING = "stage_running"
    STAGE_COMPLETED = "stage_completed"
    STAGE_FAILED = "stage_failed"
    STAGE_SKIPPED = "stage_skipped"
    STAGE_RETRYING = "stage_retrying"
    HEALTHY = "healthy"
    DEGRADED_HEALTH = "degraded_health"
    CRITICAL = "critical"


class StageStateType(Enum):
    """Individual stage states"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"
    CIRCUIT_OPEN = "circuit_open"
    TIMED_OUT = "timed_out"
    ROLLED_BACK = "rolled_back"


class EventType(Enum):
    """Events that trigger state transitions"""
    START = "start"
    COMPLETE = "complete"
    FAIL = "fail"
    ABORT = "abort"
    PAUSE = "pause"
    RESUME = "resume"
    STAGE_START = "stage_start"
    STAGE_COMPLETE = "stage_complete"
    STAGE_FAIL = "stage_fail"
    STAGE_RETRY = "stage_retry"
    STAGE_SKIP = "stage_skip"
    STAGE_TIMEOUT = "stage_timeout"
    RECOVERY_START = "recovery_start"
    RECOVERY_SUCCESS = "recovery_success"
    RECOVERY_FAIL = "recovery_fail"
    ROLLBACK_START = "rollback_start"
    ROLLBACK_COMPLETE = "rollback_complete"
    HEALTH_DEGRADED = "health_degraded"
    HEALTH_CRITICAL = "health_critical"
    HEALTH_RESTORED = "health_restored"
    CIRCUIT_OPEN = "circuit_open"
    CIRCUIT_CLOSE = "circuit_close"


class IssueType(Enum):
    """Types of issues that can occur"""
    TIMEOUT = "timeout"
    HANGING_PROCESS = "hanging_process"
    MEMORY_EXHAUSTED = "memory_exhausted"
    DISK_FULL = "disk_full"
    NETWORK_ERROR = "network_error"
    COMPILATION_ERROR = "compilation_error"
    TEST_FAILURE = "test_failure"
    SECURITY_VULNERABILITY = "security_vulnerability"
    LINTING_ERROR = "linting_error"
    MISSING_DEPENDENCY = "missing_dependency"
    VERSION_CONFLICT = "version_conflict"
    IMPORT_ERROR = "import_error"
    LLM_API_ERROR = "llm_api_error"
    LLM_TIMEOUT = "llm_timeout"
    LLM_RATE_LIMIT = "llm_rate_limit"
    INVALID_LLM_RESPONSE = "invalid_llm_response"
    ARCHITECTURE_INVALID = "architecture_invalid"
    CODE_REVIEW_FAILED = "code_review_failed"
    INTEGRATION_CONFLICT = "integration_conflict"
    VALIDATION_FAILED = "validation_failed"
    ARBITRATION_DEADLOCK = "arbitration_deadlock"
    DEVELOPER_CONFLICT = "developer_conflict"
    MESSENGER_ERROR = "messenger_error"
    INVALID_CARD = "invalid_card"
    CORRUPTED_STATE = "corrupted_state"
    RAG_ERROR = "rag_error"
    ZOMBIE_PROCESS = "zombie_process"
    FILE_LOCK = "file_lock"
    PERMISSION_DENIED = "permission_denied"


# ============================================================================
# VALUE OBJECTS - Rich Domain Models
# ============================================================================

@dataclass(frozen=True)
class StateTransitionRecord:
    """Immutable record of a state transition"""
    from_state: PipelineStateType
    to_state: PipelineStateType
    event: EventType
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "event": self.event.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "reason": self.reason
        }


@dataclass(frozen=True)
class StageInfo:
    """Immutable stage information"""
    stage_name: str
    state: StageStateType
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    retry_count: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_completed(self) -> bool:
        return self.state == StageStateType.COMPLETED

    def is_failed(self) -> bool:
        return self.state == StageStateType.FAILED

    def with_state(self, new_state: StageStateType) -> 'StageInfo':
        """Create new instance with updated state"""
        return StageInfo(
            stage_name=self.stage_name,
            state=new_state,
            start_time=self.start_time,
            end_time=self.end_time,
            duration_seconds=self.duration_seconds,
            retry_count=self.retry_count,
            error_message=self.error_message,
            metadata=self.metadata
        )

    def with_completion(self, end_time: datetime) -> 'StageInfo':
        """Create new instance with completion details"""
        duration = 0.0
        if self.start_time:
            duration = (end_time - self.start_time).total_seconds()

        return StageInfo(
            stage_name=self.stage_name,
            state=self.state,
            start_time=self.start_time,
            end_time=end_time,
            duration_seconds=duration,
            retry_count=self.retry_count,
            error_message=self.error_message,
            metadata=self.metadata
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_name": self.stage_name,
            "state": self.state.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


# ============================================================================
# STATE PATTERN - Polymorphic State Behavior
# ============================================================================

class StateContext:
    """Context for state behavior"""
    def __init__(self, card_id: str, verbose: bool = True):
        self.card_id = card_id
        self.verbose = verbose
        self.stage_states: Dict[str, StageInfo] = {}
        self.active_issues: Set[IssueType] = set()
        self.metadata: Dict[str, Any] = {}


class PipelineState(ABC):
    """Abstract base class for pipeline states (State Pattern)"""

    @abstractmethod
    def get_state_type(self) -> PipelineStateType:
        """Get the state type"""
        pass

    @abstractmethod
    def can_transition_to(self, target_state: PipelineStateType, context: StateContext) -> bool:
        """Check if transition to target state is valid"""
        pass

    @abstractmethod
    def on_enter(self, context: StateContext) -> None:
        """Called when entering this state"""
        pass

    @abstractmethod
    def on_exit(self, context: StateContext) -> None:
        """Called when exiting this state"""
        pass

    def get_valid_transitions(self) -> Set[PipelineStateType]:
        """Get set of valid next states"""
        return set()


class IdleState(PipelineState):
    """Idle state - pipeline not started"""

    def get_state_type(self) -> PipelineStateType:
        return PipelineStateType.IDLE

    def can_transition_to(self, target_state: PipelineStateType, context: StateContext) -> bool:
        return target_state in {PipelineStateType.INITIALIZING, PipelineStateType.ABORTED}

    def on_enter(self, context: StateContext) -> None:
        if context.verbose:
            print("[StateMachine] Entered IDLE state")

    def on_exit(self, context: StateContext) -> None:
        if context.verbose:
            print("[StateMachine] Exiting IDLE state")

    def get_valid_transitions(self) -> Set[PipelineStateType]:
        return {PipelineStateType.INITIALIZING, PipelineStateType.ABORTED}


class InitializingState(PipelineState):
    """Initializing state - setting up pipeline"""

    def get_state_type(self) -> PipelineStateType:
        return PipelineStateType.INITIALIZING

    def can_transition_to(self, target_state: PipelineStateType, context: StateContext) -> bool:
        return target_state in {
            PipelineStateType.RUNNING,
            PipelineStateType.FAILED,
            PipelineStateType.ABORTED
        }

    def on_enter(self, context: StateContext) -> None:
        if context.verbose:
            print("[StateMachine] Initializing pipeline...")

    def on_exit(self, context: StateContext) -> None:
        pass

    def get_valid_transitions(self) -> Set[PipelineStateType]:
        return {PipelineStateType.RUNNING, PipelineStateType.FAILED, PipelineStateType.ABORTED}


class RunningState(PipelineState):
    """Running state - active execution"""

    def get_state_type(self) -> PipelineStateType:
        return PipelineStateType.RUNNING

    def can_transition_to(self, target_state: PipelineStateType, context: StateContext) -> bool:
        return target_state in {
            PipelineStateType.STAGE_RUNNING,
            PipelineStateType.PAUSED,
            PipelineStateType.COMPLETED,
            PipelineStateType.FAILED,
            PipelineStateType.DEGRADED,
            PipelineStateType.ABORTED
        }

    def on_enter(self, context: StateContext) -> None:
        if context.verbose:
            print("[StateMachine] Pipeline running")

    def on_exit(self, context: StateContext) -> None:
        pass

    def get_valid_transitions(self) -> Set[PipelineStateType]:
        return {
            PipelineStateType.STAGE_RUNNING,
            PipelineStateType.PAUSED,
            PipelineStateType.COMPLETED,
            PipelineStateType.FAILED,
            PipelineStateType.DEGRADED,
            PipelineStateType.ABORTED
        }


class CompletedState(PipelineState):
    """Completed state - terminal success"""

    def get_state_type(self) -> PipelineStateType:
        return PipelineStateType.COMPLETED

    def can_transition_to(self, target_state: PipelineStateType, context: StateContext) -> bool:
        return False  # Terminal state

    def on_enter(self, context: StateContext) -> None:
        if context.verbose:
            print("[StateMachine] Pipeline completed successfully!")

    def on_exit(self, context: StateContext) -> None:
        pass

    def get_valid_transitions(self) -> Set[PipelineStateType]:
        return set()


class FailedState(PipelineState):
    """Failed state - execution failed"""

    def get_state_type(self) -> PipelineStateType:
        return PipelineStateType.FAILED

    def can_transition_to(self, target_state: PipelineStateType, context: StateContext) -> bool:
        return target_state in {
            PipelineStateType.RECOVERING,
            PipelineStateType.ROLLING_BACK,
            PipelineStateType.ABORTED
        }

    def on_enter(self, context: StateContext) -> None:
        if context.verbose:
            print("[StateMachine] Pipeline FAILED")

    def on_exit(self, context: StateContext) -> None:
        pass

    def get_valid_transitions(self) -> Set[PipelineStateType]:
        return {
            PipelineStateType.RECOVERING,
            PipelineStateType.ROLLING_BACK,
            PipelineStateType.ABORTED
        }


class RecoveringState(PipelineState):
    """Recovering state - attempting recovery"""

    def get_state_type(self) -> PipelineStateType:
        return PipelineStateType.RECOVERING

    def can_transition_to(self, target_state: PipelineStateType, context: StateContext) -> bool:
        return target_state in {
            PipelineStateType.RUNNING,
            PipelineStateType.DEGRADED,
            PipelineStateType.FAILED,
            PipelineStateType.ROLLING_BACK
        }

    def on_enter(self, context: StateContext) -> None:
        if context.verbose:
            print("[StateMachine] Attempting recovery...")

    def on_exit(self, context: StateContext) -> None:
        pass

    def get_valid_transitions(self) -> Set[PipelineStateType]:
        return {
            PipelineStateType.RUNNING,
            PipelineStateType.DEGRADED,
            PipelineStateType.FAILED,
            PipelineStateType.ROLLING_BACK
        }


# ============================================================================
# STATE FACTORY
# ============================================================================

class StateFactory:
    """Factory for creating state instances (Factory Pattern)"""

    _state_map: Dict[PipelineStateType, type] = {
        PipelineStateType.IDLE: IdleState,
        PipelineStateType.INITIALIZING: InitializingState,
        PipelineStateType.RUNNING: RunningState,
        PipelineStateType.COMPLETED: CompletedState,
        PipelineStateType.FAILED: FailedState,
        PipelineStateType.RECOVERING: RecoveringState,
    }

    @classmethod
    def create_state(cls, state_type: PipelineStateType) -> PipelineState:
        """Create state instance for given type"""
        state_class = cls._state_map.get(state_type)
        if not state_class:
            # For states not yet fully implemented, use a default
            return IdleState()
        return state_class()


# ============================================================================
# COMMAND PATTERN - State Transitions
# ============================================================================

class StateTransitionCommand(ABC):
    """Abstract command for state transitions (Command Pattern)"""

    @abstractmethod
    def execute(self, state_machine: 'ArtemisStateMachineRefactored') -> bool:
        """Execute the transition"""
        pass

    @abstractmethod
    def undo(self, state_machine: 'ArtemisStateMachineRefactored') -> bool:
        """Undo the transition (if possible)"""
        pass


class StartPipelineCommand(StateTransitionCommand):
    """Command to start pipeline"""

    def __init__(self, reason: Optional[str] = None):
        self.reason = reason
        self.previous_state: Optional[PipelineStateType] = None

    def execute(self, state_machine: 'ArtemisStateMachineRefactored') -> bool:
        self.previous_state = state_machine.current_state_type
        return state_machine.transition(
            PipelineStateType.RUNNING,
            EventType.START,
            self.reason
        )

    def undo(self, state_machine: 'ArtemisStateMachineRefactored') -> bool:
        if self.previous_state:
            return state_machine.transition(
                self.previous_state,
                EventType.ROLLBACK_COMPLETE,
                "Undo start"
            )
        return False


class FailPipelineCommand(StateTransitionCommand):
    """Command to fail pipeline"""

    def __init__(self, reason: Optional[str] = None):
        self.reason = reason
        self.previous_state: Optional[PipelineStateType] = None

    def execute(self, state_machine: 'ArtemisStateMachineRefactored') -> bool:
        self.previous_state = state_machine.current_state_type
        return state_machine.transition(
            PipelineStateType.FAILED,
            EventType.FAIL,
            self.reason
        )

    def undo(self, state_machine: 'ArtemisStateMachineRefactored') -> bool:
        # Cannot undo failure easily
        return False


# ============================================================================
# CHAIN OF RESPONSIBILITY - Transition Validation
# ============================================================================

class TransitionValidator(ABC):
    """Base validator in chain (Chain of Responsibility Pattern)"""

    def __init__(self, next_validator: Optional['TransitionValidator'] = None):
        self.next = next_validator

    def validate(
        self,
        from_state: PipelineStateType,
        to_state: PipelineStateType,
        context: StateContext
    ) -> tuple[bool, Optional[str]]:
        """
        Validate transition

        Returns:
            (is_valid, error_message)
        """
        # Check this validator
        is_valid, error = self._check(from_state, to_state, context)
        if not is_valid:
            return False, error

        # Check next in chain
        if self.next:
            return self.next.validate(from_state, to_state, context)

        return True, None

    @abstractmethod
    def _check(
        self,
        from_state: PipelineStateType,
        to_state: PipelineStateType,
        context: StateContext
    ) -> tuple[bool, Optional[str]]:
        """Perform specific validation"""
        pass


class StateRulesValidator(TransitionValidator):
    """Validates against state transition rules"""

    def _check(
        self,
        from_state: PipelineStateType,
        to_state: PipelineStateType,
        context: StateContext
    ) -> tuple[bool, Optional[str]]:
        # Get valid transitions for current state
        state = StateFactory.create_state(from_state)
        if to_state not in state.get_valid_transitions():
            return False, f"Invalid transition: {from_state.value} → {to_state.value}"
        return True, None


class HealthCheckValidator(TransitionValidator):
    """Validates health status before certain transitions"""

    def _check(
        self,
        from_state: PipelineStateType,
        to_state: PipelineStateType,
        context: StateContext
    ) -> tuple[bool, Optional[str]]:
        # Don't allow starting if critical issues exist
        if to_state == PipelineStateType.RUNNING and len(context.active_issues) >= 3:
            return False, f"Cannot start with {len(context.active_issues)} critical issues"
        return True, None


# ============================================================================
# MEMENTO PATTERN - State Snapshots
# ============================================================================

@dataclass
class StateMemento:
    """Memento for state snapshots (Memento Pattern)"""
    state_type: PipelineStateType
    timestamp: datetime
    card_id: str
    stage_states: Dict[str, StageInfo]
    active_issues: Set[IssueType]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_type": self.state_type.value,
            "timestamp": self.timestamp.isoformat(),
            "card_id": self.card_id,
            "stage_states": {k: v.to_dict() for k, v in self.stage_states.items()},
            "active_issues": [issue.value for issue in self.active_issues],
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateMemento':
        return cls(
            state_type=PipelineStateType(data["state_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            card_id=data["card_id"],
            stage_states={
                k: StageInfo(
                    stage_name=v["stage_name"],
                    state=StageStateType(v["state"]),
                    start_time=datetime.fromisoformat(v["start_time"]) if v["start_time"] else None,
                    end_time=datetime.fromisoformat(v["end_time"]) if v["end_time"] else None,
                    duration_seconds=v["duration_seconds"],
                    retry_count=v["retry_count"],
                    error_message=v["error_message"],
                    metadata=v["metadata"]
                )
                for k, v in data["stage_states"].items()
            },
            active_issues={IssueType(issue) for issue in data["active_issues"]},
            metadata=data["metadata"]
        )


# ============================================================================
# STRATEGY PATTERN - State Persistence
# ============================================================================

class StatePersistence(ABC):
    """Abstract persistence strategy (Strategy Pattern)"""

    @abstractmethod
    def save(self, memento: StateMemento) -> None:
        """Save state memento"""
        pass

    @abstractmethod
    def load(self, card_id: str) -> Optional[StateMemento]:
        """Load state memento"""
        pass

    @abstractmethod
    def exists(self, card_id: str) -> bool:
        """Check if state exists"""
        pass


class FileStatePersistence(StatePersistence):
    """File-based state persistence"""

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_dir.mkdir(exist_ok=True, parents=True)

    def save(self, memento: StateMemento) -> None:
        state_file = self.state_dir / f"{memento.card_id}_state.json"
        with open(state_file, 'w') as f:
            json.dump(memento.to_dict(), f, indent=2)

    def load(self, card_id: str) -> Optional[StateMemento]:
        state_file = self.state_dir / f"{card_id}_state.json"
        if not state_file.exists():
            return None

        with open(state_file, 'r') as f:
            data = json.load(f)

        return StateMemento.from_dict(data)

    def exists(self, card_id: str) -> bool:
        state_file = self.state_dir / f"{card_id}_state.json"
        return state_file.exists()


class InMemoryStatePersistence(StatePersistence):
    """In-memory state persistence (for testing)"""

    def __init__(self):
        self._states: Dict[str, StateMemento] = {}

    def save(self, memento: StateMemento) -> None:
        # Deep copy to prevent mutation
        self._states[memento.card_id] = copy.deepcopy(memento)

    def load(self, card_id: str) -> Optional[StateMemento]:
        if card_id not in self._states:
            return None
        return copy.deepcopy(self._states[card_id])

    def exists(self, card_id: str) -> bool:
        return card_id in self._states


# ============================================================================
# OBSERVER PATTERN - State Change Notifications (Enhanced)
# ============================================================================

class StateObserver(ABC):
    """Observer for state changes (Observer Pattern)"""

    @abstractmethod
    def on_state_change(
        self,
        from_state: PipelineStateType,
        to_state: PipelineStateType,
        event: EventType,
        context: StateContext
    ) -> None:
        """Called when state changes"""
        pass


class LoggingObserver(StateObserver):
    """Observer that logs state changes"""

    def on_state_change(
        self,
        from_state: PipelineStateType,
        to_state: PipelineStateType,
        event: EventType,
        context: StateContext
    ) -> None:
        print(f"[Observer] State change: {from_state.value} → {to_state.value} (event: {event.value})")


# ============================================================================
# REFACTORED STATE MACHINE
# ============================================================================

class ArtemisStateMachineRefactored:
    """
    Refactored state machine using design patterns

    Design Patterns:
    - State Pattern: Polymorphic state behavior
    - Command Pattern: Encapsulated transitions
    - Memento Pattern: State snapshots
    - Chain of Responsibility: Validation chain
    - Strategy Pattern: Pluggable persistence
    - Observer Pattern: State change notifications
    - Factory Pattern: State creation
    """

    def __init__(
        self,
        card_id: str,
        state_dir: Optional[str] = None,
        persistence: Optional[StatePersistence] = None,
        verbose: bool = True
    ):
        """
        Initialize refactored state machine

        Args:
            card_id: Kanban card ID
            state_dir: Directory for state persistence
            persistence: Custom persistence strategy (optional)
            verbose: Enable verbose logging
        """
        import os

        self.card_id = card_id
        self.verbose = verbose

        # Context for state behavior
        self.context = StateContext(card_id, verbose)

        # Current state
        self.current_state_type = PipelineStateType.IDLE
        self.current_state = StateFactory.create_state(self.current_state_type)

        # State history
        self.state_history: List[StateTransitionRecord] = []

        # Observers
        self.observers: List[StateObserver] = []
        if verbose:
            self.observers.append(LoggingObserver())

        # Persistence strategy
        if persistence:
            self.persistence = persistence
        else:
            if state_dir is None:
                state_dir = os.getenv("ARTEMIS_STATE_DIR", "../../.artemis_data/state")
            self.persistence = FileStatePersistence(Path(state_dir))

        # Validation chain
        self.validator = StateRulesValidator(
            next_validator=HealthCheckValidator()
        )

        # Command history for undo
        self.command_history: List[StateTransitionCommand] = []

        # Memento stack for rollback
        self.memento_stack: List[StateMemento] = []

        # Statistics
        self.stats = {
            "total_transitions": 0,
            "successful_transitions": 0,
            "failed_transitions": 0
        }

        if self.verbose:
            print(f"[StateMachine] Initialized (refactored) for card {card_id}")
            print(f"[StateMachine] Persistence: {type(self.persistence).__name__}")

    def transition(
        self,
        to_state: PipelineStateType,
        event: EventType,
        reason: Optional[str] = None,
        **metadata
    ) -> bool:
        """
        Transition to new state with validation

        Args:
            to_state: Target state
            event: Event triggering transition
            reason: Optional reason
            **metadata: Additional metadata

        Returns:
            True if transition succeeded
        """
        from_state = self.current_state_type

        # Validate transition
        is_valid, error = self.validator.validate(from_state, to_state, self.context)
        if not is_valid:
            if self.verbose:
                print(f"[StateMachine] ⚠️  Transition validation failed: {error}")
            self.stats["failed_transitions"] += 1
            return False

        # Save memento before transition
        self._save_memento()

        # Exit current state
        self.current_state.on_exit(self.context)

        # Create transition record
        record = StateTransitionRecord(
            from_state=from_state,
            to_state=to_state,
            event=event,
            timestamp=datetime.now(),
            metadata=metadata,
            reason=reason
        )
        self.state_history.append(record)

        # Update state
        self.current_state_type = to_state
        self.current_state = StateFactory.create_state(to_state)

        # Enter new state
        self.current_state.on_enter(self.context)

        # Notify observers
        for observer in self.observers:
            observer.on_state_change(from_state, to_state, event, self.context)

        # Persist state
        self._persist_state()

        # Update stats
        self.stats["total_transitions"] += 1
        self.stats["successful_transitions"] += 1

        return True

    def execute_command(self, command: StateTransitionCommand) -> bool:
        """Execute state transition command"""
        success = command.execute(self)
        if success:
            self.command_history.append(command)
        return success

    def update_stage_state(
        self,
        stage_name: str,
        state: StageStateType,
        **metadata
    ) -> None:
        """Update stage state"""
        if stage_name not in self.context.stage_states:
            stage_info = StageInfo(
                stage_name=stage_name,
                state=state,
                start_time=datetime.now(),
                metadata=metadata
            )
        else:
            existing = self.context.stage_states[stage_name]
            stage_info = existing.with_state(state)

            # Update completion details
            if state in {StageStateType.COMPLETED, StageStateType.FAILED}:
                stage_info = stage_info.with_completion(datetime.now())

        self.context.stage_states[stage_name] = stage_info
        self._persist_state()

    def register_issue(self, issue_type: IssueType) -> None:
        """Register an active issue"""
        self.context.active_issues.add(issue_type)
        if self.verbose:
            print(f"[StateMachine] 🚨 Issue registered: {issue_type.value}")

    def resolve_issue(self, issue_type: IssueType) -> None:
        """Resolve an active issue"""
        if issue_type in self.context.active_issues:
            self.context.active_issues.remove(issue_type)
            if self.verbose:
                print(f"[StateMachine] ✅ Issue resolved: {issue_type.value}")

    def create_memento(self) -> StateMemento:
        """Create state memento"""
        return StateMemento(
            state_type=self.current_state_type,
            timestamp=datetime.now(),
            card_id=self.card_id,
            stage_states=dict(self.context.stage_states),
            active_issues=set(self.context.active_issues),
            metadata=dict(self.context.metadata)
        )

    def restore_memento(self, memento: StateMemento) -> None:
        """Restore from memento"""
        self.current_state_type = memento.state_type
        self.current_state = StateFactory.create_state(memento.state_type)
        self.context.stage_states = dict(memento.stage_states)
        self.context.active_issues = set(memento.active_issues)
        self.context.metadata = dict(memento.metadata)

        if self.verbose:
            print(f"[StateMachine] Restored state from memento: {memento.state_type.value}")

    def rollback_to_previous(self) -> bool:
        """Rollback to previous state using memento stack"""
        if not self.memento_stack:
            if self.verbose:
                print("[StateMachine] ⚠️  No previous state to rollback to")
            return False

        memento = self.memento_stack.pop()
        self.restore_memento(memento)
        return True

    def add_observer(self, observer: StateObserver) -> None:
        """Add state observer"""
        self.observers.append(observer)

    def remove_observer(self, observer: StateObserver) -> None:
        """Remove state observer"""
        if observer in self.observers:
            self.observers.remove(observer)

    def _save_memento(self) -> None:
        """Save current state to memento stack"""
        memento = self.create_memento()
        self.memento_stack.append(memento)

        # Limit stack size
        if len(self.memento_stack) > 10:
            self.memento_stack.pop(0)

    def _persist_state(self) -> None:
        """Persist state using strategy"""
        memento = self.create_memento()
        self.persistence.save(memento)

    def get_stats(self) -> Dict[str, Any]:
        """Get state machine statistics"""
        return {
            **self.stats,
            "current_state": self.current_state_type.value,
            "total_stages": len(self.context.stage_states),
            "active_issues": len(self.context.active_issues),
            "memento_stack_depth": len(self.memento_stack),
            "command_history_length": len(self.command_history)
        }


# ============================================================================
# FACADE - Backward Compatible Interface
# ============================================================================

class ArtemisStateMachine:
    """
    Facade providing backward-compatible interface to refactored state machine

    This allows existing code to continue working while using the improved
    implementation under the hood.
    """

    def __init__(
        self,
        card_id: str,
        state_dir: Optional[str] = None,
        verbose: bool = True
    ):
        """Initialize state machine (backward compatible)"""
        self._machine = ArtemisStateMachineRefactored(
            card_id=card_id,
            state_dir=state_dir,
            verbose=verbose
        )

        # Expose properties for backward compatibility
        self.card_id = card_id
        self.verbose = verbose
        self.state_dir = self._machine.persistence.state_dir if isinstance(
            self._machine.persistence, FileStatePersistence
        ) else None

    @property
    def current_state(self):
        """Get current state (backward compatible)"""
        # Map refactored enum to original enum
        from artemis_state_machine import PipelineState as OriginalPipelineState
        state_map = {
            PipelineStateType.IDLE: OriginalPipelineState.IDLE,
            PipelineStateType.RUNNING: OriginalPipelineState.RUNNING,
            PipelineStateType.COMPLETED: OriginalPipelineState.COMPLETED,
            PipelineStateType.FAILED: OriginalPipelineState.FAILED,
            # Add more mappings as needed
        }
        return state_map.get(self._machine.current_state_type, OriginalPipelineState.IDLE)

    def transition(
        self,
        to_state,  # Can accept original enum
        event,
        reason: Optional[str] = None,
        **metadata
    ) -> bool:
        """Transition to new state (backward compatible)"""
        # Map original enum to refactored enum
        from artemis_state_machine import PipelineState as OriginalPipelineState
        state_map = {
            OriginalPipelineState.IDLE: PipelineStateType.IDLE,
            OriginalPipelineState.RUNNING: PipelineStateType.RUNNING,
            OriginalPipelineState.COMPLETED: PipelineStateType.COMPLETED,
            OriginalPipelineState.FAILED: PipelineStateType.FAILED,
            # Add more mappings as needed
        }

        refactored_state = state_map.get(to_state, PipelineStateType.IDLE)
        return self._machine.transition(refactored_state, event, reason, **metadata)

    def update_stage_state(self, stage_name: str, state, **metadata) -> None:
        """Update stage state (backward compatible)"""
        self._machine.update_stage_state(stage_name, state, **metadata)

    def register_issue(self, issue_type: IssueType) -> None:
        """Register issue (backward compatible)"""
        self._machine.register_issue(issue_type)

    def resolve_issue(self, issue_type: IssueType) -> None:
        """Resolve issue (backward compatible)"""
        self._machine.resolve_issue(issue_type)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_state_machine(
    card_id: str,
    use_refactored: bool = True,
    verbose: bool = True
) -> ArtemisStateMachine:
    """
    Create state machine instance

    Args:
        card_id: Kanban card ID
        use_refactored: Whether to use refactored version (default True)
        verbose: Enable verbose logging

    Returns:
        State machine instance
    """
    return ArtemisStateMachine(card_id=card_id, verbose=verbose)
