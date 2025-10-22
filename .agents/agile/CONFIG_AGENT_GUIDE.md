# Configuration Agent - Complete Guide

## Overview

The **Configuration Agent** provides centralized environment configuration management for the Artemis pipeline. It reads, validates, and manages all environment variables, especially API keys for LLM providers.

## Features

✅ **Centralized Configuration** - Single source of truth for all pipeline settings
✅ **Environment Variable Reading** - Automatic loading from OS environment
✅ **Validation** - Checks required keys are present and valid
✅ **Default Values** - Provides sensible defaults for optional settings
✅ **Sensitive Data Masking** - Protects API keys in logs and reports
✅ **Configuration Reports** - Comprehensive summary of current settings
✅ **SOLID Compliant** - Single Responsibility, Dependency Inversion

## Quick Start

### 1. Set Environment Variables

```bash
# Required: Set your LLM provider API key
export OPENAI_API_KEY="sk-your-actual-openai-api-key"
# OR
export ANTHROPIC_API_KEY="sk-ant-your-actual-anthropic-key"

# Optional: Choose provider (default: openai)
export ARTEMIS_LLM_PROVIDER="openai"

# Optional: Specify model (default: provider-specific)
export ARTEMIS_LLM_MODEL="gpt-4o"
```

### 2. View Configuration Report

```bash
cd .agents/agile
python3 artemis_orchestrator_solid.py --card-id any --config-report
```

### 3. Run Pipeline (with automatic validation)

```bash
python3 artemis_orchestrator_solid.py --card-id card-123 --full
```

## Configuration Schema

### LLM Provider Configuration

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `ARTEMIS_LLM_PROVIDER` | `openai` | No | Primary LLM provider (openai/anthropic) |
| `ARTEMIS_LLM_MODEL` | Provider-specific | No | Specific LLM model to use |
| `OPENAI_API_KEY` | None | If provider=openai | OpenAI API key |
| `ANTHROPIC_API_KEY` | None | If provider=anthropic | Anthropic API key |

**Supported Models:**
- **OpenAI**: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`
- **Anthropic**: `claude-sonnet-4-5-20250929`, `claude-3-5-sonnet-20241022`

### Database and Storage

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `ARTEMIS_RAG_DB_PATH` | `/tmp/rag_db` | No | Path to RAG database (ChromaDB) |
| `ARTEMIS_TEMP_DIR` | `/tmp` | No | Temporary directory for pipeline artifacts |

### Pipeline Configuration

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `ARTEMIS_MAX_PARALLEL_DEVELOPERS` | `3` | No | Maximum number of parallel developers |
| `ARTEMIS_ENABLE_CODE_REVIEW` | `true` | No | Enable code review stage (true/false) |
| `ARTEMIS_AUTO_APPROVE_PROJECT_ANALYSIS` | `false` | No | Auto-approve project analysis suggestions |

### Logging and Monitoring

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `ARTEMIS_VERBOSE` | `true` | No | Enable verbose logging (true/false) |
| `ARTEMIS_LOG_LEVEL` | `INFO` | No | Log level (DEBUG/INFO/WARNING/ERROR) |

### Security and Compliance

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `ARTEMIS_ENFORCE_GDPR` | `true` | No | Enforce GDPR compliance checks |
| `ARTEMIS_ENFORCE_WCAG` | `true` | No | Enforce WCAG accessibility checks |

### Cost Controls

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `ARTEMIS_MAX_TOKENS_PER_REQUEST` | `8000` | No | Maximum tokens per LLM request |
| `ARTEMIS_COST_LIMIT_USD` | None | No | Maximum cost limit in USD (optional) |

## Usage Examples

### Standalone Configuration Report

```bash
# Show full configuration
python3 config_agent.py --report

# Validate configuration
python3 config_agent.py --validate

# Export as JSON
python3 config_agent.py --export
```

### Programmatic Usage

```python
from config_agent import ConfigurationAgent, get_config

# Get singleton instance
config = get_config(verbose=True)

# Get configuration value
provider = config.get('ARTEMIS_LLM_PROVIDER', 'openai')
api_key = config.get('OPENAI_API_KEY')

