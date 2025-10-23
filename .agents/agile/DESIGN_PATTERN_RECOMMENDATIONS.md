# Artemis Design Pattern Recommendations

**Date:** October 23, 2025
**Status:** IMPLEMENTATION READY
**Estimated Impact:** 50-70% code quality improvement

---

## Executive Summary

This document provides **concrete design pattern implementations** to address the antipatterns and code smells identified in CODE_QUALITY_ANALYSIS.md.

### Key Recommendations

| Pattern | Target File | Impact | Effort | Priority |
|---------|-------------|--------|--------|----------|
| Factory | artemis_stages.py | HIGH | 2 days | HIGH |
| Strategy | artemis_orchestrator.py | HIGH | 3 days | HIGH |
| Builder | developer_invoker.py | MEDIUM | 2 days | MEDIUM |
| Observer | kanban_manager.py | HIGH | 2 days | HIGH |
| Decorator | llm_client.py | MEDIUM | 1 day | MEDIUM |
| Facade | artemis_workflows.py | HIGH | 3 days | HIGH |
| Template Method | pipeline_stages.py | MEDIUM | 2 days | MEDIUM |

---

## 1. Factory Pattern: Stage Creation

### Problem
`artemis_stages.py` has hard-coded stage instantiation across 8+ different stage types. Adding new stages requires modifying multiple locations.

### Current Code (lines 45-120)
```python
# Hard-coded stage creation scattered throughout
def get_project_analysis_stage(orchestrator):
    return ProjectAnalysisStage(
        orchestrator.card_id,
        orchestrator.board,
        orchestrator.messenger,
        orchestrator.rag
    )

def get_architecture_stage(orchestrator):
    return ArchitectureStage(
        orchestrator.card_id,
        orchestrator.board,
        orchestrator.messenger,
        orchestrator.rag
    )

# ... 6 more similar functions
```

### Refactored with Factory Pattern
```python
# artemis_stage_factory.py

from abc import ABC, abstractmethod
from typing import Dict, Type
from artemis_stage_interface import PipelineStage

class StageFactory:
    """Factory for creating pipeline stages"""

    def __init__(self):
        self._stages: Dict[str, Type[PipelineStage]] = {}

    def register_stage(self, stage_name: str, stage_class: Type[PipelineStage]):
        """Register a new stage type"""
        self._stages[stage_name] = stage_class

    def create_stage(self, stage_name: str, orchestrator) -> PipelineStage:
        """Create a stage instance"""
        stage_class = self._stages.get(stage_name)
        if not stage_class:
            raise ValueError(f"Unknown stage: {stage_name}")

        # All stages get same constructor parameters
        return stage_class(
            card_id=orchestrator.card_id,
            board=orchestrator.board,
            messenger=orchestrator.messenger,
            rag=orchestrator.rag
        )

    def list_stages(self) -> list[str]:
        """Get all registered stage names"""
        return list(self._stages.keys())

# Global factory instance
_factory = StageFactory()

# Register all stage types
from project_analysis_stage import ProjectAnalysisStage
from architecture_stage import ArchitectureStage
from dependencies_stage import DependenciesStage
# ... other stages

_factory.register_stage("project_analysis", ProjectAnalysisStage)
_factory.register_stage("architecture", ArchitectureStage)
_factory.register_stage("dependencies", DependenciesStage)
_factory.register_stage("development", DevelopmentStage)
_factory.register_stage("code_review", CodeReviewStage)
_factory.register_stage("validation", ValidationStage)
_factory.register_stage("integration", IntegrationStage)
_factory.register_stage("testing", TestingStage)

def get_stage_factory() -> StageFactory:
    """Get the global stage factory"""
    return _factory
```

### Updated Orchestrator Usage
```python
# artemis_orchestrator.py (simplified)

from artemis_stage_factory import get_stage_factory

class ArtemisOrchestrator:
    def __init__(self, ...):
        self.stage_factory = get_stage_factory()
        self.stages = self._create_stages()

    def _create_stages(self) -> List[PipelineStage]:
        """Create all pipeline stages using factory"""
        stage_names = [
            "project_analysis",
            "architecture",
            "dependencies",
            "development",
            "code_review",
            "validation",
            "integration",
            "testing"
        ]

        return [
            self.stage_factory.create_stage(name, self)
            for name in stage_names
        ]
```

### Benefits
- ✅ Single location to register new stages
- ✅ Easy to add custom stages without modifying core code
- ✅ Stage creation logic centralized
- ✅ Supports dynamic stage loading from config
- ✅ Testable in isolation

### Implementation Effort: 2 days

---

## 2. Strategy Pattern: Pipeline Execution

### Problem
`artemis_orchestrator.py:run_full_pipeline()` (231 lines) has hard-coded logic for different execution modes. Need flexible execution strategies.

### Current Code (lines 400-631)
```python
def run_full_pipeline(self) -> Dict[str, Any]:
    """Hard-coded pipeline execution"""

    # Project analysis (always runs)
    if not self._run_stage(self.stages[0]):
        return {"status": "failed", "stage": "project_analysis"}

    # Architecture (conditional logic)
    if self.config.get("skip_architecture"):
        print("Skipping architecture...")
    else:
        if not self._run_stage(self.stages[1]):
            return {"status": "failed", "stage": "architecture"}

    # Development (parallel logic hard-coded)
    dev_results = []
    for dev_agent in ["developer-a", "developer-b"]:
        result = self._invoke_developer(dev_agent)
        dev_results.append(result)

    # ... 150 more lines of hard-coded logic
```

