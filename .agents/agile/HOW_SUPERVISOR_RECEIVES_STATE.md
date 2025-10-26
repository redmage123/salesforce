# How Does the Supervisor Receive State Information?

## The Key Insight: Supervisor WRAPS Stage Execution

The supervisor doesn't receive state information from agents sending it. Instead, the supervisor **wraps** the stage execution and captures the return value directly.

---

## The Call Stack: From Orchestrator → Supervisor → Stage

### Step 1: Orchestrator Calls Supervisor

```python
# In artemis_orchestrator.py
def run_pipeline(self, card_id: str):
    # ...

    # Orchestrator doesn't call stage directly
    # Instead, it calls supervisor.execute_stage_with_supervision()

    code_review_result = self.supervisor.execute_stage_with_supervision(
        code_review_stage,    # ← The stage object
        "code_review",        # ← Stage name
        card_id=card_id,      # ← Arguments to pass to stage
        context=context
    )

    # Supervisor returns the result to orchestrator
    # Orchestrator doesn't know supervisor stored it in state machine
```

**Key Point**: The orchestrator calls the **supervisor**, not the stage directly.

---

### Step 2: Supervisor Executes Stage and Captures Result

```python
# In supervisor_agent.py
def execute_stage_with_supervision(
    self,
    stage: Any,           # ← Receives the stage object
    stage_name: str,
    *args,
    **kwargs
):
    """
    Execute a stage with full supervision

    The supervisor WRAPS the stage execution, so it can:
    1. Monitor health (heartbeats, timeouts)
    2. Capture the result
    3. Store result in state machine
    4. Handle retries
    5. Return result to caller
    """

    # Call internal method with retry logic
    return self._execute_stage_with_retries(
        stage,
        stage_name,
        *args,
        **kwargs
    )
```

---

### Step 3: Supervisor Calls Stage.execute() and Captures Return

```python
# In supervisor_agent.py:952-970
def _execute_stage_with_retries(self, stage, stage_name, *args, **kwargs):
    """Execute stage with retry logic"""

    while retry_count <= strategy.max_retries:
        try:
            # ═══════════════════════════════════════════════════════
            # THIS IS WHERE THE MAGIC HAPPENS
            # ═══════════════════════════════════════════════════════

            # Supervisor calls the STAGE'S execute method directly
            result_data = self._execute_stage_monitored(
                stage,        # ← Stage object
                stage_name,
                strategy,
                *args,
                **kwargs
            )
            # ↓
            # Returns: {'result': <stage_result>, 'duration': <seconds>}

            # Supervisor now HAS the result in result_data['result']
            # No need for stage to "send" anything - supervisor already has it!

            # Store it in state machine
            self._handle_successful_execution(
                stage_name,
                health,
                retry_count,
                result_data['duration'],
                result_data['result']  # ← The captured result
            )

            # Return to orchestrator
            return result_data['result']

        except Exception as e:
            # Supervisor catches exceptions too
            # Stores failure in state machine
            ...
```

---

### Step 4: The _execute_stage_monitored Method

```python
# In supervisor_agent.py:1007-1023
def _execute_stage_monitored(self, stage, stage_name, strategy, *args, **kwargs):
    """Execute stage with timeout monitoring"""

    start_time = datetime.now()

    # Start monitoring in background thread
    monitor_thread = threading.Thread(
        target=self._monitor_execution,
        args=(stage_name, strategy.timeout_seconds),
        daemon=True
    )
    monitor_thread.start()

    # ═══════════════════════════════════════════════════════
    # DIRECT CALL TO STAGE'S execute() METHOD
    # ═══════════════════════════════════════════════════════
    result = stage.execute(*args, **kwargs)
    # ↑
    # This is a normal Python function call
    # The return value flows back to supervisor

    duration = (datetime.now() - start_time).total_seconds()

    # Return both result and duration
    return {'result': result, 'duration': duration}
```

**Key Point**: The supervisor calls `stage.execute()` directly and captures the return value. The stage doesn't need to "send" anything - it just returns normally.

---

## Analogy: Decorator Pattern

Think of the supervisor like a Python decorator:

