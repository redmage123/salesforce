# Artemis Code Quality Improvement - Priority Matrix

**Date:** October 23, 2025
**Status:** ACTIONABLE
**Total Effort:** 4-5 weeks
**Expected Quality Improvement:** 60-70%

---

## Priority Matrix

Issues ranked by **Impact × Urgency ÷ Effort**

| Rank | Issue | Impact | Effort | Priority Score | Files Affected |
|------|-------|--------|--------|----------------|----------------|
| 1 | Hard-coded absolute paths | HIGH | 1 day | 10.0 | 5 files |
| 2 | Magic numbers (timeouts, limits) | HIGH | 2 days | 7.5 | 30+ locations |
| 3 | God class: WorkflowHandlers (1,141 lines) | HIGH | 5 days | 6.0 | artemis_workflows.py |
| 4 | Long method: run_full_pipeline (231 lines) | HIGH | 3 days | 5.0 | artemis_orchestrator.py |
| 5 | Primitive obsession (config dicts) | MEDIUM | 3 days | 4.0 | 8 files |
| 6 | Duplicate exception handling | MEDIUM | 2 days | 4.0 | 12 files |
| 7 | Missing Factory pattern | MEDIUM | 2 days | 4.0 | artemis_stages.py |
| 8 | Missing Observer pattern | MEDIUM | 2 days | 4.0 | kanban_manager.py |
| 9 | God class: ArtemisOrchestrator (1,111 lines) | MEDIUM | 5 days | 3.0 | artemis_orchestrator.py |
| 10 | Deep nesting (6 levels) | MEDIUM | 2 days | 3.0 | artemis_orchestrator.py |
| 11 | Duplicate RAG storage patterns | MEDIUM | 2 days | 3.0 | 8 files |
| 12 | Long parameter lists (10+ params) | MEDIUM | 2 days | 3.0 | developer_invoker.py |
| 13 | Missing Builder pattern | LOW | 2 days | 2.0 | developer_invoker.py |
| 14 | Missing Decorator pattern | LOW | 1 day | 2.0 | llm_client.py |
| 15 | Missing Facade pattern | LOW | 3 days | 1.5 | artemis_workflows.py |
| 16 | Dead code (118 lines) | LOW | 1 day | 1.5 | developer_invoker.py |
| 17 | Missing Template Method pattern | LOW | 2 days | 1.5 | pipeline_stages.py |
| 18 | Inconsistent naming | LOW | 1 day | 1.0 | All files |

---

## Week-by-Week Implementation Plan

### 🚀 Week 1: Quick Wins (HIGH PRIORITY)

**Goal:** Fix critical issues with minimal effort

#### Day 1: Hard-coded Paths ⚡ CRITICAL
**Effort:** 4 hours
**Impact:** HIGH (breaks on other systems)
**Files:** 5

```python
# Before
KANBAN_FILE = "/home/bbrelin/src/repos/salesforce/.agents/agile/kanban_board.json"

# After
import os
REPO_ROOT = os.environ.get("ARTEMIS_REPO_ROOT", os.getcwd())
KANBAN_FILE = os.path.join(REPO_ROOT, ".agents/agile/kanban_board.json")
```

**Action Items:**
- [ ] Extract to constants.py
- [ ] Use environment variables or relative paths
- [ ] Update all 5 files
- [ ] Test on different systems

#### Days 1-2: Magic Numbers → Constants
**Effort:** 1 day
**Impact:** HIGH (maintainability)
**Files:** 30+ locations

```python
# Before
time.sleep(5)
if retry_count > 3:
if len(prompt) > 8000:

# After (in constants.py)
DEFAULT_RETRY_INTERVAL_SECONDS = 5
MAX_RETRY_ATTEMPTS = 3
MAX_LLM_PROMPT_LENGTH = 8000

# Usage
time.sleep(DEFAULT_RETRY_INTERVAL_SECONDS)
if retry_count > MAX_RETRY_ATTEMPTS:
if len(prompt) > MAX_LLM_PROMPT_LENGTH:
```

**Action Items:**
- [ ] Create constants.py
- [ ] Group constants by category
- [ ] Replace all magic numbers
- [ ] Document each constant

#### Days 3-5: Strategy Pattern (run_full_pipeline)
**Effort:** 3 days
**Impact:** HIGH (231 lines → 15 lines)
**Files:** artemis_orchestrator.py, new pipeline_strategies.py

