# Inter-Agent Communication Protocol

## Overview

This protocol defines how agents in the pipeline communicate, share information, coordinate actions, and update their specialties. All agents use a standardized message format and shared data structures for efficient collaboration.

## Communication Principles

1. **Standardized Format**: All messages follow JSON schema
2. **Async-Safe**: Messages can be read/written asynchronously
3. **Persistent**: Messages stored in `/tmp/agent_messages/`
4. **Versioned**: Each message has timestamp and version
5. **Typed**: Messages have explicit types and schemas
6. **Auditable**: All communications logged

## Message Format

### Base Message Schema

```json
{
  "protocol_version": "1.0.0",
  "message_id": "msg-{timestamp}-{agent}-{sequence}",
  "timestamp": "2025-10-22T12:00:00Z",
  "from_agent": "architecture-agent",
  "to_agent": "dependency-validation-agent",
  "message_type": "data_update" | "request" | "response" | "notification" | "error",
  "card_id": "card-123",
  "priority": "high" | "medium" | "low",
  "data": {
    // Type-specific payload
  },
  "metadata": {
    "requires_response": true,
    "expires_at": "2025-10-22T13:00:00Z"
  }
}
```

## Message Types

### 1. DATA_UPDATE

Agents share specialty-specific data with downstream agents.

**Example: Architecture → Dependency Validation**
```json
{
  "message_type": "data_update",
  "from_agent": "architecture-agent",
  "to_agent": "dependency-validation-agent",
  "data": {
    "update_type": "adr_created",
    "adr_file": "/tmp/adr/ADR-001-use-chromadb.md",
    "dependencies": [
      "chromadb>=0.4.0",
      "sentence-transformers>=2.2.0"
    ],
    "python_version_required": "3.8",
    "summary": "Selected ChromaDB for vector database"
  }
}
```

**Example: Developer A → Validation Agent**
```json
{
  "message_type": "data_update",
  "from_agent": "developer-a",
  "to_agent": "validation-agent",
  "data": {
    "update_type": "implementation_complete",
    "solution_package": "/tmp/developer_a/solution_package.json",
    "test_coverage": 85,
    "files_created": [
      "src/scoring.py",
      "tests/test_scoring.py"
    ],
    "tdd_compliant": true,
    "ready_for_validation": true
  }
}
```

### 2. REQUEST

Agent requests information or action from another agent.

**Example: Validation Agent → Developer B**
```json
{
  "message_type": "request",
  "from_agent": "validation-agent",
  "to_agent": "developer-b",
  "data": {
    "request_type": "re_run_tests",
    "reason": "Coverage calculation needs refresh",
    "test_paths": [
      "tests/test_scoring.py"
    ],
    "requirements": {
      "min_coverage": 90,
      "include_branch_coverage": true
    }
  },
  "metadata": {
    "requires_response": true,
    "timeout_seconds": 300
  }
}
```

**Example: Orchestrator → Repository Manager**
```json
{
  "message_type": "request",
  "from_agent": "orchestrator-agent",
  "to_agent": "repo-manager-agent",
  "data": {
    "request_type": "cleanup_workspace",
    "include_review_patterns": false,
    "create_branch": true,
    "branch_name": "feature/card-123-scoring"
  },
  "metadata": {
    "requires_response": true,
    "priority": "high"
  }
}
```

### 3. RESPONSE

Agent responds to a request.

**Example: Developer B → Validation Agent**
```json
{
  "message_type": "response",
  "from_agent": "developer-b",
  "to_agent": "validation-agent",
  "in_response_to": "msg-20251022120000-validation-agent-001",
  "data": {
    "response_type": "tests_rerun",
    "status": "success",
    "results": {
      "total_tests": 18,
      "passed": 18,
      "failed": 0,
      "coverage_percent": 92
    }
  }
}
```

### 4. NOTIFICATION

Broadcast information to multiple agents or log important events.

**Example: Integration Agent → All**
```json
{
  "message_type": "notification",
  "from_agent": "integration-agent",
  "to_agent": "all",
  "data": {
    "notification_type": "integration_complete",
    "winner": "developer-a",
    "files_integrated": [
      "src/scoring.py"
    ],
    "regression_tests_passed": true,
    "next_stage": "testing"
  }
}
```

### 5. ERROR

Report errors for other agents to handle or escalate.

**Example: Dependency Validation → Orchestrator**
```json
{
  "message_type": "error",
  "from_agent": "dependency-validation-agent",
  "to_agent": "orchestrator-agent",
  "data": {
    "error_type": "blocking_dependency_conflict",
    "severity": "high",
    "message": "sentence-transformers 2.2.0 incompatible with transformers 4.40.0",
    "resolution_suggestions": [
      "Upgrade sentence-transformers to >=2.3.0",
      "Downgrade transformers to <4.36.0"
    ],
    "blocks_pipeline": true
  }
}
```