```python
# WITHOUT SUPERVISOR
def execute_code_review(card_id, context):
    # Do code review
    return {
        "review_results": [...],
        "refactoring_suggestions": "...",
        "overall_score": 65
    }

result = execute_code_review(card_id, context)


# WITH SUPERVISOR (decorator-like wrapper)
def with_supervision(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()

        # Call the original function
        result = func(*args, **kwargs)  # ← Capture return value

        duration = time.time() - start_time

        # Store in state machine
        state_machine.push_state(
            state=COMPLETED,
            context={"result": result, "duration": duration}  # ← Store it
        )

        # Return to caller
        return result

    return wrapper

@with_supervision
def execute_code_review(card_id, context):
    # Do code review
    return {
        "review_results": [...],
        "refactoring_suggestions": "...",
        "overall_score": 65
    }

# Caller still gets result normally
result = execute_code_review(card_id, context)
# But supervisor also stored it in state machine
```

---

## Complete Call Flow with Return Values

```
┌────────────────────┐
│  Orchestrator      │
│                    │
│  result =          │
│  supervisor.       │
│  execute_stage_    │
│  with_supervision( │
│    code_review,    │
│    ...             │
│  )                 │
└────────┬───────────┘
         │
         │ Call supervisor method
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Supervisor                                             │
│  execute_stage_with_supervision()                       │
│                                                         │
│  def execute_stage_with_supervision(                    │
│      self, stage, stage_name, *args, **kwargs           │
│  ):                                                     │
│      return self._execute_stage_with_retries(          │
│          stage, stage_name, *args, **kwargs            │
│      )                                                  │
└────────┬────────────────────────────────────────────────┘
         │
         │ Call internal retry method
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Supervisor                                             │
│  _execute_stage_with_retries()                          │
│                                                         │
│  while retry_count <= max_retries:                      │
│      try:                                               │
│          result_data =                                  │
│          self._execute_stage_monitored(                │
│              stage, stage_name, ...                     │
│          )                                              │
└────────┬────────────────────────────────────────────────┘
         │
         │ Call monitored execution
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Supervisor                                             │
│  _execute_stage_monitored()                             │
│                                                         │
│  result = stage.execute(*args, **kwargs) ← DIRECT CALL │
│  return {'result': result, 'duration': duration}        │
└────────┬────────────────────────────────────────────────┘
         │
         │ Call stage's execute() method
         │
         ▼
┌────────────────────┐
│  CodeReviewStage   │
│                    │
│  def execute(      │
│      card_id,      │
│      context       │
│  ):                │
│      # Review code │
│      return {      │
│          "review_  │
│          results": │
│          [...],    │
│          "overall_ │
│          score": 65│
│      }             │
└────────┬───────────┘
         │
         │ RETURN VALUE
         │
         ▼
    {
        "review_results": [...],
        "refactoring_suggestions": "...",
        "overall_score": 65,
        "total_critical_issues": 5
    }
         │
         │ Return value flows back up the call stack
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Supervisor                                             │
│  _execute_stage_monitored()                             │
│                                                         │
│  result = {                                             │
│      "review_results": [...],                           │
│      "refactoring_suggestions": "...",                  │
│      "overall_score": 65                                │
│  }                                                      │
│                                                         │
│  return {                                               │
│      'result': result,  ← The stage's return value     │
│      'duration': 12.5                                   │
│  }                                                      │
└────────┬────────────────────────────────────────────────┘
         │
         │ Return to retry method
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Supervisor                                             │
│  _execute_stage_with_retries()                          │
│                                                         │
│  result_data = {                                        │
│      'result': {                                        │
│          "review_results": [...],                       │
│          "refactoring_suggestions": "...",              │
│          "overall_score": 65                            │
│      },                                                 │
│      'duration': 12.5                                   │
│  }                                                      │
│                                                         │
│  # NOW SUPERVISOR STORES IT IN STATE MACHINE            │
│  self._handle_successful_execution(                     │
│      "code_review",                                     │
│      health,                                            │
│      retry_count,                                       │
│      result_data['duration'],                           │
│      result_data['result']  ← Pass to state machine    │
│  )                                                      │
│                                                         │
│  # Return to orchestrator                               │
│  return result_data['result']                           │
└────────┬────────────────────────────────────────────────┘
         │
         │ Return to orchestrator
         │
         ▼
┌────────────────────┐
│  Orchestrator      │
│                    │
│  result = {        │
│      "review_      │
│      results": [], │
│      "overall_     │
│      score": 65    │
│  }                 │
│                    │
│  # Use result      │
└────────────────────┘
```

