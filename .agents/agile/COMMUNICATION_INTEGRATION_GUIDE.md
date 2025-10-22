# Pipeline Communication Integration Guide

## Overview

This guide demonstrates how all pipeline agents use the `AgentMessenger` communication protocol to coordinate efficiently throughout the pipeline execution.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  ORCHESTRATOR AGENT                          │
│  • Coordinates all agents via AgentMessenger                │
│  • Updates shared pipeline state                            │
│  • Broadcasts notifications to all agents                   │
└─────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │  AgentMessenger       │
                │  /tmp/agent_messages/ │
                │  /tmp/pipeline_state.json │
                └───────────┬───────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
    ┌───▼────┐         ┌───▼────┐         ┌───▼────┐
    │RESEARCH│         │ ARCH   │         │ DEP    │         ┌───────┐
    │ AGENT  │────────>│ AGENT  │────────>│ VAL    │────────>│ DEV A │
    │(NEW!)  │         │        │         │ AGENT  │         │ AGENT │
    └────────┘         └────────┘         └────────┘         └───────┘
        │                   │                                      │
        │                   │                                      │
        └───────────────────┴──────────┐                 ┌────────┘
                                       │                 │
                                ┌──────▼─────────────────▼──┐
                                │   SHARED STATE            │
                                │   • Research report       │
                                │   • ADR file              │
                                │   • Dependencies          │
                                │   • Agent statuses        │
                                └───────────────────────────┘
```

---

## Integration Approach

### 0. Research Agent Integration (NEW!)

**When activated:** Complex tasks, high-priority tasks, or when user provides research prompts

```python
from agent_messenger import AgentMessenger

class ResearchAgent:
    def __init__(self, card_id: str):
        self.card_id = card_id
        self.messenger = AgentMessenger("research-agent")
        self.messenger.register_agent(
            capabilities=["autonomous_research", "user_prompted_research", "technology_comparison"],
            status="active"
        )

    def conduct_research(self, task: Dict, user_prompts: List[str]) -> Dict:
        # Autonomous topic identification
        topics = self._identify_research_topics(task)

        # Conduct research on all topics
        research_report = self._execute_research(topics, user_prompts)

        # Send to Architecture Agent
        self.messenger.send_data_update(
            to_agent="architecture-agent",
            card_id=self.card_id,
            update_type="research_complete",
            data={
                "research_report_file": "/tmp/research/report.md",
                "executive_summary": research_report["summary"],
                "recommendations": research_report["recommendations"]
            },
            priority="high"
        )

        # Update shared state
        self.messenger.update_shared_state(
            card_id=self.card_id,
            updates={
                "research_report": "/tmp/research/report.md",
                "research_status": "COMPLETE",
                "recommendations": research_report["recommendations"]
            }
        )

        return research_report
```

### 1. Orchestrator Integration

The orchestrator imports `AgentMessenger` and uses it to:
- Broadcast pipeline start/stage transitions
- Update shared state with current stage
- Read error messages from agents
- Coordinate agent handoffs

```python
from agent_messenger import AgentMessenger

class PipelineOrchestrator:
    def __init__(self, card_id: str):
        self.card_id = card_id
        # Initialize messenger
        self.messenger = AgentMessenger("pipeline-orchestrator")
        # Register orchestrator
        self.messenger.register_agent(
            capabilities=["coordinate_pipeline", "manage_workflow"],
            status="active"
        )

    def run_full_pipeline(self):
        # Broadcast pipeline start
        self.messenger.send_notification(
            to_agent="all",
            card_id=self.card_id,
            notification_type="pipeline_started",
            data={
                "pipeline_id": self.card_id,
                "stages": ["architecture", "dependencies", "validation", ...]
            }
        )

        # Update shared state
        self.messenger.update_shared_state(
            card_id=self.card_id,
            updates={
                "current_stage": "architecture",
                "started_at": datetime.utcnow().isoformat() + 'Z',
                "orchestrator_status": "running"
            }
        )

        # Run architecture stage
        arch_result = self.run_architecture_stage()

        # Send update to dependency validation agent
        self.messenger.send_data_update(
            to_agent="dependency-validation-agent",
            card_id=self.card_id,
            update_type="architecture_complete",
            data={
                "adr_file": arch_result["adr_file"],
                "dependencies_identified": ["chromadb>=0.4.0", "flask>=2.0.0"]
            },
            priority="high"
        )
