# Observer Pattern for Agent Monitoring

## Summary

The Artemis supervisor now uses the **Observer Pattern** combined with a **Watchdog** for efficient, event-driven agent monitoring. Instead of polling, agents actively register with the supervisor and send heartbeats, while the watchdog detects crashes and hangs via the state machine.

## Key Features

✅ **GPT-5 from Hydra Config** - LLM model configured via `conf/llm/openai.yaml`
✅ **Observer Pattern** - Event-driven monitoring instead of polling
✅ **Agent Registration** - Agents must register on startup
✅ **Heartbeat Mechanism** - Agents signal they're alive
✅ **Watchdog Thread** - Monitors state machine for crashes/hangs
✅ **Event Notifications** - Observers notified of agent events
✅ **Automatic Recovery** - Crash and hang recovery via observers

## Architecture

### Observer Pattern Components

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentHealthObserver                       │
│                    (Abstract Interface)                      │
│  - on_agent_event(agent_name, event, data)                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ implements
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              SupervisorHealthObserver                        │
│            (Concrete Observer - Auto Recovery)               │
│  - Listens for CRASHED, HUNG events                        │
│  - Triggers automatic recovery                               │
│  - Tracks agent start times and activity                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    SupervisorAgent                           │
│                   (Observable Subject)                       │
│  - health_observers: List[AgentHealthObserver]              │
│  - registered_agents: Dict[agent_name, info]               │
│  - register_health_observer(observer)                       │
│  - notify_agent_event(agent_name, event, data)             │
└─────────────────────────────────────────────────────────────┘
```

### Event Flow

```
Agent Lifecycle:
1. Agent starts → supervisor.register_agent(name)
2. Agent works → supervisor.agent_heartbeat(name) every 10-30s
3. Agent completes → supervisor.unregister_agent(name)

Watchdog Detection:
1. Watchdog thread runs every 5 seconds
2. Checks state machine for FAILED state → CRASHED event
3. Checks last_transition_time → HUNG or STALLED event
4. Notifies all observers of detected events

Observer Response:
1. SupervisorHealthObserver receives event
2. For CRASHED → calls supervisor.recover_crashed_agent()
3. For HUNG → calls supervisor.recover_hung_agent()
```

## Configuration

### LLM Model via Hydra

**File:** `conf/llm/openai.yaml`

```yaml
# OpenAI LLM Configuration
provider: openai
model: gpt-5  # Main model for all agents
api_key: ${oc.env:OPENAI_API_KEY}
max_tokens_per_request: 8000
temperature: 0.7
cost_limit_usd: null

# Supervisor-specific LLM settings for auto-fix
supervisor:
  model: gpt-5  # Use GPT-5 for intelligent code fixes
  temperature: 0.3  # Lower temperature for consistent fixes
  max_tokens: 4000
```

**Usage in Code:**

```python
# Supervisor automatically gets config from Hydra
supervisor = SupervisorAgent(
    card_id="card-123",
    rag=rag_agent,
    hydra_config=cfg  # Pass Hydra config
)

