# Protected Artemis Orchestrator - Usage Guide

## Quick Start

The protected orchestrator automatically wraps all critical components (RAG, LLM, Knowledge Graph) with circuit breaker protection.

### Option 1: Use Protected Factory (Recommended)

```python
from artemis_orchestrator_protected import create_protected_orchestrator
from kanban_manager import KanbanBoard
from messenger_factory import MessengerFactory

# Create board and messenger
board = KanbanBoard("kanban_board.json")
messenger = MessengerFactory.create("file")

# Create protected orchestrator
orchestrator = create_protected_orchestrator(
    card_id="card-123",
    board=board,
    messenger=messenger,
    rag_db_path="db",
    enable_supervision=True,
    check_health=True  # Check health before starting
)

# Run normally - circuit breakers active
orchestrator.run()
```

### Option 2: Modify Existing Code

If you have existing code creating `ArtemisOrchestrator`, replace component imports:

**Before:**
```python
from rag_agent import RAGAgent
from llm_client import create_llm_client

rag = RAGAgent(db_path="db")
llm = create_llm_client("openai")

orchestrator = ArtemisOrchestrator(..., rag=rag, ...)
```

**After:**
```python
from protected_components import ProtectedRAGAgent, ProtectedLLMClient

rag = ProtectedRAGAgent(db_path="db", fallback_mode=True)
llm = ProtectedLLMClient("openai")

orchestrator = ArtemisOrchestrator(..., rag=rag, ...)
```

## Health Checks

### Before Running Artemis

```bash
# Check if system is healthy
python artemis_orchestrator_protected.py --health

# Output:
# ======================================================================
# ARTEMIS HEALTH CHECK
# ======================================================================
# Overall Status: HEALTHY
# Total Components: 3
# ✅ Healthy: rag_agent, llm_openai, knowledge_graph
# ======================================================================
```

### Get JSON Health Summary

```bash
python artemis_orchestrator_protected.py --health-summary
```

Output:
```json
{
  "status": "healthy",
  "healthy_components": ["rag_agent", "llm_openai"],
  "degraded_components": [],
  "recovering_components": [],
  "total_components": 2,
  "circuit_breakers": {
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
    }
  }
}
```

## Integration with Hydra

### Update Hydra Main

In your main Hydra entry point:

```python
import hydra
from omegaconf import DictConfig
from artemis_orchestrator_protected import (
    create_protected_orchestrator,
    check_health_before_run
)

@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig):
    from artemis_services import PipelineLogger
    logger = PipelineLogger(verbose=cfg.logging.verbose)

    # Check health before starting
    if not check_health_before_run(logger):
        logger.log("❌ Health check failed - aborting", "ERROR")
        return 1

    # Create protected orchestrator
    orchestrator = create_protected_orchestrator(
        card_id=cfg.card_id,
        board=board,
        messenger=messenger,
        rag_db_path=cfg.rag.db_path,
        hydra_config=cfg,
        enable_supervision=cfg.pipeline.enable_supervision,
        check_health=False  # Already checked above
    )

    # Run with circuit breaker protection
    orchestrator.run()

if __name__ == "__main__":
    main()
```

## Behavior During Component Failures

### RAG Failure (Degraded Mode)

```
Call 1: ✅ RAG query successful
Call 2: ❌ ChromaDB timeout
Call 3: ❌ ChromaDB timeout
Call 4: ❌ ChromaDB timeout (circuit breaker opens)
Call 5: ⚠️  RAG unavailable - using hardcoded fallback prompts
Call 6+: ⚠️  Continue using fallback (circuit stays open)
... wait 120 seconds ...
Call N: 🔄 Testing RAG recovery
Call N+1: ✅ RAG recovered! (circuit closes)
```

**Impact**: Pipeline continues with hardcoded prompts instead of RAG-enhanced ones.

### LLM Failure (Critical - Cannot Continue)

```
Call 1: ✅ LLM call successful
Call 2: ❌ OpenAI API error
Call 3: ❌ OpenAI API error
Call 4: ❌ OpenAI API error
Call 5: ❌ OpenAI API error
Call 6: ❌ OpenAI API error (circuit breaker opens after 5 failures)
Call 7: ❌ ABORT - LLM is critical, cannot continue
```

**Impact**: Pipeline aborts with error message. User must fix API key/network.

### Knowledge Graph Failure (Degraded Mode)

```
Call 1: ✅ KG write successful
Call 2: ❌ Neo4j connection timeout
Call 3: ❌ Neo4j connection timeout
Call 4: ❌ Neo4j connection timeout (circuit breaker opens)
Call 5: ⚠️  KG unavailable - using in-memory storage
Call 6+: ⚠️  Continue with in-memory (circuit stays open)
```

