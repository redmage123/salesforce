#!/usr/bin/env python3
"""
Test Checkpoint Manager - Resume After Crash

Tests:
1. Checkpoint creation and saving
2. Stage checkpoint saving
3. Resume from checkpoint
4. Progress tracking
5. LLM response caching
6. Complete pipeline with checkpoints
"""

import sys
import time
from datetime import datetime
from pathlib import Path

# Add agile directory to path (relative to this file)
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from checkpoint_manager import CheckpointManager, CheckpointStatus


def test_checkpoint_creation():
    """Test 1: Create and save checkpoint"""
    print("\n" + "="*70)
    print("TEST 1: Checkpoint Creation")
    print("="*70)

    cm = CheckpointManager(card_id="test-card-001", verbose=True)

    # Create checkpoint
    checkpoint = cm.create_checkpoint(total_stages=5)

    assert checkpoint is not None
    assert checkpoint.card_id == "test-card-001"
    assert checkpoint.total_stages == 5
    assert checkpoint.stages_completed == 0
    assert checkpoint.status == CheckpointStatus.ACTIVE

    print(f"\n✅ Checkpoint created successfully")
    print(f"   Checkpoint ID: {checkpoint.checkpoint_id}")
    print(f"   Total stages: {checkpoint.total_stages}")


def test_stage_checkpoint():
    """Test 2: Save stage checkpoints"""
    print("\n" + "="*70)
    print("TEST 2: Stage Checkpoint Saving")
    print("="*70)

    cm = CheckpointManager(card_id="test-card-002", verbose=True)
    cm.create_checkpoint(total_stages=3)

    # Save checkpoints for completed stages
    print("\nSaving architecture stage...")
    start_time = datetime.now()
    time.sleep(0.1)  # Simulate work
    end_time = datetime.now()

    cm.save_stage_checkpoint(
        stage_name="architecture",
        status="completed",
        result={"adr_file": "/tmp/adr/ADR-001.md"},
        artifacts=["/tmp/adr/ADR-001.md"],
        llm_responses=[{"prompt": "Create architecture", "response": "ADR created"}],
        start_time=start_time,
        end_time=end_time
    )

    assert "architecture" in cm.checkpoint.completed_stages
    assert cm.checkpoint.stages_completed == 1

    print("\nSaving development stage...")
    cm.save_stage_checkpoint(
        stage_name="development",
        status="completed",
        result={"code_file": "/tmp/code.py"},
        start_time=datetime.now(),
        end_time=datetime.now()
    )

    assert cm.checkpoint.stages_completed == 2

    print(f"\n✅ Stage checkpoints saved")
    print(f"   Completed stages: {cm.checkpoint.stages_completed}/3")


def test_resume_from_checkpoint():
    """Test 3: Resume from checkpoint after 'crash'"""
    print("\n" + "="*70)
    print("TEST 3: Resume from Checkpoint")
    print("="*70)

    # Simulate pipeline execution
    print("\n1. Starting pipeline...")
    cm1 = CheckpointManager(card_id="test-card-003", verbose=True)
    cm1.create_checkpoint(total_stages=5)

    print("\n2. Completing first 2 stages...")
    cm1.save_stage_checkpoint("project_analysis", "completed", result={"analysis": "done"})
    cm1.save_stage_checkpoint("architecture", "completed", result={"adr": "done"})

    print("\n3. Simulating crash... 💥")
    # Destroy the checkpoint manager (simulates crash)
    del cm1

    # Try to resume
    print("\n4. Restarting and attempting resume...")
    cm2 = CheckpointManager(card_id="test-card-003", verbose=True)

    can_resume = cm2.can_resume()
    assert can_resume, "Should be able to resume"

    checkpoint = cm2.resume()
    assert checkpoint is not None
    assert checkpoint.stages_completed == 2
    assert len(checkpoint.completed_stages) == 2
    assert checkpoint.status == CheckpointStatus.RESUMED

    print(f"\n✅ Successfully resumed from checkpoint!")
    print(f"   Resume count: {checkpoint.resume_count}")
    print(f"   Completed stages: {checkpoint.completed_stages}")
    print(f"   Can continue from: stage 3")


def test_get_next_stage():
    """Test 4: Get next stage after resume"""
    print("\n" + "="*70)
    print("TEST 4: Get Next Stage After Resume")
    print("="*70)

    cm = CheckpointManager(card_id="test-card-004", verbose=True)
    cm.create_checkpoint(total_stages=5)

    # Complete first 2 stages
    cm.save_stage_checkpoint("stage1", "completed")
    cm.save_stage_checkpoint("stage2", "completed")

    # Get next stage
    all_stages = ["stage1", "stage2", "stage3", "stage4", "stage5"]
    next_stage = cm.get_next_stage(all_stages)

    assert next_stage == "stage3", f"Expected stage3, got {next_stage}"

    print(f"\n✅ Next stage identified correctly")
    print(f"   Next stage to execute: {next_stage}")


def test_progress_tracking():
    """Test 5: Progress tracking"""
    print("\n" + "="*70)
    print("TEST 5: Progress Tracking")
    print("="*70)

    cm = CheckpointManager(card_id="test-card-005", verbose=True)
    cm.create_checkpoint(total_stages=4)

    # Initial progress
    progress = cm.get_progress()
    print(f"\nInitial progress: {progress['progress_percent']}%")
    assert progress['progress_percent'] == 0

    # Complete stages
    print("\nCompleting stages...")
    for i in range(1, 4):
        cm.save_stage_checkpoint(
            f"stage{i}",
            "completed",
            start_time=datetime.now(),
            end_time=datetime.now()
        )
        progress = cm.get_progress()
        print(f"   Stage {i} complete: {progress['progress_percent']:.1f}%")

    # Final progress
    progress = cm.get_progress()
    assert progress['progress_percent'] == 75.0  # 3/4 stages

    print(f"\n✅ Progress tracking working")
    print(f"   Progress: {progress['progress_percent']}%")
    print(f"   Stages: {progress['stages_completed']}/{progress['total_stages']}")


