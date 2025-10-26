# SupervisorAgent Refactoring Plan

## Problem
SupervisorAgent is a God Class with 3,035 lines and multiple responsibilities, violating Single Responsibility Principle.

## Current Responsibilities (Identified from analysis)

### 1. Circuit Breaker Management (~300 lines)
- `check_circuit_breaker()`
- `open_circuit_breaker()`
- `stage_health` dictionary
- `recovery_strategies` dictionary
- Circuit state tracking

### 2. Cost Tracking (~200 lines)
- `track_llm_call()`
- `cost_tracker` instance
- Budget validation
- Cost reporting

### 3. Health Monitoring (~500 lines)
- `monitor_agent_health()`
- `detect_hanging_processes()`
- `_detect_agent_crash()`
- `_check_agent_progress()`
- Agent registry management
- Heartbeat monitoring
- Watchdog thread

### 4. Recovery Engine (~800 lines)
- `recover_crashed_agent()`
- `recover_hung_agent()`
- `handle_unexpected_state()`
- `_try_fix_json_parsing_failure()`
- `_try_fallback_retry()`
- `_try_default_values()`
- `_try_skip_stage()`
- `llm_auto_fix_error()`
- `_restart_failed_stage()`

### 5. Learning Engine (~400 lines)
- `enable_learning()`
- `query_learned_solutions()`
- `_query_similar_issues()`
- `_store_issue_outcome()`
- `get_learning_insights()`
- Integration with SupervisorLearningEngine

### 6. Sandbox Execution (~200 lines)
- `execute_code_safely()`
- `execute_with_supervision()`
- Sandbox configuration
- Security scanning

### 7. State Machine Integration (~150 lines)
- State machine lifecycle
- State snapshot/rollback
- Issue handling integration

### 8. Observer Pattern (~200 lines)
- Health observer management
- Agent registration
- Heartbeat tracking
- Event notification

## Refactoring Strategy

### Phase 1: Extract Independent Components (Low Risk)
These components have minimal dependencies on SupervisorAgent internals.

#### 1.1 Extract CircuitBreakerManager
**File**: `supervisor_circuit_breaker.py`
**Responsibilities**:
- Manage circuit breaker state for stages
- Track failure counts
- Implement circuit open/close logic
- Store recovery strategies

**Interface**:
```python
class CircuitBreakerManager:
    def check_circuit(self, stage_name: str) -> bool
    def record_failure(self, stage_name: str) -> None
    def record_success(self, stage_name: str) -> None
    def open_circuit(self, stage_name: str) -> None
    def reset_circuit(self, stage_name: str) -> None
    def get_stage_health(self, stage_name: str) -> StageHealth
    def register_strategy(self, stage_name: str, strategy: RecoveryStrategy) -> None
```

**Dependencies**:
- `RecoveryStrategy` (dataclass)
- `StageHealth` (dataclass)
- `LoggerInterface`

**Lines**: ~300
**Extracted from**:
- Lines 500-532 (check_circuit_breaker)
- Lines 532-560 (open_circuit_breaker)
- Lines 462-500 (register_stage)
- stage_health, recovery_strategies dicts

---

#### 1.2 Extract HealthMonitor
**File**: `supervisor_health_monitor.py`
**Responsibilities**:
- Monitor agent processes
- Detect crashes, hangs, stalls
- Agent registration and heartbeat tracking
- Process health tracking

**Interface**:
```python
class HealthMonitor:
    def register_agent(self, agent_name: str, heartbeat_interval: float, metadata: Dict) -> None
    def unregister_agent(self, agent_name: str) -> None
    def agent_heartbeat(self, agent_name: str, progress_data: Optional[Dict]) -> None
    def detect_hanging_processes(self) -> List[ProcessHealth]
    def detect_agent_crash(self, agent_name: str) -> Optional[Dict]
    def check_agent_progress(self, agent_name: str) -> Optional[Dict]
    def get_health_status(self) -> HealthStatus
    def start_watchdog(self, interval_seconds: float) -> None
    def stop_watchdog(self) -> None
```

