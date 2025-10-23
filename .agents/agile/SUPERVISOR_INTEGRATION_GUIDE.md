# Supervisor Integration Guide - Agent Reporting

**Purpose:** Define which agents/stages should report to the supervisor and what data they should send

---

## Overview

The supervisor needs to monitor the entire pipeline to detect failures, unexpected states, and trigger learning. Here's a comprehensive integration plan for all agents and stages.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│              ArtemisOrchestrator                        │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │         SupervisorAgent (Central Monitor)         │ │
│  │  • Monitors all stages                            │ │
│  │  • Detects unexpected states                      │ │
│  │  • Learns solutions from LLM                      │ │
│  │  • Applies recovery workflows                     │ │
│  └───────────────────────────────────────────────────┘ │
│                         ▲                               │
│                         │ Reports                       │
│         ┌───────────────┼───────────────┐              │
│         │               │               │              │
│    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐         │
│    │ Stage 1 │    │ Stage 2 │    │ Stage N │         │
│    └─────────┘    └─────────┘    └─────────┘         │
│         │               │               │              │
│    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐         │
│    │ Agent A │    │ Agent B │    │ Agent C │         │
│    └─────────┘    └─────────┘    └─────────┘         │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Reporting Hierarchy

### Level 1: Pipeline Stages (Primary Reporters)

Stages wrap agent execution and report to supervisor:

1. **ProjectAnalysisStage** → Supervisor
2. **ArchitectureStage** → Supervisor
3. **DependencyStage** → Supervisor
4. **DevelopmentStage** → Supervisor
5. **CodeReviewStage** → Supervisor
6. **ValidationStage** → Supervisor
7. **IntegrationStage** → Supervisor
8. **TestingStage** → Supervisor

### Level 2: Agents (Indirect via Stages)

Agents report to their parent stage, which forwards to supervisor:

1. **ProjectAnalysisAgent** → ProjectAnalysisStage → Supervisor
2. **Developer Agents (A/B)** → DevelopmentStage → Supervisor
3. **CodeReviewAgent** → CodeReviewStage → Supervisor
4. **TestRunner** → ValidationStage → Supervisor

---

## 📡 What Data to Report

### 1. Stage Lifecycle Events

**When:** Stage starts, completes, fails

```python
# Stage start
supervisor.register_stage(
    stage_name="development",
    recovery_strategy=RecoveryStrategy(
        max_retries=3,
        timeout_seconds=600
    )
)

# Stage completion
supervisor.notify_stage_completed(
    stage_name="development",
    duration_seconds=45.2,
    metadata={"developers": 2, "tests_passed": 42}
)

# Stage failure
supervisor.notify_stage_failed(
    stage_name="development",
    error_message="Developer agents timed out",
    context={
        "error": str(exception),
        "stack_trace": traceback.format_exc()
    }
)
```

---

### 2. State Transitions

**When:** Pipeline changes state

```python
# Expected state transition
supervisor.notify_state_transition(
    from_state="STAGE_RUNNING",
    to_state="STAGE_COMPLETED",
    stage_name="development",
    expected=True
)

# Unexpected state transition
supervisor.notify_state_transition(
    from_state="STAGE_RUNNING",
    to_state="STAGE_STUCK",
    stage_name="development",
    expected=False  # Triggers learning!
)
```

---

### 3. Agent Execution Events

**When:** Agent starts/completes execution

```python
# Developer agent starts
supervisor.notify_agent_started(
    agent_name="developer-a",
    stage_name="development",
    card_id="card-001"
)

# Developer agent completes
supervisor.notify_agent_completed(
    agent_name="developer-a",
    stage_name="development",
    success=True,
    output_files=["implementation.py", "tests.py"]
)

# Developer agent fails
supervisor.notify_agent_failed(
    agent_name="developer-a",
    stage_name="development",
    error_message="LLM API rate limit exceeded",
    retry_count=2
)
```

---

### 4. LLM API Calls

**When:** Any agent calls LLM API

```python
# Track LLM call for cost management
supervisor.track_llm_call(
    model="gpt-4o",
    provider="openai",
    tokens_input=5000,
    tokens_output=2000,
    stage="development",
    purpose="developer-a"
)
```

---

### 5. Code Execution Events

**When:** Developer-generated code is executed

```python
# Execute code in sandbox
result = supervisor.execute_code_safely(
    code=developer_generated_code,
    scan_security=True
)

if not result["success"]:
    # Report failure
    supervisor.notify_code_execution_failed(
        stage_name="validation",
        reason=result["kill_reason"],
        code_snippet=code[:200]
    )
```

---

### 6. Resource Usage

**When:** Monitoring resource consumption

```python
# Report resource usage
supervisor.report_resource_usage(
    stage_name="development",
    cpu_percent=85.0,
    memory_mb=450,
    disk_mb=120,
    duration_seconds=45
)
```

---

### 7. Unexpected Errors

**When:** Any unhandled exception occurs

