# Checkpoint Integration Guide

## Current Status

The `--resume` CLI flag has been added (line 1635 in artemis_orchestrator.py), but checkpoint save/restore logic is not yet integrated into the pipeline execution flow.

The CheckpointManager is initialized (artemis_orchestrator.py:345-347) but never used.

## Integration Steps Required

### 1. Pass Resume Flag to Orchestrator

In `main_legacy()` at line 1838, add resume parameter:

```python
orchestrator = ArtemisOrchestrator(
    card_id=args.card_id,
    board=board,
    messenger=messenger,
    rag=rag,
    config=config,
    resume=args.resume  # ADD THIS
)
```

### 2. Add Resume Parameter to __init__

In `Art emis Orchestrator.__init__()` at line 242, add:

```python
def __init__(
    self,
    card_id: str,
    board: KanbanBoard,
    messenger: MessengerInterface,
    rag: RAGAgent,
    config: Optional[ConfigurationAgent] = None,
    hydra_config: Optional[DictConfig] = None,
    logger: Optional[LoggerInterface] = None,
    test_runner: Optional[TestRunner] = None,
    stages: Optional[List[PipelineStage]] = None,
    supervisor: Optional[SupervisorAgent] = None,
    enable_supervision: bool = True,
    strategy: Optional[PipelineStrategy] = None,
    enable_observers: bool = True,
    resume: bool = False  # ADD THIS
):
```

Store it: `self.resume = resume`

### 3. Resume from Checkpoint in run_full_pipeline()

At the start of `run_full_pipeline()` (line 789), add:

```python
def run_full_pipeline(self, max_retries: int = None) -> Dict:
    # Check for existing checkpoint
    if self.resume and self.checkpoint_manager.can_resume():
        checkpoint = self.checkpoint_manager.resume()
        self.logger.log(f"📥 Resuming from checkpoint: {len(checkpoint.stage_checkpoints)} stages completed", "INFO")

        # Get completed stages
        completed_stages = set(checkpoint.stage_checkpoints.keys())

        # Filter out completed stages
        stages_to_run = [s for s in stages_to_run if s.__class__.__name__.replace('Stage', '').lower() not in completed_stages]

        self.logger.log(f"⏭️  Skipping {len(completed_stages)} completed stages", "INFO")
        self.logger.log(f"▶️  Running {len(stages_to_run)} remaining stages", "INFO")
```

### 4. Save Checkpoint After Each Stage

In pipeline_strategies.py `StandardPipelineStrategy.execute()` at line 152, after successful stage execution:

```python
# Execute stage with card and context
card = context.get('card')
stage_result = stage.execute(card, context)

# Store result
results[stage_name] = stage_result

# ADD: Save checkpoint after stage completion
if hasattr(context.get('orchestrator'), 'checkpoint_manager'):
    checkpoint_manager = context['orchestrator'].checkpoint_manager
    checkpoint_manager.save_stage_checkpoint(
        stage_name=stage_name.lower(),
        status="completed",
        result=stage_result,
        start_time=datetime.now() - timedelta(seconds=5),  # Estimate
        end_time=datetime.now()
    )
```

### 5. Pass Orchestrator to Context

In `run_full_pipeline()` before calling `self.strategy.execute()`:

```python
# Add orchestrator to context so strategy can access checkpoint_manager
context['orchestrator'] = self

execution_result = self.strategy.execute(stages_to_run, context)
```

## Benefits

Once integrated, checkpointing will:
- Save 10-15 minutes per test iteration
- Resume from sprint_planning, project_analysis, or development stages
- Preserve LLM responses (via LLM cache)
- Enable crash recovery

## Testing

After integration:

```bash
# Run fresh pipeline
python artemis_orchestrator.py --card-id card-20251023065355 --full

# If it crashes/stops, resume
python artemis_orchestrator.py --card-id card-20251023065355 --full --resume
```

The checkpoint file is saved at:
`../../.artemis_data/checkpoints/card-20251023065355.json`