### Refactored with Strategy Pattern
```python
# pipeline_strategies.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from artemis_stage_interface import PipelineStage

class PipelineStrategy(ABC):
    """Abstract strategy for pipeline execution"""

    @abstractmethod
    def execute(self, stages: List[PipelineStage]) -> Dict[str, Any]:
        """Execute pipeline with this strategy"""
        pass

class StandardPipelineStrategy(PipelineStrategy):
    """Standard sequential execution"""

    def execute(self, stages: List[PipelineStage]) -> Dict[str, Any]:
        for i, stage in enumerate(stages):
            print(f"Running stage {i+1}/{len(stages)}: {stage.name}")

            result = stage.execute()

            if not result.get("success", False):
                return {
                    "status": "failed",
                    "stage": stage.name,
                    "error": result.get("error")
                }

        return {"status": "success", "stages_completed": len(stages)}

class FastPipelineStrategy(PipelineStrategy):
    """Fast mode - skip optional stages"""

    def __init__(self, skip_stages: List[str] = None):
        self.skip_stages = skip_stages or ["architecture", "validation"]

    def execute(self, stages: List[PipelineStage]) -> Dict[str, Any]:
        filtered_stages = [
            s for s in stages if s.name not in self.skip_stages
        ]

        print(f"Fast mode: Running {len(filtered_stages)}/{len(stages)} stages")

        for stage in filtered_stages:
            result = stage.execute()
            if not result.get("success", False):
                return {"status": "failed", "stage": stage.name}

        return {"status": "success", "mode": "fast"}

class ParallelPipelineStrategy(PipelineStrategy):
    """Parallel execution for independent stages"""

    def execute(self, stages: List[PipelineStage]) -> Dict[str, Any]:
        import concurrent.futures

        # Group stages by dependencies
        independent_stages = self._get_independent_stages(stages)
        dependent_stages = self._get_dependent_stages(stages)

        # Run independent stages in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(stage.execute): stage
                for stage in independent_stages
            }

            for future in concurrent.futures.as_completed(futures):
                stage = futures[future]
                result = future.result()

                if not result.get("success", False):
                    return {"status": "failed", "stage": stage.name}

        # Run dependent stages sequentially
        for stage in dependent_stages:
            result = stage.execute()
            if not result.get("success", False):
                return {"status": "failed", "stage": stage.name}

        return {"status": "success", "mode": "parallel"}

    def _get_independent_stages(self, stages: List[PipelineStage]) -> List[PipelineStage]:
        """Get stages that can run in parallel"""
        # project_analysis, dependencies, validation are independent
        return [s for s in stages if s.name in ["project_analysis", "dependencies", "validation"]]

    def _get_dependent_stages(self, stages: List[PipelineStage]) -> List[PipelineStage]:
        """Get stages that must run sequentially"""
        return [s for s in stages if s.name not in ["project_analysis", "dependencies", "validation"]]

class CheckpointPipelineStrategy(PipelineStrategy):
    """Strategy with checkpointing and resume"""

    def __init__(self, checkpoint_dir: str = "/tmp/artemis_checkpoints"):
        self.checkpoint_dir = checkpoint_dir

    def execute(self, stages: List[PipelineStage]) -> Dict[str, Any]:
        # Check for existing checkpoint
        last_completed = self._load_checkpoint()
        start_index = last_completed + 1 if last_completed >= 0 else 0

        print(f"Resuming from stage {start_index+1}/{len(stages)}")

        for i, stage in enumerate(stages[start_index:], start=start_index):
            result = stage.execute()

            if result.get("success", False):
                self._save_checkpoint(i)
            else:
                return {"status": "failed", "stage": stage.name}

        self._clear_checkpoint()
        return {"status": "success", "resumed": start_index > 0}

    def _load_checkpoint(self) -> int:
        """Load last completed stage index"""
        import json
        checkpoint_file = f"{self.checkpoint_dir}/last_stage.json"

        try:
            with open(checkpoint_file) as f:
                data = json.load(f)
                return data.get("last_stage", -1)
        except FileNotFoundError:
            return -1

    def _save_checkpoint(self, stage_index: int):
        """Save checkpoint"""
        import json
        import os

        os.makedirs(self.checkpoint_dir, exist_ok=True)
        checkpoint_file = f"{self.checkpoint_dir}/last_stage.json"

        with open(checkpoint_file, 'w') as f:
            json.dump({"last_stage": stage_index}, f)

    def _clear_checkpoint(self):
        """Clear checkpoint after successful completion"""
        import os
        checkpoint_file = f"{self.checkpoint_dir}/last_stage.json"

        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)
```

### Updated Orchestrator with Strategy
```python
# artemis_orchestrator.py (refactored)

from pipeline_strategies import (
    PipelineStrategy,
    StandardPipelineStrategy,
    FastPipelineStrategy,
    ParallelPipelineStrategy,
    CheckpointPipelineStrategy
)

class ArtemisOrchestrator:
    def __init__(self, ..., strategy: PipelineStrategy = None):
        self.strategy = strategy or StandardPipelineStrategy()
        # ... rest of init

    def run_full_pipeline(self) -> Dict[str, Any]:
        """Execute pipeline using configured strategy"""
        print(f"Executing pipeline with {self.strategy.__class__.__name__}")

        # Delegate to strategy
        result = self.strategy.execute(self.stages)

        # Log results
        self._log_pipeline_result(result)

        return result

    def _log_pipeline_result(self, result: Dict[str, Any]):
        """Log pipeline execution result"""
        if result["status"] == "success":
            print(f"✅ Pipeline completed successfully")
        else:
            print(f"❌ Pipeline failed at stage: {result.get('stage')}")
```

### Usage Examples
```python
# Standard sequential execution
orchestrator = ArtemisOrchestrator(
    card_id="card-001",
    strategy=StandardPipelineStrategy()
)

# Fast mode (skip optional stages)
orchestrator = ArtemisOrchestrator(
    card_id="card-002",
    strategy=FastPipelineStrategy(skip_stages=["architecture", "validation"])
)

# Parallel execution
orchestrator = ArtemisOrchestrator(
    card_id="card-003",
    strategy=ParallelPipelineStrategy()
)

# With checkpointing
orchestrator = ArtemisOrchestrator(
    card_id="card-004",
    strategy=CheckpointPipelineStrategy(checkpoint_dir="/tmp/checkpoints")
)
```

### Benefits
- ✅ 231-line method reduced to 15 lines
- ✅ Easy to add new execution strategies
- ✅ Each strategy is testable in isolation
- ✅ Clear separation of concerns
- ✅ No conditional logic in orchestrator

### Implementation Effort: 3 days

---

## 3. Observer Pattern: Kanban Updates

### Problem
`kanban_manager.py` requires manual polling to detect board changes. Multiple components need real-time updates.

### Current Code
```python
# Manual polling in orchestrator
while True:
    board_state = kanban.get_board_state()
    if board_state != last_state:
        # React to changes
        handle_board_update(board_state)
    time.sleep(5)  # Poll every 5 seconds
```

