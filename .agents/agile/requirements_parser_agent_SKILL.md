---
name: requirements-parser-agent
description: Parses natural language requirements into structured, machine-readable format
---

# Requirements Parser Agent

## Purpose

Extracts and structures requirements from documents using NLP and LLM intelligence

## When to Use This Skill

1. **Project Kickoff** - Parse initial requirements
2. **Requirement Updates** - Process change requests
3. **Compliance Verification** - Ensure complete requirements
4. **Sprint Planning Input** - Provide structured backlog

## Responsibilities

1. **Parse natural** - language requirements documents
2. **Extract functional** - and non-functional requirements
3. **Classify requirements** - (MoSCoW: Must/Should/Could/Won't)
4. **Identify dependencies** - and constraints
5. **Validate requirement** - completeness and clarity

## Integration with Pipeline

### Communication

**Receives:**
- Input data specific to agent's purpose

**Sends:**
- Processed output and analysis results

## Usage Examples

### Standalone Usage

```bash
python3 requirements_parser_agent.py --help
```

### Programmatic Usage

```python
from requirements_parser_agent import RequirementsParserAgent

agent = RequirementsParserAgent()
result = agent.execute()
```

## Configuration

### Environment Variables

```bash
# Agent-specific configuration
ARTEMIS_REQUIREMENTS_PARSER_AGENT_ENABLED=true
ARTEMIS_LLM_PROVIDER=openai
ARTEMIS_LLM_MODEL=gpt-4o
```

### Hydra Configuration (if applicable)

```yaml
requirements_parser_agent:
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