**Action Items:**
- [ ] Create PipelineStrategy interface
- [ ] Implement StandardPipelineStrategy
- [ ] Implement FastPipelineStrategy
- [ ] Implement ParallelPipelineStrategy
- [ ] Update orchestrator to use strategy
- [ ] Write unit tests
- [ ] Write integration tests

**Success Criteria:**
- ✅ run_full_pipeline() reduced to < 20 lines
- ✅ All existing tests pass
- ✅ New strategies are testable

---

### 📦 Week 2: God Class Refactoring (HIGH PRIORITY)

**Goal:** Break down WorkflowHandlers god class

#### Days 1-3: Split WorkflowHandlers
**Effort:** 3 days
**Impact:** HIGH (1,141 lines → 8 classes)
**Files:** artemis_workflows.py → 8 new files

**New Class Structure:**
```
artemis_workflows.py (1,141 lines)
    ↓
workflow_coordinator.py (150 lines)       - Orchestration only
project_workflow.py (140 lines)           - Project analysis workflow
architecture_workflow.py (140 lines)      - Architecture workflow
development_workflow.py (150 lines)       - Development workflow
review_workflow.py (140 lines)            - Code review workflow
validation_workflow.py (140 lines)        - Validation workflow
integration_workflow.py (140 lines)       - Integration workflow
testing_workflow.py (140 lines)           - Testing workflow
```

**Action Items:**
- [ ] Extract ProjectWorkflow class
- [ ] Extract ArchitectureWorkflow class
- [ ] Extract DevelopmentWorkflow class
- [ ] Extract ReviewWorkflow class
- [ ] Extract ValidationWorkflow class
- [ ] Extract IntegrationWorkflow class
- [ ] Extract TestingWorkflow class
- [ ] Create WorkflowCoordinator (delegates to workflows)
- [ ] Update imports
- [ ] Write unit tests for each workflow

#### Days 4-5: Factory Pattern (Stage Creation)
**Effort:** 2 days
**Impact:** MEDIUM (easier extensibility)
**Files:** New artemis_stage_factory.py

**Action Items:**
- [ ] Create StageFactory class
- [ ] Register all 8 stage types
- [ ] Update orchestrator to use factory
- [ ] Write unit tests
- [ ] Document factory usage

---

### 🔍 Week 3: Code Duplication + Primitives (MEDIUM PRIORITY)

**Goal:** Eliminate duplicate code, replace primitive obsession

#### Days 1-2: Extract Exception Handling
**Effort:** 2 days
**Impact:** MEDIUM (-200 lines duplication)
**Files:** 12 files

```python
# Before (duplicated 12 times)
try:
    result = stage.execute()
    if result.get("success"):
        self.rag.store_artifact(...)
        return {"success": True}
    else:
        return {"success": False, "error": ...}
except Exception as e:
    self.messenger.notify_error(...)
    return {"success": False, "error": str(e)}

# After (single location)
from error_handling import execute_with_error_handling

result = execute_with_error_handling(
    stage.execute,
    on_success=lambda r: self.rag.store_artifact(...),
    on_error=lambda e: self.messenger.notify_error(...)
)
```

**Action Items:**
- [ ] Create error_handling.py
- [ ] Extract common exception patterns
- [ ] Replace 12 duplicated blocks
- [ ] Write unit tests

#### Days 2-3: Replace Primitive Obsession
**Effort:** 2 days
**Impact:** MEDIUM (type safety)
**Files:** 8 files

```python
# Before (primitive dict)
config = {
    "llm_provider": "openai",
    "llm_model": "gpt-5",
    "max_tokens": 8000,
    "temperature": 0.7
}

# After (dataclass)
from dataclasses import dataclass

@dataclass
class LLMConfig:
    provider: str
    model: str
    max_tokens: int = 8000
    temperature: float = 0.7

    def validate(self):
        if self.max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be 0-2")

config = LLMConfig(provider="openai", model="gpt-5")
```

**Action Items:**
- [ ] Create config_models.py
- [ ] Define LLMConfig dataclass
- [ ] Define PipelineConfig dataclass
- [ ] Define DeveloperConfig dataclass
- [ ] Replace dict configs with dataclasses
- [ ] Add validation methods

#### Days 4-5: Observer Pattern (Kanban)
**Effort:** 2 days
**Impact:** MEDIUM (real-time updates)
**Files:** kanban_manager.py, new kanban_observer.py