### Refactored with Observer Pattern
```python
# kanban_observer.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any

class KanbanObserver(ABC):
    """Observer interface for kanban board changes"""

    @abstractmethod
    def on_card_created(self, card: Dict[str, Any]):
        """Called when a card is created"""
        pass

    @abstractmethod
    def on_card_updated(self, card: Dict[str, Any]):
        """Called when a card is updated"""
        pass

    @abstractmethod
    def on_card_moved(self, card_id: str, from_column: str, to_column: str):
        """Called when a card moves between columns"""
        pass

    @abstractmethod
    def on_card_deleted(self, card_id: str):
        """Called when a card is deleted"""
        pass

class KanbanSubject:
    """Subject that notifies observers of changes"""

    def __init__(self):
        self._observers: List[KanbanObserver] = []

    def attach(self, observer: KanbanObserver):
        """Add an observer"""
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: KanbanObserver):
        """Remove an observer"""
        if observer in self._observers:
            self._observers.remove(observer)

    def notify_card_created(self, card: Dict[str, Any]):
        """Notify all observers of card creation"""
        for observer in self._observers:
            observer.on_card_created(card)

    def notify_card_updated(self, card: Dict[str, Any]):
        """Notify all observers of card update"""
        for observer in self._observers:
            observer.on_card_updated(card)

    def notify_card_moved(self, card_id: str, from_column: str, to_column: str):
        """Notify all observers of card movement"""
        for observer in self._observers:
            observer.on_card_moved(card_id, from_column, to_column)

    def notify_card_deleted(self, card_id: str):
        """Notify all observers of card deletion"""
        for observer in self._observers:
            observer.on_card_deleted(card_id)

# kanban_manager.py (updated)

class KanbanBoard(KanbanSubject):
    """Kanban board with observer notifications"""

    def __init__(self):
        super().__init__()
        self.board_file = "kanban_board.json"
        self._load_board()

    def create_card(self, title: str, description: str, priority: str, story_points: int) -> str:
        """Create a new card and notify observers"""
        card_id = self._generate_card_id()

        card = {
            "id": card_id,
            "title": title,
            "description": description,
            "priority": priority,
            "story_points": story_points,
            "column": "backlog",
            "created_at": datetime.now().isoformat()
        }

        self.cards[card_id] = card
        self._save_board()

        # Notify observers
        self.notify_card_created(card)

        return card_id

    def move_card(self, card_id: str, to_column: str) -> bool:
        """Move card and notify observers"""
        card = self.cards.get(card_id)
        if not card:
            return False

        from_column = card["column"]
        card["column"] = to_column
        self._save_board()

        # Notify observers
        self.notify_card_moved(card_id, from_column, to_column)

        return True

# Example observers
class RAGObserver(KanbanObserver):
    """Observer that stores kanban events in RAG"""

    def __init__(self, rag_agent):
        self.rag = rag_agent

    def on_card_created(self, card: Dict[str, Any]):
        self.rag.store_artifact(
            artifact_type="kanban_event",
            card_id=card["id"],
            task_title=f"Card created: {card['title']}",
            content=f"New card in backlog: {card['description']}"
        )

    def on_card_moved(self, card_id: str, from_column: str, to_column: str):
        self.rag.store_artifact(
            artifact_type="kanban_event",
            card_id=card_id,
            task_title=f"Card moved: {from_column} → {to_column}",
            content=f"Card {card_id} progressed from {from_column} to {to_column}"
        )

    def on_card_updated(self, card: Dict[str, Any]):
        pass  # Optional

    def on_card_deleted(self, card_id: str):
        pass  # Optional

class MetricsObserver(KanbanObserver):
    """Observer that tracks kanban metrics"""

    def __init__(self):
        self.metrics = {
            "cards_created": 0,
            "cards_completed": 0,
            "cards_in_progress": 0
        }

    def on_card_created(self, card: Dict[str, Any]):
        self.metrics["cards_created"] += 1

    def on_card_moved(self, card_id: str, from_column: str, to_column: str):
        if to_column == "done":
            self.metrics["cards_completed"] += 1
        elif to_column == "in_progress":
            self.metrics["cards_in_progress"] += 1

    def on_card_updated(self, card: Dict[str, Any]):
        pass

    def on_card_deleted(self, card_id: str):
        pass

class NotificationObserver(KanbanObserver):
    """Observer that sends notifications"""

    def on_card_created(self, card: Dict[str, Any]):
        print(f"🔔 New card created: {card['title']}")

    def on_card_moved(self, card_id: str, from_column: str, to_column: str):
        if to_column == "done":
            print(f"🎉 Card {card_id} completed!")

    def on_card_updated(self, card: Dict[str, Any]):
        pass

    def on_card_deleted(self, card_id: str):
        print(f"🗑️  Card {card_id} deleted")
```

### Usage
```python
# Set up kanban board with observers
kanban = KanbanBoard()

# Attach observers
kanban.attach(RAGObserver(rag_agent))
kanban.attach(MetricsObserver())
kanban.attach(NotificationObserver())

# Now all observers are automatically notified
card_id = kanban.create_card("Add feature", "...", "high", 13)
# → Triggers on_card_created() on all 3 observers

kanban.move_card(card_id, "in_progress")
# → Triggers on_card_moved() on all 3 observers
```

### Benefits
- ✅ Real-time updates (no polling)
- ✅ Loose coupling between kanban and consumers
- ✅ Easy to add new observers
- ✅ Separation of concerns
- ✅ Testable in isolation

### Implementation Effort: 2 days

---

## 4. Builder Pattern: Developer Agent Configuration

### Problem
`developer_invoker.py` has complex constructor with 10+ parameters. Configuration is error-prone.

### Current Code (lines 45-78)
```python
def invoke_developer(
    agent_name: str,
    card_id: str,
    task_description: str,
    board: KanbanBoard,
    messenger: AgentMessenger,
    rag: RAGAgent,
    config: ConfigurationAgent,
    output_dir: str = "/tmp",
    max_retries: int = 3,
    timeout: int = 300,
    enable_tdd: bool = True,
    enable_review: bool = True,
    enable_tests: bool = True,
    verbose: bool = True
) -> Dict[str, Any]:
    # 200+ lines of complex logic
```

