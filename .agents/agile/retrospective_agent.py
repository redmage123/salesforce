#!/usr/bin/env python3
"""
Retrospective Agent - Sprint Learning and Continuous Improvement

Responsibilities:
1. Analyze completed sprints for successes and failures
2. Extract learnings and patterns
3. Generate actionable improvements for next sprint
4. Store learnings in RAG for team knowledge
5. Communicate retrospective findings to orchestrator and team

Single Responsibility: Facilitate continuous improvement through sprint retrospectives
"""

import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

from artemis_stage_interface import LoggerInterface
from llm_client import LLMClient
from debug_mixin import DebugMixin


@dataclass
class RetrospectiveItem:
    """Single retrospective observation"""
    category: str  # "what_went_well", "what_didnt", "action_items"
    description: str
    impact: str  # "high", "medium", "low"
    frequency: str  # "recurring", "one-time"
    suggested_action: Optional[str] = None


@dataclass
class SprintMetrics:
    """Sprint performance metrics"""
    sprint_number: int
    planned_story_points: int
    completed_story_points: int
    velocity: float  # Percentage of planned work completed
    bugs_found: int
    bugs_fixed: int
    tests_passing: float  # Percentage
    code_review_iterations: int
    average_task_duration_hours: float
    blockers_encountered: int


@dataclass
class RetrospectiveReport:
    """Complete sprint retrospective"""
    sprint_number: int
    sprint_start_date: str
    sprint_end_date: str
    metrics: SprintMetrics
    what_went_well: List[RetrospectiveItem]
    what_didnt_go_well: List[RetrospectiveItem]
    action_items: List[RetrospectiveItem]
    key_learnings: List[str]
    velocity_trend: str  # "improving", "declining", "stable"
    overall_health: str  # "healthy", "needs_attention", "critical"
    recommendations: List[str]


@dataclass(frozen=True)
class RetrospectiveContext:
    """
    Parameter Object: Encapsulates retrospective analysis context

    Benefits:
    - Reduces method parameter count (4+ → 1)
    - Makes dependencies explicit
    - Easy to extend with new data
    - Immutable (frozen)
    - Self-documenting
    """
    metrics: SprintMetrics
    action_items: List[RetrospectiveItem]
    velocity_trend: str
    overall_health: str
    what_went_well: List[RetrospectiveItem]
    what_didnt_go_well: List[RetrospectiveItem]

    @property
    def high_priority_actions(self) -> List[RetrospectiveItem]:
        """Derived property: Filter high priority action items"""
        return [a for a in self.action_items if a.impact == "high"]

    @property
    def recurring_issues(self) -> List[RetrospectiveItem]:
        """Derived property: Filter recurring issues"""
        return [a for a in self.what_didnt_go_well if a.frequency == "recurring"]

    @property
    def is_healthy(self) -> bool:
        """Derived property: Check if sprint is healthy"""
        return self.overall_health == "healthy"

    @property
    def needs_immediate_attention(self) -> bool:
        """Derived property: Check if critical issues exist"""
        return self.overall_health == "critical" or len(self.high_priority_actions) > 3


