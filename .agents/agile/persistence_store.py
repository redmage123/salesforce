#!/usr/bin/env python3
"""
Persistence Store - Database-backed Pipeline State Storage

Provides persistent storage for pipeline state, enabling:
- Resume from crashes
- Full audit trail
- Historical analysis
- Recovery from any stage

Supports multiple backends:
- SQLite (default, file-based)
- PostgreSQL (production, distributed)
- JSON files (fallback, simple)
"""

import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict


@dataclass
class PipelineState:
    """Complete pipeline state snapshot"""
    card_id: str
    status: str  # running, completed, failed, paused
    current_stage: Optional[str]
    stages_completed: List[str]
    stage_results: Dict[str, Any]
    developer_results: List[Dict]
    metrics: Dict[str, Any]
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


@dataclass
class StageCheckpoint:
    """Checkpoint for a single stage"""
    card_id: str
    stage_name: str
    status: str  # started, completed, failed
    started_at: str
    completed_at: Optional[str]
    result: Dict[str, Any]
    error: Optional[str] = None


class PersistenceStoreInterface(ABC):
    """Abstract interface for persistence stores"""

    @abstractmethod
    def save_pipeline_state(self, state: PipelineState):
        """Save complete pipeline state"""
        pass

    @abstractmethod
    def load_pipeline_state(self, card_id: str) -> Optional[PipelineState]:
        """Load pipeline state by card ID"""
        pass

    @abstractmethod
    def save_stage_checkpoint(self, checkpoint: StageCheckpoint):
        """Save stage checkpoint"""
        pass

    @abstractmethod
    def load_stage_checkpoints(self, card_id: str) -> List[StageCheckpoint]:
        """Load all stage checkpoints for a card"""
        pass

    @abstractmethod
    def get_resumable_pipelines(self) -> List[str]:
        """Get list of pipeline card IDs that can be resumed"""
        pass

    @abstractmethod
    def cleanup_old_states(self, days: int = 30):
        """Clean up states older than X days"""
        pass


