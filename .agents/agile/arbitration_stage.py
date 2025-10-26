#!/usr/bin/env python3
"""
ArbitrationStage - Intelligent Developer Selection

Single Responsibility: Select the best developer solution using DeveloperArbitrator

This stage runs immediately after DevelopmentStage and before any validation/testing.
It analyzes both developer implementations and selects the winner based on:
- Code structure and organization
- Estimated complexity
- File count and lines of code
- Preliminary assessment

The winner is then passed to subsequent stages (Validation, UI/UX, CodeReview)
"""

import tempfile
import shutil
from typing import Dict, Optional
from pathlib import Path

from artemis_stage_interface import PipelineStage, LoggerInterface
from developer_arbitrator import DeveloperArbitrator
from supervised_agent_mixin import SupervisedStageMixin
from debug_mixin import DebugMixin
from agent_messenger import AgentMessenger
from artemis_exceptions import (
    PipelineStageError,
    FileReadError,
    wrap_exception
)


class ArbitrationStage(PipelineStage, SupervisedStageMixin, DebugMixin):
    """
    Select best developer solution before validation

    This stage ONLY selects the winner - no testing or validation.
    Uses preliminary metrics to choose the best implementation.
    """

    def __init__(
        self,
        logger: LoggerInterface,
        messenger: AgentMessenger,
        observable: Optional['PipelineObservable'] = None,
        supervisor: Optional['SupervisorAgent'] = None,
        ai_service: Optional['AIQueryService'] = None
    ):
        # Initialize PipelineStage
        PipelineStage.__init__(self)

        # Initialize SupervisedStageMixin
        SupervisedStageMixin.__init__(
            self,
            supervisor=supervisor,
            stage_name="ArbitrationStage",
            heartbeat_interval=10
        )

        # Initialize DebugMixin
        DebugMixin.__init__(self, component_name="arbitration")

        self.logger = logger
        self.messenger = messenger
        self.observable = observable
        self.ai_service = ai_service
        self.arbitrator = DeveloperArbitrator()

        # Register message handlers for supervisor commands
        if self.messenger:
            self.messenger.register_handler("arbitration_override", self._handle_arbitration_override)
            self.messenger.register_handler("select_winner", self._handle_select_winner_command)

    @wrap_exception(PipelineStageError, "Arbitration stage execution failed")
    def execute(self, card: Dict, context: Dict) -> Dict:
        """Execute with supervisor monitoring"""
        metadata = {
            "task_id": card.get('card_id'),
            "stage": "arbitration"
        }

        with self.supervised_execution(metadata):
            return self._do_work(card, context)

    def _do_work(self, card: Dict, context: Dict) -> Dict:
        """Select winner based on preliminary analysis"""
        self.logger.log("Starting Arbitration Stage", "STAGE")
        self.logger.log("🎯 Selecting best developer solution...", "INFO")

        card_id = card.get('card_id', 'unknown')

        # DEBUG: Log arbitration start
        self.debug_log("Starting arbitration", card_id=card_id)

        self.update_progress({"step": "starting", "progress_percent": 10})

        # Notify arbitration started
        if self.observable:
            from pipeline_observer import PipelineEvent, EventType
            event = PipelineEvent(
                event_type=EventType.STAGE_STARTED,
                card_id=card_id,
                data={"stage": "arbitration"}
            )
            self.observable.notify(event)

        # Get developer results from context
        developers = context.get('developers', [])

        if len(developers) < 2:
            self.logger.log("⚠️  Less than 2 developers, selecting first", "WARNING")
            winner = developers[0].get('developer', 'developer-a') if developers else 'developer-a'

            return {
                "stage": "arbitration",
                "status": "COMPLETE",  # Required by pipeline_strategies.py success check
                "success": True,  # Explicit success indicator
                "winner": winner,
                "reason": "only_one_developer",
                "arbitration_result": None
            }

        self.update_progress({"step": "analyzing_implementations", "progress_percent": 30})

        # Analyze both implementations
        dev_a_result = next((d for d in developers if d.get('developer') == 'developer-a'), {})
        dev_b_result = next((d for d in developers if d.get('developer') == 'developer-b'), {})

        # Get preliminary metrics for each developer
        dev_a_metrics = self._analyze_implementation(dev_a_result)
        dev_b_metrics = self._analyze_implementation(dev_b_result)

        self.update_progress({"step": "running_arbitration", "progress_percent": 60})

        # Use arbitrator with preliminary metrics (no code review yet)
        # Arbitrator will use default scores and available metrics
        try:
            with self.debug_section("Arbitration Selection"):
                arbitration_result = self.arbitrator.select_winner(
                    dev_a_result=dev_a_metrics,
                    dev_b_result=dev_b_metrics,
                    code_review_results=[]  # No reviews yet
                )

                # DEBUG: Dump arbitration result
                self.debug_dump_if_enabled('dump_scores', "Arbitration Result", arbitration_result)

            winner = arbitration_result['winner']

            # DEBUG: Log winner selection
            self.debug_if_enabled('show_winner_selection', "Winner selected",
                                 winner=winner,
                                 score=arbitration_result['winner_score'],
                                 margin=arbitration_result['margin'])

            self.logger.log(f"🏆 Winner: {winner}", "SUCCESS")
            self.logger.log(f"   Score: {arbitration_result['winner_score']:.2f}/100", "INFO")
            self.logger.log(f"   Margin: {arbitration_result['margin']:.2f} points", "INFO")
            self.logger.log(f"   Confidence: {arbitration_result['confidence']}", "INFO")
            self.logger.log(f"   Reasoning: {arbitration_result['reasoning']}", "INFO")

            # Clean up losing developer's artifacts
            loser = 'developer-b' if winner == 'developer-a' else 'developer-a'
            self._cleanup_losing_developer(loser, dev_a_metrics if loser == 'developer-a' else dev_b_metrics)

            # Notify arbitration completed
            if self.observable:
                from pipeline_observer import PipelineEvent, EventType
                event = PipelineEvent(
                    event_type=EventType.STAGE_COMPLETED,
                    card_id=card_id,
                    data={
                        "stage": "arbitration",
                        "winner": winner,
                        "score": arbitration_result['winner_score'],
                        "confidence": arbitration_result['confidence']
                    }
                )
                self.observable.notify(event)

        except Exception as e:
            self.logger.log(f"⚠️  Arbitration failed: {e}, defaulting to developer-a", "WARNING")
            winner = 'developer-a'
            arbitration_result = None

            # Notify arbitration failed
            if self.observable:
                from pipeline_observer import PipelineEvent, EventType
                event = PipelineEvent(
                    event_type=EventType.STAGE_FAILED,
                    card_id=card_id,
                    error=e,
                    data={
                        "stage": "arbitration",
                        "fallback_winner": winner
                    }
                )
                self.observable.notify(event)

            # Wrap exception for proper error handling
            raise wrap_exception(
                e,
                PipelineStageError,
                "Arbitration failed to select winner",
                {
                    "stage": "arbitration",
                    "dev_a_metrics": dev_a_metrics,
                    "dev_b_metrics": dev_b_metrics
                }
            )

        self.update_progress({"step": "complete", "progress_percent": 100})

        return {
            "stage": "arbitration",
            "status": "COMPLETE",  # Required by pipeline_strategies.py success check
            "success": True,  # Explicit success indicator
            "winner": winner,
            "arbitration_result": arbitration_result,
            "dev_a_metrics": dev_a_metrics,
            "dev_b_metrics": dev_b_metrics
        }

    def _count_file_lines(self, file_path: str, developer: str) -> int:
        """
        Count lines in a file with error handling

        Args:
            file_path: Path to file
            developer: Developer name for error context

        Returns:
            Number of lines in file, or 0 if error
        """
        try:
            with open(file_path, 'r') as f:
                return len(f.readlines())
        except FileNotFoundError:
            self.logger.log(f"Warning: Implementation file not found: {file_path}", "WARNING")
            return 0
        except IOError as e:
            wrapped_error = wrap_exception(
                e,
                FileReadError,
                f"Failed to read implementation file for analysis",
                {
                    "developer": developer,
                    "file_path": file_path,
                    "stage": "arbitration"
                }
            )
            self.logger.log(f"Warning: {wrapped_error}", "WARNING")
            return 0

    def _calculate_complexity(self, total_lines: int) -> int:
        """
        Calculate complexity score based on lines of code

        Args:
            total_lines: Total lines of code

        Returns:
            Complexity score (5, 10, or 15)
        """
        if total_lines < 100:
            return 5
        elif total_lines < 300:
            return 10
        else:
            return 15

    def _analyze_implementation(self, dev_result: Dict) -> Dict:
        """
        Analyze developer implementation for preliminary metrics

        Returns metrics that can be used by arbitrator before
        code review and testing
        """
        developer = dev_result.get('developer', 'unknown')
        output_dir = dev_result.get('output_dir', f'{tempfile.gettempdir()}/{developer}')

        # Count files and estimate complexity
        impl_files = dev_result.get('implementation_files', [])
        test_files = dev_result.get('test_files', [])

        # Use sum with generator expression instead of loop
        total_lines = sum(self._count_file_lines(file_path, developer) for file_path in impl_files)

        # Calculate complexity using extracted method
        complexity = self._calculate_complexity(total_lines)

        # Build metrics dict for arbitrator
        return {
            "developer": developer,
            "output_dir": output_dir,
            "implementation_files": impl_files,
            "test_files": test_files,
            "lines_of_code": total_lines,
            "complexity_score": complexity,
            "solid_score": 50.0,  # Default, will be updated by code review
            "test_results": {
                "passed": 0,
                "total": len(test_files)
            }
        }

    def _cleanup_losing_developer(self, loser: str, loser_metrics: Dict) -> None:
        """
        Remove losing developer's output directory and artifacts

        Args:
            loser: Name of losing developer
            loser_metrics: Metrics dict containing output_dir
        """
        output_dir = loser_metrics.get('output_dir')

        if not output_dir:
            self.logger.log(f"⚠️  No output directory found for {loser}, skipping cleanup", "WARNING")
            return

        output_path = Path(output_dir)

        if not output_path.exists():
            self.logger.log(f"⚠️  Output directory {output_dir} does not exist, skipping cleanup", "WARNING")
            return

        try:
            self.logger.log(f"🗑️  Removing losing developer's artifacts: {output_dir}", "INFO")
            shutil.rmtree(output_dir)
            self.logger.log(f"✅ Successfully removed {loser}'s output directory", "SUCCESS")
        except OSError as e:
            # Wrap the OSError for consistent error handling
            wrapped_error = wrap_exception(
                e,
                FileReadError,
                f"Failed to remove losing developer's artifacts",
                {
                    "developer": loser,
                    "output_dir": output_dir,
                    "stage": "arbitration"
                }
            )
            # Log but don't fail the entire stage
            self.logger.log(f"⚠️  {wrapped_error}", "WARNING")

    def get_stage_name(self) -> str:
        return "arbitration"

    def _handle_arbitration_override(self, message: Dict) -> Dict:
        """
        Handle supervisor command to override arbitration decision

        Message format:
        {
            "command": "arbitration_override",
            "winner": "developer-a" | "developer-b",
            "reason": "explanation"
        }
        """
        winner = message.get('winner', 'developer-a')
        reason = message.get('reason', 'Supervisor override')

        self.logger.log(f"🔧 Supervisor override: Selecting {winner}", "WARNING")
        self.logger.log(f"   Reason: {reason}", "INFO")

        return {
            "status": "success",
            "winner": winner,
            "reason": reason
        }

    def _handle_select_winner_command(self, message: Dict) -> Dict:
        """
        Handle supervisor command to explicitly select a winner

        Message format:
        {
            "command": "select_winner",
            "developer": "developer-a" | "developer-b"
        }
        """
        winner = message.get('developer', 'developer-a')

        self.logger.log(f"📨 Received supervisor command to select {winner}", "INFO")

        return {
            "status": "acknowledged",
            "winner": winner
        }