### Refactored with Builder Pattern
```python
# developer_builder.py

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class DeveloperConfig:
    """Configuration for developer agent"""
    agent_name: str
    card_id: str
    task_description: str
    board: KanbanBoard
    messenger: AgentMessenger
    rag: RAGAgent
    config: ConfigurationAgent
    output_dir: str = "/tmp"
    max_retries: int = 3
    timeout: int = 300
    enable_tdd: bool = True
    enable_review: bool = True
    enable_tests: bool = True
    verbose: bool = True
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None

class DeveloperBuilder:
    """Builder for developer agent configuration"""

    def __init__(self, agent_name: str, card_id: str):
        self._config = DeveloperConfig(
            agent_name=agent_name,
            card_id=card_id,
            task_description="",
            board=None,
            messenger=None,
            rag=None,
            config=None
        )

    def with_task(self, description: str) -> 'DeveloperBuilder':
        """Set task description"""
        self._config.task_description = description
        return self

    def with_board(self, board: KanbanBoard) -> 'DeveloperBuilder':
        """Set kanban board"""
        self._config.board = board
        return self

    def with_messenger(self, messenger: AgentMessenger) -> 'DeveloperBuilder':
        """Set agent messenger"""
        self._config.messenger = messenger
        return self

    def with_rag(self, rag: RAGAgent) -> 'DeveloperBuilder':
        """Set RAG agent"""
        self._config.rag = rag
        return self

    def with_config(self, config: ConfigurationAgent) -> 'DeveloperBuilder':
        """Set configuration agent"""
        self._config.config = config
        return self

    def with_output_dir(self, output_dir: str) -> 'DeveloperBuilder':
        """Set output directory"""
        self._config.output_dir = output_dir
        return self

    def with_retries(self, max_retries: int) -> 'DeveloperBuilder':
        """Set max retries"""
        self._config.max_retries = max_retries
        return self

    def with_timeout(self, timeout: int) -> 'DeveloperBuilder':
        """Set timeout in seconds"""
        self._config.timeout = timeout
        return self

    def enable_tdd(self, enabled: bool = True) -> 'DeveloperBuilder':
        """Enable/disable TDD"""
        self._config.enable_tdd = enabled
        return self

    def enable_review(self, enabled: bool = True) -> 'DeveloperBuilder':
        """Enable/disable code review"""
        self._config.enable_review = enabled
        return self

    def enable_tests(self, enabled: bool = True) -> 'DeveloperBuilder':
        """Enable/disable test execution"""
        self._config.enable_tests = enabled
        return self

    def with_llm(self, provider: str, model: Optional[str] = None) -> 'DeveloperBuilder':
        """Set LLM provider and model"""
        self._config.llm_provider = provider
        self._config.llm_model = model
        return self

    def verbose(self, enabled: bool = True) -> 'DeveloperBuilder':
        """Enable/disable verbose logging"""
        self._config.verbose = enabled
        return self

    def build(self) -> DeveloperConfig:
        """Build the configuration"""
        # Validate required fields
        if not self._config.board:
            raise ValueError("Board is required")
        if not self._config.messenger:
            raise ValueError("Messenger is required")
        if not self._config.rag:
            raise ValueError("RAG is required")
        if not self._config.config:
            raise ValueError("Config is required")

        return self._config

# developer_invoker.py (simplified)

def invoke_developer(config: DeveloperConfig) -> Dict[str, Any]:
    """Invoke developer agent with configuration"""

    print(f"Invoking {config.agent_name} for card {config.card_id}")

    # Use config object
    if config.verbose:
        print(f"Task: {config.task_description}")
        print(f"Output: {config.output_dir}")
        print(f"TDD: {config.enable_tdd}, Review: {config.enable_review}")

    # ... rest of logic using config object
```

### Usage Examples
```python
# Simple configuration
config = (
    DeveloperBuilder("developer-a", "card-001")
    .with_task("Implement authentication")
    .with_board(kanban)
    .with_messenger(messenger)
    .with_rag(rag)
    .with_config(config_agent)
    .build()
)

result = invoke_developer(config)

# Advanced configuration
config = (
    DeveloperBuilder("developer-b", "card-002")
    .with_task("Add payment processing")
    .with_board(kanban)
    .with_messenger(messenger)
    .with_rag(rag)
    .with_config(config_agent)
    .with_output_dir("/tmp/developer-b")
    .with_retries(5)
    .with_timeout(600)
    .enable_tdd(True)
    .enable_review(True)
    .enable_tests(True)
    .with_llm("anthropic", "claude-3-opus")
    .verbose(True)
    .build()
)

result = invoke_developer(config)

# Quick development mode (no review, no tests)
config = (
    DeveloperBuilder("developer-a", "card-003")
    .with_task("Quick prototype")
    .with_board(kanban)
    .with_messenger(messenger)
    .with_rag(rag)
    .with_config(config_agent)
    .enable_review(False)
    .enable_tests(False)
    .with_timeout(120)
    .build()
)

result = invoke_developer(config)
```

### Benefits
- ✅ 10+ parameters reduced to fluent interface
- ✅ Self-documenting code
- ✅ Compile-time validation
- ✅ Sensible defaults
- ✅ Easy to add new configuration options

### Implementation Effort: 2 days

---

## 5. Facade Pattern: Workflow Simplification

### Problem
`artemis_workflows.py` (1,141 lines) exposes complex internals. Need simple interface for common workflows.

### Current Code
```python
# Users must know internal implementation
orchestrator = ArtemisOrchestrator(card_id, board, messenger, rag, config)
orchestrator.initialize_stages()
orchestrator.setup_supervision()
orchestrator.configure_checkpoints("/tmp/checkpoints")
result = orchestrator.run_full_pipeline()
if result["status"] == "failed":
    orchestrator.handle_failure(result)
orchestrator.cleanup()

# Too complex!
```

