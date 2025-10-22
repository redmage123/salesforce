# 🏹 ARTEMIS

**Autonomous Multi-Agent TDD Pipeline**

> Named after the Greek goddess of the hunt, Artemis relentlessly pursues optimal solutions through competitive parallel development, automated validation, and continuous learning.

---

## What is Artemis?

Artemis is an autonomous software development pipeline that delivers high-quality solutions by:

1. **Hunting for the Best** - Running 1-3 parallel developer agents that compete to create optimal implementations
2. **Validating Quality** - Enforcing strict TDD compliance with 80-90% test coverage requirements
3. **Scoring Objectively** - Using a 100-point arbitration system across 7 categories to select winners
4. **Learning Continuously** - Building institutional memory through RAG (Retrieval-Augmented Generation)

---

## The Artemis Philosophy

**"The best solution emerges through competition, not consensus."**

Traditional development: One developer, one approach, hope for the best.

**Artemis development**: Multiple parallel approaches, objective scoring, proven winner.

### Core Principles

1. **Competitive Development** - Parallel agents with different strategies (conservative vs aggressive)
2. **Test-Driven** - Red → Green → Refactor enforced at every step
3. **Objective Selection** - Data-driven arbitration, not subjective preference
4. **Continuous Learning** - Every task improves future recommendations via RAG
5. **Autonomous Execution** - From research to production without manual gates

---

## Architecture

```
Artemis Pipeline Flow:

┌──────────────────────────────────────────────────────────────┐
│  ARTEMIS ORCHESTRATOR - Hunt for Optimal Solutions          │
└───────────────┬──────────────────────────────────────────────┘
                │
    ┌───────────┴───────────┐
    │  0. Research (Optional)│ ← Autonomous web research
    │     - WebSearch        │   for complex/unfamiliar tasks
    │     - Data gathering   │
    └───────────┬───────────┘
                │
    ┌───────────┴───────────┐
    │  1. Architecture      │ ← Create ADR with
    │     - Create ADR      │   implementation guidance
    │     - Tech decisions  │
    └───────────┬───────────┘
                │
    ┌───────────┴───────────┐
    │  2. Dependencies      │ ← Validate runtime
    │     - Python version  │   environment
    │     - Package checks  │
    └───────────┬───────────┘
                │
    ┌───────────┴────────────────────┐
    │  3. Development (Parallel)     │
    ├────────────────────────────────┤
    │  Developer A   Developer B     │ ← Competitive
    │  (Conservative) (Aggressive)   │   parallel dev
    │                                 │
    │  Developer C (Optional)        │
    └───────────┬────────────────────┘
                │
    ┌───────────┴────────────────────┐
    │  4. Validation                 │ ← Enforce TDD
    │     - TDD compliance (9 checks)│   compliance
    │     - Test coverage ≥80-90%    │
    │     - Quality gates            │
    └───────────┬────────────────────┘
                │
    ┌───────────┴───────────┐
    │  5. Arbitration       │ ← Score & select
    │     - Score (100pts)  │   winner objectively
    │     - Select winner   │
    └───────────┬───────────┘
                │
    ┌───────────┴───────────┐
    │  6. Integration       │ ← Deploy winning
    │     - Deploy winner   │   solution
    │     - Regression tests│
    └───────────┬───────────┘
                │
    ┌───────────┴───────────┐
    │  7. Testing           │ ← Final quality
    │     - UI/UX ≥80       │   gates
    │     - Performance ≥70 │
    │     - Production ready│
    └───────────┬───────────┘
                │
            ✅ DONE
```

---

## Dynamic Workflow Planning

Artemis automatically adapts the workflow based on task complexity:

### Task Complexity Analysis

Artemis analyzes each task and calculates a complexity score based on:

- **Priority** (high/medium/low)
- **Story points** (13+, 8-12, 5-7, <5)
- **Keywords** (integrate, architecture, refactor, API, etc.)

### Adaptive Execution

**Simple Tasks** (complexity score < 3):
- 1 developer (sequential)
- Skip arbitration
- Faster execution

**Medium Tasks** (score 3-5):
- 2 parallel developers
- Full validation + arbitration
- Balanced speed vs thoroughness

**Complex Tasks** (score 6+):
- 3 parallel developers
- Comprehensive research
- Full pipeline with all stages

---

## The 9 Specialized Agents