**Impact**: Task context stored in memory only (lost after restart).

## Production Deployment

### Pre-flight Checklist

```bash
# 1. Check health
python artemis_orchestrator_protected.py --health

# 2. Test RAG connection
python protected_components.py --test-rag

# 3. Test LLM connection
python protected_components.py --test-llm

# 4. Check circuit breaker status
python protected_components.py --status

# 5. If all green, start Artemis
python artemis_orchestrator.py --card-id card-123
```

### Monitoring Script

Create `monitor_artemis.sh`:

```bash
#!/bin/bash

while true; do
    # Check health
    python artemis_orchestrator_protected.py --health-summary > /tmp/artemis_health.json

    # Parse status
    STATUS=$(jq -r '.status' /tmp/artemis_health.json)

    if [ "$STATUS" == "critical" ]; then
        echo "🚨 CRITICAL: Artemis components down!"
        # Send alert
        send_alert "Artemis critical failure"
    elif [ "$STATUS" == "degraded" ]; then
        echo "⚠️  WARNING: Artemis running in degraded mode"
        # Send warning
        send_warning "Artemis degraded"
    else
        echo "✅ Artemis healthy"
    fi

    sleep 60  # Check every minute
done
```

### Recovery Procedures

#### RAG Circuit Breaker Open

```bash
# 1. Check ChromaDB
docker ps | grep chroma

# 2. Restart ChromaDB if down
docker restart chroma-db

# 3. Reset circuit breaker
python protected_components.py --reset

# 4. Test RAG
python protected_components.py --test-rag
```

#### LLM Circuit Breaker Open

```bash
# 1. Check API key
echo $OPENAI_API_KEY

# 2. Test API directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# 3. If API working, reset breaker
python protected_components.py --reset

# 4. Test LLM
python protected_components.py --test-llm
```

## Configuration

### Environment Variables

Control circuit breaker behavior:

```bash
# RAG circuit breaker
export ARTEMIS_RAG_FAILURE_THRESHOLD=5
export ARTEMIS_RAG_TIMEOUT_SECONDS=180

# LLM circuit breaker
export ARTEMIS_LLM_FAILURE_THRESHOLD=10
export ARTEMIS_LLM_TIMEOUT_SECONDS=120

# Health check behavior
export ARTEMIS_FAIL_FAST=true  # Abort on health check failure
```

### Hydra Configuration

Add to `conf/reliability/default.yaml`:

```yaml
circuit_breakers:
  rag:
    failure_threshold: 3
    timeout_seconds: 120
    fallback_mode: true

  llm:
    failure_threshold: 5
    timeout_seconds: 60
    fallback_mode: false  # Cannot fallback for LLM

  knowledge_graph:
    failure_threshold: 3
    timeout_seconds: 120
    fallback_mode: true

health_checks:
  enabled: true
  fail_on_critical: true
  check_before_run: true
```

## Troubleshooting

### Problem: "Health check failed - aborting"

**Cause**: Critical components (LLM) are down.

**Solution**:
```bash
# Check what's failing
python protected_components.py --status

# Look for "state": "open"
# Fix the failing component (API key, network, service restart)
# Reset circuit breaker
python protected_components.py --reset
```

### Problem: Pipeline using fallback prompts

**Symptom**: Logs show "RAG unavailable - using fallback"

**Cause**: RAG circuit breaker open.

**Check**:
```bash
python protected_components.py --status | grep rag_agent
```

**Solution**: Fix RAG/ChromaDB, then reset breaker.

### Problem: Circuit breaker won't close

**Symptom**: Circuit stays OPEN even after fixing component.

**Cause**: No requests sent to test recovery.

**Solution**:
```bash
# Manually reset
python protected_components.py --reset

# Or wait for timeout (60-120 seconds) and send test request
python protected_components.py --test-rag
```

## Performance Impact

Circuit breakers add minimal overhead:

- **Happy path** (all closed): ~0.1ms per call
- **Circuit open**: <0.01ms (fail immediately, no network call)
- **Half-open** (testing): Normal latency for test call

**Memory**: ~1KB per circuit breaker (3 total = 3KB)

## Summary

**Key Benefits**:
1. ✅ Prevents cascading failures
2. ✅ Fails fast instead of hanging
3. ✅ Auto-recovery after timeout
4. ✅ Graceful degradation for optional components
5. ✅ Health checks before execution

**Golden Rule**: If a component fails, the system degrades gracefully instead of crashing.

## Next Steps

1. ✅ Circuit breakers implemented
2. ⏳ Integrate into production
3. ⏳ Add monitoring/alerting
4. ⏳ Create runbooks for failures
5. ⏳ Implement minimal mode (works with zero dependencies)
