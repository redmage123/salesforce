# Artemis Codebase Refactoring Plan

**Date:** October 23, 2025
**Status:** Ready for Implementation
**Priority:** HIGH

---

## Overview

Based on the code quality audit, this document outlines the refactoring plan to eliminate code smells, apply design patterns, and improve maintainability.

---

## Phase 1: Critical - Eliminate Code Duplication (IMMEDIATE)

### Task 1.1: Consolidate Services Files ✅

**Problem:** `artemis_services.py` and `pipeline_services.py` contain similar classes

**Current Usage:**
```python
# artemis_stages.py imports from artemis_services
from artemis_services import TestRunner, FileManager

# pipeline_stages.py imports from pipeline_services
from pipeline_services import TestRunner, FileManager

# artemis_orchestrator_solid.py imports from artemis_services
from artemis_services import PipelineLogger, TestRunner
```

**Action Plan:**
1. ✅ **Keep:** `artemis_services.py` (newer, better structured)
2. ✅ **Update:** `pipeline_stages.py` to import from `artemis_services`
3. ✅ **Deprecate:** `pipeline_services.py` with warning
4. ✅ **Delete:** `pipeline_services.py` (after verification)

**Files to Modify:**
- `/home/bbrelin/src/repos/salesforce/.agents/agile/pipeline_stages.py` (line 21)

**Risk:** 🟢 LOW (simple import change)
**Effort:** 15 minutes
**Impact:** Removes 150+ duplicate lines

---

### Task 1.2: Deprecate pipeline_stages.py ✅

**Problem:** Duplicate stage implementations in `artemis_stages.py` and `pipeline_stages.py`

**Current Usage:**
```python
# pipeline_orchestrator.py uses pipeline_stages
from pipeline_stages import (
    ProjectAnalysisStage,
    ArchitectureStage,
    # ... etc
)

# artemis_orchestrator_solid.py uses artemis_stages
from artemis_stages import (
    ProjectAnalysisStage,
    ArchitectureStage,
    # ... etc
)
```

**Action Plan:**
1. ✅ **Mark deprecated:** Add deprecation warning to `pipeline_stages.py`
2. ✅ **Add comment:** Explain migration path
3. ✅ **Future:** Remove in next major version

**Deprecation Notice:**
```python
# pipeline_stages.py (top of file)
import warnings

warnings.warn(
    "pipeline_stages.py is deprecated and will be removed in Artemis 3.0. "
    "Please use artemis_stages.py instead. "
    "See REFACTORING_PLAN.md for migration guide.",
    DeprecationWarning,
    stacklevel=2
)
```

**Risk:** 🟢 LOW (non-breaking)
**Effort:** 10 minutes
**Impact:** Clear migration path for users

---

### Task 1.3: Deprecate pipeline_stage_interface.py ✅

**Problem:** Duplicate interfaces in `artemis_stage_interface.py` and `pipeline_stage_interface.py`

**Action Plan:**
1. ✅ Add deprecation warning
2. ✅ Keep both temporarily for backward compatibility
3. ✅ Remove in next major version

**Risk:** 🟢 LOW
**Effort:** 5 minutes

---

### Task 1.4: Deprecate pipeline_orchestrator.py ✅

**Problem:** Legacy orchestrator (2,200 lines) replaced by `artemis_orchestrator_solid.py` (600 lines)

**Action Plan:**
1. ✅ Add deprecation warning
2. ✅ Add migration guide in comments
3. ✅ Mark for removal in Artemis 3.0

**Risk:** 🟢 LOW (replacement exists)
**Effort:** 10 minutes

---

## Phase 2: High Priority - Apply Design Patterns (THIS SPRINT)

### Task 2.1: Builder Pattern for Card Creation 🎯

**Problem:** 15-parameter method signature
```python
def create_card(
    self,
    task_id: str,
    title: str,
    description: str,
    priority: str = "medium",
    labels: List[str] = None,
    size: str = "medium",
    story_points: int = 3,
    assigned_agents: List[str] = None,
    acceptance_criteria: List[Dict] = None,
    # ... many more
) -> Dict:
```

