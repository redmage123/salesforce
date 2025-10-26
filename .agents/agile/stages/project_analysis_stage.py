#!/usr/bin/env python3
"""
ProjectAnalysisStage

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


class ProjectAnalysisStage(PipelineStage, SupervisedStageMixin, DebugMixin):
    """
    Single Responsibility: Analyze project BEFORE implementation

    This stage analyzes tasks across 8 dimensions:
    1. Scope & Requirements
    2. Technical Approach
    3. Architecture & Design Patterns
    4. Security
    5. Scalability & Performance
    6. Error Handling & Edge Cases
    7. Testing Strategy
    8. Dependencies & Integration

    Identifies issues, gets user approval, and sends approved changes downstream.

    Integrates with supervisor for:
    - Unexpected state handling (user rejection, analysis failures)
    - LLM cost tracking (if using LLM for analysis)
    - Automatic heartbeat and health monitoring
    """

    def __init__(
        self,
        board: KanbanBoard,
        messenger: AgentMessenger,
        rag: RAGAgent,
        logger: LoggerInterface,
        supervisor: Optional['SupervisorAgent'] = None,
        llm_client: Optional[Any] = None,
        config: Optional[Any] = None
    ):
        # Initialize PipelineStage
        PipelineStage.__init__(self)

        # Initialize SupervisedStageMixin for health monitoring
        SupervisedStageMixin.__init__(
            self,
            supervisor=supervisor,
            stage_name="ProjectAnalysisStage",
            heartbeat_interval=15
        )

        # Initialize DebugMixin
        DebugMixin.__init__(self, component_name="project_analysis")

        self.board = board
        self.messenger = messenger
        self.rag = rag
        self.logger = logger
        self.llm_client = llm_client
        self.config = config  # Store config for auto-approve setting

        # Initialize ProjectAnalysisEngine with LLM support
        self.engine = ProjectAnalysisEngine(
            llm_client=llm_client,
            config=config,
            enable_llm_analysis=True
        )
        self.approval_handler = UserApprovalHandler()

    def execute(self, card: Dict, context: Dict) -> Dict:
        """Run project analysis and get user approval with supervisor monitoring"""
        # Use supervised execution context manager for automatic monitoring
        metadata = {
            "task_id": card.get('card_id'),
            "stage": "project_analysis"
        }

        with self.supervised_execution(metadata):
            return self._do_analysis(card, context)

    def _do_analysis(self, card: Dict, context: Dict) -> Dict:
        """Internal method that performs the actual analysis work"""
        self.logger.log("Starting Project Analysis Stage", "STAGE")

        card_id = card['card_id']

        # DEBUG: Log stage entry
        self.debug_log("Starting project analysis", card_id=card_id, title=card.get('title'))

        # Get RAG recommendations from context
        rag_recommendations = context.get('rag_recommendations', {})

        # Build analysis context
        analysis_context = {
            'rag_recommendations': rag_recommendations,
            'workflow_plan': context.get('workflow_plan', {}),
            'priority': card.get('priority', 'medium'),
            'complexity': context.get('workflow_plan', {}).get('complexity', 'medium')
        }

        # DEBUG: Dump analysis context
        self.debug_dump_if_enabled('dump_analysis_context', "Analysis Context", analysis_context)

        # Update progress: starting analysis
        self.update_progress({"step": "analyzing_task", "progress_percent": 10})

        # Run analysis across all dimensions
        with self.debug_section("Task Analysis"):
            analysis = self.engine.analyze_task(card, analysis_context)

            # DEBUG: Log analysis results
            self.debug_if_enabled('log_analysis', "Analysis complete",
                                 total_issues=analysis['total_issues'],
                                 critical=analysis['critical_count'],
                                 high=analysis['high_count'])

        # Update progress: analysis complete
        self.update_progress({"step": "analysis_complete", "progress_percent": 40})

        self.logger.log(f"Analysis complete: {analysis['total_issues']} issues found", "INFO")
        self.logger.log(f"  CRITICAL: {analysis['critical_count']}", "WARNING" if analysis['critical_count'] > 0 else "INFO")
        self.logger.log(f"  HIGH: {analysis['high_count']}", "WARNING" if analysis['high_count'] > 0 else "INFO")
        self.logger.log(f"  MEDIUM: {analysis['medium_count']}", "INFO")

        # Update progress: presenting findings
        self.update_progress({"step": "presenting_findings", "progress_percent": 50})

        # Check auto-approve config first (before presenting to user)
        auto_approve = self.config.get('ARTEMIS_AUTO_APPROVE_PROJECT_ANALYSIS', True) if self.config else True

        if not auto_approve:
            # Interactive mode - present findings to user
            presentation = self.approval_handler.present_findings(analysis)
            print("\n" + presentation)
        else:
            # Auto-approve mode - log summary instead of full presentation
            self.logger.log(f"📊 Analysis Summary: {analysis['total_issues']} issues (Critical: {analysis['critical_count']}, High: {analysis['high_count']}, Medium: {analysis['medium_count']})", "INFO")

        # Update progress: waiting for approval
        self.update_progress({"step": "waiting_for_approval", "progress_percent": 60})

        if auto_approve:
            # Use agent's recommendation
            recommendation = analysis.get('recommendation', 'APPROVE_ALL')
            reason = analysis.get('recommendation_reason', 'Auto-approved by agent')
            self.logger.log(f"✅ Auto-approving based on agent recommendation: {recommendation}", "INFO")
            self.logger.log(f"   Reason: {reason}", "INFO")

            # Map recommendation to approval decision
            if recommendation == "REJECT":
                decision_choice = "4"  # REJECT
            elif recommendation == "APPROVE_CRITICAL":
                decision_choice = "2"  # APPROVE_CRITICAL
            else:
                decision_choice = "1"  # APPROVE ALL
        else:
            # Interactive mode - would prompt user (not implemented in background mode)
            self.logger.log("⚠️  Interactive approval required but running in non-interactive mode", "WARNING")
            self.logger.log(f"   Agent recommends: {analysis.get('recommendation', 'APPROVE_ALL')}", "INFO")
            decision_choice = "1"  # Default to approve all

        decision = self.approval_handler.get_approval_decision(analysis, decision_choice)

        self.logger.log(f"✅ User decision: {'APPROVED' if decision['approved'] else 'REJECTED'}", "SUCCESS")

        # Update progress: processing decision
        self.update_progress({"step": "processing_decision", "progress_percent": 70})

        # Send approved changes to Architecture Agent
        if decision['approved'] and len(decision['approved_issues']) > 0:
            self._send_approved_changes_to_architecture(card_id, decision['approved_issues'])

        # Update progress: updating kanban
        self.update_progress({"step": "updating_kanban", "progress_percent": 85})

        # Update Kanban
        self.board.update_card(card_id, {
            "analysis_status": "complete",
            "critical_issues": analysis['critical_count'],
            "approved_changes": decision['approved_count']
        })

        # Update progress: storing in RAG
        self.update_progress({"step": "storing_in_rag", "progress_percent": 95})

        # Store in RAG
        self._store_analysis_in_rag(card_id, card, analysis, decision)

        # Convert to JSON-serializable format
        serializable_decision = {
            "approved": decision['approved'],
            "approved_count": decision['approved_count'],
            "approved_issues_count": len(decision.get('approved_issues', []))
        }

        serializable_analysis = {
            "total_issues": analysis['total_issues'],
            "critical_count": analysis['critical_count'],
            "high_count": analysis['high_count'],
            "medium_count": analysis['medium_count'],
            "dimensions_analyzed": analysis['dimensions_analyzed']
        }

        # Update progress: complete
        self.update_progress({"step": "complete", "progress_percent": 100})

        return {
            "stage": "project_analysis",
            "analysis": serializable_analysis,
            "decision": serializable_decision,
            "status": "COMPLETE"
        }

    def get_stage_name(self) -> str:
        return "project_analysis"

    def _send_approved_changes_to_architecture(self, card_id: str, approved_issues: List):
        """Send approved changes to Architecture Agent via AgentMessenger"""

        # Format approved changes for Architecture Agent using list comprehension
        changes_summary = [
            {
                "category": issue.category,
                "description": issue.description,
                "suggestion": issue.suggestion,
                "severity": issue.severity.value
            }
            for issue in approved_issues
        ]

        self.messenger.send_data_update(
            to_agent="architecture-agent",
            card_id=card_id,
            update_type="project_analysis_complete",
            data={
                "approved_changes": changes_summary,
                "total_changes": len(changes_summary)
            },
            priority="high"
        )

        self.messenger.update_shared_state(
            card_id=card_id,
            updates={
                "current_stage": "project_analysis_complete",
                "approved_changes_count": len(changes_summary)
            }
        )

        self.logger.log(f"Sent {len(changes_summary)} approved changes to Architecture Agent", "SUCCESS")

    def _store_analysis_in_rag(self, card_id: str, card: Dict, analysis: Dict, decision: Dict):
        """Store analysis results in RAG for future learning"""

        # Create content summary
        content_parts = [
            f"Project Analysis for: {card.get('title', 'Unknown')}",
            f"Total Issues: {analysis['total_issues']}",
            f"Critical: {analysis['critical_count']}, High: {analysis['high_count']}, Medium: {analysis['medium_count']}",
            f"User Decision: {'APPROVED' if decision['approved'] else 'REJECTED'}",
            f"Approved Changes: {decision['approved_count']}"
        ]

        # Add critical issues to content using list comprehension
        if analysis['critical_issues']:
            content_parts.append("\nCritical Issues:")
            content_parts.extend([
                f"  - [{issue.category}] {issue.description}"
                for issue in analysis['critical_issues']
            ])

        content = "\n".join(content_parts)

        # Store in RAG using helper (DRY)
        RAGStorageHelper.store_stage_artifact(
            rag=self.rag,
            stage_name="project_analysis",
            card_id=card_id,
            task_title=card.get('title', 'Unknown'),
            content=content,
            metadata={
                "total_issues": analysis['total_issues'],
                "critical_count": analysis['critical_count'],
                "high_count": analysis['high_count'],
                "medium_count": analysis['medium_count'],
                "approved": decision['approved'],
                "approved_count": decision['approved_count'],
                "dimensions_analyzed": analysis['dimensions_analyzed']
            }
        )


# ============================================================================
# ARCHITECTURE STAGE
# ============================================================================

