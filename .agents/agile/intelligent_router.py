#!/usr/bin/env python3
"""
Intelligent Router - AI-Powered Stage Selection

Single Responsibility: Determine which pipeline stages should execute based on
task requirements using AI analysis.

This router analyzes task descriptions using the AI Query Service to make
intelligent decisions about stage execution:
- Skip UI/UX stage if no frontend requirement
- Skip dependency validation if no external dependencies
- Skip retrospective for simple tasks
- Customize parallel developers based on complexity

SOLID Principles:
- Single Responsibility: Only handles intelligent stage routing
- Open/Closed: Extensible via configuration and AI prompts
- Liskov Substitution: Works with any AIQueryService implementation
- Interface Segregation: Minimal, focused interface
- Dependency Inversion: Depends on AIQueryService abstraction
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum
import json

from ai_query_service import (
    AIQueryService,
    QueryType,
    AIQueryResult
)
from artemis_exceptions import (
    ArtemisException,
    wrap_exception
)


class StageDecision(Enum):
    """Decision for a stage"""
    REQUIRED = "required"       # Stage must run
    OPTIONAL = "optional"       # Stage can run but not critical
    SKIP = "skip"              # Stage should be skipped
    CONDITIONAL = "conditional" # Stage depends on previous results


@dataclass
class TaskRequirements:
    """Analyzed requirements from task description"""
    has_frontend: bool
    has_backend: bool
    has_api: bool
    has_database: bool
    has_external_dependencies: bool
    has_ui_components: bool
    has_accessibility_requirements: bool
    complexity: str  # 'simple', 'medium', 'complex'
    task_type: str   # 'feature', 'bugfix', 'refactor', 'documentation', 'test'
    estimated_story_points: int
    requires_architecture_review: bool
    requires_project_review: bool
    parallel_developers_recommended: int
    confidence_score: float


@dataclass
class RoutingDecision:
    """Complete routing decision for a task"""
    task_id: str
    task_title: str
    requirements: TaskRequirements
    stage_decisions: Dict[str, StageDecision]
    stages_to_run: List[str]
    stages_to_skip: List[str]
    reasoning: str
    confidence_score: float


class IntelligentRouter:
    """
    Intelligent router that uses AI to determine which stages should execute

    This class analyzes task requirements and makes informed decisions about
    which pipeline stages are necessary for each specific task.
    """

    # All available stages in execution order
    ALL_STAGES = [
        "requirements",
        "sprint_planning",
        "project_analysis",
        "architecture",
        "project_review",
        "dependency_validation",
        "development",
        "code_review",
        "uiux",
        "validation",
        "integration",
        "testing",
        "notebook_generation"
    ]

    # Performance: Pre-compiled regex patterns for keyword matching (O(n) vs O(n*m))
    import re
    FRONTEND_PATTERN = re.compile(r'\b(html|css|javascript|react|vue|angular|frontend|ui|user\s*interface|visualization|chart|dashboard|button|form|modal|component|page|view|template)\b', re.IGNORECASE)
    BACKEND_PATTERN = re.compile(r'\b(api|backend|server|endpoint|service|business\s*logic|data\s*processing|calculation|algorithm|function|method)\b', re.IGNORECASE)
    API_PATTERN = re.compile(r'\b(api|endpoint|rest|graphql|request|response)\b', re.IGNORECASE)
    DATABASE_PATTERN = re.compile(r'\b(database|sql|nosql|mongodb|postgres|mysql|schema|table|collection|query|data\s*model)\b', re.IGNORECASE)
    DEPENDENCY_PATTERN = re.compile(r'\b(library|package|dependency|npm|pip|import|external|third-party|integration|sdk)\b', re.IGNORECASE)
    UI_COMPONENT_PATTERN = re.compile(r'\b(button|form|input|modal|dialog|menu|navigation|dropdown|select|checkbox|radio|slider|tooltip)\b', re.IGNORECASE)
    A11Y_PATTERN = re.compile(r'\b(accessibility|wcag|screen\s*reader|aria|keyboard|a11y|alt\s*text|focus|semantic|contrast)\b', re.IGNORECASE)
    NOTEBOOK_PATTERN = re.compile(r'\b(jupyter|notebook|ipynb|data\s*analysis|data\s*science|machine\s*learning|ml|model|training|visualization|pandas|numpy|matplotlib|seaborn|experiment|analysis)\b', re.IGNORECASE)

    # Stages that are always required (core pipeline)
    CORE_STAGES = {
        "development",      # Always need code
        "code_review",      # Always review code
        "validation",       # Always validate
        "integration",      # Always integrate
        "testing"          # Always test
    }

    def __init__(
        self,
        ai_service: Optional[AIQueryService] = None,
        logger: Optional[Any] = None,
        config: Optional[Any] = None
    ):
        """
        Initialize intelligent router

        Args:
            ai_service: AI Query Service for requirement analysis
            logger: Logger for output
            config: Configuration for routing rules
        """
        self.ai_service = ai_service
        self.logger = logger
        self.config = config

        # Load routing configuration
        self.enable_ai_routing = config.get('routing.enable_ai', True) if config else True
        self.skip_stages_threshold = config.get('routing.skip_threshold', 0.8) if config else 0.8
        self.require_stages_threshold = config.get('routing.require_threshold', 0.6) if config else 0.6

    def analyze_task_requirements(self, card: Dict) -> TaskRequirements:
        """
        Analyze task to extract requirements

        Args:
            card: Kanban card with task details

        Returns:
            TaskRequirements with analyzed needs
        """
        task_title = card.get('title', '')
        task_description = card.get('description', '')
        full_text = f"{task_title}\n\n{task_description}".lower()

        # If AI service available, use it for intelligent analysis
        if self.ai_service and self.enable_ai_routing:
            return self._ai_analyze_requirements(card, full_text)

        # Fallback: Rule-based analysis
        return self._rule_based_analysis(card, full_text)

    def _ai_analyze_requirements(self, card: Dict, full_text: str) -> TaskRequirements:
        """Use AI to analyze task requirements"""

        prompt = f"""Analyze this software development task and extract requirements:

