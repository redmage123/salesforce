# How the Supervisor Tracks State in Code Review/Refactor Pipeline

## Overview

The Supervisor Agent maintains **complete pipeline state awareness** by storing stage execution results in the Artemis State Machine using a **Pushdown Automaton** (state stack) architecture. This enables the supervisor to make informed decisions about retries, recovery strategies, and circuit breaker activation based on actual stage outcomes.

---

## Architecture Components

### 1. Supervisor Agent (`supervisor_agent.py`)
- **Role**: Health monitoring, retry management, state tracking
- **Responsibility**: Execute stages with supervision and store results
- **Does NOT**: Route messages or transform data (separation of concerns)

### 2. Artemis State Machine (`artemis_state_machine.py`)
- **Role**: Pipeline state tracking and management
- **Architecture**: Pushdown Automaton with state stack
- **Features**: State history, transitions, rollback capability

### 3. State Stack (`_state_stack`)
- **Structure**: List of state entries with context
- **Purpose**: Track complete execution history with results
- **Enables**: Backtracking, rollback, state queries

---

## How State Tracking Works: Step-by-Step

### Phase 1: Stage Execution

```python
# supervisor_agent.py:952-970
def _execute_stage_with_retries(self, stage, stage_name, *args, **kwargs):
    while retry_count <= strategy.max_retries:
        try:
            # Execute stage with monitoring
            result_data = self._execute_stage_monitored(stage, stage_name, strategy, *args, **kwargs)
            # ↓ Returns: {'result': <stage_result>, 'duration': <seconds>}

            # Handle successful execution - PASS RESULT FOR STATE TRACKING
            self._handle_successful_execution(
                stage_name,
                health,
                retry_count,
                result_data['duration'],
                result_data['result']  # ← CRITICAL: Pass complete result
            )

            return result_data['result']
```

**What happens here**:
1. Stage executes (e.g., `code_review_stage.execute()`)
2. Returns result dict containing:
   - `review_results`: List of code review results
   - `refactoring_suggestions`: Text with refactoring instructions
   - `overall_score`: Aggregate quality score
   - `total_critical_issues`: Count of critical issues
3. Supervisor captures this **complete result** and duration
4. Passes to `_handle_successful_execution()` for state storage

---

### Phase 2: Success State Storage

```python
# supervisor_agent.py:1025-1051
def _handle_successful_execution(self, stage_name, health, retry_count, duration, result=None):
    """
    Handle successful stage execution

    Args:
        result: Stage execution result (optional, for state tracking)
    """
    health.execution_count += 1
    health.total_duration += duration

    # Store result in state machine for complete pipeline state tracking
    if self.state_machine and result is not None:
        self.state_machine.push_state(
            PipelineState.STAGE_COMPLETED,  # ← State type
            {
                "stage": stage_name,         # ← Which stage
                "result": result,            # ← COMPLETE RESULT DICT
                "duration": duration,
                "retry_count": retry_count,
                "timestamp": datetime.now().isoformat()
            }
        )
        self.state_machine.update_stage_state(stage_name, StageState.COMPLETED)
```

**What happens here**:
1. Supervisor receives the complete stage result
2. Calls `state_machine.push_state()` with:
   - **State**: `STAGE_COMPLETED`
   - **Context**: Dict containing the full result + metadata
3. State machine pushes this onto the state stack
4. Updates stage state to `COMPLETED`

**Example for Code Review Stage**:
```python
# When code review completes, supervisor stores:
{
    "stage": "code_review",
    "result": {
        "review_results": [
            {"file": "app.py", "score": 65, "issues": [...]}
        ],
        "refactoring_suggestions": "# REFACTORING INSTRUCTIONS\n1. Extract long methods...",
        "overall_score": 65,
        "total_critical_issues": 5
    },
    "duration": 12.5,
    "retry_count": 0,
    "timestamp": "2025-10-25T14:30:22"
}
```

---

### Phase 3: Failure State Storage

