# Supervisor Learning System - Complete! 🎉

**Status:** ✅ All 5/5 tests passing
**Date:** 2025-10-23
**Feature:** Autonomous Learning & Adaptation

---

## Overview

The supervisor agent now has **autonomous learning capability** that enables it to:

1. **Detect** unexpected states automatically
2. **Learn** solutions by querying LLM (GPT-4o/Claude)
3. **Generate** dynamic recovery workflows
4. **Store** learned solutions in RAG for future reuse
5. **Adapt** and improve over time through experience

This is a **game-changing capability** that allows Artemis to handle novel failure scenarios without human intervention!

---

## ✅ Implementation

### New Files

| File | Purpose | Lines | Status |
|------|---------|-------|--------|
| `supervisor_learning.py` | Learning engine implementation | 700+ | ✅ Complete |
| `test_supervisor_learning.py` | Comprehensive tests | 450+ | ✅ 5/5 passing |

### Updated Files

| File | Changes | Status |
|------|---------|--------|
| `supervisor_agent.py` | +100 lines (integration) | ✅ Complete |

**Total:** 1,250+ lines of autonomous learning capability

---

## 🧠 How It Works

### 1. Unexpected State Detection

When the pipeline enters an unexpected state:

```python
# Supervisor detects unexpected state
unexpected = supervisor.handle_unexpected_state(
    current_state="STAGE_STUCK",
    expected_states=["STAGE_RUNNING", "STAGE_COMPLETED"],
    context={
        "stage_name": "development",
        "error_message": "Developer agents not responding",
        "previous_state": "STAGE_RUNNING"
    }
)
```

**What Gets Captured:**
- Current state vs. expected states
- Error messages and stack traces
- Full context (stage, card_id, previous state)
- Severity assessment (low, medium, high, critical)

---

### 2. LLM Consultation

The supervisor asks an LLM for a solution:

**Prompt sent to LLM:**
```
You are an expert DevOps/SRE engineer helping debug an autonomous AI development pipeline called Artemis.

UNEXPECTED STATE DETECTED:

Current State: STAGE_STUCK
Expected States: STAGE_RUNNING, STAGE_COMPLETED
Severity: high

CONTEXT:
Card ID: card-003
Stage: development
Previous State: STAGE_RUNNING

ERROR INFORMATION:
Developer agents stuck

TASK:
Analyze this unexpected state and provide a step-by-step recovery workflow...
```

**LLM Response (Structured JSON):**
```json
{
  "problem_analysis": "Developer agents are stuck in infinite loop waiting for response",
  "root_cause": "Message queue deadlock between developer-a and developer-b",
  "solution_description": "Clear message queue and restart stuck agents",
  "workflow_steps": [
    {
      "step": 1,
      "action": "cleanup_resources",
      "description": "Clear stuck message queue",
      "parameters": {"queue_name": "developer_messages"}
    },
    {
      "step": 2,
      "action": "restart_process",
      "description": "Restart developer agents",
      "parameters": {"agents": ["developer-a", "developer-b"]}
    },
    {
      "step": 3,
      "action": "retry_stage",
      "description": "Retry development stage",
      "parameters": {"stage": "development"}
    }
  ],
  "confidence": "high",
  "risks": ["May lose in-progress work"],
  "alternative_approaches": ["Manual intervention", "Rollback to checkpoint"]
}
```

---

### 3. Dynamic Workflow Execution

The supervisor executes the learned workflow:

```python
# Apply learned solution
success = supervisor.learning_engine.apply_learned_solution(solution, context)

# Workflow executes:
# Step 1: Cleanup resources ✅
# Step 2: Restart process ✅
# Step 3: Retry stage ✅

# Result: Problem solved!
```

**Tracked Metrics:**
- Times applied
- Times successful
- Success rate (100% in tests!)

---

### 4. Knowledge Storage (RAG)

Solution is stored in RAG for future use:

