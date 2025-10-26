#!/usr/bin/env python3
"""
Project Review Stage - Architecture & Sprint Plan Validation

Responsibilities:
1. Review architecture design decisions
2. Validate sprint planning and capacity
3. Check for technical debt and anti-patterns
4. Provide actionable feedback to Architecture and Sprint Planning stages
5. Approve or reject project plans with detailed reasoning

Single Responsibility: Quality gate for project planning phases
"""

import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from artemis_stage_interface import PipelineStage, LoggerInterface
from supervised_agent_mixin import SupervisedStageMixin
from llm_client import LLMClient
from pipeline_observer import PipelineObservable, PipelineEvent, EventType
from rag_storage_helper import RAGStorageHelper


class ProjectReviewStage(PipelineStage, SupervisedStageMixin):
    """
    Project Review Stage - Validate architecture and sprint plans

    Pipeline Position: AFTER Sprint Planning and Architecture, BEFORE Development
    Input: Architecture design + Sprint plans
    Output: Approval/Rejection with feedback

    If rejected, sends feedback to Architecture stage for iteration
    """

    def __init__(
        self,
        board,
        messenger,
        rag,
        logger: LoggerInterface,
        llm_client: LLMClient,
        config=None,  # ConfigurationAgent for settings
        observable=None,
        supervisor=None,
        max_review_iterations: int = 3
    ):
        """
        Initialize Project Review Stage

        Args:
            board: KanbanBoard instance
            messenger: AgentMessenger for feedback communication
            rag: RAG agent for learning from reviews
            logger: Logger interface
            llm_client: LLM client for review analysis
            config: ConfigurationAgent for review criteria weights
            observable: Observable for event broadcasting
            supervisor: SupervisorAgent for health monitoring
            max_review_iterations: Max times architecture can be revised
        """
        PipelineStage.__init__(self)
        SupervisedStageMixin.__init__(
            self,
            supervisor=supervisor,
            stage_name="ProjectReviewStage",
            heartbeat_interval=20  # LLM-heavy analysis, longer interval
        )

        self.board = board
        self.messenger = messenger
        self.rag = rag
        self.logger = logger
        self.llm_client = llm_client
        self.config = config
        self.observable = observable

        # Load max iterations from config or use default
        if config:
            self.max_review_iterations = config.get(
                'project_review.max_iterations',
                max_review_iterations
            )
        else:
            self.max_review_iterations = max_review_iterations

        # Load review criteria weights from config with sensible defaults
        if config:
            self.review_weights = {
                'architecture_quality': config.get('project_review.weights.architecture_quality', 0.30),
                'sprint_feasibility': config.get('project_review.weights.sprint_feasibility', 0.25),
                'technical_debt': config.get('project_review.weights.technical_debt', 0.20),
                'scalability': config.get('project_review.weights.scalability', 0.15),
                'maintainability': config.get('project_review.weights.maintainability', 0.10)
            }
            # Load capacity thresholds from config
            self.capacity_high_threshold = config.get('project_review.capacity_high_threshold', 0.95)
            self.capacity_low_threshold = config.get('project_review.capacity_low_threshold', 0.70)
            self.tech_debt_penalty = config.get('project_review.tech_debt_penalty', 0.5)
        else:
            # Sensible defaults if no config
            self.review_weights = {
                'architecture_quality': 0.30,
                'sprint_feasibility': 0.25,
                'technical_debt': 0.20,
                'scalability': 0.15,
                'maintainability': 0.10
            }
            self.capacity_high_threshold = 0.95
            self.capacity_low_threshold = 0.70
            self.tech_debt_penalty = 0.5

    def execute(self, card: Dict, context: Dict) -> Dict:
        """
        Execute Project Review with supervisor monitoring

        Args:
            card: Kanban card with project plan
            context: Shared pipeline context with architecture and sprints

        Returns:
            Dict with review decision and feedback
        """
        metadata = {
            "task_id": card.get('card_id'),
            "stage": "project_review"
        }

        with self.supervised_execution(metadata):
            result = self._do_project_review(card, context)

        return result

    def _do_project_review(self, card: Dict, context: Dict) -> Dict:
        """Internal project review logic"""
        card_id = card.get('card_id')
        task_title = card.get('title', 'Unknown Task')

        self.logger.log(f"🔍 Project Review: {task_title}", "INFO")
        self.update_progress({"step": "starting", "progress_percent": 5})

        # Notify project review started
        if self.observable:
            event = PipelineEvent(
                event_type=EventType.STAGE_STARTED,
                card_id=card_id,
                stage_name="project_review",
                data={"task_title": task_title}
            )
            self.observable.notify(event)

        # Check iteration count
        iteration_count = context.get('review_iteration_count', 0)
        if iteration_count >= self.max_review_iterations:
            self.logger.log(
                f"Max review iterations ({self.max_review_iterations}) reached, forcing approval",
                "WARNING"
            )
            return self._force_approval(card_id, task_title, context)

        # Step 1: Extract architecture and sprint plans
        self.update_progress({"step": "extracting_plans", "progress_percent": 15})
        architecture = context.get('architecture', {})
        sprints = context.get('sprints', [])

        # Step 2: Review architecture quality (if available)
        if not architecture:
            self.logger.log("No architecture found - skipping architecture review (may have been skipped by intelligent routing)", "WARNING")
            self.update_progress({"step": "skipping_architecture", "progress_percent": 30})
            arch_review = {
                "status": "SKIPPED",
                "message": "Architecture stage was skipped",
                "score": 70,  # Neutral score
                "recommendations": ["Consider adding architecture documentation if project grows in complexity"]
            }
        else:
            self.update_progress({"step": "reviewing_architecture", "progress_percent": 30})
            arch_review = self._review_architecture(architecture, task_title)

        # Step 3: Review sprint feasibility
        self.update_progress({"step": "reviewing_sprints", "progress_percent": 50})
        # Pass None for architecture if not available - _review_sprints should handle it
        sprint_review = self._review_sprints(sprints, architecture if architecture else None)

        # Step 4: Check for technical debt and anti-patterns
        self.update_progress({"step": "checking_quality", "progress_percent": 65})
        # Pass None for architecture if not available - _check_quality_issues should handle it
        quality_review = self._check_quality_issues(architecture if architecture else None, context)

        # Step 5: Calculate overall score
        self.update_progress({"step": "calculating_score", "progress_percent": 80})
        overall_score, decision = self._calculate_review_score(
            arch_review,
            sprint_review,
            quality_review
        )

        # Step 6: Handle decision
        self.update_progress({"step": "processing_decision", "progress_percent": 90})
        if decision == "APPROVED":
            result = self._handle_approval(card_id, task_title, overall_score, context)
        else:
            result = self._handle_rejection(
                card_id,
                task_title,
                overall_score,
                arch_review,
                sprint_review,
                quality_review,
                context,
                iteration_count
            )

        # Step 7: Store review in RAG
        self.update_progress({"step": "storing_review", "progress_percent": 95})
        self._store_review(card_id, task_title, result)

        self.update_progress({"step": "complete", "progress_percent": 100})
        self.logger.log(f"✅ Review complete: {decision}", "SUCCESS" if decision == "APPROVED" else "WARNING")

        return result

    def _review_architecture(self, architecture: Dict, task_title: str) -> Dict:
        """
        Review architecture design using LLM

        Checks:
        - Appropriate patterns for use case
        - Scalability considerations
        - Security best practices
        - Separation of concerns
        """
        arch_description = json.dumps(architecture, indent=2)

        prompt = f"""Review this architecture design for: {task_title}

Architecture:
{arch_description}

Evaluate the following (rate 1-10 and provide feedback):

1. **Design Patterns**: Are appropriate patterns used?
2. **Scalability**: Can it handle growth?
3. **Security**: Are security best practices followed?
4. **Maintainability**: Is code organization clear?
5. **Performance**: Are there obvious bottlenecks?

Respond in JSON:
{{
    "design_patterns": {{"score": 8, "feedback": "Good use of MVC..."}},
    "scalability": {{"score": 6, "feedback": "Database may bottleneck..."}},
    "security": {{"score": 9, "feedback": "Good auth implementation..."}},
    "maintainability": {{"score": 7, "feedback": "Could improve modularity..."}},
    "performance": {{"score": 8, "feedback": "Good caching strategy..."}},
    "overall_recommendation": "APPROVE | REVISE | REJECT",
    "critical_issues": ["Issue 1", "Issue 2"],
    "suggestions": ["Suggestion 1", "Suggestion 2"]
}}
"""

        try:
            from llm_client import LLMMessage

            messages = [
                LLMMessage(role="system", content="You are a senior architect reviewing project designs."),
                LLMMessage(role="user", content=prompt)
            ]

            llm_response = self.llm_client.complete(
                messages=messages,
                response_format={"type": "json_object"}
            )

            review = json.loads(llm_response.content)
            return review

        except Exception as e:
            self.logger.log(f"Error reviewing architecture: {e}", "ERROR")
            return {
                "overall_recommendation": "REVISE",
                "critical_issues": [f"Review error: {e}"],
                "suggestions": ["Manual review required"]
            }

    def _review_sprints(self, sprints: List[Dict], architecture: Dict) -> Dict:
        """
        Review sprint planning feasibility

        Checks:
        - Capacity utilization (not overcommitted)
        - Feature dependencies aligned with architecture
        - Realistic timelines
        - Risk distribution across sprints
        """
        if not sprints:
            return {
                "score": 0,
                "feedback": "No sprints to review",
                "issues": ["No sprint plan provided"]
            }

        total_sprints = len(sprints)
        total_points = sum(s.get('total_story_points', 0) for s in sprints)
        avg_capacity = sum(s.get('capacity_used', 0) for s in sprints) / max(total_sprints, 1)

        issues = []
        score = 10

        # Check for overcommitment using list comprehension
        overcommitted = [
            (sprint.get('sprint_number'), sprint.get('capacity_used', 0))
            for sprint in sprints
            if sprint.get('capacity_used', 0) > self.capacity_high_threshold
        ]
        for sprint_num, capacity in overcommitted:
            issues.append(f"Sprint {sprint_num} is overcommitted ({capacity:.0%})")
            score -= 2

        # Check for underutilization
        if avg_capacity < self.capacity_low_threshold:
            issues.append(f"Average capacity utilization is low ({avg_capacity:.0%})")
            score -= 1

        # Check for unrealistic sprint 1
        if sprints and sprints[0].get('total_story_points', 0) > 25:
            issues.append("Sprint 1 may be too ambitious")
            score -= 1

        feedback = f"Reviewed {total_sprints} sprints with {total_points} total story points. "
        feedback += f"Average capacity: {avg_capacity:.0%}. "

        if issues:
            feedback += f"Found {len(issues)} potential issues."
        else:
            feedback += "Sprint plan looks feasible."

        return {
            "score": max(0, score),
            "feedback": feedback,
            "issues": issues,
            "total_sprints": total_sprints,
            "total_story_points": total_points
        }

    def _check_quality_issues(self, architecture: Dict, context: Dict) -> Dict:
        """
        Check for technical debt, anti-patterns, and code smells

        Checks:
        - Hardcoded configuration
        - Missing error handling
        - No logging/monitoring
        - Missing tests
        - Security vulnerabilities
        """
        issues = []
        warnings = []
        score = 10

        # Check architecture for common anti-patterns
        arch_str = json.dumps(architecture).lower()

        # Check for hardcoded values
        if 'hardcoded' in arch_str or 'localhost' in arch_str:
            issues.append("Hardcoded configuration detected")
            score -= 2

        # Check for error handling
        if 'error' not in arch_str and 'exception' not in arch_str:
            warnings.append("No explicit error handling mentioned")
            score -= 1

        # Check for logging
        if 'log' not in arch_str and 'monitor' not in arch_str:
            warnings.append("No logging/monitoring strategy mentioned")
            score -= 1

        # Check for testing
        if 'test' not in arch_str:
            warnings.append("No testing strategy mentioned")
            score -= 2

        # Check for security
        if 'auth' not in arch_str and 'security' not in arch_str:
            warnings.append("No authentication/security mentioned")
            score -= 1

        # Check for database considerations
        if 'database' in arch_str or 'db' in arch_str:
            if 'migration' not in arch_str:
                warnings.append("No database migration strategy")
                score -= self.tech_debt_penalty

        return {
            "score": max(0, score),
            "critical_issues": issues,
            "warnings": warnings,
            "total_issues": len(issues) + len(warnings)
        }

    def _calculate_review_score(
        self,
        arch_review: Dict,
        sprint_review: Dict,
        quality_review: Dict
    ) -> Tuple[float, str]:
        """
        Calculate overall review score and decision

        Returns:
            (score, decision) where decision is "APPROVED" or "REJECTED"
        """
        # Extract scores
        arch_scores = {
            k: v.get('score', 5)
            for k, v in arch_review.items()
            if isinstance(v, dict) and 'score' in v
        }
        avg_arch_score = sum(arch_scores.values()) / max(len(arch_scores), 1) if arch_scores else 5

        sprint_score = sprint_review.get('score', 5)
        quality_score = quality_review.get('score', 5)

        # Weighted overall score
        overall_score = (
            avg_arch_score * self.review_weights['architecture_quality'] +
            sprint_score * self.review_weights['sprint_feasibility'] +
            quality_score * (
                self.review_weights['technical_debt'] +
                self.review_weights['scalability'] +
                self.review_weights['maintainability']
            )
        )

        # Decision thresholds using configuration mapping
        critical_issues = arch_review.get('critical_issues', []) + quality_review.get('critical_issues', [])

        # Define decision rules based on score and critical issues
        if overall_score >= 8.0:
            decision = "APPROVED"
        elif overall_score >= 6.0:
            decision = "REJECTED" if critical_issues else "APPROVED"
        else:
            decision = "REJECTED"

        return overall_score, decision

    def _handle_approval(
        self,
        card_id: str,
        task_title: str,
        score: float,
        context: Dict
    ) -> Dict:
        """Handle project approval"""
        self.logger.log(f"✅ Project APPROVED (score: {score:.1f}/10)", "SUCCESS")

        # Update Kanban board
        self.board.update_card(
            card_id,
            {
                'project_review_status': 'APPROVED',
                'review_score': score,
                'approved_at': datetime.now().isoformat()
            }
        )

        # Notify orchestrator that project is ready for development
        self.messenger.send_data_update(
            to_agent="orchestrator",
            card_id=card_id,
            update_type="project_approved",
            data={
                'status': 'APPROVED',
                'score': score,
                'ready_for_development': True
            },
            priority="high"
        )

        # Notify project review completed with approval
        if self.observable:
            event = PipelineEvent(
                event_type=EventType.STAGE_COMPLETED,
                card_id=card_id,
                stage_name="project_review",
                data={
                    'status': 'APPROVED',
                    'score': score,
                    'ready_for_development': True
                }
            )
            self.observable.notify(event)

        return {
            "stage": "project_review",
            "status": "APPROVED",
            "success": True,
            "score": score,
            "message": "Project approved for development",
            "ready_for_development": True
        }

    def _handle_rejection(
        self,
        card_id: str,
        task_title: str,
        score: float,
        arch_review: Dict,
        sprint_review: Dict,
        quality_review: Dict,
        context: Dict,
        iteration_count: int
    ) -> Dict:
        """Handle project rejection and send feedback to Architecture stage"""
        self.logger.log(f"❌ Project REJECTED (score: {score:.1f}/10)", "WARNING")

        # Compile feedback for Architecture stage
        feedback = self._compile_feedback(arch_review, sprint_review, quality_review)

        # Send feedback to Architecture agent
        self.messenger.send_data_update(
            to_agent="architecture-agent",
            card_id=card_id,
            update_type="review_feedback_for_revision",
            data={
                'status': 'REJECTED',
                'score': score,
                'feedback': feedback,
                'iteration': iteration_count + 1,
                'max_iterations': self.max_review_iterations,
                'requires_revision': True
            },
            priority="high"
        )

        # Update context for next iteration
        context['review_iteration_count'] = iteration_count + 1
        context['review_feedback'] = feedback

        # Update Kanban board
        self.board.update_card(
            card_id,
            {
                'project_review_status': 'REJECTED',
                'review_score': score,
                'review_iteration': iteration_count + 1,
                'feedback': feedback,
                'rejected_at': datetime.now().isoformat()
            }
        )

        # Notify project review rejected with feedback for revision
        if self.observable:
            event = PipelineEvent(
                event_type=EventType.STAGE_COMPLETED,
                card_id=card_id,
                stage_name="project_review",
                data={
                    'status': 'REJECTED',
                    'score': score,
                    'iteration': iteration_count + 1,
                    'requires_revision': True
                }
            )
            self.observable.notify(event)

        return {
            "stage": "project_review",
            "status": "REJECTED",
            "success": True,
            "score": score,
            "message": "Project requires revision",
            "feedback": feedback,
            "iteration": iteration_count + 1,
            "requires_architecture_revision": True
        }

    def _compile_feedback(
        self,
        arch_review: Dict,
        sprint_review: Dict,
        quality_review: Dict
    ) -> Dict:
        """Compile actionable feedback for Architecture stage"""
        feedback = {
            "architecture_issues": [],
            "sprint_issues": [],
            "quality_issues": [],
            "actionable_steps": []
        }

        # Architecture feedback
        if arch_review.get('critical_issues'):
            feedback['architecture_issues'].extend(arch_review['critical_issues'])

        if arch_review.get('suggestions'):
            feedback['actionable_steps'].extend(arch_review['suggestions'])

        # Sprint feedback
        if sprint_review.get('issues'):
            feedback['sprint_issues'].extend(sprint_review['issues'])

        # Quality feedback
        if quality_review.get('critical_issues'):
            feedback['quality_issues'].extend(quality_review['critical_issues'])

        if quality_review.get('warnings'):
            feedback['quality_issues'].extend(quality_review['warnings'])

        # Generate actionable steps summary
        feedback['summary'] = self._generate_feedback_summary(
            len(feedback['architecture_issues']),
            len(feedback['sprint_issues']),
            len(feedback['quality_issues'])
        )

        return feedback

    def _generate_feedback_summary(
        self,
        arch_count: int,
        sprint_count: int,
        quality_count: int
    ) -> str:
        """Generate human-readable feedback summary"""
        parts = []

        if arch_count > 0:
            parts.append(f"{arch_count} architecture issue(s)")
        if sprint_count > 0:
            parts.append(f"{sprint_count} sprint planning issue(s)")
        if quality_count > 0:
            parts.append(f"{quality_count} quality issue(s)")

        if not parts:
            return "Minor improvements needed"

        return f"Address: {', '.join(parts)}"

    def _force_approval(self, card_id: str, task_title: str, context: Dict) -> Dict:
        """Force approval after max iterations"""
        self.logger.log("⚠️  Forcing approval after max review iterations", "WARNING")

        # Update Kanban
        self.board.update_card(
            card_id,
            {
                'project_review_status': 'APPROVED_WITH_WARNINGS',
                'review_score': 6.0,
                'forced_approval': True,
                'approved_at': datetime.now().isoformat()
            }
        )

        return {
            "stage": "project_review",
            "status": "APPROVED",
            "score": 6.0,
            "message": "Forced approval after max iterations",
            "ready_for_development": True,
            "forced": True
        }

    def _store_review(self, card_id: str, task_title: str, result: Dict) -> None:
        """Store review in RAG for learning"""
        content = f"""Project Review: {task_title}

Status: {result.get('status')}
Score: {result.get('score', 0):.1f}/10

"""
        if result.get('feedback'):
            content += f"\nFeedback provided for revision:\n{json.dumps(result['feedback'], indent=2)}"

        # Store in RAG using helper (DRY)


        RAGStorageHelper.store_stage_artifact(


            rag=self.rag,
            stage_name="project_review",
            card_id=card_id,
            task_title=task_title,
            content=content,
            metadata=result
        )

    def get_stage_name(self) -> str:
        return "project_review"
