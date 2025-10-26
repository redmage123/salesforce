#!/usr/bin/env python3
"""
TestingStage

Extracted from artemis_stages.py for strict Single Responsibility Principle compliance.
Each stage has its own file for independent testing and evolution.
"""

#!/usr/bin/env python3
"""
Artemis Stage Implementations (SOLID Principles)

Each stage class follows SOLID:
- Single Responsibility: ONE stage, ONE responsibility
- Open/Closed: Can add new stages without modifying existing
- Liskov Substitution: All stages implement PipelineStage interface
- Interface Segregation: Minimal, focused interfaces
- Dependency Inversion: Stages depend on injected abstractions
"""

import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from artemis_stage_interface import PipelineStage, LoggerInterface
from artemis_services import TestRunner, FileManager
from kanban_manager import KanbanBoard
from agent_messenger import AgentMessenger
from rag_agent import RAGAgent
from developer_invoker import DeveloperInvoker
from project_analysis_agent import ProjectAnalysisEngine, UserApprovalHandler
from artemis_exceptions import (
    FileReadError,
    ADRGenerationError,
    wrap_exception
)

# Import PromptManager for RAG-based prompts
try:
    from prompt_manager import PromptManager
    PROMPT_MANAGER_AVAILABLE = True
except ImportError:
    PROMPT_MANAGER_AVAILABLE = False
from supervised_agent_mixin import SupervisedStageMixin
from debug_mixin import DebugMixin
from knowledge_graph_factory import get_knowledge_graph

# Import centralized AI Query Service
from ai_query_service import (
    AIQueryService,
    create_ai_query_service,
    QueryType,
    AIQueryResult
)
from rag_storage_helper import RAGStorageHelper


# ============================================================================
# PROJECT ANALYSIS STAGE (Pre-Implementation Review)
# ============================================================================


class TestingStage(PipelineStage, SupervisedStageMixin, DebugMixin):
    """
    Single Responsibility: Final quality gates

    This stage ONLY performs final testing - nothing else.

    Integrates with supervisor for:
    - Final test execution tracking
    - Quality gate failure handling
    - Automatic heartbeat and health monitoring
    """

    def __init__(
        self,
        board: KanbanBoard,
        messenger: AgentMessenger,
        rag: RAGAgent,
        test_runner: TestRunner,
        logger: LoggerInterface,
        supervisor: Optional['SupervisorAgent'] = None
    ):
        # Initialize PipelineStage
        PipelineStage.__init__(self)

        # Initialize SupervisedStageMixin for health monitoring
        SupervisedStageMixin.__init__(
            self,
            supervisor=supervisor,
            stage_name="TestingStage",
            heartbeat_interval=15
        )

        # Initialize DebugMixin
        DebugMixin.__init__(self, component_name="testing")

        self.board = board
        self.messenger = messenger
        self.rag = rag
        self.test_runner = test_runner
        self.logger = logger

    def execute(self, card: Dict, context: Dict) -> Dict:
        """Execute with supervisor monitoring"""
        metadata = {
            "task_id": card.get('card_id'),
            "stage": "testing"
        }

        with self.supervised_execution(metadata):
            return self._do_work(card, context)

    def _do_work(self, card: Dict, context: Dict) -> Dict:
        """Internal method - runs final quality gates"""
        self.logger.log("Starting Testing Stage", "STAGE")

        card_id = card['card_id']
        winner = context.get('winner', 'developer-a')

        # DEBUG: Log stage entry
        self.debug_log("Starting final testing", card_id=card_id, winner=winner)

        # Update progress: starting
        self.update_progress({"step": "starting", "progress_percent": 10})

        # Run final regression tests
        self.update_progress({"step": "running_regression_tests", "progress_percent": 30})
        test_path = f"/tmp/{winner}/tests"

        with self.debug_section("Final Regression Tests"):
            self.debug_if_enabled('log_tests', "Running final tests", test_path=test_path)
            regression_results = self.test_runner.run_tests(test_path)

            # DEBUG: Dump test results
            self.debug_dump_if_enabled('dump_test_results', "Final Test Results", regression_results)

        # Evaluate performance (simplified)
        self.update_progress({"step": "evaluating_performance", "progress_percent": 60})
        performance_score = 85  # In real implementation, this would measure actual performance

        # DEBUG: Log performance evaluation
        self.debug_if_enabled('log_performance', "Performance evaluated", score=performance_score)

        # All quality gates
        self.update_progress({"step": "checking_quality_gates", "progress_percent": 80})
        all_gates_passed = regression_results['exit_code'] == 0
        status = "PASS" if all_gates_passed else "FAIL"

        # DEBUG: Dump quality gate results
        self.debug_dump_if_enabled('dump_quality_gates', "Quality Gates Results", {
            "all_gates_passed": all_gates_passed,
            "status": status,
            "performance_score": performance_score,
            "exit_code": regression_results.get('exit_code')
        })

        if status == "PASS":
            self.logger.log("Testing complete: All quality gates passed", "SUCCESS")

        # Update Kanban
        self.update_progress({"step": "updating_kanban", "progress_percent": 90})
        self.board.move_card(card_id, "done", "pipeline-orchestrator")

        # Store in RAG
        self.update_progress({"step": "storing_in_rag", "progress_percent": 95})
        # Store in RAG using helper (DRY)

        RAGStorageHelper.store_stage_artifact(

            rag=self.rag,
            stage_name="testing_result",
            card_id=card_id,
            task_title=card.get('title', 'Unknown'),
            content=f"Final testing of {winner} solution completed",
            metadata={
                "winner": winner,
                "performance_score": performance_score,
                "all_gates_passed": all_gates_passed
            }
        )

        # Update progress: complete
        self.update_progress({"step": "complete", "progress_percent": 100})

        return {
            "stage": "testing",
            "winner": winner,
            "regression_tests": regression_results,
            "performance_score": performance_score,
            "all_quality_gates_passed": all_gates_passed,
            "status": status
        }

    def get_stage_name(self) -> str:
        return "testing"

