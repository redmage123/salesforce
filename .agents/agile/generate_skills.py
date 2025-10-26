#!/usr/bin/env python3
"""
Script to generate SKILL.md files for all remaining Artemis agents.
"""

from pathlib import Path

# Define all agents and their metadata
AGENTS = {
    "planning_poker": {
        "name": "planning-poker",
        "description": "Facilitates agile planning poker estimation with parallel vote collection and risk assessment",
        "purpose": "Conducts story point estimation using multiple developer personas with Planning Poker methodology",
        "responsibilities": [
            "Facilitate Planning Poker sessions with multiple agents",
            "Collect votes in parallel (3x faster with ThreadPoolExecutor)",
            "Build consensus through discussion rounds",
            "Assess risk based on estimates and confidence",
            "Generate detailed estimation reports"
        ],
        "when_to_use": [
            "Sprint Planning - Estimate user stories",
            "Feature Sizing - Assess complexity",
            "Risk Assessment - Identify high-risk items",
            "Team Calibration - Align estimation standards"
        ]
    },
    "requirements_parser_agent": {
        "name": "requirements-parser-agent",
        "description": "Parses natural language requirements into structured, machine-readable format",
        "purpose": "Extracts and structures requirements from documents using NLP and LLM intelligence",
        "responsibilities": [
            "Parse natural language requirements documents",
            "Extract functional and non-functional requirements",
            "Classify requirements (MoSCoW: Must/Should/Could/Won't)",
            "Identify dependencies and constraints",
            "Validate requirement completeness and clarity"
        ],
        "when_to_use": [
            "Project Kickoff - Parse initial requirements",
            "Requirement Updates - Process change requests",
            "Compliance Verification - Ensure complete requirements",
            "Sprint Planning Input - Provide structured backlog"
        ]
    },
    "retrospective_agent": {
        "name": "retrospective-agent",
        "description": "Conducts sprint retrospectives with metric analysis and improvement recommendations",
        "purpose": "Analyzes sprint execution to generate actionable insights for continuous improvement",
        "responsibilities": [
            "Analyze sprint metrics (velocity, cycle time, defect rate)",
            "Identify what went well and improvement areas",
            "Perform root cause analysis on issues",
            "Generate actionable recommendations",
            "Track improvement actions over time"
        ],
        "when_to_use": [
            "Sprint End - Conduct retrospective",
            "Milestone Review - Analyze multiple sprints",
            "Process Improvement - Identify optimization opportunities",
            "Team Health Check - Assess team dynamics"
        ]
    },
    "project_analysis_agent": {
        "name": "project-analysis-agent",
        "description": "Analyzes codebase structure, identifies technical debt, and generates architecture insights",
        "purpose": "Provides deep analysis of project structure and code quality",
        "responsibilities": [
            "Analyze codebase structure and architecture",
            "Map dependencies and component relationships",
            "Identify technical debt and code smells",
            "Generate architecture documentation",
            "Extract knowledge for RAG storage"
        ],
        "when_to_use": [
            "Project Onboarding - Understand codebase",
            "Architecture Review - Assess system design",
            "Technical Debt Assessment - Prioritize refactoring",
            "Documentation Generation - Auto-generate docs"
        ]
    },
    "rag_agent": {
        "name": "rag-agent",
        "description": "Retrieval-Augmented Generation for project knowledge management using ChromaDB",
        "purpose": "Stores and retrieves project artifacts with semantic search capabilities",
        "responsibilities": [
            "Store artifacts (prompts, code, docs) with embeddings",
            "Semantic search across project knowledge",
            "Context retrieval for LLM queries",
            "Version management for artifacts",
            "Integration with Knowledge Graph"
        ],
        "when_to_use": [
            "Context Retrieval - Get relevant info for LLMs",
            "Documentation Search - Find relevant docs",
            "Prompt Management - Store/retrieve prompts",
            "Code Examples - Find similar implementations"
        ]
    },
    "knowledge_graph": {
        "name": "knowledge-graph",
        "description": "GraphQL-based knowledge graph for managing project entities and relationships",
        "purpose": "Maintains structured knowledge about project components and their relationships",
        "responsibilities": [
            "Store entities and relationships (GraphQL)",
            "Complex relationship traversals",
            "Traceability (requirements → code → tests)",
            "Impact analysis for changes",
            "Hybrid retrieval with RAG"
        ],
        "when_to_use": [
            "Dependency Analysis - Understand relationships",
            "Impact Assessment - Predict change effects",
            "Traceability - Track requirement to implementation",
            "Knowledge Discovery - Find implicit connections"
        ]
    },
    "config_agent": {
        "name": "config-agent",
        "description": "Manages Hydra-based hierarchical configuration with validation",
        "purpose": "Provides type-safe, validated configuration management for Artemis",
        "responsibilities": [
            "Load Hydra YAML configurations",
            "Validate configuration schemas",
            "Support composition and overrides",
            "Environment-specific configs",
            "Type-safe configuration access"
        ],
        "when_to_use": [
            "System Initialization - Load configs",
            "Environment Setup - Dev/staging/prod configs",
            "Configuration Validation - Check correctness",
            "Override Management - Apply runtime overrides"
        ]
    },
    "ai_query_service": {
        "name": "ai-query-service",
        "description": "Centralized LLM query service with intelligent routing and optimization",
        "purpose": "Routes LLM queries to optimal providers with caching and resilience",
        "responsibilities": [
            "Intelligent routing (task type → best LLM)",
            "Response caching for identical queries",
            "Rate limit and retry handling",
            "Token usage optimization",
            "Cost and latency tracking"
        ],
        "when_to_use": [
            "All LLM Queries - Centralized access point",
            "Cost Optimization - Route to cheapest capable model",
            "Resilience - Automatic fallback on failures",
            "Observability - Track LLM usage metrics"
        ]
    }
}