## Specialty-Specific Data Structures

### Architecture Agent

```json
{
  "specialty": "architecture",
  "data": {
    "adr_number": 1,
    "adr_file": "/tmp/adr/ADR-001.md",
    "decision": "Use ChromaDB for vector storage",
    "options_evaluated": 3,
    "dependencies_identified": ["chromadb", "sentence-transformers"],
    "architectural_patterns": ["RAG", "vector-search"],
    "implementation_notes": "Use persistent storage for production"
  }
}
```

### Dependency Validation Agent

```json
{
  "specialty": "dependency_validation",
  "data": {
    "validation_status": "PASS",
    "python_version": {
      "required": "3.8",
      "found": "3.9",
      "compatible": true
    },
    "packages_validated": 5,
    "conflicts_found": 0,
    "requirements_file": "/tmp/requirements.txt",
    "environment_ready": true
  }
}
```

### Developer Agents

```json
{
  "specialty": "development",
  "data": {
    "developer_id": "developer-a",
    "approach": "conservative-tdd",
    "implementation_complete": true,
    "test_coverage": 85,
    "tdd_cycles": 12,
    "files_created": 3,
    "tests_passing": true,
    "solution_package": "/tmp/developer_a/solution_package.json"
  }
}
```

### Validation Agent

```json
{
  "specialty": "validation",
  "data": {
    "validation_decision": "DEVELOPER_A_ONLY",
    "developer_a_status": "APPROVED",
    "developer_b_status": "BLOCKED",
    "tdd_compliance_score": "9/9",
    "coverage_met": true,
    "blockers": [
      {
        "developer": "developer-b",
        "issue": "1 test failing"
      }
    ]
  }
}
```

### Arbitration Agent

```json
{
  "specialty": "arbitration",
  "data": {
    "winner": "developer-a",
    "winning_score": 97,
    "scores": {
      "developer-a": 97,
      "developer-b": 94
    },
    "decision_rationale": "Higher simplicity, equal correctness",
    "tie_breaker_used": false
  }
}
```

### Integration Agent

```json
{
  "specialty": "integration",
  "data": {
    "integration_status": "PASS",
    "winner_integrated": "developer-a",
    "regression_tests": {
      "total": 16,
      "passed": 16,
      "failed": 0
    },
    "deployment_verified": true,
    "files_integrated": ["src/scoring.py"]
  }
}
```

### Testing Agent

```json
{
  "specialty": "testing",
  "data": {
    "testing_status": "PASS",
    "quality_gates": {
      "regression_tests": "PASS",
      "uiux": "PASS (95/100)",
      "performance": "PASS (85/100)"
    },
    "production_ready": true,
    "all_gates_passed": true
  }
}
```

### Repository Manager

```json
{
  "specialty": "repository_management",
  "data": {
    "cleanup_complete": true,
    "files_deleted": 15,
    "space_freed_mb": 2.0,
    "branch_created": "feature/card-123-scoring",
    "git_status": {
      "uncommitted_changes": 0,
      "unpushed_commits": 0
    }
  }
}
```

### Orchestrator Agent

```json
{
  "specialty": "orchestration",
  "data": {
    "workflow_plan": {
      "complexity": "medium",
      "parallel_developers": 2,
      "stages": ["architecture", "dependencies", "validation", "arbitration", "integration", "testing"]
    },
    "current_stage": "validation",
    "pipeline_status": "RUNNING",
    "estimated_completion": "2025-10-22T12:30:00Z"
  }
}
```

## Communication Channels

### 1. Message Files

**Location**: `/tmp/agent_messages/`

**Naming**: `{timestamp}_{from_agent}_to_{to_agent}_{message_type}.json`

**Example**: `20251022120000_architecture-agent_to_dependency-validation-agent_data_update.json`

### 2. Shared State File

**Location**: `/tmp/pipeline_state.json`

All agents can read/update shared pipeline state.

```json
{
  "card_id": "card-123",
  "current_stage": "validation",
  "workflow_plan": { ... },
  "agent_statuses": {
    "architecture-agent": "COMPLETE",
    "dependency-validation-agent": "COMPLETE",
    "developer-a": "COMPLETE",
    "developer-b": "IN_PROGRESS",
    "validation-agent": "PENDING"
  },
  "shared_data": {
    "adr_file": "/tmp/adr/ADR-001.md",
    "requirements_file": "/tmp/requirements.txt",
    "winner": null
  },
  "last_updated": "2025-10-22T12:00:00Z",
  "updated_by": "dependency-validation-agent"
}
```