---

## Meanwhile, in the State Machine...

While the return value flows back to the orchestrator, the supervisor **also** stores it:

```python
# In supervisor_agent.py:1025-1051
def _handle_successful_execution(
    self,
    stage_name,
    health,
    retry_count,
    duration,
    result=None  # ← Supervisor passes the result here
):
    # Update health metrics
    health.execution_count += 1
    health.total_duration += duration

    # Store result in state machine
    if self.state_machine and result is not None:
        self.state_machine.push_state(
            PipelineState.STAGE_COMPLETED,
            {
                "stage": stage_name,
                "result": result,  # ← The complete result from stage.execute()
                "duration": duration,
                "retry_count": retry_count,
                "timestamp": datetime.now().isoformat()
            }
        )
```

---

## Visual: Two Paths for the Result

```
┌─────────────────┐
│ Stage.execute() │
└────────┬────────┘
         │
         │ Returns result dict
         │
         ▼
    {
        "review_results": [...],
        "refactoring_suggestions": "...",
        "overall_score": 65
    }
         │
         │
    ┌────┴────┐
    │         │
    │  Split  │
    │         │
    └────┬────┘
         │
         │
    ┌────┴──────────────────────────────────┐
    │                                       │
    ▼                                       ▼
PATH 1: Return to Orchestrator      PATH 2: Store in State Machine
    │                                       │
    │                                       │
    ▼                                       ▼
┌────────────────┐              ┌──────────────────────┐
│  Orchestrator  │              │  State Machine       │
│                │              │  _state_stack.append(│
│  Uses result:  │              │    {                 │
│  - Store in    │              │      "stage": "...", │
│    RAG         │              │      "result": {...} │
│  - Continue    │              │    }                 │
│    pipeline    │              │  )                   │
└────────────────┘              └──────────────────────┘
```

**Key Point**: The result goes to **TWO places**:
1. **Path 1**: Returns to orchestrator (normal Python return)
2. **Path 2**: Stored in state machine (side effect via supervisor)

---

## Why This Design Works

### 1. No Communication Protocol Needed
- Stages don't need to "send" messages to supervisor
- Stages just return normally (standard Python)
- Supervisor captures return value because it wraps the call

### 2. Transparent to Stages
- Stages don't know they're being supervised
- No coupling between stage and supervisor
- Any callable with `.execute()` method works

### 3. Transparent to Orchestrator
- Orchestrator doesn't know supervisor is storing state
- Orchestrator just gets the result back
- No change to orchestrator's code

### 4. Clean Separation of Concerns
- **Stage**: Does its job, returns result
- **Supervisor**: Wraps execution, stores state, handles retries
- **Orchestrator**: Manages workflow, uses results
- **State Machine**: Stores history

---

## Concrete Example: Code Review Stage

### The Code Review Stage Implementation

```python
# In code_review_stage.py
class CodeReviewStage:
    def execute(self, card_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute code review

        Returns:
            Dict with review results and refactoring suggestions
        """
        # Review code
        review_results = self._review_code(card_id, context)

        # Generate refactoring suggestions if review failed
        refactoring_suggestions = None
        if self._needs_refactoring(review_results):
            refactoring_suggestions = self._generate_refactoring_suggestions(
                review_results,
                card_id,
                context.get('task_title', '')
            )

        # Return result dict - JUST A NORMAL RETURN
        return {
            "review_results": review_results,
            "refactoring_suggestions": refactoring_suggestions,
            "overall_score": self._calculate_overall_score(review_results),
            "total_critical_issues": self._count_critical_issues(review_results)
        }
```

**Notice**: The stage doesn't:
- Call `supervisor.store_state()`
- Send a message to supervisor
- Know supervisor exists
- Do anything special