**Solution:** Builder Pattern

**Implementation:**
```python
class CardBuilder:
    """
    Builder pattern for creating Kanban cards

    Usage:
        card = (CardBuilder("TASK-001", "Add feature")
            .with_priority("high")
            .with_labels(["feature", "backend"])
            .with_story_points(8)
            .with_assigned_agents(["developer-a"])
            .build())
    """

    def __init__(self, task_id: str, title: str):
        """Initialize with required fields only"""
        self._card = {
            'task_id': task_id,
            'title': title,
            'description': '',
            # Set defaults
            'priority': 'medium',
            'labels': [],
            'size': 'medium',
            'story_points': 3,
            'assigned_agents': [],
            'acceptance_criteria': [],
            'blocked': False,
            'blocked_reason': None,
        }

    def with_description(self, description: str) -> 'CardBuilder':
        """Set description"""
        self._card['description'] = description
        return self

    def with_priority(self, priority: str) -> 'CardBuilder':
        """Set priority: high, medium, low"""
        if priority not in ['high', 'medium', 'low']:
            raise ValueError(f"Invalid priority: {priority}")
        self._card['priority'] = priority
        return self

    def with_labels(self, labels: List[str]) -> 'CardBuilder':
        """Set labels"""
        self._card['labels'] = labels
        return self

    def with_size(self, size: str) -> 'CardBuilder':
        """Set size: small, medium, large"""
        if size not in ['small', 'medium', 'large']:
            raise ValueError(f"Invalid size: {size}")
        self._card['size'] = size
        return self

    def with_story_points(self, points: int) -> 'CardBuilder':
        """Set story points (Fibonacci: 1, 2, 3, 5, 8, 13)"""
        if points not in [1, 2, 3, 5, 8, 13]:
            raise ValueError(f"Invalid story points: {points}. Must be Fibonacci number.")
        self._card['story_points'] = points
        return self

    def with_assigned_agents(self, agents: List[str]) -> 'CardBuilder':
        """Set assigned agents"""
        self._card['assigned_agents'] = agents
        return self

    def with_acceptance_criteria(self, criteria: List[Dict]) -> 'CardBuilder':
        """Set acceptance criteria"""
        self._card['acceptance_criteria'] = criteria
        return self

    def blocked(self, reason: str) -> 'CardBuilder':
        """Mark card as blocked"""
        self._card['blocked'] = True
        self._card['blocked_reason'] = reason
        return self

    def build(self) -> Dict:
        """Build and return the card"""
        # Add timestamps and IDs
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        card_id = f"card-{timestamp}"

        self._card.update({
            'card_id': card_id,
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'moved_to_current_column_at': datetime.utcnow().isoformat() + 'Z',
            'current_column': 'backlog',
            'test_status': {
                'unit_tests_written': False,
                'unit_tests_passing': False,
                'integration_tests_written': False,
                'integration_tests_passing': False,
                'test_coverage_percent': 0
            },
            'definition_of_done': {
                'code_complete': False,
                'tests_passing': False,
                'code_reviewed': False,
                'documentation_updated': False,
                'deployed_to_production': False
            },
            'history': [
                {
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'action': 'created',
                    'column': 'backlog',
                    'agent': 'system',
                    'comment': 'Card created'
                }
            ]
        })

        return self._card


# Update KanbanBoard class
class KanbanBoard:
    def create_card_with_builder(self) -> CardBuilder:
        """
        Create card using Builder pattern

        Usage:
            card = (board.create_card_with_builder()
                .with_title("Add feature")
                .with_priority("high")
                .build())
        """
        return CardBuilder("", "")

    def add_card(self, card: Dict) -> Dict:
        """Add pre-built card to backlog"""
        backlog = self._get_column("backlog")
        if backlog:
            backlog['cards'].append(card)
            self._save_board()
        return card

    # Keep old method for backward compatibility
    def create_card(self, task_id: str, title: str, **kwargs) -> Dict:
        """
        DEPRECATED: Use create_card_with_builder() instead

        Legacy method maintained for backward compatibility.
        Will be removed in Artemis 3.0.
        """
        warnings.warn(
            "create_card() is deprecated. Use create_card_with_builder() instead.",
            DeprecationWarning,
            stacklevel=2
        )

        # Use builder internally
        builder = CardBuilder(task_id, title)

        if 'description' in kwargs:
            builder.with_description(kwargs['description'])
        if 'priority' in kwargs:
            builder.with_priority(kwargs['priority'])
        # ... map all kwargs

        card = builder.build()
        return self.add_card(card)
```

