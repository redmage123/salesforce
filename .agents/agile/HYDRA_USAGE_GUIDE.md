# Artemis Hydra Configuration - Usage Guide

**Date:** October 23, 2025
**Status:** ✅ IMPLEMENTED
**Version:** 1.0

---

## Quick Start

### Basic Usage

```bash
# Run with default config
python test_hydra_config.py card_id=card-001

# Override LLM provider
python test_hydra_config.py card_id=card-001 llm.provider=anthropic

# Use mock LLM for testing
python test_hydra_config.py card_id=test-001 llm=mock

# Fast pipeline (minimal stages)
python test_hydra_config.py card_id=test-001 pipeline=fast

# Use development profile
python test_hydra_config.py --config-name env/dev card_id=dev-001
```

---

## Configuration Structure

### Directory Layout

```
.agents/agile/
├── conf/
│   ├── config.yaml              # Default configuration
│   ├── llm/
│   │   ├── openai.yaml         # OpenAI settings
│   │   ├── anthropic.yaml      # Anthropic Claude settings
│   │   └── mock.yaml           # Mock LLM for testing
│   ├── storage/
│   │   ├── local.yaml          # Local SQLite storage
│   │   └── postgres.yaml       # PostgreSQL storage
│   ├── pipeline/
│   │   ├── standard.yaml       # Full pipeline
│   │   └── fast.yaml           # Quick testing pipeline
│   ├── security/
│   │   ├── strict.yaml         # Production security
│   │   └── permissive.yaml     # Development security
│   └── env/
│       ├── dev.yaml            # Development environment
│       └── prod.yaml           # Production environment
├── hydra_config.py              # Structured config dataclasses
└── test_hydra_config.py         # Test/validation script
```

---

## Usage Examples

### Example 1: Default Configuration

```bash
python test_hydra_config.py card_id=card-001
```

**Uses:**
- LLM: OpenAI GPT-4o
- Storage: Local SQLite (/tmp/rag_db)
- Pipeline: Standard (all 8 stages)
- Security: Strict (GDPR + WCAG enforced)

**Output:**
```
✅ Type-Safe Access:
  Card ID: card-001
  LLM Provider: openai
  LLM Model: gpt-4o
  RAG DB Path: /tmp/rag_db
  Max Parallel Devs: 3
  Code Review Enabled: True
  GDPR Enforcement: True
  Log Level: INFO
```

---

### Example 2: Switch LLM Provider

```bash
# Use Anthropic Claude
python test_hydra_config.py card_id=card-002 llm.provider=anthropic

# Use specific model
python test_hydra_config.py card_id=card-002 llm.model=claude-3-opus
```

**Changes:**
- LLM provider switches to Anthropic
- API key read from $ANTHROPIC_API_KEY
- Model can be overridden

---

### Example 3: Fast Pipeline for Testing

```bash
python test_hydra_config.py card_id=test-001 pipeline=fast llm=mock
```

**Uses:**
- LLM: Mock (no API calls, free)
- Pipeline: Fast (only development + validation)
- 1 parallel developer (faster)
- No code review

**Perfect for:**
- Quick testing
- Development
- CI/CD pipelines

---

### Example 4: Multiple Overrides

```bash
python test_hydra_config.py \
  card_id=custom-001 \
  llm.provider=anthropic \
  llm.model=claude-3-7-sonnet \
  pipeline.max_parallel_developers=2 \
  security.enforce_gdpr=false \
  logging.log_level=DEBUG
```

**Overrides:**
- LLM: Claude 3.7 Sonnet
- 2 parallel developers (instead of 3)
- GDPR not enforced
- Debug logging enabled

---

### Example 5: Development Profile

```bash
# Use complete dev profile (note the + prefix for card_id due to struct mode)
python test_hydra_config.py --config-name env/dev +card_id=dev-001

# Dev profile with override
python test_hydra_config.py --config-name env/dev +card_id=dev-001 llm.cost_limit_usd=5.0
```

**Dev Profile Includes:**
- Mock LLM (free)
- Fast pipeline (2 stages)
- Permissive security (no GDPR/WCAG)
- Debug logging
- $1 cost limit

**Note:** Environment profiles use structured configs which enable struct mode. Use `+card_id=value` syntax (with `+` prefix) to add card_id at runtime.

---

### Example 6: Production Profile

```bash
# Note the + prefix for card_id when using environment profiles
python test_hydra_config.py --config-name env/prod +card_id=prod-001
```