SKILL_TEMPLATE = """---
name: {name}
description: {description}
---

# {title}

## Purpose

{purpose}

## When to Use This Skill

{when_to_use}

## Responsibilities

{responsibilities}

## Integration with Pipeline

### Communication

**Receives:**
{receives}

**Sends:**
{sends}

## Usage Examples

### Standalone Usage

```bash
{standalone_usage}
```

### Programmatic Usage

```python
{programmatic_usage}
```

## Configuration

### Environment Variables

```bash
{env_vars}
```

### Hydra Configuration (if applicable)

```yaml
{hydra_config}
```

## Best Practices

{best_practices}

## Cost Considerations

{cost_considerations}

## Limitations

{limitations}

## References

{references}

---

**Version:** 1.0.0

**Maintained By:** Artemis Pipeline Team

**Last Updated:** October 24, 2025
"""


def generate_skill_file(agent_key: str, agent_data: dict) -> str:
    """Generate SKILL.md content for an agent"""

    # Format lists
    when_to_use_formatted = "\n".join([f"{i+1}. **{item.split(' - ')[0]}** - {item.split(' - ')[1]}" for i, item in enumerate(agent_data["when_to_use"])])

    responsibilities_formatted = "\n".join([f"{i+1}. **{resp.split(' ')[0]} {resp.split(' ')[1] if len(resp.split(' ')) > 1 else ''}** - {' '.join(resp.split(' ')[2:])}" for i, resp in enumerate(agent_data["responsibilities"])])

    # Customize based on agent type
    if agent_key == "planning_poker":
        receives = """
- User stories from Sprint Planning stage
- Developer agent personas (conservative, aggressive)
- Team velocity from previous sprints
"""
        sends = """
- Story point estimates with confidence
- Risk assessment (low/medium/high)
- Voting history and discussion notes
"""
        standalone_usage = """python3 planning_poker.py \\
  --story-title "User Authentication" \\
  --story-description "Implement JWT-based authentication" \\
  --team-velocity 15"""

        programmatic_usage = """from planning_poker import PlanningPoker

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
print(f"Risk: {result['risk_level']}")"""

        best_practices = """1. **Use Multiple Personas** - At least 2-3 developers for diverse perspectives
2. **Set Team Velocity** - Provides context for estimation
3. **Enable Parallelization** - Use ThreadPoolExecutor for 3x speedup
4. **Discussion Rounds** - Allow 2-3 rounds for consensus
5. **Risk Assessment** - Use confidence scores to identify risky estimates"""

    elif agent_key == "rag_agent":
        receives = """
- Artifacts to store (prompts, docs, code)
- Search queries from other agents
- Context retrieval requests for LLMs
"""
        sends = """
- Relevant artifacts based on semantic similarity
- Context for LLM queries
- Search results with relevance scores
"""
        standalone_usage = """python3 rag_agent.py \\
  --operation store \\
  --content-file prompt.txt \\
  --collection prompts \\
  --metadata '{"type": "developer_prompt", "version": "1.0"}'"""

        programmatic_usage = """from rag_agent import RAGAgent

rag = RAGAgent(persist_directory="./rag_data")

# Store artifact
rag.store_artifact(
    content=prompt_text,
    collection_name="prompts",
    metadata={"type": "developer_prompt"}
)

# Retrieve context
results = rag.query(
    query_text="How to implement authentication?",
    collection_name="documentation",
    top_k=5
)

for doc in results:
    print(f"Relevance: {doc['score']:.2f}")
    print(f"Content: {doc['content'][:200]}...")"""

        best_practices = """1. **Organize Collections** - Separate prompts, docs, code
2. **Rich Metadata** - Tag artifacts for better filtering
3. **Regular Cleanup** - Archive old/unused artifacts
4. **Monitor Size** - ChromaDB can grow large
5. **Backup Regularly** - Persist directory is critical"""

    else:
        # Generic defaults
        receives = "- Input data specific to agent's purpose"
        sends = "- Processed output and analysis results"
        standalone_usage = f"python3 {agent_key}.py --help"
        programmatic_usage = f"""from {agent_key} import {agent_key.title().replace('_', '')}

agent = {agent_key.title().replace('_', '')}()
result = agent.execute()"""
        best_practices = """1. Follow agent-specific guidelines
2. Monitor performance metrics
3. Handle errors gracefully
4. Log important events
5. Integrate with observability"""

    env_vars = f"""# Agent-specific configuration
ARTEMIS_{agent_key.upper()}_ENABLED=true
ARTEMIS_LLM_PROVIDER=openai
ARTEMIS_LLM_MODEL=gpt-4o"""

    hydra_config = f"""{agent_key}:
  enabled: true
  llm:
    provider: openai
    model: gpt-4o"""

    cost_considerations = "Typical cost: $0.05-0.20 per operation depending on complexity"
    limitations = "- Depends on LLM quality\n- Context window limits\n- May require multiple iterations"
    references = "- [Artemis Documentation](../README.md)\n- [Agent Pattern](https://en.wikipedia.org/wiki/Software_agent)"

    return SKILL_TEMPLATE.format(
        name=agent_data["name"],
        description=agent_data["description"],
        title=agent_data["name"].replace("-", " ").title(),
        purpose=agent_data["purpose"],
        when_to_use=when_to_use_formatted,
        responsibilities=responsibilities_formatted,
        receives=receives,
        sends=sends,
        standalone_usage=standalone_usage,
        programmatic_usage=programmatic_usage,
        env_vars=env_vars,
        hydra_config=hydra_config,
        best_practices=best_practices,
        cost_considerations=cost_considerations,
        limitations=limitations,
        references=references
    )


def main():
    """Generate all SKILL.md files"""
    base_dir = Path(__file__).parent

    for agent_key, agent_data in AGENTS.items():
        filename = f"{agent_key}_SKILL.md"
        filepath = base_dir / filename

        content = generate_skill_file(agent_key, agent_data)

        with open(filepath, 'w') as f:
            f.write(content)

        print(f"Created: {filename}")

if __name__ == "__main__":
    main()