```python
# Stored in RAG as artifact
{
  "artifact_type": "learned_solution",
  "content": "Solution: Clear message queue and restart stuck agents\n\n" +
             "Problem: Unexpected state STAGE_STUCK...",
  "metadata": {
    "solution_id": "learned-abc123",
    "workflow_steps": [...],
    "success_rate": 1.0,
    "learning_strategy": "llm_consultation",
    "llm_model_used": "gpt-4o"
  }
}
```

**Future Benefit:** Next time a similar problem occurs, supervisor can:
1. Query RAG for similar past solutions
2. Reuse successful solutions instantly
3. No need to consult LLM again (faster + cheaper!)

---

## 📊 API Reference

### Supervisor Methods

#### 1. Enable Learning

```python
supervisor.enable_learning(llm_client)
```

Enables learning capability with an LLM client.

**Parameters:**
- `llm_client`: LLM client (OpenAI, Anthropic, etc.)

**Example:**
```python
from llm_client import get_llm_client

llm = get_llm_client(provider="openai", model="gpt-4o")
supervisor.enable_learning(llm)
```

---

#### 2. Handle Unexpected State

```python
result = supervisor.handle_unexpected_state(
    current_state="STAGE_STUCK",
    expected_states=["STAGE_RUNNING", "STAGE_COMPLETED"],
    context={
        "stage_name": "development",
        "error_message": "Agents deadlocked"
    },
    auto_learn=True  # Automatically learn and apply solution
)
```

**Returns:**
```python
{
    "unexpected_state": UnexpectedState(...),
    "solution": LearnedSolution(...),
    "success": True,
    "action": "learned_and_applied"
}
```

**Actions:**
- `"detected_only"` - Only detected, didn't learn
- `"learning_failed"` - Tried to learn but failed
- `"learned_and_applied"` - Learned solution and applied it

---

#### 3. Query Learned Solutions

```python
solutions = supervisor.query_learned_solutions(
    problem_description="developer agents stuck",
    top_k=3
)
```

Queries RAG for similar past solutions.

**Returns:** List of learned solutions from RAG

---

### Learning Engine Methods

#### 1. Detect Unexpected State

```python
unexpected = learning_engine.detect_unexpected_state(
    card_id="card-001",
    current_state="STAGE_TIMEOUT",
    expected_states=["STAGE_RUNNING", "STAGE_COMPLETED"],
    context={"stage_name": "testing", "timeout": 300}
)
```

**Returns:** `UnexpectedState` object or `None` if state is expected

---

#### 2. Learn Solution

```python
solution = learning_engine.learn_solution(
    unexpected_state,
    strategy=LearningStrategy.LLM_CONSULTATION
)
```

**Strategies:**
- `LLM_CONSULTATION` - Ask LLM for solution (default)
- `SIMILAR_CASE_ADAPTATION` - Adapt from similar past case
- `HUMAN_IN_LOOP` - Request human guidance
- `EXPERIMENTAL_TRIAL` - Try experimental solutions

---

#### 3. Apply Solution

```python
success = learning_engine.apply_learned_solution(
    solution,
    context={"card_id": "card-001"}
)
```

Executes the workflow steps and tracks success rate.

---

## 🧪 Test Results

All 5/5 tests passing:

```
✅ PASS - Detect Unexpected States
✅ PASS - LLM Consultation
✅ PASS - Apply Learned Solutions
✅ PASS - RAG Storage & Retrieval
✅ PASS - Supervisor Integration

🎯 Result: 5/5 tests passed
```

### Test Coverage

1. **Unexpected State Detection**
   - ✅ Correctly ignores expected states
   - ✅ Detects unexpected states
   - ✅ Assesses severity automatically

2. **LLM Consultation**
   - ✅ Builds detailed prompts
   - ✅ Parses structured JSON responses
   - ✅ Extracts workflow steps
   - ✅ Creates learned solutions

3. **Solution Application**
   - ✅ Executes workflow steps in order
   - ✅ Tracks success rates
   - ✅ Reuses solutions multiple times

