---
name: supervisor-agent
description: LLM-powered intelligent supervisor that orchestrates Artemis pipeline stages with context-aware decision making, failure recovery, and continuous learning.
---

# Supervisor Agent

## Purpose

The **Supervisor Agent** is the brain of the Artemis pipeline, using LLM intelligence to:
- **Orchestrate Workflow** - Coordinate multi-stage pipeline execution
- **Make Intelligent Decisions** - Context-aware stage transitions and parameter tuning
- **Recover from Failures** - Root cause analysis and retry strategy selection
- **Learn from History** - Adapt based on past execution patterns
- **Monitor Execution** - Real-time event tracking via Observer Pattern

## When to Use This Skill

The Supervisor Agent is always active as the central coordinator:

1. **Pipeline Orchestration** - Every Artemis pipeline execution
2. **Stage Transitions** - Deciding next stage based on current state
3. **Failure Recovery** - When stages fail and need intelligent retry
4. **Configuration Tuning** - Adjusting parameters based on context
5. **Anomaly Detection** - Identifying unusual execution patterns

## Responsibilities

### 1. Workflow Orchestration

Coordinates the entire Artemis pipeline through multiple stages:

```
Requirements → Sprint Planning → Development → Code Review →
UI/UX Review → Arbitration → Integration → Retrospective
```

**Capabilities:**
- **Dynamic Stage Ordering** - Adjusts stage sequence based on dependencies
- **Parallel Execution** - Runs independent stages concurrently
- **Stage Skipping** - Intelligently bypasses unnecessary stages
- **Checkpoint Integration** - Resumes from interruptions
- **State Machine Coordination** - Manages state transitions

**Example Decision:**
```
Context: Sprint planning completed, but requirements were unclear
Decision: Skip directly to Requirements stage before Development
Reasoning: Insufficient context for developers to proceed
```

### 2. Intelligent Decision Making

Uses LLM to make context-aware decisions:

**Decision Types:**
- **Stage Selection** - Which stage to execute next
- **Parameter Tuning** - Adjusting timeouts, retries, thresholds
- **Resource Allocation** - Number of agents, LLM model selection
- **Quality Gates** - Pass/fail decisions based on context
- **Escalation** - When to involve human intervention

**Example LLM Query:**
```
Input: "Code review found 3 high-severity security issues.
        Developer A has 85% test coverage.
        Developer B has 70% test coverage but cleaner architecture.
        Historical data shows Developer A's code had 2 production bugs.
        Should we proceed to arbitration or request fixes?"

LLM Response: "Request fixes from both developers. Security issues
               are critical and must be addressed before arbitration.
               Provide 2-hour deadline for fixes, then re-review."
```

### 3. Failure Recovery

Performs root cause analysis and intelligent retry:

**Failure Handling:**
- **Root Cause Analysis** - Uses LLM to diagnose failures
- **Retry Strategy Selection** - Chooses optimal retry approach
- **Fallback Orchestration** - Alternative paths when primary fails
- **Circuit Breaking** - Stops retries when futile
- **Human Escalation** - Knows when to ask for help

**Example Recovery:**
```
Failure: LLM API rate limit exceeded during Planning Poker
Root Cause: Too many concurrent API calls
Retry Strategy:
  1. Switch to exponential backoff
  2. Reduce parallelism from 3 to 1
  3. Use cheaper model (gpt-4o-mini) for retries
  4. If still failing after 3 attempts, switch to Anthropic
```

### 4. Learning and Adaptation

Learns from execution history to improve future decisions:

**Learning Mechanisms:**
- **Success Pattern Recognition** - Identifies configurations that work
- **Failure Pattern Recognition** - Avoids known failure modes
- **Performance Optimization** - Tunes for faster execution
- **Cost Optimization** - Balances quality and token usage
- **Anomaly Detection** - Flags unusual behavior

