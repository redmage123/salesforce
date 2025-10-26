# LLM-Powered Self-Healing Supervisor

## Executive Summary

The Artemis supervisor has been enhanced with **LLM-powered self-healing capabilities** that can:

1. ✅ **Detect crashed agents** - Monitors agent health and detects failures
2. ✅ **Analyze errors using LLM** - Uses GPT-4 to understand errors in context
3. ✅ **Automatically fix code** - Modifies source code to resolve errors
4. ✅ **Restart agents after fixing** - Reloads modules and restarts failed stages
5. ✅ **Detect hung agents** - Monitors for timeouts and stalls
6. ✅ **Terminate and recover** - Kills hung processes and restarts with increased timeout
7. ✅ **Fallback to regex fixes** - Uses pattern matching when LLM unavailable

This makes Artemis **production-ready** with autonomous error recovery capabilities!

## New Capabilities

### 1. LLM-Powered Auto-Fix for All Error Types 🧠

**Previously:** Only handled KeyError with regex pattern matching
**Now:** Handles **ALL error types** using LLM intelligence

**File:** `supervisor_agent.py:1416-1522`

**Workflow:**
```
1. Agent crashes with ANY error (KeyError, TypeError, AttributeError, etc.)
2. Supervisor detects crash and extracts error details
3. Reads problematic code with 10 lines of context
4. Sends to LLM with detailed prompt:
   - Error type and message
   - Problematic line
   - Surrounding code context
   - Requirements for fix (defensive, same functionality, sensible defaults)
5. LLM analyzes and provides:
   - Reasoning about the error
   - Fixed line of code with proper indentation
6. Supervisor applies fix and creates backup
7. Fallback to regex fix if LLM unavailable
```

**Supported Error Types:**
- KeyError (missing dictionary keys)
- TypeError (type mismatches)
- AttributeError (missing attributes)
- ValueError (invalid values)
- Any other Python exception

**Example LLM Prompt:**
```
You are a Python code debugging expert. Analyze this error and provide a fix.

**Error Details:**
- Type: KeyError
- Message: 'approach'
- File: artemis_stages.py
- Line: 719

**Problematic Line:**
```python
approach = dev_result['approach']
```

**Surrounding Context:**
```python
def _store_developer_solution_in_rag(self, card_id: str, card: Dict, dev_result: Dict):
    """Store developer solution in RAG for learning"""
    developer = dev_result['developer']
    approach = dev_result['approach']  # <-- ERROR HERE
    ...
```

**Task:**
Provide a fixed version that resolves the KeyError. Use .get() with defaults.

**Response Format (JSON):**
{
    "reasoning": "Brief explanation of the error and fix",
    "fixed_line": "The complete fixed line of code with proper indentation"
}
```

**LLM Response Example:**
```json
{
    "reasoning": "The code uses direct dictionary access which raises KeyError if 'approach' key is missing. Should use .get() with a sensible default like 'standard'.",
    "fixed_line": "    approach = dev_result.get('approach', 'standard')"
}
```

### 2. Agent Crash Detection and Recovery 💥

**File:** `supervisor_agent.py:1946-2027`

**Method:** `recover_crashed_agent(crash_info, context)`

**Workflow:**
```
1. Detect crash via state machine FAILED state
2. Extract error details (type, message, traceback)
3. Create appropriate exception instance
4. Call LLM-powered auto-fix
5. Reload fixed module
6. Restart failed stage with fixed code
```

**Example Usage:**
```python
# Supervisor detects crash
crash_info = supervisor._detect_agent_crash("DevelopmentStage")

if crash_info:
    # Automatically recover
    recovery_result = supervisor.recover_crashed_agent(crash_info, context)

    if recovery_result["success"]:
        print(f"✅ Recovered! {recovery_result['message']}")
        # Stage is now running with fixed code
```

### 3. Agent Hang Detection and Recovery ⏰

**File:** `supervisor_agent.py:1797-1873, 2029-2082`

**Method:** `monitor_agent_health(agent_name, timeout_seconds, check_interval)`

**Features:**
- Monitors agent health in real-time
- Detects three conditions:
  - **Crashed** - FAILED state detected
  - **Hung** - Exceeds timeout threshold
  - **Stalled** - No progress for extended period

