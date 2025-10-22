# Communication Protocol Usage Examples

## Real-World Usage in the Pipeline

This document shows **exactly** how the communication protocol is integrated into the pipeline orchestrator and how agents will use it in practice.

---

## 1. Pipeline Orchestrator Integration

### Initialization

```python
class PipelineOrchestrator:
    def __init__(self, card_id: str):
        # Initialize messenger
        self.messenger = AgentMessenger("pipeline-orchestrator")

        # Register with capabilities
        self.messenger.register_agent(
            capabilities=[
                "coordinate_pipeline",
                "manage_workflow",
                "handle_errors",
                "broadcast_notifications"
            ],
            status="active"
        )
```

### Pipeline Start

```python
def run_full_pipeline(self):
    # 1. Broadcast pipeline start to ALL agents
    self.messenger.send_notification(
        to_agent="all",
        card_id=self.card_id,
        notification_type="pipeline_started",
        data={
            "pipeline_id": self.card_id,
            "card_title": card.get("title"),
            "started_at": datetime.utcnow().isoformat() + 'Z'
        },
        priority="medium"
    )

    # 2. Update shared state
    self.messenger.update_shared_state(
        card_id=self.card_id,
        updates={
            "pipeline_status": "running",
            "current_stage": "planning",
            "started_at": datetime.utcnow().isoformat() + 'Z'
        }
    )
```

**What happens?**
- All registered agents receive notification in their inboxes
- Shared state file `/tmp/pipeline_state.json` is created/updated
- Agents can query shared state to see pipeline status

---

## 2. Architecture Stage → Dependency Validation

### Architecture Agent Sends ADR

```python
def run_architecture_stage(self):
    # Create ADR...
    adr_path = "/tmp/adr/ADR-001-task.md"

    # Send ADR to dependency validation agent
    self.messenger.send_data_update(
        to_agent="dependency-validation-agent",
        card_id=self.card_id,
        update_type="adr_created",
        data={
            "adr_file": str(adr_path),
            "adr_number": adr_number,
            "technical_decisions": {
                "approach": "TDD with parallel developers"
            }
        },
        priority="high"
    )

    # Update shared state so ALL agents can see ADR
    self.messenger.update_shared_state(
        card_id=self.card_id,
        updates={
            "current_stage": "architecture_complete",
            "adr_file": str(adr_path),
            "adr_number": adr_number,
            "architecture_status": "COMPLETE"
        }
    )
```

**Message saved to:**
```
/tmp/agent_messages/dependency-validation-agent/
  20251022120000_pipeline-orchestrator_to_dependency-validation-agent_data_update.json
```

**Message content:**
```json
{
  "protocol_version": "1.0.0",
  "message_id": "msg-20251022120000-pipeline-orchestrator-1-abc123",
  "timestamp": "2025-10-22T12:00:00Z",
  "from_agent": "pipeline-orchestrator",
  "to_agent": "dependency-validation-agent",
  "message_type": "data_update",
  "card_id": "card-123",
  "priority": "high",
  "data": {
    "update_type": "adr_created",
    "adr_file": "/tmp/adr/ADR-001-task.md",
    "adr_number": "001",
    "technical_decisions": {
      "approach": "TDD with parallel developers"
    }
  }
}
```

---

## 3. Dependency Validation Stage

### Reading Messages from Architecture Agent

```python
def run_dependency_validation_stage(self):
    # Dependency validation agent would read like this:
    # (In the actual agent implementation, not orchestrator)

    messenger = AgentMessenger("dependency-validation-agent")

    # Read messages from architecture agent
    messages = messenger.read_messages(
        message_type="data_update",
        from_agent="pipeline-orchestrator",
        priority="high"
    )

    for msg in messages:
        if msg.data.get("update_type") == "adr_created":
            adr_file = msg.data.get("adr_file")
            # Validate dependencies from ADR...
```

### Broadcasting Success to Developer Agents

```python
def run_dependency_validation_stage(self):
    # After validation passes...

    # Broadcast to ALL developer agents
    self.messenger.send_notification(
        to_agent="all",
        card_id=self.card_id,
        notification_type="dependencies_validated",
        data={
            "requirements_file": "/tmp/requirements.txt",
            "all_dependencies_validated": True
        },
        priority="high"
    )

    # Update shared state
    self.messenger.update_shared_state(
        card_id=self.card_id,
        updates={
            "current_stage": "dependencies_complete",
            "dependencies_status": "PASS",
            "requirements_file": "/tmp/requirements.txt"
        }
    )
```

**What happens?**
- Message broadcast to ALL agents (developer-a, developer-b, developer-c, etc.)
- Each agent gets copy in their inbox
- Shared state updated so any agent can check status

### Error Handling

```python
def run_dependency_validation_stage(self):
    # If validation fails...

    if len(blockers) > 0:
        # Send error to orchestrator
        self.messenger.send_error(
            to_agent="pipeline-orchestrator",
            card_id=self.card_id,
            error_type="dependency_validation_failed",
            message=f"{len(blockers)} dependency blockers found",
            severity="high",
            blocks_pipeline=True,
            resolution_suggestions=[
                "Upgrade package X to >=1.0.0",
                "Remove conflicting dependency Y"
            ]
        )
```

