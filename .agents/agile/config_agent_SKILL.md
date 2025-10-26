---
name: config-agent
description: Manages Hydra-based hierarchical configuration with validation
---

# Config Agent

## Purpose

Provides type-safe, validated configuration management for Artemis

## When to Use This Skill

1. **System Initialization** - Load configs
2. **Environment Setup** - Dev/staging/prod configs
3. **Configuration Validation** - Check correctness
4. **Override Management** - Apply runtime overrides

## Responsibilities

1. **Load Hydra** - YAML configurations
2. **Validate configuration** - schemas
3. **Support composition** - and overrides
4. **Environment-specific configs** - 
5. **Type-safe configuration** - access

## Integration with Pipeline

### Communication

**Receives:**
- Input data specific to agent's purpose

**Sends:**
- Processed output and analysis results

## Usage Examples

### Standalone Usage

```bash
python3 config_agent.py --help
```

### Programmatic Usage

```python
from config_agent import ConfigAgent

agent = ConfigAgent()
result = agent.execute()
```

## Configuration

### Environment Variables

```bash
# Agent-specific configuration
ARTEMIS_CONFIG_AGENT_ENABLED=true
ARTEMIS_LLM_PROVIDER=openai
ARTEMIS_LLM_MODEL=gpt-4o
```

### Hydra Configuration (if applicable)

```yaml
config_agent:
  enabled: true
  llm:
    provider: openai
    model: gpt-4o
```

## Best Practices

1. Follow agent-specific guidelines
2. Monitor performance metrics
3. Handle errors gracefully
4. Log important events
5. Integrate with observability

## Cost Considerations

Typical cost: $0.05-0.20 per operation depending on complexity

## Limitations

- Depends on LLM quality
- Context window limits
- May require multiple iterations

## References

- [Artemis Documentation](../README.md)
- [Agent Pattern](https://en.wikipedia.org/wiki/Software_agent)

---

**Version:** 1.0.0

**Maintained By:** Artemis Pipeline Team

**Last Updated:** October 24, 2025
