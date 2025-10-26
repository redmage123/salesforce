# Refactoring Integration Guide

## Overview

This document explains how to integrate the refactored components into the Artemis pipeline.

## Refactored Files

### 1. config_validator_refactored.py
**Purpose:** Validates Artemis configuration with design patterns
**Design Patterns Applied:**
- Configuration Object Pattern (ArtemisConfig)
- Strategy Pattern (ValidationStrategy implementations)
- Chain of Responsibility (ValidationPipeline)
- Factory Pattern (ValidatorFactory)
- Enums for type safety (Severity, LLMProvider, etc.)

**Key Improvements:**
- Eliminates code duplication (repeated os.getenv calls)
- Separates concerns (validation logic from config reading)
- Testable (can inject mock configs)
- Extensible (add new validators easily)

### 2. artemis_checkpoint_manager_refactored.py
**Purpose:** Manages pipeline checkpoints with design patterns
**Design Patterns Applied:**
- Value Object Pattern (StageResult, Checkpoint - immutable domain objects)
- Builder Pattern (CheckpointBuilder for complex construction)
- Strategy Pattern (CheckpointStorage ABC with File/InMemory implementations)
- Repository Pattern (CheckpointRepository for data access)
- Facade Pattern (CheckpointManager for backward compatibility)
- Enums for type safety (StageStatus, CheckpointStatus)

**Key Improvements:**
- Splits God Class into focused classes
- Pluggable storage backends (File, S3, InMemory)
- Immutable value objects prevent bugs
- Repository abstracts data access
- Backward compatible via Facade

### 3. artemis_state_machine_refactored.py
**Purpose:** Manages pipeline state transitions with design patterns
**Design Patterns Applied:**
- State Pattern (PipelineState subclasses with polymorphic behavior)
- Command Pattern (StateTransitionCommand for encapsulated transitions)
- Memento Pattern (StateMemento for state snapshots)
- Chain of Responsibility (TransitionValidator chain)
- Strategy Pattern (StatePersistence implementations)
- Observer Pattern (StateObserver for notifications - enhanced)
- Factory Pattern (StateFactory for state creation)
- Facade Pattern (ArtemisStateMachine for backward compatibility)

**Key Improvements:**
- Eliminates if/elif chains with polymorphic states
- Encapsulated transition logic in Command objects
- Rollback capability via Memento pattern
- Validation chain for transition rules
- Pluggable persistence (File/InMemory)
- Enhanced observer for state change notifications
- Backward compatible via Facade

## Integration Strategy

### Phase 1: Side-by-Side Testing (Recommended)
Run both old and refactored versions in parallel to verify correctness.

**Approach:**
1. Keep existing files unchanged
2. Import refactored versions with `_refactored` suffix
3. Add feature flag to switch between implementations
4. Compare outputs and validate behavior

**Example for artemis_orchestrator.py:**
```python
# At top of file
USE_REFACTORED_COMPONENTS = os.getenv("ARTEMIS_USE_REFACTORED", "false").lower() == "true"

if USE_REFACTORED_COMPONENTS:
    from config_validator_refactored import ConfigValidator, ArtemisConfig
    from artemis_checkpoint_manager_refactored import CheckpointManager
    from artemis_state_machine_refactored import ArtemisStateMachine
else:
    from config_validator import ConfigValidator
    from checkpoint_manager import CheckpointManager
    from artemis_state_machine import ArtemisStateMachine
```

### Phase 2: Gradual Migration
Migrate one component at a time.

**Recommended Order:**
1. **config_validator** (lowest risk - only used at startup)
2. **checkpoint_manager** (medium risk - file I/O, but isolated)
3. **state_machine** (highest risk - core pipeline logic)

### Phase 3: Full Replacement
Once validated, replace old files completely.

**Steps:**
1. Backup old files: `mv checkpoint_manager.py checkpoint_manager_legacy.py`
2. Remove `_refactored` suffix: `mv artemis_checkpoint_manager_refactored.py artemis_checkpoint_manager.py`
3. Update imports in all files
4. Remove feature flag
5. Run full test suite

## Integration Points

### Files That Import These Components

#### config_validator imports:
```bash
grep -r "from config_validator import" . --include="*.py"
grep -r "import config_validator" . --include="*.py"
```

Expected files:
- artemis_orchestrator.py
- preflight_validator.py

#### checkpoint_manager imports:
```bash
grep -r "from checkpoint_manager import" . --include="*.py"
grep -r "import checkpoint_manager" . --include="*.py"
```

Expected files:
- artemis_orchestrator.py
- artemis_state_machine.py
- artemis_stages.py

#### artemis_state_machine imports:
```bash
grep -r "from artemis_state_machine import" . --include="*.py"
grep -r "import artemis_state_machine" . --include="*.py"
```

Expected files:
- artemis_orchestrator.py
- artemis_stages.py
- supervisor_agent.py

## Backward Compatibility

All refactored files include **Facade Pattern** implementations that maintain the original interface.

### config_validator_refactored.py
```python
class ConfigValidator:
    """Facade providing backward-compatible interface"""
    def __init__(self):
        self.config = ArtemisConfig.from_env()
        # ... uses refactored implementation internally

    def validate(self) -> bool:
        # Original interface preserved
```