class RetrospectiveAgent(DebugMixin):
    """
    Retrospective Agent - Learn from sprints and improve process

    Analyzes sprint outcomes, extracts patterns, generates improvements
    """

    def __init__(
        self,
        llm_client: LLMClient,
        rag,
        logger: LoggerInterface,
        messenger,
        historical_sprints_to_analyze: int = 3
    ):
        """
        Initialize Retrospective Agent

        Args:
            llm_client: LLM client for analysis
            rag: RAG agent for storing and retrieving learnings
            logger: Logger interface
            messenger: AgentMessenger for communicating results
            historical_sprints_to_analyze: Number of past sprints to compare
        """
        DebugMixin.__init__(self, component_name="retrospective")
        self.llm_client = llm_client
        self.rag = rag
        self.logger = logger
        self.messenger = messenger
        self.historical_sprints_to_analyze = historical_sprints_to_analyze
        self.debug_log("RetrospectiveAgent initialized", historical_sprints=historical_sprints_to_analyze)

    def conduct_retrospective(
        self,
        sprint_number: int,
        sprint_data: Dict,
        card_id: str
    ) -> RetrospectiveReport:
        """
        Conduct sprint retrospective

        Args:
            sprint_number: Sprint number
            sprint_data: Sprint execution data (metrics, events, outcomes)
            card_id: Card ID for storing retrospective

        Returns:
            RetrospectiveReport with findings and recommendations
        """
        self.debug_trace("conduct_retrospective", sprint_number=sprint_number, card_id=card_id)
        self.logger.log(f"🔄 Sprint {sprint_number} Retrospective", "INFO")

        # Step 1: Extract metrics from sprint data
        metrics = self._extract_metrics(sprint_data)

        # Step 2: Retrieve historical sprint data for comparison
        historical_data = self._retrieve_historical_sprints(card_id)

        # Step 3: Analyze what went well
        what_went_well = self._analyze_successes(sprint_data, metrics)

        # Step 4: Analyze what didn't go well
        what_didnt_go_well = self._analyze_failures(sprint_data, metrics)

        # Step 5: Generate action items
        action_items = self._generate_action_items(
            what_went_well,
            what_didnt_go_well,
            metrics
        )

        # Step 6: Extract key learnings
        key_learnings = self._extract_learnings(
            sprint_data,
            what_went_well,
            what_didnt_go_well,
            historical_data
        )

        # Step 7: Analyze velocity trend
        velocity_trend = self._analyze_velocity_trend(metrics, historical_data)

        # Step 8: Assess overall sprint health
        overall_health = self._assess_sprint_health(metrics)

        # Step 9: Build retrospective context (Parameter Object pattern)
        retro_context = RetrospectiveContext(
            metrics=metrics,
            action_items=action_items,
            velocity_trend=velocity_trend,
            overall_health=overall_health,
            what_went_well=what_went_well,
            what_didnt_go_well=what_didnt_go_well
        )

        # Step 10: Generate recommendations using Parameter Object
        recommendations = self._generate_recommendations(retro_context)

        # Create retrospective report
        report = RetrospectiveReport(
            sprint_number=sprint_number,
            sprint_start_date=sprint_data.get('start_date', 'Unknown'),
            sprint_end_date=sprint_data.get('end_date', 'Unknown'),
            metrics=metrics,
            what_went_well=what_went_well,
            what_didnt_go_well=what_didnt_go_well,
            action_items=action_items,
            key_learnings=key_learnings,
            velocity_trend=velocity_trend,
            overall_health=overall_health,
            recommendations=recommendations
        )

        # Store retrospective in RAG for learning
        self._store_retrospective(card_id, report)

        # Communicate to orchestrator
        self._communicate_retrospective(card_id, report)

        self.logger.log(f"✅ Retrospective complete: {overall_health} health", "SUCCESS")
        self.debug_if_enabled("retrospective_summary", "Retrospective completed",
                             sprint=sprint_number, health=overall_health,
                             action_items=len(action_items))

        return report

    def _extract_metrics(self, sprint_data: Dict) -> SprintMetrics:
        """Extract quantitative metrics from sprint data"""
        return SprintMetrics(
            sprint_number=sprint_data.get('sprint_number', 0),
            planned_story_points=sprint_data.get('total_story_points', 0),
            completed_story_points=sprint_data.get('completed_story_points', 0),
            velocity=(
                sprint_data.get('completed_story_points', 0) /
                max(sprint_data.get('total_story_points', 1), 1) * 100
            ),
            bugs_found=sprint_data.get('bugs_found', 0),
            bugs_fixed=sprint_data.get('bugs_fixed', 0),
            tests_passing=sprint_data.get('test_pass_rate', 100.0),
            code_review_iterations=sprint_data.get('code_review_iterations', 0),
            average_task_duration_hours=sprint_data.get('average_task_duration_hours', 0),
            blockers_encountered=sprint_data.get('blockers_encountered', 0)
        )

    def _retrieve_historical_sprints(self, card_id: str) -> List[Dict]:
        """Retrieve historical sprint data from RAG"""
        try:
            # Query RAG for past sprint retrospectives
            results = self.rag.query(
                query=f"Sprint retrospectives for {card_id}",
                limit=self.historical_sprints_to_analyze
            )
            return results
        except Exception as e:
            self.logger.log(f"Could not retrieve historical sprints: {e}", "WARNING")
            return []

    def _analyze_successes(
        self,
        sprint_data: Dict,
        metrics: SprintMetrics
    ) -> List[RetrospectiveItem]:
        """Analyze what went well using LLM and metrics"""
        successes = []

        # Rule-based successes
        if metrics.velocity >= 90:
            successes.append(RetrospectiveItem(
                category="what_went_well",
                description=f"Excellent velocity: {metrics.velocity:.0f}% of planned work completed",
                impact="high",
                frequency="recurring" if metrics.velocity >= 90 else "one-time",
                suggested_action="Maintain current sprint planning accuracy"
            ))

        if metrics.tests_passing >= 95:
            successes.append(RetrospectiveItem(
                category="what_went_well",
                description=f"High test quality: {metrics.tests_passing:.0f}% tests passing",
                impact="high",
                frequency="recurring",
                suggested_action="Continue strong testing practices"
            ))

        if metrics.blockers_encountered == 0:
            successes.append(RetrospectiveItem(
                category="what_went_well",
                description="No blockers encountered during sprint",
                impact="medium",
                frequency="one-time",
                suggested_action="Document factors that prevented blockers"
            ))

        # LLM-based analysis for qualitative successes
        llm_successes = self._llm_analyze_successes(sprint_data)
        successes.extend(llm_successes)

        return successes

    def _analyze_failures(
        self,
        sprint_data: Dict,
        metrics: SprintMetrics
    ) -> List[RetrospectiveItem]:
        """Analyze what didn't go well"""
        failures = []

        # Rule-based failures
        if metrics.velocity < 70:
            failures.append(RetrospectiveItem(
                category="what_didnt_go_well",
                description=f"Low velocity: Only {metrics.velocity:.0f}% of planned work completed",
                impact="high",
                frequency="recurring" if metrics.velocity < 70 else "one-time",
                suggested_action="Review estimation accuracy and capacity planning"
            ))

        if metrics.bugs_found > metrics.bugs_fixed:
            failures.append(RetrospectiveItem(
                category="what_didnt_go_well",
                description=f"Bug backlog increased: {metrics.bugs_found} found, {metrics.bugs_fixed} fixed",
                impact="medium",
                frequency="recurring",
                suggested_action="Allocate more time for bug fixes in next sprint"
            ))

        if metrics.code_review_iterations > 3:
            failures.append(RetrospectiveItem(
                category="what_didnt_go_well",
                description=f"High code review iterations: {metrics.code_review_iterations} average",
                impact="medium",
                frequency="recurring",
                suggested_action="Improve code quality standards and pre-review checklists"
            ))

        if metrics.blockers_encountered > 2:
            failures.append(RetrospectiveItem(
                category="what_didnt_go_well",
                description=f"Multiple blockers: {metrics.blockers_encountered} encountered",
                impact="high",
                frequency="recurring",
                suggested_action="Identify and address dependency issues in planning"
            ))

        # LLM-based analysis for qualitative failures
        llm_failures = self._llm_analyze_failures(sprint_data)
        failures.extend(llm_failures)

        return failures

    def _llm_analyze_successes(self, sprint_data: Dict) -> List[RetrospectiveItem]:
        """Use LLM to identify qualitative successes"""
        prompt = f"""Analyze this sprint data and identify what went well:

{json.dumps(sprint_data, indent=2)}

Focus on:
- Team collaboration
- Process improvements
- Technical achievements
- Communication effectiveness

Respond in JSON format:
{{
    "successes": [
        {{
            "description": "Clear description",
            "impact": "high | medium | low",
            "frequency": "recurring | one-time"
        }}
    ]
}}
"""

        try:
            from llm_client import LLMMessage

            messages = [
                LLMMessage(role="system", content="You are a Scrum Master conducting a sprint retrospective."),
                LLMMessage(role="user", content=prompt)
            ]

            llm_response = self.llm_client.complete(
                messages=messages,
                response_format={"type": "json_object"}
            )

            data = json.loads(llm_response.content)
            return [
                RetrospectiveItem(
                    category="what_went_well",
                    description=item['description'],
                    impact=item['impact'],
                    frequency=item['frequency']
                )
                for item in data.get('successes', [])
            ]

        except Exception as e:
            self.logger.log(f"Error in LLM success analysis: {e}", "ERROR")
            return []

    def _llm_analyze_failures(self, sprint_data: Dict) -> List[RetrospectiveItem]:
        """Use LLM to identify qualitative failures"""
        prompt = f"""Analyze this sprint data and identify what didn't go well:

{json.dumps(sprint_data, indent=2)}

Focus on:
- Process bottlenecks
- Communication gaps
- Technical challenges
- Estimation accuracy

Respond in JSON format:
{{
    "failures": [
        {{
            "description": "Clear description",
            "impact": "high | medium | low",
            "frequency": "recurring | one-time",
            "suggested_action": "Actionable improvement"
        }}
    ]
}}
"""

        try:
            from llm_client import LLMMessage

            messages = [
                LLMMessage(role="system", content="You are a Scrum Master conducting a sprint retrospective."),
                LLMMessage(role="user", content=prompt)
            ]

            llm_response = self.llm_client.complete(
                messages=messages,
                response_format={"type": "json_object"}
            )

            data = json.loads(llm_response.content)
            return [
                RetrospectiveItem(
                    category="what_didnt_go_well",
                    description=item['description'],
                    impact=item['impact'],
                    frequency=item['frequency'],
                    suggested_action=item.get('suggested_action')
                )
                for item in data.get('failures', [])
            ]

        except Exception as e:
            self.logger.log(f"Error in LLM failure analysis: {e}", "ERROR")
            return []

    def _generate_action_items(
        self,
        successes: List[RetrospectiveItem],
        failures: List[RetrospectiveItem],
        metrics: SprintMetrics
    ) -> List[RetrospectiveItem]:
        """Generate concrete action items for next sprint"""
        # Extract suggested actions from failures using list comprehension
        failure_actions = [
            RetrospectiveItem(
                category="action_items",
                description=failure.suggested_action,
                impact=failure.impact,
                frequency="one-time"
            )
            for failure in failures
            if failure.suggested_action and failure.impact in ['high', 'medium']
        ]

        # Add actions to maintain successes using list comprehension
        success_actions = [
            RetrospectiveItem(
                category="action_items",
                description=success.suggested_action,
                impact="medium",
                frequency="recurring"
            )
            for success in successes
            if success.frequency == "recurring" and success.impact == "high" and success.suggested_action
        ]

        return failure_actions + success_actions

    def _extract_learnings(
        self,
        sprint_data: Dict,
        successes: List[RetrospectiveItem],
        failures: List[RetrospectiveItem],
        historical_data: List[Dict]
    ) -> List[str]:
        """Extract key learnings from sprint"""
        learnings = []

        # Pattern detection across sprints
        if len(failures) > 3:
            learnings.append(
                f"Sprint had {len(failures)} challenges - may need to reduce scope or improve planning"
            )

        # Velocity insights
        if historical_data:
            # Compare with historical velocity
            learnings.append("Historical sprint data reviewed for velocity trends")

        # Success patterns
        high_impact_successes = [s for s in successes if s.impact == "high"]
        if high_impact_successes:
            learnings.append(
                f"Team excelled at: {', '.join([s.description for s in high_impact_successes[:2]])}"
            )

        # Failure patterns
        recurring_failures = [f for f in failures if f.frequency == "recurring"]
        if recurring_failures:
            learnings.append(
                f"Recurring issues identified: {', '.join([f.description for f in recurring_failures[:2]])}"
            )

        return learnings

    def _analyze_velocity_trend(
        self,
        current_metrics: SprintMetrics,
        historical_data: List[Dict]
    ) -> str:
        """Analyze velocity trend"""
        if not historical_data:
            return "stable"

        # Compare current velocity with historical average
        # (Simplified - in production would use actual historical metrics)
        current_velocity = current_metrics.velocity

        if current_velocity >= 90:
            return "improving"
        elif current_velocity < 70:
            return "declining"
        else:
            return "stable"

    def _assess_sprint_health(self, metrics: SprintMetrics) -> str:
        """Assess overall sprint health"""
        health_score = 0

        # Velocity (40% weight)
        if metrics.velocity >= 90:
            health_score += 40
        elif metrics.velocity >= 70:
            health_score += 25
        else:
            health_score += 10

        # Test quality (30% weight)
        if metrics.tests_passing >= 95:
            health_score += 30
        elif metrics.tests_passing >= 80:
            health_score += 20
        else:
            health_score += 5

        # Blockers (20% weight)
        if metrics.blockers_encountered == 0:
            health_score += 20
        elif metrics.blockers_encountered <= 2:
            health_score += 10
        else:
            health_score += 0

        # Bug management (10% weight)
        if metrics.bugs_fixed >= metrics.bugs_found:
            health_score += 10
        elif metrics.bugs_fixed >= metrics.bugs_found * 0.75:
            health_score += 5

        # Determine health status
        if health_score >= 80:
            return "healthy"
        elif health_score >= 50:
            return "needs_attention"
        else:
            return "critical"

    def _generate_recommendations(
        self,
        context: RetrospectiveContext
    ) -> List[str]:
        """
        Generate recommendations for next sprint using Parameter Object

        Args:
            context: RetrospectiveContext with all analysis data

        Returns:
            List of actionable recommendations

        Benefits of Parameter Object:
        - Single parameter instead of 4+
        - Access to derived properties (high_priority_actions, recurring_issues)
        - Easy to extend with new analysis
        """
        recommendations = []

        # Velocity-based recommendations
        if context.velocity_trend == "declining":
            recommendations.append(
                "Consider reducing sprint scope or investigating capacity constraints"
            )
        elif context.velocity_trend == "improving":
            recommendations.append(
                "Maintain current practices that are improving velocity"
            )

        # Health-based recommendations (using derived property)
        if context.needs_immediate_attention:
            recommendations.append(
                "Focus on addressing critical issues before planning next sprint"
            )
            recommendations.append(
                "Consider a technical debt sprint to stabilize the codebase"
            )

        # Action item priorities (using derived property)
        high_priority_actions = context.high_priority_actions
        if high_priority_actions:
            recommendations.append(
                f"Prioritize {len(high_priority_actions)} high-impact action items in next sprint planning"
            )

        # Recurring issues (using derived property)
        recurring_issues = context.recurring_issues
        if recurring_issues:
            recommendations.append(
                f"Address {len(recurring_issues)} recurring issues to prevent future sprints from similar problems"
            )

        # Test quality recommendations
        if context.metrics.tests_passing < 90:
            recommendations.append(
                "Improve test coverage and quality - current pass rate below threshold"
            )

        return recommendations

    def _store_retrospective(self, card_id: str, report: RetrospectiveReport) -> None:
        """Store retrospective in RAG for learning"""
        content = f"""Sprint {report.sprint_number} Retrospective

Duration: {report.sprint_start_date} to {report.sprint_end_date}
Health: {report.overall_health}
Velocity: {report.metrics.velocity:.0f}%
Velocity Trend: {report.velocity_trend}

What Went Well ({len(report.what_went_well)} items):
{self._format_items(report.what_went_well)}

What Didn't Go Well ({len(report.what_didnt_go_well)} items):
{self._format_items(report.what_didnt_go_well)}

Action Items ({len(report.action_items)} items):
{self._format_items(report.action_items)}

Key Learnings:
{chr(10).join(['- ' + l for l in report.key_learnings])}

Recommendations:
{chr(10).join(['- ' + r for r in report.recommendations])}
"""

        self.rag.store_artifact(
            artifact_type="sprint_retrospective",
            card_id=card_id,
            task_title=f"Sprint {report.sprint_number} Retrospective",
            content=content,
            metadata={
                'sprint_number': report.sprint_number,
                'overall_health': report.overall_health,
                'velocity': report.metrics.velocity,
                'velocity_trend': report.velocity_trend
            }
        )

    def _format_items(self, items: List[RetrospectiveItem]) -> str:
        """Format retrospective items for display"""
        if not items:
            return "  (none)"

        return "\n".join([
            f"  - [{item.impact.upper()}] {item.description}"
            for item in items
        ])

    def _communicate_retrospective(self, card_id: str, report: RetrospectiveReport) -> None:
        """Communicate retrospective to orchestrator and team"""
        self.messenger.send_data_update(
            to_agent="orchestrator",
            card_id=card_id,
            update_type="sprint_retrospective_complete",
            data={
                'sprint_number': report.sprint_number,
                'overall_health': report.overall_health,
                'velocity': report.metrics.velocity,
                'velocity_trend': report.velocity_trend,
                'action_items_count': len(report.action_items),
                'recommendations': report.recommendations,
                'key_learnings': report.key_learnings
            },
            priority="medium"
        )

        self.logger.log(
            f"📊 Retrospective communicated to orchestrator: {report.overall_health} health",
            "INFO"
        )