It just **returns a dict**, like any normal Python function.

---

### How Supervisor Captures This

```python
# In orchestrator
code_review_stage = CodeReviewStage(...)

# Orchestrator calls supervisor, passes stage object
result = supervisor.execute_stage_with_supervision(
    code_review_stage,  # ← The stage object
    "code_review",
    card_id=card_id,
    context=context
)

# Inside supervisor:
def execute_stage_with_supervision(self, stage, stage_name, *args, **kwargs):
    # ...
    result = stage.execute(*args, **kwargs)  # ← Calls code_review_stage.execute()
    # ↑
    # This is just calling: code_review_stage.execute(card_id, context)
    # The return value from execute() is captured in 'result' variable

    # Supervisor now has the result
    # Store it in state machine
    self.state_machine.push_state(
        PipelineState.STAGE_COMPLETED,
        {"stage": stage_name, "result": result}
    )

    # Return to orchestrator
    return result
```

---

## Why No "Sending" Needed?

In Python, when you call a function, the return value is automatically available to the caller:

```python
# Simple example
def add(a, b):
    return a + b

result = add(2, 3)  # result = 5

# The add() function doesn't "send" 5 to the caller
# It just returns 5, and Python gives it to the caller
```

Same with stages:

```python
# Stage returns result
def execute(card_id, context):
    return {"score": 65, "suggestions": "..."}

# Supervisor calls stage and gets result
result = stage.execute(card_id, context)  # result = {"score": 65, ...}

# Stage didn't "send" anything
# Supervisor called execute() and captured the return value
```

---

## Summary

**Question**: How does supervisor receive state information?

**Answer**:
1. **Orchestrator calls supervisor**, not stage directly
2. **Supervisor calls stage.execute()** and captures return value
3. **Supervisor stores result** in state machine
4. **Supervisor returns result** to orchestrator

**No messaging protocol needed** - it's just normal Python function calls and return values.

**The supervisor wraps the stage execution**, so it sits "in the middle" and can see everything that passes through.

```
Orchestrator → Supervisor → Stage
                   ↑
                   │
                   └─ Stores result in state machine
                   │
Orchestrator ← Supervisor ← Stage (returns)
```

---

## Diagram: Information Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATOR                                │
│                                                                     │
│  result = supervisor.execute_stage_with_supervision(                │
│      code_review_stage,  ← Passes stage OBJECT                     │
│      "code_review",                                                 │
│      card_id=card_id,                                               │
│      context=context                                                │
│  )                                                                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ Calls supervisor method
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         SUPERVISOR                                  │
│                                                                     │
│  def execute_stage_with_supervision(stage, stage_name, *args, **k):│
│      # Supervisor calls the stage                                  │
│      result = stage.execute(*args, **kwargs)                       │
│                ↑                                                    │
│                │                                                    │
│                └─── This is the actual call                        │
│                                                                     │
│      # Supervisor now HAS the result                               │
│      # (because it called execute() and captured return value)     │
│                                                                     │
│      # Store in state machine                                      │
│      self.state_machine.push_state(                                │
│          STAGE_COMPLETED,                                          │
│          {"stage": stage_name, "result": result}                   │
│      )                                                             │
│                                                                     │
│      # Return to orchestrator                                      │
│      return result                                                 │
└────────┬────────────────────────────────────────────────────────────┘
         │
         │ Calls stage.execute()
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         CODE REVIEW STAGE                           │
│                                                                     │
│  def execute(card_id, context):                                    │
│      # Review code                                                 │
│      # Generate suggestions                                        │
│                                                                     │
│      # Just return normally                                        │
│      return {                                                      │
│          "review_results": [...],                                  │
│          "refactoring_suggestions": "...",                         │
│          "overall_score": 65                                       │
│      }                                                             │
└─────────────────────────────────────────────────────────────────────┘

RETURN VALUE FLOWS BACK UP:

Stage → Supervisor → State Machine (stored)
                  ↓
              Orchestrator (returned)
```

The stage doesn't send anything. The supervisor **calls** the stage and **captures** what it returns.