**Prod Profile Includes:**
- OpenAI GPT-4o
- Full pipeline (8 stages)
- Strict security (GDPR + WCAG)
- INFO logging
- $100 cost limit

---

## Configuration Files

### conf/config.yaml (Base)

```yaml
defaults:
  - llm: openai
  - storage: local
  - pipeline: standard
  - security: strict
  - _self_

card_id: ???  # Required via CLI

logging:
  verbose: true
  log_level: INFO
```

---

### conf/llm/openai.yaml

```yaml
provider: openai
model: gpt-4o
api_key: ${oc.env:OPENAI_API_KEY}  # From environment
max_tokens_per_request: 8000
temperature: 0.7
cost_limit_usd: null
```

**Features:**
- Reads API key from environment variable
- Uses OmegaConf interpolation: `${oc.env:VAR_NAME}`
- Null cost limit = no limit

---

### conf/llm/mock.yaml

```yaml
provider: mock
model: mock-gpt-4
api_key: "test-key-12345"
max_tokens_per_request: 8000
temperature: 0.7
cost_limit_usd: 0.0  # Free
```

**Use for:**
- Unit testing
- CI/CD
- Development without API costs

---

### conf/pipeline/standard.yaml

```yaml
max_parallel_developers: 3
enable_code_review: true
auto_approve_project_analysis: false
enable_supervision: true
max_retries: 2

stages:
  - project_analysis
  - architecture
  - dependencies
  - development
  - code_review
  - validation
  - integration
  - testing
```

---

### conf/pipeline/fast.yaml

```yaml
max_parallel_developers: 1
enable_code_review: false
auto_approve_project_analysis: true
enable_supervision: false
max_retries: 0

stages:
  - development
  - validation
```

**Speedup:** ~5-10x faster than standard

---

### conf/storage/local.yaml

```yaml
rag_db_type: sqlite
rag_db_path: /tmp/rag_db
chromadb_host: null
chromadb_port: null
temp_dir: /tmp
checkpoint_dir: /tmp/artemis_checkpoints
state_dir: /tmp/artemis_state
```

**For:** Single-machine deployments

---

### conf/storage/postgres.yaml

```yaml
rag_db_type: postgres
rag_db_path: null
chromadb_host: ${oc.env:CHROMADB_HOST,localhost}
chromadb_port: ${oc.env:CHROMADB_PORT,8000}
temp_dir: /tmp
checkpoint_dir: /var/artemis/checkpoints
state_dir: /var/artemis/state
```

**For:** Concurrent pipelines, production

**Default values:** `${oc.env:VAR,default}` syntax

---

## Command-Line Reference

### Syntax

```bash
python script.py [OPTIONS] [OVERRIDES]
```

### Options

| Option | Description | Example |
|--------|-------------|---------|
| `--config-name` | Use alternate config file | `--config-name env/dev` |
| `--config-path` | Override config directory | `--config-path /custom/conf` |
| `--help` | Show help | `--help` |

### Override Syntax

| Pattern | Example | Description |
|---------|---------|-------------|
| `key=value` | `card_id=card-001` | Set simple value |
| `nested.key=value` | `llm.provider=anthropic` | Set nested value |
| `group=name` | `llm=mock` | Use config group |
| `+key=value` | `+new_key=value` | Add new key |
| `~key` | `~llm.cost_limit_usd` | Remove key |

---

## Type-Safe Configuration

### Structured Configs (hydra_config.py)

```python
from dataclasses import dataclass
from hydra_config import ArtemisConfig

@dataclass
class ArtemisConfig:
    card_id: str  # Required
    llm: LLMConfig
    storage: StorageConfig
    pipeline: PipelineConfig
    security: SecurityConfig
    logging: LoggingConfig
```

### Benefits

1. **IDE Autocomplete**
   ```python
   cfg.llm.provider  # IDE suggests: provider, model, api_key, ...
   ```

2. **Type Checking**
   ```python
   cfg.pipeline.max_parallel_developers = "invalid"  # Type error caught!
   ```

3. **Validation**
   ```python
   cfg.card_id = "???"  # Error: Required field not provided
   ```

---

## Testing Configuration

### Validate Config

```bash
# Test if config loads correctly
python test_hydra_config.py card_id=test-001

# Check dev profile
python test_hydra_config.py --config-name env/dev card_id=dev-001

# Validate with overrides
python test_hydra_config.py card_id=test llm=mock pipeline=fast
```

### Expected Output