```

### 2. Architecture Agent Integration

```python
from agent_messenger import AgentMessenger

class ArchitectureAgent:
    def __init__(self, card_id: str):
        self.card_id = card_id
        self.messenger = AgentMessenger("architecture-agent")
        self.messenger.register_agent(
            capabilities=["create_adr", "evaluate_options", "document_decisions"]
        )

    def create_adr(self, card: Dict) -> Dict:
        # Create ADR...
        adr_file = "/tmp/adr/ADR-001.md"

        # Extract dependencies from requirements
        dependencies = self._extract_dependencies(card)

        # Send update to Dependency Validation Agent
        self.messenger.send_data_update(
            to_agent="dependency-validation-agent",
            card_id=self.card_id,
            update_type="adr_created",
            data={
                "adr_file": adr_file,
                "dependencies": dependencies,
                "technical_decisions": {
                    "database": "chromadb",
                    "framework": "flask",
                    "testing": "pytest"
                }
            },
            priority="high"
        )

        # Update shared state
        self.messenger.update_shared_state(
            card_id=self.card_id,
            updates={
                "agent_status": "COMPLETE",
                "adr_file": adr_file,
                "dependencies": dependencies
            }
        )

        # Send notification to all agents
        self.messenger.send_notification(
            to_agent="all",
            card_id=self.card_id,
            notification_type="adr_available",
            data={
                "adr_file": adr_file,
                "message": "Architecture decisions documented"
            },
            priority="low"
        )

        return {"status": "COMPLETE", "adr_file": adr_file}
```

### 3. Dependency Validation Agent Integration

```python
from agent_messenger import AgentMessenger

class DependencyValidationAgent:
    def __init__(self, card_id: str):
        self.card_id = card_id
        self.messenger = AgentMessenger("dependency-validation-agent")
        self.messenger.register_agent(
            capabilities=["validate_dependencies", "check_compatibility"]
        )

    def validate_dependencies(self) -> Dict:
        # Read messages from architecture agent
        messages = self.messenger.read_messages(
            message_type="data_update",
            from_agent="architecture-agent"
        )

        for msg in messages:
            if msg.data.get("update_type") == "adr_created":
                adr_file = msg.data.get("adr_file")
                dependencies = msg.data.get("dependencies", [])

                # Validate each dependency
                validation_results = self._validate_deps(dependencies)

                if validation_results["blockers"]:
                    # Send error to orchestrator
                    self.messenger.send_error(
                        to_agent="pipeline-orchestrator",
                        card_id=self.card_id,
                        error_type="dependency_conflict",
                        message=f"Found {len(validation_results['blockers'])} blockers",
                        severity="high",
                        blocks_pipeline=True,
                        resolution_suggestions=[
                            "Upgrade chromadb to >=0.5.0",
                            "Use alternative vector database"
                        ]
                    )
                else:
                    # Send success to developer agents
                    self.messenger.send_data_update(
                        to_agent="all",
                        card_id=self.card_id,
                        update_type="dependencies_validated",
                        data={
                            "dependencies": dependencies,
                            "requirements_file": "/tmp/requirements.txt",
                            "all_validated": True
                        },
                        priority="high"
                    )

                # Update shared state
                self.messenger.update_shared_state(
                    card_id=self.card_id,
                    updates={
                        "agent_status": "COMPLETE",
                        "dependencies_validated": True,
                        "requirements_file": "/tmp/requirements.txt"
                    }
                )
```

### 4. Developer Agent Integration

```python
from agent_messenger import AgentMessenger