def test_llm_caching():
    """Test 6: LLM response caching"""
    print("\n" + "="*70)
    print("TEST 6: LLM Response Caching")
    print("="*70)

    cm = CheckpointManager(card_id="test-card-006", verbose=True, enable_llm_cache=True)
    cm.create_checkpoint(total_stages=2)

    # Save stage with LLM responses
    print("\nSaving stage with LLM responses...")
    cm.save_stage_checkpoint(
        stage_name="architecture",
        status="completed",
        llm_responses=[
            {"prompt": "Create ADR for database", "response": "# ADR-001: PostgreSQL\n..."},
            {"prompt": "Create ADR for API", "response": "# ADR-002: REST API\n..."}
        ]
    )

    # Try to get cached responses
    print("\nAttempting to retrieve cached LLM responses...")
    cached1 = cm.get_cached_llm_response("architecture", "Create ADR for database")
    cached2 = cm.get_cached_llm_response("architecture", "Create ADR for API")
    cached3 = cm.get_cached_llm_response("architecture", "Different prompt")

    assert cached1 is not None, "Should have cached response 1"
    assert cached2 is not None, "Should have cached response 2"
    assert cached3 is None, "Should not have cached response for different prompt"

    print(f"\n✅ LLM caching working")
    print(f"   Cache hits: 2/3")
    print(f"   Cached response 1: {cached1['response'][:30]}...")


def test_complete_pipeline():
    """Test 7: Complete pipeline with checkpoints"""
    print("\n" + "="*70)
    print("TEST 7: Complete Pipeline with Checkpoints")
    print("="*70)

    stages = ["project_analysis", "architecture", "development", "code_review", "integration"]

    cm = CheckpointManager(card_id="test-card-007", verbose=True)
    cm.create_checkpoint(total_stages=len(stages))

    print(f"\nExecuting pipeline with {len(stages)} stages...")

    for i, stage in enumerate(stages):
        print(f"\n   Executing {stage}...")
        cm.set_current_stage(stage)

        # Simulate work
        time.sleep(0.05)

        # Save checkpoint
        cm.save_stage_checkpoint(
            stage_name=stage,
            status="completed",
            result={"output": f"{stage} result"},
            start_time=datetime.now(),
            end_time=datetime.now()
        )

        progress = cm.get_progress()
        print(f"   Progress: {progress['progress_percent']:.1f}% ({i+1}/{len(stages)})")

    # Mark pipeline as completed
    cm.mark_completed()

    assert cm.checkpoint.status == CheckpointStatus.COMPLETED
    assert cm.checkpoint.stages_completed == len(stages)

    print(f"\n✅ Complete pipeline executed with checkpoints")
    print(f"   Total stages: {cm.checkpoint.stages_completed}")
    print(f"   Total duration: {cm.checkpoint.total_duration_seconds:.2f}s")
    print(f"   Status: {cm.checkpoint.status.value}")


def test_resume_and_continue():
    """Test 8: Resume and continue execution"""
    print("\n" + "="*70)
    print("TEST 8: Resume and Continue Execution")
    print("="*70)

    stages = ["stage1", "stage2", "stage3", "stage4", "stage5"]

    # Part 1: Execute first 3 stages
    print("\n1. Executing first 3 stages...")
    cm1 = CheckpointManager(card_id="test-card-008", verbose=False)
    cm1.create_checkpoint(total_stages=len(stages))

    for stage in stages[:3]:
        cm1.save_stage_checkpoint(stage, "completed")

    print(f"   Completed: {cm1.checkpoint.stages_completed}/5")

    # Simulate crash
    print("\n2. Simulating crash... 💥")
    del cm1

    # Part 2: Resume and complete remaining stages
    print("\n3. Resuming from checkpoint...")
    cm2 = CheckpointManager(card_id="test-card-008", verbose=False)
    checkpoint = cm2.resume()

    assert checkpoint.stages_completed == 3

    # Find next stage
    next_stage = cm2.get_next_stage(stages)
    print(f"   Resuming from: {next_stage}")

    # Complete remaining stages
    print("\n4. Completing remaining stages...")
    for stage in stages[3:]:
        cm2.save_stage_checkpoint(stage, "completed")
        print(f"   Completed: {stage}")

    cm2.mark_completed()

    print(f"\n✅ Successfully resumed and completed pipeline")
    print(f"   Total stages: {cm2.checkpoint.stages_completed}/5")
    print(f"   Resume count: {cm2.checkpoint.resume_count}")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("CHECKPOINT MANAGER TESTS")
    print("="*70)

    try:
        test_checkpoint_creation()
        test_stage_checkpoint()
        test_resume_from_checkpoint()
        test_get_next_stage()
        test_progress_tracking()
        test_llm_caching()
        test_complete_pipeline()
        test_resume_and_continue()

        print("\n" + "="*70)
        print("✅ ALL CHECKPOINT TESTS PASSED!")
        print("="*70)
        print("\nSummary:")
        print("  ✅ Checkpoint creation and saving")
        print("  ✅ Stage checkpoint tracking")
        print("  ✅ Resume from checkpoint after crash")
        print("  ✅ Next stage identification")
        print("  ✅ Progress tracking")
        print("  ✅ LLM response caching")
        print("  ✅ Complete pipeline execution")
        print("  ✅ Resume and continue execution")
        print("\nThe Checkpoint Manager is fully functional!")
        print("="*70 + "\n")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