class SQLitePersistenceStore(PersistenceStoreInterface):
    """
    SQLite-based persistence store

    Benefits:
    - File-based (no server needed)
    - ACID transactions
    - SQL queries for analysis
    - Good for single-machine deployment
    """

    def __init__(self, db_path: str = "../../.artemis_data/artemis_persistence.db"):
        """
        Initialize SQLite store

        Args:
            db_path: Path to SQLite database file (relative to .agents/agile)
        """
        # Convert relative path to absolute
        if not os.path.isabs(db_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, db_path)

        self.db_path = db_path

        # Ensure parent directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row  # Enable dict access
        self._create_tables()

    def _create_tables(self):
        """Create database tables if they don't exist"""
        cursor = self.connection.cursor()

        # Pipeline states table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_states (
                card_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                current_stage TEXT,
                stages_completed TEXT,  -- JSON array
                stage_results TEXT,     -- JSON object
                developer_results TEXT, -- JSON array
                metrics TEXT,           -- JSON object
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                error TEXT
            )
        """)

        # Stage checkpoints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stage_checkpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id TEXT NOT NULL,
                stage_name TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                result TEXT,  -- JSON object
                error TEXT,
                UNIQUE(card_id, stage_name, started_at)
            )
        """)

        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pipeline_status
            ON pipeline_states(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_stage_card_id
            ON stage_checkpoints(card_id)
        """)

        self.connection.commit()

    def save_pipeline_state(self, state: PipelineState):
        """Save complete pipeline state"""
        cursor = self.connection.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO pipeline_states (
                card_id, status, current_stage, stages_completed,
                stage_results, developer_results, metrics,
                created_at, updated_at, completed_at, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            state.card_id,
            state.status,
            state.current_stage,
            json.dumps(state.stages_completed),
            json.dumps(state.stage_results),
            json.dumps(state.developer_results),
            json.dumps(state.metrics),
            state.created_at,
            state.updated_at,
            state.completed_at,
            state.error
        ))

        self.connection.commit()

    def load_pipeline_state(self, card_id: str) -> Optional[PipelineState]:
        """Load pipeline state by card ID"""
        cursor = self.connection.cursor()

        cursor.execute("""
            SELECT * FROM pipeline_states WHERE card_id = ?
        """, (card_id,))

        row = cursor.fetchone()
        if not row:
            return None

        return PipelineState(
            card_id=row['card_id'],
            status=row['status'],
            current_stage=row['current_stage'],
            stages_completed=json.loads(row['stages_completed']),
            stage_results=json.loads(row['stage_results']),
            developer_results=json.loads(row['developer_results']),
            metrics=json.loads(row['metrics']),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            completed_at=row['completed_at'],
            error=row['error']
        )

    def save_stage_checkpoint(self, checkpoint: StageCheckpoint):
        """Save stage checkpoint"""
        cursor = self.connection.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO stage_checkpoints (
                card_id, stage_name, status, started_at,
                completed_at, result, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            checkpoint.card_id,
            checkpoint.stage_name,
            checkpoint.status,
            checkpoint.started_at,
            checkpoint.completed_at,
            json.dumps(checkpoint.result),
            checkpoint.error
        ))

        self.connection.commit()

    def load_stage_checkpoints(self, card_id: str) -> List[StageCheckpoint]:
        """Load all stage checkpoints for a card"""
        cursor = self.connection.cursor()

        cursor.execute("""
            SELECT * FROM stage_checkpoints
            WHERE card_id = ?
            ORDER BY started_at ASC
        """, (card_id,))

        checkpoints = []
        for row in cursor.fetchall():
            checkpoints.append(StageCheckpoint(
                card_id=row['card_id'],
                stage_name=row['stage_name'],
                status=row['status'],
                started_at=row['started_at'],
                completed_at=row['completed_at'],
                result=json.loads(row['result']),
                error=row['error']
            ))

        return checkpoints

    def get_resumable_pipelines(self) -> List[str]:
        """Get list of pipeline card IDs that can be resumed"""
        cursor = self.connection.cursor()

        cursor.execute("""
            SELECT card_id FROM pipeline_states
            WHERE status IN ('running', 'failed', 'paused')
            ORDER BY updated_at DESC
        """)

        return [row['card_id'] for row in cursor.fetchall()]

    def cleanup_old_states(self, days: int = 30):
        """Clean up states older than X days"""
        from datetime import timedelta

        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat() + 'Z'

        cursor = self.connection.cursor()

        # Delete old completed/failed pipelines
        cursor.execute("""
            DELETE FROM pipeline_states
            WHERE status IN ('completed', 'failed')
            AND updated_at < ?
        """, (cutoff,))

        # Delete associated checkpoints
        cursor.execute("""
            DELETE FROM stage_checkpoints
            WHERE card_id NOT IN (SELECT card_id FROM pipeline_states)
        """)

        self.connection.commit()

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        cursor = self.connection.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM pipeline_states")
        total = cursor.fetchone()['total']

        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM pipeline_states
            GROUP BY status
        """)
        by_status = {row['status']: row['count'] for row in cursor.fetchall()}

        cursor.execute("SELECT COUNT(*) as total FROM stage_checkpoints")
        total_checkpoints = cursor.fetchone()['total']

        return {
            "total_pipelines": total,
            "by_status": by_status,
            "total_checkpoints": total_checkpoints,
            "db_path": self.db_path
        }

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()


class JSONFilePersistenceStore(PersistenceStoreInterface):
    """
    JSON file-based persistence store (fallback)

    Simple file-based storage for when database is not available.
    Good for development/testing.
    """

    def __init__(self, storage_dir: str = "../../.artemis_data/persistence"):
        """
        Initialize JSON file store

        Args:
            storage_dir: Directory to store JSON files (relative to .agents/agile)
        """
        # Convert relative path to absolute
        if not os.path.isabs(storage_dir):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            storage_dir = os.path.join(script_dir, storage_dir)

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True, parents=True)

    def save_pipeline_state(self, state: PipelineState):
        """Save pipeline state to JSON file"""
        file_path = self.storage_dir / f"{state.card_id}_state.json"
        with open(file_path, 'w') as f:
            json.dump(asdict(state), f, indent=2)

    def load_pipeline_state(self, card_id: str) -> Optional[PipelineState]:
        """Load pipeline state from JSON file"""
        file_path = self.storage_dir / f"{card_id}_state.json"
        if not file_path.exists():
            return None

        with open(file_path) as f:
            data = json.load(f)
            return PipelineState(**data)

    def save_stage_checkpoint(self, checkpoint: StageCheckpoint):
        """Save stage checkpoint to JSON file"""
        file_path = self.storage_dir / f"{checkpoint.card_id}_checkpoints.json"

        # Load existing checkpoints
        checkpoints = []
        if file_path.exists():
            with open(file_path) as f:
                checkpoints = json.load(f)

        # Append new checkpoint
        checkpoints.append(asdict(checkpoint))

        # Save
        with open(file_path, 'w') as f:
            json.dump(checkpoints, f, indent=2)

    def load_stage_checkpoints(self, card_id: str) -> List[StageCheckpoint]:
        """Load stage checkpoints from JSON file"""
        file_path = self.storage_dir / f"{card_id}_checkpoints.json"
        if not file_path.exists():
            return []

        with open(file_path) as f:
            data = json.load(f)
            return [StageCheckpoint(**cp) for cp in data]

    def get_resumable_pipelines(self) -> List[str]:
        """Get list of resumable pipelines"""
        resumable = []
        for file_path in self.storage_dir.glob("*_state.json"):
            with open(file_path) as f:
                state = json.load(f)
                if state['status'] in ['running', 'failed', 'paused']:
                    resumable.append(state['card_id'])
        return resumable

    def cleanup_old_states(self, days: int = 30):
        """Clean up old state files"""
        from datetime import timedelta
        import os

        cutoff = datetime.utcnow() - timedelta(days=days)

        for file_path in self.storage_dir.glob("*.json"):
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            if mtime < cutoff:
                file_path.unlink()