**Example Learning:**
```
Observation: Last 5 sprints, Developer A's code had 0 critical issues
             but Developer B's code failed security review 3 times.

Learned Pattern: Prioritize Developer A's implementation in arbitration
                 when security is critical. Allocate more review time
                 to Developer B.

Action: Adjust arbitration weights and review SLA accordingly.
```

### 5. Observer Pattern Integration

Monitors real-time events from all stages:

**Event Types:**
- **stage.started** - Stage execution begins
- **stage.completed** - Stage finishes successfully
- **stage.failed** - Stage encounters error
- **stage.progress** - Incremental progress updates
- **metric.recorded** - Performance/cost metrics

**Example Event Handling:**
```python
# Supervisor receives event
Event: stage.failed
Stage: code_review
Error: "Developer A: 5 critical security issues"
Context: {
  "issues": ["SQL injection", "XSS", "hardcoded secret", ...],
  "developer": "developer-a",
  "score": 45
}

# Supervisor decision
Action:
  1. Log failure to Knowledge Graph
  2. Send detailed feedback to Developer A
  3. Request fixes with 1-hour deadline
  4. Schedule re-review automatically
  5. Update Developer A's quality score
```

## Integration with Pipeline

### Placement in Pipeline

The Supervisor Agent oversees all stages:

```
           ┌─────────────────────────┐
           │   Supervisor Agent      │
           │  (Orchestrator Brain)   │
           └──────────┬──────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
  Requirements  Sprint Planning  Development
        │             │             │
        └─────────────┼─────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
   Code Review    UI/UX Review  Arbitration
        │             │             │
        └─────────────┼─────────────┘
                      │
                      ▼
               Retrospective
```

### Communication

**Receives:**
- Stage completion events (success/failure)
- Checkpoint state (for resume)
- Configuration overrides
- Human intervention requests

**Sends:**
- Stage execution commands
- Configuration parameters
- Failure notifications
- Learning insights to Knowledge Graph

## Usage Examples

### Standalone Usage

```bash
# The supervisor is typically invoked by the orchestrator
python3 artemis_orchestrator.py \
  --card-id card-12345 \
  --full \
  --supervisor-enabled
```

### Programmatic Usage

```python
from supervisor_agent import SupervisorAgent
from artemis_state_machine import ArtemisStateMachine
from checkpoint_manager import CheckpointManager

# Initialize supervisor
supervisor = SupervisorAgent(
    llm_provider="openai",
    llm_model="gpt-4o",
    logger=logger
)

# Decision: Should we skip a stage?
decision = supervisor.decide_stage_transition(
    current_stage="sprint_planning",
    context={
        "requirements_clarity": 0.3,
        "team_velocity": 15,
        "sprint_capacity": 20
    }
)

# Decision: {
#   "next_stage": "requirements",
#   "reason": "Requirements clarity too low (30%). Need clarification before development.",
#   "confidence": 0.9
# }
```

### Failure Recovery Example

```python
# Stage failed, ask supervisor for recovery strategy
failure_context = {
    "stage": "code_review",
    "error": "LLM API timeout",
    "attempt": 1,
    "max_attempts": 3
}

strategy = supervisor.plan_recovery(failure_context)

# Strategy: {
#   "action": "retry",
#   "delay": 60,  # seconds
#   "modifications": {
#     "timeout": 300,  # increase from 120s
#     "model": "gpt-4o-mini"  # use faster model
#   },
#   "fallback": "switch_to_anthropic"
# }
```

### Learning from History

```python
# After successful sprint, update learning
supervisor.record_execution_outcome(
    sprint_id="sprint-2025-01",
    outcome={
        "success": True,
        "duration": 3600,  # seconds
        "cost": 2.50,  # USD
        "quality_score": 85,
        "stages_executed": ["requirements", "sprint_planning", ...],
        "developer_a_score": 90,
        "developer_b_score": 80
    }
)

# Supervisor learns:
# - This configuration works well
# - Developer A consistently scores higher
# - Requirements stage reduces rework
```