# Get masked value (for logging)
print(f"API Key: {config.get_masked('OPENAI_API_KEY')}")
# Output: "API Key: sk-XYZ...ABC"

# Validate configuration
validation = config.validate_configuration(require_llm_key=True)
if not validation.is_valid:
    print(f"Missing: {validation.missing_keys}")
    print(f"Invalid: {validation.invalid_keys}")

# Print comprehensive report
config.print_configuration_report()
```

### Integration with Orchestrator

The configuration agent is automatically integrated into the orchestrator:

```python
# Orchestrator automatically validates config on startup
orchestrator = ArtemisOrchestrator(
    card_id="card-123",
    board=board,
    messenger=messenger,
    rag=rag,
    config=config  # Optional: auto-loaded if not provided
)
```

**Validation happens automatically:**
1. Orchestrator checks for required API keys
2. Validates provider-specific configuration
3. Raises `ValueError` if configuration is invalid
4. Provides helpful error messages with instructions

## Configuration Validation

### Validation Results

```python
@dataclass
class ConfigValidationResult:
    is_valid: bool                   # True if all checks pass
    missing_keys: List[str]          # Required keys not found
    invalid_keys: List[str]          # Keys with invalid values
    warnings: List[str]              # Non-blocking warnings
    config_summary: Dict[str, Any]   # Summary of current config
```

### Validation Rules

1. **Provider-Specific API Keys**
   - If `ARTEMIS_LLM_PROVIDER=openai`, requires `OPENAI_API_KEY`
   - If `ARTEMIS_LLM_PROVIDER=anthropic`, requires `ANTHROPIC_API_KEY`

2. **Valid Values**
   - `ARTEMIS_LLM_PROVIDER` must be `openai` or `anthropic`
   - `ARTEMIS_LOG_LEVEL` must be `DEBUG`, `INFO`, `WARNING`, or `ERROR`

3. **Cost Limits**
   - If `ARTEMIS_COST_LIMIT_USD` is set, must be numeric
   - Warning if limit is below $1.00

### Example Validation Error

```bash
$ python3 artemis_orchestrator_solid.py --card-id card-123 --full

================================================================================
❌ CONFIGURATION ERROR
================================================================================

The pipeline cannot run due to invalid configuration.

Missing Required Keys:
  ❌ OPENAI_API_KEY
     Description: OpenAI API key

💡 Set your OpenAI API key:
   export OPENAI_API_KEY='your-key-here'

================================================================================

💡 Run with --config-report to see full configuration
💡 Run with --skip-validation to bypass (NOT RECOMMENDED)
```

## Sensitive Data Masking

API keys and other sensitive values are automatically masked in:
- Configuration reports
- Log messages
- Exported JSON

**Masking Strategy:**
- Shows first 6 characters: `sk-XYZ...`
- Shows last 4 characters: `...ABC`
- Total: `sk-XYZ...ABC`

**Example:**
```python
# Actual value: sk-proj-1234567890abcdefghijklmnopqrstuvwxyz
# Masked value: sk-pro...wxyz
```

## Common Scenarios

### Scenario 1: Multiple Developers with Different API Keys

```bash
# Developer A uses OpenAI
export OPENAI_API_KEY="sk-dev-a-key"

# Developer B uses Anthropic
export ARTEMIS_LLM_PROVIDER="anthropic"
export ANTHROPIC_API_KEY="sk-ant-dev-b-key"
```

### Scenario 2: Testing Without Real API Calls

```python
from config_agent import ConfigurationAgent

