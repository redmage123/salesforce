#!/usr/bin/env python3
"""
Centralized Environment Context for All Artemis Agents

This module provides a single source of truth about the execution environment
that all agents should use when generating code, making architectural decisions,
or providing guidance.

This ensures consistent understanding across:
- Architecture Agent (ADR generation)
- Developer Agents (code implementation)
- Code Review Agent (review feedback)
- Project Analysis Agent (feasibility checks)
- Any other agent making technical decisions
"""

def get_environment_context() -> str:
    """
    Returns the standard environment context block that should be included
    in prompts for all agents that make technical/architectural decisions.

    This context helps agents understand:
    1. The execution environment (dev workstation vs production)
    2. What infrastructure is available
    3. What technologies are accessible
    4. What design patterns are appropriate

    Returns:
        str: Formatted environment context block ready for prompt inclusion
    """
    return """
**IMPLEMENTATION ENVIRONMENT & CONSTRAINTS**:

**Execution Environment**:
- Development/test environment (single developer workstation)
- No external infrastructure servers running or available
- No DevOps/infrastructure team to set up services
- Implementation must be immediately runnable after `git clone`

**Available Resources**:
- Standard programming language runtimes and their standard libraries
- Common development libraries (pandas/numpy for Python, Jackson/Gson for Java, Lodash for JS, etc.)
- File system access (for JSON, CSV, log files, etc.)
- Embedded databases (SQLite for Python, H2 for Java, SQLite for Node.js, etc.)
- In-memory data structures and caches

**Not Available** (would require separate installation/configuration):
- Message brokers (Kafka, RabbitMQ, ActiveMQ, etc.)
- Distributed computing frameworks (Spark, Hadoop, Flink, etc.)
- External databases requiring database servers (PostgreSQL, MySQL, MongoDB, Cassandra, etc.)
- Caching servers (Redis, Memcached, etc.)
- Search engines (Elasticsearch, Solr, etc.)
- Container orchestration (Kubernetes, Docker Swarm, etc.)

**Architecture Guidelines**:
- Design for single-machine execution
- Use file-based storage when persistence is needed
- Use embedded databases (SQLite/H2) instead of database servers
- Simulate streaming with file-watching or polling when needed
- Prefer simple, pragmatic solutions over enterprise patterns
- If requirements mention external systems, explain local alternatives
- Focus on testability with mocked dependencies

**Language-Specific Guidance**:
- Python: Use pandas, matplotlib, unittest.mock, sqlite3, pathlib
- Java: Use Jackson, H2, JUnit with mocks, java.nio.file
- JavaScript/Node: Use Lodash, SQLite3, Jest with mocks, fs/promises
- Go: Use encoding/json, sqlite3 driver, testify/mock, io/ioutil
- Rust: Use serde, rusqlite, mockall, std::fs
- Other languages: Follow similar patterns with standard libraries
"""


def get_environment_context_short() -> str:
    """
    Returns a condensed version of the environment context for agents
    that need brief reminders rather than full context.

    Returns:
        str: Condensed environment context
    """
    return """
**Environment**: Dev workstation, no external infrastructure, must run after git clone.
**Use**: Standard libs, file storage, embedded DBs (SQLite/H2), mocks for external systems.
**Avoid**: Kafka, Spark, PostgreSQL, Redis, Elasticsearch, or any server requiring separate setup.
"""


def validate_technology_choice(technology: str) -> tuple[bool, str]:
    """
    Validates whether a technology choice is appropriate for the environment.

    Args:
        technology: Name of the technology/library/framework

    Returns:
        tuple: (is_valid, reason_or_alternative)
    """
    # Technologies that require external infrastructure
    forbidden = {
        'kafka': 'Use file-watching or in-memory queues instead',
        'spark': 'Use pandas (Python), Streams API (Java), or standard collections',
        'hadoop': 'Use local file processing with standard I/O',
        'postgresql': 'Use SQLite (Python), H2 (Java), or file-based storage',
        'mysql': 'Use SQLite (Python), H2 (Java), or file-based storage',
        'mongodb': 'Use JSON files or embedded databases',
        'redis': 'Use in-memory dictionaries/maps or embedded cache',
        'elasticsearch': 'Use simple text search or embedded solutions',
        'rabbitmq': 'Use in-memory queues or file-based message passing',
        'cassandra': 'Use SQLite or file-based storage',
        'influxdb': 'Use CSV files or SQLite with time-series data',
    }

    tech_lower = technology.lower()
    for forbidden_tech, alternative in forbidden.items():
        if forbidden_tech in tech_lower:
            return False, alternative

    return True, "Technology is appropriate for the environment"


# Example usage for agents:
"""
from environment_context import get_environment_context

def build_agent_prompt(task_description: str) -> str:
    prompt = f"Task: {task_description}\n\n"
    prompt += get_environment_context()
    prompt += "\n\nGenerate implementation..."
    return prompt
"""