4. **RAG Storage**
   - ✅ Stores solutions in RAG
   - ✅ Retrieves similar solutions
   - ✅ Updates success rates

5. **Supervisor Integration**
   - ✅ Enable/disable learning
   - ✅ Auto-handle unexpected states
   - ✅ Learning stats in health reports

---

## 💡 Usage Examples

### Example 1: Basic Learning Setup

```python
from supervisor_agent import SupervisorAgent
from llm_client import get_llm_client

# Create supervisor
supervisor = SupervisorAgent(
    card_id="card-001",
    verbose=True
)

# Enable learning with GPT-4o
llm = get_llm_client(provider="openai", model="gpt-4o")
supervisor.enable_learning(llm)

print("✅ Supervisor learning enabled!")
```

---

### Example 2: Auto-Handle Unexpected State

```python
# Pipeline enters unexpected state
result = supervisor.handle_unexpected_state(
    current_state="STAGE_HUNG",
    expected_states=["STAGE_RUNNING", "STAGE_COMPLETED"],
    context={
        "stage_name": "integration",
        "error_message": "Tests hanging for 10 minutes",
        "previous_state": "STAGE_RUNNING"
    },
    auto_learn=True  # Automatically learn and apply solution
)

if result and result["success"]:
    print("✅ Problem resolved automatically!")
    print(f"   Solution: {result['solution'].solution_description}")
else:
    print("❌ Could not resolve automatically, escalating...")
```

---

### Example 3: Manual Learning & Application

```python
# Detect unexpected state
unexpected = supervisor.learning_engine.detect_unexpected_state(
    card_id="card-002",
    current_state="STAGE_CORRUPTED",
    expected_states=["STAGE_COMPLETED"],
    context={"error": "Database corruption detected"}
)

if unexpected:
    # Learn solution from LLM
    solution = supervisor.learning_engine.learn_solution(
        unexpected,
        strategy=LearningStrategy.LLM_CONSULTATION
    )

    # Review solution before applying (human-in-loop)
    print(f"Proposed solution: {solution.solution_description}")
    print(f"Workflow steps: {len(solution.workflow_steps)}")

    confirm = input("Apply solution? (y/n): ")
    if confirm.lower() == 'y':
        success = supervisor.learning_engine.apply_learned_solution(
            solution,
            context={}
        )
        print(f"Result: {'Success' if success else 'Failed'}")
```

---

### Example 4: Query Past Solutions

```python
# Search for similar past solutions
solutions = supervisor.query_learned_solutions(
    problem_description="code review agent crashed",
    top_k=3
)

if solutions:
    print(f"Found {len(solutions)} similar past solutions:")
    for i, sol in enumerate(solutions, 1):
        metadata = sol.get("metadata", {})
        print(f"{i}. {sol.get('content', '')[:100]}...")
        print(f"   Success rate: {metadata.get('success_rate', 0)*100:.1f}%")
        print(f"   Applied: {metadata.get('times_applied', 0)} times")
else:
    print("No similar solutions found, will consult LLM")
```

---

### Example 5: Learning Statistics

```python
# Get comprehensive statistics
stats = supervisor.get_statistics()

if "learning" in stats:
    ln = stats["learning"]
    print(f"\n🧠 Learning Statistics:")
    print(f"   Unexpected states detected: {ln['unexpected_states_detected']}")
    print(f"   Solutions learned: {ln['solutions_learned']}")
    print(f"   Solutions applied: {ln['solutions_applied']}")
    print(f"   LLM consultations: {ln['llm_consultations']}")
    print(f"   Success rate: {ln['average_success_rate']*100:.1f}%")

# Or print full health report
supervisor.print_health_report()
# Includes learning section:
# 🧠 Learning Engine:
#    Unexpected States:       5
#    Solutions Learned:       5
#    Solutions Applied:       8
#    LLM Consultations:       5
#    Successful Applications: 7
#    Failed Applications:     1
#    Average Success Rate:    87.5%
```

---

## 🎯 Benefits