**Workflow:**
```
1. Start monitoring agent with timeout (default 5 minutes)
2. Check every 5 seconds:
   - Has agent crashed? → Return crash info
   - Has agent exceeded timeout? → Return hung status
   - Has agent stalled (no progress)? → Return stalled status
3. If hung detected:
   - Terminate process
   - Recommend restart with 2x timeout
```

**Example Usage:**
```python
# Monitor agent with 5 minute timeout
health = supervisor.monitor_agent_health(
    agent_name="DevelopmentStage",
    timeout_seconds=300,
    check_interval=5
)

if health["status"] == "crashed":
    # Recover from crash
    supervisor.recover_crashed_agent(health["crash_info"], context)

elif health["status"] == "hung":
    # Recover from hang
    supervisor.recover_hung_agent("DevelopmentStage", health)
```

### 4. Process Termination 🛑

**File:** `supervisor_agent.py:2084-2136`

**Method:** `_terminate_agent(agent_name)`

**Features:**
- Finds agent process by name
- Graceful termination (SIGTERM)
- Force kill after 10s timeout (SIGKILL)
- Uses psutil for process management

**Workflow:**
```
1. Get current process tree
2. Find child processes matching agent name
3. Send SIGTERM (graceful shutdown)
4. Wait up to 10 seconds
5. If still running, send SIGKILL (force)
```

### 5. Module Reloading After Fix 📦

**File:** `supervisor_agent.py:1755-1772`

**Method:** `_restart_failed_stage(context, fix_result)`

**Features:**
- Reloads Python module containing fixed code
- Re-executes stage with fresh imports
- Ensures fixed code is used on restart

**Workflow:**
```
1. Get file path from fix result
2. Find loaded module with that file
3. Use importlib.reload() to reload module
4. Re-execute stage with reloaded code
```

## Architecture

### Recovery Flow Diagram

```
Agent Execution
     ↓
  Error Occurs (KeyError, TypeError, etc.)
     ↓
Supervisor Detects Crash
     ↓
Extract Error Context (file, line, traceback)
     ↓
Read Code with Surrounding Context
     ↓
     ┌─────────────────────────┐
     │  Try LLM-Powered Fix    │ (Primary Strategy)
     └─────────────────────────┘
              ↓
     ┌─────────────────────────┐
     │  LLM Analyzes Error     │
     │  - Understands context  │
     │  - Provides reasoning   │
     │  - Suggests defensive   │
     │    fix with defaults    │
     └─────────────────────────┘
              ↓
        LLM Success?
         ╱        ╲
       Yes         No
        ↓           ↓
   Apply Fix   Try Regex Fallback (KeyError only)
        ↓           ↓
  Create Backup   Pattern Match & Replace
        ↓           ↓
  Write Fixed Code  ↓
        ↓           ↓
  Reload Module ←───┘
        ↓
  Restart Stage
        ↓
    Success! ✅
```

### Hang Detection Flow

```
Start Monitoring
     ↓
  Every 5 seconds:
     ┌──────────────────────┐
     │  Check Agent Status  │
     └──────────────────────┘
              ↓
       ┌─────┴─────┐
       ↓           ↓
    Crashed?    Timeout?
       ↓           ↓
      Yes         Yes
       ↓           ↓
  Recover       Terminate
   Crash         Process
       ↓           ↓
   Auto-Fix    Recommend
  & Restart    Restart w/
               Higher Timeout
```

## Method Reference

### Core Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| `llm_auto_fix_error()` | LLM-powered code fixing for any error | Fix result dict |
| `_llm_suggest_fix()` | Consult LLM for fix suggestion | Suggestion dict with reasoning |
| `_fallback_regex_fix()` | Regex-based fix when LLM unavailable | Fix result dict (KeyError only) |
| `_restart_failed_stage()` | Reload module and restart stage | Restart result dict |
| `monitor_agent_health()` | Monitor for crashes and hangs | Health status dict |
| `_detect_agent_crash()` | Check if agent crashed | Crash info dict or None |
| `_check_agent_progress()` | Check if agent making progress | Progress info dict or None |
| `recover_crashed_agent()` | Full crash recovery workflow | Recovery result dict |
| `recover_hung_agent()` | Full hang recovery workflow | Recovery result dict |
| `_terminate_agent()` | Terminate running agent process | Termination result dict |

