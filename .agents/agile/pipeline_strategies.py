#!/usr/bin/env python3
"""
Pipeline Execution Strategies (Design Pattern: Strategy)

Provides different execution strategies for the Artemis pipeline, implementing
the Strategy Pattern for flexible and extensible pipeline execution.

SOLID Principles:
- Single Responsibility: Each strategy handles ONE execution mode
- Open/Closed: Add new strategies without modifying existing code
- Liskov Substitution: All strategies are interchangeable
- Interface Segregation: Minimal strategy interface
- Dependency Inversion: Depends on PipelineStage abstraction

Strategies:
1. StandardPipelineStrategy - Sequential execution (default)
2. FastPipelineStrategy - Skip optional stages for quick turnaround
3. ParallelPipelineStrategy - Execute independent stages concurrently
4. CheckpointPipelineStrategy - Resume from failures with checkpoints
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import os
import concurrent.futures
from datetime import datetime, timedelta

from artemis_stage_interface import PipelineStage
from artemis_constants import (
    STAGE_PROJECT_ANALYSIS,
    STAGE_ARCHITECTURE,
    STAGE_DEPENDENCIES,
    STAGE_DEVELOPMENT,
    STAGE_CODE_REVIEW,
    STAGE_VALIDATION,
    STAGE_INTEGRATION,
    STAGE_TESTING
)
from pipeline_observer import PipelineObservable, EventBuilder


class PipelineStrategy(ABC):
    """
    Abstract base class for pipeline execution strategies.

    All strategies must implement execute() which takes a list of stages
    and returns execution results.
    """

    def __init__(self, verbose: bool = True, observable: Optional[PipelineObservable] = None):
        """
        Initialize strategy.

        Args:
            verbose: Enable verbose logging
            observable: Optional PipelineObservable for event broadcasting
        """
        self.verbose = verbose
        self.observable = observable

    @abstractmethod
    def execute(self, stages: List[PipelineStage], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute pipeline stages using this strategy.

        Args:
            stages: List of pipeline stages to execute
            context: Execution context (card info, config, etc.)

        Returns:
            Dict with execution results:
            {
                "status": "success" | "failed",
                "stages_completed": int,
                "failed_stage": str (if failed),
                "results": Dict[str, Any],
                "duration_seconds": float,
                "strategy": str
            }
        """
        pass

    def _log(self, message: str, level: str = "INFO"):
        """Log message if verbose enabled"""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")

    def _notify_stage_started(self, card_id: str, stage_name: str, **data):
        """Notify observers that stage started"""
        if self.observable:
            event = EventBuilder.stage_started(card_id, stage_name, **data)
            self.observable.notify(event)

    def _notify_stage_completed(self, card_id: str, stage_name: str, **data):
        """Notify observers that stage completed"""
        if self.observable:
            event = EventBuilder.stage_completed(card_id, stage_name, **data)
            self.observable.notify(event)

    def _notify_stage_failed(self, card_id: str, stage_name: str, error: Exception, **data):
        """Notify observers that stage failed"""
        if self.observable:
            event = EventBuilder.stage_failed(card_id, stage_name, error, **data)
            self.observable.notify(event)

    def _recalculate_complexity_after_sprint_planning(
        self,
        card: Dict,
        sprint_planning_result: Dict,
        context: Dict[str, Any]
    ):
        """
        POST-SPRINT-PLANNING HOOK: Recalculate complexity based on actual story points

        This fixes the bug where AI guesses complexity without seeing actual sprint planning results.
        After sprint planning completes, we update the routing decision based on actual story points.

        Args:
            card: Kanban card
            sprint_planning_result: Result from SprintPlanningStage with total_story_points
            context: Pipeline execution context
        """
        # Get orchestrator from context
        orchestrator = context.get('orchestrator')
        if not orchestrator or not hasattr(orchestrator, 'intelligent_router'):
            return

        router = orchestrator.intelligent_router
        if not router:
            return

        # Recalculate complexity using intelligent router
        updated_decision = router.recalculate_complexity_from_sprint_planning(
            card,
            sprint_planning_result
        )

        # Update context with corrected routing decision
        context['routing_decision'] = updated_decision

        # Re-filter stages based on corrected complexity
        if hasattr(orchestrator, 'stages'):
            corrected_stages = router.filter_stages(orchestrator.stages, updated_decision)
            # Update orchestrator's active stages (note: this won't affect current execution but will log)
            self._log(f"🔧 Complexity recalculated after sprint planning", "INFO")
            self._log(f"   Updated stages to run: {len(corrected_stages)}", "INFO")


