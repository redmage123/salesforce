# Circuit Breaker Integration Guide

## Quick Start

Circuit breakers are now implemented for all critical Artemis components to prevent cascading failures.

### Replace Your Imports

**Before (Risky):**
```python
from rag_agent import RAGAgent
from llm_client import create_llm_client
from knowledge_graph import KnowledgeGraph

# If any of these fail, entire pipeline crashes
rag = RAGAgent(db_path="db")
llm = create_llm_client("openai")
kg = KnowledgeGraph()
```

**After (Protected):**
```python
from protected_components import (
    ProtectedRAGAgent,
    ProtectedLLMClient,
    ProtectedKnowledgeGraph
)

# Fails fast if component is down, prevents cascading failures
rag = ProtectedRAGAgent(db_path="db", fallback_mode=True)
llm = ProtectedLLMClient("openai")
kg = ProtectedKnowledgeGraph(fallback_mode=True)
```

## How It Works

### Circuit Breaker States

1. **CLOSED** (Normal): All requests pass through
2. **OPEN** (Failing): Reject requests immediately, fail fast
3. **HALF_OPEN** (Testing): Try limited requests to test recovery

### Example Flow

```
Call 1: ✅ Success (CLOSED)
Call 2: ❌ ChromaDB timeout (CLOSED, failure_count=1)
Call 3: ❌ ChromaDB timeout (CLOSED, failure_count=2)
Call 4: ❌ ChromaDB timeout (OPEN - circuit trips!)
Call 5: ⛔ Rejected immediately (OPEN)
Call 6: ⛔ Rejected immediately (OPEN)
... wait 60 seconds ...
Call 7: 🔄 Testing recovery (HALF_OPEN)
Call 8: ✅ Success! (HALF_OPEN → CLOSED)
```

## Protected Components

### 1. ProtectedRAGAgent

**Configuration:**
- Failure threshold: 3 failures
- Timeout: 120 seconds
- Fallback mode: Returns `None` instead of raising exception

**Usage:**
```python
from protected_components import ProtectedRAGAgent

# With fallback mode (recommended)
rag = ProtectedRAGAgent(db_path="db", fallback_mode=True)

result = rag.query_similar("test", top_k=5)
if result is None:
    # RAG is down, use hardcoded prompt
    prompt = FALLBACK_PROMPT
else:
    # RAG is working
    prompt = build_prompt_from_rag(result)
```

**Fallback Strategy:**
```python
# Always check if RAG returned None
prompt_data = rag.query_similar(query_text, top_k=1)

if prompt_data:
    # Use RAG-enhanced prompt
    prompt = PromptTemplate.from_rag(prompt_data)
else:
    # Use hardcoded fallback
    prompt = HARDCODED_PROMPTS["developer_conservative"]
```

### 2. ProtectedLLMClient

**Configuration:**
- Failure threshold: 5 failures
- Timeout: 60 seconds
- Fallback mode: **NOT AVAILABLE** (LLM is critical - must fail if down)

**Usage:**
```python
from protected_components import ProtectedLLMClient
from llm_client import LLMMessage

llm = ProtectedLLMClient("openai")

try:
    response = llm.complete(
        messages=[LLMMessage(role="user", content="...")],
        temperature=0.7
    )
    print(response.content)
except LLMClientError as e:
    # LLM is critical - cannot continue
    logger.error(f"LLM unavailable: {e}")
    raise
```

**Why No Fallback?**
LLM is the core of Artemis. If it's down, we cannot generate code. Better to fail fast and report error than produce invalid output.

### 3. ProtectedKnowledgeGraph

**Configuration:**
- Failure threshold: 3 failures
- Timeout: 120 seconds
- Fallback mode: In-memory dict storage

**Usage:**
```python
from protected_components import ProtectedKnowledgeGraph

kg = ProtectedKnowledgeGraph(fallback_mode=True)

# If Neo4j is down, uses in-memory storage
kg.add_node(
    node_id="task-123",
    node_type="task",
    properties={"title": "Implement feature"}
)

# Query works with both Neo4j and in-memory fallback
results = kg.query("MATCH (t:task) RETURN t")
```

## Integration with Existing Code

### Step 1: Update artemis_orchestrator.py