| Agent | Role | Input | Output |
|-------|------|-------|--------|
| **Research** | Autonomous web research | Task description | Research report with recommendations |
| **Architecture** | Create ADRs | Task + research | Architecture Decision Record |
| **Dependency Validation** | Check runtime environment | ADR + requirements | Validated dependencies or blockers |
| **Developer A** | Conservative implementation | ADR | TDD solution (80%+ coverage) |
| **Developer B** | Aggressive implementation | ADR | TDD solution (90%+ coverage) |
| **Developer C** | Alternative approach | ADR | TDD solution (optional, complex tasks only) |
| **Validator** | TDD compliance check | Developer solutions | Approved/Blocked per solution |
| **Arbitrator** | Score & select winner | Approved solutions | Winning solution (scored 0-100) |
| **Integrator** | Deploy winner | Winning solution | Deployed + regression tests |
| **Tester** | Final quality gates | Integrated solution | Production-ready confirmation |
| **Orchestrator** | Coordinate all agents | Kanban card | Complete pipeline execution |

---

## RAG Institutional Memory

Artemis learns from every task and continuously improves recommendations.

### What Gets Stored

Every pipeline run stores:

- **Research reports** - Technology recommendations, security findings
- **Architecture decisions** - ADRs with technical rationale
- **Developer solutions** - Winning and losing approaches
- **Validation results** - TDD compliance, test quality
- **Arbitration scores** - What worked, what didn't
- **Integration results** - Deployment success/failures
- **Testing results** - Quality metrics over time

### What You Get

When Artemis starts a new task, it queries RAG for similar past work:

```
🧠 RAG Insights (5 similar tasks found):
Confidence: HIGH

Based on history:
  • Used authlib in 3 past similar tasks
  • OAuth implementation approach scored 95/100
  • Flask integration pattern proven successful

Recommendations:
  ✓ Consider authlib (proven in 3 similar tasks)
  ✓ Use Flask-Login for session management
  ✓ Encrypt tokens in database (critical security finding)

Things to avoid:
  ⚠ Watch for token expiration issues (found in 2 similar tasks)
```

### Continuous Improvement

- **Week 1**: No history → Generic recommendations
- **Week 4**: 20 tasks → Technology preferences emerge
- **Week 12**: 80+ tasks → High-confidence recommendations
- **Week 24**: 200+ tasks → Institutional expert knowledge

---

## Arbitration Scoring System

Artemis uses a 100-point objective scoring system:

| Category | Points | Criteria |
|----------|--------|----------|
| **Syntax & Structure** | 20 | Valid HTML/syntax, no errors |
| **TDD Compliance** | 10 | Tests written first, Red→Green→Refactor |
| **Test Coverage** | 15 | ≥85% = 15pts, ≥80% = 12pts, ≥75% = 8pts |
| **Test Quality** | 20 | Test count, 100% pass rate, test types |
| **Functional Correctness** | 15 | Acceptance criteria met, edge cases |
| **Code Quality** | 15 | Readability, documentation, maintainability |
| **Simplicity Bonus** | 5 | Simpler solution preferred (tie-breaker) |

**Winner Selection:**
- Highest score wins
- Ties broken by simplicity (fewer lines = better)
- Conservative approach (Developer A) preferred for ties

---

## Usage

### Run Full Pipeline

```bash
python3 pipeline_orchestrator.py --card-id card-20241021135619 --full
```

**Output:**
```
🏹 ARTEMIS - STARTING AUTONOMOUS HUNT FOR OPTIMAL SOLUTION
============================================================

📊 ANALYZING TASK AND CREATING WORKFLOW PLAN
🧠 QUERYING RAG FOR HISTORICAL CONTEXT

📋 WORKFLOW PLAN
============================================================
Task Type: feature
Complexity: medium
Parallel Developers: 2
Execution Strategy: parallel

Stages to Execute: architecture, dependencies, validation, arbitration, integration, testing

Reasoning:
  • Medium complexity: Running 2 parallel developers
============================================================

📋 STAGE 1/6: ARCHITECTURE
✅ ADR created: ADR-003-oauth-implementation.md
```

### Run Specific Stage

```bash
python3 pipeline_orchestrator.py --card-id card-123 --stage arbitration
```

### Continue from Current Stage

```bash
python3 pipeline_orchestrator.py --card-id card-123 --continue
```

---

## Configuration

### Developer Agent Strategies

**Developer A - Conservative** (.agents/developer_a_SKILL.md):
- 80%+ test coverage
- Proven patterns only
- Minimal dependencies
- Prioritizes stability

**Developer B - Aggressive** (.agents/developer_b_SKILL.md):
- 90%+ test coverage
- Modern patterns
- Edge case handling
- Prioritizes completeness

