#!/usr/bin/env python3
"""
DependencyValidationStage

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


class DependencyValidationStage(PipelineStage, SupervisedStageMixin, DebugMixin):
    """
    Single Responsibility: Validate runtime dependencies

    This stage ONLY validates dependencies - nothing else.

    Integrates with supervisor for:
    - Dependency validation failure tracking
    - Automatic heartbeat and health monitoring
    """

    def __init__(
        self,
        board: KanbanBoard,
        messenger: AgentMessenger,
        logger: LoggerInterface,
        supervisor: Optional['SupervisorAgent'] = None
    ):
        # Initialize PipelineStage
        PipelineStage.__init__(self)

        # Initialize SupervisedStageMixin for health monitoring
        SupervisedStageMixin.__init__(
            self,
            supervisor=supervisor,
            stage_name="DependencyValidationStage",
            heartbeat_interval=15
        )

        # Initialize DebugMixin
        DebugMixin.__init__(self, component_name="dependency_validation")

        self.board = board
        self.messenger = messenger
        self.logger = logger

    def execute(self, card: Dict, context: Dict) -> Dict:
        """Execute with supervisor monitoring"""
        metadata = {
            "task_id": card.get('card_id'),
            "stage": "dependencies"
        }

        with self.supervised_execution(metadata):
            return self._do_work(card, context)

    def _do_work(self, card: Dict, context: Dict) -> Dict:
        """Internal method - performs dependency validation"""
        self.logger.log("Starting Dependency Validation Stage", "STAGE")

        card_id = card['card_id']

        # DEBUG: Log stage entry
        self.debug_log("Starting dependency validation", card_id=card_id)

        # Update progress: starting validation
        self.update_progress({"step": "starting", "progress_percent": 10})

        # Check Python version
        self.update_progress({"step": "checking_python_version", "progress_percent": 30})
        with self.debug_section("Python Version Check"):
            python_check = self._check_python_version()
            self.debug_if_enabled('log_checks', "Python version check",
                                 version=python_check.get('found'),
                                 compatible=python_check.get('compatible'))

        # Test basic imports
        self.update_progress({"step": "testing_imports", "progress_percent": 50})
        with self.debug_section("Import Tests"):
            import_check = self._test_imports()
            self.debug_if_enabled('log_checks', "Import tests",
                                 tested=import_check.get('imports_tested'),
                                 all_passed=import_check.get('all_passed'))

        # Determine status
        self.update_progress({"step": "determining_status", "progress_percent": 70})
        all_passed = python_check['compatible'] and import_check['all_passed']
        status = "PASS" if all_passed else "BLOCKED"

        # DEBUG: Dump validation results
        self.debug_dump_if_enabled('dump_validation', "Dependency Validation Results", {
            "python_check": python_check,
            "import_check": import_check,
            "status": status
        })

        if status == "PASS":
            self.logger.log("Dependency validation PASSED", "SUCCESS")
            self.update_progress({"step": "sending_success_notification", "progress_percent": 85})
            self._send_success_notification(card_id)
        else:
            self.logger.log("Dependency validation FAILED", "ERROR")
            self.update_progress({"step": "sending_failure_notification", "progress_percent": 85})
            self._send_failure_notification(card_id)

        # Update Kanban
        self.update_progress({"step": "updating_kanban", "progress_percent": 95})
        self.board.move_card(card_id, "development", "pipeline-orchestrator")

        # Update progress: complete
        self.update_progress({"step": "complete", "progress_percent": 100})

        return {
            "stage": "dependencies",
            "status": "COMPLETE" if all_passed else "FAILED",
            "validation_status": status,  # Keep original PASS/BLOCKED info
            "checks": {
                "python_version": python_check,
                "import_test": import_check
            }
        }

    def get_stage_name(self) -> str:
        return "dependencies"

    def _check_python_version(self) -> Dict:
        """Check Python version compatibility"""
        import sys
        version = f"{sys.version_info.major}.{sys.version_info.minor}"
        compatible = sys.version_info >= (3, 8)

        return {
            "status": "PASS" if compatible else "FAIL",
            "required": "3.8+",
            "found": version,
            "compatible": compatible
        }

    def _test_imports(self) -> Dict:
        """Test that required imports work"""
        test_imports = ["json", "subprocess", "pathlib", "bs4"]
        all_passed = True

        for module in test_imports:
            try:
                __import__(module)
            except ImportError:
                all_passed = False
                break

        return {
            "status": "PASS" if all_passed else "FAIL",
            "imports_tested": test_imports,
            "all_passed": all_passed
        }

    def _send_success_notification(self, card_id: str):
        """Notify success"""
        self.messenger.send_notification(
            to_agent="all",
            card_id=card_id,
            notification_type="dependencies_validated",
            data={"status": "PASS"},
            priority="medium"
        )

    def _send_failure_notification(self, card_id: str):
        """Notify failure"""
        self.messenger.send_error(
            to_agent="artemis-orchestrator",
            card_id=card_id,
            error_type="dependency_validation_failed",
            details={"severity": "high", "blocks_pipeline": True},
            priority="high"
        )


# ============================================================================
# DEVELOPMENT STAGE (New - Invokes Developer A/B)
# ============================================================================