**Orchestrator receives error:**
```json
{
  "protocol_version": "1.0.0",
  "message_id": "msg-20251022120230-pipeline-orchestrator-2-def456",
  "timestamp": "2025-10-22T12:02:30Z",
  "from_agent": "pipeline-orchestrator",
  "to_agent": "pipeline-orchestrator",
  "message_type": "error",
  "card_id": "card-123",
  "priority": "high",
  "data": {
    "error_type": "dependency_validation_failed",
    "severity": "high",
    "message": "2 dependency blockers found",
    "blocks_pipeline": true,
    "resolution_suggestions": [
      "Upgrade package X to >=1.0.0",
      "Remove conflicting dependency Y"
    ]
  }
}
```

---

## 4. Developer Agents (Parallel Execution)

### How Developer Agents Use Protocol

```python
class DeveloperAgent:
    def __init__(self, agent_name: str, card_id: str):
        self.agent_name = agent_name  # "developer-a" or "developer-b"
        self.card_id = card_id
        self.messenger = AgentMessenger(self.agent_name)

        # Register agent
        self.messenger.register_agent(
            capabilities=["implement_tdd", "write_tests", "write_code"]
        )

    def start_implementation(self):
        # 1. Read shared state to get ADR and requirements
        state = self.messenger.get_shared_state(card_id=self.card_id)
        adr_file = state.get("shared_data", {}).get("adr_file")
        requirements_file = state.get("shared_data", {}).get("requirements_file")

        # 2. Check for dependency validation notification
        messages = self.messenger.read_messages(
            message_type="notification",
            unread_only=True
        )

        dependencies_validated = False
        for msg in messages:
            if msg.data.get("notification_type") == "dependencies_validated":
                dependencies_validated = True
                break

        if not dependencies_validated:
            # Wait or request dependencies
            self.messenger.send_request(
                to_agent="dependency-validation-agent",
                card_id=self.card_id,
                request_type="dependency_status",
                requirements={"need_validation_status": True}
            )
            return

        # 3. Implement solution using TDD
        solution = self.implement_tdd(adr_file, requirements_file)

        # 4. Send completion to validation agent
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

        # 5. Update shared state
        self.messenger.update_shared_state(
            card_id=self.card_id,
            updates={
                f"{self.agent_name}_status": "COMPLETE",
                f"{self.agent_name}_solution": solution["solution_path"],
                f"{self.agent_name}_coverage": solution["coverage"]
            }
        )
```

---

## 5. Pipeline Completion

### Successful Completion

```python
def run_full_pipeline(self):
    try:
        # Execute all stages...

        # On success:
        self.messenger.send_notification(
            to_agent="all",
            card_id=self.card_id,
            notification_type="pipeline_completed",
            data={
                "pipeline_id": self.card_id,
                "status": "COMPLETED_SUCCESSFULLY",
                "completed_at": datetime.utcnow().isoformat() + 'Z',
                "stages_executed": total_stages,
                "parallel_developers": num_devs
            },
            priority="medium"
        )

        # Update shared state
        self.messenger.update_shared_state(
            card_id=self.card_id,
            updates={
                "pipeline_status": "complete",
                "current_stage": "done",
                "completed_at": datetime.utcnow().isoformat() + 'Z',
                "final_status": "COMPLETED_SUCCESSFULLY"
            }
        )

    except Exception as e:
        # On error:
        self.messenger.send_error(
            to_agent="all",
            card_id=self.card_id,
            error_type="pipeline_failure",
            message=f"Pipeline failed: {str(e)}",
            severity="high",
            blocks_pipeline=True
        )

        self.messenger.update_shared_state(
            card_id=self.card_id,
            updates={
                "pipeline_status": "error",
                "error": str(e),
                "completed_at": datetime.utcnow().isoformat() + 'Z'
            }
        )
```

---

## 6. Checking Pipeline Status from Any Agent

### Any Agent Can Query Shared State

```python
# Any agent can do this:
messenger = AgentMessenger("some-agent")

# Get current pipeline status
state = messenger.get_shared_state(card_id="card-123")

print(f"Pipeline Status: {state.get('shared_data', {}).get('pipeline_status')}")
print(f"Current Stage: {state.get('shared_data', {}).get('current_stage')}")
print(f"ADR File: {state.get('shared_data', {}).get('adr_file')}")
print(f"Dependencies File: {state.get('shared_data', {}).get('requirements_file')}")

# Check other agent statuses
agent_statuses = state.get('agent_statuses', {})
for agent_name, status in agent_statuses.items():
    print(f"{agent_name}: {status}")
```