### Research Triggers

Research stage runs automatically when:
- User explicitly requests research prompts
- Task complexity = "complex"
- Task priority = "high"
- Unfamiliar technology detected (OAuth, Kubernetes, ML, etc.)
- Security-critical keywords found (payment, auth, encryption, etc.)

---

## Communication Protocol

All agents communicate via:

1. **AgentMessenger** - Inter-agent messaging system
2. **Shared State** - Pipeline-wide state at `/tmp/pipeline_state.json`
3. **Agent Registry** - Active agent tracking at `/tmp/agent_registry.json`

### Message Types

- **DATA_UPDATE** - Share specialty data (e.g., ADR created)
- **REQUEST** - Request action from another agent
- **RESPONSE** - Respond to requests
- **NOTIFICATION** - Broadcast to all agents
- **ERROR** - Report errors for escalation

---

## Quality Gates

### TDD Validation (9 Checks)

1. ✅ Tests written first
2. ✅ Red phase (failing tests)
3. ✅ Green phase (passing tests)
4. ✅ Refactor phase
5. ✅ Test coverage ≥80% (Dev A) or ≥90% (Dev B)
6. ✅ All tests passing
7. ✅ Test quality (unit, integration, E2E)
8. ✅ Edge cases tested
9. ✅ Acceptance criteria covered

### Final Testing Gates

1. **Regression Tests** - All tests 100% passing
2. **UI/UX Score** - ≥80/100 (accessibility, responsiveness, design)
3. **Performance Score** - ≥70/100 (load time, efficiency)

**Fail any gate** → Pipeline blocks, card stays in current stage

---

## Roadmap

### Phase 1: Branding ✅ (Current)
- ✅ Rename PipelineOrchestrator → ArtemisOrchestrator
- ✅ Update module docstrings with Artemis branding
- ✅ Update log messages ("Artemis hunt successful!")
- ✅ Create ARTEMIS_README.md

### Phase 2: CLI Enhancement (Future)
- Create `artemis` CLI command
- Shorter invocation: `artemis hunt card-123`
- Progress visualization with hunt metaphor
- Real-time agent status dashboard

### Phase 3: Full Rename (Later)
- Rename `pipeline_orchestrator.py` → `artemis_orchestrator.py`
- Rename directory `.agents/agile/` → `.agents/artemis/`
- Update all documentation
- Migration guide for existing users

---

## Why "Artemis"?

**Artemis** is the Greek goddess of:
- **The Hunt** - Relentlessly pursuing optimal solutions
- **Precision** - Objective scoring and strict quality gates
- **Independence** - Autonomous execution without manual intervention
- **Protection** - Guarding quality through continuous validation

Like Artemis never missing her mark, this pipeline never ships suboptimal code.

---

## FAQs

**Q: Does Artemis replace developers?**
A: No. Artemis is a development pipeline framework. You still need to implement the actual developer agents that write code. Artemis coordinates them, validates their work, and selects the best solution.

**Q: Can I run Artemis with just one developer?**
A: Yes! For simple tasks, Artemis automatically uses a single developer (no arbitration needed). The competitive advantage emerges for medium/complex tasks.

**Q: What if all developers fail validation?**
A: Pipeline stops at validation stage. Card remains in "development" column. You can review validation blockers and address them.

**Q: How long does a full pipeline take?**
A: Depends on task complexity:
- Simple: ~30 seconds (1 developer, skip stages)
- Medium: ~2 minutes (2 developers, full pipeline)
- Complex: ~5 minutes (3 developers + research)

Most time is spent in LLM API calls (developer agents writing code), not Artemis orchestration.

**Q: Can I customize the scoring system?**
A: Yes! Edit `_score_solution()` method in ArtemisOrchestrator to adjust category weights or add new categories.

**Q: Does RAG work across multiple repositories?**
A: Currently RAG is per-repository at `/tmp/rag_db/`. For multi-repo learning, point all orchestrators to a shared RAG database path.

---

## Contributing

Artemis is designed to be extended. Key extension points:

1. **Add new agents** - Create new SKILL.md files in `.agents/` directory
2. **Modify workflow** - Update `WorkflowPlanner` class for different strategies
3. **Enhance scoring** - Add categories to arbitration scoring
4. **Improve RAG** - Add new artifact types or recommendation logic

---

## License

Part of the Salesforce AI Agent Pipeline Demo Project

---

**🏹 Hunt for optimal solutions. Ship with confidence. Learn continuously.**

**Welcome to Artemis.**