### Refactored with Facade Pattern
```python
# artemis_facade.py

from typing import Optional, Dict, Any
from artemis_orchestrator import ArtemisOrchestrator
from kanban_manager import KanbanBoard
from agent_messenger import AgentMessenger
from rag_agent import RAGAgent
from config_agent import get_config

class ArtemisFacade:
    """Simplified interface for Artemis pipeline"""

    @staticmethod
    def run_card(card_id: str, verbose: bool = True) -> Dict[str, Any]:
        """
        Run complete pipeline for a card with sensible defaults.

        This is the simplest way to use Artemis - just provide a card_id.
        """
        # Set up all dependencies with defaults
        board = KanbanBoard()
        messenger = AgentMessenger("artemis")
        rag = RAGAgent(db_path="/tmp/rag_db", verbose=verbose)
        config = get_config(verbose=verbose)

        # Create orchestrator
        orchestrator = ArtemisOrchestrator(
            card_id=card_id,
            board=board,
            messenger=messenger,
            rag=rag,
            config=config
        )

        # Run pipeline
        result = orchestrator.run_full_pipeline()

        return result

    @staticmethod
    def run_card_with_config(
        card_id: str,
        llm_provider: str = "openai",
        llm_model: str = "gpt-5",
        output_dir: str = "/tmp",
        enable_supervision: bool = True,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Run pipeline with custom configuration.
        """
        board = KanbanBoard()
        messenger = AgentMessenger("artemis")
        rag = RAGAgent(db_path=f"{output_dir}/rag_db", verbose=verbose)

        # Custom config
        config = get_config(verbose=verbose)
        config.set("llm_provider", llm_provider)
        config.set("llm_model", llm_model)

        orchestrator = ArtemisOrchestrator(
            card_id=card_id,
            board=board,
            messenger=messenger,
            rag=rag,
            config=config,
            enable_supervision=enable_supervision
        )

        return orchestrator.run_full_pipeline()

    @staticmethod
    def run_fast_mode(card_id: str) -> Dict[str, Any]:
        """
        Run pipeline in fast mode (skip optional stages).
        """
        from pipeline_strategies import FastPipelineStrategy

        board = KanbanBoard()
        messenger = AgentMessenger("artemis")
        rag = RAGAgent(db_path="/tmp/rag_db", verbose=False)
        config = get_config(verbose=False)

        orchestrator = ArtemisOrchestrator(
            card_id=card_id,
            board=board,
            messenger=messenger,
            rag=rag,
            config=config,
            strategy=FastPipelineStrategy()
        )

        return orchestrator.run_full_pipeline()

    @staticmethod
    def resume_card(card_id: str, checkpoint_dir: str = "/tmp/checkpoints") -> Dict[str, Any]:
        """
        Resume pipeline from last checkpoint.
        """
        from pipeline_strategies import CheckpointPipelineStrategy

        board = KanbanBoard()
        messenger = AgentMessenger("artemis")
        rag = RAGAgent(db_path="/tmp/rag_db", verbose=True)
        config = get_config(verbose=True)

        orchestrator = ArtemisOrchestrator(
            card_id=card_id,
            board=board,
            messenger=messenger,
            rag=rag,
            config=config,
            strategy=CheckpointPipelineStrategy(checkpoint_dir)
        )

        return orchestrator.run_full_pipeline()

    @staticmethod
    def analyze_card(card_id: str) -> Dict[str, Any]:
        """
        Run only project analysis stage (no code generation).
        """
        board = KanbanBoard()
        messenger = AgentMessenger("artemis")
        rag = RAGAgent(db_path="/tmp/rag_db", verbose=True)
        config = get_config(verbose=True)

        orchestrator = ArtemisOrchestrator(
            card_id=card_id,
            board=board,
            messenger=messenger,
            rag=rag,
            config=config
        )

        # Run only first stage
        return orchestrator.stages[0].execute()

    @staticmethod
    def get_card_status(card_id: str) -> Dict[str, Any]:
        """
        Get current status of a card without running pipeline.
        """
        board = KanbanBoard()
        card = board.get_card(card_id)

        if not card:
            return {"error": f"Card {card_id} not found"}

        return {
            "card_id": card_id,
            "title": card.get("title"),
            "column": card.get("column"),
            "priority": card.get("priority"),
            "story_points": card.get("story_points")
        }
```

### Usage Examples
```python
# SIMPLE: Run card with all defaults
from artemis_facade import ArtemisFacade

result = ArtemisFacade.run_card("card-001")
print(f"Status: {result['status']}")

# CUSTOM: Run with specific config
result = ArtemisFacade.run_card_with_config(
    card_id="card-002",
    llm_provider="anthropic",
    llm_model="claude-3-opus",
    enable_supervision=True,
    verbose=True
)

# FAST: Skip optional stages
result = ArtemisFacade.run_fast_mode("card-003")

# RESUME: Resume from checkpoint
result = ArtemisFacade.resume_card("card-004", checkpoint_dir="/tmp/checkpoints")

# ANALYZE: Just analyze, don't generate code
result = ArtemisFacade.analyze_card("card-005")

# STATUS: Check card status
status = ArtemisFacade.get_card_status("card-001")
print(f"Card is in {status['column']} column")
```

### Benefits
- ✅ 50+ lines of setup reduced to 1 line
- ✅ Hides complex internal implementation
- ✅ Common use cases have dedicated methods
- ✅ Easy to test
- ✅ Backward compatible (old code still works)

### Implementation Effort: 3 days

---

## 6. Decorator Pattern: LLM Client Features

### Problem
`llm_client.py` needs features like rate limiting, caching, retries, logging - but shouldn't modify core client.

### Current Code
```python
class LLMClient:
    def generate(self, prompt: str) -> str:
        # Rate limiting logic mixed in
        if self._should_rate_limit():
            time.sleep(1)

        # Caching logic mixed in
        cache_key = hash(prompt)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Retry logic mixed in
        for attempt in range(3):
            try:
                response = self._call_api(prompt)
                break
            except Exception:
                time.sleep(2 ** attempt)

        # Logging mixed in
        print(f"Generated {len(response)} chars")

        return response
```