```python
try:
    result = stage.execute(card, context)
except Exception as e:
    # Let supervisor learn from this
    supervisor.handle_unexpected_state(
        current_state="STAGE_FAILED",
        expected_states=["STAGE_COMPLETED"],
        context={
            "stage_name": stage.name,
            "error_message": str(e),
            "stack_trace": traceback.format_exc(),
            "card_id": card["card_id"]
        }
    )
    raise
```

---

## 🔌 Implementation Pattern

### Pattern 1: Wrapper Pattern (Recommended)

Each stage execution is wrapped by supervisor:

```python
class ArtemisOrchestrator:
    def __init__(self, card_id: str):
        self.supervisor = SupervisorAgent(
            card_id=card_id,
            enable_cost_tracking=True,
            enable_sandboxing=True,
            enable_config_validation=True
        )

    def execute_stage(self, stage: PipelineStage, stage_name: str, card: Dict, context: Dict):
        """Execute stage with supervisor monitoring"""

        # Register stage
        self.supervisor.register_stage(stage_name)

        # Execute with supervision (includes retry, circuit breaker, etc.)
        try:
            result = self.supervisor.execute_with_supervision(
                stage=stage,
                stage_name=stage_name,
                card=card,
                context=context
            )

            # Check for unexpected states
            current_state = self.state_machine.get_current_state()
            expected_states = self.state_machine.get_expected_states()

            if current_state not in expected_states:
                # Trigger learning
                recovery = self.supervisor.handle_unexpected_state(
                    current_state=current_state,
                    expected_states=expected_states,
                    context={
                        "stage_name": stage_name,
                        "card_id": card["card_id"],
                        "result": result
                    }
                )

                if not recovery or not recovery["success"]:
                    raise Exception(f"Unexpected state {current_state}, recovery failed")

            return result

        except Exception as e:
            # Supervisor already handled retries, circuit breaker, etc.
            raise
```

---

### Pattern 2: Explicit Reporting

Stages explicitly report events to supervisor:

```python
class DevelopmentStage(PipelineStage):
    def __init__(self, board, messenger, rag, logger, supervisor=None):
        self.board = board
        self.messenger = messenger
        self.rag = rag
        self.logger = logger
        self.supervisor = supervisor  # Inject supervisor

    def execute(self, card: Dict, context: Dict) -> Dict:
        stage_name = "development"

        # Notify start
        if self.supervisor:
            self.supervisor.register_stage(stage_name)

        try:
            # Invoke developers
            developer_results = self.developer_invoker.invoke_parallel_developers(
                num_developers=2,
                card=card,
                adr_content=context["adr_content"],
                adr_file=context["adr_file"]
            )

            # Track LLM calls made by developers
            if self.supervisor:
                for result in developer_results:
                    if "llm_usage" in result:
                        self.supervisor.track_llm_call(
                            model=result["llm_usage"]["model"],
                            provider=result["llm_usage"]["provider"],
                            tokens_input=result["llm_usage"]["tokens_input"],
                            tokens_output=result["llm_usage"]["tokens_output"],
                            stage=stage_name,
                            purpose=result["developer"]
                        )

            # Execute developer code in sandbox
            if self.supervisor:
                for result in developer_results:
                    code_result = self.supervisor.execute_code_safely(
                        code=result["implementation"],
                        scan_security=True
                    )

                    if not code_result["success"]:
                        raise Exception(f"Code execution failed: {code_result['kill_reason']}")

            return {"status": "success", "developer_results": developer_results}

        except Exception as e:
            # Report failure
            if self.supervisor:
                self.supervisor.handle_unexpected_state(
                    current_state="STAGE_FAILED",
                    expected_states=["STAGE_COMPLETED"],
                    context={
                        "stage_name": stage_name,
                        "error_message": str(e),
                        "card_id": card["card_id"]
                    }
                )
            raise
```

---

## 📋 Integration Checklist

### Stage Integration

For each stage, integrate supervisor monitoring:

- [ ] **ProjectAnalysisStage**
  - [ ] Register stage on start
  - [ ] Report unexpected states (analysis fails, user rejects)
  - [ ] Track LLM calls (if using LLM for analysis)

- [ ] **ArchitectureStage**
  - [ ] Register stage on start
  - [ ] Report ADR generation failures
  - [ ] Track LLM calls for ADR generation

- [ ] **DevelopmentStage**
  - [ ] Register stage on start
  - [ ] Report developer agent failures
  - [ ] Track LLM calls for each developer
  - [ ] Execute developer code in sandbox
  - [ ] Report code execution failures

- [ ] **CodeReviewStage**
  - [ ] Register stage on start
  - [ ] Track LLM calls for code review
  - [ ] Report review failures (low scores, security issues)

- [ ] **ValidationStage**
  - [ ] Register stage on start
  - [ ] Execute tests in sandbox
  - [ ] Report test failures
  - [ ] Handle test timeouts

- [ ] **IntegrationStage**
  - [ ] Register stage on start
  - [ ] Report merge conflicts
  - [ ] Track final test execution

### Agent Integration

For each agent, report to parent stage:

- [ ] **Developer Agents (A/B)**
  - [ ] Report start/completion to DevelopmentStage
  - [ ] Include LLM usage metadata in results
  - [ ] Report errors with context

