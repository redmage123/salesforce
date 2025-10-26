---
name: retrospective-agent
description: Conducts sprint retrospectives with metric analysis and improvement recommendations
---

# Retrospective Agent

## Purpose

Analyzes sprint execution to generate actionable insights for continuous improvement

## When to Use This Skill

1. **Sprint End** - Conduct retrospective
2. **Milestone Review** - Analyze multiple sprints
3. **Process Improvement** - Identify optimization opportunities
4. **Team Health Check** - Assess team dynamics

## Responsibilities

1. **Analyze sprint** - metrics (velocity, cycle time, defect rate)
2. **Identify what** - went well and improvement areas
3. **Perform root** - cause analysis on issues
4. **Generate actionable** - recommendations
5. **Track improvement** - actions over time

## Integration with Pipeline

### Communication

**Receives:**
- Input data specific to agent's purpose

**Sends:**
- Processed output and analysis results

## Usage Examples

### Standalone Usage

```bash
python3 retrospective_agent.py --help
```

### Programmatic Usage

```python
from retrospective_agent import RetrospectiveAgent

agent = RetrospectiveAgent()
result = agent.execute()
```

## Configuration

### Environment Variables

```bash
# Agent-specific configuration
ARTEMIS_RETROSPECTIVE_AGENT_ENABLED=true
ARTEMIS_LLM_PROVIDER=openai
ARTEMIS_LLM_MODEL=gpt-4o
```

### Hydra Configuration (if applicable)

```yaml
retrospective_agent:
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