**Dependencies**:
- `ProcessHealth` (dataclass)
- `HealthStatus` (enum)
- `LoggerInterface`
- `AgentHealthObserver` (for event notifications)

**Lines**: ~500
**Extracted from**:
- Lines 2054-2132 (monitor_agent_health)
- Lines 976-1008 (detect_hanging_processes)
- Lines 2132-2167 (_detect_agent_crash)
- Lines 2167-2203 (_check_agent_progress)
- Lines 2444-2482 (register_agent)
- Lines 2502-2528 (agent_heartbeat)
- Lines 2672-2774 (start_watchdog)
- registered_agents dict
- process_registry dict

---

#### 1.3 Extract RecoveryEngine
**File**: `supervisor_recovery_engine.py`
**Responsibilities**:
- Execute recovery strategies
- Handle unexpected states
- Retry failed stages
- Fallback to safe defaults
- LLM-powered auto-fix

**Interface**:
```python
class RecoveryEngine:
    def recover_crashed_agent(self, crash_info: Dict, context: Dict) -> Dict
    def recover_hung_agent(self, agent_name: str, timeout_info: Dict) -> Dict
    def handle_unexpected_state(self, current_state: str, expected: List[str], context: Dict) -> Dict
    def try_fix_json_parsing(self, error: Exception, context: Dict) -> Optional[Dict]
    def try_fallback_retry(self, error: Exception, context: Dict) -> Optional[Dict]
    def try_default_values(self, error: Exception, context: Dict) -> Optional[Dict]
    def llm_auto_fix(self, error: Exception, traceback: str, context: Dict) -> Optional[Dict]
    def restart_failed_stage(self, context: Dict, fix_result: Dict) -> Dict
```

**Dependencies**:
- `ArtemisStateMachine` (for rollback)
- `LLMClient` (for auto-fix)
- `RAGAgent` (for similar issues)
- `SupervisorLearningEngine` (for learned solutions)
- `LoggerInterface`

**Lines**: ~800
**Extracted from**:
- Lines 2203-2286 (recover_crashed_agent)
- Lines 2286-2341 (recover_hung_agent)
- Lines 639-737 (handle_unexpected_state)
- Lines 1424-1530 (_try_fix_json_parsing_failure)
- Lines 1530-1563 (_try_fallback_retry)
- Lines 1563-1640 (_try_default_values)
- Lines 1676-1784 (llm_auto_fix_error)
- Lines 1982-2054 (_restart_failed_stage)

---

### Phase 2: Composition Pattern (Refactor SupervisorAgent)

**New SupervisorAgent Structure**:
```python
class SupervisorAgent:
    """
    Simplified supervisor using composition

    Delegates to specialized components:
    - circuit_breaker: Circuit breaker management
    - health_monitor: Agent health monitoring
    - recovery_engine: Failure recovery
    - cost_tracker: LLM cost tracking (already extracted)
    - sandbox: Code execution (already extracted)
    - learning_engine: Solution learning (already extracted)
    - state_machine: State management (already extracted)
    """

    def __init__(self, logger, messenger, ...):
        # Core dependencies
        self.logger = logger
        self.messenger = messenger

        # Specialized components (Composition)
        self.circuit_breaker = CircuitBreakerManager(logger)
        self.health_monitor = HealthMonitor(logger)
        self.recovery_engine = RecoveryEngine(logger, messenger)

        # Already extracted components
        self.cost_tracker = CostTracker(...) if enable_cost_tracking else None
        self.sandbox = SandboxExecutor(...) if enable_sandboxing else None
        self.learning_engine = SupervisorLearningEngine(...) if rag else None
        self.state_machine = ArtemisStateMachine(...) if rag else None

    # Facade methods (delegate to components)
    def check_circuit_breaker(self, stage_name: str) -> bool:
        return self.circuit_breaker.check_circuit(stage_name)

    def track_llm_call(self, **kwargs) -> Dict:
        if self.cost_tracker:
            return self.cost_tracker.track_call(**kwargs)
        return {}

    def monitor_agent_health(self, **kwargs):
        return self.health_monitor.monitor_agent_health(**kwargs)

    def recover_crashed_agent(self, crash_info, context):
        return self.recovery_engine.recover_crashed_agent(crash_info, context)
```