class PersistenceStoreFactory:
    """Factory for creating persistence stores"""

    @staticmethod
    def create(store_type: str = "sqlite", **kwargs) -> PersistenceStoreInterface:
        """
        Create persistence store

        Args:
            store_type: "sqlite", "postgres", or "json"
            **kwargs: Store-specific arguments

        Returns:
            PersistenceStoreInterface implementation
        """
        if store_type == "sqlite":
            db_path = kwargs.get("db_path", "../../.artemis_data/artemis_persistence.db")
            return SQLitePersistenceStore(db_path=db_path)

        elif store_type == "json":
            storage_dir = kwargs.get("storage_dir", "../../.artemis_data/persistence")
            return JSONFilePersistenceStore(storage_dir=storage_dir)

        elif store_type == "postgres":
            # Future implementation
            raise NotImplementedError("PostgreSQL persistence store coming soon")

        else:
            raise ValueError(f"Unknown store type: {store_type}")

    @staticmethod
    def create_from_env() -> PersistenceStoreInterface:
        """Create persistence store from environment variables"""
        import os

        store_type = os.getenv("ARTEMIS_PERSISTENCE_TYPE", "sqlite")

        if store_type == "sqlite":
            db_path = os.getenv("ARTEMIS_PERSISTENCE_DB", "../../.artemis_data/artemis_persistence.db")
            return SQLitePersistenceStore(db_path=db_path)

        elif store_type == "json":
            storage_dir = os.getenv("ARTEMIS_PERSISTENCE_DIR", "../../.artemis_data/persistence")
            return JSONFilePersistenceStore(storage_dir=storage_dir)

        else:
            # Default to SQLite
            return SQLitePersistenceStore()


if __name__ == "__main__":
    """Example usage and testing"""

    print("Persistence Store - Example Usage")
    print("=" * 70)

    # Create store
    store = PersistenceStoreFactory.create("sqlite", db_path="/tmp/test_persistence.db")

    # Save pipeline state
    state = PipelineState(
        card_id="test-card-001",
        status="running",
        current_stage="development",
        stages_completed=["project_analysis", "architecture"],
        stage_results={"architecture": {"adr": "ADR-001.md"}},
        developer_results=[],
        metrics={"stages_completed": 2},
        created_at=datetime.utcnow().isoformat() + 'Z',
        updated_at=datetime.utcnow().isoformat() + 'Z'
    )

    store.save_pipeline_state(state)
    print(f"✅ Saved pipeline state: {state.card_id}")

    # Save stage checkpoint
    checkpoint = StageCheckpoint(
        card_id="test-card-001",
        stage_name="architecture",
        status="completed",
        started_at=datetime.utcnow().isoformat() + 'Z',
        completed_at=datetime.utcnow().isoformat() + 'Z',
        result={"adr_file": "ADR-001.md"}
    )

    store.save_stage_checkpoint(checkpoint)
    print(f"✅ Saved stage checkpoint: {checkpoint.stage_name}")

    # Load pipeline state
    loaded_state = store.load_pipeline_state("test-card-001")
    print(f"✅ Loaded pipeline state: status={loaded_state.status}")

    # Get resumable pipelines
    resumable = store.get_resumable_pipelines()
    print(f"✅ Resumable pipelines: {resumable}")

    # Get statistics
    stats = store.get_statistics()
    print(f"✅ Database statistics:")
    print(f"   Total pipelines: {stats['total_pipelines']}")
    print(f"   By status: {stats['by_status']}")
    print(f"   Total checkpoints: {stats['total_checkpoints']}")

    print("\n" + "=" * 70)
    print("✅ Persistence store working correctly!")
