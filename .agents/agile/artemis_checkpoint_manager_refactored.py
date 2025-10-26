#!/usr/bin/env python3
"""
Checkpoint Manager - Refactored with Design Patterns

Patterns Applied:
- Strategy Pattern: Pluggable storage backends
- Builder Pattern: Checkpoint construction
- Repository Pattern: Data access abstraction
- Value Object Pattern: Immutable domain objects

Benefits:
- Testable (mock storage)
- Extensible (add storage backends)
- Maintainable (separated concerns)
- Type-safe (strong domain objects)
"""

import json
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import os


# ============================================================================
# ENUMS - Eliminate Magic Strings
# ============================================================================

class StageStatus(Enum):
    """Stage execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class CheckpointStatus(Enum):
    """Overall checkpoint status"""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RESUMED = "resumed"


# ============================================================================
# VALUE OBJECTS - Rich Domain Models
# ============================================================================

@dataclass(frozen=True)
class StageResult:
    """Immutable stage execution result"""
    stage_name: str
    status: StageStatus
    start_time: str
    end_time: Optional[str]
    duration_seconds: float
    error_message: Optional[str] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)

    def is_successful(self) -> bool:
        """Check if stage completed successfully"""
        return self.status == StageStatus.COMPLETED

    def is_terminal(self) -> bool:
        """Check if stage is in terminal state"""
        return self.status in (StageStatus.COMPLETED, StageStatus.FAILED, StageStatus.SKIPPED)


@dataclass
class Checkpoint:
    """
    Checkpoint representing pipeline state snapshot

    Not frozen to allow updates during pipeline execution
    """
    checkpoint_id: str
    card_id: str
    status: CheckpointStatus
    created_at: str
    updated_at: str
    total_stages: int
    stages_completed: int
    completed_stages: List[str]
    failed_stages: List[str]
    stage_results: Dict[str, StageResult]
    current_stage: Optional[str]
    total_duration_seconds: float
    resume_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_complete(self) -> bool:
        """Check if all stages are completed"""
        return self.stages_completed == self.total_stages

    def is_failed(self) -> bool:
        """Check if checkpoint has failed stages"""
        return len(self.failed_stages) > 0

    def get_progress_percentage(self) -> float:
        """Get completion percentage"""
        if self.total_stages == 0:
            return 0.0
        return (self.stages_completed / self.total_stages) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "checkpoint_id": self.checkpoint_id,
            "card_id": self.card_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_stages": self.total_stages,
            "stages_completed": self.stages_completed,
            "completed_stages": self.completed_stages,
            "failed_stages": self.failed_stages,
            "stage_results": {
                name: {
                    "stage_name": result.stage_name,
                    "status": result.status.value,
                    "start_time": result.start_time,
                    "end_time": result.end_time,
                    "duration_seconds": result.duration_seconds,
                    "error_message": result.error_message,
                    "artifacts": result.artifacts
                }
                for name, result in self.stage_results.items()
            },
            "current_stage": self.current_stage,
            "total_duration_seconds": self.total_duration_seconds,
            "resume_count": self.resume_count,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Checkpoint':
        """Create checkpoint from dictionary"""
        stage_results = {}
        for name, result_data in data.get("stage_results", {}).items():
            stage_results[name] = StageResult(
                stage_name=result_data["stage_name"],
                status=StageStatus(result_data["status"]),
                start_time=result_data["start_time"],
                end_time=result_data.get("end_time"),
                duration_seconds=result_data["duration_seconds"],
                error_message=result_data.get("error_message"),
                artifacts=result_data.get("artifacts", {})
            )

        return cls(
            checkpoint_id=data["checkpoint_id"],
            card_id=data["card_id"],
            status=CheckpointStatus(data["status"]),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            total_stages=data["total_stages"],
            stages_completed=data["stages_completed"],
            completed_stages=data["completed_stages"],
            failed_stages=data["failed_stages"],
            stage_results=stage_results,
            current_stage=data.get("current_stage"),
            total_duration_seconds=data["total_duration_seconds"],
            resume_count=data.get("resume_count", 0),
            metadata=data.get("metadata", {})
        )


# ============================================================================
# BUILDER PATTERN - Checkpoint Construction
# ============================================================================

class CheckpointBuilder:
    """Builder for constructing checkpoints"""

    def __init__(self, card_id: str):
        self._card_id = card_id
        self._checkpoint_id = self._generate_id(card_id)
        self._status = CheckpointStatus.IN_PROGRESS
        self._total_stages = 0
        self._stage_results: Dict[str, StageResult] = {}
        self._current_stage: Optional[str] = None
        self._metadata: Dict[str, Any] = {}
        self._resume_count = 0

    def with_total_stages(self, count: int) -> 'CheckpointBuilder':
        """Set total number of stages"""
        self._total_stages = count
        return self

    def with_current_stage(self, stage: str) -> 'CheckpointBuilder':
        """Set current stage"""
        self._current_stage = stage
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> 'CheckpointBuilder':
        """Add metadata"""
        self._metadata.update(metadata)
        return self

    def with_resume_count(self, count: int) -> 'CheckpointBuilder':
        """Set resume count"""
        self._resume_count = count
        return self

    def build(self) -> Checkpoint:
        """Build the checkpoint"""
        now = datetime.utcnow().isoformat() + 'Z'
        completed_stages = [
            name for name, result in self._stage_results.items()
            if result.is_successful()
        ]
        failed_stages = [
            name for name, result in self._stage_results.items()
            if result.status == StageStatus.FAILED
        ]

        return Checkpoint(
            checkpoint_id=self._checkpoint_id,
            card_id=self._card_id,
            status=self._status,
            created_at=now,
            updated_at=now,
            total_stages=self._total_stages,
            stages_completed=len(completed_stages),
            completed_stages=completed_stages,
            failed_stages=failed_stages,
            stage_results=self._stage_results,
            current_stage=self._current_stage,
            total_duration_seconds=sum(r.duration_seconds for r in self._stage_results.values()),
            resume_count=self._resume_count,
            metadata=self._metadata
        )

    @staticmethod
    def _generate_id(card_id: str) -> str:
        """Generate unique checkpoint ID"""
        timestamp = datetime.utcnow().isoformat()
        content = f"{card_id}-{timestamp}"
        return f"checkpoint-{hashlib.md5(content.encode()).hexdigest()[:8]}"


# ============================================================================
# STRATEGY PATTERN - Storage Backends
# ============================================================================

class CheckpointStorage(ABC):
    """Abstract storage strategy for checkpoints"""

    @abstractmethod
    def save(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint to storage"""
        pass

    @abstractmethod
    def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Load checkpoint from storage"""
        pass

    @abstractmethod
    def exists(self, checkpoint_id: str) -> bool:
        """Check if checkpoint exists"""
        pass

    @abstractmethod
    def list_checkpoints(self, card_id: str) -> List[str]:
        """List all checkpoint IDs for a card"""
        pass

    @abstractmethod
    def delete(self, checkpoint_id: str) -> bool:
        """Delete checkpoint"""
        pass


class FileCheckpointStorage(CheckpointStorage):
    """File-based checkpoint storage"""

    def __init__(self, checkpoint_dir: Path):
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint to JSON file"""
        file_path = self._get_path(checkpoint.checkpoint_id)
        with open(file_path, 'w') as f:
            json.dump(checkpoint.to_dict(), f, indent=2)

    def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Load checkpoint from JSON file"""
        file_path = self._get_path(checkpoint_id)
        if not file_path.exists():
            return None

        with open(file_path, 'r') as f:
            data = json.load(f)
            return Checkpoint.from_dict(data)

    def exists(self, checkpoint_id: str) -> bool:
        """Check if checkpoint file exists"""
        return self._get_path(checkpoint_id).exists()

    def list_checkpoints(self, card_id: str) -> List[str]:
        """List all checkpoint files for a card"""
        pattern = f"checkpoint-*-{card_id}.json"
        return [p.stem for p in self.checkpoint_dir.glob(pattern)]

    def delete(self, checkpoint_id: str) -> bool:
        """Delete checkpoint file"""
        file_path = self._get_path(checkpoint_id)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def _get_path(self, checkpoint_id: str) -> Path:
        """Get file path for checkpoint"""
        return self.checkpoint_dir / f"{checkpoint_id}.json"


class InMemoryCheckpointStorage(CheckpointStorage):
    """In-memory checkpoint storage (for testing)"""

    def __init__(self):
        self._checkpoints: Dict[str, Checkpoint] = {}

    def save(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint to memory"""
        self._checkpoints[checkpoint.checkpoint_id] = checkpoint

    def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Load checkpoint from memory"""
        return self._checkpoints.get(checkpoint_id)

    def exists(self, checkpoint_id: str) -> bool:
        """Check if checkpoint exists in memory"""
        return checkpoint_id in self._checkpoints

    def list_checkpoints(self, card_id: str) -> List[str]:
        """List all checkpoints for a card"""
        return [
            cp_id for cp_id, cp in self._checkpoints.items()
            if cp.card_id == card_id
        ]

    def delete(self, checkpoint_id: str) -> bool:
        """Delete checkpoint from memory"""
        if checkpoint_id in self._checkpoints:
            del self._checkpoints[checkpoint_id]
            return True
        return False


# ============================================================================
# REPOSITORY PATTERN - Data Access Layer
# ============================================================================

class CheckpointRepository:
    """Repository for checkpoint persistence"""

    def __init__(self, storage: CheckpointStorage):
        self.storage = storage

    def save(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint"""
        checkpoint.updated_at = datetime.utcnow().isoformat() + 'Z'
        self.storage.save(checkpoint)

    def find_by_id(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Find checkpoint by ID"""
        return self.storage.load(checkpoint_id)

    def find_latest_for_card(self, card_id: str) -> Optional[Checkpoint]:
        """Find most recent checkpoint for a card"""
        checkpoint_ids = self.storage.list_checkpoints(card_id)
        if not checkpoint_ids:
            return None

        # Load all and find most recent
        checkpoints = [
            self.storage.load(cp_id) for cp_id in checkpoint_ids
        ]
        checkpoints = [cp for cp in checkpoints if cp is not None]

        if not checkpoints:
            return None

        return max(checkpoints, key=lambda cp: cp.updated_at)

    def delete(self, checkpoint_id: str) -> bool:
        """Delete checkpoint"""
        return self.storage.delete(checkpoint_id)

    def exists(self, checkpoint_id: str) -> bool:
        """Check if checkpoint exists"""
        return self.storage.exists(checkpoint_id)


# ============================================================================
# FACADE - Simplified Manager Interface (Backward Compatible)
# ============================================================================

class CheckpointManager:
    """
    Checkpoint Manager Facade

    Provides backward-compatible interface while using new patterns internally.
    """

    def __init__(
        self,
        card_id: str,
        checkpoint_dir: Optional[str] = None,
        enable_llm_cache: bool = True,
        verbose: bool = True
    ):
        """Initialize checkpoint manager"""
        self.card_id = card_id
        self.verbose = verbose
        self.enable_llm_cache = enable_llm_cache

        # Get checkpoint dir from parameter, env var, or default
        if checkpoint_dir is None:
            checkpoint_dir = os.getenv("ARTEMIS_CHECKPOINT_DIR", "../../.artemis_data/checkpoints")

        # Initialize storage and repository
        storage = FileCheckpointStorage(Path(checkpoint_dir))
        self.repository = CheckpointRepository(storage)

        # Current checkpoint
        self.checkpoint: Optional[Checkpoint] = None

        if self.verbose:
            print(f"[CheckpointManager] Initialized for card {card_id}")
            print(f"[CheckpointManager] Checkpoint directory: {checkpoint_dir}")

    def create_checkpoint(self, total_stages: int, metadata: Optional[Dict[str, Any]] = None) -> Checkpoint:
        """Create new checkpoint"""
        builder = CheckpointBuilder(self.card_id)
        builder.with_total_stages(total_stages)

        if metadata:
            builder.with_metadata(metadata)

        self.checkpoint = builder.build()
        self.repository.save(self.checkpoint)

        if self.verbose:
            print(f"[CheckpointManager] Created checkpoint: {self.checkpoint.checkpoint_id}")

        return self.checkpoint

    def save_stage_result(
        self,
        stage_name: str,
        status: str,
        duration: float,
        error: Optional[str] = None,
        artifacts: Optional[Dict] = None
    ) -> None:
        """Save stage execution result"""
        if not self.checkpoint:
            raise ValueError("No active checkpoint")

        # Create stage result
        stage_status = StageStatus(status) if isinstance(status, str) else status
        result = StageResult(
            stage_name=stage_name,
            status=stage_status,
            start_time=datetime.utcnow().isoformat() + 'Z',
            end_time=datetime.utcnow().isoformat() + 'Z',
            duration_seconds=duration,
            error_message=error,
            artifacts=artifacts or {}
        )

        # Update checkpoint
        self.checkpoint.stage_results[stage_name] = result

        if result.is_successful():
            if stage_name not in self.checkpoint.completed_stages:
                self.checkpoint.completed_stages.append(stage_name)
                self.checkpoint.stages_completed += 1
        elif result.status == StageStatus.FAILED:
            if stage_name not in self.checkpoint.failed_stages:
                self.checkpoint.failed_stages.append(stage_name)

        self.checkpoint.total_duration_seconds = sum(
            r.duration_seconds for r in self.checkpoint.stage_results.values()
        )

        self.repository.save(self.checkpoint)

        if self.verbose:
            print(f"[CheckpointManager] Saved stage checkpoint: {stage_name} ({status})")
            print(f"[CheckpointManager]    Duration: {duration:.2f}s")
            print(f"[CheckpointManager]    Progress: {self.checkpoint.stages_completed}/{self.checkpoint.total_stages}")

    def set_current_stage(self, stage_name: str) -> None:
        """Set currently executing stage"""
        if not self.checkpoint:
            raise ValueError("No active checkpoint")

        self.checkpoint.current_stage = stage_name
        self.repository.save(self.checkpoint)

    def mark_completed(self) -> None:
        """Mark checkpoint as completed"""
        if not self.checkpoint:
            raise ValueError("No active checkpoint")

        self.checkpoint.status = CheckpointStatus.COMPLETED
        self.repository.save(self.checkpoint)

        if self.verbose:
            print(f"[CheckpointManager] ✅ Pipeline completed!")
            print(f"[CheckpointManager]    Total duration: {self.checkpoint.total_duration_seconds:.2f}s")
            print(f"[CheckpointManager]    Stages completed: {self.checkpoint.stages_completed}/{self.checkpoint.total_stages}")

    def mark_failed(self, reason: str) -> None:
        """Mark checkpoint as failed"""
        if not self.checkpoint:
            raise ValueError("No active checkpoint")

        self.checkpoint.status = CheckpointStatus.FAILED
        self.checkpoint.metadata["failure_reason"] = reason
        self.repository.save(self.checkpoint)

        if self.verbose:
            print(f"[CheckpointManager] ❌ Pipeline failed: {reason}")

    def resume_from_checkpoint(self) -> Optional[Checkpoint]:
        """Resume from most recent checkpoint"""
        checkpoint = self.repository.find_latest_for_card(self.card_id)

        if not checkpoint:
            if self.verbose:
                print(f"[CheckpointManager] No checkpoint to resume from")
            return None

        checkpoint.resume_count += 1
        checkpoint.status = CheckpointStatus.RESUMED
        self.checkpoint = checkpoint
        self.repository.save(checkpoint)

        if self.verbose:
            print(f"[CheckpointManager] Resumed from checkpoint!")
            print(f"[CheckpointManager]    Checkpoint ID: {checkpoint.checkpoint_id}")
            print(f"[CheckpointManager]    Completed stages: {len(checkpoint.completed_stages)}")
            print(f"[CheckpointManager]    Current stage: {checkpoint.current_stage}")
            print(f"[CheckpointManager]    Resume count: {checkpoint.resume_count}")

        return checkpoint


# ============================================================================
# FACTORY - Backward Compatibility
# ============================================================================

def create_checkpoint_manager(
    card_id: str,
    checkpoint_dir: Optional[str] = None,
    verbose: bool = True
) -> CheckpointManager:
    """Factory function for creating checkpoint manager"""
    return CheckpointManager(card_id=card_id, checkpoint_dir=checkpoint_dir, verbose=verbose)


if __name__ == "__main__":
    # Example usage
    manager = CheckpointManager("card-test-123", verbose=True)
    checkpoint = manager.create_checkpoint(total_stages=3, metadata={"test": "example"})

    manager.set_current_stage("stage1")
    manager.save_stage_result("stage1", "completed", 10.5)

    manager.set_current_stage("stage2")
    manager.save_stage_result("stage2", "completed", 5.3)

    manager.mark_completed()

    print("\n✅ Checkpoint Manager refactored successfully!")
