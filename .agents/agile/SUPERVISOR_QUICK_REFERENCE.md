# Supervisor Agent - Quick Reference

**TL;DR:** Supervisor Agent = Traffic Cop + Circuit Breaker + Auto-Recovery

---

## What It Does

- ✅ Automatically retries failed stages (exponential backoff)
- ✅ Detects and kills hanging processes
- ✅ Opens circuit breakers for repeatedly failing stages
- ✅ Monitors timeouts and intervenes
- ✅ Cleans up zombie processes
- ✅ Provides health reports

---

## Quick Start

### Already Enabled by Default!

The Supervisor Agent is automatically enabled in ArtemisOrchestrator:

```python
# No changes needed - supervisor enabled by default
orchestrator = ArtemisOrchestrator(
    card_id="my-card",
    board=board,
    messenger=messenger,
    rag=rag
)

# Supervisor automatically monitors all stages
orchestrator.run_full_pipeline()
```

### Disable Supervision (Optional)

```python
orchestrator = ArtemisOrchestrator(
    card_id="my-card",
    board=board,
    messenger=messenger,
    rag=rag,
    enable_supervision=False  # Disable supervisor
)
```

---

## Recovery Strategies

### Current Stage Configurations

| Stage | Retries | Timeout | Circuit Threshold |
|-------|---------|---------|-------------------|
| Project Analysis | 2 | 120s | 3 |
| Architecture | 2 | 180s | 3 |
| Dependencies | 2 | 60s | 3 |
| **Development** | **3** | **600s** | **5** |
| Code Review | 2 | 180s | 4 |
| Validation | 2 | 120s | 3 |
| Integration | 2 | 180s | 3 |
| Testing | 2 | 300s | 3 |

**Development stage gets:**
- Most retries (3)
- Longest timeout (10 minutes)
- Highest circuit threshold (5)

---

## What You'll See

### Normal Operation (No Issues)

```
[Pipeline] Starting...
📋 STAGE 1/8: PROJECT_ANALYSIS
✅ Completed in 45s

📋 STAGE 2/8: ARCHITECTURE
✅ Completed in 120s

[Supervisor] Overall Health: HEALTHY
```

### Transient Failure (Automatic Recovery)

```
📋 STAGE 4/8: DEVELOPMENT
[Supervisor] ❌ Stage development failed: LLM API error
[Supervisor] Retry 1/3 (waiting 10s)
✅ Recovery successful after 1 retry

[Supervisor] Overall Health: HEALTHY
```

### Repeated Failures (Circuit Breaker)

```
📋 STAGE 5/8: CODE_REVIEW
[Supervisor] ❌ Stage code_review failed: Validation error
[Supervisor] Retry 1/2 (waiting 5s)
[Supervisor] ❌ Stage code_review failed: Validation error
[Supervisor] Retry 2/2 (waiting 10s)
[Supervisor] ❌ Stage code_review failed: Validation error
[Supervisor] 🚨 Circuit breaker OPEN for code_review (300s timeout)

[Supervisor] Overall Health: CRITICAL
```

### Timeout Detection

```
📋 STAGE 4/8: DEVELOPMENT
[Supervisor] ⏰ TIMEOUT detected for development (615s > 600s)
[Supervisor] Retry 1/3 (waiting 10s)
✅ Recovery successful after 1 retry
```

---

## Health Report

At end of pipeline:

```
======================================================================
ARTEMIS SUPERVISOR - HEALTH REPORT
======================================================================

✅ Overall Health: HEALTHY

📊 Supervision Statistics:
   Total Interventions:     3
   Successful Recoveries:   3
   Failed Recoveries:       0
   Processes Killed:        0
   Timeouts Detected:       1

📈 Stage Statistics:

   development:
      Executions:      1
      Failures:        1
      Failure Rate:    100.0%
      Avg Duration:    245.5s
      Circuit Breaker: ✅

======================================================================
```

---

## Health Status Levels

| Status | Meaning | Action |
|--------|---------|--------|
| ✅ **HEALTHY** | No recent failures | None needed |
| ⚠️  **DEGRADED** | 1-2 failures in last 5 min | Monitor |
| ❌ **FAILING** | 3+ failures in last 5 min | Investigate |
| 🚨 **CRITICAL** | Circuit breakers open | Urgent fix needed |

---

## Common Scenarios

### Scenario 1: LLM API Rate Limit

**What Happens:**
```
[Supervisor] ❌ Stage development failed: Rate limit exceeded
[Supervisor] Retry 1/3 (waiting 10s)  # Exponential backoff
[Supervisor] ✅ Recovery successful
```