**Action Items:**
- [ ] Create KanbanObserver interface
- [ ] Update KanbanBoard as Subject
- [ ] Implement RAGObserver
- [ ] Implement MetricsObserver
- [ ] Implement NotificationObserver
- [ ] Write unit tests

---

### 🎨 Week 4: Design Patterns + Polish (MEDIUM PRIORITY)

**Goal:** Add remaining design patterns

#### Days 1-2: Builder Pattern
**Effort:** 2 days
**Impact:** MEDIUM (developer UX)
**Files:** developer_invoker.py, new developer_builder.py

**Action Items:**
- [ ] Create DeveloperBuilder class
- [ ] Create DeveloperConfig dataclass
- [ ] Update invoke_developer() to accept config
- [ ] Write unit tests
- [ ] Update documentation

#### Days 2-3: Template Method Pattern
**Effort:** 2 days
**Impact:** MEDIUM (-200 lines duplication)
**Files:** pipeline_stages.py, new pipeline_stage_base.py

**Action Items:**
- [ ] Create PipelineStageTemplate base class
- [ ] Refactor ProjectAnalysisStage
- [ ] Refactor ArchitectureStage
- [ ] Refactor DevelopmentStage
- [ ] Refactor CodeReviewStage
- [ ] Refactor ValidationStage
- [ ] Refactor IntegrationStage
- [ ] Refactor TestingStage
- [ ] Write unit tests

#### Day 4: Decorator Pattern
**Effort:** 1 day
**Impact:** LOW (LLM features)
**Files:** llm_client.py, new llm_decorators.py

**Action Items:**
- [ ] Create LLM decorators (Caching, RateLimiting, Retry, Logging)
- [ ] Update LLM client creation
- [ ] Write unit tests

#### Day 5: Flatten Deep Nesting
**Effort:** 1 day
**Impact:** MEDIUM (readability)
**Files:** artemis_orchestrator.py, rag_agent.py

```python
# Before (6 levels)
if condition1:
    if condition2:
        if condition3:
            if condition4:
                if condition5:
                    if condition6:
                        do_work()

# After (early returns, guard clauses)
if not condition1:
    return
if not condition2:
    return
if not condition3:
    return
if not condition4:
    return
if not condition5:
    return
if not condition6:
    return

do_work()
```

**Action Items:**
- [ ] Identify all 6+ level nesting
- [ ] Use early returns
- [ ] Extract methods
- [ ] Write unit tests

---

### 🚢 Week 5: Testing + Deployment (LOW PRIORITY)

**Goal:** Ensure quality, deploy gradually

#### Days 1-2: Comprehensive Testing
**Effort:** 2 days
**Impact:** HIGH (quality assurance)

**Test Coverage Targets:**
- Unit tests: 80% coverage
- Integration tests: Key workflows
- Performance tests: No regression

**Action Items:**
- [ ] Write unit tests for all new patterns
- [ ] Write integration tests for full pipeline
- [ ] Write performance benchmarks
- [ ] Run test suite on CI/CD
- [ ] Fix any test failures

#### Days 3-4: Documentation + Migration Guide
**Effort:** 2 days
**Impact:** MEDIUM (developer onboarding)

**Action Items:**
- [ ] Update STANDALONE_USAGE.md
- [ ] Create DESIGN_PATTERNS_GUIDE.md
- [ ] Create MIGRATION_GUIDE.md
- [ ] Update all docstrings
- [ ] Record demo video

#### Day 5: Gradual Rollout
**Effort:** 1 day
**Impact:** HIGH (production stability)

**Rollout Strategy:**
- 10% of cards (canary)
- 50% of cards (gradual)
- 100% of cards (full)

**Action Items:**
- [ ] Deploy to staging
- [ ] Test with 10% of cards
- [ ] Monitor metrics (performance, errors)
- [ ] Deploy to 50%
- [ ] Monitor for 24 hours
- [ ] Deploy to 100%
- [ ] Monitor for 1 week

---

## Cleanup Tasks (Ongoing)

### Dead Code Removal
**Effort:** 1 day
**Impact:** LOW (reduce bloat)

**Files:**
- developer_invoker.py (lines 150-268)
- Other unused functions

**Action Items:**
- [ ] Run dead code detection
- [ ] Verify code is truly unused
- [ ] Remove dead code
- [ ] Run tests to confirm

