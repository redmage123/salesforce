# Artemis Hydra Configuration Migration Plan

**Date:** October 23, 2025
**Goal:** Refactor Artemis to use Hydra for configuration management
**Status:** Planning Phase

---

## Executive Summary

### What is Hydra?

**Hydra** is an open-source Python framework by Meta (Facebook AI Research) that provides:
- **Hierarchical configuration** - Compose configs from multiple sources
- **Command-line overrides** - Override any parameter via CLI
- **Config groups** - Organize configs by category (llm, storage, pipeline)
- **Multi-run** - Run experiments with different configs
- **Type safety** - Structured configs with dataclasses
- **Dynamic composition** - Mix and match config pieces

### Why Migrate to Hydra?

**Current problems with config_agent.py:**
- ❌ Environment variable-only configuration (not flexible)
- ❌ No config file support (must set 15+ env vars)
- ❌ No config profiles (dev/staging/prod)
- ❌ Hard to experiment with different settings
- ❌ No config history/versioning
- ❌ Verbose validation code (180 lines)

**Benefits of Hydra:**
- ✅ YAML config files (readable, versionable)
- ✅ Config composition (base + overrides)
- ✅ Command-line overrides (`--config llm.provider=anthropic`)
- ✅ Type-safe configs (Pydantic/dataclass integration)
- ✅ Built-in validation
- ✅ Multi-run experiments (`--multirun llm.provider=openai,anthropic`)

---

## Current vs Hydra Architecture

### Current: Environment Variables

```bash
# Must set all these environment variables
export ARTEMIS_LLM_PROVIDER="openai"
export OPENAI_API_KEY="sk-..."
export ARTEMIS_RAG_DB_PATH="/tmp/rag_db"
export ARTEMIS_MAX_PARALLEL_DEVELOPERS="3"
export ARTEMIS_ENABLE_CODE_REVIEW="true"
# ... 10 more env vars ...

# Run Artemis
python artemis_orchestrator_solid.py --card-id card-001 --full
```

**Problems:**
- Must remember all variable names
- No defaults visible
- Can't version control
- Hard to share configs

---

### With Hydra: YAML + CLI

```yaml
# conf/config.yaml
llm:
  provider: openai
  model: gpt-4o
  api_keys:
    openai: ${env:OPENAI_API_KEY}

storage:
  rag_db_path: /tmp/rag_db
  temp_dir: /tmp

pipeline:
  max_parallel_developers: 3
  enable_code_review: true
  auto_approve_project_analysis: false

security:
  enforce_gdpr: true
  enforce_wcag: true
```

```bash
# Run with defaults
python artemis_orchestrator_solid.py --card-id card-001 --full

# Override specific values
python artemis_orchestrator_solid.py --card-id card-001 --full llm.provider=anthropic

# Use different config profile
python artemis_orchestrator_solid.py --card-id card-001 --full --config-name prod

# Multi-run experiment
python artemis_orchestrator_solid.py --multirun llm.model=gpt-4o,claude-3-opus
```

**Benefits:**
- Config visible and versionable
- Easy overrides
- Multiple profiles (dev/prod)
- Experiment-friendly

---

## Proposed Hydra Structure

### Directory Layout

```
.agents/agile/
├── conf/                          # Hydra config directory
│   ├── config.yaml               # Default config
│   ├── llm/                      # LLM provider configs
│   │   ├── openai.yaml
│   │   ├── anthropic.yaml
│   │   └── mock.yaml (for testing)
│   ├── storage/                  # Storage configs
│   │   ├── local.yaml
│   │   └── postgres.yaml
│   ├── pipeline/                 # Pipeline configs
│   │   ├── standard.yaml
│   │   ├── fast.yaml (minimal stages)
│   │   └── comprehensive.yaml (all stages)
│   ├── security/                 # Security configs
│   │   ├── strict.yaml
│   │   └── permissive.yaml
│   └── env/                      # Environment profiles
│       ├── dev.yaml
│       ├── staging.yaml
│       └── prod.yaml
│
├── hydra_config.py               # Hydra structured configs
├── config_agent.py               # Keep for backward compat
└── artemis_orchestrator_solid.py # Updated to use Hydra
```

---

## Hydra Config Files

### conf/config.yaml (Base Config)

```yaml
defaults:
  - llm: openai
  - storage: local
  - pipeline: standard
  - security: strict
  - _self_

# Hydra runtime config
hydra:
  run:
    dir: /tmp/artemis_runs/${now:%Y-%m-%d}/${now:%H-%M-%S}
  sweep:
    dir: /tmp/artemis_multirun/${now:%Y-%m-%d}/${now:%H-%M-%S}
  job:
    name: artemis_${card_id}
```

### conf/llm/openai.yaml

```yaml
provider: openai
model: gpt-4o
api_key: ${env:OPENAI_API_KEY}
max_tokens_per_request: 8000
temperature: 0.7
cost_limit_usd: null  # No limit
```

### conf/llm/anthropic.yaml

