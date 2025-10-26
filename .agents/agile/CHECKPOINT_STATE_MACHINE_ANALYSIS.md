# Code Smells and Anti-Patterns Analysis
## checkpoint_manager.py and artemis_state_machine.py

## Code Smells Identified

### checkpoint_manager.py (618 lines)

**1. God Class / Too Many Responsibilities**
- CheckpointManager handles: checkpoint creation, stage tracking, metrics, LLM caching, file I/O, JSON serialization
- Violates Single Responsibility Principle
- Should be split into: CheckpointManager, CheckpointSerializer, CheckpointStorage

**2. Long Methods**
- `create_checkpoint()` - 30+ lines doing too much
- `resume_from_checkpoint()` - 30+ lines with complex logic
- `_save_checkpoint()` - Handles both serialization and file I/O

**3. Primitive Obsession**
- Uses dictionaries for checkpoint data instead of proper value objects
- Stage info stored as dicts rather than domain objects
- Makes code harder to maintain and test

**4. Feature Envy**
- Methods constantly access and modify checkpoint dict internals
- Suggests checkpoint data should be its own class

**5. Data Class**
- `PipelineCheckpoint` dataclass is anemic - just data, no behavior
- Business logic scattered across manager methods

**6. Magic Numbers/Strings**
- Hardcoded file extensions (".json")
- Status strings ("completed", "failed", "in_progress")
- Should be constants/enums

**7. Tight Coupling**
- Direct file system access throughout
- Hard to test without actual filesystem
- Should use Storage abstraction

### artemis_state_machine.py (987 lines)

**1. God Class**
- Handles: state transitions, workflow registration, event observation, persistence, recovery
- Massive class with too many concerns
- 987 lines indicates complexity overflow

**2. State Pattern Not Used**
- Ironically, a "state machine" not using State pattern
- Uses if/elif chains for state transitions
- Should use State objects with polymorphic behavior

**3. Long Methods**
- `transition_to()` - Complex validation and transition logic
- `_is_valid_transition()` - Long conditional chains
- Workflow methods are lengthy

**4. Primitive Obsession**
- States represented as strings/enums instead of objects
- Transition rules as nested dicts
- Should use State objects with behavior

**5. Feature Envy**
- Constantly checking and manipulating state dicts
- State behavior should be in State objects

**6. Shotgun Surgery**
- Adding new state requires changes in multiple methods
- Should be localized to State classes

**7. Duplicate Code**
- Similar patterns for handling different states
- Recovery workflow code repetitive
- Should use polymorphism

## Design Pattern Recommendations

### For CheckpointManager

**1. Strategy Pattern - Checkpoint Storage**
```python
class CheckpointStorage(ABC):
    @abstractmethod
    def save(self, checkpoint: Checkpoint) -> None: pass
    @abstractmethod
    def load(self, checkpoint_id: str) -> Checkpoint: pass

class FileCheckpointStorage(CheckpointStorage):
    # File-based implementation

class S3CheckpointStorage(CheckpointStorage):
    # S3-based implementation
```

**2. Builder Pattern - Checkpoint Construction**
```python
class CheckpointBuilder:
    def set_card_id(self, card_id: str) -> 'CheckpointBuilder':
        self._card_id = card_id
        return self

    def add_stage(self, stage_name: str, status: str) -> 'CheckpointBuilder':
        self._stages.append((stage_name, status))
        return self

    def build(self) -> Checkpoint:
        return Checkpoint(...)
```

**3. Repository Pattern - Checkpoint Access**
```python
class CheckpointRepository:
    def __init__(self, storage: CheckpointStorage):
        self.storage = storage

    def find_by_card_id(self, card_id: str) -> Optional[Checkpoint]:
        pass

    def save(self, checkpoint: Checkpoint) -> None:
        pass
```

**4. Value Object Pattern - Rich Domain Objects**
```python
@dataclass(frozen=True)
class StageResult:
    stage_name: str
    status: StageStatus  # Enum
    duration: float

    def is_successful(self) -> bool:
        return self.status == StageStatus.COMPLETED
```

### For StateMachine

**1. State Pattern - Polymorphic State Behavior**
```python
class PipelineState(ABC):
    @abstractmethod
    def handle_transition(self, target_state: str, context: StateContext) -> bool:
        pass

    @abstractmethod
    def on_enter(self, context: StateContext) -> None:
        pass

    @abstractmethod
    def on_exit(self, context: StateContext) -> None:
        pass

class IdleState(PipelineState):
    def handle_transition(self, target_state: str, context: StateContext) -> bool:
        # Idle can transition to RUNNING
        return target_state == "RUNNING"
```

**2. Command Pattern - State Transitions**
```python
class StateTransitionCommand(ABC):
    @abstractmethod
    def execute(self, state_machine: StateMachine) -> bool:
        pass

class StartPipelineCommand(StateTransitionCommand):
    def execute(self, state_machine: StateMachine) -> bool:
        return state_machine.transition_to(PipelineState.RUNNING)
```

**3. Observer Pattern - State Change Notifications** (Already used)
- Good pattern usage
- Could be enhanced with event bus

**4. Memento Pattern - State Snapshots**
```python
class StateMemento:
    def __init__(self, state: dict):
        self._state = copy.deepcopy(state)

    def get_state(self) -> dict:
        return copy.deepcopy(self._state)

class StateMachine:
    def create_memento(self) -> StateMemento:
        return StateMemento(self._get_state_dict())

    def restore(self, memento: StateMemento) -> None:
        self._restore_state(memento.get_state())
```

**5. Chain of Responsibility - Transition Validation**
```python
class TransitionValidator(ABC):
    def __init__(self, next_validator: Optional['TransitionValidator'] = None):
        self.next = next_validator

    def validate(self, from_state: str, to_state: str) -> bool:
        if not self._check(from_state, to_state):
            return False
        if self.next:
            return self.next.validate(from_state, to_state)
        return True

    @abstractmethod
    def _check(self, from_state: str, to_state: str) -> bool:
        pass
```

## Recommended Refactoring Priority

### High Priority (Critical Issues)
1. **Split God Classes** - Both files violate SRP heavily
2. **Apply State Pattern** to state_machine.py - Core domain logic
3. **Add Storage Abstraction** - Enables testing, flexibility

### Medium Priority (Maintainability)
4. **Builder Pattern** for checkpoint construction
5. **Value Objects** for domain concepts
6. **Extract constants** for magic strings

### Low Priority (Nice to Have)
7. **Command Pattern** for transitions
8. **Enhanced Observer** with event bus
9. **Memento Pattern** for sophisticated snapshots

## Benefits of Refactoring

**Testability**
- Mock storage instead of filesystem
- Test state behavior in isolation
- Inject dependencies

**Maintainability**
- Smaller, focused classes
- Clear responsibilities
- Easier to understand

**Extensibility**
- Add new states without modifying existing code
- Swap storage implementations
- Add validation rules via chain

**Flexibility**
- Support multiple storage backends
- Different serialization formats
- Custom state behaviors per environment