### artemis_checkpoint_manager_refactored.py
```python
class CheckpointManager:
    """Facade providing backward-compatible interface"""
    def __init__(self, card_id: str, checkpoint_dir: Optional[str] = None, ...):
        # Original signature preserved
        # Uses refactored components internally
```

### artemis_state_machine_refactored.py
```python
class ArtemisStateMachine:
    """Facade providing backward-compatible interface"""
    def __init__(self, card_id: str, state_dir: Optional[str] = None, verbose: bool = True):
        # Original signature preserved
        # Uses refactored state machine internally
```

This means you can do a **direct drop-in replacement** in most cases!

## Testing Strategy

### 1. Unit Tests
Create unit tests for each refactored component:

```python
# test_checkpoint_manager_refactored.py
from artemis_checkpoint_manager_refactored import (
    CheckpointBuilder, InMemoryCheckpointStorage, CheckpointRepository
)

def test_checkpoint_builder():
    checkpoint = (
        CheckpointBuilder("card-123")
        .with_total_stages(5)
        .add_stage_result(StageResult(...))
        .build()
    )
    assert checkpoint.card_id == "card-123"
    assert checkpoint.total_stages == 5

def test_storage_implementations():
    # Test both File and InMemory storage
    storage = InMemoryCheckpointStorage()
    checkpoint = CheckpointBuilder("card-123").build()

    storage.save(checkpoint)
    loaded = storage.load("card-123")
    assert loaded.checkpoint_id == checkpoint.checkpoint_id
```

### 2. Integration Tests
Test refactored components with real Artemis pipeline:

```bash
# Set feature flag
export ARTEMIS_USE_REFACTORED=true

# Run demo task
./artemis run card-20251023095355 --full

# Compare outputs
diff /tmp/artemis_legacy_run.log /tmp/artemis_refactored_run.log
```

### 3. Performance Tests
Measure performance impact:

```python
import time

# Test old version
start = time.time()
old_manager = OldCheckpointManager("card-123")
old_manager.create_checkpoint(total_stages=10)
old_time = time.time() - start

# Test refactored version
start = time.time()
new_manager = CheckpointManager("card-123")
new_manager.create_checkpoint(total_stages=10)
new_time = time.time() - start

print(f"Performance change: {((new_time - old_time) / old_time) * 100:.2f}%")
```

## Migration Checklist

### Pre-Migration
- [ ] Read this integration guide completely
- [ ] Backup current pipeline state
- [ ] Create branch: `git checkout -b refactor/design-patterns`
- [ ] Review refactored file documentation

### Phase 1: config_validator
- [ ] Set feature flag: `export ARTEMIS_USE_REFACTORED_CONFIG=true`
- [ ] Run preflight validation: `./artemis validate`
- [ ] Run full pipeline with refactored config validator
- [ ] Verify no errors in validation
- [ ] Compare validation output with original

### Phase 2: checkpoint_manager
- [ ] Set feature flag: `export ARTEMIS_USE_REFACTORED_CHECKPOINTS=true`
- [ ] Run pipeline with checkpoints
- [ ] Test resume functionality
- [ ] Verify checkpoint files are created correctly
- [ ] Test rollback scenarios

### Phase 3: state_machine
- [ ] Set feature flag: `export ARTEMIS_USE_REFACTORED_STATE_MACHINE=true`
- [ ] Run full pipeline
- [ ] Verify state transitions work correctly
- [ ] Test recovery workflows
- [ ] Test state persistence and resume

### Post-Migration
- [ ] Run full test suite
- [ ] Update documentation
- [ ] Remove legacy files
- [ ] Update imports in all files
- [ ] Remove feature flags
- [ ] Commit changes: `git commit -m "Refactor components with design patterns"`

## Rollback Plan

If issues occur during migration:

1. **Immediate Rollback:**
   ```bash
   export ARTEMIS_USE_REFACTORED=false
   # Restart pipeline
   ```

2. **File Rollback:**
   ```bash
   # Restore legacy files
   git checkout HEAD -- checkpoint_manager.py artemis_state_machine.py config_validator.py
   ```

3. **Full Rollback:**
   ```bash
   git revert <commit-hash>
   git push origin master
   ```

## Benefits Summary

### Maintainability
- Smaller, focused classes (SRP)
- Clear responsibilities
- Easier to understand and modify

### Testability
- Mock storage/persistence for tests
- Test state behavior in isolation
- Dependency injection enabled

### Extensibility
- Add new states without modifying existing code
- Swap storage implementations (File → S3)
- Add validation rules via chain
- New observers for monitoring

### Flexibility
- Multiple storage backends
- Different serialization formats
- Custom state behaviors per environment
- Pluggable validation strategies

### Code Quality
- Eliminates God Classes
- Removes code duplication
- Type safety with enums
- Immutable value objects prevent bugs
- Design patterns make intent clear

## Questions?

If you encounter issues or have questions about integration:

1. Check the refactored file docstrings (comprehensive documentation)
2. Review the CHECKPOINT_STATE_MACHINE_ANALYSIS.md for rationale
3. Look at the Facade implementations for backward compatibility examples
4. Test with InMemory implementations first (faster, no file I/O)

## Next Steps

1. Start with **Phase 1: Side-by-Side Testing** using feature flags
2. Focus on **config_validator** first (lowest risk)
3. Run integration tests and verify outputs match
4. Gradually migrate remaining components
5. Keep legacy files as backup until fully validated