```yaml
provider: anthropic
model: claude-3-7-sonnet-20250219
api_key: ${env:ANTHROPIC_API_KEY}
max_tokens_per_request: 8000
temperature: 0.7
cost_limit_usd: null
```

### conf/llm/mock.yaml

```yaml
provider: mock
model: mock-gpt-4
api_key: "test-key"
max_tokens_per_request: 8000
temperature: 0.7
cost_limit_usd: 0.0  # Free for testing
```

### conf/storage/local.yaml

```yaml
rag_db_path: /tmp/rag_db
temp_dir: /tmp
checkpoint_dir: /tmp/artemis_checkpoints
state_dir: /tmp/artemis_state
```

### conf/storage/postgres.yaml

```yaml
rag_db_type: postgres
rag_db_url: postgresql://localhost:5432/artemis_rag
chromadb_host: localhost
chromadb_port: 8000
temp_dir: /tmp
checkpoint_dir: /var/artemis/checkpoints
state_dir: /var/artemis/state
```

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

### conf/security/strict.yaml

```yaml
enforce_gdpr: true
enforce_wcag: true
require_security_review: true
min_code_review_score: 80
```

### conf/security/permissive.yaml

```yaml
enforce_gdpr: false
enforce_wcag: false
require_security_review: false
min_code_review_score: 60
```

### conf/env/dev.yaml

```yaml
defaults:
  - /llm: mock
  - /pipeline: fast
  - /security: permissive

llm:
  cost_limit_usd: 1.0

logging:
  verbose: true
  log_level: DEBUG
```

### conf/env/prod.yaml

```yaml
defaults:
  - /llm: openai
  - /pipeline: standard
  - /security: strict

llm:
  cost_limit_usd: 100.0

logging:
  verbose: false
  log_level: INFO
```

---

## Structured Configs (Type-Safe)

### hydra_config.py

```python
from dataclasses import dataclass, field
from typing import List, Optional
from hydra.core.config_store import ConfigStore


@dataclass
class LLMConfig:
    """LLM provider configuration"""
    provider: str = "openai"
    model: Optional[str] = None
    api_key: Optional[str] = None
    max_tokens_per_request: int = 8000
    temperature: float = 0.7
    cost_limit_usd: Optional[float] = None


@dataclass
class StorageConfig:
    """Storage configuration"""
    rag_db_path: str = "/tmp/rag_db"
    rag_db_type: str = "sqlite"  # sqlite or postgres
    rag_db_url: Optional[str] = None
    chromadb_host: Optional[str] = None
    chromadb_port: Optional[int] = None
    temp_dir: str = "/tmp"
    checkpoint_dir: str = "/tmp/artemis_checkpoints"
    state_dir: str = "/tmp/artemis_state"


@dataclass
class PipelineConfig:
    """Pipeline execution configuration"""
    max_parallel_developers: int = 3
    enable_code_review: bool = True
    auto_approve_project_analysis: bool = False
    enable_supervision: bool = True
    max_retries: int = 2
    stages: List[str] = field(default_factory=lambda: [
        "project_analysis",
        "architecture",
        "dependencies",
        "development",
        "code_review",
        "validation",
        "integration",
        "testing"
    ])


@dataclass
class SecurityConfig:
    """Security and compliance configuration"""
    enforce_gdpr: bool = True
    enforce_wcag: bool = True
    require_security_review: bool = True
    min_code_review_score: int = 80


@dataclass
class LoggingConfig:
    """Logging configuration"""
    verbose: bool = True
    log_level: str = "INFO"


@dataclass
class ArtemisConfig:
    """Complete Artemis configuration"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


# Register configs with Hydra
cs = ConfigStore.instance()
cs.store(name="artemis_config", node=ArtemisConfig)
cs.store(group="llm", name="openai", node=LLMConfig(provider="openai"))
cs.store(group="llm", name="anthropic", node=LLMConfig(provider="anthropic"))
cs.store(group="llm", name="mock", node=LLMConfig(provider="mock", api_key="test-key"))
```

---

## Migration Strategy

### Phase 1: Install Hydra (5 minutes)

```bash
cd /home/bbrelin/src/repos/salesforce/.agents/agile
source ../../.venv/bin/activate
pip install hydra-core
```

### Phase 2: Create Config Structure (30 minutes)

1. Create `conf/` directory
2. Create base `config.yaml`
3. Create config groups (llm/, storage/, pipeline/, security/, env/)
4. Create structured configs in `hydra_config.py`

### Phase 3: Update Orchestrator (1 hour)

**Before:**
```python
# artemis_orchestrator_solid.py
config = get_config(verbose=True)
provider = config.get('ARTEMIS_LLM_PROVIDER', 'openai')
```

**After:**
```python
# artemis_orchestrator_solid.py
import hydra
from hydra_config import ArtemisConfig

@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: ArtemisConfig):
    provider = cfg.llm.provider
    rag_path = cfg.storage.rag_db_path

    orchestrator = ArtemisOrchestrator(
        card_id=cfg.card_id,
        board=board,
        messenger=messenger,
        rag=RAGAgent(db_path=cfg.storage.rag_db_path),
        config=cfg  # Pass Hydra config instead
    )
```