### 1. Autonomous Problem Solving
- ✅ Handles novel failures without human intervention
- ✅ Learns from every unexpected state
- ✅ Builds knowledge base over time

### 2. Reduced Downtime
- ✅ Instant recovery from known issues (RAG lookup)
- ✅ Fast recovery from new issues (LLM consultation)
- ✅ No waiting for human operators

### 3. Continuous Improvement
- ✅ Success rates tracked and improved
- ✅ Failed solutions identified and avoided
- ✅ Best practices emerge from experience

### 4. Cost Efficiency
- ✅ Reuses successful solutions (no repeated LLM calls)
- ✅ Prevents expensive failures
- ✅ Reduces operational overhead

---

## 🔧 Integration with ArtemisOrchestrator

### Step 1: Initialize Supervisor with Learning

```python
from supervisor_agent import SupervisorAgent
from llm_client import get_llm_client

class ArtemisOrchestrator:
    def __init__(self, card_id: str, **kwargs):
        # Create supervisor
        self.supervisor = SupervisorAgent(
            card_id=card_id,
            messenger=self.messenger,
            rag=self.rag,
            verbose=True
        )

        # Enable learning
        llm = get_llm_client(provider="openai", model="gpt-4o")
        self.supervisor.enable_learning(llm)
```

### Step 2: Monitor for Unexpected States

```python
def execute_pipeline(self):
    try:
        # Run pipeline stages
        for stage in self.stages:
            result = self.supervisor.execute_with_supervision(
                stage,
                stage_name=stage.name
            )

            # Check if state is expected
            current_state = self.state_machine.get_current_state()
            expected_states = self.state_machine.get_expected_states()

            if current_state not in expected_states:
                # Handle unexpected state automatically
                recovery = self.supervisor.handle_unexpected_state(
                    current_state=current_state,
                    expected_states=expected_states,
                    context={
                        "stage_name": stage.name,
                        "card_id": self.card_id,
                        "error": str(result.get("error"))
                    }
                )

                if recovery and recovery["success"]:
                    print("✅ Recovered from unexpected state!")
                else:
                    raise Exception("Could not recover")

    except Exception as e:
        print(f"Pipeline failed: {e}")
```

---

## 📊 Statistics & Monitoring

### Health Report with Learning

```
======================================================================
ARTEMIS SUPERVISOR - HEALTH REPORT
======================================================================

✅ Overall Health: HEALTHY

📊 Supervision Statistics:
   Total Interventions:     0
   Successful Recoveries:   0
   ...

🧠 Learning Engine:
   Unexpected States:       1
   Solutions Learned:       1
   Solutions Applied:       1
   LLM Consultations:       1
   Successful Applications: 1
   Failed Applications:     0
   Average Success Rate:    100.0%

======================================================================
```

---

## 🚀 Future Enhancements

Possible improvements:

1. **Multi-Strategy Learning**
   - Try multiple learning strategies in parallel
   - Select best solution based on confidence

2. **Human Validation**
   - Request human approval for high-risk solutions
   - Learn from human feedback

3. **A/B Testing**
   - Test multiple solutions simultaneously
   - Learn which works best

4. **Predictive Learning**
   - Predict failures before they happen
   - Proactively apply preventive solutions

---

## ✅ Summary

**Supervisor Learning System:**

| Feature | Status | Tests |
|---------|--------|-------|
| Unexpected State Detection | ✅ Complete | ✅ Passing |
| LLM Consultation | ✅ Complete | ✅ Passing |
| Workflow Generation | ✅ Complete | ✅ Passing |
| RAG Storage/Retrieval | ✅ Complete | ✅ Passing |
| Supervisor Integration | ✅ Complete | ✅ Passing |

**Overall:** 🎉 **Learning System Complete!**

The supervisor can now autonomously learn from unexpected states, consult LLM for solutions, generate recovery workflows, and improve over time through experience!

This is a **major milestone** that makes Artemis truly autonomous and self-healing! 🚀
