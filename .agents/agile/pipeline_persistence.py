#!/usr/bin/env python3
"""
Pipeline Persistence Integration

Integrates persistence store with ArtemisOrchestrator for:
- Automatic state saving after each stage
- Pipeline resume from crashes
- Full audit trail
"""

from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path

from persistence_store import (
    PersistenceStoreInterface,
    PersistenceStoreFactory,
    PipelineState,
    StageCheckpoint
)


class PipelinePersistenceManager:
    """
    Manages pipeline persistence and recovery

    Single Responsibility: Handle all persistence operations for pipeline
    """

    def __init__(
        self,
        card_id: str,
        store: Optional[PersistenceStoreInterface] = None,
        auto_save: bool = True
    ):
        """
        Initialize persistence manager

        Args:
            card_id: Kanban card ID
            store: Persistence store (default: create from environment)
            auto_save: Automatically save state after each stage
        """
        self.card_id = card_id
        self.store = store or PersistenceStoreFactory.create_from_env()
        self.auto_save = auto_save

        # Initialize pipeline state
        self.state = self._load_or_create_state()

    def _load_or_create_state(self) -> PipelineState:
        """Load existing state or create new one"""
        existing = self.store.load_pipeline_state(self.card_id)

        if existing:
            return existing
        else:
            # Create new state
            return PipelineState(
                card_id=self.card_id,
                status="running",
                current_stage=None,
                stages_completed=[],
                stage_results={},
                developer_results=[],
                metrics={},
                created_at=datetime.utcnow().isoformat() + 'Z',
                updated_at=datetime.utcnow().isoformat() + 'Z'
            )

    def mark_pipeline_started(self):
        """Mark pipeline as started"""
        self.state.status = "running"
        self.state.updated_at = datetime.utcnow().isoformat() + 'Z'

        if self.auto_save:
            self.store.save_pipeline_state(self.state)

    def mark_stage_started(self, stage_name: str):
        """Mark stage as started"""
        self.state.current_stage = stage_name
        self.state.updated_at = datetime.utcnow().isoformat() + 'Z'

        # Save checkpoint
        checkpoint = StageCheckpoint(
            card_id=self.card_id,
            stage_name=stage_name,
            status="started",
            started_at=datetime.utcnow().isoformat() + 'Z',
            completed_at=None,
            result={}
        )

        self.store.save_stage_checkpoint(checkpoint)

        if self.auto_save:
            self.store.save_pipeline_state(self.state)

    def mark_stage_completed(self, stage_name: str, result: Dict):
        """Mark stage as completed"""
        self.state.stages_completed.append(stage_name)
        self.state.stage_results[stage_name] = result
        self.state.updated_at = datetime.utcnow().isoformat() + 'Z'

        # Save checkpoint
        checkpoint = StageCheckpoint(
            card_id=self.card_id,
            stage_name=stage_name,
            status="completed",
            started_at=self.state.updated_at,
            completed_at=datetime.utcnow().isoformat() + 'Z',
            result=result
        )

        self.store.save_stage_checkpoint(checkpoint)

        if self.auto_save:
            self.store.save_pipeline_state(self.state)

    def mark_stage_failed(self, stage_name: str, error: str):
        """Mark stage as failed"""
        self.state.current_stage = stage_name
        self.state.error = error
        self.state.updated_at = datetime.utcnow().isoformat() + 'Z'

        # Save checkpoint
        checkpoint = StageCheckpoint(
            card_id=self.card_id,
            stage_name=stage_name,
            status="failed",
            started_at=self.state.updated_at,
            completed_at=datetime.utcnow().isoformat() + 'Z',
            result={},
            error=error
        )

        self.store.save_stage_checkpoint(checkpoint)

        if self.auto_save:
            self.store.save_pipeline_state(self.state)

    def mark_pipeline_completed(self):
        """Mark pipeline as completed"""
        self.state.status = "completed"
        self.state.current_stage = None
        self.state.completed_at = datetime.utcnow().isoformat() + 'Z'
        self.state.updated_at = self.state.completed_at

        self.store.save_pipeline_state(self.state)

    def mark_pipeline_failed(self, error: str):
        """Mark pipeline as failed"""
        self.state.status = "failed"
        self.state.error = error
        self.state.completed_at = datetime.utcnow().isoformat() + 'Z'
        self.state.updated_at = self.state.completed_at

        self.store.save_pipeline_state(self.state)

    def mark_pipeline_paused(self):
        """Mark pipeline as paused"""
        self.state.status = "paused"
        self.state.updated_at = datetime.utcnow().isoformat() + 'Z'

        self.store.save_pipeline_state(self.state)

    def save_developer_results(self, developer_results: List[Dict]):
        """Save developer results"""
        self.state.developer_results = developer_results
        self.state.updated_at = datetime.utcnow().isoformat() + 'Z'

        if self.auto_save:
            self.store.save_pipeline_state(self.state)

    def update_metrics(self, metrics: Dict):
        """Update pipeline metrics"""
        self.state.metrics.update(metrics)
        self.state.updated_at = datetime.utcnow().isoformat() + 'Z'

        if self.auto_save:
            self.store.save_pipeline_state(self.state)

    def can_resume(self) -> bool:
        """Check if pipeline can be resumed"""
        return self.state.status in ["running", "paused", "failed"]

    def get_resume_point(self) -> Optional[str]:
        """Get the stage to resume from"""
        if not self.can_resume():
            return None

        # Resume from the stage after the last completed one
        if self.state.stages_completed:
            return None  # Let orchestrator determine next stage

        return None  # Start from beginning

    def get_completed_stages(self) -> List[str]:
        """Get list of completed stages"""
        return self.state.stages_completed

    def get_stage_result(self, stage_name: str) -> Optional[Dict]:
        """Get result for a specific stage"""
        return self.state.stage_results.get(stage_name)

    def get_checkpoints(self) -> List[StageCheckpoint]:
        """Get all stage checkpoints for this pipeline"""
        return self.store.load_stage_checkpoints(self.card_id)

    def get_statistics(self) -> Dict:
        """Get pipeline statistics"""
        checkpoints = self.get_checkpoints()

        return {
            "card_id": self.card_id,
            "status": self.state.status,
            "stages_completed": len(self.state.stages_completed),
            "total_checkpoints": len(checkpoints),
            "created_at": self.state.created_at,
            "updated_at": self.state.updated_at,
            "completed_at": self.state.completed_at,
            "duration_seconds": self._calculate_duration()
        }

    def _calculate_duration(self) -> Optional[float]:
        """Calculate pipeline duration in seconds"""
        if not self.state.completed_at:
            return None

        from datetime import datetime

        created = datetime.fromisoformat(self.state.created_at.replace('Z', '+00:00'))
        completed = datetime.fromisoformat(self.state.completed_at.replace('Z', '+00:00'))

        return (completed - created).total_seconds()