class DeveloperAgent:
    def __init__(self, agent_name: str, card_id: str):
        self.agent_name = agent_name  # "developer-a" or "developer-b"
        self.card_id = card_id
        self.messenger = AgentMessenger(self.agent_name)
        self.messenger.register_agent(
            capabilities=["implement_tdd", "write_tests", "write_code"]
        )

    def implement_solution(self) -> Dict:
        # Read shared state to get ADR and dependencies
        state = self.messenger.get_shared_state(card_id=self.card_id)
        adr_file = state.get("shared_data", {}).get("adr_file")
        dependencies = state.get("shared_data", {}).get("dependencies", [])

        # Read messages from dependency validation
        messages = self.messenger.read_messages(
            message_type="data_update",
            from_agent="dependency-validation-agent"
        )

        # Implement solution using TDD...
        solution = self._implement_tdd(adr_file, dependencies)

        # Send completion to validation agent
        self.messenger.send_data_update(
            to_agent="validation-agent",
            card_id=self.card_id,
            update_type="implementation_complete",
            data={
                "developer": self.agent_name,
                "solution_path": f"/tmp/{self.agent_name.replace('-', '_')}",
                "test_results": solution["test_results"],
                "coverage": solution["coverage"],
                "tests_written_first": True
            },
            priority="high"
        )

        # Update shared state
        self.messenger.update_shared_state(
            card_id=self.card_id,
            updates={
                "agent_status": "COMPLETE",
                f"{self.agent_name}_solution": solution["solution_path"]
            }
        )

        return solution
```

### 5. Validation Agent Integration

```python
from agent_messenger import AgentMessenger

class ValidationAgent:
    def __init__(self, card_id: str):
        self.card_id = card_id
        self.messenger = AgentMessenger("validation-agent")
        self.messenger.register_agent(
            capabilities=["validate_tdd", "check_coverage", "verify_tests"]
        )

    def validate_solutions(self, num_developers: int) -> Dict:
        # Read messages from all developers
        dev_messages = self.messenger.read_messages(
            message_type="data_update",
            unread_only=True
        )

        solutions_ready = []
        for msg in dev_messages:
            if msg.data.get("update_type") == "implementation_complete":
                solutions_ready.append(msg.data.get("developer"))

        # Validate each solution
        validation_results = {}
        for dev_name in solutions_ready:
            result = self._validate_developer(dev_name)
            validation_results[dev_name] = result

            if result["status"] == "BLOCKED":
                # Send error back to developer
                self.messenger.send_error(
                    to_agent=dev_name,
                    card_id=self.card_id,
                    error_type="validation_failed",
                    message=f"{len(result['blockers'])} blockers found",
                    severity="high",
                    blocks_pipeline=False,
                    resolution_suggestions=[b["message"] for b in result["blockers"]]
                )

        # Send results to arbitration agent
        approved_devs = [d for d, r in validation_results.items() if r["status"] == "APPROVED"]

        if len(approved_devs) > 0:
            self.messenger.send_data_update(
                to_agent="arbitration-agent",
                card_id=self.card_id,
                update_type="validation_complete",
                data={
                    "approved_developers": approved_devs,
                    "validation_results": validation_results
                },
                priority="high"
            )

        # Update shared state
        self.messenger.update_shared_state(
            card_id=self.card_id,
            updates={
                "agent_status": "COMPLETE",
                "approved_developers": approved_devs,
                "validation_results": validation_results
            }
        )

        return validation_results
```

### 6. Arbitration Agent Integration

```python
from agent_messenger import AgentMessenger

class ArbitrationAgent:
    def __init__(self, card_id: str):
        self.card_id = card_id
        self.messenger = AgentMessenger("arbitration-agent")
        self.messenger.register_agent(
            capabilities=["score_solutions", "select_winner"]
        )

    def score_and_select_winner(self) -> Dict:
        # Read validation results from shared state
        state = self.messenger.get_shared_state(card_id=self.card_id)
        approved_devs = state.get("shared_data", {}).get("approved_developers", [])

        # Score each approved solution
        scores = {}
        for dev_name in approved_devs:
            score = self._score_solution(dev_name)
            scores[dev_name] = score

        # Select winner
        winner = max(scores.keys(), key=lambda d: scores[d]["total_score"])

        # Send winner notification to integration agent
        self.messenger.send_data_update(
            to_agent="integration-agent",
            card_id=self.card_id,
            update_type="winner_selected",
            data={
                "winner": winner,
                "winner_score": scores[winner],
                "all_scores": scores
            },
            priority="high"
        )

        # Broadcast winner to all agents
        self.messenger.send_notification(
            to_agent="all",
            card_id=self.card_id,
            notification_type="arbitration_complete",
            data={
                "winner": winner,
                "total_score": scores[winner]["total_score"]
            },
            priority="medium"
        )

        # Update shared state
        self.messenger.update_shared_state(
            card_id=self.card_id,
            updates={
                "agent_status": "COMPLETE",
                "winner": winner,
                "arbitration_scores": scores
            }
        )

        return {"winner": winner, "scores": scores}