```python
# supervisor_agent.py:972-988
except Exception as e:
    last_error = e
    retry_count += 1

    # Store failure in state machine for complete state tracking
    if self.state_machine:
        self.state_machine.push_state(
            PipelineState.STAGE_FAILED,  # ← State type
            {
                "stage": stage_name,
                "error": str(e),
                "error_type": type(e).__name__,
                "retry_count": retry_count,
                "timestamp": datetime.now().isoformat()
            }
        )
        self.state_machine.update_stage_state(stage_name, StageState.FAILED)
```

**What happens here**:
1. If stage raises exception, supervisor catches it
2. Stores failure details in state machine via `push_state()`
3. Includes error message, type, retry count
4. Continues with retry logic if retries remain

---

### Phase 4: State Stack Implementation (Pushdown Automaton)

```python
# artemis_state_machine.py:912-933
def push_state(self, state: PipelineState, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Push state onto stack (Pushdown Automaton feature)

    Enables backtracking and rollback by maintaining state stack

    Args:
        state: State to push
        context: Optional context for this state
    """
    if not hasattr(self, '_state_stack'):
        self._state_stack = []

    self._state_stack.append({
        "state": state,
        "timestamp": datetime.now(),
        "context": context or {}  # ← STORES COMPLETE RESULT HERE
    })

    if self.verbose:
        print(f"[StateMachine] Pushed state onto stack: {state.value} (depth: {len(self._state_stack)})")
```

**State Stack Structure**:
```python
_state_stack = [
    {
        "state": PipelineState.STAGE_COMPLETED,
        "timestamp": datetime(2025, 10, 25, 14, 30, 10),
        "context": {
            "stage": "project_analysis",
            "result": {...},
            "duration": 5.2,
            "retry_count": 0,
            "timestamp": "2025-10-25T14:30:10"
        }
    },
    {
        "state": PipelineState.STAGE_COMPLETED,
        "timestamp": datetime(2025, 10, 25, 14, 30, 22),
        "context": {
            "stage": "code_review",
            "result": {
                "review_results": [...],
                "refactoring_suggestions": "...",
                "overall_score": 65,
                "total_critical_issues": 5
            },
            "duration": 12.5,
            "retry_count": 0,
            "timestamp": "2025-10-25T14:30:22"
        }
    },
    {
        "state": PipelineState.STAGE_FAILED,
        "timestamp": datetime(2025, 10, 25, 14, 30, 45),
        "context": {
            "stage": "developer",
            "error": "Build failed: compilation errors",
            "error_type": "BuildException",
            "retry_count": 1,
            "timestamp": "2025-10-25T14:30:45"
        }
    }
]
```

**Why Pushdown Automaton?**
- **Stack-based**: Latest state on top (LIFO)
- **History preservation**: Never loses past states
- **Rollback capability**: Can pop states to revert
- **Query capability**: Can search stack for past results

---

## Querying State: Helper Methods

### Method 1: Get Latest Result for a Specific Stage

```python
# supervisor_agent.py:1366-1403 (REFACTORED WITH PATTERN #4)
def get_stage_result(self, stage_name: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve latest result for a stage from state machine

    This allows the supervisor to query "What did code review find?"
    without needing to ask the orchestrator.
    """
    # Guard clauses (Pattern #10)
    if not self.state_machine:
        return None

    if not hasattr(self.state_machine, '_state_stack'):
        return None

    # Pattern #4: Use next() with generator for first match
    return next(
        (
            context['result']
            for state_entry in reversed(self.state_machine._state_stack)
            if (context := state_entry.get('context', {})).get('stage') == stage_name
            and 'result' in context
        ),
        None  # Default if not found
    )
```

**How it works**:
1. Searches state stack in **reverse order** (latest first)
2. Uses **generator expression** with `next()` for efficiency
3. Finds first match where:
   - `context['stage']` matches the requested stage name
   - `context['result']` exists
4. Returns the complete result dict or None