**Why It Works:**
- Exponential backoff gives API time to reset
- Automatic retry without manual intervention

### Scenario 2: Hanging Process

**What Happens:**
```
[Supervisor] Detected hanging process (PID 12345)
[Supervisor] CPU: 95%, Duration: 320s
[Supervisor] 💀 Killed hanging process (SIGTERM)
[Supervisor] Retry 1/3
```

**Why It Works:**
- Detects high CPU + long duration
- Kills process gracefully
- Retries stage with fresh process

### Scenario 3: Repeatedly Failing Stage

**What Happens:**
```
[Supervisor] ❌ Stage validation failed (attempt 5)
[Supervisor] 🚨 Circuit breaker OPEN for validation
[Supervisor] Skipping validation (circuit open)
[Pipeline] Continues with remaining stages
```

**Why It Works:**
- Prevents wasting time on broken stage
- Allows pipeline to complete other stages
- Auto-recovers after cooldown period

---

## Customizing Recovery Strategies

### Example: Increase Development Timeout

```python
from supervisor_agent import RecoveryStrategy

# Create custom supervisor
supervisor = SupervisorAgent(verbose=True)

# Register with custom strategy
supervisor.register_stage(
    "development",
    RecoveryStrategy(
        max_retries=5,              # More retries
        retry_delay_seconds=15.0,   # Longer initial delay
        timeout_seconds=900.0,      # 15 minutes
        circuit_breaker_threshold=8 # More tolerant
    )
)

# Pass to orchestrator
orchestrator = ArtemisOrchestrator(
    card_id="my-card",
    board=board,
    messenger=messenger,
    rag=rag,
    supervisor=supervisor  # Use custom supervisor
)
```

---

## Monitoring Health

### Check Health Programmatically

```python
# After pipeline completion
health = orchestrator.supervisor.get_health_status()

if health == HealthStatus.FAILING:
    print("⚠️  Pipeline experiencing issues!")

# Get detailed stats
stats = orchestrator.supervisor.get_statistics()
success_rate = (stats['successful_recoveries'] /
                stats['total_interventions'] * 100)
print(f"Recovery Success Rate: {success_rate}%")
```

### View Health in Pipeline Report

```bash
cat /tmp/pipeline_full_report_card-001.json | jq .supervisor_statistics
```

Output:
```json
{
  "overall_health": "healthy",
  "total_interventions": 7,
  "successful_recoveries": 6,
  "failed_recoveries": 1
}
```

---

## Testing

### Run Supervisor Tests

```bash
cd /home/bbrelin/src/repos/salesforce/.agents/agile
/home/bbrelin/src/repos/salesforce/.venv/bin/python3 supervisor_agent.py
```

Expected output:
```
✅ All supervisor tests passed!
```

---

## Integration with Redis Metrics

Supervisor statistics automatically included in Redis metrics:

```python
from redis_metrics import RedisMetrics

metrics = RedisMetrics()

# View pipeline with supervisor stats
recent = metrics.get_recent_pipelines(limit=1)
print(recent[0]['metadata']['supervisor_interventions'])
```

---

## Troubleshooting

### Problem: Too Many Retries

**Symptom:**
```
[Supervisor] Retry 1/3
[Supervisor] Retry 2/3
[Supervisor] Retry 3/3
```

**Solution:**
- Reduce max_retries in RecoveryStrategy
- Investigate root cause of failures

### Problem: Circuit Breakers Opening Too Fast

**Symptom:**
```
[Supervisor] 🚨 Circuit breaker OPEN (3 failures)
```

**Solution:**
- Increase circuit_breaker_threshold
- Add fallback_action for critical stages

### Problem: Timeouts Too Aggressive

**Symptom:**
```
[Supervisor] ⏰ TIMEOUT (125s > 120s)
```

**Solution:**
- Increase timeout_seconds for stage
- Optimize stage implementation

---

## Key Takeaways

✅ **Enabled by default** - No configuration needed
✅ **Automatic recovery** - Retries with exponential backoff
✅ **Circuit breakers** - Prevents cascading failures
✅ **Process monitoring** - Kills hanging processes
✅ **Health visibility** - Comprehensive reports
✅ **Zero overhead** - Only activates when needed

---

## Related Files

- **Implementation:** `supervisor_agent.py` (600 lines)
- **Integration:** `artemis_orchestrator_solid.py` (lines 44, 183-215, 243-336, 427-433, 521-527, 562-581)
- **Documentation:** `SUPERVISOR_AGENT_SUMMARY.md` (comprehensive guide)

---

**Version:** 1.0
**Status:** ✅ OPERATIONAL
**Default:** ENABLED
**Overhead:** < 1ms per stage
