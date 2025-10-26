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
import tempfile
from typing import Dict, Optional, List, Any
from pathlib import Path

from artemis_stage_interface import PipelineStage, LoggerInterface
from code_review_agent import CodeReviewAgent
from agent_messenger import AgentMessenger
from rag_agent import RAGAgent
from pipeline_observer import PipelineObservable, PipelineEvent, EventType
from supervised_agent_mixin import SupervisedStageMixin
from debug_mixin import DebugMixin
from knowledge_graph_factory import get_knowledge_graph
from rag_storage_helper import RAGStorageHelper
from artemis_exceptions import PipelineStageError, wrap_exception


class CodeReviewStage(PipelineStage, SupervisedStageMixin, DebugMixin):
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
        supervisor: Optional['SupervisorAgent'] = None,
        code_review_dir: Optional[str] = None,
        ai_service: Optional['AIQueryService'] = None
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
            code_review_dir: Directory for code review output
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

        # Initialize DebugMixin
        DebugMixin.__init__(self, component_name="code_review")

        self.messenger = messenger
        self.rag = rag
        self.logger = logger
        self.ai_service = ai_service  # Store AI Query Service for potential future use
        self.llm_provider = llm_provider or os.getenv("ARTEMIS_LLM_PROVIDER", "openai")
        self.llm_model = llm_model or os.getenv("ARTEMIS_LLM_MODEL")
        self.observable = observable

        # Set code review directory from config or use default
        if code_review_dir is None:
            code_review_dir = os.getenv("ARTEMIS_CODE_REVIEW_DIR", "../../.artemis_data/code_reviews")
            if not os.path.isabs(code_review_dir):
                script_dir = os.path.dirname(os.path.abspath(__file__))
                code_review_dir = os.path.join(script_dir, code_review_dir)
        self.code_review_dir = code_review_dir

    @wrap_exception(PipelineStageError, "Code review stage execution failed")
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

        # DEBUG: Log stage entry
        self.debug_log("Starting code review", card_id=card_id, task_title=task_title)

        # Update progress: starting
        self.update_progress({"step": "starting", "progress_percent": 5})

        # Get developer results from context
        developers = context.get('developers', [])
        if not developers:
            self.logger.log("No developer implementations found to review", "WARNING")
            self.debug_log("No developers to review", developer_count=0)
            return {
                "stage": "code_review",
                "status": "SKIPPED",
                "reason": "No implementations to review"
            }

        self.logger.log(f"Reviewing {len(developers)} developer implementation(s)", "INFO")
        self.debug_log("Developers found for review", developer_count=len(developers),
                      developer_names=[d if isinstance(d, str) else d.get('name', 'unknown') for d in developers])

        # Update progress: initializing reviews
        self.update_progress({"step": "initializing_reviews", "progress_percent": 10})

        # Review each developer's implementation
        review_results, all_reviews_pass, total_critical_issues, total_high_issues = self._review_all_developers(
            developers, card_id, task_title, task_description
        )

        # Update progress: summarizing results
        self.update_progress({"step": "summarizing_results", "progress_percent": 85})

        # DEBUG: Dump review results
        self.debug_dump_if_enabled('dump_review_results', "Code Review Results", {
            "review_count": len(review_results),
            "critical_issues": total_critical_issues,
            "high_issues": total_high_issues,
            "all_pass": all_reviews_pass,
            "reviews": review_results
        })

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

        # Generate refactoring suggestions if review failed or needs improvement
        refactoring_suggestions = None
        if stage_status in ["FAIL", "NEEDS_IMPROVEMENT"]:
            refactoring_suggestions = self._generate_refactoring_suggestions(
                review_results, card_id, task_title
            )

        # Update progress: complete
        self.update_progress({"step": "complete", "progress_percent": 100})

        result = {
            "stage": "code_review",
            "status": stage_status,
            "reviews": review_results,
            "total_critical_issues": total_critical_issues,
            "total_high_issues": total_high_issues,
            "all_reviews_pass": all_reviews_pass,
            "implementations_reviewed": len(review_results)
        }

        # Add refactoring suggestions if available
        if refactoring_suggestions:
            result["refactoring_suggestions"] = refactoring_suggestions

        return result

    def get_stage_name(self) -> str:
        """Return stage name"""
        return "code_review"

    def _review_all_developers(self, developers, card_id, task_title, task_description):
        """
        Review all developer implementations

        Returns:
            Tuple of (review_results, all_reviews_pass, total_critical_issues, total_high_issues)
        """
        review_results = []
        all_reviews_pass = True
        total_critical_issues = 0
        total_high_issues = 0

        for i, dev_result in enumerate(developers):
            result = self._review_single_developer(
                i, dev_result, developers, card_id, task_title, task_description
            )

            review_results.append(result['review_result'])
            total_critical_issues += result['critical_issues']
            total_high_issues += result['high_issues']

            if result['review_status'] == "FAIL":
                all_reviews_pass = False

        return review_results, all_reviews_pass, total_critical_issues, total_high_issues

    def _review_single_developer(self, index, dev_result, all_developers, card_id, task_title, task_description):
        """Review a single developer's implementation"""
        developer_name = dev_result.get('developer', 'unknown')
        implementation_dir = dev_result.get('output_dir', f'{tempfile.gettempdir()}/{developer_name}/')

        # Update progress for each developer review (10% to 80% dynamically)
        progress = 10 + ((index + 1) / len(all_developers)) * 70
        self.update_progress({
            "step": f"reviewing_{developer_name}",
            "progress_percent": int(progress),
            "current_developer": developer_name,
            "total_developers": len(all_developers)
        })

        self.logger.log(f"\n{'='*60}", "INFO")
        self.logger.log(f"🔍 Reviewing {developer_name} implementation", "INFO")
        self.logger.log(f"{'='*60}", "INFO")

        # Notify code review started
        self._notify_review_started(card_id, developer_name, implementation_dir)

        # Create and run code review agent
        review_agent = CodeReviewAgent(
            developer_name=developer_name,
            llm_provider=self.llm_provider,
            llm_model=self.llm_model,
            logger=self.logger,
            rag_agent=self.rag
        )

        review_result = review_agent.review_implementation(
            implementation_dir=implementation_dir,
            task_title=task_title,
            task_description=task_description,
            output_dir=self.code_review_dir
        )

        # Extract review metrics
        review_status = review_result.get('review_status', 'FAIL')
        critical_issues = review_result.get('critical_issues', 0)
        high_issues = review_result.get('high_issues', 0)
        overall_score = review_result.get('overall_score', 0)

        # Log review summary
        self._log_review_summary(review_status, overall_score, critical_issues, high_issues)

        # Handle review outcome notifications
        self._handle_review_outcome(
            review_status, developer_name, card_id, overall_score, critical_issues, high_issues
        )

        # Store review results
        self._store_review_in_rag(card_id, task_title, developer_name, review_result)
        self._store_review_in_knowledge_graph(card_id, developer_name, review_result, implementation_dir)
        self._send_review_notification(card_id, developer_name, review_result)

        return {
            'review_result': review_result,
            'review_status': review_status,
            'critical_issues': critical_issues,
            'high_issues': high_issues
        }

    def _notify_review_started(self, card_id, developer_name, implementation_dir):
        """Send notification that code review has started"""
        if self.observable:
            event = PipelineEvent(
                event_type=EventType.CODE_REVIEW_STARTED,
                card_id=card_id,
                developer_name=developer_name,
                data={"implementation_dir": implementation_dir}
            )
            self.observable.notify(event)

    def _log_review_summary(self, review_status, overall_score, critical_issues, high_issues):
        """Log review summary metrics"""
        self.logger.log(f"Review Status: {review_status}", "INFO")
        self.logger.log(f"Overall Score: {overall_score}/100", "INFO")
        self.logger.log(f"Critical Issues: {critical_issues}", "INFO")
        self.logger.log(f"High Issues: {high_issues}", "INFO")

    def _handle_review_outcome(self, review_status, developer_name, card_id, overall_score, critical_issues, high_issues):
        """Handle review outcome with appropriate notifications"""
        if review_status == "FAIL":
            self.logger.log(f"❌ {developer_name} implementation FAILED code review", "ERROR")
            self._notify_review_failed(card_id, developer_name, overall_score, critical_issues)
        elif review_status == "NEEDS_IMPROVEMENT":
            self.logger.log(f"⚠️  {developer_name} implementation needs improvement", "WARNING")
        else:
            self.logger.log(f"✅ {developer_name} implementation PASSED code review", "SUCCESS")
            self._notify_review_completed(card_id, developer_name, overall_score, critical_issues, high_issues, review_status)

    def _notify_review_failed(self, card_id, developer_name, overall_score, critical_issues):
        """Send notification that code review failed"""
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

    def _notify_review_completed(self, card_id, developer_name, overall_score, critical_issues, high_issues, review_status):
        """Send notification that code review completed successfully"""
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

            # Store in RAG using helper (DRY)


            RAGStorageHelper.store_stage_artifact(


                rag=self.rag,
                stage_name="code_review",
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

    def _store_review_in_knowledge_graph(
        self,
        card_id: str,
        developer_name: str,
        review_result: Dict,
        implementation_dir: str
    ):
        """Store code review results in Knowledge Graph for traceability"""
        kg = get_knowledge_graph()
        if not kg:
            self.logger.log("Knowledge Graph not available - skipping KG storage", "DEBUG")
            return

        try:
            self.logger.log(f"Storing code review for {developer_name} in Knowledge Graph...", "DEBUG")

            # Generate unique review ID
            review_id = f"{card_id}-{developer_name}-review"

            # Add code review node
            kg.add_code_review(
                review_id=review_id,
                card_id=card_id,
                status=review_result.get('review_status', 'UNKNOWN'),
                score=review_result.get('overall_score', 0),
                critical_issues=review_result.get('critical_issues', 0),
                high_issues=review_result.get('high_issues', 0)
            )

            # Link modified files to task (if we have file list)
            modified_files = review_result.get('modified_files', [])
            if modified_files:
                for file_path in modified_files[:10]:  # Limit to 10 files
                    try:
                        # Add file if not exists
                        file_path_str = str(file_path)
                        kg.add_file(file_path_str, self._detect_file_type(file_path_str))

                        # Link task to file (this file was modified for this task)
                        kg.link_task_to_file(card_id, file_path_str)

                    except Exception as e:
                        self.logger.log(f"   Could not link file {file_path}: {e}", "DEBUG")

                self.logger.log(f"✅ Stored code review {review_id} with {len(modified_files)} file links", "INFO")
            else:
                self.logger.log(f"✅ Stored code review {review_id} in Knowledge Graph", "INFO")

        except Exception as e:
            self.logger.log(f"Warning: Could not store review in Knowledge Graph: {e}", "WARNING")
            self.logger.log(f"   Exception details: {type(e).__name__}", "DEBUG")

    def _detect_file_type(self, file_path: str) -> str:
        """Detect file type from path"""
        if file_path.endswith('.py'):
            return 'python'
        elif file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
            return 'javascript'
        elif file_path.endswith('.java'):
            return 'java'
        elif file_path.endswith('.go'):
            return 'go'
        elif file_path.endswith('.rs'):
            return 'rust'
        elif file_path.endswith(('.c', '.cpp', '.h', '.hpp')):
            return 'c++'
        elif file_path.endswith('.md'):
            return 'markdown'
        elif file_path.endswith(('.yaml', '.yml')):
            return 'yaml'
        elif file_path.endswith('.json'):
            return 'json'
        else:
            return 'unknown'

    def _generate_refactoring_suggestions(
        self,
        review_results: List[Dict],
        card_id: str,
        task_title: str
    ) -> str:
        """
        Generate refactoring suggestions based on code review failures

        Creates detailed, actionable refactoring instructions for developers
        to address code quality issues found during review.

        Args:
            review_results: List of review results for all developers
            card_id: Card ID for context
            task_title: Task title

        Returns:
            Formatted refactoring suggestions string
        """
        self.logger.log("🔧 Generating refactoring suggestions based on code review failures...", "INFO")

        suggestions = []
        suggestions.append("# REFACTORING INSTRUCTIONS FOR CODE REVIEW FAILURES\n")
        suggestions.append(f"**Task**: {task_title}")
        suggestions.append(f"**Card ID**: {card_id}\n")
        suggestions.append("The following refactorings are required to pass code review:\n")

        for result in review_results:
            developer_name = result.get('review_result', {}).get('developer_name', 'unknown')
            review_status = result.get('review_status', 'UNKNOWN')
            critical_issues = result.get('critical_issues', 0)
            high_issues = result.get('high_issues', 0)

            if review_status in ["FAIL", "NEEDS_IMPROVEMENT"]:
                suggestions.append(f"\n## {developer_name} - Refactoring Required")
                suggestions.append(f"Status: {review_status}")
                suggestions.append(f"Critical Issues: {critical_issues}")
                suggestions.append(f"High Issues: {high_issues}\n")

                # Add specific refactoring recommendations
                suggestions.append("### Required Refactorings:")
                suggestions.append("1. **Extract Long Methods**: Break down methods longer than 50 lines")
                suggestions.append("2. **Reduce Complexity**: Simplify nested if/else chains using guard clauses")
                suggestions.append("3. **Remove Code Duplication**: Apply DRY principle")
                suggestions.append("4. **Improve Naming**: Use descriptive, meaningful names for variables and methods")
                suggestions.append("5. **Add Error Handling**: Properly handle all error cases")
                suggestions.append("6. **Security Fixes**: Address all OWASP Top 10 vulnerabilities")
                suggestions.append("7. **Apply Design Patterns**: Use Strategy, Builder, or Null Object patterns where appropriate")
                suggestions.append("8. **Type Safety**: Add type hints and perform proper type checking")
                suggestions.append("9. **Documentation**: Add comprehensive docstrings and comments")
                suggestions.append("10. **SOLID Principles**: Ensure Single Responsibility, Open/Closed, etc.\n")

        # Add general best practices
        suggestions.append("\n## General Best Practices")
        suggestions.append("- Follow language-specific idioms and conventions")
        suggestions.append("- Keep methods focused on a single responsibility")
        suggestions.append("- Prefer composition over inheritance")
        suggestions.append("- Use dependency injection for better testability")
        suggestions.append("- Write self-documenting code")
        suggestions.append("- Add unit tests for all refactored code")
        suggestions.append("- Ensure all tests pass after refactoring\n")

        # Query RAG for additional refactoring patterns
        if self.rag:
            try:
                rag_suggestions = self.rag.query_similar(
                    query_text="refactoring patterns code quality best practices",
                    artifact_type="architecture_decision",
                    top_k=3
                )

                if rag_suggestions:
                    suggestions.append("\n## Additional Refactoring Patterns from Knowledge Base")
                    for i, result in enumerate(rag_suggestions, 1):
                        content = result.get('content', '')
                        metadata = result.get('metadata', {})
                        refactoring_type = metadata.get('refactoring_type', 'Unknown')
                        suggestions.append(f"\n### Pattern {i}: {refactoring_type}")
                        suggestions.append(content[:500] + "..." if len(content) > 500 else content)

            except Exception as e:
                self.logger.log(f"Could not query RAG for additional patterns: {e}", "WARNING")

        suggestion_text = "\n".join(suggestions)
        self.logger.log(f"✅ Generated {len(suggestions)} lines of refactoring suggestions", "INFO")

        return suggestion_text