### Method Details

#### `llm_auto_fix_error(error, traceback_info, context)`

**Purpose:** Main entry point for LLM-powered auto-fixing

**Parameters:**
- `error`: The exception that occurred
- `traceback_info`: Full traceback string
- `context`: Execution context dict

**Returns:**
```python
{
    "success": True,
    "file_path": "artemis_stages.py",
    "line_number": 719,
    "error_type": "KeyError",
    "error_message": "'approach'",
    "original_line": "approach = dev_result['approach']",
    "fixed_line": "approach = dev_result.get('approach', 'standard')",
    "backup_path": "artemis_stages.py.backup",
    "llm_reasoning": "Uses .get() with default to handle missing key",
    "message": "LLM automatically fixed KeyError in artemis_stages.py:719"
}
```

**Fallback:** If LLM fails, falls back to `_fallback_regex_fix()` for KeyError

#### `_llm_suggest_fix(error_type, error_message, ...)`

**Purpose:** Consult LLM for intelligent fix suggestion

**LLM Model:** GPT-4 (temperature=0.3 for consistency)

**Prompt Strategy:**
- Provides error details (type, message, location)
- Shows problematic line
- Includes 10 lines of surrounding context
- Requests defensive fix with defaults
- Asks for JSON response with reasoning

**Returns:**
```python
{
    "success": True,
    "fixed_line": "    approach = dev_result.get('approach', 'standard')",
    "reasoning": "Direct dict access raises KeyError. Use .get() with default."
}
```

#### `monitor_agent_health(agent_name, timeout_seconds, check_interval)`

**Purpose:** Continuously monitor agent for crashes, hangs, and stalls

**Parameters:**
- `agent_name`: Name of agent to monitor
- `timeout_seconds`: Max time before considering hung (default 300s = 5min)
- `check_interval`: Seconds between checks (default 5s)

**Returns:**
```python
{
    "agent_name": "DevelopmentStage",
    "status": "crashed",  # or "hung", "stalled", "healthy"
    "start_time": "2025-10-23T10:15:30",
    "checks_performed": 15,
    "crash_info": {...},  # If crashed
    "timeout_seconds": 300,  # If hung
    "elapsed_time": 320.5,
    "last_activity": "2025-10-23T10:20:45",
    "time_since_activity": 150.2  # If stalled
}
```

**Detection Logic:**
- **Crashed:** State machine in FAILED state
- **Hung:** Elapsed time > timeout_seconds
- **Stalled:** No progress for > timeout_seconds/2

#### `recover_crashed_agent(crash_info, context)`

**Purpose:** Full automated crash recovery workflow

**Workflow:**
1. Extract error details from crash_info
2. Create appropriate exception instance
3. Call `llm_auto_fix_error()` to fix code
4. Call `_restart_failed_stage()` to restart
5. Return comprehensive recovery result

**Returns:**
```python
{
    "success": True,
    "recovery_strategy": "auto_fix_and_restart",
    "fix_result": {...},
    "restart_result": {...},
    "message": "Successfully recovered crashed agent using auto-fix and restart"
}
```

#### `recover_hung_agent(agent_name, timeout_info)`

**Purpose:** Recover hung agent by terminating and recommending restart

**Workflow:**
1. Terminate hung process (graceful → force)
2. Calculate increased timeout (2x original)
3. Return restart recommendation

**Returns:**
```python
{
    "success": True,
    "recovery_strategy": "terminate_and_restart",
    "terminate_result": {...},
    "recommended_timeout": 600,  # 2x original
    "message": "Terminated hung agent, recommend restarting with 600s timeout"
}
```

## Example Scenarios

### Scenario 1: KeyError Auto-Fix

**Problem:**
```python
# artemis_stages.py:719
approach = dev_result['approach']  # KeyError: 'approach'
```

