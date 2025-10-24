#!/usr/bin/env python3
"""
Code Review Stage - Security, Quality, GDPR, and Accessibility Review

Reviews developer implementations for:
- Security vulnerabilities (OWASP Top 10)
- Code quality and anti-patterns
- GDPR compliance
- Accessibility (WCAG 2.1 AA)
"""

import os
import json
from typing import Dict, Optional
from pathlib import Path

from artemis_stage_interface import PipelineStage, LoggerInterface
from code_review_agent import CodeReviewAgent
from agent_messenger import AgentMessenger
from rag_agent import RAGAgent
from pipeline_observer import PipelineObservable, PipelineEvent, EventType
from supervised_agent_mixin import SupervisedStageMixin


class CodeReviewStage(PipelineStage, SupervisedStageMixin):
    """
    Single Responsibility: Review code for security, quality, GDPR, and accessibility

    This stage reviews all developer implementations and provides comprehensive
    reports on security vulnerabilities, code quality issues, GDPR compliance,
    and accessibility standards.

    Integrates with supervisor for:
    - LLM cost tracking for code review
    - Critical security finding alerts
    - Code review failure recovery
    - Automatic heartbeat and health monitoring
    """

    def __init__(
        self,
        messenger: AgentMessenger,
        rag: RAGAgent,
        logger: LoggerInterface,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        observable: Optional[PipelineObservable] = None,
        supervisor: Optional['SupervisorAgent'] = None
    ):
        """
        Initialize Code Review Stage

        Args:
            messenger: Agent messenger for inter-agent communication
            rag: RAG agent for storing review results
            logger: Logger interface
            llm_provider: LLM provider (openai/anthropic)
            llm_model: Specific model to use
            observable: Optional PipelineObservable for event broadcasting
            supervisor: Optional SupervisorAgent for monitoring
        """
        # Initialize PipelineStage
        PipelineStage.__init__(self)

        # Initialize SupervisedStageMixin for health monitoring
        # Code review typically takes longer, so use 20 second heartbeat
        SupervisedStageMixin.__init__(
            self,
            supervisor=supervisor,
            stage_name="CodeReviewStage",
            heartbeat_interval=20  # Longer interval for LLM-heavy stage
        )

        self.messenger = messenger
        self.rag = rag
        self.logger = logger
        self.llm_provider = llm_provider or os.getenv("ARTEMIS_LLM_PROVIDER", "openai")
        self.llm_model = llm_model or os.getenv("ARTEMIS_LLM_MODEL")
        self.observable = observable

    def execute(self, card: Dict, context: Dict) -> Dict:
        """Execute code review with supervisor monitoring"""
        metadata = {
            "task_id": card.get('card_id'),
            "stage": "code_review"
        }

        with self.supervised_execution(metadata):
            return self._do_code_review(card, context)

    def _do_code_review(self, card: Dict, context: Dict) -> Dict:
        """
        Internal method - performs code review on all developer implementations

        Reviews each developer's implementation for:
        - OWASP Top 10 security vulnerabilities
        - Code quality and anti-patterns
        - GDPR compliance
        - WCAG 2.1 AA accessibility

        Args:
            card: Kanban card with task details
            context: Context from previous stages (includes developers)

        Returns:
            Dict with review results for all developers
        """
        self.logger.log("Starting Code Review Stage", "STAGE")
        self.logger.log("🔍 Comprehensive Security & Quality Analysis", "INFO")

        card_id = card['card_id']
        task_title = card.get('title', 'Unknown Task')
        task_description = card.get('description', '')

        # Update progress: starting
        self.update_progress({"step": "starting", "progress_percent": 5})

        # Get developer results from context
        developers = context.get('developers', [])
        if not developers:
            self.logger.log("No developer implementations found to review", "WARNING")
            return {
                "stage": "code_review",
                "status": "SKIPPED",
                "reason": "No implementations to review"
            }

        self.logger.log(f"Reviewing {len(developers)} developer implementation(s)", "INFO")

        # Update progress: initializing reviews
        self.update_progress({"step": "initializing_reviews", "progress_percent": 10})

        # Review each developer's implementation
        review_results = []
        all_reviews_pass = True
        total_critical_issues = 0
        total_high_issues = 0

        for i, dev_result in enumerate(developers):
            developer_name = dev_result.get('developer', 'unknown')
            implementation_dir = dev_result.get('output_dir', f'/tmp/{developer_name}/')

            # Update progress for each developer review (10% to 80% dynamically)
            progress = 10 + ((i + 1) / len(developers)) * 70
            self.update_progress({
                "step": f"reviewing_{developer_name}",
                "progress_percent": int(progress),
                "current_developer": developer_name,
                "total_developers": len(developers)
            })

            self.logger.log(f"\n{'='*60}", "INFO")
            self.logger.log(f"🔍 Reviewing {developer_name} implementation", "INFO")
            self.logger.log(f"{'='*60}", "INFO")

            # Notify code review started
            if self.observable:
                event = PipelineEvent(
                    event_type=EventType.CODE_REVIEW_STARTED,
                    card_id=card_id,
                    developer_name=developer_name,
                    data={"implementation_dir": implementation_dir}
                )
                self.observable.notify(event)

            # Create code review agent for this developer
            review_agent = CodeReviewAgent(
                developer_name=developer_name,
                llm_provider=self.llm_provider,
                llm_model=self.llm_model,
                logger=self.logger,
                rag_agent=self.rag  # Pass RAG for prompt management
            )

            # Perform review
            review_result = review_agent.review_implementation(
                implementation_dir=implementation_dir,
                task_title=task_title,
                task_description=task_description,
                output_dir="/tmp/code-reviews/"
            )

            review_results.append(review_result)

            # Check review status
            review_status = review_result.get('review_status', 'FAIL')
            critical_issues = review_result.get('critical_issues', 0)
            high_issues = review_result.get('high_issues', 0)
            overall_score = review_result.get('overall_score', 0)

            total_critical_issues += critical_issues
            total_high_issues += high_issues

            # Log review summary
            self.logger.log(f"Review Status: {review_status}", "INFO")
            self.logger.log(f"Overall Score: {overall_score}/100", "INFO")
            self.logger.log(f"Critical Issues: {critical_issues}", "INFO")
            self.logger.log(f"High Issues: {high_issues}", "INFO")

            # Track if any reviews fail
            if review_status == "FAIL":
                all_reviews_pass = False
                self.logger.log(f"❌ {developer_name} implementation FAILED code review", "ERROR")

                # Notify code review failed
                if self.observable:
                    error = Exception(f"Code review failed with {critical_issues} critical issues")
                    event = PipelineEvent(
                        event_type=EventType.CODE_REVIEW_FAILED,
                        card_id=card_id,
                        developer_name=developer_name,
                        error=error,
                        data={"score": overall_score, "critical_issues": critical_issues}
                    )
                    self.observable.notify(event)

            elif review_status == "NEEDS_IMPROVEMENT":
                self.logger.log(f"⚠️  {developer_name} implementation needs improvement", "WARNING")
            else:
                self.logger.log(f"✅ {developer_name} implementation PASSED code review", "SUCCESS")

                # Notify code review completed
                if self.observable:
                    event = PipelineEvent(
                        event_type=EventType.CODE_REVIEW_COMPLETED,
                        card_id=card_id,
                        developer_name=developer_name,
                        data={
                            "score": overall_score,
                            "critical_issues": critical_issues,
                            "high_issues": high_issues,
                            "status": review_status
                        }
                    )
                    self.observable.notify(event)

            # Store review in RAG for learning
            self._store_review_in_rag(card_id, task_title, developer_name, review_result)

            # Send review notification to other agents
            self._send_review_notification(card_id, developer_name, review_result)

        # Update progress: summarizing results
        self.update_progress({"step": "summarizing_results", "progress_percent": 85})

        # Overall summary
        self.logger.log(f"\n{'='*60}", "INFO")
        self.logger.log("📊 Code Review Summary", "INFO")
        self.logger.log(f"{'='*60}", "INFO")
        self.logger.log(f"Implementations Reviewed: {len(review_results)}", "INFO")
        self.logger.log(f"Total Critical Issues: {total_critical_issues}", "INFO")
        self.logger.log(f"Total High Issues: {total_high_issues}", "INFO")

        # Update progress: determining status
        self.update_progress({"step": "determining_status", "progress_percent": 95})

        # Determine overall stage status
        if total_critical_issues > 0:
            stage_status = "FAIL"
            self.logger.log("❌ Code review FAILED - Critical security/compliance issues found", "ERROR")
        elif not all_reviews_pass:
            stage_status = "NEEDS_IMPROVEMENT"
            self.logger.log("⚠️  Code review completed with warnings", "WARNING")
        else:
            stage_status = "PASS"
            self.logger.log("✅ Code review PASSED - All implementations meet standards", "SUCCESS")

        # Update progress: complete
        self.update_progress({"step": "complete", "progress_percent": 100})

        return {
            "stage": "code_review",
            "status": stage_status,
            "reviews": review_results,
            "total_critical_issues": total_critical_issues,
            "total_high_issues": total_high_issues,
            "all_reviews_pass": all_reviews_pass,
            "implementations_reviewed": len(review_results)
        }

    def get_stage_name(self) -> str:
        """Return stage name"""
        return "code_review"

    def _store_review_in_rag(
        self,
        card_id: str,
        task_title: str,
        developer_name: str,
        review_result: Dict
    ):
        """Store code review results in RAG for future learning"""
        try:
            # Create summary of key findings
            content = f"""Code Review for {developer_name} - {task_title}

Review Status: {review_result.get('review_status', 'UNKNOWN')}
Overall Score: {review_result.get('overall_score', 0)}/100

Issues Found:
- Critical: {review_result.get('critical_issues', 0)}
- High: {review_result.get('high_issues', 0)}
- Total: {review_result.get('total_issues', 0)}

This review can inform future implementations to avoid similar issues.
"""

            self.rag.store_artifact(
                artifact_type="code_review",
                card_id=card_id,
                task_title=task_title,
                content=content,
                metadata={
                    "developer": developer_name,
                    "review_status": review_result.get('review_status', 'UNKNOWN'),
                    "overall_score": review_result.get('overall_score', 0),
                    "critical_issues": review_result.get('critical_issues', 0),
                    "high_issues": review_result.get('high_issues', 0),
                    "total_issues": review_result.get('total_issues', 0),
                    "report_file": review_result.get('report_file', '')
                }
            )

            self.logger.log(f"Stored review results in RAG for {developer_name}", "DEBUG")

        except Exception as e:
            self.logger.log(f"Warning: Could not store review in RAG: {e}", "WARNING")

    def _send_review_notification(
        self,
        card_id: str,
        developer_name: str,
        review_result: Dict
    ):
        """Send code review notification to other agents"""
        try:
            self.messenger.send_notification(
                to_agent="all",
                card_id=card_id,
                notification_type="code_review_completed",
                data={
                    "developer": developer_name,
                    "review_status": review_result.get('review_status', 'UNKNOWN'),
                    "overall_score": review_result.get('overall_score', 0),
                    "critical_issues": review_result.get('critical_issues', 0),
                    "high_issues": review_result.get('high_issues', 0),
                    "report_file": review_result.get('report_file', '')
                }
            )

            # Update shared state
            self.messenger.update_shared_state(
                card_id=card_id,
                updates={
                    f"code_review_{developer_name}_status": review_result.get('review_status', 'UNKNOWN'),
                    f"code_review_{developer_name}_score": review_result.get('overall_score', 0),
                    "current_stage": "code_review_complete"
                }
            )

        except Exception as e:
            self.logger.log(f"Warning: Could not send review notification: {e}", "WARNING")