### 3. Agent Registry

**Location**: `/tmp/agent_registry.json`

Tracks all active agents and their capabilities.

```json
{
  "agents": {
    "architecture-agent": {
      "status": "active",
      "specialty": "architecture",
      "capabilities": ["create_adr", "evaluate_options", "document_decisions"],
      "message_endpoint": "/tmp/agent_messages/architecture-agent/",
      "last_heartbeat": "2025-10-22T12:00:00Z"
    },
    "dependency-validation-agent": {
      "status": "active",
      "specialty": "dependency_validation",
      "capabilities": ["validate_dependencies", "check_compatibility", "test_imports"],
      "message_endpoint": "/tmp/agent_messages/dependency-validation-agent/",
      "last_heartbeat": "2025-10-22T12:00:30Z"
    }
  }
}
```

## Communication Patterns

### Pattern 1: Sequential Handoff

```
Architecture Agent → Dependency Validation Agent

1. Architecture creates ADR
2. Architecture sends DATA_UPDATE with dependencies
3. Dependency Validation reads update
4. Dependency Validation validates
5. Dependency Validation updates shared state
6. Dependency Validation sends NOTIFICATION to Orchestrator
```

### Pattern 2: Parallel Collaboration

```
Orchestrator → [Developer A, Developer B] → Validation Agent

1. Orchestrator sends REQUEST to both developers
2. Developers work in parallel
3. Each developer sends DATA_UPDATE when complete
4. Validation Agent waits for both updates
5. Validation Agent processes both solutions
6. Validation Agent sends RESPONSE to Orchestrator
```

### Pattern 3: Error Escalation

```
Developer B → Validation Agent → Orchestrator

1. Developer B encounters error
2. Developer B sends ERROR to Validation Agent
3. Validation Agent evaluates severity
4. Validation Agent escalates ERROR to Orchestrator
5. Orchestrator decides: retry, skip, or abort
6. Orchestrator sends REQUEST with decision
```

### Pattern 4: Broadcast Notification

```
Integration Agent → ALL

1. Integration completes successfully
2. Integration sends NOTIFICATION(type=integration_complete) to "all"
3. All agents receive notification
4. Testing Agent reacts by starting tests
5. Orchestrator updates pipeline status
6. Repository Manager prepares for commit
```

## Agent Communication API

### Python Implementation

```python
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

class AgentMessenger:
    """Handle inter-agent communication"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.message_dir = Path("/tmp/agent_messages")
        self.message_dir.mkdir(exist_ok=True)
        self.inbox = self.message_dir / agent_name
        self.inbox.mkdir(exist_ok=True)

    def send_message(
        self,
        to_agent: str,
        message_type: str,
        data: Dict,
        card_id: str,
        priority: str = "medium"
    ) -> str:
        """Send message to another agent"""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        message_id = f"msg-{timestamp}-{self.agent_name}-{hash(str(data))}"

        message = {
            "protocol_version": "1.0.0",
            "message_id": message_id,
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "from_agent": self.agent_name,
            "to_agent": to_agent,
            "message_type": message_type,
            "card_id": card_id,
            "priority": priority,
            "data": data,
            "metadata": {}
        }

        # Save to recipient's inbox
        recipient_inbox = self.message_dir / to_agent
        recipient_inbox.mkdir(exist_ok=True)

        filename = f"{timestamp}_{self.agent_name}_to_{to_agent}_{message_type}.json"
        filepath = recipient_inbox / filename

        with open(filepath, 'w') as f:
            json.dump(message, f, indent=2)

        return message_id

    def read_messages(
        self,
        message_type: Optional[str] = None,
        from_agent: Optional[str] = None,
        unread_only: bool = True
    ) -> list[Dict]:
        """Read messages from inbox"""
        messages = []

        for filepath in sorted(self.inbox.glob("*.json")):
            with open(filepath) as f:
                message = json.load(f)

            # Filter by type
            if message_type and message["message_type"] != message_type:
                continue

            # Filter by sender
            if from_agent and message["from_agent"] != from_agent:
                continue

            messages.append(message)

            # Mark as read
            if unread_only:
                filepath.rename(filepath.with_suffix('.json.read'))

        return messages

    def update_shared_state(self, card_id: str, updates: Dict):
        """Update shared pipeline state"""
        state_file = Path("/tmp/pipeline_state.json")

        # Load existing state
        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)
        else:
            state = {
                "card_id": card_id,
                "agent_statuses": {},
                "shared_data": {}
            }

        # Update with new data
        for key, value in updates.items():
            if key == "agent_status":
                state["agent_statuses"][self.agent_name] = value
            else:
                state["shared_data"][key] = value

        state["last_updated"] = datetime.utcnow().isoformat() + 'Z'
        state["updated_by"] = self.agent_name

        # Save
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def get_shared_state(self, card_id: str) -> Dict:
        """Get current shared pipeline state"""
        state_file = Path("/tmp/pipeline_state.json")

        if not state_file.exists():
            return {}

        with open(state_file) as f:
            return json.load(f)
```

