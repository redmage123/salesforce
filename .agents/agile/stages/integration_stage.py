#!/usr/bin/env python3
"""
IntegrationStage

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


# ============================================================================
# PROJECT ANALYSIS STAGE (Pre-Implementation Review)
# ============================================================================


class IntegrationStage(PipelineStage, SupervisedStageMixin, DebugMixin):
    """
    Single Responsibility: Integrate winning solution

    This stage ONLY deploys and runs regression tests - nothing else.

    Integrates with supervisor for:
    - Merge conflict handling
    - Final test execution tracking
    - Integration failure recovery
    - Automatic heartbeat and health monitoring
    """

    def __init__(
        self,
        board: KanbanBoard,
        messenger: AgentMessenger,
        rag: RAGAgent,
        test_runner: TestRunner,
        logger: LoggerInterface,
        observable: Optional['PipelineObservable'] = None,
        supervisor: Optional['SupervisorAgent'] = None
    ):
        # Initialize PipelineStage
        PipelineStage.__init__(self)

        # Initialize SupervisedStageMixin for health monitoring
        SupervisedStageMixin.__init__(
            self,
            supervisor=supervisor,
            stage_name="IntegrationStage",
            heartbeat_interval=15
        )

        # Initialize DebugMixin
        DebugMixin.__init__(self, component_name="integration")

        self.board = board
        self.messenger = messenger
        self.rag = rag
        self.test_runner = test_runner
        self.logger = logger
        self.supervisor = supervisor
        self.observable = observable

    def execute(self, card: Dict, context: Dict) -> Dict:
        """Execute with supervisor monitoring"""
        metadata = {
            "task_id": card.get('card_id'),
            "stage": "integration"
        }

        with self.supervised_execution(metadata):
            return self._do_work(card, context)

    def _do_work(self, card: Dict, context: Dict) -> Dict:
        """Internal method - integrates winning solution"""
        self.logger.log("Starting Integration Stage", "STAGE")

        card_id = card['card_id']

        # Update progress: starting
        self.update_progress({"step": "starting", "progress_percent": 10})

        # Determine winner
        winner = context.get('winner', 'developer-a')

        # DEBUG: Log stage entry
        self.debug_log("Starting integration", card_id=card_id, winner=winner)

        # Update progress: notifying start
        self.update_progress({"step": "notifying_integration_start", "progress_percent": 20})

        # Notify integration started
        if self.observable:
            from pipeline_observer import PipelineEvent, EventType
            event = PipelineEvent(
                event_type=EventType.INTEGRATION_STARTED,
                card_id=card_id,
                developer_name=winner,
                data={"winning_developer": winner}
            )
            self.observable.notify(event)

        self.logger.log(f"Integrating {winner} solution...", "INFO")

        # Run regression tests
        self.update_progress({"step": "running_regression_tests", "progress_percent": 40})
        test_path = f"/tmp/{winner}/tests"

        with self.debug_section("Regression Testing"):
            self.debug_if_enabled('log_tests', "Running regression tests", test_path=test_path)
            regression_results = self.test_runner.run_tests(test_path)

            # DEBUG: Dump test results
            self.debug_dump_if_enabled('dump_test_results', "Regression Test Results", regression_results)

        # Verify deployment
        self.update_progress({"step": "verifying_deployment", "progress_percent": 60})
        deployment_verified = regression_results['exit_code'] == 0
        status = "PASS" if deployment_verified else "FAIL"

        # DEBUG: Log deployment verification
        self.debug_if_enabled('log_deployment', "Deployment verification",
                             verified=deployment_verified,
                             status=status,
                             exit_code=regression_results.get('exit_code'))

        if status == "PASS":
            self.logger.log("Integration complete: All tests passing, deployment verified", "SUCCESS")

            # Notify integration completed
            self.update_progress({"step": "notifying_success", "progress_percent": 75})
            if self.observable:
                from pipeline_observer import PipelineEvent, EventType
                event = PipelineEvent(
                    event_type=EventType.INTEGRATION_COMPLETED,
                    card_id=card_id,
                    developer_name=winner,
                    data={
                        "winner": winner,
                        "tests_passed": regression_results.get('passed', 0),
                        "deployment_verified": deployment_verified
                    }
                )
                self.observable.notify(event)
        else:
            self.logger.log(f"Integration issues detected: {regression_results.get('failed', 0)} tests failed", "WARNING")

            # Notify integration conflict (failures during integration)
            self.update_progress({"step": "notifying_conflict", "progress_percent": 75})
            if self.observable:
                from pipeline_observer import PipelineEvent, EventType
                event = PipelineEvent(
                    event_type=EventType.INTEGRATION_CONFLICT,
                    card_id=card_id,
                    developer_name=winner,
                    data={
                        "winner": winner,
                        "tests_failed": regression_results.get('failed', 0),
                        "exit_code": regression_results.get('exit_code', 1)
                    }
                )
                self.observable.notify(event)

        # Update Kanban
        self.update_progress({"step": "updating_kanban", "progress_percent": 85})
        self.board.move_card(card_id, "testing", "pipeline-orchestrator")

        # Store in RAG
        self.update_progress({"step": "storing_in_rag", "progress_percent": 95})
        # Store in RAG using helper (DRY)

        RAGStorageHelper.store_stage_artifact(

            rag=self.rag,
            stage_name="integration_result",
            card_id=card_id,
            task_title=card.get('title', 'Unknown'),
            content=f"Integration of {winner} solution completed",
            metadata={
                "winner": winner,
                "tests_passed": regression_results.get('passed', 0),
                "deployment_verified": deployment_verified
            }
        )

        # Update progress: complete
        self.update_progress({"step": "complete", "progress_percent": 100})

        return {
            "stage": "integration",
            "winner": winner,
            "regression_tests": regression_results,
            "deployment_verified": deployment_verified,
            "status": status
        }

    def get_stage_name(self) -> str:
        return "integration"


# ============================================================================
# TESTING STAGE
# ============================================================================