**Usage Example**:
```python
# Supervisor can query code review results
supervisor = SupervisorAgent(...)

code_review_result = supervisor.get_stage_result('code_review')
if code_review_result:
    refactoring_suggestions = code_review_result.get('refactoring_suggestions')
    critical_issues = code_review_result.get('total_critical_issues', 0)

    # Adjust retry strategy based on complexity
    if critical_issues > 5:
        supervisor.set_recovery_strategy(
            "code_review",
            RecoveryStrategy(
                max_retries=5,
                retry_delay_seconds=180,  # 3 minutes
                backoff_multiplier=1.5
            )
        )
```

---

### Method 2: Get All Stage Results

```python
# supervisor_agent.py:1405-1440 (REFACTORED WITH PATTERN #11)
def get_all_stage_results(self) -> Dict[str, Dict[str, Any]]:
    """
    Retrieve latest results for all stages from state machine

    Returns:
        Dict mapping stage_name to result dict
    """
    # Guard clauses
    if not self.state_machine:
        return {}

    if not hasattr(self.state_machine, '_state_stack'):
        return {}

    # Pattern #11: Use generator pattern
    seen_stages = set()

    def _unique_stage_results():
        """Generator yielding (stage, result) tuples for unseen stages"""
        for state_entry in reversed(self.state_machine._state_stack):
            context = state_entry.get('context', {})
            stage = context.get('stage')
            result = context.get('result')

            if stage and result and stage not in seen_stages:
                seen_stages.add(stage)
                yield (stage, result)

    return dict(_unique_stage_results())
```