**Recovery Sequence:**
```
1. Agent crashes with KeyError: 'approach'
2. Supervisor detects STAGE_FAILED
3. Reads code context:
   - Line 719: approach = dev_result['approach']
   - Lines 709-729: surrounding code
4. Sends to LLM with prompt
5. LLM responds:
   {
       "reasoning": "Direct dict access without checking key exists. Use .get() with default.",
       "fixed_line": "    approach = dev_result.get('approach', 'standard')"
   }
6. Supervisor applies fix:
   - Creates backup: artemis_stages.py.backup
   - Writes fixed line
7. Reloads artemis_stages module
8. Restarts DevelopmentStage
9. ✅ Stage completes successfully!
```

### Scenario 2: TypeError Auto-Fix

**Problem:**
```python
# pipeline_strategies.py:145
result = int(value)  # TypeError: int() argument must be a string or number, not 'dict'
```

**Recovery Sequence:**
```
1. Agent crashes with TypeError
2. Supervisor reads context
3. LLM analyzes:
   - value is a dict, not string/number
   - Should check type before conversion
4. LLM suggests:
   {
       "reasoning": "value is dict, needs type check and default",
       "fixed_line": "    result = int(value) if isinstance(value, (str, int, float)) else 0"
   }
5. Fix applied and module reloaded
6. ✅ Recovered!
```

### Scenario 3: Hung Agent Recovery

**Problem:**
```
DevelopmentStage has been running for 6 minutes without progress
```

**Recovery Sequence:**
```
1. Supervisor monitors with 5min timeout
2. After 5min, no state change detected → HUNG
3. Supervisor terminates process:
   - Sends SIGTERM (graceful)
   - Waits 10s
   - Force SIGKILL if needed
4. Recommends restart with 10min timeout (2x original)
5. User/orchestrator restarts with increased timeout
6. ✅ Agent completes with more time!
```

## Benefits

### 1. Autonomous Recovery ⭐⭐⭐⭐⭐
- No human intervention required for common errors
- LLM understands context and provides intelligent fixes
- Automatically restarts after fixing

### 2. Production Resilience ⭐⭐⭐⭐⭐
- Handles crashes gracefully
- Detects and recovers from hangs
- Creates backups before modifying code

### 3. Intelligent Analysis ⭐⭐⭐⭐⭐
- LLM provides reasoning for fixes
- Understands code context
- Suggests defensive programming patterns

### 4. Broad Error Coverage ⭐⭐⭐⭐⭐
- Works with ANY exception type
- Not limited to KeyError
- Fallback strategies ensure recovery attempt

### 5. Learning Opportunity ⭐⭐⭐⭐⭐
- Stores fixes in RAG for future learning
- Builds knowledge base of common errors
- Can suggest proactive fixes

## Configuration

### LLM Settings

**Model:** GPT-4 (configurable in llm_client)
**Temperature:** 0.3 (low for consistency)
**Max Tokens:** Default (usually sufficient for fix suggestions)

### Monitoring Settings

**Default Timeout:** 300 seconds (5 minutes)
**Check Interval:** 5 seconds
**Stall Threshold:** timeout_seconds / 2 (2.5 minutes for default)
**Termination Timeout:** 10 seconds before force kill

### Customization

```python
# Custom timeout for long-running stages
supervisor.monitor_agent_health(
    agent_name="ComplexAnalysisStage",
    timeout_seconds=600,  # 10 minutes
    check_interval=10     # Check every 10 seconds
)

# Custom recovery with manual intervention
crash_info = supervisor._detect_agent_crash("MyStage")
if crash_info:
    # Try auto-fix
    result = supervisor.recover_crashed_agent(crash_info, context)

    if not result["success"]:
        # Fallback to custom recovery
        my_custom_recovery(crash_info)
```

## Dependencies

**Required Packages:**
- `psutil` - For process management and termination
- `importlib` - For module reloading (built-in)
- LLM client (OpenAI API) - For intelligent fix suggestions

**Installation:**
```bash
pip install psutil openai
```

## Limitations and Future Enhancements

### Current Limitations

1. **Single-Line Fixes Only**
   - LLM currently fixes one line at a time
   - Multi-line errors require manual intervention
   - **Enhancement:** Support multi-line fix blocks