**Benefits:**
- ✅ Fluent API (easy to read and write)
- ✅ Reduced from 15 parameters to 2 required
- ✅ Type-safe with validation
- ✅ Backward compatible (keep old method)
- ✅ Easier testing

**Risk:** 🟢 LOW (backward compatible)
**Effort:** 3 hours
**Impact:** Major API improvement

---

### Task 2.2: Factory Pattern for Stage Creation 🎯

**Problem:** Repetitive stage creation with many parameters

**Current:**
```python
def _create_default_stages(self) -> List[PipelineStage]:
    return [
        ProjectAnalysisStage(self.board, self.messenger, self.rag, self.logger),
        ArchitectureStage(self.board, self.messenger, self.rag, self.logger),
        DependencyValidationStage(self.board, self.messenger, self.logger),
        DevelopmentStage(self.board, self.rag, self.logger),
        CodeReviewStage(self.messenger, self.rag, self.logger),
        ValidationStage(self.board, self.test_runner, self.logger),
        IntegrationStage(self.board, self.messenger, self.rag, self.test_runner, self.logger),
        TestingStage(self.board, self.messenger, self.rag, self.test_runner, self.logger)
    ]
```

**Solution:** Abstract Factory Pattern

**Implementation:**
```python
class StageFactory:
    """
    Factory for creating pipeline stages

    Single Responsibility: Create stages with proper dependencies
    Open/Closed: Easy to add new stage types
    """

    def __init__(
        self,
        board: KanbanBoard,
        messenger: AgentMessenger,
        rag: RAGAgent,
        logger: LoggerInterface,
        test_runner: TestRunner
    ):
        """Initialize factory with dependencies"""
        self.board = board
        self.messenger = messenger
        self.rag = rag
        self.logger = logger
        self.test_runner = test_runner

        # Registry of stage creators
        self._stage_creators = {
            'project_analysis': self._create_project_analysis,
            'architecture': self._create_architecture,
            'dependencies': self._create_dependencies,
            'development': self._create_development,
            'code_review': self._create_code_review,
            'validation': self._create_validation,
            'integration': self._create_integration,
            'testing': self._create_testing,
        }

    def create_stage(self, stage_type: str) -> PipelineStage:
        """
        Create a single stage by type

        Args:
            stage_type: Stage type name

        Returns:
            PipelineStage instance

        Raises:
            ValueError: If stage type unknown
        """
        creator = self._stage_creators.get(stage_type)
        if not creator:
            raise ValueError(f"Unknown stage type: {stage_type}")

        return creator()

    def create_all_stages(self) -> List[PipelineStage]:
        """Create all default stages in order"""
        stage_types = [
            'project_analysis',
            'architecture',
            'dependencies',
            'development',
            'code_review',
            'validation',
            'integration',
            'testing',
        ]

        return [self.create_stage(stage_type) for stage_type in stage_types]

    def create_custom_pipeline(self, stage_types: List[str]) -> List[PipelineStage]:
        """Create custom pipeline with specific stages"""
        return [self.create_stage(stage_type) for stage_type in stage_types]

    # Private stage creators
    def _create_project_analysis(self) -> ProjectAnalysisStage:
        return ProjectAnalysisStage(
            self.board,
            self.messenger,
            self.rag,
            self.logger
        )

    def _create_architecture(self) -> ArchitectureStage:
        return ArchitectureStage(
            self.board,
            self.messenger,
            self.rag,
            self.logger
        )

    def _create_dependencies(self) -> DependencyValidationStage:
        return DependencyValidationStage(
            self.board,
            self.messenger,
            self.logger
        )

    def _create_development(self) -> DevelopmentStage:
        return DevelopmentStage(
            self.board,
            self.rag,
            self.logger
        )

    def _create_code_review(self) -> CodeReviewStage:
        return CodeReviewStage(
            self.messenger,
            self.rag,
            self.logger
        )

    def _create_validation(self) -> ValidationStage:
        return ValidationStage(
            self.board,
            self.test_runner,
            self.logger
        )

    def _create_integration(self) -> IntegrationStage:
        return IntegrationStage(
            self.board,
            self.messenger,
            self.rag,
            self.test_runner,
            self.logger
        )

    def _create_testing(self) -> TestingStage:
        return TestingStage(
            self.board,
            self.messenger,
            self.rag,
            self.test_runner,
            self.logger
        )


# Update ArtemisOrchestrator
class ArtemisOrchestrator:
    def __init__(
        self,
        card_id: str,
        board: KanbanBoard,
        messenger: AgentMessenger,
        rag: RAGAgent,
        config: Optional[ConfigurationAgent] = None,
        logger: Optional[LoggerInterface] = None,
        test_runner: Optional[TestRunner] = None,
        stages: Optional[List[PipelineStage]] = None,
        supervisor: Optional[SupervisorAgent] = None,
        enable_supervision: bool = True
    ):
        self.card_id = card_id
        self.board = board
        self.messenger = messenger
        self.rag = rag
        self.config = config or get_config(verbose=True)
        self.logger = logger or PipelineLogger(verbose=True)
        self.test_runner = test_runner or TestRunner()

        # Create stage factory
        self.stage_factory = StageFactory(
            self.board,
            self.messenger,
            self.rag,
            self.logger,
            self.test_runner
        )

        # Create stages using factory
        if stages is None:
            self.stages = self.stage_factory.create_all_stages()
        else:
            self.stages = stages

        # ... rest of init

    # Remove _create_default_stages() - replaced by factory
```

