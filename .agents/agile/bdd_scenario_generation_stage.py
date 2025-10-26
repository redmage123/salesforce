#!/usr/bin/env python3
"""
BDD Scenario Generation Stage

Generates Gherkin feature files from requirements using LLM.
Follows BDD best practices for Given/When/Then scenarios.

Integration Points:
- Runs after SprintPlanningStage
- Provides scenarios to DevelopmentStage
- Feeds into BDD Test Generation Stage
"""

from typing import Dict, Optional
from pathlib import Path

from artemis_stage_interface import PipelineStage, LoggerInterface
from supervised_agent_mixin import SupervisedStageMixin
from kanban_manager import KanbanBoard
from rag_agent import RAGAgent
from llm_client import LLMClient
from artemis_exceptions import PipelineStageError, wrap_exception


class BDDScenarioGenerationStage(PipelineStage, SupervisedStageMixin):
    """
    Generate BDD scenarios in Gherkin format from requirements.

    Single Responsibility: Transform requirements into executable specifications

    Integrates with supervisor for:
    - LLM call monitoring
    - Scenario validation
    - Feature file generation tracking
    """

    def __init__(
        self,
        board: KanbanBoard,
        rag: RAGAgent,
        logger: LoggerInterface,
        llm_client: LLMClient,
        observable: Optional['PipelineObservable'] = None,
        supervisor: Optional['SupervisorAgent'] = None,
        ai_service: Optional['AIQueryService'] = None
    ):
        PipelineStage.__init__(self)
        SupervisedStageMixin.__init__(
            self,
            supervisor=supervisor,
            stage_name="BDDScenarioGenerationStage",
            heartbeat_interval=20
        )

        self.board = board
        self.rag = rag
        self.logger = logger
        self.llm_client = llm_client
        self.observable = observable
        self.supervisor = supervisor
        self.ai_service = ai_service

    def execute(self, card: Dict, context: Dict) -> Dict:
        """Execute with supervisor monitoring"""
        metadata = {
            "task_id": card.get('card_id'),
            "stage": "bdd_scenario_generation"
        }

        with self.supervised_execution(metadata):
            result = self._do_work(card, context)

        return result

    def _do_work(self, card: Dict, context: Dict) -> Dict:
        """Generate BDD scenarios from requirements"""
        self.logger.log("🥒 Starting BDD Scenario Generation Stage", "STAGE")

        card_id = card.get('card_id', 'unknown')
        title = card.get('title', 'Unknown Task')

        # Update progress
        self.update_progress({"step": "starting", "progress_percent": 10})

        # Get requirements from context or RAG
        requirements = context.get('requirements', {})
        if not requirements:
            # Try to fetch from RAG
            requirements_artifact = self.rag.query(
                query_text=f"requirements for {title}",
                filter_metadata={"card_id": card_id, "artifact_type": "requirements"}
            )
            if requirements_artifact:
                requirements = requirements_artifact[0].get('content', {})

        self.logger.log(f"📋 Generating BDD scenarios for: {title}", "INFO")

        # Update progress
        self.update_progress({"step": "generating_scenarios", "progress_percent": 30})

        # Generate Gherkin scenarios using LLM
        scenarios_content = self._generate_gherkin_scenarios(
            card_id=card_id,
            title=title,
            requirements=requirements
        )

        # Update progress
        self.update_progress({"step": "validating_scenarios", "progress_percent": 60})

        # Validate scenario structure
        validation_result = self._validate_gherkin_syntax(scenarios_content)

        if not validation_result['valid']:
            self.logger.log(f"⚠️  Scenario validation issues: {validation_result['errors']}", "WARNING")

        # Update progress
        self.update_progress({"step": "storing_scenarios", "progress_percent": 80})

        # Store feature files for each developer
        winner = context.get('winner', 'developer-a')
        feature_path = self._store_feature_file(winner, title, scenarios_content)

        # Store in RAG
        self.rag.store_artifact(
            artifact_type="bdd_scenarios",
            card_id=card_id,
            task_title=title,
            content=scenarios_content,
            metadata={
                "feature_path": str(feature_path),
                "scenario_count": scenarios_content.count("Scenario:"),
                "validation_status": "valid" if validation_result['valid'] else "has_issues"
            }
        )

        # Update progress
        self.update_progress({"step": "complete", "progress_percent": 100})

        self.logger.log(f"✅ Generated {scenarios_content.count('Scenario:')} BDD scenarios", "SUCCESS")

        return {
            "stage": "bdd_scenario_generation",
            "feature_path": str(feature_path),
            "scenarios_content": scenarios_content,
            "scenario_count": scenarios_content.count("Scenario:"),
            "validation": validation_result
        }

    def _generate_gherkin_scenarios(
        self,
        card_id: str,
        title: str,
        requirements: Dict
    ) -> str:
        """Generate Gherkin scenarios using LLM"""

        prompt = f"""You are a BDD expert. Generate comprehensive Gherkin scenarios for the following feature.

Feature: {title}

Requirements:
{requirements}

Generate a complete .feature file with:
1. Feature description (As a/I want/So that format)
2. Multiple scenarios covering:
   - Happy path (normal expected behavior)
   - Edge cases
   - Error handling
   - User interactions
3. Use Given/When/Then format
4. Make scenarios specific and testable
5. Include scenario outlines for data-driven tests where appropriate

Format the output as a valid Gherkin feature file."""

        # Use AI Query Service if available for token optimization
        if self.ai_service:
            result = self.ai_service.query(
                query=prompt,
                context={"card_id": card_id, "title": title},
                temperature=0.3,
                max_tokens=2000
            )
            if result.success:
                return result.response
            else:
                self.logger.log(f"AI Query Service failed: {result.error}, falling back to direct LLM", "WARNING")

        # Fallback to direct LLM call
        response = self.llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )

        return response

    def _validate_gherkin_syntax(self, content: str) -> Dict:
        """Validate Gherkin scenario structure"""
        errors = []

        # Check for required keywords
        if "Feature:" not in content:
            errors.append("Missing 'Feature:' declaration")

        if "Scenario:" not in content and "Scenario Outline:" not in content:
            errors.append("No scenarios defined")

        # Check scenario structure
        scenarios = content.split("Scenario:")
        for i, scenario in enumerate(scenarios[1:], 1):  # Skip feature description
            if "Given" not in scenario and "When" not in scenario:
                errors.append(f"Scenario {i} missing Given/When steps")
            if "Then" not in scenario:
                errors.append(f"Scenario {i} missing Then assertions")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    def _store_feature_file(self, developer: str, title: str, content: str) -> Path:
        """Store feature file in developer's directory"""
        feature_dir = Path(f"/tmp/{developer}/features")
        feature_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        filename = title.lower().replace(' ', '_').replace('/', '_')
        feature_path = feature_dir / f"{filename}.feature"

        with open(feature_path, 'w') as f:
            f.write(content)

        self.logger.log(f"📝 Stored feature file: {feature_path}", "INFO")

        return feature_path

    def get_stage_name(self) -> str:
        return "bdd_scenario_generation"