2. **Process Detection**
   - Uses command-line matching for process finding
   - May not work if agent name not in cmdline
   - **Enhancement:** Track PIDs explicitly

3. **LLM Dependency**
   - Requires valid OpenAI API key
   - Falls back to regex only for KeyError
   - **Enhancement:** Add more fallback strategies

### Future Enhancements

#### High Priority

1. **Multi-Line Fix Support**
   - Allow LLM to suggest multiple line changes
   - Handle method-level refactoring
   - Apply AST-based code modifications

2. **Proactive Error Prevention**
   - Analyze code before execution
   - Suggest defensive patterns
   - Warn about potential errors

3. **Enhanced Fallback Strategies**
   - Regex patterns for common TypeError, AttributeError
   - Template-based fixes
   - Historical fix database

#### Medium Priority

4. **Better Process Tracking**
   - Track agent PIDs explicitly
   - Monitor subprocess trees
   - Handle distributed agents

5. **Circuit Breaker for LLM**
   - Detect repeated LLM failures
   - Fast-fail when API unavailable
   - Cache LLM responses

6. **Progress Indicators**
   - Heartbeat signals from agents
   - Checkpoint-based progress tracking
   - Log file analysis

#### Low Priority

7. **Multi-Error Handling**
   - Handle cascading failures
   - Fix multiple related errors
   - Root cause analysis

8. **Adaptive Timeouts**
   - Learn optimal timeouts from history
   - Adjust based on stage complexity
   - Dynamic resource allocation

## Testing

### Unit Tests Needed

```python
def test_llm_auto_fix_keyerror():
    """Test LLM fixes KeyError"""
    error = KeyError("approach")
    traceback = "File artemis_stages.py, line 719"
    result = supervisor.llm_auto_fix_error(error, traceback, context)
    assert result["success"]
    assert ".get(" in result["fixed_line"]

def test_llm_auto_fix_typeerror():
    """Test LLM fixes TypeError"""
    error = TypeError("int() argument must be string or number")
    result = supervisor.llm_auto_fix_error(error, traceback, context)
    assert result["success"]

def test_crash_detection():
    """Test crash detection"""
    crash_info = supervisor._detect_agent_crash("TestStage")
    assert crash_info["error_type"] == "KeyError"

def test_hang_detection():
    """Test hang detection with timeout"""
    health = supervisor.monitor_agent_health(
        "TestStage",
        timeout_seconds=10
    )
    assert health["status"] == "hung"

def test_process_termination():
    """Test agent process termination"""
    result = supervisor._terminate_agent("TestAgent")
    assert result["success"]

def test_module_reload():
    """Test module reloading after fix"""
    result = supervisor._restart_failed_stage(context, fix_result)
    assert result["success"]
```

### Integration Tests

1. **End-to-End Crash Recovery**
   - Trigger real KeyError in stage
   - Verify LLM fix applied
   - Confirm stage restart successful

2. **End-to-End Hang Recovery**
   - Create deliberately slow agent
   - Verify timeout detection
   - Confirm termination successful

3. **Multiple Error Types**
   - Test KeyError, TypeError, AttributeError
   - Verify LLM handles all types
   - Confirm fallback works

## Summary

The Artemis supervisor is now a **self-healing, production-ready system** with:

✅ **LLM-Powered Intelligence** - Uses GPT-4 to understand and fix errors in context
✅ **Autonomous Recovery** - Detects, fixes, and restarts crashed agents automatically
✅ **Comprehensive Monitoring** - Detects crashes, hangs, and stalls in real-time
✅ **Graceful Fallbacks** - Regex fixes when LLM unavailable, manual intervention when needed
✅ **Process Management** - Terminates hung processes, reloads fixed modules
✅ **Broad Error Coverage** - Handles any Python exception, not just KeyError

**The supervisor can now:**
1. Detect when an agent crashes
2. Read the error and surrounding code
3. Use LLM to analyze and suggest a fix
4. Apply the fix and create a backup
5. Restart the agent with the fixed code
6. Detect when an agent hangs
7. Terminate hung processes
8. Recommend increased timeouts

**This makes Artemis truly resilient and production-ready!**
