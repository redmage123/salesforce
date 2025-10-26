#!/usr/bin/env python3
"""
Artemis Checkpoint Manager - Pipeline Checkpoint and Resume

Enables pipeline execution to survive:
- Crashes and restarts
- System reboots
- Manual interruptions
- Resource exhaustion

Checkpoints save:
- Completed stages and their results
- Current execution state
- Stage outputs and artifacts
- LLM responses (for caching)
- Execution context

SOLID Principles:
- Single Responsibility: Only manages checkpoints
- Open/Closed: Extensible checkpoint formats
- Liskov Substitution: Storage backends interchangeable
- Interface Segregation: Minimal checkpoint interface
- Dependency Inversion: Depends on storage abstraction
"""

import json
import hashlib
import pickle
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
from debug_mixin import DebugMixin


# ============================================================================
# CHECKPOINT DATA MODELS
# ============================================================================

class CheckpointStatus(Enum):
    """Checkpoint status"""
    ACTIVE = "active"           # Pipeline running
    PAUSED = "paused"           # Pipeline paused
    COMPLETED = "completed"     # Pipeline finished
    FAILED = "failed"           # Pipeline failed
    RESUMED = "resumed"         # Resumed from checkpoint


@dataclass
class StageCheckpoint:
    """Checkpoint data for a single stage"""
    stage_name: str
    status: str  # completed, failed, skipped
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    result: Optional[Dict[str, Any]] = None
    artifacts: List[str] = field(default_factory=list)  # File paths
    llm_responses: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineCheckpoint:
    """Complete pipeline checkpoint"""
    checkpoint_id: str
    card_id: str
    status: CheckpointStatus
    created_at: datetime
    updated_at: datetime

    # Stage tracking
    completed_stages: List[str] = field(default_factory=list)
    failed_stages: List[str] = field(default_factory=list)
    skipped_stages: List[str] = field(default_factory=list)
    current_stage: Optional[str] = None

    # Stage details
    stage_checkpoints: Dict[str, StageCheckpoint] = field(default_factory=dict)

    # Execution context
    execution_context: Dict[str, Any] = field(default_factory=dict)

    # Statistics
    total_stages: int = 0
    stages_completed: int = 0
    total_duration_seconds: float = 0.0
    estimated_remaining_seconds: float = 0.0

    # Recovery info
    resume_count: int = 0
    last_resume_time: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "checkpoint_id": self.checkpoint_id,
            "card_id": self.card_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_stages": self.completed_stages,
            "failed_stages": self.failed_stages,
            "skipped_stages": self.skipped_stages,
            "current_stage": self.current_stage,
            "stage_checkpoints": {
                name: {
                    "stage_name": cp.stage_name,
                    "status": cp.status,
                    "start_time": cp.start_time.isoformat() if cp.start_time else None,
                    "end_time": cp.end_time.isoformat() if cp.end_time else None,
                    "duration_seconds": cp.duration_seconds,
                    "result": cp.result,
                    "artifacts": cp.artifacts,
                    "llm_responses": cp.llm_responses,
                    "error_message": cp.error_message,
                    "retry_count": cp.retry_count,
                    "metadata": cp.metadata
                }
                for name, cp in self.stage_checkpoints.items()
            },
            "execution_context": self.execution_context,
            "total_stages": self.total_stages,
            "stages_completed": self.stages_completed,
            "total_duration_seconds": self.total_duration_seconds,
            "estimated_remaining_seconds": self.estimated_remaining_seconds,
            "resume_count": self.resume_count,
            "last_resume_time": self.last_resume_time.isoformat() if self.last_resume_time else None,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PipelineCheckpoint':
        """Create checkpoint from dictionary"""
        # Parse stage checkpoints
        stage_checkpoints = {}
        for name, cp_data in data.get("stage_checkpoints", {}).items():
            stage_checkpoints[name] = StageCheckpoint(
                stage_name=cp_data["stage_name"],
                status=cp_data["status"],
                start_time=datetime.fromisoformat(cp_data["start_time"]) if cp_data.get("start_time") else datetime.now(),
                end_time=datetime.fromisoformat(cp_data["end_time"]) if cp_data.get("end_time") else None,
                duration_seconds=cp_data.get("duration_seconds", 0.0),
                result=cp_data.get("result"),
                artifacts=cp_data.get("artifacts", []),
                llm_responses=cp_data.get("llm_responses", []),
                error_message=cp_data.get("error_message"),
                retry_count=cp_data.get("retry_count", 0),
                metadata=cp_data.get("metadata", {})
            )

        return cls(
            checkpoint_id=data["checkpoint_id"],
            card_id=data["card_id"],
            status=CheckpointStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            completed_stages=data.get("completed_stages", []),
            failed_stages=data.get("failed_stages", []),
            skipped_stages=data.get("skipped_stages", []),
            current_stage=data.get("current_stage"),
            stage_checkpoints=stage_checkpoints,
            execution_context=data.get("execution_context", {}),
            total_stages=data.get("total_stages", 0),
            stages_completed=data.get("stages_completed", 0),
            total_duration_seconds=data.get("total_duration_seconds", 0.0),
            estimated_remaining_seconds=data.get("estimated_remaining_seconds", 0.0),
            resume_count=data.get("resume_count", 0),
            last_resume_time=datetime.fromisoformat(data["last_resume_time"]) if data.get("last_resume_time") else None,
            metadata=data.get("metadata", {})
        )