```

### 7. Integration Agent Integration

```python
from agent_messenger import AgentMessenger

class IntegrationAgent:
    def __init__(self, card_id: str):
        self.card_id = card_id
        self.messenger = AgentMessenger("integration-agent")
        self.messenger.register_agent(
            capabilities=["deploy_solution", "run_regression_tests"]
        )

    def integrate_winner(self) -> Dict:
        # Read winner from arbitration agent
        messages = self.messenger.read_messages(
            message_type="data_update",
            from_agent="arbitration-agent"
        )

        winner = None
        for msg in messages:
            if msg.data.get("update_type") == "winner_selected":
                winner = msg.data.get("winner")
                break

        if not winner:
            # No winner - send error
            self.messenger.send_error(
                to_agent="pipeline-orchestrator",
                card_id=self.card_id,
                error_type="no_winner",
                message="No winning solution selected",
                severity="high",
                blocks_pipeline=True
            )
            return {"status": "FAILED"}

        # Deploy winning solution
        deployment_result = self._deploy_solution(winner)

        # Run regression tests
        test_results = self._run_regression_tests(winner)

        # Send to testing agent
        self.messenger.send_data_update(
            to_agent="testing-agent",
            card_id=self.card_id,
            update_type="integration_complete",
            data={
                "winner": winner,
                "deployed": deployment_result["deployed"],
                "regression_tests": test_results
            },
            priority="high"
        )

        # Update shared state
        self.messenger.update_shared_state(
            card_id=self.card_id,
            updates={
                "agent_status": "COMPLETE",
                "deployed_solution": winner,
                "deployment_verified": deployment_result["deployed"]
            }
        )

        return deployment_result
```

---

## Communication Flows

### Flow 1: Architecture → Dependency Validation

```
Architecture Agent                Dependency Validation Agent
       │                                      │
       │  send_data_update()                 │
       │  ─────────────────────────────────> │
       │  {                                   │
       │    "adr_file": "/tmp/adr/ADR-001.md"│
       │    "dependencies": ["chromadb"]      │
       │  }                                   │
       │                                      │
       │  update_shared_state()               │
       │  ─────────────────────────────────> │
       │                                      │ read_messages()
       │                                      │ get_shared_state()
       │                                      │ validate_dependencies()
       │                                      │
       │                      <─────────────  │ send_data_update()
       │                                      │ (to developer agents)
```

### Flow 2: Parallel Developer Execution

```
Orchestrator              Dev A              Dev B              Shared State
     │                      │                  │                      │
     │ broadcast()          │                  │                      │
     │────────────────────> │ ───────────────> │                      │
     │                      │                  │                      │
     │                      │ get_shared_state()                      │
     │                      │ ─────────────────────────────────────> │
     │                      │                  │ get_shared_state()   │
     │                      │                  │ ──────────────────> │
     │                      │                  │                      │
     │                      │ implement()      │ implement()          │
     │                      │                  │                      │
     │                      │ send_update()    │ send_update()        │
     │   <──────────────────│                  │                      │
     │   <─────────────────────────────────────│                      │
```

### Flow 3: Error Escalation

```
Dependency Validation          Orchestrator
         │                          │
         │ validate_dependencies()  │
         │ ❌ CONFLICT DETECTED     │
         │                          │
         │ send_error()             │
         │ ───────────────────────> │
         │ {                        │
         │   "error_type": "dep..."  │
         │   "severity": "high"     │
         │   "blocks_pipeline": true│
         │   "suggestions": [...]   │
         │ }                        │
         │                          │ read_messages()
         │                          │ process_errors()
         │                          │ STOP PIPELINE
