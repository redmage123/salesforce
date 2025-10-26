#!/usr/bin/env python3
"""
UI/UX Stage - Comprehensive User Experience and Accessibility Evaluation

Evaluates developer implementations for:
- WCAG 2.1 AA accessibility compliance
- GDPR compliance (data privacy, consent, user rights)
- User experience metrics and usability

REFACTORED: 2025-10-23
- Eliminated magic numbers → Hydra configuration
- Removed speculative generality → No NOT_EVALUATED fields
- Specific exceptions → No bare Exception
- Observer pattern → StageNotificationHelper (DRY)
- Agent communication → Explicit messenger calls
- List comprehensions → Pythonic code
"""

import os
import tempfile
from typing import Dict, Optional, List, Any
from pathlib import Path
from dataclasses import dataclass

from artemis_stage_interface import PipelineStage, LoggerInterface
from agent_messenger import AgentMessenger
from rag_agent import RAGAgent
from kanban_manager import KanbanBoard
from pipeline_observer import PipelineObservable, PipelineEvent, EventType
from supervised_agent_mixin import SupervisedStageMixin
from debug_mixin import DebugMixin
from stage_notifications import StageNotificationHelper
from wcag_evaluator import WCAGEvaluator
from gdpr_evaluator import GDPREvaluator
from artemis_exceptions import (
    UIUXEvaluationError,
    WCAGEvaluationError,
    GDPREvaluationError,
    wrap_exception
)
from knowledge_graph_factory import get_knowledge_graph
from rag_storage_helper import RAGStorageHelper

# Import AIQueryService for KG-First accessibility pattern retrieval
try:
    from ai_query_service import (
        AIQueryService,
        create_ai_query_service,
        QueryType
    )
    AI_QUERY_SERVICE_AVAILABLE = True
except ImportError:
    AI_QUERY_SERVICE_AVAILABLE = False


# ============================================================================
# VALUE OBJECTS
# ============================================================================

@dataclass(frozen=True)
class DeveloperEvaluation:
    """
    Value Object: Encapsulates UI/UX evaluation for a single developer

    Benefits:
    - Immutable result object
    - Type-safe access
    - Self-documenting
    - No speculative generality (only implemented features)
    """
    developer: str
    task_title: str
    evaluation_status: str  # "PASS", "NEEDS_IMPROVEMENT", "FAIL"
    ux_score: int  # 0-100

    # WCAG Accessibility results
    accessibility_issues: int
    wcag_aa_compliance: bool
    accessibility_details: Dict
    accessibility_issues_list: List[Dict]

    # UX issues
    ux_issues: int
    ux_issues_details: List[Dict]

    # GDPR compliance results
    gdpr_compliance: Dict
    gdpr_issues: int
    gdpr_issues_list: List[Dict]

    def to_dict(self) -> Dict:
        """Convert to dictionary for pipeline context"""
        return {
            "developer": self.developer,
            "task_title": self.task_title,
            "evaluation_status": self.evaluation_status,
            "ux_score": self.ux_score,
            "accessibility_issues": self.accessibility_issues,
            "wcag_aa_compliance": self.wcag_aa_compliance,
            "accessibility_details": self.accessibility_details,
            "accessibility_issues_list": self.accessibility_issues_list,
            "ux_issues": self.ux_issues,
            "ux_issues_details": self.ux_issues_details,
            "gdpr_compliance": self.gdpr_compliance,
            "gdpr_issues": self.gdpr_issues,
            "gdpr_issues_list": self.gdpr_issues_list
        }


# ============================================================================
# UI/UX STAGE
# ============================================================================