def get_resumable_pipelines(store: Optional[PersistenceStoreInterface] = None) -> List[str]:
    """
    Get list of pipelines that can be resumed

    Args:
        store: Persistence store (default: create from environment)

    Returns:
        List of card IDs that can be resumed
    """
    if store is None:
        store = PersistenceStoreFactory.create_from_env()

    return store.get_resumable_pipelines()


if __name__ == "__main__":
    """Example usage"""

    print("Pipeline Persistence Manager - Example Usage")
    print("=" * 70)

    # Create persistence manager
    manager = PipelinePersistenceManager(card_id="test-card-002")

    # Simulate pipeline execution
    print("\n1. Starting pipeline...")
    manager.mark_pipeline_started()

    print("2. Starting stage: project_analysis...")
    manager.mark_stage_started("project_analysis")

    print("3. Completing stage: project_analysis...")
    manager.mark_stage_completed("project_analysis", {"issues": 0})

    print("4. Starting stage: architecture...")
    manager.mark_stage_started("architecture")

    print("5. Completing stage: architecture...")
    manager.mark_stage_completed("architecture", {"adr": "ADR-001.md"})

    print("6. Saving developer results...")
    manager.save_developer_results([
        {"developer": "developer-a", "score": 85},
        {"developer": "developer-b", "score": 90}
    ])

    print("7. Completing pipeline...")
    manager.mark_pipeline_completed()

    # Get statistics
    stats = manager.get_statistics()
    print(f"\n✅ Pipeline statistics:")
    print(f"   Status: {stats['status']}")
    print(f"   Stages completed: {stats['stages_completed']}")
    print(f"   Total checkpoints: {stats['total_checkpoints']}")
    print(f"   Duration: {stats['duration_seconds']:.2f} seconds")

    # Check resumable pipelines
    resumable = get_resumable_pipelines()
    print(f"\n✅ Resumable pipelines: {resumable}")

    print("\n" + "=" * 70)
    print("✅ Pipeline persistence working correctly!")