config = ConfigurationAgent(verbose=True)
config.set_defaults_for_testing()
# Sets provider to 'mock', disables code review, uses test DB
```

### Scenario 3: Production Environment

```bash
# .env file for production
export ARTEMIS_LLM_PROVIDER="openai"
export OPENAI_API_KEY="sk-prod-key"
export ARTEMIS_LLM_MODEL="gpt-4o"
export ARTEMIS_RAG_DB_PATH="/var/lib/artemis/rag_db"
export ARTEMIS_COST_LIMIT_USD="50.00"
export ARTEMIS_AUTO_APPROVE_PROJECT_ANALYSIS="true"
export ARTEMIS_ENABLE_CODE_REVIEW="true"
export ARTEMIS_ENFORCE_GDPR="true"
export ARTEMIS_ENFORCE_WCAG="true"
```

### Scenario 4: CI/CD Pipeline

```yaml
# .github/workflows/artemis.yml
env:
  ARTEMIS_LLM_PROVIDER: openai
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  ARTEMIS_AUTO_APPROVE_PROJECT_ANALYSIS: "true"
  ARTEMIS_COST_LIMIT_USD: "10.00"
  ARTEMIS_MAX_PARALLEL_DEVELOPERS: "2"
```

## Troubleshooting

### Issue: "Invalid API key" Error

**Cause:** API key is expired, invalid, or incorrectly formatted

**Solution:**
1. Check API key format (should start with `sk-` for OpenAI)
2. Verify key is active in provider dashboard
3. Ensure no extra spaces or quotes in environment variable

```bash
# Wrong
export OPENAI_API_KEY=" sk-key-here "

# Correct
export OPENAI_API_KEY="sk-key-here"
```

### Issue: "Missing Required Keys" Error

**Cause:** Required API key not set for selected provider

**Solution:**
```bash
# Check current provider
echo $ARTEMIS_LLM_PROVIDER

# Set correct API key
export OPENAI_API_KEY="your-key"
# OR
export ANTHROPIC_API_KEY="your-key"
```

### Issue: Configuration Not Loading

**Cause:** Environment variables not exported in current shell

**Solution:**
```bash
# Check if variable is set
env | grep ARTEMIS

# Set and verify
export OPENAI_API_KEY="sk-key"
echo $OPENAI_API_KEY

# Persist across sessions (add to ~/.bashrc or ~/.zshrc)
echo 'export OPENAI_API_KEY="sk-key"' >> ~/.bashrc
source ~/.bashrc
```

### Issue: Want to Use Different Models for Different Stages

**Current Limitation:** Configuration applies globally to all stages

**Workaround:** Modify specific stage code to override model:

```python
# In developer_invoker.py or specific stage
developer = StandaloneDeveloperAgent(
    developer_name="developer-a",
    llm_model="gpt-4o-mini"  # Override for this stage only
)
```

## Best Practices

1. **Never Commit API Keys** - Use environment variables, not hardcoded values
2. **Use .env Files** - Store local development config in `.env` (gitignored)
3. **Validate Early** - Check configuration before starting expensive operations
4. **Monitor Costs** - Set `ARTEMIS_COST_LIMIT_USD` in production
5. **Rotate Keys** - Regularly rotate API keys for security
6. **Log Masked Values** - Always use `get_masked()` for sensitive data in logs
7. **Test Configuration** - Run `--config-report` before full pipeline execution

## Security Considerations

1. **API Key Protection**
   - Never log unmasked API keys
   - Never commit API keys to git
   - Use environment variables or secret managers

2. **Validation**
   - Always validate configuration before running pipeline
   - Use `--skip-validation` only for debugging (not recommended)

3. **Cost Controls**
   - Set `ARTEMIS_COST_LIMIT_USD` to prevent runaway costs
   - Monitor `ARTEMIS_MAX_TOKENS_PER_REQUEST` for budget control

4. **Compliance**
   - Keep `ARTEMIS_ENFORCE_GDPR=true` in production
   - Keep `ARTEMIS_ENFORCE_WCAG=true` for accessibility

## Future Enhancements

- [ ] Support for `.env` file loading
- [ ] Integration with secret managers (AWS Secrets Manager, HashiCorp Vault)
- [ ] Per-stage model configuration
- [ ] Dynamic cost tracking and limits
- [ ] Configuration validation hooks (pre-flight checks)
- [ ] Configuration templates for different environments (dev/staging/prod)

---

**Version:** 1.0.0
**Date:** October 22, 2025
**Status:** ✅ **PRODUCTION READY**
**Maintainer:** Artemis Pipeline Team