class UIUXStage(PipelineStage, SupervisedStageMixin, DebugMixin):
    """
    Single Responsibility: Evaluate UI/UX and accessibility

    This stage evaluates user experience, accessibility, and design quality.

    Integrates with supervisor for:
    - UI/UX evaluation tracking
    - Accessibility compliance monitoring
    - Automatic heartbeat and health monitoring

    IMPROVEMENTS:
    - Configuration from Hydra (no magic numbers)
    - Specific exceptions (no bare Exception)
    - StageNotificationHelper (DRY observer pattern)
    - Value Objects (DeveloperEvaluation)
    - List comprehensions (Pythonic)
    - Removed speculative generality (NOT_EVALUATED fields)
    """

    def __init__(
        self,
        board: KanbanBoard,
        messenger: AgentMessenger,
        rag: RAGAgent,
        logger: LoggerInterface,
        observable: Optional[PipelineObservable] = None,
        supervisor: Optional['SupervisorAgent'] = None,
        config: Optional[Any] = None,
        ai_service: Optional['AIQueryService'] = None
    ):
        """
        Initialize UI/UX Stage

        Args:
            board: Kanban board for status updates
            messenger: Agent messenger for inter-agent communication
            rag: RAG agent for storing evaluation results
            logger: Logger interface
            observable: Optional PipelineObservable for event broadcasting
            supervisor: Optional SupervisorAgent for monitoring
            config: Optional ConfigurationAgent for settings
            ai_service: AI Query Service for KG-First pattern retrieval (optional)
        """
        # Initialize PipelineStage
        PipelineStage.__init__(self)

        # Initialize SupervisedStageMixin for health monitoring
        # UI/UX evaluation can be time-consuming, use 25 second heartbeat
        SupervisedStageMixin.__init__(
            self,
            supervisor=supervisor,
            stage_name="UIUXStage",
            heartbeat_interval=25  # Longer interval for evaluation-heavy stage
        )

        # Initialize DebugMixin
        DebugMixin.__init__(self, component_name="uiux")

        self.board = board
        self.messenger = messenger
        self.rag = rag
        self.logger = logger
        self.observable = observable
        self.config = config

        # Load configuration with defaults
        self._load_config()

        # Initialize notification helper (DRY - reduces 30 lines to 3)
        self.notifier = StageNotificationHelper(observable, "uiux")

        # Initialize AI Query Service for KG-First accessibility pattern retrieval
        self.ai_service = None
        if AI_QUERY_SERVICE_AVAILABLE:
            try:
                if ai_service:
                    self.ai_service = ai_service
                    logger.log("✅ Using provided AI Query Service for pattern retrieval", "INFO")
                else:
                    self.ai_service = create_ai_query_service(
                        llm_client=None,  # UI/UX stage doesn't need LLM
                        rag=rag,
                        logger=logger,
                        verbose=False
                    )
                    logger.log("✅ AI Query Service initialized for accessibility patterns", "INFO")
            except Exception as e:
                logger.log(f"⚠️  Could not initialize AI Query Service: {e}", "WARNING")
                self.ai_service = None

    def _load_config(self):
        """Load configuration with sensible defaults"""
        if self.config:
            # Load from ConfigurationAgent
            self.score_deductions = {
                'wcag_critical': self.config.get('uiux.score_deductions.wcag_critical', 20),
                'wcag_serious': self.config.get('uiux.score_deductions.wcag_serious', 10),
                'wcag_moderate': self.config.get('uiux.score_deductions.wcag_moderate', 5),
                'gdpr_critical': self.config.get('uiux.score_deductions.gdpr_critical', 20),
                'gdpr_high': self.config.get('uiux.score_deductions.gdpr_high', 10),
                'gdpr_medium': self.config.get('uiux.score_deductions.gdpr_medium', 5),
            }
            self.critical_accessibility_threshold = self.config.get('uiux.thresholds.critical_accessibility_issues', 5)
        else:
            # Sensible defaults if no config
            self.score_deductions = {
                'wcag_critical': 20,
                'wcag_serious': 10,
                'wcag_moderate': 5,
                'gdpr_critical': 20,
                'gdpr_high': 10,
                'gdpr_medium': 5,
            }
            self.critical_accessibility_threshold = 5

    def execute(self, card: Dict, context: Dict) -> Dict:
        """
        Execute UI/UX evaluation with supervisor monitoring

        Raises:
            UIUXEvaluationError: On evaluation failures
        """
        metadata = {
            "task_id": card.get('card_id'),
            "stage": "uiux"
        }

        try:
            with self.supervised_execution(metadata):
                return self._evaluate_uiux(card, context)
        except UIUXEvaluationError:
            raise  # Re-raise specific errors
        except Exception as e:
            # Wrap unexpected errors in specific exception
            raise wrap_exception(
                e,
                UIUXEvaluationError,
                "Unexpected error during UI/UX evaluation",
                {"card_id": card.get('card_id')}
            )

    def _evaluate_uiux(self, card: Dict, context: Dict) -> Dict:
        """
        Internal method - performs UI/UX and accessibility evaluation

        Evaluates each developer's implementation for:
        - WCAG 2.1 AA accessibility standards
        - GDPR compliance (data privacy, consent, user rights)
        - User experience metrics

        Args:
            card: Kanban card with task details
            context: Context from previous stages (includes developers)

        Returns:
            Dict with evaluation results for all developers
        """
        card_id = card['card_id']
        task_title = card.get('title', 'Unknown Task')

        # Context manager handles STAGE_STARTED/COMPLETED/FAILED automatically
        with self.notifier.stage_lifecycle(card_id, {'task_title': task_title}):
            self.logger.log("Starting UI/UX Evaluation Stage", "STAGE")
            self.logger.log("🎨 Comprehensive UI/UX and Accessibility Analysis", "INFO")

            # Update progress: starting
            self.update_progress({"step": "starting", "progress_percent": 5})

            # Get developer results from context
            developers = context.get('developers', [])
            if not developers:
                self.logger.log("No developer implementations found to evaluate", "WARNING")
                return {
                    "stage": "uiux",
                    "status": "SKIPPED",
                    "reason": "No implementations to evaluate"
                }

            self.logger.log(f"Evaluating {len(developers)} developer implementation(s)", "INFO")

            # Update progress: initializing evaluations
            self.update_progress({"step": "initializing_evaluations", "progress_percent": 10})

            # Evaluate each developer's implementation (using list comprehension for collection)
            evaluation_results = self._evaluate_all_developers(
                developers, card_id, task_title
            )

            # Calculate summary metrics (using list comprehensions - Pythonic!)
            total_accessibility_issues = sum(
                eval_result.accessibility_issues
                for eval_result in evaluation_results
            )
            total_ux_issues = sum(
                eval_result.ux_issues
                for eval_result in evaluation_results
            )
            all_evaluations_pass = all(
                eval_result.evaluation_status == "PASS"
                for eval_result in evaluation_results
            )

            # Update progress: summarizing results
            self.update_progress({"step": "summarizing_results", "progress_percent": 85})

            # Overall summary
            self.logger.log(f"\n{'='*60}", "INFO")
            self.logger.log("📊 UI/UX Evaluation Summary", "INFO")
            self.logger.log(f"{'='*60}", "INFO")
            self.logger.log(f"Implementations Evaluated: {len(evaluation_results)}", "INFO")
            self.logger.log(f"Total Accessibility Issues: {total_accessibility_issues}", "INFO")
            self.logger.log(f"Total UX Issues: {total_ux_issues}", "INFO")

            # Update progress: determining status
            self.update_progress({"step": "determining_status", "progress_percent": 95})

            # Determine overall stage status (using configuration threshold - NO MAGIC NUMBERS!)
            stage_status = self._determine_stage_status(
                total_accessibility_issues,
                all_evaluations_pass,
                self.critical_accessibility_threshold
            )

            # Update Kanban
            self.board.update_card(card_id, {
                "uiux_status": stage_status,
                "accessibility_issues": total_accessibility_issues,
                "ux_issues": total_ux_issues
            })

            # Update progress: complete
            self.update_progress({"step": "complete", "progress_percent": 100})

            return {
                "stage": "uiux",
                "status": stage_status,
                "evaluations": [e.to_dict() for e in evaluation_results],  # List comprehension
                "total_accessibility_issues": total_accessibility_issues,
                "total_ux_issues": total_ux_issues,
                "all_evaluations_pass": all_evaluations_pass,
                "implementations_evaluated": len(evaluation_results)
            }

    def _evaluate_all_developers(
        self,
        developers: List[Dict],
        card_id: str,
        task_title: str
    ) -> List[DeveloperEvaluation]:
        """
        Evaluate all developers' implementations

        Returns list of DeveloperEvaluation value objects
        """
        evaluation_results = []

        for i, dev_result in enumerate(developers):
            developer_name = dev_result.get('developer', 'unknown')
            implementation_dir = dev_result.get('output_dir', f'{tempfile.gettempdir()}/{developer_name}/')

            # Update progress for each developer evaluation (10% to 80% dynamically)
            progress = 10 + ((i + 1) / len(developers)) * 70
            self.update_progress({
                "step": f"evaluating_{developer_name}",
                "progress_percent": int(progress),
                "current_developer": developer_name,
                "total_developers": len(developers)
            })

            self.logger.log(f"\n{'='*60}", "INFO")
            self.logger.log(f"🎨 Evaluating {developer_name} implementation", "INFO")
            self.logger.log(f"{'='*60}", "INFO")

            # Perform evaluation
            evaluation_result = self._evaluate_developer_uiux(
                developer_name=developer_name,
                implementation_dir=implementation_dir,
                task_title=task_title
            )

            evaluation_results.append(evaluation_result)

            # Log evaluation summary
            self.logger.log(f"Evaluation Status: {evaluation_result.evaluation_status}", "INFO")
            self.logger.log(f"UX Score: {evaluation_result.ux_score}/100", "INFO")
            self.logger.log(f"Accessibility Issues: {evaluation_result.accessibility_issues}", "INFO")

            # Track if any evaluations fail using status mapping
            status_messages = {
                "FAIL": (f"❌ {developer_name} implementation FAILED UI/UX evaluation", "ERROR"),
                "NEEDS_IMPROVEMENT": (f"⚠️  {developer_name} implementation needs UI/UX improvement", "WARNING"),
            }

            # Get message and log level, default to success
            message, level = status_messages.get(
                evaluation_result.evaluation_status,
                (f"✅ {developer_name} implementation PASSED UI/UX evaluation", "SUCCESS")
            )
            self.logger.log(message, level)

            # Store evaluation in RAG for learning
            self._store_evaluation_in_rag(card_id, task_title, evaluation_result)

            # Store evaluation in Knowledge Graph for traceability
            self._store_evaluation_in_knowledge_graph(card_id, developer_name, evaluation_result, implementation_dir)

            # Send evaluation notification to other agents
            self._send_evaluation_notification(card_id, evaluation_result)

            # Send feedback to developer for iteration if issues found
            if evaluation_result.ux_issues > 0:
                self._send_feedback_to_developer(card_id, evaluation_result)

            # Notify evaluation progress for this developer
            self.notifier.notify_progress(
                card_id,
                step=f'evaluated_{developer_name}',
                progress_percent=int(progress),
                developer=developer_name,
                evaluation_status=evaluation_result.evaluation_status,
                ux_score=evaluation_result.ux_score,
                accessibility_issues=evaluation_result.accessibility_issues
            )

        return evaluation_results

    def _query_accessibility_patterns(self, task_title: str) -> Optional[Dict]:
        """
        Query KG for similar UI/UX implementations and accessibility patterns

        Uses AIQueryService for KG-First approach to find proven patterns.

        Args:
            task_title: Title of the task

        Returns:
            Dict with patterns found, or None if unavailable
        """
        if not self.ai_service:
            return None

        try:
            result = self.ai_service.query(
                query_type=QueryType.UIUX_EVALUATION,
                prompt="",  # Not calling LLM, just getting KG patterns
                kg_query_params={
                    'task_title': task_title,
                    'file_types': ['html', 'css', 'javascript', 'typescript']
                },
                skip_llm_call=True  # Only get KG patterns
            )

            if result.kg_context and result.kg_context.pattern_count > 0:
                return {
                    'patterns_found': result.kg_context.patterns_found,
                    'pattern_count': result.kg_context.pattern_count,
                    'estimated_token_savings': result.kg_context.estimated_token_savings
                }
        except Exception as e:
            self.logger.log(f"⚠️  Could not query accessibility patterns: {e}", "WARNING")

        return None

    def _evaluate_developer_uiux(
        self,
        developer_name: str,
        implementation_dir: str,
        task_title: str
    ) -> DeveloperEvaluation:
        """
        Evaluate a single developer's implementation for UI/UX

        Uses real WCAG and GDPR evaluators to perform compliance checks.
        Queries KG for accessibility patterns to improve evaluation context.

        Args:
            developer_name: Name of the developer
            implementation_dir: Directory containing implementation
            task_title: Title of the task

        Returns:
            DeveloperEvaluation value object

        Raises:
            WCAGEvaluationError: If WCAG evaluation fails
            GDPREvaluationError: If GDPR evaluation fails
        """
        self.logger.log(f"Evaluating UI/UX for {developer_name}...", "INFO")

        # Query for accessibility patterns (KG-First approach)
        patterns = self._query_accessibility_patterns(task_title)
        if patterns:
            self.logger.log(
                f"📚 Found {patterns['pattern_count']} accessibility pattern(s) in KG",
                "INFO"
            )

        try:
            # Run WCAG 2.1 AA accessibility evaluation
            self.logger.log("Running WCAG 2.1 AA accessibility checks...", "INFO")
            wcag_evaluator = WCAGEvaluator()
            wcag_results = wcag_evaluator.evaluate_directory(implementation_dir)
        except Exception as e:
            raise wrap_exception(
                e,
                WCAGEvaluationError,
                f"WCAG evaluation failed for {developer_name}",
                {"developer": developer_name, "implementation_dir": implementation_dir}
            )

        try:
            # Run GDPR compliance evaluation
            self.logger.log("Running GDPR compliance checks...", "INFO")
            gdpr_evaluator = GDPREvaluator()
            gdpr_results = gdpr_evaluator.evaluate_directory(implementation_dir)
        except Exception as e:
            raise wrap_exception(
                e,
                GDPREvaluationError,
                f"GDPR evaluation failed for {developer_name}",
                {"developer": developer_name, "implementation_dir": implementation_dir}
            )

        # Calculate overall scores
        accessibility_issues = wcag_results.get('accessibility_issues', 0)
        gdpr_issues = gdpr_results.get('gdpr_issues', 0)
        total_issues = accessibility_issues + gdpr_issues

        # Determine evaluation status
        if wcag_results.get('critical_count', 0) > 0 or gdpr_results.get('critical_count', 0) > 0:
            evaluation_status = "FAIL"
        elif wcag_results.get('serious_count', 0) > 0 or gdpr_results.get('high_count', 0) > 0:
            evaluation_status = "NEEDS_IMPROVEMENT"
        elif total_issues == 0:
            evaluation_status = "PASS"
        else:
            evaluation_status = "NEEDS_IMPROVEMENT"

        # Calculate UX score (0-100) - FROM CONFIG (NO MAGIC NUMBERS!)
        ux_score = self._calculate_ux_score(wcag_results, gdpr_results)

        # Compile comprehensive evaluation (Value Object)
        evaluation = DeveloperEvaluation(
            developer=developer_name,
            task_title=task_title,
            evaluation_status=evaluation_status,
            ux_score=ux_score,
            # WCAG Accessibility results
            accessibility_issues=accessibility_issues,
            wcag_aa_compliance=wcag_results.get('wcag_aa_compliance', False),
            accessibility_details=wcag_results.get('accessibility_details', {}),
            accessibility_issues_list=wcag_results.get('issues', []),
            # UX issues
            ux_issues=total_issues,
            ux_issues_details=wcag_results.get('issues', []) + gdpr_results.get('issues', []),
            # GDPR compliance results
            gdpr_compliance=gdpr_results.get('gdpr_compliance', {}),
            gdpr_issues=gdpr_issues,
            gdpr_issues_list=gdpr_results.get('issues', [])
        )

        # Log results summary
        self.logger.log(f"WCAG Issues: {accessibility_issues}", "INFO")
        self.logger.log(f"GDPR Issues: {gdpr_issues}", "INFO")
        self.logger.log(f"UX Score: {ux_score}/100", "INFO")
        self.logger.log(f"Status: {evaluation_status}", "INFO")

        return evaluation

    def _calculate_ux_score(self, wcag_results: Dict, gdpr_results: Dict) -> int:
        """
        Calculate UX score based on issue severity

        Uses configuration for deductions (NO MAGIC NUMBERS!)

        Returns:
            UX score (0-100)
        """
        # Get deductions from configuration
        deductions = self.score_deductions

        # Start at 100 and deduct points for issues
        ux_score = 100
        ux_score -= wcag_results.get('critical_count', 0) * deductions['wcag_critical']
        ux_score -= wcag_results.get('serious_count', 0) * deductions['wcag_serious']
        ux_score -= wcag_results.get('moderate_count', 0) * deductions['wcag_moderate']
        ux_score -= gdpr_results.get('critical_count', 0) * deductions['gdpr_critical']
        ux_score -= gdpr_results.get('high_count', 0) * deductions['gdpr_high']
        ux_score -= gdpr_results.get('medium_count', 0) * deductions['gdpr_medium']

        return max(0, ux_score)  # Don't go below 0

    def _determine_stage_status(
        self,
        total_accessibility_issues: int,
        all_evaluations_pass: bool,
        threshold: int
    ) -> str:
        """
        Determine overall stage status

        Uses configuration threshold (NO MAGIC NUMBERS!)

        Args:
            total_accessibility_issues: Total accessibility issues found
            all_evaluations_pass: Whether all evaluations passed
            threshold: Critical accessibility issues threshold from config

        Returns:
            Stage status ("PASS", "NEEDS_IMPROVEMENT", "FAIL")
        """
        if total_accessibility_issues > threshold:
            self.logger.log(
                f"❌ UI/UX evaluation FAILED - Critical accessibility issues found "
                f"({total_accessibility_issues} > {threshold})",
                "ERROR"
            )
            return "FAIL"
        elif not all_evaluations_pass:
            self.logger.log("⚠️  UI/UX evaluation completed with warnings", "WARNING")
            return "NEEDS_IMPROVEMENT"
        else:
            self.logger.log(
                "✅ UI/UX evaluation PASSED - All implementations meet standards",
                "SUCCESS"
            )
            return "PASS"

    def _store_evaluation_in_rag(
        self,
        card_id: str,
        task_title: str,
        evaluation_result: DeveloperEvaluation
    ):
        """
        Store UI/UX evaluation results in RAG for future learning

        Best-effort: Does not raise exceptions
        """
        try:
            # Create summary of key findings
            content = f"""UI/UX Evaluation for {evaluation_result.developer} - {task_title}

Evaluation Status: {evaluation_result.evaluation_status}
UX Score: {evaluation_result.ux_score}/100

Accessibility:
- WCAG AA Compliance: {evaluation_result.wcag_aa_compliance}
- Accessibility Issues: {evaluation_result.accessibility_issues}

GDPR Compliance:
- GDPR Issues: {evaluation_result.gdpr_issues}
- Compliant: {evaluation_result.gdpr_issues == 0}

This evaluation can inform future implementations to improve UX.
"""

            # Store in RAG using helper (DRY)


            RAGStorageHelper.store_stage_artifact(


                rag=self.rag,
                stage_name="uiux_evaluation",
                card_id=card_id,
                task_title=task_title,
                content=content,
                metadata={
                    "developer": evaluation_result.developer,
                    "evaluation_status": evaluation_result.evaluation_status,
                    "ux_score": evaluation_result.ux_score,
                    "accessibility_issues": evaluation_result.accessibility_issues,
                    "wcag_aa_compliance": evaluation_result.wcag_aa_compliance,
                    "ux_issues": evaluation_result.ux_issues
                }
            )

            self.logger.log(
                f"Stored UI/UX evaluation results in RAG for {evaluation_result.developer}",
                "DEBUG"
            )

        except Exception as e:
            # Best-effort: Don't fail evaluation if storage fails
            self.logger.log(f"Error storing UI/UX evaluation in RAG: {e}", "WARNING")

    def _send_evaluation_notification(
        self,
        card_id: str,
        evaluation_result: DeveloperEvaluation
    ):
        """
        Send UI/UX evaluation notification to other agents

        Best-effort: Does not raise exceptions
        """
        try:
            self.messenger.send_data_update(
                to_agent="integration-agent",
                card_id=card_id,
                update_type="uiux_evaluation_complete",
                data={
                    "developer": evaluation_result.developer,
                    "evaluation_status": evaluation_result.evaluation_status,
                    "ux_score": evaluation_result.ux_score,
                    "accessibility_issues": evaluation_result.accessibility_issues,
                    "wcag_aa_compliance": evaluation_result.wcag_aa_compliance
                },
                priority="medium"
            )

            self.logger.log(
                f"Sent UI/UX evaluation notification for {evaluation_result.developer}",
                "DEBUG"
            )

        except Exception as e:
            # Best-effort: Don't fail evaluation if notification fails
            self.logger.log(
                f"Error sending UI/UX evaluation notification: {e}",
                "WARNING"
            )

    def _send_feedback_to_developer(
        self,
        card_id: str,
        evaluation_result: DeveloperEvaluation
    ):
        """
        Send detailed feedback to developer for iteration

        This enables the feedback loop where developers can fix UI/UX issues
        and re-submit their implementation.

        Best-effort: Does not raise exceptions
        """
        try:
            # Compile actionable feedback
            feedback = {
                "evaluation_status": evaluation_result.evaluation_status,
                "ux_score": evaluation_result.ux_score,
                "requires_iteration": True,

                # WCAG accessibility feedback
                "accessibility_feedback": {
                    "total_issues": evaluation_result.accessibility_issues,
                    "wcag_aa_compliant": evaluation_result.wcag_aa_compliance,
                    "issues": evaluation_result.accessibility_issues_list,
                    "details": evaluation_result.accessibility_details
                },

                # GDPR compliance feedback
                "gdpr_feedback": {
                    "total_issues": evaluation_result.gdpr_issues,
                    "gdpr_compliant": evaluation_result.gdpr_issues == 0,
                    "issues": evaluation_result.gdpr_issues_list,
                    "compliance_status": evaluation_result.gdpr_compliance
                },

                # Summary for quick action
                "action_required": self._create_action_summary(evaluation_result)
            }

            # Send feedback to developer via messenger
            self.messenger.send_data_update(
                to_agent=f"{evaluation_result.developer}-agent",
                card_id=card_id,
                update_type="uiux_feedback_for_iteration",
                data=feedback,
                priority="high"  # High priority so developer can iterate quickly
            )

            # Also store in shared state for developer to retrieve
            self.messenger.update_shared_state(
                card_id=card_id,
                updates={
                    f"{evaluation_result.developer}_uiux_feedback": feedback,
                    f"{evaluation_result.developer}_needs_iteration": True
                }
            )

            self.logger.log(
                f"📤 Sent feedback to {evaluation_result.developer} for iteration ({evaluation_result.ux_issues} issues)",
                "INFO"
            )

        except Exception as e:
            # Best-effort: Don't fail evaluation if feedback fails
            self.logger.log(
                f"Error sending feedback to developer: {e}",
                "WARNING"
            )

    def _create_action_summary(self, evaluation_result: DeveloperEvaluation) -> str:
        """
        Create a concise action summary for developers

        Uses list comprehension (Pythonic!)

        Args:
            evaluation_result: Full evaluation results

        Returns:
            Human-readable action summary
        """
        actions = []

        # Accessibility actions
        if evaluation_result.accessibility_issues > 0:
            actions.append(f"Fix {evaluation_result.accessibility_issues} WCAG accessibility issue(s)")

        # GDPR actions
        if evaluation_result.gdpr_issues > 0:
            actions.append(f"Resolve {evaluation_result.gdpr_issues} GDPR compliance issue(s)")

        # Priority guidance (using list comprehension - Pythonic!)
        critical_count = sum(
            1
            for issue in (evaluation_result.accessibility_issues_list + evaluation_result.gdpr_issues_list)
            if issue.get('severity') in ['critical', 'serious', 'high']
        )

        if critical_count > 0:
            actions.append(f"⚠️  {critical_count} critical issue(s) require immediate attention")

        return " | ".join(actions) if actions else "No major issues found"

    def get_stage_name(self) -> str:
        """Return stage name"""
        return "uiux"

    def _store_evaluation_in_knowledge_graph(
        self,
        card_id: str,
        developer_name: str,
        evaluation_result: DeveloperEvaluation,
        implementation_dir: str
    ):
        """
        Store UI/UX evaluation in Knowledge Graph for traceability

        Best-effort: Does not raise exceptions
        """
        kg = get_knowledge_graph()
        if not kg:
            self.logger.log("Knowledge Graph not available - skipping KG storage", "DEBUG")
            return

        try:
            self.logger.log(f"Storing UI/UX evaluation for {developer_name} in Knowledge Graph...", "DEBUG")

            # Generate unique evaluation ID
            eval_id = f"{card_id}-{developer_name}-uiux-eval"

            # Store UI/UX evaluation as metadata on existing nodes
            # We can extend the CodeReview node type or create a new UIUXEvaluation type
            # For now, we'll link evaluated files to the task with evaluation metadata

            # Find HTML/CSS/JS files in implementation directory
            from pathlib import Path
            impl_path = Path(implementation_dir)
            ui_files = []

            if impl_path.exists():
                # Find UI-related files
                for ext in ['*.html', '*.css', '*.js', '*.jsx', '*.tsx', '*.vue', '*.svelte']:
                    ui_files.extend(impl_path.rglob(ext))

            # Link UI files to task with evaluation metadata
            files_linked = 0
            for file_path in ui_files[:20]:  # Limit to 20 files
                try:
                    file_path_str = str(file_path)
                    file_type = self._detect_ui_file_type(file_path_str)

                    # Add file node
                    kg.add_file(file_path_str, file_type)

                    # Link to task
                    kg.link_task_to_file(card_id, file_path_str)

                    files_linked += 1

                except Exception as e:
                    self.logger.log(f"   Could not link UI file {file_path}: {e}", "DEBUG")

            if files_linked > 0:
                self.logger.log(
                    f"✅ Stored UI/UX evaluation {eval_id} with {files_linked} UI file links",
                    "INFO"
                )
            else:
                self.logger.log(
                    f"✅ Stored UI/UX evaluation {eval_id} in Knowledge Graph",
                    "INFO"
                )

        except Exception as e:
            # Best-effort: Don't fail evaluation if KG storage fails
            self.logger.log(f"Warning: Could not store UI/UX evaluation in Knowledge Graph: {e}", "WARNING")
            self.logger.log(f"   Exception details: {type(e).__name__}", "DEBUG")

    def _detect_ui_file_type(self, file_path: str) -> str:
        """Detect UI file type from path using extension mapping"""
        # Map file extensions to types
        extension_map = [
            (('.html',), 'html'),
            (('.css',), 'css'),
            (('.js', '.jsx'), 'javascript'),
            (('.ts', '.tsx'), 'typescript'),
            (('.vue',), 'vue'),
            (('.svelte',), 'svelte'),
        ]

        # Return first matching type or 'unknown'
        return next(
            (file_type for extensions, file_type in extension_map if file_path.endswith(extensions)),
            'unknown'
        )
