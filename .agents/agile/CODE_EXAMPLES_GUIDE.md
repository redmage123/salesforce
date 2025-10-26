# Code Examples for RAG/Knowledge Graph

This guide documents the curated code examples stored in RAG and Knowledge Graph to help Artemis agents generate better code.

## Overview

We maintain high-quality code examples for **30+ languages and 10+ database systems** demonstrating:
- Design patterns (Factory, Repository, Strategy, Observer, etc.)
- Language-specific idioms and best practices
- Database-specific optimizations
- Security patterns
- Anti-patterns (with corrections)

## Quick Start

### Populate All Examples

```bash
# Populate all code examples
python populate_code_examples.py --all

# Populate specific language
python populate_code_examples.py --language python

# Populate specific pattern
python populate_code_examples.py --pattern repository

# RAG only (skip Knowledge Graph)
python populate_code_examples.py --all --rag-only
```

### Query Examples in Agent Code

```python
from rag_agent import RAGAgent

rag = RAGAgent()

# Find repository pattern examples in Python
examples = rag.query(
    query_text="Repository pattern with SQLAlchemy database access",
    collection_name="code_examples_python",
    top_k=3
)

# Use in developer prompt
prompt = f"""
Implement a user repository.

Reference these proven patterns:
{examples[0]['content']}

Follow the same principles but adapt to your task.
"""
```

## Examples by Language

### Programming Languages (30)

| Language | Examples | Patterns Covered |
|----------|----------|------------------|
| **Python** | 10+ | Repository, Factory, Error Handling, SQLAlchemy, Functional Patterns |
| **Rust** | 8+ | Result Types, Ownership, Iterators, Error Handling, Traits |
| **Java** | 8+ | Stream API, Optional, Builder, Factory, Records |
| **JavaScript** | 8+ | Promises, async/await, Functional Patterns, Closures |
| **TypeScript** | 8+ | Type Guards, Generics, Decorators, Strict Types |
| **Go** | 6+ | Goroutines, Channels, Error Handling, Interfaces |
| **C++** | 6+ | RAII, Smart Pointers, Move Semantics, Templates |
| **Rust** | 6+ | Ownership, Borrowing, Lifetimes, Error Handling |
| **C#** | 6+ | LINQ, async/await, Records, Pattern Matching |
| **Scala** | 5+ | Case Classes, Pattern Matching, For-Comprehensions |
| **Haskell** | 5+ | Monads, Functors, Type Classes, Lazy Evaluation |
| **Erlang** | 5+ | Actor Model, Supervision Trees, Pattern Matching |
| **Perl** | 4+ | Regex, Context-Aware Operations, CPAN Modules |
| **Fortran** | 4+ | Array Operations, Coarrays, Pure Functions |
| **R** | 5+ | Vectorization, data.table, dplyr, apply Family |
| **MATLAB** | 5+ | Vectorization, Matrix Operations, parfor |
| **PHP** | 5+ | Modern PHP 8+, PSR Standards, Type Declarations |
| **Ruby** | 4+ | Blocks, Enumerable, Metaprogramming |
| **Swift** | 4+ | Optionals, Protocol-Oriented, Value Types |
| **Kotlin** | 4+ | Null Safety, Coroutines, Data Classes |
| **Assembly** | 4+ | SIMD, Register Optimization, Calling Conventions |

### Databases (10+)

#### SQL Databases

| Database | Examples | Features Covered |
|----------|----------|------------------|
| **PostgreSQL** | 12+ | JSONB, Window Functions, Full-Text Search, CTEs, LISTEN/NOTIFY, Extensions |
| **MySQL** | 8+ | InnoDB, utf8mb4, JSON Functions, Partitioning, Upserts |
| **SQL Server** | 8+ | Columnstore, Temporal Tables, MERGE, Memory-Optimized Tables |
| **IBM DB2** | 6+ | MQTs, pureXML, Federation, Column-Organized Tables |

#### NoSQL Databases

| Database | Examples | Features Covered |
|----------|----------|------------------|
| **MongoDB** | 10+ | Aggregation Pipeline, Sharding, Change Streams, Schema Validation |
| **Cassandra** | 8+ | Partition Keys, TTL, Materialized Views, Time-Series Modeling |
| **Redis** | 8+ | Data Structures, Pipelining, Lua Scripts, Streams, HyperLogLog |
| **DynamoDB** | 6+ | Single-Table Design, GSI/LSI, Streams, Transactions |
| **Elasticsearch** | 6+ | Inverted Indexes, Query DSL, Aggregations, Bulk API |
| **Neo4j** | 6+ | Cypher Queries, Graph Algorithms, APOC, Relationship Modeling |

