---
name: knowledge-graph
description: GraphQL-based knowledge graph for managing project entities and relationships
---

# Knowledge Graph

## Purpose

Maintains structured knowledge about project components and their relationships

## When to Use This Skill

1. **Dependency Analysis** - Understand relationships
2. **Impact Assessment** - Predict change effects
3. **Traceability** - Track requirement to implementation
4. **Knowledge Discovery** - Find implicit connections

## Responsibilities

1. **Store entities** - and relationships (GraphQL)
2. **Complex relationship** - traversals
3. **Traceability (requirements** - → code → tests)
4. **Impact analysis** - for changes
5. **Hybrid retrieval** - with RAG

## Integration with Pipeline

### Communication

**Receives:**
- Input data specific to agent's purpose

**Sends:**
- Processed output and analysis results

## Usage Examples

### Standalone Usage

```bash
python3 knowledge_graph.py --help
```

### Programmatic Usage

```python
from knowledge_graph import KnowledgeGraph

agent = KnowledgeGraph()
result = agent.execute()
```

## Configuration

### Environment Variables

```bash
# Agent-specific configuration
ARTEMIS_KNOWLEDGE_GRAPH_ENABLED=true
ARTEMIS_LLM_PROVIDER=openai
ARTEMIS_LLM_MODEL=gpt-4o
```

### Hydra Configuration (if applicable)

```yaml
knowledge_graph:
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
