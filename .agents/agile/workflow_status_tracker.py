#!/usr/bin/env python3
"""
Workflow Status Tracker for Artemis
Tracks and persists workflow execution status
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from contextlib import contextmanager
import time


class WorkflowStatusTracker:
    """
    Tracks workflow execution status and persists to disk

    Usage:
        tracker = WorkflowStatusTracker(card_id="card-123")

        with tracker.track_workflow():
            with tracker.track_stage("STAGE_1", "Project Analysis"):
                # Do stage work
                pass
    """

    def __init__(self, card_id: str, status_dir: str = "../../.artemis_data/status"):
        self.card_id = card_id

        # Convert relative path to absolute
        if not os.path.isabs(status_dir):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            status_dir = os.path.join(script_dir, status_dir)

        self.status_dir = Path(status_dir)
        self.status_dir.mkdir(exist_ok=True, parents=True)
        self.status_file = self.status_dir / f"{card_id}.json"

        self.status_data = {
            'card_id': card_id,
            'status': 'not_started',
            'current_stage': None,
            'stages': [],
            'start_time': None,
            'end_time': None,
            'total_duration_seconds': None,
            'error': None
        }

    def start_workflow(self):
        """Mark workflow as started"""
        self.status_data['status'] = 'running'
        self.status_data['start_time'] = datetime.now().isoformat()
        self._save()

    def complete_workflow(self):
        """Mark workflow as completed"""
        self.status_data['status'] = 'completed'
        self.status_data['end_time'] = datetime.now().isoformat()
        self._calculate_duration()
        self.status_data['current_stage'] = None
        self._save()

    def fail_workflow(self, error_message: str):
        """Mark workflow as failed"""
        self.status_data['status'] = 'failed'
        self.status_data['end_time'] = datetime.now().isoformat()
        self.status_data['error'] = error_message
        self._calculate_duration()
        self._save()

    def start_stage(self, stage_id: str, stage_name: str):
        """Mark a stage as started"""
        self.status_data['current_stage'] = stage_name

        stage_data = {
            'id': stage_id,
            'name': stage_name,
            'status': 'in_progress',
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'duration_seconds': None,
            'error': None
        }

        self.status_data['stages'].append(stage_data)
        self._save()

    def complete_stage(self, stage_id: str):
        """Mark a stage as completed"""
        stage = self._find_stage(stage_id)
        if stage:
            stage['status'] = 'completed'
            stage['end_time'] = datetime.now().isoformat()
            stage['duration_seconds'] = self._calculate_stage_duration(stage)
            self._save()

    def fail_stage(self, stage_id: str, error_message: str):
        """Mark a stage as failed"""
        stage = self._find_stage(stage_id)
        if stage:
            stage['status'] = 'failed'
            stage['end_time'] = datetime.now().isoformat()
            stage['error'] = error_message
            stage['duration_seconds'] = self._calculate_stage_duration(stage)
            self._save()

    def skip_stage(self, stage_id: str, reason: str = None):
        """Mark a stage as skipped"""
        stage = self._find_stage(stage_id)
        if stage:
            stage['status'] = 'skipped'
            stage['end_time'] = datetime.now().isoformat()
            if reason:
                stage['error'] = f"Skipped: {reason}"
            self._save()

    def update_stage_progress(self, stage_id: str, message: str):
        """Update stage progress message"""
        stage = self._find_stage(stage_id)
        if stage:
            if 'progress' not in stage:
                stage['progress'] = []
            stage['progress'].append({
                'timestamp': datetime.now().isoformat(),
                'message': message
            })
            self._save()

    @contextmanager
    def track_workflow(self):
        """Context manager for tracking entire workflow"""
        try:
            self.start_workflow()
            yield self
            self.complete_workflow()
        except Exception as e:
            self.fail_workflow(str(e))
            raise

    @contextmanager
    def track_stage(self, stage_id: str, stage_name: str):
        """Context manager for tracking a stage"""
        self.start_stage(stage_id, stage_name)
        try:
            yield self
            self.complete_stage(stage_id)
        except Exception as e:
            self.fail_stage(stage_id, str(e))
            raise

    def _find_stage(self, stage_id: str) -> Optional[Dict]:
        """Find stage by ID"""
        for stage in self.status_data['stages']:
            if stage['id'] == stage_id:
                return stage
        return None

    def _calculate_duration(self):
        """Calculate total workflow duration"""
        if self.status_data['start_time'] and self.status_data['end_time']:
            start = datetime.fromisoformat(self.status_data['start_time'])
            end = datetime.fromisoformat(self.status_data['end_time'])
            self.status_data['total_duration_seconds'] = (end - start).total_seconds()

    def _calculate_stage_duration(self, stage: Dict) -> Optional[float]:
        """Calculate stage duration"""
        if stage['start_time'] and stage['end_time']:
            start = datetime.fromisoformat(stage['start_time'])
            end = datetime.fromisoformat(stage['end_time'])
            return (end - start).total_seconds()
        return None

    def _save(self):
        """Save status to disk"""
        try:
            with open(self.status_file, 'w') as f:
                json.dump(self.status_data, f, indent=2)
        except Exception as e:
            # Don't fail workflow if status save fails
            print(f"Warning: Failed to save workflow status: {e}")

    def cleanup(self):
        """Remove status file"""
        try:
            if self.status_file.exists():
                self.status_file.unlink()
        except Exception as e:
            print(f"Warning: Failed to cleanup status file: {e}")


# Example usage
if __name__ == '__main__':
    # Test the tracker
    tracker = WorkflowStatusTracker(card_id="test-card-001")

    with tracker.track_workflow():
        print("Workflow started")

        with tracker.track_stage("STAGE_1", "Test Stage 1"):
            print("Stage 1 running...")
            time.sleep(1)
            tracker.update_stage_progress("STAGE_1", "Processing files...")
            time.sleep(1)

        with tracker.track_stage("STAGE_2", "Test Stage 2"):
            print("Stage 2 running...")
            time.sleep(1)

        print("Workflow completed")

    print(f"\nStatus saved to: {tracker.status_file}")
    print("\nRun: python3 artemis_status.py --card-id test-card-001")