**Benefits**:
1. ✅ Single Responsibility: Each component has ONE job
2. ✅ Testability: Components can be unit tested independently
3. ✅ Maintainability: Easier to understand and modify
4. ✅ Reusability: Components can be used in other contexts
5. ✅ Reduced coupling: Dependencies are explicit
6. ✅ Smaller files: Each file < 500 lines

**Result**:
- SupervisorAgent: ~500 lines (facade + coordination)
- CircuitBreakerManager: ~300 lines
- HealthMonitor: ~500 lines
- RecoveryEngine: ~800 lines
- **Total**: Same functionality, better organized

---

## Implementation Steps

### Step 1: Extract CircuitBreakerManager ✅
- [x] Create supervisor_circuit_breaker.py
- [x] Move circuit breaker logic
- [x] Add unit tests
- [x] Update SupervisorAgent to use CircuitBreakerManager

### Step 2: Extract HealthMonitor ✅
- [x] Create supervisor_health_monitor.py
- [x] Move health monitoring logic
- [x] Add unit tests
- [x] Update SupervisorAgent to use HealthMonitor

### Step 3: Extract RecoveryEngine ✅
- [x] Create supervisor_recovery_engine.py
- [x] Move recovery logic
- [x] Add unit tests
- [x] Update SupervisorAgent to use RecoveryEngine

### Step 4: Refactor SupervisorAgent ✅
- [x] Replace internal logic with component delegation
- [x] Simplify __init__ to create components
- [x] Maintain backward compatibility
- [x] Update all callers if needed

### Step 5: Testing ✅
- [x] Unit tests for each component
- [x] Integration tests for SupervisorAgent
- [x] Regression tests for existing functionality
- [x] Verify no behavior changes

---

## Backward Compatibility

All public methods remain the same. Internal refactoring only.

**Example**:
```python
# Before (all in SupervisorAgent)
supervisor.check_circuit_breaker("stage1")

# After (delegates to component, but same API)
supervisor.check_circuit_breaker("stage1")  # Internally calls self.circuit_breaker.check_circuit()
```

No changes required in calling code.

---

## Success Metrics

1. ✅ SupervisorAgent reduced from 3,035 lines to < 600 lines
2. ✅ All components < 500 lines
3. ✅ All existing tests pass
4. ✅ No regression in functionality
5. ✅ Improved code coverage (easier to test)
6. ✅ Reduced cyclomatic complexity

---

## Files Created

1. `supervisor_circuit_breaker.py` - Circuit breaker management
2. `supervisor_health_monitor.py` - Health monitoring
3. `supervisor_recovery_engine.py` - Recovery strategies
4. `supervisor_agent_refactored.py` - Refactored SupervisorAgent
5. `test_supervisor_components.py` - Unit tests

---

## Risk Mitigation

1. **Backward compatibility**: Keep all public methods unchanged
2. **Incremental refactoring**: Extract one component at a time
3. **Testing**: Unit test each component before integration
4. **Feature flag**: `USE_REFACTORED_SUPERVISOR` env var for gradual rollout
5. **Rollback plan**: Keep original supervisor_agent.py as supervisor_agent_legacy.py

---

## Timeline

- Phase 1 (Extract Components): 8 hours
  - CircuitBreakerManager: 2 hours
  - HealthMonitor: 3 hours
  - RecoveryEngine: 3 hours

- Phase 2 (Refactor SupervisorAgent): 4 hours
  - Composition pattern: 2 hours
  - Testing: 2 hours

**Total**: 12 hours (1.5 days)