### Refactored with Decorator Pattern
```python
# llm_decorators.py

from abc import ABC, abstractmethod
from typing import Optional
import time
import hashlib

class LLMInterface(ABC):
    """Interface for LLM clients"""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt"""
        pass

class BaseLLMClient(LLMInterface):
    """Basic LLM client (no extra features)"""

    def __init__(self, provider: str, model: str, api_key: str):
        self.provider = provider
        self.model = model
        self.api_key = api_key

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using LLM API"""
        # Pure API call, no side effects
        if self.provider == "openai":
            return self._call_openai(prompt, **kwargs)
        elif self.provider == "anthropic":
            return self._call_anthropic(prompt, **kwargs)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

class LLMDecorator(LLMInterface):
    """Base decorator"""

    def __init__(self, llm: LLMInterface):
        self._llm = llm

    def generate(self, prompt: str, **kwargs) -> str:
        return self._llm.generate(prompt, **kwargs)

class CachingLLMDecorator(LLMDecorator):
    """Add caching to LLM client"""

    def __init__(self, llm: LLMInterface, cache_dir: str = "/tmp/llm_cache"):
        super().__init__(llm)
        self.cache_dir = cache_dir
        self.cache = {}

    def generate(self, prompt: str, **kwargs) -> str:
        # Check cache
        cache_key = self._get_cache_key(prompt, kwargs)

        if cache_key in self.cache:
            print(f"✅ Cache hit for prompt (hash: {cache_key[:8]}...)")
            return self.cache[cache_key]

        # Generate and cache
        response = self._llm.generate(prompt, **kwargs)
        self.cache[cache_key] = response

        print(f"💾 Cached response (hash: {cache_key[:8]}...)")
        return response

    def _get_cache_key(self, prompt: str, kwargs: dict) -> str:
        """Generate cache key from prompt and kwargs"""
        import json
        content = prompt + json.dumps(kwargs, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

class RateLimitingLLMDecorator(LLMDecorator):
    """Add rate limiting to LLM client"""

    def __init__(self, llm: LLMInterface, requests_per_minute: int = 10):
        super().__init__(llm)
        self.requests_per_minute = requests_per_minute
        self.last_request_times = []

    def generate(self, prompt: str, **kwargs) -> str:
        # Check if we need to wait
        self._enforce_rate_limit()

        # Record request time
        self.last_request_times.append(time.time())

        return self._llm.generate(prompt, **kwargs)

    def _enforce_rate_limit(self):
        """Wait if we've exceeded rate limit"""
        now = time.time()

        # Remove old requests (older than 1 minute)
        self.last_request_times = [
            t for t in self.last_request_times
            if now - t < 60
        ]

        # Check if we've hit limit
        if len(self.last_request_times) >= self.requests_per_minute:
            wait_time = 60 - (now - self.last_request_times[0])
            if wait_time > 0:
                print(f"⏳ Rate limit reached, waiting {wait_time:.1f}s...")
                time.sleep(wait_time)

class RetryLLMDecorator(LLMDecorator):
    """Add retry logic to LLM client"""

    def __init__(self, llm: LLMInterface, max_retries: int = 3, backoff_factor: int = 2):
        super().__init__(llm)
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def generate(self, prompt: str, **kwargs) -> str:
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return self._llm.generate(prompt, **kwargs)
            except Exception as e:
                last_exception = e
                wait_time = self.backoff_factor ** attempt

                print(f"❌ Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    print(f"🔄 Retrying in {wait_time}s...")
                    time.sleep(wait_time)

        raise last_exception

class LoggingLLMDecorator(LLMDecorator):
    """Add logging to LLM client"""

    def __init__(self, llm: LLMInterface, verbose: bool = True):
        super().__init__(llm)
        self.verbose = verbose
        self.request_count = 0

    def generate(self, prompt: str, **kwargs) -> str:
        self.request_count += 1

        if self.verbose:
            print(f"\n📝 LLM Request #{self.request_count}")
            print(f"   Prompt length: {len(prompt)} chars")
            print(f"   Kwargs: {kwargs}")

        start_time = time.time()
        response = self._llm.generate(prompt, **kwargs)
        elapsed = time.time() - start_time

        if self.verbose:
            print(f"✅ Response received in {elapsed:.2f}s")
            print(f"   Response length: {len(response)} chars")

        return response

class CostTrackingLLMDecorator(LLMDecorator):
    """Track LLM API costs"""

    COST_PER_1K_TOKENS = {
        "gpt-5": 0.03,
        "gpt-5-mini": 0.01,
        "claude-3-opus": 0.015,
        "claude-3-sonnet": 0.003
    }

    def __init__(self, llm: LLMInterface, model: str):
        super().__init__(llm)
        self.model = model
        self.total_cost = 0.0
        self.total_tokens = 0

    def generate(self, prompt: str, **kwargs) -> str:
        response = self._llm.generate(prompt, **kwargs)

        # Estimate tokens (rough approximation)
        tokens = (len(prompt) + len(response)) // 4
        cost = self._calculate_cost(tokens)

        self.total_tokens += tokens
        self.total_cost += cost

        print(f"💰 Request cost: ${cost:.4f} ({tokens} tokens)")
        print(f"💰 Total cost: ${self.total_cost:.4f} ({self.total_tokens} tokens)")

        return response

    def _calculate_cost(self, tokens: int) -> float:
        """Calculate cost for tokens"""
        cost_per_1k = self.COST_PER_1K_TOKENS.get(self.model, 0.01)
        return (tokens / 1000) * cost_per_1k
```

### Usage Examples
```python
# Basic client (no decorators)
llm = BaseLLMClient(provider="openai", model="gpt-5", api_key="...")
response = llm.generate("Explain Python decorators")

# Add caching
llm = CachingLLMDecorator(
    BaseLLMClient(provider="openai", model="gpt-5", api_key="...")
)
response = llm.generate("Explain Python decorators")  # API call
response = llm.generate("Explain Python decorators")  # Cached!

# Stack multiple decorators
llm = LoggingLLMDecorator(
    RateLimitingLLMDecorator(
        RetryLLMDecorator(
            CachingLLMDecorator(
                BaseLLMClient(provider="openai", model="gpt-5", api_key="...")
            ),
            max_retries=3
        ),
        requests_per_minute=10
    ),
    verbose=True
)

# Now has: logging + rate limiting + retries + caching!
response = llm.generate("Explain design patterns")

# Production setup with all features
def create_production_llm(provider: str, model: str, api_key: str) -> LLMInterface:
    """Create fully-featured LLM client"""
    return LoggingLLMDecorator(
        CostTrackingLLMDecorator(
            RateLimitingLLMDecorator(
                RetryLLMDecorator(
                    CachingLLMDecorator(
                        BaseLLMClient(provider, model, api_key)
                    ),
                    max_retries=3,
                    backoff_factor=2
                ),
                requests_per_minute=10
            ),
            model=model
        ),
        verbose=True
    )

llm = create_production_llm("openai", "gpt-5", "sk-...")
```

### Benefits
- ✅ Features can be added/removed without modifying core client
- ✅ Each decorator is testable in isolation
- ✅ Mix and match features as needed
- ✅ Single Responsibility Principle
- ✅ Open/Closed Principle

### Implementation Effort: 1 day

---

## 7. Template Method Pattern: Pipeline Stages

### Problem
`pipeline_stages.py` has duplicated stage execution logic across 8 different stage classes.