## Configuration

### Environment Variables

```bash
# Enable supervisor (default: true)
ARTEMIS_SUPERVISOR_ENABLED=true

# LLM Provider for supervisor decisions
ARTEMIS_SUPERVISOR_LLM_PROVIDER=openai
ARTEMIS_SUPERVISOR_LLM_MODEL=gpt-4o

# Learning and adaptation
ARTEMIS_SUPERVISOR_LEARNING_ENABLED=true
ARTEMIS_SUPERVISOR_HISTORY_SIZE=100

# Failure recovery
ARTEMIS_SUPERVISOR_MAX_RETRIES=3
ARTEMIS_SUPERVISOR_RETRY_DELAY=60
```

### Hydra Configuration

```yaml
# conf/supervisor/default.yaml
supervisor:
  enabled: true
  llm:
    provider: openai
    model: gpt-4o
  learning:
    enabled: true
    history_size: 100
  recovery:
    max_retries: 3
    retry_delay: 60
    exponential_backoff: true
  decision_thresholds:
    requirements_clarity: 0.5
    code_quality_pass: 75
    security_score_pass: 80
```

## Decision Framework

### Decision Types and Criteria

| Decision | Criteria | Example |
|----------|----------|---------|
| **Skip Stage** | Requirements clarity < 50%, Stage unnecessary | Skip UI/UX for backend-only changes |
| **Request Fixes** | Critical issues > 0, Score < 60 | Security vulnerabilities found |
| **Proceed** | All quality gates pass | Code review passed, tests green |
| **Retry** | Transient failure, Attempts < max | LLM API timeout |
| **Escalate** | Repeated failures, Human needed | Ambiguous requirements |
| **Switch Provider** | Provider failing, Fallback available | OpenAI down, use Anthropic |

### LLM Query Templates

```python
# Template 1: Stage Transition Decision
STAGE_TRANSITION_PROMPT = """
You are the Artemis pipeline supervisor. Decide the next stage.

Current State:
- Stage: {current_stage}
- Status: {status}
- Context: {context}

Available Next Stages: {available_stages}

Historical Data:
- Similar sprints: {similar_sprints}
- Average success rate: {success_rate}

Decide:
1. Which stage to execute next
2. Should any stages be skipped? Why?
3. What parameters should be adjusted?
4. Confidence level (0-1)

Respond with JSON: {{"next_stage": "...", "skip": [], "params": {{}}, "reason": "...", "confidence": 0.9}}
"""

# Template 2: Failure Recovery
FAILURE_RECOVERY_PROMPT = """
A stage has failed. Analyze and recommend recovery.

Failure Details:
- Stage: {stage}
- Error: {error}
- Attempt: {attempt}/{max_attempts}
- Duration before failure: {duration}s

Context:
- Previous similar failures: {similar_failures}
- Current system load: {load}
- Budget remaining: ${budget}

Recommend:
1. Should we retry? With what modifications?
2. Should we skip this stage?
3. Should we escalate to human?
4. Alternative approaches?

Respond with JSON: {{"action": "retry|skip|escalate", "modifications": {{}}, "reason": "..."}}
"""
```

## Integration with Other Agents

### With Knowledge Graph

```python
# Supervisor stores learning in KG
supervisor.knowledge_graph.add_entity(
    entity_type="execution_pattern",
    name=f"sprint-{sprint_id}-pattern",
    properties={
        "success": True,
        "configuration": config_hash,
        "quality_score": 85
    }
)

# Query KG for similar situations
similar_patterns = supervisor.knowledge_graph.query("""
  MATCH (p:execution_pattern {success: true})
  WHERE p.context_similarity > 0.8
  RETURN p.configuration, p.quality_score
  ORDER BY p.quality_score DESC
  LIMIT 5
""")
```

### With Observer Pattern