### Inconsistent Naming
**Effort:** 1 day
**Impact:** LOW (readability)

**Patterns to Fix:**
- snake_case vs camelCase
- Abbreviations (cfg vs config)
- Inconsistent prefixes (_private vs private)

**Action Items:**
- [ ] Define naming conventions
- [ ] Update Python Style Guide
- [ ] Refactor inconsistent names
- [ ] Update tests

---

## Success Metrics

### Code Quality (Before → After)

| Metric | Before | Target | Improvement |
|--------|--------|--------|-------------|
| Total Lines of Code | 17,257 | 12,000 | -30% |
| Largest File | 1,141 lines | 300 lines | -74% |
| Longest Method | 231 lines | 50 lines | -78% |
| Cyclomatic Complexity (avg) | 12.5 | 7.5 | -40% |
| Code Duplication | 8.2% | 2.0% | -76% |
| Test Coverage | 45% | 80% | +78% |
| God Classes | 3 | 0 | -100% |
| Magic Numbers | 30+ | 0 | -100% |
| Hard-coded Paths | 5 | 0 | -100% |

### Developer Experience (Before → After)

| Metric | Before | Target | Improvement |
|--------|--------|--------|-------------|
| Setup Lines | 50+ | 1-5 | -90% |
| Time to Add Feature | 4 hours | 2 hours | -50% |
| Bug Fix Time | 3 hours | 2 hours | -33% |
| New Developer Onboarding | 2 days | 1 day | -50% |

### Performance (Before → After)

| Metric | Before | Target | Acceptable Range |
|--------|--------|--------|------------------|
| Pipeline Execution Time | 180s | 180s | ±5% |
| Memory Usage | 512 MB | 460 MB | -10% |
| Startup Time | 2.5s | 2.5s | ±10% |

---

## Risk Assessment

### HIGH RISK (Mitigation Required)

**Risk:** Breaking existing functionality
- **Mitigation:** Comprehensive test suite before refactoring
- **Mitigation:** Feature flags for new patterns
- **Mitigation:** Gradual rollout (10% → 50% → 100%)

**Risk:** Performance regression
- **Mitigation:** Benchmark before/after each change
- **Mitigation:** Profile code to identify bottlenecks
- **Mitigation:** Rollback if >5% performance degradation

### MEDIUM RISK (Monitor)

**Risk:** Team learning curve for design patterns
- **Mitigation:** Documentation with examples
- **Mitigation:** Code review sessions
- **Mitigation:** Pair programming for first implementations

**Risk:** Over-engineering simple features
- **Mitigation:** Apply patterns only where beneficial
- **Mitigation:** YAGNI principle (You Aren't Gonna Need It)
- **Mitigation:** Code review approval required

### LOW RISK

**Risk:** Merge conflicts during refactoring
- **Mitigation:** Small, focused PRs
- **Mitigation:** Communicate with team
- **Mitigation:** Daily merges from main

---

## Approval Checklist

Before starting implementation:

- [ ] **User Approval:** User has approved this priority matrix
- [ ] **Resource Allocation:** 4-5 weeks dedicated time available
- [ ] **Test Infrastructure:** CI/CD pipeline ready
- [ ] **Rollback Plan:** Can revert to previous version
- [ ] **Team Communication:** All developers aware of changes
- [ ] **Documentation:** Migration guide prepared
- [ ] **Success Criteria:** Metrics defined and measurable

---

## Next Steps

**Awaiting user decision:**

1. **Option A: Full Implementation** (4-5 weeks)
   - Implement all improvements in priority order
   - Expected: 60-70% quality improvement

2. **Option B: Quick Wins Only** (1 week)
   - Implement Week 1 items only (hard-coded paths, magic numbers, strategy pattern)
   - Expected: 30-40% quality improvement

3. **Option C: Incremental** (2 weeks, revisit later)
   - Implement Weeks 1-2 (quick wins + god class refactoring)
   - Expected: 45-55% quality improvement
   - Revisit remaining items later

**Recommended:** Option A (Full Implementation) for maximum long-term benefit.

---

**Created:** October 23, 2025
**Status:** ⏸️  AWAITING USER APPROVAL
**Next Action:** User selects Option A, B, or C
**Estimated Start Date:** Upon approval
**Estimated Completion:** 4-5 weeks from start