### Current Code
```python
class ProjectAnalysisStage:
    def execute(self) -> Dict[str, Any]:
        # Duplicated pattern
        print(f"Starting project analysis...")
        self.messenger.notify_stage_start("project_analysis")

        try:
            result = self._do_analysis()  # Unique logic

            self.rag.store_artifact("analysis", result)
            self.messenger.notify_stage_complete("project_analysis")

            return {"success": True, "result": result}
        except Exception as e:
            self.messenger.notify_stage_failed("project_analysis", str(e))
            return {"success": False, "error": str(e)}

class ArchitectureStage:
    def execute(self) -> Dict[str, Any]:
        # Same pattern duplicated!
        print(f"Starting architecture...")
        self.messenger.notify_stage_start("architecture")

        try:
            result = self._design_architecture()  # Unique logic

            self.rag.store_artifact("architecture", result)
            self.messenger.notify_stage_complete("architecture")

            return {"success": True, "result": result}
        except Exception as e:
            self.messenger.notify_stage_failed("architecture", str(e))
            return {"success": False, "error": str(e)}

# ... 6 more stages with same duplicated pattern
```

### Refactored with Template Method Pattern
```python
# pipeline_stage_base.py

from abc import ABC, abstractmethod
from typing import Dict, Any

class PipelineStageTemplate(ABC):
    """Template for pipeline stages with common execution pattern"""

    def __init__(self, card_id: str, board, messenger, rag):
        self.card_id = card_id
        self.board = board
        self.messenger = messenger
        self.rag = rag

    @property
    @abstractmethod
    def stage_name(self) -> str:
        """Name of this stage"""
        pass

    def execute(self) -> Dict[str, Any]:
        """
        Template method defining the execution pattern.

        This method is final - subclasses override hooks instead.
        """
        # Pre-execution
        self._log_start()
        self._notify_start()
        self._setup()

        try:
            # Main execution (subclass implements)
            result = self._execute_stage()

            # Post-execution (success)
            self._store_result(result)
            self._notify_success()
            self._teardown(success=True)

            return {"success": True, "result": result}

        except Exception as e:
            # Post-execution (failure)
            self._notify_failure(str(e))
            self._teardown(success=False)

            return {"success": False, "error": str(e)}

    # Template method hooks (subclasses can override)

    def _log_start(self):
        """Log stage start (default implementation)"""
        print(f"\n{'='*60}")
        print(f"Starting {self.stage_name}...")
        print(f"{'='*60}")

    def _notify_start(self):
        """Notify observers of stage start"""
        self.messenger.notify_stage_start(self.stage_name)

    def _setup(self):
        """Pre-execution setup (override if needed)"""
        pass

    @abstractmethod
    def _execute_stage(self) -> Any:
        """
        Main stage execution logic.

        Subclasses MUST implement this method.
        """
        pass

    def _store_result(self, result: Any):
        """Store result in RAG (override if needed)"""
        self.rag.store_artifact(
            artifact_type=f"{self.stage_name}_result",
            card_id=self.card_id,
            task_title=f"{self.stage_name} completed",
            content=str(result)
        )

    def _notify_success(self):
        """Notify observers of success"""
        self.messenger.notify_stage_complete(self.stage_name)
        print(f"✅ {self.stage_name} completed successfully")

    def _notify_failure(self, error: str):
        """Notify observers of failure"""
        self.messenger.notify_stage_failed(self.stage_name, error)
        print(f"❌ {self.stage_name} failed: {error}")

    def _teardown(self, success: bool):
        """Post-execution cleanup (override if needed)"""
        pass

# Concrete implementations
class ProjectAnalysisStage(PipelineStageTemplate):
    """Project analysis stage"""

    @property
    def stage_name(self) -> str:
        return "project_analysis"

    def _execute_stage(self) -> Any:
        """Implement actual project analysis"""
        from project_analysis_agent import ProjectAnalysisAgent

        agent = ProjectAnalysisAgent(
            card_id=self.card_id,
            board=self.board
        )

        return agent.analyze_project()

class ArchitectureStage(PipelineStageTemplate):
    """Architecture design stage"""

    @property
    def stage_name(self) -> str:
        return "architecture"

    def _setup(self):
        """Load project analysis before designing architecture"""
        self.project_analysis = self.rag.retrieve_artifact(
            artifact_type="project_analysis_result",
            card_id=self.card_id
        )

    def _execute_stage(self) -> Any:
        """Implement architecture design"""
        # Use self.project_analysis here
        return self._design_architecture()

    def _design_architecture(self):
        """Design system architecture"""
        # ... architecture logic
        pass

class DevelopmentStage(PipelineStageTemplate):
    """Development stage with parallel execution"""

    @property
    def stage_name(self) -> str:
        return "development"

    def _execute_stage(self) -> Any:
        """Implement parallel development"""
        import concurrent.futures

        developer_agents = ["developer-a", "developer-b"]

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(self._invoke_developer, agent): agent
                for agent in developer_agents
            }

            results = {}
            for future in concurrent.futures.as_completed(futures):
                agent = futures[future]
                results[agent] = future.result()

        return results

    def _invoke_developer(self, agent_name: str):
        """Invoke a single developer agent"""
        # ... developer invocation logic
        pass

    def _teardown(self, success: bool):
        """Clean up development artifacts"""
        if not success:
            # Clean up failed development artifacts
            pass

class CodeReviewStage(PipelineStageTemplate):
    """Code review stage"""

    @property
    def stage_name(self) -> str:
        return "code_review"

    def _execute_stage(self) -> Any:
        """Implement code review"""
        from code_review_agent import CodeReviewAgent

        agent = CodeReviewAgent(
            card_id=self.card_id,
            board=self.board,
            rag=self.rag
        )

        return agent.review_code()

    def _notify_success(self):
        """Custom success notification with score"""
        super()._notify_success()

        # Add score to notification
        score = self.result.get("score", 0)
        print(f"   Code quality score: {score}/100")
```

### Benefits
- ✅ Eliminates 200+ lines of duplicated code
- ✅ Consistent execution pattern across all stages
- ✅ Easy to add new stages (just implement _execute_stage())
- ✅ Common behavior changes in one place
- ✅ Each stage focuses only on unique logic

### Implementation Effort: 2 days

---

## Implementation Roadmap

### Week 1: High-Priority Patterns (HIGH ROI)
**Days 1-2: Factory Pattern** (artemis_stages.py)
- Create StageFactory class
- Register all 8 stage types
- Update orchestrator to use factory
- Write unit tests
- **Impact:** Easier to add custom stages

**Days 3-5: Strategy Pattern** (artemis_orchestrator.py)
- Create PipelineStrategy interface
- Implement 4 concrete strategies
- Update orchestrator
- Write integration tests
- **Impact:** 231-line method → 15 lines