```python
from pipeline_observer import PipelineObserver

# Supervisor observes all events
observable = PipelineObserver()
observable.register_observer(supervisor)

# Stage emits event
observable.notify_event(
    event_type="stage.failed",
    stage="code_review",
    data={"error": "timeout", "duration": 120}
)

# Supervisor handles event immediately
```

### With Checkpoint Manager

```python
# Save supervisor state
checkpoint_manager.save_checkpoint({
    "stage": "code_review",
    "supervisor_state": supervisor.get_state(),
    "learning_history": supervisor. get_learning_history()
})

# Resume from checkpoint
supervisor.restore_state(checkpoint["supervisor_state"])
```

## Performance Considerations

### LLM Usage Optimization

The supervisor makes strategic decisions to minimize costs:

**Query Optimization:**
- **Caching** - Identical decisions cached for 1 hour
- **Batching** - Multiple decisions in single LLM call
- **Model Selection** - Use gpt-4o-mini for simple decisions
- **Prompt Compression** - Remove redundant context

**Typical Costs:**
- **Stage transition decision**: ~500 tokens ($0.005-0.01)
- **Failure recovery plan**: ~800 tokens ($0.008-0.015)
- **Learning query**: ~1000 tokens ($0.01-0.02)
- **Per sprint total**: ~5000 tokens ($0.05-0.10)

### Decision Latency

| Decision Type | Latency | Can Cache? |
|--------------|---------|------------|
| Stage transition | 1-2s | ✅ Yes (5 min) |
| Failure recovery | 2-3s | ❌ No (context-specific) |
| Parameter tuning | 1-2s | ✅ Yes (per config) |
| Skip decision | 0.5-1s | ✅ Yes (per stage type) |

## Best Practices

1. **Trust the Supervisor** - It learns from history, respect its decisions
2. **Monitor Learning** - Review learning patterns weekly for quality
3. **Tune Thresholds** - Adjust decision thresholds based on team needs
4. **Use Knowledge Graph** - Store learning for long-term memory
5. **Enable Observability** - Log all decisions for audit trail
6. **Test Failure Recovery** - Simulate failures to validate recovery logic
7. **Human Override** - Always allow manual intervention when needed

## Limitations

- **LLM Dependent** - Quality depends on LLM reasoning capability
- **Context Window** - Limited by LLM context size (128K tokens)
- **Cost** - Adds $0.05-0.15 per sprint in LLM costs
- **Latency** - Adds 2-5s per decision
- **Learning Delay** - Requires 10+ executions for good patterns
- **No Guarantees** - LLM decisions are probabilistic, not deterministic

## Future Enhancements

1. **Reinforcement Learning** - Learn from explicit feedback (good/bad decisions)
2. **Multi-Agent Coordination** - Coordinate multiple supervisors in parallel pipelines
3. **Predictive Analytics** - Predict failures before they happen
4. **Auto-Scaling** - Dynamically adjust resources based on load
5. **A/B Testing** - Compare different supervision strategies
6. **Explainability** - Better explanations for decisions (SHAP, LIME)

## Metrics and KPIs

Track supervisor effectiveness:

| Metric | Target | Measurement |
|--------|--------|-------------|
| Decision Accuracy | >85% | % of good decisions (human-validated) |
| Recovery Success Rate | >90% | % of failures successfully recovered |
| Pipeline Efficiency | +20% | Time saved vs. no supervisor |
| Cost Optimization | -15% | Cost reduction through smart routing |
| Quality Improvement | +10% | Higher quality scores with supervision |

## References

- [Observer Pattern](https://refactoring.guru/design-patterns/observer)
- [State Machine Pattern](https://en.wikipedia.org/wiki/Finite-state_machine)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [LLM Decision Making](https://arxiv.org/abs/2305.10601)

---

**Version:** 1.0.0

**Maintained By:** Artemis Pipeline Team

**Last Updated:** October 24, 2025