**Benefits:**
- ✅ Single place to manage stage creation
- ✅ Easy to add new stage types
- ✅ Custom pipelines without code changes
- ✅ Better testability

**Risk:** 🟢 LOW
**Effort:** 2 hours
**Impact:** Cleaner orchestrator code

---

### Task 2.3: Extract Long Methods 🎯

**Target Methods:**
1. `ArtemisOrchestrator.run_full_pipeline()` (~200 lines)
2. `KanbanBoard.move_card()` (~80 lines)
3. `RAGAgent.store_artifact()` (~70 lines)

**Refactoring Pattern:** Extract Method

**Example: run_full_pipeline()**

**Before:**
```python
def run_full_pipeline(self, max_retries: int = 2) -> Dict:
    # 200 lines of mixed concerns
    self.logger.log("Starting...")
    card, _ = self.board._find_card(self.card_id)
    planner = WorkflowPlanner(card)
    workflow_plan = planner.create_workflow_plan()
    # ... 150 more lines
    return report
```

**After:**
```python
def run_full_pipeline(self, max_retries: int = 2) -> Dict:
    """
    Run complete pipeline with retry logic

    Orchestrates: initialization → execution → reporting → finalization
    """
    # High-level orchestration (< 50 lines)
    card, workflow_plan = self._initialize_pipeline()
    stage_results = self._execute_pipeline_stages(card, workflow_plan, max_retries)
    report = self._generate_pipeline_report(card, workflow_plan, stage_results)
    self._finalize_pipeline(report)
    return report

def _initialize_pipeline(self) -> Tuple[Dict, Dict]:
    """Initialize pipeline: load card, create workflow plan"""
    self.logger.log("=" * 60, "INFO")
    self.logger.log("🏹 ARTEMIS - STARTING AUTONOMOUS HUNT", "STAGE")
    self.logger.log("=" * 60, "INFO")

    card, _ = self.board._find_card(self.card_id)
    if not card:
        raise KanbanCardNotFoundError(
            f"Card {self.card_id} not found",
            context={"card_id": self.card_id}
        )

    planner = WorkflowPlanner(card)
    workflow_plan = planner.create_workflow_plan()

    self._notify_pipeline_start(card, workflow_plan)

    return card, workflow_plan

def _execute_pipeline_stages(
    self,
    card: Dict,
    workflow_plan: Dict,
    max_retries: int
) -> Dict:
    """Execute all pipeline stages with retry logic"""
    stages_to_run = self._filter_stages_by_plan(workflow_plan)
    stage_results = {}
    all_retry_history = []

    retry_count = 0
    while retry_count <= max_retries:
        context = {"card": card, "workflow_plan": workflow_plan}

        for i, stage in enumerate(stages_to_run, 1):
            stage_name = stage.get_stage_name()

            # Skip stages before development on retry
            if retry_count > 0 and stage_name not in ['development', 'code_review']:
                continue

            self.logger.log(f"📋 STAGE {i}/{len(stages_to_run)}: {stage_name.upper()}", "STAGE")

            result = self._execute_single_stage(stage, stage_name, card, context)
            stage_results[stage_name] = result
            context.update(result)

            # Handle code review failures
            if stage_name == 'code_review' and result.get('status') == 'FAIL':
                if retry_count < max_retries:
                    all_retry_history.append(self._record_retry(retry_count, result))
                    break  # Retry from development

        # Check if we should continue
        if self._should_exit_retry_loop(stage_results, max_retries, retry_count):
            break

        retry_count += 1

    stage_results['retry_history'] = all_retry_history
    stage_results['total_retries'] = retry_count

    return stage_results

def _execute_single_stage(
    self,
    stage: PipelineStage,
    stage_name: str,
    card: Dict,
    context: Dict
) -> Dict:
    """Execute a single stage with supervision"""
    try:
        if self.enable_supervision and self.supervisor:
            return self.supervisor.execute_with_supervision(
                stage, stage_name, card, context
            )
        else:
            return stage.execute(card, context)
    except Exception as e:
        raise wrap_exception(
            e,
            PipelineStageError,
            f"Stage {stage_name} execution failed",
            context={"card_id": self.card_id, "stage": stage_name}
        )

def _generate_pipeline_report(
    self,
    card: Dict,
    workflow_plan: Dict,
    stage_results: Dict
) -> Dict:
    """Generate comprehensive pipeline report"""
    final_status = self._determine_final_status(stage_results)

    self._log_final_status(final_status)

    supervisor_stats = None
    if self.enable_supervision and self.supervisor:
        self.supervisor.print_health_report()
        supervisor_stats = self.supervisor.get_statistics()

    report = {
        "card_id": self.card_id,
        "workflow_plan": workflow_plan,
        "stages": stage_results,
        "status": final_status,
        "retry_history": stage_results.get('retry_history'),
        "total_retries": stage_results.get('total_retries', 0),
        "supervisor_statistics": supervisor_stats
    }

    return report

def _finalize_pipeline(self, report: Dict) -> None:
    """Finalize pipeline: save report, cleanup"""
    report_path = Path("/tmp") / f"pipeline_full_report_{self.card_id}.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    if self.enable_supervision and self.supervisor:
        cleaned = self.supervisor.cleanup_zombie_processes()
        if cleaned > 0:
            self.logger.log(f"🧹 Cleaned up {cleaned} zombie processes", "INFO")

# Helper methods (< 20 lines each)
def _determine_final_status(self, stage_results: Dict) -> str:
    if stage_results.get('pipeline_status') == 'FAILED_CODE_REVIEW':
        return "FAILED_CODE_REVIEW"
    return "COMPLETED_SUCCESSFULLY"

def _log_final_status(self, status: str) -> None:
    if status == "FAILED_CODE_REVIEW":
        self.logger.log("=" * 60, "ERROR")
        self.logger.log("❌ PIPELINE FAILED - CODE REVIEW ISSUES", "ERROR")
        self.logger.log("=" * 60, "ERROR")
    else:
        self.logger.log("=" * 60, "INFO")
        self.logger.log("🎉 ARTEMIS HUNT SUCCESSFUL!", "SUCCESS")
        self.logger.log("=" * 60, "INFO")

def _should_exit_retry_loop(
    self,
    stage_results: Dict,
    max_retries: int,
    retry_count: int
) -> bool:
    code_review_result = stage_results.get('code_review', {})
    if code_review_result.get('status') == 'PASS':
        return True
    if stage_results.get('pipeline_status') == 'FAILED_CODE_REVIEW':
        return True
    return False

def _record_retry(self, retry_count: int, result: Dict) -> Dict:
    return {
        'attempt': retry_count + 1,
        'review_result': result,
        'critical_issues': result.get('total_critical_issues', 0),
        'high_issues': result.get('total_high_issues', 0)
    }
```