# ============================================================================
# CHECKPOINT MANAGER
# ============================================================================

class CheckpointManager(DebugMixin):
    """
    Manages pipeline checkpoints for crash recovery

    Features:
    - Save checkpoint after each stage completion
    - Resume from last checkpoint
    - Cache LLM responses to avoid re-running
    - Store artifacts and outputs
    - Track execution statistics
    """

    def __init__(
        self,
        card_id: str,
        checkpoint_dir: Optional[str] = None,
        enable_llm_cache: bool = True,
        verbose: bool = True
    ):
        """
        Initialize checkpoint manager

        Args:
            card_id: Kanban card ID
            checkpoint_dir: Directory for checkpoint storage (defaults to env var or repo path)
            enable_llm_cache: Enable LLM response caching
            verbose: Enable verbose logging
        """
        import os
        DebugMixin.__init__(self, component_name="checkpoint")
        self.card_id = card_id

        # Get checkpoint dir from parameter, env var, or default
        if checkpoint_dir is None:
            checkpoint_dir = os.getenv("ARTEMIS_CHECKPOINT_DIR", "../../.artemis_data/checkpoints")

        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True, parents=True)
        self.enable_llm_cache = enable_llm_cache
        self.verbose = verbose

        # Current checkpoint
        self.checkpoint: Optional[PipelineCheckpoint] = None

        # LLM response cache (in-memory)
        self.llm_cache: Dict[str, Any] = {}

        self.debug_log("Checkpoint manager initialized", card_id=card_id, checkpoint_dir=str(self.checkpoint_dir))
        if self.verbose:
            print(f"[CheckpointManager] Initialized for card {card_id}")
            print(f"[CheckpointManager] Checkpoint directory: {self.checkpoint_dir}")

    def create_checkpoint(
        self,
        total_stages: int,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> PipelineCheckpoint:
        """
        Create a new checkpoint

        Args:
            total_stages: Total number of stages in pipeline
            execution_context: Initial execution context

        Returns:
            New checkpoint
        """
        checkpoint_id = f"checkpoint-{self.card_id}-{int(time.time())}"

        self.checkpoint = PipelineCheckpoint(
            checkpoint_id=checkpoint_id,
            card_id=self.card_id,
            status=CheckpointStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            total_stages=total_stages,
            execution_context=execution_context or {}
        )

        self._save_checkpoint()

        if self.verbose:
            print(f"[CheckpointManager] Created checkpoint: {checkpoint_id}")

        return self.checkpoint

    def save_stage_checkpoint(
        self,
        stage_name: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        artifacts: Optional[List[str]] = None,
        llm_responses: Optional[List[Dict[str, Any]]] = None,
        error_message: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> None:
        """
        Save checkpoint for a completed stage

        Args:
            stage_name: Name of the stage
            status: Stage status (completed, failed, skipped)
            result: Stage execution result
            artifacts: List of artifact file paths
            llm_responses: LLM responses to cache
            error_message: Error message if failed
            start_time: Stage start time
            end_time: Stage end time
        """
        if not self.checkpoint:
            raise ValueError("No checkpoint created. Call create_checkpoint() first.")

        self.debug_log("Saving stage checkpoint", stage_name=stage_name, status=status, artifacts_count=len(artifacts or []))

        # Calculate duration
        duration = 0.0
        if start_time and end_time:
            duration = (end_time - start_time).total_seconds()

        # Create stage checkpoint
        stage_checkpoint = StageCheckpoint(
            stage_name=stage_name,
            status=status,
            start_time=start_time or datetime.now(),
            end_time=end_time or datetime.now(),
            duration_seconds=duration,
            result=result,
            artifacts=artifacts or [],
            llm_responses=llm_responses or [],
            error_message=error_message
        )

        # Update checkpoint
        self.checkpoint.stage_checkpoints[stage_name] = stage_checkpoint

        # Update stage lists using status mapping
        status_actions = {
            "completed": lambda: (
                self.checkpoint.completed_stages.append(stage_name),
                setattr(self.checkpoint, 'stages_completed', self.checkpoint.stages_completed + 1)
            ) if stage_name not in self.checkpoint.completed_stages else None,
            "failed": lambda: self.checkpoint.failed_stages.append(stage_name)
            if stage_name not in self.checkpoint.failed_stages else None,
            "skipped": lambda: self.checkpoint.skipped_stages.append(stage_name)
            if stage_name not in self.checkpoint.skipped_stages else None,
        }

        # Execute action for status
        action = status_actions.get(status)
        if action:
            action()

        self.checkpoint.total_duration_seconds += duration
        self.checkpoint.updated_at = datetime.now()

        # Cache LLM responses
        if self.enable_llm_cache and llm_responses:
            for response in llm_responses:
                cache_key = self._generate_llm_cache_key(
                    stage_name,
                    response.get("prompt", "")
                )
                self.llm_cache[cache_key] = response

        # Save checkpoint
        self._save_checkpoint()

        if self.verbose:
            print(f"[CheckpointManager] Saved stage checkpoint: {stage_name} ({status})")
            print(f"[CheckpointManager]    Duration: {duration:.2f}s")
            print(f"[CheckpointManager]    Progress: {self.checkpoint.stages_completed}/{self.checkpoint.total_stages}")

    def set_current_stage(self, stage_name: str) -> None:
        """
        Set the currently executing stage

        Args:
            stage_name: Stage name
        """
        if not self.checkpoint:
            raise ValueError("No checkpoint created.")

        self.checkpoint.current_stage = stage_name
        self.checkpoint.updated_at = datetime.now()
        self._save_checkpoint()

        if self.verbose:
            print(f"[CheckpointManager] Current stage: {stage_name}")

    def mark_completed(self) -> None:
        """Mark pipeline as completed"""
        if not self.checkpoint:
            return

        self.checkpoint.status = CheckpointStatus.COMPLETED
        self.checkpoint.current_stage = None
        self.checkpoint.updated_at = datetime.now()
        self._save_checkpoint()

        if self.verbose:
            print(f"[CheckpointManager] Pipeline completed!")
            print(f"[CheckpointManager]    Total duration: {self.checkpoint.total_duration_seconds:.2f}s")
            print(f"[CheckpointManager]    Stages completed: {self.checkpoint.stages_completed}/{self.checkpoint.total_stages}")

    def mark_failed(self, reason: str) -> None:
        """
        Mark pipeline as failed

        Args:
            reason: Failure reason
        """
        if not self.checkpoint:
            return

        self.checkpoint.status = CheckpointStatus.FAILED
        self.checkpoint.metadata["failure_reason"] = reason
        self.checkpoint.updated_at = datetime.now()
        self._save_checkpoint()

        if self.verbose:
            print(f"[CheckpointManager] Pipeline failed: {reason}")

    def can_resume(self) -> bool:
        """
        Check if there's a checkpoint to resume from

        Returns:
            True if checkpoint exists and can be resumed
        """
        checkpoint_file = self._get_checkpoint_file()

        if not checkpoint_file.exists():
            return False

        try:
            checkpoint = self._load_checkpoint()

            # Can resume if pipeline was active or paused
            can_resume = checkpoint.status in [CheckpointStatus.ACTIVE, CheckpointStatus.PAUSED]

            # Can't resume if completed or failed (unless explicitly allowed)
            if checkpoint.status == CheckpointStatus.COMPLETED:
                return False

            return can_resume
        except Exception as e:
            if self.verbose:
                print(f"[CheckpointManager] Cannot resume: {e}")
            return False

    def resume(self) -> Optional[PipelineCheckpoint]:
        """
        Resume from checkpoint

        Returns:
            Checkpoint if available, None otherwise
        """
        self.debug_log("Attempting to resume from checkpoint", card_id=self.card_id)

        if not self.can_resume():
            self.debug_log("Cannot resume - no valid checkpoint found")
            if self.verbose:
                print(f"[CheckpointManager] No checkpoint to resume from")
            return None

        self.checkpoint = self._load_checkpoint()
        self.checkpoint.status = CheckpointStatus.RESUMED
        self.checkpoint.resume_count += 1
        self.checkpoint.last_resume_time = datetime.now()
        self.checkpoint.updated_at = datetime.now()

        self.debug_log("Resumed from checkpoint", checkpoint_id=self.checkpoint.checkpoint_id, completed_stages=len(self.checkpoint.completed_stages))

        # Restore LLM cache
        if self.enable_llm_cache:
            for stage_name, stage_cp in self.checkpoint.stage_checkpoints.items():
                for response in stage_cp.llm_responses:
                    cache_key = self._generate_llm_cache_key(
                        stage_name,
                        response.get("prompt", "")
                    )
                    self.llm_cache[cache_key] = response

        self._save_checkpoint()

        if self.verbose:
            print(f"[CheckpointManager] Resumed from checkpoint!")
            print(f"[CheckpointManager]    Checkpoint ID: {self.checkpoint.checkpoint_id}")
            print(f"[CheckpointManager]    Completed stages: {len(self.checkpoint.completed_stages)}")
            print(f"[CheckpointManager]    Current stage: {self.checkpoint.current_stage}")
            print(f"[CheckpointManager]    Resume count: {self.checkpoint.resume_count}")

        return self.checkpoint

    def get_cached_llm_response(
        self,
        stage_name: str,
        prompt: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached LLM response if available

        Args:
            stage_name: Stage name
            prompt: LLM prompt

        Returns:
            Cached response or None
        """
        if not self.enable_llm_cache:
            return None

        cache_key = self._generate_llm_cache_key(stage_name, prompt)
        cached = self.llm_cache.get(cache_key)

        if cached and self.verbose:
            print(f"[CheckpointManager] ✅ LLM cache hit for {stage_name}")

        return cached

    def get_next_stage(self, all_stages: List[str]) -> Optional[str]:
        """
        Get the next stage to execute after resume

        Args:
            all_stages: List of all stages in order

        Returns:
            Next stage name or None if all completed
        """
        if not self.checkpoint:
            return all_stages[0] if all_stages else None

        # Find first stage not completed
        for stage in all_stages:
            if stage not in self.checkpoint.completed_stages:
                return stage

        return None  # All stages completed

    def get_progress(self) -> Dict[str, Any]:
        """
        Get execution progress

        Returns:
            Progress statistics
        """
        if not self.checkpoint:
            return {
                "progress_percent": 0,
                "stages_completed": 0,
                "total_stages": 0,
                "current_stage": None,
                "elapsed_seconds": 0,
                "estimated_remaining_seconds": 0
            }

        elapsed = (datetime.now() - self.checkpoint.created_at).total_seconds()

        # Estimate remaining time
        if self.checkpoint.stages_completed > 0:
            avg_stage_duration = self.checkpoint.total_duration_seconds / self.checkpoint.stages_completed
            remaining_stages = self.checkpoint.total_stages - self.checkpoint.stages_completed
            estimated_remaining = avg_stage_duration * remaining_stages
        else:
            estimated_remaining = 0

        progress_percent = (self.checkpoint.stages_completed / self.checkpoint.total_stages * 100) if self.checkpoint.total_stages > 0 else 0

        return {
            "progress_percent": round(progress_percent, 2),
            "stages_completed": self.checkpoint.stages_completed,
            "total_stages": self.checkpoint.total_stages,
            "current_stage": self.checkpoint.current_stage,
            "elapsed_seconds": round(elapsed, 2),
            "estimated_remaining_seconds": round(estimated_remaining, 2)
        }

    def _save_checkpoint(self) -> None:
        """Save checkpoint to disk"""
        if not self.checkpoint:
            return

        checkpoint_file = self._get_checkpoint_file()

        with open(checkpoint_file, 'w') as f:
            json.dump(self.checkpoint.to_dict(), f, indent=2)

    def _load_checkpoint(self) -> PipelineCheckpoint:
        """Load checkpoint from disk"""
        checkpoint_file = self._get_checkpoint_file()

        with open(checkpoint_file, 'r') as f:
            data = json.load(f)

        return PipelineCheckpoint.from_dict(data)

    def _get_checkpoint_file(self) -> Path:
        """Get checkpoint file path"""
        return self.checkpoint_dir / f"{self.card_id}.json"

    def _generate_llm_cache_key(self, stage_name: str, prompt: str) -> str:
        """
        Generate cache key for LLM response

        Args:
            stage_name: Stage name
            prompt: LLM prompt

        Returns:
            Cache key
        """
        # Hash the prompt for cache key
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        return f"{self.card_id}:{stage_name}:{prompt_hash}"

    def clear_checkpoint(self) -> None:
        """Clear checkpoint (delete from disk)"""
        self.debug_log("Clearing checkpoint", card_id=self.card_id)

        checkpoint_file = self._get_checkpoint_file()

        if checkpoint_file.exists():
            checkpoint_file.unlink()

        self.checkpoint = None
        self.llm_cache.clear()

        self.debug_log("Checkpoint cleared", card_id=self.card_id)
        if self.verbose:
            print(f"[CheckpointManager] Checkpoint cleared")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_checkpoint_manager(
    card_id: str,
    verbose: bool = True
) -> CheckpointManager:
    """
    Create checkpoint manager

    Args:
        card_id: Card ID
        verbose: Enable verbose logging

    Returns:
        CheckpointManager instance
    """
    return CheckpointManager(card_id=card_id, verbose=verbose)