## Example Structure

Each code example includes:

```python
CodeExample(
    language="Python",                    # Target language
    pattern="Repository Pattern",         # Design pattern
    title="User Repository with SQLAlchemy", # Descriptive title
    description="...",                    # What it demonstrates
    code="...",                           # Actual code
    quality_score=95,                     # 1-100 (human-reviewed)
    tags=["ORM", "database", "..."],     # Searchable tags
    complexity="intermediate",            # beginner/intermediate/advanced
    demonstrates=[...],                   # Concepts taught
    prevents=[...]                        # Anti-patterns prevented
)
```

## RAG Storage Structure

Examples are stored in language-specific collections:

```
Collections:
  - code_examples_python/
  - code_examples_rust/
  - code_examples_sql/
  - code_examples_javascript/
  - ...
```

Each artifact includes:
- Full code with comments
- Explanation of WHY (not just WHAT)
- Anti-patterns prevented
- Related patterns
- Searchable metadata

## Knowledge Graph Structure

Relationships created:

```
(Example) -[DEMONSTRATES]-> (Pattern)
(Example) -[WRITTEN_IN]-> (Language)
(Example) -[TEACHES]-> (Concept)
(Example) -[PREVENTS]-> (AntiPattern)
(Example) -[USES]-> (Library/Framework)
(Example) -[QUALITY_SCORE]-> (Score)
```

Example queries:

```cypher
// Find all examples preventing God Class anti-pattern
MATCH (ex:CodeExample)-[:PREVENTS]->(ap {name: "God Class"})
RETURN ex.language, ex.title, ex.quality_score
ORDER BY ex.quality_score DESC;

// Find best Repository Pattern examples
MATCH (ex:CodeExample)-[:DEMONSTRATES]->(p {name: "Repository Pattern"})
WHERE ex.quality_score > 90
RETURN ex.language, ex.title, ex.quality_score
ORDER BY ex.quality_score DESC;

// Find all examples using SQLAlchemy
MATCH (ex:CodeExample)-[:USES]->(lib {name: "SQLAlchemy"})
RETURN ex.title, ex.pattern;
```

## Example Categories

### 1. Design Patterns

**Creational:**
- Factory Pattern (10 languages)
- Builder Pattern (8 languages)
- Singleton Pattern (6 languages)

**Structural:**
- Repository Pattern (12 languages)
- Adapter Pattern (8 languages)
- Decorator Pattern (8 languages)

**Behavioral:**
- Strategy Pattern (10 languages)
- Observer Pattern (8 languages)
- Command Pattern (6 languages)

### 2. Language-Specific Idioms

- **Python**: List comprehensions, context managers, decorators
- **Rust**: Ownership patterns, iterator combinators
- **Haskell**: Monad transformers, type classes
- **Perl**: Regex patterns, context-aware operations
- **R**: Vectorization, pipes, data.table syntax
- **MATLAB**: Vectorization, anonymous functions

### 3. Database Patterns

**Query Optimization:**
- N+1 query prevention (all SQL databases)
- Eager loading (ORMs)
- Index usage (all databases)
- Query plan optimization

**Data Modeling:**
- Normalization vs denormalization
- Partition key selection (Cassandra, DynamoDB)
- Shard key selection (MongoDB)
- Graph modeling (Neo4j)

**Performance:**
- Batch operations
- Connection pooling
- Query caching
- Aggregation pipelines

### 4. Security Patterns

- Parameterized queries (SQL injection prevention)
- Input validation
- Output encoding (XSS prevention)
- CSRF protection
- Password hashing (bcrypt, Argon2)

### 5. Anti-Patterns (with Corrections)

- God Classes → Single Responsibility
- Nested Loops → Functional patterns
- N+1 Queries → Eager loading
- Magic Numbers → Configuration classes
- Nested Ifs → Guard clauses
- String concatenation in SQL → Parameterized queries

## Quality Standards

