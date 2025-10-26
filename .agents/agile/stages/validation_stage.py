#!/usr/bin/env python3
"""
ValidationStage

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
from path_config_service import get_developer_tests_path
from kanban_manager import KanbanBoard
from agent_messenger import AgentMessenger
from debug_mixin import DebugMixin
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


class ValidationStage(PipelineStage, SupervisedStageMixin, DebugMixin):
    """
    Single Responsibility: Validate developer solutions

    This stage ONLY validates test quality and TDD compliance - nothing else.

    Integrates with supervisor for:
    - Test execution in sandbox
    - Test failure tracking
    - Test timeout handling
    - Automatic heartbeat and health monitoring
    """

    def __init__(
        self,
        board: KanbanBoard,
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
            stage_name="ValidationStage",
            heartbeat_interval=15
        )

        # Initialize DebugMixin
        DebugMixin.__init__(self, component_name="validation")

        self.board = board
        self.test_runner = test_runner
        self.logger = logger
        self.observable = observable
        self.supervisor = supervisor

    def execute(self, card: Dict, context: Dict) -> Dict:
        """Execute with supervisor monitoring"""
        metadata = {
            "task_id": card.get('card_id'),
            "stage": "validation"
        }

        with self.supervised_execution(metadata):
            return self._do_work(card, context)

    def _do_work(self, card: Dict, context: Dict) -> Dict:
        """Internal method - validates developer solutions"""
        self.logger.log("Starting Validation Stage", "STAGE")

        card_id = card.get('card_id', 'unknown')

        # Update progress: starting
        self.update_progress({"step": "starting", "progress_percent": 10})

        # Notify validation started
        if self.observable:
            from pipeline_observer import PipelineEvent, EventType
            event = PipelineEvent(
                event_type=EventType.VALIDATION_STARTED,
                card_id=card_id,
                data={"num_developers": context.get('parallel_developers', 1)}
            )
            self.observable.notify(event)

        # Get number of developers from context
        num_developers = context.get('parallel_developers', 1)

        # Update progress: validating developers
        self.update_progress({"step": "validating_developers", "progress_percent": 30})

        # Validate each developer's solution
        developers = {}
        all_approved = True

        for i in range(num_developers):
            dev_name = "developer-a" if i == 0 else f"developer-{chr(98+i-1)}"

            # Update progress for each developer
            progress = 30 + (i + 1) * (40 // max(num_developers, 1))
            self.update_progress({"step": f"validating_{dev_name}", "progress_percent": progress})

            dev_result = self._validate_developer(dev_name, card_id)
            developers[dev_name] = dev_result

            if dev_result['status'] != "APPROVED":
                all_approved = False

        # Update progress: processing results
        self.update_progress({"step": "processing_results", "progress_percent": 70})

        decision = "ALL_APPROVED" if all_approved else "SOME_BLOCKED"
        approved_devs = [k for k, v in developers.items() if v['status'] == "APPROVED"]

        result = {
            "stage": "validation",
            "num_developers": num_developers,
            "developers": developers,
            "decision": decision,
            "approved_developers": approved_devs
        }

        # Notify validation completed or failed
        self.update_progress({"step": "sending_notifications", "progress_percent": 85})
        if self.observable:
            from pipeline_observer import PipelineEvent, EventType
            if all_approved:
                event = PipelineEvent(
                    event_type=EventType.VALIDATION_COMPLETED,
                    card_id=card_id,
                    data={
                        "decision": decision,
                        "approved_developers": approved_devs,
                        "num_developers": num_developers
                    }
                )
                self.observable.notify(event)
            else:
                error = Exception(f"Validation failed: {len(approved_devs)}/{num_developers} developers approved")
                event = PipelineEvent(
                    event_type=EventType.VALIDATION_FAILED,
                    card_id=card_id,
                    error=error,
                    data={
                        "decision": decision,
                        "approved_developers": approved_devs,
                        "blocked_developers": [k for k, v in developers.items() if v['status'] != "APPROVED"]
                    }
                )
                self.observable.notify(event)

        # Update progress: complete
        self.update_progress({"step": "complete", "progress_percent": 100})

        return result

    def get_stage_name(self) -> str:
        return "validation"

    def _validate_developer(self, dev_name: str, card_id: str = None) -> Dict:
        """Validate a single developer's solution"""
        # Use path config service to get correct test path (not hardcoded /tmp)
        test_path = get_developer_tests_path(dev_name)

        # DEBUG: Log path resolution using mixin
        self.debug_if_enabled('log_paths', f"Resolved test path for {dev_name}", path=test_path)

        self.logger.log(f"Validating {dev_name} solution...", "INFO")

        # Run tests
        test_results = self.test_runner.run_tests(test_path)

        # DEBUG: Dump full test results using mixin
        self.debug_dump_if_enabled('dump_test_results', f"Test results for {dev_name}", test_results)

        # DEBUG: Show verbose test output using mixin
        if self.is_debug_feature_enabled('verbose_test_output'):
            if test_results.get('stdout'):
                self.debug_log(f"Test stdout for {dev_name}:")
                self.logger.log(test_results['stdout'], "DEBUG")
            if test_results.get('stderr'):
                self.debug_log(f"Test stderr for {dev_name}:")
                self.logger.log(test_results['stderr'], "DEBUG")

        # Determine status
        status = "APPROVED" if test_results['exit_code'] == 0 else "BLOCKED"

        self.logger.log(f"{dev_name}: {status} (exit_code={test_results['exit_code']})",
                       "SUCCESS" if status == "APPROVED" else "WARNING")

        return {
            "developer": dev_name,
            "status": status,
            "test_results": test_results
        }


# ============================================================================
# INTEGRATION STAGE
# ============================================================================