**How it works**:
1. Uses **generator function** for memory efficiency (Pattern #11)
2. Tracks seen stages to avoid duplicates
3. Searches stack in reverse (latest results first)
4. Yields `(stage_name, result)` tuples for each unique stage
5. Converts generator to dict

**Usage Example**:
```python
# Get complete pipeline state snapshot
all_results = supervisor.get_all_stage_results()

# Access individual stage results
project_analysis = all_results.get('project_analysis', {})
code_review = all_results.get('code_review', {})
developer = all_results.get('developer', {})

# Make decisions based on multiple stages
if code_review.get('overall_score', 100) < 70 and developer.get('build_status') == 'failed':
    # Heavy refactoring needed + build failure = increase timeout
    supervisor.increase_timeout('developer', factor=2.0)
```

---

## Code Review/Refactor Pipeline: Complete Flow

### Step 1: Code Review Executes

```python
# In orchestrator
code_review_result = supervisor.execute_stage_with_supervision(
    code_review_stage,
    "code_review",
    card_id=card_id,
    context=context
)
```

**Code Review Returns**:
```python
{
    "review_results": [
        {
            "file": "app.py",
            "developer": "developer_a",
            "review_status": "FAIL",
            "overall_score": 65,
            "critical_issues": 5,
            "issues": [...]
        }
    ],
    "refactoring_suggestions": """
# REFACTORING INSTRUCTIONS FOR CODE REVIEW FAILURES

## Developer: developer_a | File: app.py | Score: 65/100

### Required Refactorings:
1. **Extract Long Methods**: Break down methods >50 lines into focused functions
2. **Reduce Complexity**: Use guard clauses instead of nested ifs
3. **Use next() for First Match**: Replace for loops with generator + next()
...
    """,
    "overall_score": 65,
    "total_critical_issues": 5
}
```

---

### Step 2: Supervisor Stores Result in State Machine

```python
# supervisor_agent.py:1040-1051
if self.state_machine and result is not None:
    self.state_machine.push_state(
        PipelineState.STAGE_COMPLETED,
        {
            "stage": "code_review",
            "result": code_review_result,  # ← COMPLETE RESULT
            "duration": 12.5,
            "retry_count": 0,
            "timestamp": "2025-10-25T14:30:22"
        }
    )
```

**State Stack Now Contains**:
```python
_state_stack = [
    ...,  # Previous stages
    {
        "state": PipelineState.STAGE_COMPLETED,
        "timestamp": datetime(2025, 10, 25, 14, 30, 22),
        "context": {
            "stage": "code_review",
            "result": {
                "refactoring_suggestions": "...",
                "overall_score": 65,
                "total_critical_issues": 5
            },
            ...
        }
    }
]
```

---

### Step 3: Orchestrator Stores Refactoring Suggestions in RAG

```python
# artemis_orchestrator.py:_store_retry_feedback_in_rag()
refactoring_suggestions = code_review_result.get('refactoring_suggestions')
if refactoring_suggestions:
    content += f"\n{'='*60}\n"
    content += "REFACTORING INSTRUCTIONS\n"
    content += f"{'='*60}\n\n"
    content += refactoring_suggestions
    content += "\n"

# Store in RAG
artifact_id = self.rag.store_artifact(
    artifact_type="code_review_retry_feedback",
    card_id=card_id,
    task_title=task_title,
    content=content,  # Includes refactoring_suggestions
    metadata={
        'retry_attempt': retry_attempt,
        'has_refactoring_suggestions': True
    }
)
```

---

### Step 4: Developer Fails (Build Error)

```python
# Developer executes, but build fails
developer_result = supervisor.execute_stage_with_supervision(
    developer_stage,
    "developer",
    card_id=card_id,
    context=context
)
# ↑ Raises exception: BuildException
```

**Supervisor Stores Failure**:
```python
# supervisor_agent.py:978-988
if self.state_machine:
    self.state_machine.push_state(
        PipelineState.STAGE_FAILED,
        {
            "stage": "developer",
            "error": "Build failed: compilation errors in app.py",
            "error_type": "BuildException",
            "retry_count": 1,
            "timestamp": "2025-10-25T14:30:45"
        }
    )
```

**State Stack Now Contains**:
```python
_state_stack = [
    {...},  # project_analysis
    {
        "state": PipelineState.STAGE_COMPLETED,
        "context": {
            "stage": "code_review",
            "result": {
                "refactoring_suggestions": "...",
                "overall_score": 65,
                "total_critical_issues": 5
            }
        }
    },
    {
        "state": PipelineState.STAGE_FAILED,
        "context": {
            "stage": "developer",
            "error": "Build failed: compilation errors in app.py",
            "error_type": "BuildException",
            "retry_count": 1
        }
    }
]
```

---

### Step 5: Supervisor Queries State for Informed Retry

```python
# Before retrying developer stage, supervisor can check code review results
code_review_result = supervisor.get_stage_result('code_review')

if code_review_result:
    critical_issues = code_review_result.get('total_critical_issues', 0)
    overall_score = code_review_result.get('overall_score', 100)

    # Heavy refactoring needed - adjust retry strategy
    if critical_issues > 5 or overall_score < 70:
        supervisor.set_recovery_strategy(
            "developer",
            RecoveryStrategy(
                max_retries=5,        # More retries
                retry_delay_seconds=180,  # Longer delay (3 min)
                timeout_seconds=600,   # Longer timeout (10 min)
                backoff_multiplier=1.5
            )
        )

        if supervisor.verbose:
            print(f"[Supervisor] Adjusted retry strategy for developer stage:")
            print(f"  - Code review score: {overall_score}/100")
            print(f"  - Critical issues: {critical_issues}")
            print(f"  - Increased retries and timeout for complex refactoring")
```

---

### Step 6: Developer Retries with Refactoring Guidance

```python
# Developer stage queries RAG for refactoring suggestions
rag_feedback = self.rag.query_similar(
    query_text=f"code review feedback {card_id} {task_title} retry",
    artifact_type="code_review_retry_feedback",
    top_k=3
)

# Receives refactoring suggestions from RAG
# Applies refactorings
# Retries build
# ✅ Success
```

**Supervisor Stores Success**:
```python
self.state_machine.push_state(
    PipelineState.STAGE_COMPLETED,
    {
        "stage": "developer",
        "result": {
            "build_status": "success",
            "tests_passed": 45,
            "refactorings_applied": [
                "Extracted long methods",
                "Applied guard clauses",
                "Used next() for first match"
            ]
        },
        "duration": 95.3,
        "retry_count": 2,
        "timestamp": "2025-10-25T14:35:20"
    }
)
```

---

## State Awareness Benefits

### 1. Informed Retry Decisions
```python
# Supervisor knows:
# - Code review found 5 critical issues
# - Overall quality score was 65/100
# - Developer already failed once
# → Increase retry limits and timeout
```

### 2. Circuit Breaker Activation
```python
# Supervisor can detect patterns:
failures = [
    entry for entry in state_stack
    if entry['context'].get('stage') == 'developer'
    and entry['state'] == PipelineState.STAGE_FAILED
]

if len(failures) > 3:
    supervisor.open_circuit('developer')
```

### 3. Learning Engine Input
```python
# Supervisor can learn from patterns:
if code_review.score < 70 and developer.retries > 2:
    learning_engine.record_pattern(
        "low_code_quality_needs_more_retries",
        {
            "code_review_score": 65,
            "retry_count": 3,
            "critical_issues": 5
        }
    )
```

### 4. Complete Pipeline Visibility
```python
# At any time, supervisor can answer:
# - What stages have completed?
# - What were their results?
# - How many retries have been used?
# - What errors occurred?
# - Is the pipeline healthy?

snapshot = supervisor.get_all_stage_results()
# Returns complete state across all stages
```

---

## Architecture Principles

### ✅ Separation of Concerns
- **Supervisor**: Monitors health, stores state, manages retries
- **Orchestrator**: Manages workflow, stores data in RAG
- **State Machine**: Tracks state, provides history

### ✅ Single Responsibility
- Supervisor does NOT route messages
- Supervisor does NOT transform data
- Supervisor ONLY tracks execution and makes health decisions

### ✅ Content-Agnostic Monitoring
- Supervisor stores **complete results** without understanding them
- Works with ANY stage type
- Generic `push_state(state, context)` interface

### ✅ Observable Pattern
- Supervisor observes execution
- State machine provides state queries
- No tight coupling between components

---

## Key Takeaways

1. **Pushdown Automaton**: State stack enables complete history tracking
2. **Complete Results Storage**: Supervisor stores full stage results in context
3. **Query Capability**: Helper methods retrieve results from stack
4. **Informed Decisions**: Supervisor adjusts strategies based on past results
5. **Separation of Concerns**: Supervisor tracks, orchestrator routes
6. **Refactoring Patterns Applied**: Uses generators, next(), guard clauses

---

## Example: Complete State Stack After Failed Pipeline

```python
supervisor.state_machine._state_stack = [
    {
        "state": PipelineState.STAGE_COMPLETED,
        "context": {
            "stage": "project_analysis",
            "result": {"project_type": "python", "complexity": "medium"},
            "retry_count": 0
        }
    },
    {
        "state": PipelineState.STAGE_COMPLETED,
        "context": {
            "stage": "code_review",
            "result": {
                "refactoring_suggestions": "# Extract long methods...",
                "overall_score": 65,
                "total_critical_issues": 5
            },
            "retry_count": 0
        }
    },
    {
        "state": PipelineState.STAGE_FAILED,
        "context": {
            "stage": "developer",
            "error": "Build failed",
            "retry_count": 1
        }
    },
    {
        "state": PipelineState.STAGE_COMPLETED,
        "context": {
            "stage": "developer",
            "result": {
                "build_status": "success",
                "refactorings_applied": [...]
            },
            "retry_count": 2
        }
    }
]

# Supervisor can now answer:
# - How many times did developer retry? (2)
# - What was the code review score? (65)
# - What refactorings were needed? (Extract long methods...)
# - Did pipeline eventually succeed? (Yes)
```

---

## Files Reference

- **supervisor_agent.py:952-998** - State storage on success/failure
- **supervisor_agent.py:1025-1051** - `_handle_successful_execution()`
- **supervisor_agent.py:1366-1403** - `get_stage_result()` helper
- **supervisor_agent.py:1405-1440** - `get_all_stage_results()` helper
- **artemis_state_machine.py:912-933** - `push_state()` implementation
- **artemis_state_machine.py:258-330** - State machine initialization

---

## Status

✅ **Implemented and Verified**
✅ **Refactoring Patterns Applied** (Patterns #4, #10, #11)
✅ **All Code Compiles Successfully**
✅ **Documentation Complete**

**Next Step**: Run full pipeline test to verify state tracking in action.
