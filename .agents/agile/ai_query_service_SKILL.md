---
name: ai-query-service
description: Centralized LLM query service with intelligent routing and optimization
---

# Ai Query Service

## Purpose

Routes LLM queries to optimal providers with caching and resilience

## When to Use This Skill

1. **All LLM Queries** - Centralized access point
2. **Cost Optimization** - Route to cheapest capable model
3. **Resilience** - Automatic fallback on failures
4. **Observability** - Track LLM usage metrics

## Responsibilities

1. **Intelligent routing** - (task type → best LLM)
2. **Response caching** - for identical queries
3. **Rate limit** - and retry handling
4. **Token usage** - optimization
5. **Cost and** - latency tracking

## Integration with Pipeline

### Communication

**Receives:**
- Input data specific to agent's purpose

**Sends:**
- Processed output and analysis results

## Usage Examples

### Standalone Usage

```bash
python3 ai_query_service.py --help
```

### Programmatic Usage

```python
from ai_query_service import AiQueryService

agent = AiQueryService()
result = agent.execute()
```

## Configuration

### Environment Variables

```bash
# Agent-specific configuration
ARTEMIS_AI_QUERY_SERVICE_ENABLED=true
ARTEMIS_LLM_PROVIDER=openai
ARTEMIS_LLM_MODEL=gpt-4o
```

### Hydra Configuration (if applicable)

```yaml
ai_query_service:
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
