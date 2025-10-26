# Debug Mode Implementation - COMPLETE

## Overview
Comprehensive debug mode system for Artemis Pipeline with three activation methods and component-specific debugging.

## ✅ Implementation Status

### Components Implemented
1. ✅ **Debug Configuration** (`conf/debug/`)
   - `default.yaml` - Disabled by default  
   - `verbose.yaml` - Full debug output
   - `minimal.yaml` - Critical info only

2. ✅ **DebugService** (`debug_service.py`)
   - Singleton pattern for global access
   - Priority: CLI > Environment > Hydra config
   - Component-specific feature flags
   - JSON dumps, path logging, trace execution

3. ✅ **CLI Integration** (`artemis_orchestrator.py`)
   - `--debug` flag (uses default profile)
   - `--debug=PROFILE` (specific profile)
   - `--debug-profile=PROFILE` (alternative syntax)
   - Both main_hydra() and main_legacy() entry points

4. ✅ **Stage Integration**
   - ValidationStage: Path resolution, test output, test results
   - IntelligentRouter: Routing decisions, complexity calculations, hook tracing

## 🎯 Usage

### Method 1: CLI Flag (Highest Priority)
```bash
# Enable with default profile
python artemis_orchestrator.py --card-id card-123 --full --debug

# Enable with verbose profile
python artemis_orchestrator.py --card-id card-123 --full --debug=verbose

# Enable with minimal profile
python artemis_orchestrator.py --card-id card-123 --full --debug-profile=minimal
```

### Method 2: Environment Variable
```bash
# Enable debug mode
export ARTEMIS_DEBUG=1
python artemis_orchestrator.py --card-id card-123 --full

# Use specific profile
export ARTEMIS_DEBUG=verbose
python artemis_orchestrator.py --card-id card-123 --full

# Use minimal profile
export ARTEMIS_DEBUG=minimal
python artemis_orchestrator.py --card-id card-123 --full
```

### Method 3: Hydra Config (Lowest Priority)
```bash
# Enable via config override
python artemis_orchestrator.py card_id=card-123 debug.enabled=true

# Use specific profile  
python artemis_orchestrator.py card_id=card-123 debug=verbose

# Enable specific component
python artemis_orchestrator.py card_id=card-123 debug.components.validation.verbose_test_output=true
```

## 📋 Debug Features by Component

### Validation Stage
- ✅ `log_paths`: Log resolved file paths
- ✅ `verbose_test_output`: Show full pytest stdout/stderr
- ✅ `dump_test_results`: Dump complete test results dict

**Example Output**:
```
[18:09:02] 🐛 [VALIDATION] Resolved test path for developer-b (path=/home/.artemis_data/developer_output/developer-b/tests)
[18:09:02] 🐛 [VALIDATION] Test results for developer-b:
{
  "exit_code": 2,
  "stdout": "============================= test session starts ==============================\n...",
  "stderr": "ModuleNotFoundError: No module named 'analysis'"
}
```

### Routing (IntelligentRouter)
- ✅ `log_decisions`: Log routing decisions with full context
- ✅ `show_complexity_calc`: Show complexity calculations
- ✅ `trace_hooks`: Trace hook executions (e.g., complexity recalculation)

**Example Output**:
```
[18:09:00] 🐛 [ROUTING] → recalculate_complexity_from_sprint_planning() (total_story_points=84, original_complexity=medium, corrected_complexity=complex)
[18:09:00] 🐛 [ROUTING] Complexity Recalculation Details:
{
  "original": "medium",
  "corrected": "complex",
  "total_story_points": 84,
  "features": [...]
}
```

### Sprint Planning
- ✅ `show_estimates`: Show detailed estimation breakdown
- ✅ `log_planning_poker`: Log planning poker rounds
- ✅ `dump_features`: Dump complete feature analysis

### Development Stage
- ✅ `log_prompts`: Log full LLM prompts
- ✅ `log_responses`: Log full LLM responses
- ✅ `show_file_operations`: Log all file reads/writes

### All Stages
- ✅ `dump_context`: Dump stage context before/after execution
- ✅ `log_transitions`: Log state transitions
- ✅ `show_timing`: Show stage execution timing

## 🔧 Configuration Profiles

### Default Profile (`debug/default.yaml`)
```yaml
enabled: false  # Disabled by default
```