```python
# At the top of artemis_orchestrator.py
from protected_components import (
    ProtectedRAGAgent,
    ProtectedLLMClient,
    ProtectedKnowledgeGraph,
    check_all_protected_components
)

class ArtemisOrchestrator:
    def __init__(self, config: ArtemisConfig):
        # Replace RAGAgent with ProtectedRAGAgent
        if config.enable_rag:
            self.rag = ProtectedRAGAgent(
                db_path=config.rag.db_path,
                fallback_mode=True  # Use fallback if RAG fails
            )

        # Replace LLMClient with ProtectedLLMClient
        self.llm = ProtectedLLMClient(
            provider=config.llm.provider
        )

        # Replace KnowledgeGraph with ProtectedKnowledgeGraph
        if config.enable_knowledge_graph:
            self.kg = ProtectedKnowledgeGraph(
                fallback_mode=True
            )
```

### Step 2: Add Health Check Before Execution

```python
def run(self, card_id: str):
    """Run Artemis pipeline with health checks"""

    # Check circuit breaker status
    statuses = check_all_protected_components()

    open_breakers = [
        name for name, status in statuses.items()
        if status['state'] == 'open'
    ]

    if open_breakers:
        self.logger.warning(
            f"Circuit breakers OPEN: {', '.join(open_breakers)}. "
            f"Running in degraded mode."
        )

    # Continue with pipeline...
```

### Step 3: Add Status Endpoint

```python
def get_system_health(self) -> Dict[str, Any]:
    """Get overall system health"""
    from protected_components import check_all_protected_components

    breaker_statuses = check_all_protected_components()

    all_healthy = all(
        status['state'] == 'closed'
        for status in breaker_statuses.values()
    )

    return {
        "healthy": all_healthy,
        "circuit_breakers": breaker_statuses,
        "timestamp": datetime.now().isoformat()
    }
```

## Monitoring

### CLI Status Check

```bash
# Check all circuit breaker statuses
cd /home/bbrelin/src/repos/salesforce/.agents/agile
python protected_components.py --status

# Output:
{
  "rag_agent": {
    "name": "rag_agent",
    "state": "closed",
    "failure_count": 0,
    "time_until_retry": 0.0
  },
  "llm_openai": {
    "name": "llm_openai",
    "state": "closed",
    "failure_count": 0,
    "time_until_retry": 0.0
  },
  "knowledge_graph": {
    "name": "knowledge_graph",
    "state": "open",  # ⚠️ Problem!
    "failure_count": 5,
    "time_until_retry": 45.3
  }
}
```

### Reset Circuit Breakers

```bash
# Reset all circuit breakers (force retry)
python protected_components.py --reset
```

### Test Individual Components

```bash
# Test RAG
python protected_components.py --test-rag

# Test LLM
python protected_components.py --test-llm
```

## Configuration

### Customize Circuit Breaker Settings

```python
from circuit_breaker import CircuitBreakerConfig, get_circuit_breaker

# Custom configuration for RAG
custom_config = CircuitBreakerConfig(
    failure_threshold=10,  # More tolerant
    timeout_seconds=300,   # Wait 5 minutes
    success_threshold=3    # Need 3 successes to close
)

# Get breaker and update config
rag_breaker = get_circuit_breaker("rag_agent", custom_config)
```

### Environment Variables

Set via environment:
```bash
export ARTEMIS_RAG_FAILURE_THRESHOLD=10
export ARTEMIS_RAG_TIMEOUT_SECONDS=300
export ARTEMIS_LLM_FAILURE_THRESHOLD=5
export ARTEMIS_LLM_TIMEOUT_SECONDS=60
```

Load in code:
```python
import os

config = CircuitBreakerConfig(
    failure_threshold=int(os.getenv("ARTEMIS_RAG_FAILURE_THRESHOLD", "3")),
    timeout_seconds=int(os.getenv("ARTEMIS_RAG_TIMEOUT_SECONDS", "120"))
)
```

## Troubleshooting

### Problem: Circuit breaker keeps opening

**Symptoms:**
- Frequent "Circuit breaker OPEN" errors
- Components working fine when tested individually

**Causes:**
1. Network timeouts
2. Rate limiting
3. Transient failures

**Solutions:**
```python
# 1. Increase failure threshold
config = CircuitBreakerConfig(
    failure_threshold=10,  # More tolerant
    timeout_seconds=120
)

# 2. Add retry logic BEFORE circuit breaker
from tenacity import retry, stop_after_attempt, wait_fixed

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def query_rag_with_retry(text):
    return rag.query_similar(text, top_k=5)

# 3. Use exponential backoff
```

### Problem: Degraded mode not working

**Symptoms:**
- System crashes even with fallback_mode=True