**Benefits:**
- ✅ Each method < 50 lines
- ✅ Single Responsibility per method
- ✅ Easier to test
- ✅ Better readability
- ✅ Easier to modify

**Risk:** 🟢 LOW (pure refactoring)
**Effort:** 4 hours
**Impact:** Major readability improvement

---

## Phase 3: Medium Priority - Configuration & Portability

### Task 3.1: Replace Hardcoded Paths

**Create:** `artemis_config.py`

```python
"""
Artemis Configuration
Centralized configuration management with environment variable support
"""

import os
from pathlib import Path
from typing import Optional

class ArtemisConfig:
    """Centralized configuration for Artemis"""

    # Base directories
    ARTEMIS_HOME = os.getenv(
        "ARTEMIS_HOME",
        str(Path.home() / ".artemis")
    )

    # Data directories
    DATA_DIR = os.getenv(
        "ARTEMIS_DATA_DIR",
        str(Path(ARTEMIS_HOME) / "data")
    )

    TEMP_DIR = os.getenv(
        "ARTEMIS_TEMP_DIR",
        "/tmp/artemis"
    )

    # Kanban board
    BOARD_PATH = os.getenv(
        "ARTEMIS_BOARD_PATH",
        str(Path(DATA_DIR) / "kanban_board.json")
    )

    # Agent messages
    MESSAGE_DIR = os.getenv(
        "ARTEMIS_MESSAGE_DIR",
        str(Path(DATA_DIR) / "messages")
    )

    # ADR output
    ADR_DIR = os.getenv(
        "ARTEMIS_ADR_DIR",
        str(Path(TEMP_DIR) / "adr")
    )

    # RAG database
    RAG_DB_PATH = os.getenv(
        "ARTEMIS_RAG_DB_PATH",
        str(Path(DATA_DIR) / "rag_db")
    )

    @classmethod
    def ensure_directories(cls):
        """Create all required directories"""
        for dir_path in [
            cls.DATA_DIR,
            cls.TEMP_DIR,
            cls.MESSAGE_DIR,
            cls.ADR_DIR,
            cls.RAG_DB_PATH
        ]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_board_path(cls) -> str:
        """Get kanban board path"""
        return cls.BOARD_PATH

    @classmethod
    def get_message_dir(cls) -> str:
        """Get message directory"""
        return cls.MESSAGE_DIR
```