# ============================================================================
# STANDARD PIPELINE STRATEGY
# ============================================================================

class StandardPipelineStrategy(PipelineStrategy):
    """
    Standard sequential execution strategy.

    Executes all stages in order, stopping at first failure.
    This is the default behavior and matches the original implementation.

    Execution Flow:
    1. Project Analysis
    2. Architecture
    3. Dependencies
    4. Development
    5. Code Review
    6. Validation
    7. Integration
    8. Testing
    """

    def execute(self, stages: List[PipelineStage], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all stages sequentially"""
        start_time = datetime.now()

        self._log(f"🎯 Starting STANDARD pipeline execution ({len(stages)} stages)")

        results = {}

        for i, stage in enumerate(stages, 1):
            stage_name = stage.__class__.__name__
            card_id = context.get('card_id', 'unknown')

            self._log(f"▶️  Stage {i}/{len(stages)}: {stage_name}", "STAGE")

            # Notify stage started
            self._notify_stage_started(card_id, stage_name, stage_number=i, total_stages=len(stages))

            try:
                # Execute stage with card and context
                card = context.get('card')
                stage_result = stage.execute(card, context)

                # Store result
                results[stage_name] = stage_result

                # Update context with stage result for downstream stages
                context.update(stage_result)

                # POST-SPRINT-PLANNING HOOK: Recalculate complexity based on actual story points
                # This fixes the bug where AI guesses complexity without seeing sprint planning results
                if stage_name == "SprintPlanningStage" and "total_story_points" in stage_result:
                    self._recalculate_complexity_after_sprint_planning(card, stage_result, context)

                # Check if stage succeeded (check both "success" and "status" keys)
                success = stage_result.get("success", False) or stage_result.get("status") in ["COMPLETE", "PASS"]
                if not success:
                    self._log(f"❌ Stage FAILED: {stage_name}", "ERROR")

                    # Notify stage failed
                    error = Exception(stage_result.get("error", "Unknown error"))
                    self._notify_stage_failed(card_id, stage_name, error, stage_result=stage_result)

                    return {
                        "status": "failed",
                        "stages_completed": i - 1,
                        "failed_stage": stage_name,
                        "error": stage_result.get("error", "Unknown error"),
                        "results": results,
                        "duration_seconds": (datetime.now() - start_time).total_seconds(),
                        "strategy": "standard"
                    }

                self._log(f"✅ Stage COMPLETE: {stage_name}", "SUCCESS")

                # Notify stage completed
                self._notify_stage_completed(card_id, stage_name, stage_result=stage_result)

                # Save checkpoint after successful stage completion
                orchestrator = context.get('orchestrator')
                if orchestrator and hasattr(orchestrator, 'checkpoint_manager'):
                    checkpoint_manager = orchestrator.checkpoint_manager
                    checkpoint_manager.save_stage_checkpoint(
                        stage_name=stage_name.lower(),
                        status="completed",
                        result=stage_result,
                        start_time=datetime.now() - timedelta(seconds=5),  # Estimate (TODO: track actual start time)
                        end_time=datetime.now()
                    )

            except Exception as e:
                self._log(f"❌ Stage EXCEPTION: {stage_name} - {e}", "ERROR")

                # Notify stage failed
                self._notify_stage_failed(card_id, stage_name, e, exception=str(e))

                return {
                    "status": "failed",
                    "stages_completed": i - 1,
                    "failed_stage": stage_name,
                    "error": str(e),
                    "results": results,
                    "duration_seconds": (datetime.now() - start_time).total_seconds(),
                    "strategy": "standard"
                }

        # All stages completed successfully
        duration = (datetime.now() - start_time).total_seconds()

        self._log(f"🎉 Pipeline COMPLETE! ({duration:.1f}s)", "SUCCESS")

        return {
            "status": "success",
            "stages_completed": len(stages),
            "results": results,
            "duration_seconds": duration,
            "strategy": "standard"
        }


# ============================================================================
# FAST PIPELINE STRATEGY
# ============================================================================

class FastPipelineStrategy(PipelineStrategy):
    """
    Fast execution strategy - skip optional stages.

    Skips optional stages to reduce execution time. Useful for:
    - Quick prototypes
    - Development testing
    - Low-priority tasks

    Skipped Stages (by default):
    - Architecture (can be regenerated later)
    - Validation (tests run in development)

    Execution Flow:
    1. Project Analysis ✅
    2. Architecture ⏭️  SKIP
    3. Dependencies ✅
    4. Development ✅
    5. Code Review ✅
    6. Validation ⏭️  SKIP
    7. Integration ✅
    8. Testing ✅
    """

    def __init__(self, skip_stages: Optional[List[str]] = None, verbose: bool = True):
        """
        Initialize fast strategy.

        Args:
            skip_stages: List of stage names to skip (default: ["architecture", "validation"])
            verbose: Enable verbose logging
        """
        super().__init__(verbose)
        self.skip_stages = skip_stages or [STAGE_ARCHITECTURE, STAGE_VALIDATION]

    def execute(self, stages: List[PipelineStage], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute pipeline with optional stages skipped"""
        start_time = datetime.now()

        # Filter out skipped stages
        active_stages = [
            s for s in stages
            if self._get_stage_name(s) not in self.skip_stages
        ]

        skipped_count = len(stages) - len(active_stages)

        self._log(f"⚡ Starting FAST pipeline execution")
        self._log(f"   Running: {len(active_stages)} stages")
        self._log(f"   Skipping: {skipped_count} stages ({', '.join(self.skip_stages)})")

        results = {}

        for i, stage in enumerate(active_stages, 1):
            stage_name = stage.__class__.__name__

            self._log(f"▶️  Stage {i}/{len(active_stages)}: {stage_name}", "STAGE")

            try:
                # Execute stage with card and context
                card = context.get('card')
                stage_result = stage.execute(card, context)
                results[stage_name] = stage_result

                # Update context with stage result for downstream stages
                context.update(stage_result)

                # Check if stage succeeded (check both "success" and "status" keys)
                success = stage_result.get("success", False) or stage_result.get("status") in ["COMPLETE", "PASS"]
                if not success:
                    self._log(f"❌ Stage FAILED: {stage_name}", "ERROR")

                    return {
                        "status": "failed",
                        "stages_completed": i - 1,
                        "stages_skipped": skipped_count,
                        "failed_stage": stage_name,
                        "error": stage_result.get("error"),
                        "results": results,
                        "duration_seconds": (datetime.now() - start_time).total_seconds(),
                        "strategy": "fast"
                    }

                self._log(f"✅ Stage COMPLETE: {stage_name}", "SUCCESS")

            except Exception as e:
                self._log(f"❌ Stage EXCEPTION: {stage_name} - {e}", "ERROR")

                return {
                    "status": "failed",
                    "stages_completed": i - 1,
                    "stages_skipped": skipped_count,
                    "failed_stage": stage_name,
                    "error": str(e),
                    "results": results,
                    "duration_seconds": (datetime.now() - start_time).total_seconds(),
                    "strategy": "fast"
                }

        duration = (datetime.now() - start_time).total_seconds()

        self._log(f"⚡ FAST pipeline COMPLETE! ({duration:.1f}s, skipped {skipped_count} stages)", "SUCCESS")

        return {
            "status": "success",
            "stages_completed": len(active_stages),
            "stages_skipped": skipped_count,
            "results": results,
            "duration_seconds": duration,
            "strategy": "fast"
        }

    def _get_stage_name(self, stage: PipelineStage) -> str:
        """Get normalized stage name for comparison"""
        # Try to get name from stage, fallback to class name
        if hasattr(stage, 'name'):
            return stage.name.lower()
        return stage.__class__.__name__.replace('Stage', '').lower()


# ============================================================================
# PARALLEL PIPELINE STRATEGY
# ============================================================================

class ParallelPipelineStrategy(PipelineStrategy):
    """
    Parallel execution strategy - run independent stages concurrently.

    Executes independent stages in parallel to reduce total execution time.
    Maintains dependencies between stages.

    Parallelization Groups:
    - Group 1 (parallel): Project Analysis, Dependencies
    - Group 2 (sequential): Architecture (needs Group 1)
    - Group 3 (sequential): Development (needs Group 2)
    - Group 4 (sequential): Code Review (needs Group 3)
    - Group 5 (parallel): Validation, Integration
    - Group 6 (sequential): Testing (needs Group 5)

    Potential Speedup: 20-30% reduction in execution time
    """

    def __init__(self, max_workers: int = 4, verbose: bool = True):
        """
        Initialize parallel strategy.

        Args:
            max_workers: Maximum number of parallel workers
            verbose: Enable verbose logging
        """
        super().__init__(verbose)
        self.max_workers = max_workers

    def execute(self, stages: List[PipelineStage], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute pipeline with parallel execution where possible"""
        start_time = datetime.now()

        self._log(f"⚡ Starting PARALLEL pipeline execution (max workers: {self.max_workers})")

        # Group stages by dependencies
        stage_groups = self._group_stages_by_dependencies(stages)

        self._log(f"   Grouped into {len(stage_groups)} execution groups")

        results = {}
        total_stages_completed = 0

        for group_idx, stage_group in enumerate(stage_groups, 1):
            self._log(f"📦 Executing Group {group_idx}: {len(stage_group)} stage(s)", "STAGE")

            if len(stage_group) == 1:
                # Single stage - execute directly
                stage = stage_group[0]
                stage_name = stage.__class__.__name__

                self._log(f"   ▶️  {stage_name}")

                try:
                    # Execute stage with card and context
                    card = context.get('card')
                    stage_result = stage.execute(card, context)
                    results[stage_name] = stage_result

                    # Check if stage succeeded (check both "success" and "status" keys)
                    success = stage_result.get("success", False) or stage_result.get("status") in ["COMPLETE", "PASS"]
                    if not success:
                        return self._build_failure_result(
                            total_stages_completed,
                            stage_name,
                            stage_result.get("error"),
                            results,
                            start_time
                        )

                    self._log(f"   ✅ {stage_name}")
                    total_stages_completed += 1

                except Exception as e:
                    return self._build_failure_result(
                        total_stages_completed,
                        stage_name,
                        str(e),
                        results,
                        start_time
                    )
            else:
                # Multiple stages - execute in parallel
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # Submit all stages in this group
                    future_to_stage = {
                        executor.submit(stage.execute): stage
                        for stage in stage_group
                    }

                    # Wait for all to complete
                    for future in concurrent.futures.as_completed(future_to_stage):
                        stage = future_to_stage[future]
                        stage_name = stage.__class__.__name__

                        try:
                            stage_result = future.result()
                            results[stage_name] = stage_result

                            # Check if stage succeeded (check both "success" and "status" keys)
                            success = stage_result.get("success", False) or stage_result.get("status") in ["COMPLETE", "PASS"]
                            if not success:
                                # Cancel remaining futures
                                for f in future_to_stage:
                                    f.cancel()

                                return self._build_failure_result(
                                    total_stages_completed,
                                    stage_name,
                                    stage_result.get("error"),
                                    results,
                                    start_time
                                )

                            self._log(f"   ✅ {stage_name}")
                            total_stages_completed += 1

                        except Exception as e:
                            return self._build_failure_result(
                                total_stages_completed,
                                stage_name,
                                str(e),
                                results,
                                start_time
                            )

        duration = (datetime.now() - start_time).total_seconds()

        self._log(f"⚡ PARALLEL pipeline COMPLETE! ({duration:.1f}s)", "SUCCESS")

        return {
            "status": "success",
            "stages_completed": total_stages_completed,
            "execution_groups": len(stage_groups),
            "results": results,
            "duration_seconds": duration,
            "strategy": "parallel"
        }

    def _group_stages_by_dependencies(self, stages: List[PipelineStage]) -> List[List[PipelineStage]]:
        """
        Group stages by their dependencies.

        Returns list of stage groups where stages in each group can run in parallel.
        """
        # Simplified grouping - in production, analyze actual dependencies
        groups = []

        # Map stage names to stages
        stage_map = {self._get_stage_name(s): s for s in stages}

        # Group 1: Independent analysis stages
        group1 = []
        for name in [STAGE_PROJECT_ANALYSIS, STAGE_DEPENDENCIES]:
            if name in stage_map:
                group1.append(stage_map[name])
        if group1:
            groups.append(group1)

        # Group 2: Architecture (needs analysis)
        if STAGE_ARCHITECTURE in stage_map:
            groups.append([stage_map[STAGE_ARCHITECTURE]])

        # Group 3: Development (needs architecture)
        if STAGE_DEVELOPMENT in stage_map:
            groups.append([stage_map[STAGE_DEVELOPMENT]])

        # Group 4: Code Review (needs development)
        if STAGE_CODE_REVIEW in stage_map:
            groups.append([stage_map[STAGE_CODE_REVIEW]])

        # Group 5: Validation and Integration (can run in parallel)
        group5 = []
        for name in [STAGE_VALIDATION, STAGE_INTEGRATION]:
            if name in stage_map:
                group5.append(stage_map[name])
        if group5:
            groups.append(group5)

        # Group 6: Testing (needs validation/integration)
        if STAGE_TESTING in stage_map:
            groups.append([stage_map[STAGE_TESTING]])

        return groups

    def _get_stage_name(self, stage: PipelineStage) -> str:
        """Get normalized stage name"""
        if hasattr(stage, 'name'):
            return stage.name.lower()
        return stage.__class__.__name__.replace('Stage', '').lower()

    def _build_failure_result(
        self,
        stages_completed: int,
        failed_stage: str,
        error: str,
        results: Dict,
        start_time: datetime
    ) -> Dict[str, Any]:
        """Build failure result dict"""
        self._log(f"❌ Stage FAILED: {failed_stage}", "ERROR")

        return {
            "status": "failed",
            "stages_completed": stages_completed,
            "failed_stage": failed_stage,
            "error": error,
            "results": results,
            "duration_seconds": (datetime.now() - start_time).total_seconds(),
            "strategy": "parallel"
        }


# ============================================================================
# CHECKPOINT PIPELINE STRATEGY
# ============================================================================

class CheckpointPipelineStrategy(PipelineStrategy):
    """
    Checkpoint-based execution strategy - resume from failures.

    Saves progress after each stage completes. If pipeline fails,
    can resume from last successful checkpoint instead of starting over.

    Features:
    - Automatic checkpointing after each stage
    - Resume from last successful stage
    - LLM response caching (avoid re-running expensive operations)
    - Progress tracking

    Use Cases:
    - Long-running pipelines
    - Unreliable environments
    - Development/testing (iterate on single stage)
    - Cost optimization (don't re-run LLM calls)
    """

    def __init__(self, checkpoint_dir: str = "../../.artemis_data/checkpoints", verbose: bool = True):
        """
        Initialize checkpoint strategy.

        Args:
            checkpoint_dir: Directory to store checkpoints (relative to .agents/agile)
            verbose: Enable verbose logging
        """
        super().__init__(verbose)

        # Convert relative path to absolute
        if not os.path.isabs(checkpoint_dir):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            checkpoint_dir = os.path.join(script_dir, checkpoint_dir)

        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, stages: List[PipelineStage], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute pipeline with checkpointing"""
        start_time = datetime.now()

        card_id = context.get("card_id", "unknown")
        checkpoint_file = self.checkpoint_dir / f"{card_id}_checkpoint.json"

        # Check for existing checkpoint
        last_completed_idx, checkpoint_data = self._load_checkpoint(checkpoint_file)

        if last_completed_idx >= 0:
            self._log(f"💾 Found checkpoint - resuming from stage {last_completed_idx + 2}/{len(stages)}")
            start_idx = last_completed_idx + 1
            results = checkpoint_data.get("results", {})
            resumed = True
        else:
            self._log(f"💾 Starting CHECKPOINT pipeline execution (no existing checkpoint)")
            start_idx = 0
            results = {}
            resumed = False

        # Execute remaining stages
        for i in range(start_idx, len(stages)):
            stage = stages[i]
            stage_name = stage.__class__.__name__

            self._log(f"▶️  Stage {i + 1}/{len(stages)}: {stage_name}", "STAGE")

            try:
                # Execute stage with card and context
                card = context.get('card')
                stage_result = stage.execute(card, context)
                results[stage_name] = stage_result

                # Update context with stage result for downstream stages
                context.update(stage_result)

                # Check if stage succeeded (check both "success" and "status" keys)
                success = stage_result.get("success", False) or stage_result.get("status") in ["COMPLETE", "PASS"]
                if not success:
                    self._log(f"❌ Stage FAILED: {stage_name}", "ERROR")

                    # Save checkpoint before returning
                    self._save_checkpoint(checkpoint_file, i - 1, results)

                    return {
                        "status": "failed",
                        "stages_completed": i,
                        "failed_stage": stage_name,
                        "error": stage_result.get("error"),
                        "results": results,
                        "duration_seconds": (datetime.now() - start_time).total_seconds(),
                        "strategy": "checkpoint",
                        "resumed": resumed,
                        "checkpoint_saved": True
                    }

                # Save checkpoint after successful stage
                self._save_checkpoint(checkpoint_file, i, results)

                self._log(f"✅ Stage COMPLETE: {stage_name} (checkpoint saved)", "SUCCESS")

            except Exception as e:
                self._log(f"❌ Stage EXCEPTION: {stage_name} - {e}", "ERROR")

                # Save checkpoint
                self._save_checkpoint(checkpoint_file, i - 1, results)

                return {
                    "status": "failed",
                    "stages_completed": i,
                    "failed_stage": stage_name,
                    "error": str(e),
                    "results": results,
                    "duration_seconds": (datetime.now() - start_time).total_seconds(),
                    "strategy": "checkpoint",
                    "resumed": resumed,
                    "checkpoint_saved": True
                }

        # All stages completed - clear checkpoint
        self._clear_checkpoint(checkpoint_file)

        duration = (datetime.now() - start_time).total_seconds()

        self._log(f"💾 CHECKPOINT pipeline COMPLETE! ({duration:.1f}s, resumed: {resumed})", "SUCCESS")

        return {
            "status": "success",
            "stages_completed": len(stages),
            "results": results,
            "duration_seconds": duration,
            "strategy": "checkpoint",
            "resumed": resumed,
            "checkpoint_cleared": True
        }

    def _load_checkpoint(self, checkpoint_file: Path) -> tuple[int, Dict]:
        """
        Load checkpoint from file.

        Returns:
            Tuple of (last_completed_stage_index, checkpoint_data)
            Returns (-1, {}) if no checkpoint exists
        """
        if not checkpoint_file.exists():
            return -1, {}

        try:
            with open(checkpoint_file) as f:
                data = json.load(f)

            last_stage = data.get("last_completed_stage", -1)

            self._log(f"   Loaded checkpoint: {checkpoint_file.name}")
            self._log(f"   Last completed stage: {last_stage + 1}")

            return last_stage, data

        except Exception as e:
            self._log(f"   ⚠️  Failed to load checkpoint: {e}", "WARNING")
            return -1, {}

    def _save_checkpoint(self, checkpoint_file: Path, stage_index: int, results: Dict):
        """Save checkpoint to file"""
        try:
            checkpoint_data = {
                "last_completed_stage": stage_index,
                "timestamp": datetime.now().isoformat(),
                "results": results
            }

            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)

            self._log(f"   💾 Checkpoint saved (stage {stage_index + 1})")

        except Exception as e:
            self._log(f"   ⚠️  Failed to save checkpoint: {e}", "WARNING")

    def _clear_checkpoint(self, checkpoint_file: Path):
        """Clear checkpoint file after successful completion"""
        try:
            if checkpoint_file.exists():
                checkpoint_file.unlink()
                self._log(f"   🗑️  Checkpoint cleared")
        except Exception as e:
            self._log(f"   ⚠️  Failed to clear checkpoint: {e}", "WARNING")


# ============================================================================
# STRATEGY FACTORY
# ============================================================================

def get_strategy(
    strategy_name: str,
    verbose: bool = True,
    **kwargs
) -> PipelineStrategy:
    """
    Factory function to create pipeline strategy by name.

    Args:
        strategy_name: Strategy name ("standard", "fast", "parallel", "checkpoint")
        verbose: Enable verbose logging
        **kwargs: Strategy-specific parameters

    Returns:
        PipelineStrategy instance

    Raises:
        ValueError: If strategy_name is unknown

    Examples:
        # Standard strategy
        strategy = get_strategy("standard")

        # Fast strategy with custom skip list
        strategy = get_strategy("fast", skip_stages=["architecture"])

        # Parallel strategy with custom worker count
        strategy = get_strategy("parallel", max_workers=8)

        # Checkpoint strategy with custom directory
        strategy = get_strategy("checkpoint", checkpoint_dir="/tmp/my_checkpoints")
    """
    strategies = {
        "standard": StandardPipelineStrategy,
        "fast": FastPipelineStrategy,
        "parallel": ParallelPipelineStrategy,
        "checkpoint": CheckpointPipelineStrategy
    }

    if strategy_name not in strategies:
        raise ValueError(
            f"Unknown strategy: {strategy_name}. "
            f"Available: {', '.join(strategies.keys())}"
        )

    strategy_class = strategies[strategy_name]
    return strategy_class(verbose=verbose, **kwargs)