Task: {card.get('title', '')}
Description: {card.get('description', '')}

Provide a JSON response with the following fields:
{{
    "has_frontend": true/false,
    "has_backend": true/false,
    "has_api": true/false,
    "has_database": true/false,
    "has_external_dependencies": true/false,
    "has_ui_components": true/false,
    "has_accessibility_requirements": true/false,
    "complexity": "simple|medium|complex",
    "task_type": "feature|bugfix|refactor|documentation|test",
    "estimated_story_points": 1-13,
    "requires_architecture_review": true/false,
    "requires_project_review": true/false,
    "parallel_developers_recommended": 1-3,
    "confidence_score": 0.0-1.0,
    "reasoning": "Brief explanation"
}}

Consider:
- Frontend: HTML, CSS, JavaScript, React, Vue, UI, visualization, charts
- Backend: API, server, business logic, data processing
- Database: SQL, NoSQL, schema, queries, data models
- Dependencies: External libraries, packages, services, APIs
- UI/Accessibility: WCAG, screen readers, keyboard navigation, ARIA
- Complexity: Lines of code, number of files, integration points
"""

        try:
            # Query AI service
            result = self.ai_service.query(
                query_type=QueryType.PROJECT_ANALYSIS,
                prompt=prompt,
                kg_query_params={
                    'task_title': card.get('title', ''),
                    'context_type': 'requirement_analysis'
                }
            )

            # Parse AI response
            response_text = result.llm_response.content

            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(response_text[json_start:json_end])
            else:
                # AI didn't return valid JSON, fall back to rule-based
                if self.logger:
                    self.logger.log("AI analysis failed to return valid JSON, using rule-based fallback", "WARNING")
                return self._rule_based_analysis(card, full_text)

            # Create TaskRequirements from AI analysis
            return TaskRequirements(
                has_frontend=analysis.get('has_frontend', False),
                has_backend=analysis.get('has_backend', True),
                has_api=analysis.get('has_api', False),
                has_database=analysis.get('has_database', False),
                has_external_dependencies=analysis.get('has_external_dependencies', False),
                has_ui_components=analysis.get('has_ui_components', False),
                has_accessibility_requirements=analysis.get('has_accessibility_requirements', False),
                complexity=analysis.get('complexity', 'medium'),
                task_type=analysis.get('task_type', 'feature'),
                estimated_story_points=analysis.get('estimated_story_points', 5),
                requires_architecture_review=analysis.get('requires_architecture_review', True),
                requires_project_review=analysis.get('requires_project_review', True),
                parallel_developers_recommended=analysis.get('parallel_developers_recommended', 1),
                confidence_score=analysis.get('confidence_score', 0.7)
            )

        except Exception as e:
            if self.logger:
                self.logger.log(f"AI requirement analysis failed: {e}, using rule-based fallback", "WARNING")
            return self._rule_based_analysis(card, full_text)

    def _rule_based_analysis(self, card: Dict, full_text: str) -> TaskRequirements:
        """Fallback: Rule-based requirement analysis using pre-compiled patterns"""

        # Performance: Use pre-compiled regex patterns (single scan vs multiple any() loops)
        has_frontend = bool(self.FRONTEND_PATTERN.search(full_text))
        has_backend = bool(self.BACKEND_PATTERN.search(full_text))
        has_api = bool(self.API_PATTERN.search(full_text))
        has_database = bool(self.DATABASE_PATTERN.search(full_text))
        has_external_dependencies = bool(self.DEPENDENCY_PATTERN.search(full_text))
        has_ui_components = bool(self.UI_COMPONENT_PATTERN.search(full_text))
        has_accessibility_requirements = bool(self.A11Y_PATTERN.search(full_text))
        requires_notebook = bool(self.NOTEBOOK_PATTERN.search(full_text))

        # Estimate complexity from story points or description length
        story_points = card.get('story_points', 5)
        if story_points <= 3:
            complexity = 'simple'
        elif story_points <= 8:
            complexity = 'medium'
        else:
            complexity = 'complex'

        # ALWAYS use 2 parallel developers for competitive development
        parallel_devs = 2

        # Detect task type
        if any(kw in full_text for kw in ['bug', 'fix', 'error', 'issue']):
            task_type = 'bugfix'
        elif any(kw in full_text for kw in ['refactor', 'cleanup', 'improve']):
            task_type = 'refactor'
        elif any(kw in full_text for kw in ['test', 'testing', 'coverage']):
            task_type = 'test'
        elif any(kw in full_text for kw in ['documentation', 'doc', 'readme']):
            task_type = 'documentation'
        else:
            task_type = 'feature'

        # Determine if reviews are needed
        requires_architecture_review = complexity in ['medium', 'complex'] or has_database or has_api
        requires_project_review = complexity == 'complex' or story_points >= 8

        return TaskRequirements(
            has_frontend=has_frontend,
            has_backend=has_backend,
            has_api=has_api,
            has_database=has_database,
            has_external_dependencies=has_external_dependencies,
            has_ui_components=has_ui_components,
            has_accessibility_requirements=has_accessibility_requirements,
            complexity=complexity,
            task_type=task_type,
            estimated_story_points=story_points,
            requires_architecture_review=requires_architecture_review,
            requires_project_review=requires_project_review,
            parallel_developers_recommended=parallel_devs,
            confidence_score=0.6  # Rule-based has lower confidence
        )

    def make_routing_decision(self, card: Dict) -> RoutingDecision:
        """
        Make complete routing decision for a task

        Args:
            card: Kanban card with task details

        Returns:
            RoutingDecision with stage selections
        """
        # Analyze requirements
        requirements = self.analyze_task_requirements(card)

        # Make decisions for each stage
        stage_decisions = {}
        reasoning_parts = []

        # Requirements stage - always run if using requirements parser
        stage_decisions['requirements'] = StageDecision.OPTIONAL

        # Sprint planning - skip for simple tasks
        if requirements.complexity == 'simple':
            stage_decisions['sprint_planning'] = StageDecision.SKIP
            reasoning_parts.append("Skipping sprint planning for simple task")
        else:
            stage_decisions['sprint_planning'] = StageDecision.REQUIRED

        # Project analysis - run for medium/complex tasks
        if requirements.complexity in ['medium', 'complex']:
            stage_decisions['project_analysis'] = StageDecision.REQUIRED
        else:
            stage_decisions['project_analysis'] = StageDecision.SKIP
            reasoning_parts.append("Skipping project analysis for simple task")

        # Architecture - required for complex tasks or those with database/API
        if requirements.requires_architecture_review:
            stage_decisions['architecture'] = StageDecision.REQUIRED
        else:
            stage_decisions['architecture'] = StageDecision.SKIP
            reasoning_parts.append("Skipping architecture for simple implementation")

        # Project review - required for complex tasks
        if requirements.requires_project_review:
            stage_decisions['project_review'] = StageDecision.REQUIRED
        else:
            stage_decisions['project_review'] = StageDecision.SKIP
            reasoning_parts.append("Skipping project review for simple task")

        # Dependency validation - only if external dependencies detected
        if requirements.has_external_dependencies:
            stage_decisions['dependency_validation'] = StageDecision.REQUIRED
        else:
            stage_decisions['dependency_validation'] = StageDecision.SKIP
            reasoning_parts.append("No external dependencies detected, skipping validation")

        # Core stages - always required
        stage_decisions['development'] = StageDecision.REQUIRED
        stage_decisions['code_review'] = StageDecision.REQUIRED
        stage_decisions['validation'] = StageDecision.REQUIRED
        stage_decisions['integration'] = StageDecision.REQUIRED
        stage_decisions['testing'] = StageDecision.REQUIRED

        # UI/UX stage - only if frontend/UI components detected
        if requirements.has_frontend or requirements.has_ui_components or requirements.has_accessibility_requirements:
            stage_decisions['uiux'] = StageDecision.REQUIRED
            reasoning_parts.append(f"UI/UX stage required (frontend={requirements.has_frontend}, ui_components={requirements.has_ui_components}, a11y={requirements.has_accessibility_requirements})")
        else:
            stage_decisions['uiux'] = StageDecision.SKIP
            reasoning_parts.append("No frontend/UI requirements detected, skipping UI/UX stage")

        # Notebook generation - only if data science/ML/analysis task detected
        if requires_notebook:
            stage_decisions['notebook_generation'] = StageDecision.REQUIRED
            reasoning_parts.append("Notebook generation required for data analysis/ML task")
        else:
            stage_decisions['notebook_generation'] = StageDecision.SKIP

        # Build final stage lists
        stages_to_run = [
            stage for stage in self.ALL_STAGES
            if stage_decisions.get(stage, StageDecision.SKIP) in [StageDecision.REQUIRED, StageDecision.OPTIONAL]
        ]

        stages_to_skip = [
            stage for stage in self.ALL_STAGES
            if stage_decisions.get(stage, StageDecision.SKIP) == StageDecision.SKIP
        ]

        # Build reasoning
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Running all standard stages"

        return RoutingDecision(
            task_id=card.get('card_id', card.get('task_id', 'unknown')),
            task_title=card.get('title', 'Unknown'),
            requirements=requirements,
            stage_decisions=stage_decisions,
            stages_to_run=stages_to_run,
            stages_to_skip=stages_to_skip,
            reasoning=reasoning,
            confidence_score=requirements.confidence_score
        )

    def filter_stages(self, all_stages: List[Any], routing_decision: RoutingDecision) -> List[Any]:
        """
        Filter stage instances based on routing decision

        Args:
            all_stages: List of stage instances
            routing_decision: Routing decision with stages to run

        Returns:
            Filtered list of stage instances to execute
        """
        stages_to_run_names = set(routing_decision.stages_to_run)

        filtered_stages = [
            stage for stage in all_stages
            if stage.get_stage_name() in stages_to_run_names
        ]

        return filtered_stages

    def log_routing_decision(self, decision: RoutingDecision):
        """Log routing decision for visibility"""
        if not self.logger:
            return

        self.logger.log("=" * 60, "INFO")
        self.logger.log("🧭 INTELLIGENT ROUTING DECISION", "INFO")
        self.logger.log("=" * 60, "INFO")
        self.logger.log(f"Task: {decision.task_title}", "INFO")
        self.logger.log(f"Complexity: {decision.requirements.complexity}", "INFO")
        self.logger.log(f"Type: {decision.requirements.task_type}", "INFO")
        self.logger.log(f"Story Points: {decision.requirements.estimated_story_points}", "INFO")
        self.logger.log(f"Parallel Developers: {decision.requirements.parallel_developers_recommended}", "INFO")
        self.logger.log("", "INFO")
        self.logger.log("Requirements Detected:", "INFO")
        self.logger.log(f"  Frontend: {decision.requirements.has_frontend}", "INFO")
        self.logger.log(f"  Backend: {decision.requirements.has_backend}", "INFO")
        self.logger.log(f"  API: {decision.requirements.has_api}", "INFO")
        self.logger.log(f"  Database: {decision.requirements.has_database}", "INFO")
        self.logger.log(f"  UI Components: {decision.requirements.has_ui_components}", "INFO")
        self.logger.log(f"  Accessibility: {decision.requirements.has_accessibility_requirements}", "INFO")
        self.logger.log(f"  External Deps: {decision.requirements.has_external_dependencies}", "INFO")
        self.logger.log("", "INFO")
        self.logger.log(f"Stages to Run ({len(decision.stages_to_run)}):", "INFO")
        for stage in decision.stages_to_run:
            self.logger.log(f"  ✓ {stage}", "INFO")
        self.logger.log("", "INFO")
        if decision.stages_to_skip:
            self.logger.log(f"Stages to Skip ({len(decision.stages_to_skip)}):", "INFO")
            for stage in decision.stages_to_skip:
                self.logger.log(f"  ✗ {stage}", "INFO")
            self.logger.log("", "INFO")
        self.logger.log(f"Reasoning: {decision.reasoning}", "INFO")
        self.logger.log(f"Confidence: {decision.confidence_score:.1%}", "INFO")
        self.logger.log("=" * 60, "INFO")