**Update files to use config:**
- `kanban_manager.py`: Replace `BOARD_PATH` constant
- `agent_messenger.py`: Replace `message_dir` default
- All files with hardcoded `/tmp` paths

**Risk:** 🟡 MEDIUM (affects multiple files)
**Effort:** 2 hours
**Impact:** Better portability

---

## Implementation Order

### Sprint 1 (This Week)

1. ✅ **Day 1:** Add deprecation warnings to duplicate files
2. ✅ **Day 2:** Implement Builder Pattern for Card creation
3. ✅ **Day 3:** Implement Factory Pattern for Stage creation
4. ✅ **Day 4:** Extract long methods in ArtemisOrchestrator
5. ✅ **Day 5:** Testing and verification

### Sprint 2 (Next Week)

6. ✅ **Day 1-2:** Replace hardcoded paths with configuration
7. ✅ **Day 3:** Update imports to remove duplicates
8. ✅ **Day 4-5:** Testing and documentation

---

## Testing Strategy

### Unit Tests

```python
# test_card_builder.py
def test_card_builder_minimal():
    card = CardBuilder("TASK-001", "Add feature").build()
    assert card['task_id'] == "TASK-001"
    assert card['title'] == "Add feature"
    assert card['priority'] == "medium"  # default

def test_card_builder_full():
    card = (CardBuilder("TASK-001", "Add feature")
        .with_priority("high")
        .with_story_points(8)
        .with_labels(["feature", "backend"])
        .build())

    assert card['priority'] == "high"
    assert card['story_points'] == 8
    assert "feature" in card['labels']

def test_card_builder_validation():
    with pytest.raises(ValueError):
        CardBuilder("TASK-001", "Test").with_priority("invalid")

# test_stage_factory.py
def test_stage_factory_create_all():
    factory = StageFactory(board, messenger, rag, logger, test_runner)
    stages = factory.create_all_stages()
    assert len(stages) == 8
    assert isinstance(stages[0], ProjectAnalysisStage)

def test_stage_factory_custom_pipeline():
    factory = StageFactory(board, messenger, rag, logger, test_runner)
    stages = factory.create_custom_pipeline(['development', 'testing'])
    assert len(stages) == 2
```