```

---

## Benefits of This Integration

1. **Decoupled Communication**: Agents don't need direct references to each other
2. **Asynchronous Coordination**: Agents can work in parallel and coordinate via messages
3. **Centralized State**: All agents can access/update shared pipeline state
4. **Error Escalation**: Agents can report errors that orchestrator handles
5. **Audit Trail**: All communication is logged automatically
6. **Priority Handling**: High-priority messages (errors, blockers) processed first
7. **Broadcast Support**: Orchestrator can notify all agents of pipeline events
8. **Dynamic Discovery**: Agents can discover each other via registry

---

## Message Examples

### Example 1: Architecture Agent → Dependency Validation

```json
{
  "protocol_version": "1.0.0",
  "message_id": "msg-20251022120000-architecture-agent-1-abc123",
  "timestamp": "2025-10-22T12:00:00Z",
  "from_agent": "architecture-agent",
  "to_agent": "dependency-validation-agent",
  "message_type": "data_update",
  "card_id": "card-20251021135619",
  "priority": "high",
  "data": {
    "update_type": "adr_created",
    "adr_file": "/tmp/adr/ADR-001-revenue-intelligence.md",
    "dependencies": [
      "chromadb>=0.4.0",
      "flask>=2.0.0",
      "scikit-learn>=1.0.0"
    ],
    "technical_decisions": {
      "database": "chromadb",
      "framework": "flask",
      "ml_framework": "scikit-learn"
    }
  },
  "metadata": {}
}
```

### Example 2: Validation Agent → Arbitration Agent

```json
{
  "protocol_version": "1.0.0",
  "message_id": "msg-20251022121500-validation-agent-3-def456",
  "timestamp": "2025-10-22T12:15:00Z",
  "from_agent": "validation-agent",
  "to_agent": "arbitration-agent",
  "message_type": "data_update",
  "card_id": "card-20251021135619",
  "priority": "high",
  "data": {
    "update_type": "validation_complete",
    "approved_developers": ["developer-a", "developer-b"],
    "validation_results": {
      "developer-a": {
        "status": "APPROVED",
        "test_coverage": 85,
        "tests_passed": 16,
        "tests_failed": 0
      },
      "developer-b": {
        "status": "APPROVED",
        "test_coverage": 92,
        "tests_passed": 24,
        "tests_failed": 0
      }
    }
  },
  "metadata": {
    "validation_timestamp": "2025-10-22T12:15:00Z"
  }
}
```

### Example 3: Dependency Validation Error → Orchestrator

```json
{
  "protocol_version": "1.0.0",
  "message_id": "msg-20251022120230-dependency-validation-agent-2-xyz789",
  "timestamp": "2025-10-22T12:02:30Z",
  "from_agent": "dependency-validation-agent",
  "to_agent": "pipeline-orchestrator",
  "message_type": "error",
  "card_id": "card-20251021135619",
  "priority": "high",
  "data": {
    "error_type": "dependency_conflict",
    "severity": "high",
    "message": "chromadb>=0.4.0 conflicts with existing scikit-learn==0.24.0",
    "blocks_pipeline": true,
    "resolution_suggestions": [
      "Upgrade scikit-learn to >=1.0.0",
      "Downgrade chromadb to <0.4.0",
      "Use alternative vector database (e.g., pinecone, weaviate)"
    ]
  },
  "metadata": {
    "conflicting_package": "scikit-learn",
    "required_version": ">=1.0.0",
    "found_version": "0.24.0"
  }
}
```

---

## Implementation Checklist

- [x] AgentMessenger class implemented (`agent_messenger.py`)
- [x] Communication protocol documented (`INTER_AGENT_COMMUNICATION_PROTOCOL.md`)
- [ ] Orchestrator updated to use AgentMessenger
- [ ] Architecture agent prompt updated with messenger usage
- [ ] Dependency validation agent prompt updated
- [ ] Developer agent prompts updated
- [ ] Validation agent prompt updated
- [ ] Arbitration agent prompt updated
- [ ] Integration agent prompt updated
- [ ] Testing agent prompt updated
- [ ] Repository manager agent integrated
- [ ] End-to-end testing with full pipeline

---

## Next Steps

1. **Update Orchestrator**: Integrate AgentMessenger into `pipeline_orchestrator.py`
2. **Update Agent Prompts**: Add messenger usage instructions to all agent prompts
3. **Test Communication**: Run full pipeline and verify message flows
4. **Monitor Logs**: Check `/tmp/agent_messages/logs/` for audit trail
5. **Optimize**: Tune message priorities and shared state updates
