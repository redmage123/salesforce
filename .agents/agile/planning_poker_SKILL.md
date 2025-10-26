---
name: planning-poker
description: Facilitates agile planning poker estimation with parallel vote collection and risk assessment
---

# Planning Poker

## Purpose

Conducts story point estimation using multiple developer personas with Planning Poker methodology

## When to Use This Skill

1. **Sprint Planning** - Estimate user stories
2. **Feature Sizing** - Assess complexity
3. **Risk Assessment** - Identify high-risk items
4. **Team Calibration** - Align estimation standards

## Responsibilities

1. **Facilitate Planning** - Poker sessions with multiple agents
2. **Collect votes** - in parallel (3x faster with ThreadPoolExecutor)
3. **Build consensus** - through discussion rounds
4. **Assess risk** - based on estimates and confidence
5. **Generate detailed** - estimation reports

## Integration with Pipeline

### Communication

**Receives:**

- User stories from Sprint Planning stage
- Developer agent personas (conservative, aggressive)
- Team velocity from previous sprints


**Sends:**

- Story point estimates with confidence
- Risk assessment (low/medium/high)
- Voting history and discussion notes


## Usage Examples

### Standalone Usage

```bash
python3 planning_poker.py \
  --story-title "User Authentication" \
  --story-description "Implement JWT-based authentication" \
  --team-velocity 15
```

### Programmatic Usage

```python
from planning_poker import PlanningPoker

poker = PlanningPoker(
    agents=developer_agents,
    llm_client=llm_client,
    team_velocity=15
)

result = poker.estimate_story(
    title="User Authentication",
    description="Implement JWT authentication",
    acceptance_criteria=["Login works", "Logout works"]
)

print(f"Estimate: {result['estimate']} points")
print(f"Confidence: {result['confidence']}")
print(f"Risk: {result['risk_level']}")
```

## Configuration

### Environment Variables

```bash
# Agent-specific configuration
ARTEMIS_PLANNING_POKER_ENABLED=true
ARTEMIS_LLM_PROVIDER=openai
ARTEMIS_LLM_MODEL=gpt-4o
```

### Hydra Configuration (if applicable)

```yaml
planning_poker:
  enabled: true
  llm:
    provider: openai
    model: gpt-4o
```

## Best Practices

1. **Use Multiple Personas** - At least 2-3 developers for diverse perspectives
2. **Set Team Velocity** - Provides context for estimation
3. **Enable Parallelization** - Use ThreadPoolExecutor for 3x speedup
4. **Discussion Rounds** - Allow 2-3 rounds for consensus
5. **Risk Assessment** - Use confidence scores to identify risky estimates

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