### Integration Tests

```python
# test_orchestrator_refactored.py
def test_orchestrator_with_factory():
    orchestrator = ArtemisOrchestrator(
        card_id="test-001",
        board=mock_board,
        messenger=mock_messenger,
        rag=mock_rag
    )

    assert len(orchestrator.stages) == 8
    assert orchestrator.stage_factory is not None

def test_builder_card_creation():
    card = (board.create_card_with_builder()
        .with_title("Test")
        .with_priority("high")
        .build())

    board.add_card(card)
    found_card, _ = board._find_card(card['card_id'])
    assert found_card is not None
```

---

## Success Criteria

### Phase 1 (Critical)
- ✅ All duplicate files marked deprecated
- ✅ Clear migration path documented
- ✅ All tests passing
- ✅ No breaking changes

### Phase 2 (High Priority)
- ✅ Builder Pattern implemented and tested
- ✅ Factory Pattern implemented and tested
- ✅ All methods < 50 lines
- ✅ Cyclomatic complexity < 10
- ✅ Test coverage > 80%

### Phase 3 (Medium Priority)
- ✅ No hardcoded paths remaining
- ✅ Configuration centralized
- ✅ Portable across environments

---

## Rollback Plan

If issues arise:

1. **Deprecation warnings:** Remove warnings, keep both files
2. **Builder Pattern:** Keep old method, mark builder as experimental
3. **Factory Pattern:** Keep old `_create_default_stages()` method
4. **Extracted methods:** Can be inlined back if needed

All changes are backward compatible and can be rolled back independently.

---

## Documentation Updates

After refactoring:

1. ✅ Update `REFACTORING_PLAN.md` (this file)
2. ✅ Create `MIGRATION_GUIDE.md`
3. ✅ Update `README.md` with new patterns
4. ✅ Update docstrings in modified files
5. ✅ Create examples in documentation

---

## Conclusion

This refactoring plan addresses the main code quality issues while maintaining backward compatibility and minimizing risk. The changes will:

- **Reduce code duplication** by ~1,500 lines
- **Improve API usability** with Builder pattern
- **Enhance maintainability** with Factory pattern
- **Increase readability** with extracted methods
- **Improve portability** with centralized configuration

**Estimated Total Effort:** 20-25 hours
**Risk Level:** 🟢 LOW (backward compatible)
**Impact:** 🟢 HIGH (major quality improvement)

---

**Status:** Ready for implementation
**Next Action:** Begin Phase 1 (deprecation warnings)
**Timeline:** 2 sprints (2 weeks)