### Phase 4: Backward Compatibility (30 minutes)

Keep `config_agent.py` for scripts that don't use Hydra yet:

```python
# config_agent.py - Updated to work with Hydra
class ConfigurationAgent:
    def __init__(self, hydra_config: Optional[ArtemisConfig] = None):
        if hydra_config:
            # Use Hydra config
            self.config = self._hydra_to_dict(hydra_config)
        else:
            # Fall back to environment variables
            self.config = self._load_from_env()
```

### Phase 5: Testing (1 hour)

1. Test with default config
2. Test with CLI overrides
3. Test with different profiles (dev/prod)
4. Test backward compatibility
5. Test multirun

### Phase 6: Documentation (30 minutes)

Update README and docs to explain Hydra usage

---

## Usage Examples

### Example 1: Run with Defaults

```bash
python artemis_orchestrator_solid.py card_id=card-001
```

Uses `conf/config.yaml` defaults.

### Example 2: Override LLM Provider

```bash
python artemis_orchestrator_solid.py \
  card_id=card-001 \
  llm.provider=anthropic
```

### Example 3: Use Production Config

```bash
python artemis_orchestrator_solid.py \
  card_id=card-001 \
  --config-name env/prod
```

### Example 4: Fast Pipeline for Testing

```bash
python artemis_orchestrator_solid.py \
  card_id=test-001 \
  pipeline=fast \
  llm=mock
```

### Example 5: Multi-Run Experiment

```bash
# Test with different LLM providers
python artemis_orchestrator_solid.py \
  --multirun \
  card_id=experiment-001 \
  llm=openai,anthropic

# Runs twice:
# 1. With llm=openai
# 2. With llm=anthropic
```

### Example 6: Custom RAG Path

```bash
python artemis_orchestrator_solid.py \
  card_id=card-001 \
  storage.rag_db_path=/custom/path/rag_db
```

---

## Benefits Summary

| Feature | Current (config_agent.py) | With Hydra |
|---------|--------------------------|------------|
| **Config files** | ❌ No | ✅ YAML |
| **CLI overrides** | ❌ No | ✅ Yes |
| **Config profiles** | ❌ No | ✅ dev/staging/prod |
| **Type safety** | ❌ No | ✅ Dataclasses |
| **Validation** | ⚠️ Manual (180 lines) | ✅ Automatic |
| **Composition** | ❌ No | ✅ Mix & match |
| **Multi-run** | ❌ No | ✅ Built-in |
| **Config history** | ❌ No | ✅ Git + Hydra logs |
| **IDE autocomplete** | ❌ Strings only | ✅ Type hints |
| **Experimentation** | ❌ Hard | ✅ Easy |

---

## Risks and Mitigation

### Risk 1: Breaking Changes

**Risk:** Existing scripts break
**Mitigation:** Keep `config_agent.py` for backward compatibility

### Risk 2: Learning Curve

**Risk:** Team needs to learn Hydra
**Mitigation:** Provide examples and documentation

### Risk 3: Overcomplication

**Risk:** Hydra adds unnecessary complexity
**Mitigation:** Start simple, add features incrementally

---

## Recommendation

**Should we migrate to Hydra?**

**For a production AI pipeline like Artemis: YES!** ✅

**Why:**
1. **Experimentation** - Easy to try different LLMs, parameters
2. **Reproducibility** - Config files version controlled
3. **Flexibility** - Quick config changes via CLI
4. **Type safety** - Catch config errors before runtime
5. **Standard** - Industry standard for ML/AI projects

**When:**
- Phase 1-2: Now (5-30 min) - Create config structure
- Phase 3-4: Next session (1-1.5 hours) - Migrate orchestrator
- Phase 5-6: Testing and docs (1.5 hours)

**Total time:** 3-4 hours for complete migration

**ROI:** High - Makes Artemis more flexible and experiment-friendly

---

## Implementation Plan

### Immediate (Do Now)
- [ ] Install hydra-core (`pip install hydra-core`)
- [ ] Create `conf/` directory structure
- [ ] Create base `config.yaml`

### Short-term (Next Session)
- [ ] Create `hydra_config.py` with structured configs
- [ ] Update `artemis_orchestrator_solid.py` to use Hydra decorator
- [ ] Create config groups (llm/, storage/, pipeline/)

### Medium-term (This Week)
- [ ] Test all config combinations
- [ ] Update documentation
- [ ] Create dev/staging/prod profiles

### Long-term (Future)
- [ ] Add config validation rules
- [ ] Add multirun for experiments
- [ ] Integrate with MLflow/W&B for tracking

---

**TL;DR:** Hydra makes Artemis configuration more flexible, versionable, and experiment-friendly. Highly recommended for a production AI pipeline. Implementation is ~3-4 hours with high ROI.