### Usage Examples

**Architecture Agent sending to Dependency Validation**:
```python
messenger = AgentMessenger("architecture-agent")

messenger.send_message(
    to_agent="dependency-validation-agent",
    message_type="data_update",
    card_id="card-123",
    data={
        "update_type": "adr_created",
        "adr_file": "/tmp/adr/ADR-001.md",
        "dependencies": ["chromadb>=0.4.0"]
    }
)

# Update shared state
messenger.update_shared_state(
    card_id="card-123",
    updates={
        "agent_status": "COMPLETE",
        "adr_file": "/tmp/adr/ADR-001.md"
    }
)
```

**Dependency Validation reading messages**:
```python
messenger = AgentMessenger("dependency-validation-agent")

# Read updates from architecture
messages = messenger.read_messages(
    message_type="data_update",
    from_agent="architecture-agent"
)

for message in messages:
    dependencies = message["data"]["dependencies"]
    # Process dependencies...
```

## Best Practices

1. **Always update shared state**: When completing work, update shared state
2. **Use appropriate message types**: Don't use DATA_UPDATE for requests
3. **Include context**: Card ID should always be included
4. **Handle errors gracefully**: Use ERROR messages for failures
5. **Clean up old messages**: Periodically remove processed messages
6. **Log all communications**: Keep audit trail
7. **Validate message schema**: Verify messages before processing
8. **Use timeouts**: Don't wait indefinitely for responses
9. **Heartbeat monitoring**: Agents should send periodic status updates
10. **Version protocol**: Include protocol_version in all messages

## Communication Flow Diagram

```
┌─────────────┐
│Orchestrator │
└──────┬──────┘
       │
       ├─────────────► Architecture Agent
       │                      │
       │                      ▼
       │               [Creates ADR]
       │                      │
       │                      ├──► Send DATA_UPDATE
       │                      │      (dependencies)
       │                      ▼
       ├─────────────► Dependency Validation
       │                      │
       │                      ▼
       │               [Validates deps]
       │                      │
       │                      ├──► Update shared state
       │                      ▼
       ├─────────────► Developer A & B (parallel)
       │                      │         │
       │                      ▼         ▼
       │               [Implement] [Implement]
       │                      │         │
       │                      ├─────────┤
       │                      ▼         ▼
       │               Send DATA_UPDATE x2
       │                      │
       │                      ▼
       ├─────────────► Validation Agent
       │                      │
       │                      ▼
       │               [Validates both]
       │                      │
       │                      ├──► Send RESPONSE
       │                      ▼
       ├─────────────► Arbitration Agent
       │                      │
       │                      ▼
       │               [Selects winner]
       │                      │
       │                      ├──► Send NOTIFICATION
       │                      │      (winner selected)
       │                      ▼
       ├─────────────► Integration Agent
       │                      │
       │                      ▼
       │               [Integrates winner]
       │                      │
       │                      ├──► Send DATA_UPDATE
       │                      ▼
       ├─────────────► Testing Agent
       │                      │
       │                      ▼
       │               [Runs quality gates]
       │                      │
       │                      ├──► Send NOTIFICATION
       │                      │      (pipeline complete)
       │                      ▼
       └─────────────► Repository Manager
                             │
                             ▼
                      [Commit & push]
```

## Message Priority Levels

- **high**: Errors, blocking issues, critical updates
- **medium**: Normal workflow updates, requests
- **low**: Informational notifications, logs

High priority messages should be processed first and may interrupt current work.

## Error Handling

When an agent encounters an error:

1. Send ERROR message to Orchestrator
2. Update shared state with error details
3. Include resolution suggestions if possible
4. Mark agent status as "ERROR" or "BLOCKED"
5. Wait for Orchestrator decision (retry/skip/abort)

## Conclusion

This protocol enables efficient, standardized communication between all pipeline agents. By using structured messages, shared state, and clear communication patterns, agents can coordinate complex workflows while maintaining their specialized responsibilities.