**Cause:**
- Fallback not implemented for all methods

**Solution:**
```python
# Always check for None
result = rag.query_similar("test", top_k=1)

if result is None:
    # Implement proper fallback
    result = use_hardcoded_fallback()
```

### Problem: Circuit breaker never closes

**Symptoms:**
- Circuit stays OPEN even after component recovers

**Cause:**
- No requests being sent to test recovery

**Solution:**
```python
# Manually reset circuit breaker
from protected_components import reset_all_circuit_breakers
reset_all_circuit_breakers()

# Or wait for timeout and send test request
import time
time.sleep(120)  # Wait for timeout
result = rag.query_similar("test", top_k=1)  # This will test recovery
```

## Best Practices

### 1. Always Use Fallbacks for Optional Components

```python
# ✅ GOOD: Optional component with fallback
rag = ProtectedRAGAgent(db_path="db", fallback_mode=True)
prompt_data = rag.query_similar(query, top_k=1)
prompt = prompt_data if prompt_data else HARDCODED_PROMPT

# ❌ BAD: Optional component without fallback
rag = RAGAgent(db_path="db")  # Will crash if ChromaDB down
prompt_data = rag.query_similar(query, top_k=1)
```

### 2. No Fallback for Critical Components

```python
# ✅ GOOD: Critical component fails fast
llm = ProtectedLLMClient("openai")
try:
    response = llm.complete(messages)
except LLMClientError:
    # Cannot continue without LLM - fail gracefully
    logger.error("LLM unavailable")
    return {"error": "Service temporarily unavailable"}

# ❌ BAD: Silent failure of critical component
try:
    response = llm.complete(messages)
except:
    response = None  # This will produce garbage output!
```

### 3. Monitor Circuit Breaker Status

```python
# ✅ GOOD: Check health before long operations
def execute_pipeline(self):
    statuses = check_all_protected_components()

    if any(s['state'] == 'open' for s in statuses.values()):
        self.logger.warning("Some components degraded")
        self.send_alert("Artemis running in degraded mode")

    # Continue with pipeline...
```

### 4. Log Circuit Breaker Events

```python
# Add to logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("artemis.log"),
        logging.StreamHandler()
    ]
)

# Circuit breaker automatically logs:
# - State changes (CLOSED → OPEN → HALF_OPEN → CLOSED)
# - Failure counts
# - Recovery attempts
```

## Migration Checklist

- [ ] Replace `RAGAgent` with `ProtectedRAGAgent`
- [ ] Replace `create_llm_client()` with `ProtectedLLMClient`
- [ ] Replace `KnowledgeGraph` with `ProtectedKnowledgeGraph`
- [ ] Add health check before pipeline execution
- [ ] Implement fallbacks for optional components
- [ ] Add monitoring/alerting for circuit breaker events
- [ ] Test failure scenarios (unplug ChromaDB, invalid API key, etc.)
- [ ] Document circuit breaker status in logs
- [ ] Create runbook for "Circuit breaker OPEN" incidents

## Production Deployment

### Pre-deployment Checklist

```bash
# 1. Test circuit breakers
python protected_components.py --test-rag
python protected_components.py --test-llm

# 2. Verify health checks working
python protected_components.py --status

# 3. Test failure scenario
# Stop ChromaDB, verify graceful degradation
docker stop chroma-db
python artemis_orchestrator.py --card-id test-123
# Should use fallback prompts

# 4. Verify recovery
docker start chroma-db
python protected_components.py --reset
python artemis_orchestrator.py --card-id test-123
# Should use RAG again
```

### Monitoring Setup

Add to your monitoring dashboard:
```python
# Prometheus metrics
circuit_breaker_state{component="rag_agent"} = 0  # CLOSED
circuit_breaker_state{component="llm_openai"} = 1  # OPEN
circuit_breaker_failures{component="rag_agent"} = 3

# Alert rules
ALERT CircuitBreakerOpen
  IF circuit_breaker_state == 1
  FOR 5m
  LABELS { severity="warning" }
  ANNOTATIONS {
    summary = "Circuit breaker {{ $labels.component }} is OPEN"
  }
```

## Summary

Circuit breakers prevent cascading failures by:

1. **Failing Fast**: Don't wait for timeouts, reject immediately
2. **Self-Healing**: Automatically test recovery after timeout
3. **Graceful Degradation**: Use fallbacks when available
4. **Visibility**: Log all state changes

**Golden Rule**: If a component fails, the system should degrade gracefully, not crash catastrophically.