# Supervisor extracts LLM settings:
# self.llm_model = cfg.llm.supervisor.model  # "gpt-5"
# self.llm_temperature = cfg.llm.supervisor.temperature  # 0.3
# self.llm_max_tokens = cfg.llm.supervisor.max_tokens  # 4000
```

## Agent Registration (Required)

### Why Registration is Required

Agents **cannot** notify the supervisor if they've crashed (by definition). Therefore:

1. **Agents MUST register** on startup
2. **Agents SHOULD send heartbeats** periodically (every 10-30s)
3. **Watchdog monitors** state machine for crashes
4. **Observers react** to detected events

### Registration API

#### 1. Register Agent (on startup)

```python
# In agent's __init__ or execute method
supervisor.register_agent(
    agent_name="DevelopmentStage",
    agent_type="stage",
    metadata={
        "task_id": "card-123",
        "start_time": datetime.now().isoformat()
    }
)
```

**What happens:**
- Agent added to `supervisor.registered_agents`
- `AgentHealthEvent.STARTED` event sent to observers
- Supervisor starts monitoring this agent

#### 2. Send Heartbeat (periodically)

```python
# Call every 10-30 seconds during execution
supervisor.agent_heartbeat(
    agent_name="DevelopmentStage",
    progress_data={
        "step": "analyzing_code",
        "progress_percent": 45
    }
)
```

**What happens:**
- `last_heartbeat` timestamp updated
- `AgentHealthEvent.PROGRESS` event sent to observers
- Watchdog knows agent is alive

#### 3. Unregister Agent (on completion)

```python
# In agent's cleanup or at end of execute
supervisor.unregister_agent("DevelopmentStage")
```

**What happens:**
- Agent removed from `supervisor.registered_agents`
- `AgentHealthEvent.COMPLETED` event sent to observers
- Supervisor stops monitoring this agent

## Health Events

### AgentHealthEvent Enum

```python
class AgentHealthEvent(Enum):
    STARTED = "started"      # Agent registered
    PROGRESS = "progress"    # Agent sent heartbeat
    STALLED = "stalled"      # No heartbeat for timeout/2
    CRASHED = "crashed"      # State machine in FAILED
    HUNG = "hung"            # No activity for > timeout
    COMPLETED = "completed"  # Agent unregistered
```

### Event Sources

| Event | Source | Trigger |
|-------|--------|---------|
| `STARTED` | Agent registration | `supervisor.register_agent()` |
| `PROGRESS` | Agent heartbeat | `supervisor.agent_heartbeat()` |
| `STALLED` | Watchdog | No activity for > timeout/2 |
| `CRASHED` | Watchdog | State machine in FAILED state |
| `HUNG` | Watchdog | No activity for > timeout |
| `COMPLETED` | Agent unregistration | `supervisor.unregister_agent()` |

## Watchdog Thread

### Starting the Watchdog

```python
# Start watchdog with default settings
watchdog_thread = supervisor.start_watchdog(
    check_interval=5,        # Check every 5 seconds
    timeout_seconds=300      # 5 minute timeout
)

# Watchdog runs in daemon thread, auto-terminates with process
```

### Watchdog Detection Logic

**1. Crash Detection:**
```python
if state_machine.current_state == "FAILED":
    # Notify observers: AgentHealthEvent.CRASHED
    crash_info = extract_error_details()
    supervisor.notify_agent_event(
        agent_name,
        AgentHealthEvent.CRASHED,
        {"crash_info": crash_info, "context": context}
    )
```

**2. Hang Detection:**
```python
elapsed = (now - last_transition_time).total_seconds()

if elapsed > timeout_seconds:
    # Notify observers: AgentHealthEvent.HUNG
    supervisor.notify_agent_event(
        agent_name,
        AgentHealthEvent.HUNG,
        {"timeout_info": {...}}
    )
```

**3. Stall Detection:**
```python
elif elapsed > (timeout_seconds / 2):
    # Notify observers: AgentHealthEvent.STALLED
    supervisor.notify_agent_event(
        agent_name,
        AgentHealthEvent.STALLED,
        {"time_since_activity": elapsed}
    )
```

## Observer Implementation

### Creating a Custom Observer

```python
from supervisor_agent import AgentHealthObserver, AgentHealthEvent

class CustomHealthObserver(AgentHealthObserver):
    """Custom observer for specific monitoring needs"""

    def on_agent_event(
        self,
        agent_name: str,
        event: AgentHealthEvent,
        data: Dict[str, Any]
    ) -> None:
        """Handle agent health events"""
        if event == AgentHealthEvent.CRASHED:
            # Custom crash handling
            self.log_to_database(agent_name, data)
            self.send_slack_alert(agent_name, data)

        elif event == AgentHealthEvent.HUNG:
            # Custom hang handling
            self.escalate_to_human(agent_name, data)

# Register with supervisor
supervisor.register_health_observer(CustomHealthObserver())
```

### Built-in SupervisorHealthObserver

```python
class SupervisorHealthObserver(AgentHealthObserver):
    """Built-in observer that triggers automatic recovery"""

    def on_agent_event(self, agent_name, event, data):
        if event == AgentHealthEvent.CRASHED:
            # Automatic crash recovery
            crash_info = data["crash_info"]
            context = data["context"]
            self.supervisor.recover_crashed_agent(crash_info, context)

        elif event == AgentHealthEvent.HUNG:
            # Automatic hang recovery
            timeout_info = data["timeout_info"]
            self.supervisor.recover_hung_agent(agent_name, timeout_info)