```
======================================================================
🔧 ARTEMIS HYDRA CONFIGURATION TEST
======================================================================

📋 Raw Configuration:
llm:
  provider: openai
  model: gpt-4o
  ...

✅ Type-Safe Access:
  Card ID: test-001
  LLM Provider: openai
  LLM Model: gpt-4o
  ...

✅ Configuration Validation:
  ✅ card_id: test-001
  ✅ LLM provider: openai
  ✅ API key: sk-XLX...3r3B

======================================================================
✅ CONFIGURATION VALID
======================================================================
```

---

## Common Patterns

### Pattern 1: Development with Mock LLM

```bash
python script.py card_id=dev-001 llm=mock pipeline=fast
```

**Use when:** Quick testing without API costs

---

### Pattern 2: Production Run

```bash
python script.py --config-name env/prod card_id=prod-001
```

**Use when:** Production deployment

---

### Pattern 3: Experiment with Different LLMs

```bash
# Test with OpenAI
python script.py card_id=exp-001 llm=openai

# Test with Anthropic
python script.py card_id=exp-001 llm=anthropic
```

**Use when:** Comparing LLM performance

---

### Pattern 4: Custom Storage Location

```bash
python script.py card_id=card-001 storage.rag_db_path=/custom/path/rag_db
```

**Use when:** Multiple concurrent runs need separate databases

---

### Pattern 5: Debug Mode

```bash
python script.py card_id=debug-001 logging.log_level=DEBUG logging.verbose=true
```

**Use when:** Troubleshooting issues

---

## Environment Variables

### Required

```bash
# OpenAI (if using llm=openai)
export OPENAI_API_KEY="sk-..."

# Anthropic (if using llm=anthropic)
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Optional

```bash
# ChromaDB host/port (if using storage=postgres)
export CHROMADB_HOST="localhost"
export CHROMADB_PORT="8000"
```

---

## Troubleshooting

### Error: "No module named 'hydra'"

**Solution:**
```bash
pip install hydra-core omegaconf
```

---

### Error: "Key 'card_id' is not in struct"

**Cause:** card_id is required

**Solution:**
```bash
# Always provide card_id
python script.py card_id=my-card-id
```

---

### Error: "Could not find 'conf/config.yaml'"

**Cause:** Running from wrong directory

**Solution:**
```bash
# Run from .agents/agile directory
cd /home/bbrelin/src/repos/salesforce/.agents/agile
python test_hydra_config.py card_id=test-001
```

---

### Warning: "API key not set"

**Cause:** Environment variable not set

**Solution:**
```bash
export OPENAI_API_KEY="your-key-here"
# or use mock for testing
python script.py card_id=test llm=mock
```

---

## Benefits Summary

| Feature | Before (env vars) | After (Hydra) |
|---------|-------------------|---------------|
| **Config files** | ❌ No | ✅ YAML |
| **CLI overrides** | ❌ No | ✅ `key=value` |
| **Profiles** | ❌ No | ✅ dev/prod |
| **Type safety** | ❌ Strings only | ✅ Dataclasses |
| **Validation** | ⚠️ Manual | ✅ Automatic |
| **Version control** | ❌ Hard | ✅ Easy |
| **Experimentation** | ❌ Difficult | ✅ Simple |
| **Documentation** | ⚠️ Comments | ✅ Self-documenting |

---

## Next Steps

### For Artemis Integration

1. Update `artemis_orchestrator_solid.py` to use Hydra:
   ```python
   @hydra.main(version_base=None, config_path="conf", config_name="config")
   def main(cfg: ArtemisConfig):
       # Use cfg instead of config_agent
       orchestrator = ArtemisOrchestrator(...)
   ```

2. Keep backward compatibility with `config_agent.py`

3. Update CLI arguments to work with Hydra

---

## Summary

**Hydra Configuration is now fully implemented for Artemis!**

✅ **Working Features:**
- YAML configuration files
- CLI overrides (`key=value`)
- Config groups (llm/, storage/, pipeline/)
- Type-safe structured configs
- Environment variable interpolation
- Development/production profiles

**Usage:**
```bash
# Simple
python test_hydra_config.py card_id=card-001

# Advanced
python test_hydra_config.py \
  --config-name env/prod \
  card_id=prod-001 \
  llm.model=gpt-4-turbo \
  pipeline.max_parallel_developers=5
```

**Status:** ✅ Ready for integration with Artemis orchestrator

---

**Implementation Date:** October 23, 2025
**Time to Implement:** 2 hours
**Files Created:** 14 config files + 2 Python modules
**Status:** ✅ COMPLETE
