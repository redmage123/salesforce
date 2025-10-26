---
name: project-analysis-agent
description: Analyzes codebase structure, identifies technical debt, and generates architecture insights
---

# Project Analysis Agent

## Purpose

Provides deep analysis of project structure and code quality

## When to Use This Skill

1. **Project Onboarding** - Understand codebase
2. **Architecture Review** - Assess system design
3. **Technical Debt Assessment** - Prioritize refactoring
4. **Documentation Generation** - Auto-generate docs

## Responsibilities

1. **Analyze codebase** - structure and architecture
2. **Map dependencies** - and component relationships
3. **Identify technical** - debt and code smells
4. **Generate architecture** - documentation
5. **Extract knowledge** - for RAG storage

## Integration with Pipeline

### Communication

**Receives:**
- Input data specific to agent's purpose

**Sends:**
- Processed output and analysis results

## Usage Examples

### Standalone Usage

```bash
python3 project_analysis_agent.py --help
```

### Programmatic Usage

```python
from project_analysis_agent import ProjectAnalysisAgent

agent = ProjectAnalysisAgent()
result = agent.execute()
```

## Configuration

### Environment Variables

```bash
# Agent-specific configuration
ARTEMIS_PROJECT_ANALYSIS_AGENT_ENABLED=true
ARTEMIS_LLM_PROVIDER=openai
ARTEMIS_LLM_MODEL=gpt-4o
```

### Hydra Configuration (if applicable)

```yaml
project_analysis_agent:
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