- [ ] **Code Review Agent**
  - [ ] Report start/completion to CodeReviewStage
  - [ ] Include LLM usage metadata
  - [ ] Report critical security findings

- [ ] **Project Analysis Agent**
  - [ ] Report start/completion to ProjectAnalysisStage
  - [ ] Report critical issues found

---

## 🔧 Implementation Example

### Complete Integration Example

```python
# artemis_orchestrator.py

from supervisor_agent import SupervisorAgent
from llm_client import get_llm_client

class ArtemisOrchestrator:
    def __init__(self, card_id: str, **kwargs):
        # Initialize supervisor
        self.supervisor = SupervisorAgent(
            card_id=card_id,
            messenger=self.messenger,
            rag=self.rag,
            verbose=True,
            enable_cost_tracking=True,
            enable_config_validation=True,
            enable_sandboxing=True,
            daily_budget=10.00,
            monthly_budget=200.00
        )

        # Enable learning
        llm = get_llm_client(provider="openai", model="gpt-4o")
        self.supervisor.enable_learning(llm)

        # Create stages with supervisor injection
        self.stages = self._create_stages()

    def _create_stages(self):
        """Create stages with supervisor injection"""
        return [
            ProjectAnalysisStage(
                board=self.board,
                messenger=self.messenger,
                rag=self.rag,
                logger=self.logger,
                supervisor=self.supervisor  # Inject!
            ),
            ArchitectureStage(
                board=self.board,
                messenger=self.messenger,
                rag=self.rag,
                logger=self.logger,
                supervisor=self.supervisor  # Inject!
            ),
            DevelopmentStage(
                board=self.board,
                messenger=self.messenger,
                rag=self.rag,
                logger=self.logger,
                supervisor=self.supervisor  # Inject!
            ),
            # ... other stages
        ]

    def run(self, card: Dict):
        """Execute pipeline with supervisor monitoring"""

        for stage in self.stages:
            stage_name = stage.__class__.__name__

            try:
                # Execute with supervision
                result = self.supervisor.execute_with_supervision(
                    stage=stage,
                    stage_name=stage_name,
                    card=card,
                    context=self.context
                )

                # Update context
                self.context.update(result)

            except Exception as e:
                self.logger.log(f"Stage {stage_name} failed: {e}", "ERROR")

                # Supervisor has already attempted recovery
                # Check if we should continue or abort
                stats = self.supervisor.get_statistics()

                if stats.get("learning"):
                    ln = stats["learning"]
                    if ln["unexpected_states_detected"] > 5:
                        self.logger.log("Too many unexpected states, aborting", "ERROR")
                        raise

                raise

        # Print final health report
        self.supervisor.print_health_report()
```

---

## 📊 Expected Data Flow

### Normal Execution

```
1. Stage starts
   └→ supervisor.register_stage("development")

2. Stage executes
   ├→ Developer A starts
   │  └→ supervisor.track_llm_call(...)
   ├→ Developer B starts
   │  └→ supervisor.track_llm_call(...)
   └→ Both complete

3. Code execution
   └→ supervisor.execute_code_safely(developer_a_code)
   └→ supervisor.execute_code_safely(developer_b_code)

4. Stage completes
   └→ State: STAGE_COMPLETED (expected ✅)
```

### Unexpected State (Learning Trigger)

```
1. Stage starts
   └→ supervisor.register_stage("development")

2. Stage executes
   ├→ Developer A starts
   │  └→ supervisor.track_llm_call(...)
   └→ Developer A hangs...

3. Timeout detected
   └→ State: STAGE_TIMEOUT (unexpected ❌)
   └→ supervisor.handle_unexpected_state()
      ├→ Detect: Current=STAGE_TIMEOUT, Expected=[STAGE_RUNNING, STAGE_COMPLETED]
      ├→ Learn: Query LLM for solution
      │  └→ LLM: "Kill hung process, restart developer, retry stage"
      ├→ Apply: Execute 3-step workflow
      │  ├→ Step 1: Kill process ✅
      │  ├→ Step 2: Restart developer ✅
      │  └→ Step 3: Retry stage ✅
      └→ Store: Save solution in RAG

4. Recovery successful
   └→ State: STAGE_COMPLETED ✅
```

---

## ✅ Summary

**Which agents report to supervisor:**
- ✅ All 8 pipeline stages (primary reporters)
- ✅ Developer agents (via DevelopmentStage)
- ✅ Code review agent (via CodeReviewStage)
- ✅ Test runner (via ValidationStage)

**What data they send:**
- ✅ Lifecycle events (start, complete, fail)
- ✅ State transitions
- ✅ LLM API calls (for cost tracking)
- ✅ Code execution requests (for sandboxing)
- ✅ Unexpected errors (for learning)

**How to integrate:**
- ✅ **Pattern 1:** Wrap with `supervisor.execute_with_supervision()` (easiest)
- ✅ **Pattern 2:** Inject supervisor into stages, explicit reporting (more control)

**Next step:** Update each stage to inject supervisor and report events!