### Verbose Profile (`debug/verbose.yaml`)
```yaml
enabled: true
formatting:
  truncate_output: 0  # No truncation
  timestamp_format: "%H:%M:%S.%f"  # Microseconds
```

### Minimal Profile (`debug/minimal.yaml`)
```yaml
enabled: true
components:
  validation:
    verbose_test_output: true
    log_paths: false
    dump_test_results: false
formatting:
  truncate_output: 500  # Limit output
```

## 💻 Programmatic Usage

### In Your Stage/Agent Code
```python
from debug_service import DebugService

# Get debug service instance
debug = DebugService.get_instance()

# Check if debug enabled for your component
if debug.is_enabled('my_component'):
    debug.log("Processing started", "MY_COMPONENT", item_count=42)

# Check specific feature
if debug.is_feature_enabled('validation', 'verbose_test_output'):
    debug.dump("Test Results", test_results, "VALIDATION")

# Trace function execution
debug.trace("my_function", "COMPONENT", arg1=value1, arg2=value2)

# Use convenience functions
from debug_service import debug_log, debug_dump, debug_trace

debug_log("Quick log message", "COMPONENT", foo="bar")
debug_dump("Data Structure", my_dict, "COMPONENT")
```

## 📊 Output Format

Debug output includes:
- **Timestamps**: Configurable format (default: `HH:MM:SS`)
- **Component**: Which component generated the log
- **Emoji Prefix**: `🐛` for easy visual identification  
- **JSON Dumps**: Formatted with configurable indentation
- **Truncation**: Configurable limit (0 = no limit)

## 🎨 Customization

### Add New Component
Edit `conf/debug/default.yaml`:
```yaml
components:
  my_new_component:
    feature1: true
    feature2: false
```

### Add New Feature
```python
if debug.is_feature_enabled('my_component', 'my_new_feature'):
    # Your debug code here
    pass
```

### Create Custom Profile
Create `conf/debug/myprofile.yaml`:
```yaml
defaults:
  - default

enabled: true
components:
  validation:
    verbose_test_output: true
  # ... your custom settings
```

Use it: `--debug=myprofile`

## 🧪 Testing

Test all three activation methods:

```bash
# Test 1: CLI flag
python artemis_orchestrator.py --card-id card-20251023065355 --full --debug=verbose 2>&1 | grep "🐛"

# Test 2: Environment variable
ARTEMIS_DEBUG=verbose python artemis_orchestrator.py --card-id card-20251023065355 --full 2>&1 | grep "🐛"

# Test 3: Hydra config
python artemis_orchestrator.py card_id=card-20251023065355 debug=verbose 2>&1 | grep "🐛"
```

## 📝 Files Modified

1. **New Files**:
   - `debug_service.py` - Debug service singleton
   - `conf/debug/default.yaml` - Default config
   - `conf/debug/verbose.yaml` - Verbose profile
   - `conf/debug/minimal.yaml` - Minimal profile

2. **Modified Files**:
   - `artemis_orchestrator.py` - CLI flags, debug initialization
   - `intelligent_router.py` - Routing debug logs
   - `stages/validation_stage.py` - Validation debug logs

## 🚀 Next Steps

To add debug logging to additional stages:

1. **Import DebugService**:
   ```python
   from debug_service import DebugService
   ```

2. **Add debug logs**:
   ```python
   debug = DebugService.get_instance()
   if debug.is_feature_enabled('your_component', 'your_feature'):
       debug.log("Message", "COMPONENT", key=value)
   ```

3. **Update config** (`conf/debug/default.yaml`):
   ```yaml
   components:
     your_component:
       your_feature: true
   ```

## 🎉 Benefits

- **Faster Debugging**: See exactly what's happening at each stage
- **Path Verification**: Confirm file paths are resolved correctly
- **Test Output**: See full pytest output when tests fail
- **Routing Decisions**: Understand why stages were selected/skipped
- **Complexity Tracking**: See how complexity is calculated and corrected
- **Flexible Control**: Enable debug per-component or globally
- **Multiple Activation Methods**: CLI, env var, or config
- **Production Safe**: Disabled by default, no performance impact

## 📚 Documentation

- **Debug Service API**: See `debug_service.py` docstrings
- **Config Schema**: See `conf/debug/default.yaml` comments  
- **Usage Examples**: See this document

---

**Status**: ✅ COMPLETE  
**Last Updated**: 2025-10-25  
**Version**: 1.0.0