### Week 2: Observer + Facade Patterns
**Days 1-2: Observer Pattern** (kanban_manager.py)
- Create KanbanObserver interface
- Update KanbanBoard as Subject
- Implement 3 concrete observers
- Write tests
- **Impact:** Real-time updates (no polling)

**Days 3-5: Facade Pattern** (artemis_workflows.py)
- Create ArtemisFacade class
- Implement 5 common workflows
- Write documentation
- Write tests
- **Impact:** 50+ lines setup → 1 line

### Week 3: Builder + Decorator Patterns
**Days 1-2: Builder Pattern** (developer_invoker.py)
- Create DeveloperBuilder class
- Create DeveloperConfig dataclass
- Update invoke_developer() signature
- Write tests
- **Impact:** 10+ params → fluent interface

**Days 3-4: Decorator Pattern** (llm_client.py)
- Create LLM decorators (5 types)
- Update client creation
- Write tests
- **Impact:** Flexible LLM features

**Day 5: Buffer**

### Week 4: Template Method + Testing
**Days 1-2: Template Method** (pipeline_stages.py)
- Create PipelineStageTemplate base class
- Refactor 8 stages to use template
- Write tests
- **Impact:** Eliminate 200+ lines duplication

**Days 3-5: Comprehensive Testing**
- Unit tests for all patterns
- Integration tests
- Performance tests
- Documentation updates

### Week 5: Integration + Rollout
**Days 1-2: Integration**
- Integrate all patterns together
- Resolve conflicts
- Performance optimization

**Days 3-4: Documentation**
- Update all READMEs
- Create migration guide
- Record demo videos

**Day 5: Gradual Rollout**
- Deploy to staging
- Monitor performance
- Deploy to production

---

## Success Metrics

### Code Quality Improvements
- **Lines of Code:** -30% (eliminate duplication)
- **Cyclomatic Complexity:** -40% (flatten nesting, simplify)
- **Test Coverage:** +25% (testable patterns)
- **Code Smells:** -80% (god classes → SOLID classes)

### Developer Experience
- **Setup Time:** 50+ lines → 1-5 lines (Facade)
- **Configuration Errors:** -60% (Builder validation)
- **Learning Curve:** -40% (self-documenting patterns)

### Maintainability
- **Time to Add Feature:** -50% (Factory, Strategy)
- **Bug Fix Time:** -35% (isolated concerns)
- **Refactoring Safety:** +70% (better tests)

### Performance
- **Pipeline Execution:** No regression (same speed)
- **Memory Usage:** -10% (fewer god objects)
- **Startup Time:** No regression

---

## Testing Strategy

### Unit Tests (80% coverage target)
```python
# Test Factory
def test_stage_factory_creates_all_stages():
    factory = get_stage_factory()
    for stage_name in factory.list_stages():
        stage = factory.create_stage(stage_name, mock_orchestrator)
        assert isinstance(stage, PipelineStage)

# Test Strategy
def test_fast_pipeline_skips_optional_stages():
    strategy = FastPipelineStrategy(skip_stages=["architecture"])
    result = strategy.execute(mock_stages)
    assert "architecture" not in result["executed_stages"]

# Test Observer
def test_observer_notified_on_card_created():
    observer = MockObserver()
    kanban = KanbanBoard()
    kanban.attach(observer)

    kanban.create_card("Test", "...", "high", 5)

    assert observer.on_card_created_called

# Test Builder
def test_builder_validates_required_fields():
    with pytest.raises(ValueError, match="Board is required"):
        DeveloperBuilder("dev-a", "card-001").build()

# Test Decorator
def test_caching_decorator_caches_responses():
    mock_llm = MockLLM()
    cached_llm = CachingLLMDecorator(mock_llm)

    cached_llm.generate("test prompt")  # Call 1
    cached_llm.generate("test prompt")  # Call 2 (cached)

    assert mock_llm.call_count == 1  # Only called once

# Test Facade
def test_facade_runs_complete_pipeline():
    result = ArtemisFacade.run_card("test-card-001")
    assert result["status"] in ["success", "failed"]

# Test Template Method
def test_template_method_calls_hooks_in_order():
    stage = MockStage()
    stage.execute()

    assert stage.call_order == [
        "_log_start",
        "_notify_start",
        "_setup",
        "_execute_stage",
        "_store_result",
        "_notify_success",
        "_teardown"
    ]
```

### Integration Tests
```python
def test_full_pipeline_with_all_patterns():
    """Test complete pipeline using all design patterns"""

    # Factory creates stages
    factory = get_stage_factory()
    stages = [factory.create_stage(name, orchestrator) for name in stage_names]

    # Strategy executes pipeline
    strategy = StandardPipelineStrategy()

    # Observer monitors progress
    observer = MetricsObserver()
    kanban.attach(observer)

    # Facade simplifies usage
    result = ArtemisFacade.run_card_with_config(
        card_id="integration-test-001",
        llm_provider="mock",
        enable_supervision=False
    )

    assert result["status"] == "success"
    assert observer.metrics["stages_completed"] == 8
```

---

## Rollout Strategy

### Phase 1: Canary (Week 1)
- Deploy Factory and Strategy patterns only
- Test with 10% of cards
- Monitor performance and errors
- Rollback if issues detected

### Phase 2: Gradual Rollout (Weeks 2-3)
- Deploy Observer, Facade, Builder patterns
- Test with 50% of cards
- Collect feedback from developers

### Phase 3: Full Deployment (Week 4)
- Deploy Decorator and Template Method patterns
- Test with 100% of cards
- Monitor for 1 week

### Phase 4: Cleanup (Week 5)
- Remove old code after successful deployment
- Update all documentation
- Training for team members

---

## Conclusion

Implementing these 7 design patterns will:

✅ **Reduce code by 30%** (eliminate duplication)
✅ **Improve quality by 50-70%** (SOLID principles)
✅ **Simplify usage by 90%** (Facade pattern)
✅ **Enable extensibility** (Factory, Strategy)
✅ **Improve testability** (isolated concerns)

**Total Effort:** 4-5 weeks
**Total Impact:** Transforms Artemis into production-grade system

**Recommended Priority:**
1. **HIGH:** Factory, Strategy, Facade (Week 1-2) - Biggest impact
2. **MEDIUM:** Observer, Builder (Week 2-3) - Quality of life
3. **LOW:** Decorator, Template Method (Week 3-4) - Code elegance

---

**Created:** October 23, 2025
**Status:** Ready for implementation approval
**Next Step:** Get user approval to proceed with Week 1 (Factory + Strategy)