```

## Integration Example

### Full Agent Integration

```python
class DevelopmentStage:
    """Example of fully integrated agent"""

    def __init__(self, supervisor: SupervisorAgent):
        self.supervisor = supervisor
        self.agent_name = "DevelopmentStage"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute development stage with supervisor integration"""

        # 1. Register with supervisor
        self.supervisor.register_agent(
            self.agent_name,
            agent_type="stage",
            metadata={"task_id": context.get("card_id")}
        )

        try:
            # 2. Start background heartbeat thread
            heartbeat_thread = self._start_heartbeat()

            # 3. Do work (with progress updates)
            result = self._do_development_work(context)

            # 4. Stop heartbeat
            heartbeat_thread.stop()

            # 5. Unregister
            self.supervisor.unregister_agent(self.agent_name)

            return result

        except Exception as e:
            # Agent crashes - watchdog will detect via state machine
            raise

    def _start_heartbeat(self) -> threading.Thread:
        """Start heartbeat thread"""
        def heartbeat_loop():
            while not stop_event.is_set():
                self.supervisor.agent_heartbeat(
                    self.agent_name,
                    {"progress": self.get_progress()}
                )
                time.sleep(15)  # Heartbeat every 15 seconds

        stop_event = threading.Event()
        thread = threading.Thread(target=heartbeat_loop, daemon=True)
        thread.stop = stop_event.set
        thread.start()
        return thread

    def _do_development_work(self, context):
        """Actual development work"""
        # Implement development logic
        pass

    def get_progress(self) -> float:
        """Get current progress percentage"""
        # Return progress (0-100)
        return 50.0
```

### Orchestrator Integration

```python
from omegaconf import DictConfig
import hydra

@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig):
    """Artemis orchestrator with supervisor monitoring"""

    # Create supervisor with Hydra config
    supervisor = SupervisorAgent(
        card_id=cfg.card_id,
        rag=rag_agent,
        hydra_config=cfg,  # Pass config for LLM settings
        verbose=True
    )

    # Start watchdog
    watchdog = supervisor.start_watchdog(
        check_interval=5,
        timeout_seconds=300
    )

    # Create stages with supervisor reference
    stages = [
        ProjectAnalysisStage(supervisor),
        DevelopmentStage(supervisor),
        CodeReviewStage(supervisor),
        TestingStage(supervisor)
    ]

    # Execute pipeline
    for stage in stages:
        result = stage.execute(context)
        # Supervisor automatically monitors via observers

if __name__ == "__main__":
    main()
```

## Benefits

### 1. Event-Driven vs Polling

**Before (Polling):**
```python
# Inefficient - wastes CPU checking repeatedly
while True:
    if agent_crashed():
        handle_crash()
    time.sleep(5)  # Check every 5 seconds
```

**After (Observer Pattern):**
```python
# Efficient - only acts when events occur
def on_agent_event(agent_name, event, data):
    if event == AgentHealthEvent.CRASHED:
        handle_crash(data)  # Only when actually crashed
```

### 2. Separation of Concerns

- **Agents**: Focus on their work, send simple heartbeats
- **Watchdog**: Monitors state machine, detects problems
- **Observers**: React to events, trigger recovery
- **Supervisor**: Coordinates everything

### 3. Extensibility

Add new observers without modifying existing code:

```python
# Add database logging
supervisor.register_health_observer(DatabaseLogObserver())

# Add Slack notifications
supervisor.register_health_observer(SlackNotificationObserver())

# Add metrics collection
supervisor.register_health_observer(PrometheusMetricsObserver())
```

### 4. Testability

```python
class MockHealthObserver(AgentHealthObserver):
    def __init__(self):
        self.events = []

    def on_agent_event(self, agent_name, event, data):
        self.events.append((agent_name, event, data))

# Test
observer = MockHealthObserver()
supervisor.register_health_observer(observer)
supervisor.notify_agent_event("TestAgent", AgentHealthEvent.STARTED, {})
assert len(observer.events) == 1
assert observer.events[0][1] == AgentHealthEvent.STARTED
```

## How Agents Notify Crashes (They Don't!)

### The Problem

**Crashed agents cannot notify anyone** - they're crashed!

### The Solution: Watchdog + State Machine

```
Agent Process:
┌─────────────┐
│   Agent     │
│  Working... │ → Updates state machine
└─────────────┘    ↓
       ↓           State: RUNNING
   CRASH! 💥        ↓
       ↓           State: FAILED (set by exception handler)
   (dead)          ↓

Watchdog Process:
┌─────────────┐
│  Watchdog   │ → Checks state machine every 5s
│  Thread     │    ↓
└─────────────┘    Detects: State == FAILED
       ↓           ↓
   Notifies → AgentHealthEvent.CRASHED
   Observers  ↓
       ↓      SupervisorHealthObserver
       ↓           ↓
   Triggers → supervisor.recover_crashed_agent()
   Recovery   ↓
       ↓      LLM auto-fix + restart
       ↓           ↓
   ✅ RECOVERED!
```

### Key Components

1. **State Machine** - Single source of truth for agent state
2. **Exception Handlers** - Update state to FAILED on crash
3. **Watchdog** - Monitors state machine, not agents directly
4. **Observers** - React to state changes
5. **Recovery** - Automatic fix and restart

## Configuration Summary

### Files Modified

1. **conf/llm/openai.yaml** - Added GPT-5 and supervisor-specific settings
2. **supervisor_agent.py** - Added Observer Pattern, watchdog, agent registration

### New Classes

- `AgentHealthEvent` - Event type enum
- `AgentHealthObserver` - Observer interface (ABC)
- `SupervisorHealthObserver` - Built-in recovery observer

### New Methods

- `register_health_observer(observer)` - Register observer
- `unregister_health_observer(observer)` - Unregister observer
- `notify_agent_event(agent_name, event, data)` - Notify all observers
- `register_agent(name, type, metadata)` - Register agent for monitoring
- `unregister_agent(name)` - Unregister agent
- `agent_heartbeat(name, progress)` - Agent signals it's alive
- `start_watchdog(interval, timeout)` - Start watchdog thread

## Best Practices

### For Agent Developers

1. **Always register** on startup:
   ```python
   supervisor.register_agent(self.name, "stage")
   ```

2. **Send heartbeats** every 10-30 seconds:
   ```python
   supervisor.agent_heartbeat(self.name, {"progress": 50})
   ```

3. **Always unregister** on completion:
   ```python
   supervisor.unregister_agent(self.name)
   ```

4. **Use try/finally** to ensure cleanup:
   ```python
   try:
       supervisor.register_agent(...)
       do_work()
   finally:
       supervisor.unregister_agent(...)
   ```

### For Supervisor Configuration

1. **Tune timeouts** based on stage complexity:
   ```python
   # Fast stages
   supervisor.start_watchdog(timeout_seconds=60)

   # Slow stages (LLM-heavy)
   supervisor.start_watchdog(timeout_seconds=600)
   ```

2. **Add custom observers** for specific needs:
   ```python
   supervisor.register_health_observer(MyCustomObserver())
   ```

3. **Configure LLM model** via Hydra, not hardcoded:
   ```yaml
   # conf/llm/openai.yaml
   supervisor:
     model: gpt-5  # Easy to change without code
   ```

## Summary

✅ **GPT-5 Configured** - Via Hydra config, not hardcoded
✅ **Observer Pattern** - Event-driven, not polling
✅ **Agent Registration** - Required for monitoring
✅ **Heartbeat Mechanism** - Agents signal they're alive
✅ **Watchdog Thread** - Monitors state machine
✅ **Automatic Recovery** - Observers trigger fixes
✅ **Extensible** - Easy to add custom observers
✅ **Testable** - Mock observers for testing

The supervisor now has a **production-ready monitoring system** that combines the Observer Pattern with a Watchdog for efficient, event-driven agent health monitoring and automatic recovery!