All examples are:
- ✅ **Production-ready** - No TODOs or placeholders
- ✅ **Well-commented** - Explain WHY, not just WHAT
- ✅ **Security-conscious** - Follow OWASP guidelines
- ✅ **Performance-optimized** - Use language-specific best practices
- ✅ **SOLID-compliant** - Follow design principles
- ✅ **Tested** - Include test examples where applicable

## Adding New Examples

To add new examples:

1. **Create CodeExample instance:**
```python
new_example = CodeExample(
    language="YourLanguage",
    pattern="YourPattern",
    title="Descriptive Title",
    description="What it demonstrates",
    code='''
    # Your code here with comments
    ''',
    quality_score=90,  # Honest assessment
    tags=["tag1", "tag2"],
    complexity="intermediate",
    demonstrates=["Concept1", "Concept2"],
    prevents=["AntiPattern1", "AntiPattern2"]
)
```

2. **Add to appropriate list:**
```python
# In populate_code_examples.py or code_examples_database.py
YOUR_LANGUAGE_EXAMPLES = [new_example]
LANGUAGE_EXAMPLES["YourLanguage"] = YOUR_LANGUAGE_EXAMPLES
```

3. **Populate RAG/KG:**
```bash
python populate_code_examples.py --language yourlanguage
```

## Integration with Agents

### Developer Agents

Developer agents automatically retrieve relevant examples:

```python
# In standalone_developer_agent.py
def generate_implementation(self, task, language):
    # Retrieve examples
    examples = self.rag.query(
        query_text=f"{task.pattern} in {language}",
        collection_name=f"code_examples_{language.lower()}",
        top_k=2
    )

    # Inject into prompt
    prompt = self._build_prompt(task, examples)

    # Generate code
    return self.llm.generate(prompt)
```

### Code Review Agents

Code review agents use examples to validate implementations:

```python
# In code_review_agent.py
def review_code(self, code, language):
    # Find anti-patterns
    anti_pattern_examples = self.rag.query(
        query_text="anti-patterns to avoid",
        collection_name=f"code_examples_{language.lower()}",
        filters={"prevents": ["God Class", "N+1 Queries"]}
    )

    # Compare implementation against best practices
    return self._analyze_code(code, anti_pattern_examples)
```

## Maintenance

### Quarterly Review

- Review quality scores
- Add new patterns
- Update outdated examples (library versions, syntax)
- Remove deprecated patterns

### Continuous Improvement

- Track which examples agents retrieve most
- Measure code quality improvements
- Add examples for frequently occurring issues
- Community contributions

## Metrics

Track effectiveness:

```sql
-- Most retrieved examples
SELECT language, pattern, COUNT(*) as retrieval_count
FROM rag_query_logs
WHERE collection LIKE 'code_examples_%'
GROUP BY language, pattern
ORDER BY retrieval_count DESC;

-- Code quality improvement
SELECT
    AVG(quality_score_before) as before,
    AVG(quality_score_after) as after,
    (AVG(quality_score_after) - AVG(quality_score_before)) as improvement
FROM code_review_results
WHERE examples_used = true;
```

## Resources

### External Sources

**Language-Specific:**
- Python: [Real Python](https://realpython.com/), SQLAlchemy docs
- Rust: [Rust by Example](https://doc.rust-lang.org/rust-by-example/)
- Haskell: [Learn You a Haskell](http://learnyouahaskell.com/)
- Go: [Go by Example](https://gobyexample.com/)

**Database-Specific:**
- PostgreSQL: [PostgreSQL Wiki](https://wiki.postgresql.org/)
- MongoDB: [MongoDB University](https://university.mongodb.com/)
- Redis: [Redis University](https://university.redis.com/)
- Neo4j: [Neo4j GraphAcademy](https://graphacademy.neo4j.com/)

**Design Patterns:**
- [Refactoring Guru](https://refactoring.guru/design-patterns)
- [Source Making](https://sourcemaking.com/)

## Future Enhancements

1. **Automated Collection** - Scrape high-quality open-source projects
2. **Community Contributions** - Allow team to submit examples
3. **Version Tracking** - Track example evolution over time
4. **A/B Testing** - Test which examples lead to better code
5. **Multi-modal Examples** - Include diagrams, videos
6. **Interactive Examples** - Runnable code snippets

---

**Maintained By:** Artemis Development Team
**Last Updated:** October 24, 2025
**Version:** 1.0.0