**Shared State File (`/tmp/pipeline_state.json`):**
```json
{
  "card_id": "card-123",
  "pipeline_status": "running",
  "current_stage": "validation",
  "started_at": "2025-10-22T12:00:00Z",
  "agent_statuses": {
    "pipeline-orchestrator": "running",
    "architecture-agent": "COMPLETE",
    "dependency-validation-agent": "COMPLETE",
    "developer-a": "running",
    "developer-b": "running"
  },
  "shared_data": {
    "adr_file": "/tmp/adr/ADR-001-task.md",
    "adr_number": "001",
    "architecture_status": "COMPLETE",
    "requirements_file": "/tmp/requirements.txt",
    "dependencies_status": "PASS"
  },
  "last_updated": "2025-10-22T12:05:00Z",
  "updated_by": "developer-a"
}
```

---

## 7. Message Audit Trail

### All Messages Are Logged

**Location:** `/tmp/agent_messages/logs/{agent_name}.log`

**Example log file (`/tmp/agent_messages/logs/pipeline-orchestrator.log`):**
```json
{"timestamp": "2025-10-22T12:00:00Z", "direction": "sent", "message_id": "msg-001", "message_type": "notification", "from_agent": "pipeline-orchestrator", "to_agent": "all", "card_id": "card-123"}
{"timestamp": "2025-10-22T12:00:30Z", "direction": "sent", "message_id": "msg-002", "message_type": "data_update", "from_agent": "pipeline-orchestrator", "to_agent": "dependency-validation-agent", "card_id": "card-123"}
{"timestamp": "2025-10-22T12:02:30Z", "direction": "received", "message_id": "msg-003", "message_type": "error", "from_agent": "pipeline-orchestrator", "to_agent": "pipeline-orchestrator", "card_id": "card-123"}
```

---

## 8. Complete Communication Flow Diagram

```
Pipeline Start
      │
      ├─> Broadcast "pipeline_started" → ALL agents
      ├─> Update shared_state: pipeline_status="running"
      │
      ▼
Architecture Stage
      │
      ├─> Create ADR
      ├─> Send "adr_created" → dependency-validation-agent
      ├─> Update shared_state: adr_file, adr_number
      │
      ▼
Dependency Validation Stage
      │
      ├─> Read messages from pipeline-orchestrator
      ├─> Validate dependencies
      ├─> IF SUCCESS:
      │     ├─> Broadcast "dependencies_validated" → ALL
      │     └─> Update shared_state: dependencies_status="PASS"
      ├─> IF FAILURE:
      │     ├─> Send ERROR → pipeline-orchestrator
      │     └─> Update shared_state: dependencies_status="BLOCKED"
      │
      ▼
Developer Agents (Parallel)
      │
      ├─> developer-a:
      │     ├─> Read shared_state (get ADR, requirements)
      │     ├─> Implement TDD solution
      │     ├─> Send "implementation_complete" → validation-agent
      │     └─> Update shared_state: developer-a_status="COMPLETE"
      │
      ├─> developer-b:
      │     ├─> Read shared_state (get ADR, requirements)
      │     ├─> Implement TDD solution
      │     ├─> Send "implementation_complete" → validation-agent
      │     └─> Update shared_state: developer-b_status="COMPLETE"
      │
      ▼
Validation Stage
      │
      ├─> Read messages from developers
      ├─> Validate each solution
      ├─> Send results → arbitration-agent
      └─> Update shared_state: approved_developers
      │
      ▼
Arbitration Stage
      │
      ├─> Score solutions
      ├─> Select winner
      ├─> Send "winner_selected" → integration-agent
      ├─> Broadcast "arbitration_complete" → ALL
      └─> Update shared_state: winner, scores
      │
      ▼
Integration Stage
      │
      ├─> Deploy winner
      ├─> Run regression tests
      ├─> Send "integration_complete" → testing-agent
      └─> Update shared_state: deployed_solution
      │
      ▼
Testing Stage
      │
      ├─> Run quality gates
      ├─> IF SUCCESS:
      │     └─> Send "testing_complete" → orchestrator
      │
      ▼
Pipeline Completion
      │
      ├─> Broadcast "pipeline_completed" → ALL
      └─> Update shared_state: pipeline_status="complete"
```

---

## Summary

The communication protocol is integrated into the pipeline through:

1. **AgentMessenger** - Imported and initialized by orchestrator
2. **Registration** - Each agent registers with capabilities
3. **Message Types** - Uses 5 types: data_update, request, response, notification, error
4. **Shared State** - Central `/tmp/pipeline_state.json` for global status
5. **Message Files** - Agent inboxes in `/tmp/agent_messages/`
6. **Audit Logs** - All messages logged in `/tmp/agent_messages/logs/`
7. **Priority Handling** - High-priority errors processed first
8. **Broadcast** - Orchestrator can notify all agents at once

**Benefits:**
- ✅ Decoupled agents (no direct dependencies)
- ✅ Async coordination (parallel execution)
- ✅ Error escalation (automatic routing to orchestrator)
- ✅ Audit trail (complete communication history)
- ✅ Dynamic discovery (agent registry)
- ✅ Shared state (global pipeline status)
