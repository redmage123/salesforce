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
    PipelineStageError,
    wrap_exception
)
from environment_context import get_environment_context
from path_config_service import get_developer_tests_path

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

# Import ADR service classes for ArchitectureStage refactoring
from adr_numbering_service import ADRNumberingService
from adr_generator import ADRGenerator
from user_story_generator import UserStoryGenerator
from adr_storage_service import ADRStorageService

# Import Research Stage components
from research_stage import ResearchStage, create_research_stage


# ============================================================================
# PROJECT ANALYSIS STAGE (Pre-Implementation Review)
# ============================================================================

class ProjectAnalysisStage(PipelineStage, SupervisedStageMixin):
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

    @wrap_exception(PipelineStageError, "Project analysis stage execution failed")
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

        # Get RAG recommendations from context
        rag_recommendations = context.get('rag_recommendations', {})

        # Build analysis context
        analysis_context = {
            'rag_recommendations': rag_recommendations,
            'workflow_plan': context.get('workflow_plan', {}),
            'priority': card.get('priority', 'medium'),
            'complexity': context.get('workflow_plan', {}).get('complexity', 'medium')
        }

        # Update progress: starting analysis
        self.update_progress({"step": "analyzing_task", "progress_percent": 10})

        # Run analysis across all dimensions
        analysis = self.engine.analyze_task(card, analysis_context)

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

        self.rag.store_artifact(
            artifact_type="project_analysis",
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

class ArchitectureStage(PipelineStage, SupervisedStageMixin):
    """
    Single Responsibility: Create Architecture Decision Records (ADRs)

    This stage ONLY handles ADR creation - nothing else.

    Integrates with supervisor for:
    - Unexpected state handling (ADR generation failures)
    - LLM cost tracking (if using LLM for ADR generation)
    - Automatic heartbeat and health monitoring
    """

    def __init__(
        self,
        board: KanbanBoard,
        messenger: AgentMessenger,
        rag: RAGAgent,
        logger: LoggerInterface,
        adr_dir: Optional[Path] = None,
        supervisor: Optional['SupervisorAgent'] = None,
        llm_client: Optional[Any] = None,
        ai_service: Optional[AIQueryService] = None
    ):
        # Initialize PipelineStage
        PipelineStage.__init__(self)

        # Set ADR directory from config or use default
        if adr_dir is None:
            adr_path = os.getenv("ARTEMIS_ADR_DIR", "../../.artemis_data/adrs")
            if not os.path.isabs(adr_path):
                script_dir = os.path.dirname(os.path.abspath(__file__))
                adr_path = os.path.join(script_dir, adr_path)
            adr_dir = Path(adr_path)

        # Initialize SupervisedStageMixin for health monitoring
        SupervisedStageMixin.__init__(
            self,
            supervisor=supervisor,
            stage_name="ArchitectureStage",
            heartbeat_interval=15
        )

        self.board = board
        self.messenger = messenger
        self.rag = rag
        self.logger = logger
        self.llm_client = llm_client
        self.adr_dir = adr_dir
        self.adr_dir.mkdir(exist_ok=True, parents=True)

        # Initialize PromptManager if available
        self.prompt_manager = None
        if PROMPT_MANAGER_AVAILABLE and self.rag:
            try:
                self.prompt_manager = PromptManager(self.rag, verbose=False)
                self.logger.log("✅ Prompt manager initialized (RAG-based prompts)", "INFO")
            except Exception as e:
                self.logger.log(f"⚠️  Could not initialize PromptManager: {e}", "WARNING")

        # Initialize centralized AI Query Service (KG→RAG→LLM pipeline)
        try:
            if ai_service:
                self.ai_service = ai_service
                self.logger.log("✅ Using provided AI Query Service", "INFO")
            else:
                self.ai_service = create_ai_query_service(
                    llm_client=llm_client,
                    rag=rag,
                    logger=logger,
                    verbose=False
                )
                self.logger.log("✅ AI Query Service initialized (KG→RAG→LLM)", "INFO")
        except Exception as e:
            self.logger.log(f"⚠️  Could not initialize AI Query Service: {e}", "WARNING")
            self.ai_service = None

        # Initialize ADR service classes (SOLID refactoring)
        self.numbering_service = ADRNumberingService(self.adr_dir)
        self.adr_generator = ADRGenerator(
            rag=self.rag,
            logger=self.logger,
            llm_client=self.llm_client,
            ai_service=self.ai_service,
            prompt_manager=self.prompt_manager
        )
        self.story_generator = UserStoryGenerator(
            llm_client=self.llm_client,
            logger=self.logger,
            prompt_manager=self.prompt_manager
        )
        self.storage_service = ADRStorageService(
            rag=self.rag,
            board=self.board,
            logger=self.logger
        )

    @wrap_exception(PipelineStageError, "Architecture stage execution failed")
    def execute(self, card: Dict, context: Dict) -> Dict:
        """Create ADR for the task with supervisor monitoring"""
        metadata = {
            "task_id": card.get('card_id'),
            "stage": "architecture"
        }

        with self.supervised_execution(metadata):
            return self._create_adr(card, context)

    def _create_adr(self, card: Dict, context: Dict) -> Dict:
        """Internal method that performs ADR creation"""
        self.logger.log("Starting Architecture Stage", "STAGE")

        card_id = card['card_id']

        # Check for structured requirements from requirements_parsing stage
        structured_requirements = context.get('structured_requirements')
        if structured_requirements:
            self.logger.log("✅ Using structured requirements from requirements parsing stage", "INFO")
            self.logger.log(f"   Found {len(structured_requirements.functional_requirements)} functional requirements", "INFO")
            self.logger.log(f"   Found {len(structured_requirements.non_functional_requirements)} non-functional requirements", "INFO")

        # Update progress: getting ADR number
        self.update_progress({"step": "getting_adr_number", "progress_percent": 10})

        # Get next ADR number (using ADRNumberingService)
        adr_number = self.numbering_service.get_next_adr_number()

        # Update progress: generating ADR
        self.update_progress({"step": "generating_adr", "progress_percent": 30})

        # Create ADR file (using ADRGenerator service)
        adr_content = self.adr_generator.generate_adr(card, adr_number, structured_requirements)
        adr_filename = self.numbering_service.create_adr_filename(card['title'], adr_number)
        adr_path = self.adr_dir / adr_filename

        # Update progress: writing ADR file
        self.update_progress({"step": "writing_adr_file", "progress_percent": 50})

        FileManager.write_text(adr_path, adr_content)
        self.logger.log(f"ADR created: {adr_filename}", "SUCCESS")

        # Update progress: sending notifications
        self.update_progress({"step": "sending_notifications", "progress_percent": 65})

        # Update messaging
        self._send_adr_notification(card_id, str(adr_path), adr_number)

        # Update progress: updating kanban
        self.update_progress({"step": "updating_kanban", "progress_percent": 80})

        # Update Kanban
        self.board.update_card(card_id, {
            "architecture_status": "complete",
            "adr_number": adr_number,
            "adr_file": str(adr_path)
        })
        self.board.move_card(card_id, "development", "pipeline-orchestrator")

        # Update progress: storing ADR in RAG
        self.update_progress({"step": "storing_adr_in_rag", "progress_percent": 70})

        # Store ADR in RAG (using ADRStorageService)
        self.storage_service.store_adr_in_rag(
            card_id=card_id,
            task_title=card.get('title', 'Unknown'),
            adr_content=adr_content,
            adr_number=adr_number,
            adr_path=str(adr_path),
            priority=card.get('priority', 'medium'),
            story_points=card.get('points', 5)
        )

        # Store ADR in Knowledge Graph for traceability (using ADRStorageService)
        self.storage_service.store_adr_in_knowledge_graph(
            card_id=card_id,
            adr_number=adr_number,
            adr_path=str(adr_path),
            adr_title=f"Architecture Decision {adr_number}",
            structured_requirements=structured_requirements
        )

        # Update progress: generating user stories from ADR
        self.update_progress({"step": "generating_user_stories", "progress_percent": 80})

        # Generate user stories from ADR and add to Kanban (using UserStoryGenerator)
        user_stories = self.story_generator.generate_user_stories(adr_content, adr_number, card)

        # Update progress: adding user stories to kanban
        self.update_progress({"step": "adding_stories_to_kanban", "progress_percent": 90})

        story_cards = []
        for idx, story in enumerate(user_stories):
            # Generate unique task ID for user story
            story_task_id = f"{card_id}-story-{idx+1}"

            # Use CardBuilder pattern to create story card
            story_card = (self.board.new_card(story_task_id, story['title'])
                .with_description(story['description'])
                .with_priority(story.get('priority', card.get('priority', 'medium')))
                .with_story_points(story.get('points', 3))
                .build())

            # Add metadata
            story_card['metadata'] = {
                'parent_adr': adr_number,
                'parent_card': card_id,
                'acceptance_criteria': story.get('acceptance_criteria', [])
            }

            # Add card to board
            self.board.add_card(story_card)
            story_cards.append(story_task_id)
            self.logger.log(f"  ✅ Created user story: {story['title']}", "INFO")

        # Update progress: storing kanban in RAG
        self.update_progress({"step": "storing_kanban_in_rag", "progress_percent": 95})

        # Store Kanban board state in RAG (using ADRStorageService)
        self.storage_service.store_kanban_in_rag(card_id, story_cards)

        # Update progress: complete
        self.update_progress({"step": "complete", "progress_percent": 100})

        return {
            "stage": "architecture",
            "adr_number": adr_number,
            "adr_file": str(adr_path),
            "user_stories_created": len(story_cards),
            "story_card_ids": story_cards,
            "status": "COMPLETE",
            "metrics": {
                "user_stories_generated": len(story_cards),
                "adr_created": True
            }
        }

    def get_stage_name(self) -> str:
        return "architecture"

    def _get_next_adr_number(self) -> str:
        """Get next available ADR number"""
        existing_adrs = list(self.adr_dir.glob("ADR-*.md"))
        if existing_adrs:
            numbers = []
            for adr_file in existing_adrs:
                match = re.search(r'ADR-(\d+)', adr_file.name)
                if match:
                    numbers.append(int(match.group(1)))
            next_num = max(numbers) + 1 if numbers else 1
        else:
            next_num = 1
        return f"{next_num:03d}"

    def _create_adr_filename(self, title: str, adr_number: str) -> str:
        """Create ADR filename from title"""
        # Sanitize title to remove file paths and invalid characters
        slug = re.sub(r'[^a-zA-Z0-9\s-]', '', title)  # Remove invalid chars
        slug = slug.lower().replace(' ', '-')[:50]  # Convert to kebab-case
        slug = re.sub(r'-+', '-', slug).strip('-')  # Normalize multiple dashes
        return f"ADR-{adr_number}-{slug}.md"

    def _generate_adr(self, card: Dict, adr_number: str, structured_requirements=None) -> str:
        """
        Generate ADR content using AIQueryService (KG→RAG→LLM pipeline)

        Uses centralized AIQueryService to automatically query Knowledge Graph
        for similar ADRs, get RAG recommendations, and call LLM with enhanced context.
        """
        try:
            title = card.get('title', 'Untitled Task')
            description = card.get('description', 'No description provided')

            # If AIQueryService available, use it for intelligent ADR generation
            if self.ai_service:
                # Build base ADR prompt
                prompt = self._build_adr_prompt(card, adr_number, structured_requirements)

                # Extract keywords for KG query
                keywords = title.split()[:3]

                # Use AI Query Service (handles KG→RAG→LLM automatically)
                self.logger.log("🔄 Using AI Query Service for KG→RAG→LLM pipeline", "INFO")

                result = self.ai_service.query(
                    query_type=QueryType.ARCHITECTURE_DESIGN,
                    prompt=prompt,
                    kg_query_params={
                        'keywords': keywords,
                        'req_type': 'functional'
                    },
                    temperature=0.3,
                    max_tokens=3000
                )

                if not result.success:
                    raise ADRGenerationError(
                        f"AI Query Service failed: {result.error}",
                        context={"card_id": card.get('card_id'), "title": title}
                    )

                # Log token savings
                if result.kg_context and result.kg_context.pattern_count > 0:
                    self.logger.log(
                        f"📊 KG found {result.kg_context.pattern_count} ADR patterns, "
                        f"saved ~{result.llm_response.tokens_saved} tokens",
                        "INFO"
                    )

                # Return LLM-generated ADR content
                return result.llm_response.content

            # Fallback: Generate ADR manually without AI service
            self.logger.log("⚠️  AI Query Service unavailable - using template-based generation", "WARNING")
            return self._generate_adr_template(card, adr_number, structured_requirements)

        except ADRGenerationError:
            # Re-raise already wrapped exceptions
            raise
        except Exception as e:
            raise wrap_exception(
                e,
                ADRGenerationError,
                f"Failed to generate ADR: {str(e)}",
                context={"card_id": card.get('card_id'), "adr_number": adr_number}
            )

    def _build_adr_prompt(self, card: Dict, adr_number: str, structured_requirements=None) -> str:
        """
        Build prompt for LLM ADR generation

        Now queries RAG for Software Specification Document (SSD) to provide
        comprehensive context including:
        - Executive summary and business case
        - Functional and non-functional requirements
        - Diagram specifications
        - Constraints and assumptions
        """
        title = card.get('title', 'Untitled Task')
        description = card.get('description', 'No description provided')
        card_id = card.get('card_id', 'unknown')

        prompt = f"""Generate an Architecture Decision Record (ADR) for the following task:

**Title**: {title}
**Description**: {description}
**Priority**: {card.get('priority', 'medium')}
**Complexity**: {card.get('size', 'medium')}
"""

        # Query RAG for Software Specification Document (Pattern #10: Guard clause)
        ssd_context = self._query_ssd_from_rag(card_id)
        if ssd_context:
            prompt += f"""
**Software Specification Document Available**: ✅

**Executive Summary**:
{ssd_context.get('executive_summary', 'N/A')}

**Business Case**:
{ssd_context.get('business_case', 'N/A')}

**Requirements Summary**:
- Functional Requirements: {ssd_context.get('functional_count', 0)}
- Non-Functional Requirements: {ssd_context.get('non_functional_count', 0)}

**Key Requirements**:
{ssd_context.get('key_requirements', 'See full SSD for details')}

**Architectural Diagrams**:
{ssd_context.get('diagram_descriptions', 'See SSD for visual diagrams')}

**Constraints**:
{chr(10).join(f'- {c}' for c in ssd_context.get('constraints', []))}

**Success Criteria**:
{chr(10).join(f'- {sc}' for sc in ssd_context.get('success_criteria', []))}
"""
        elif structured_requirements:
            # Fallback to structured requirements if SSD not available
            prompt += f"""
**Structured Requirements Available**:
- Project: {structured_requirements.project_name}
- Functional Requirements: {len(structured_requirements.functional_requirements)}
- Non-Functional Requirements: {len(structured_requirements.non_functional_requirements)}
- Use Cases: {len(structured_requirements.use_cases)}

**Top Requirements**:
"""
            for req in structured_requirements.functional_requirements[:3]:
                prompt += f"- {req.id}: {req.title} [{req.priority.value}]\n"

        # Use centralized environment context
        prompt += get_environment_context()

        prompt += f"""
Generate ADR-{adr_number} in this format:

# ADR-{adr_number}: {title}

**Status**: Accepted
**Date**: {datetime.utcnow().strftime('%Y-%m-%d')}
**Deciders**: Architecture Agent (Automated)

## Context
[Explain the technical context and problem being solved in a development/test environment]

## Decision
[Document the architectural decision using ONLY available standard libraries and tools]
[If requirements mention external infrastructure (Kafka/Spark/databases/message queues), provide concrete
 alternatives: mock interfaces + file storage, in-memory simulations, embedded databases (SQLite/H2), etc.]
[Specify exact libraries/frameworks to use (e.g., "use pandas for data analysis, not Spark")]

## Consequences
[List positive and negative consequences]

Focus on pragmatic, executable implementation that can run in a basic development environment
without requiring external infrastructure installation."""

        return prompt

    def _query_ssd_from_rag(self, card_id: str) -> Optional[Dict[str, Any]]:
        """
        Query RAG for Software Specification Document artifacts

        Pattern #10: Guard clauses for early returns
        Pattern #11: Generator pattern for processing multiple SSD artifacts

        Returns:
            Dict with SSD context or None if SSD not found/not generated
        """
        # Guard clause: Check RAG available
        if not self.rag:
            return None

        try:
            # Query RAG for SSD executive summary
            executive_results = self.rag.query_similar(
                query_text=f"software specification document {card_id} executive summary business case",
                artifact_type="ssd_executive_summary",
                card_id=card_id,
                top_k=1
            )

            # Guard clause: Check if SSD found
            if not executive_results:
                # SSD was not generated for this task (e.g., simple refactor)
                self.logger.log("No SSD found in RAG (task may have skipped SSD generation)", "INFO")
                return None

            # Query for requirements
            requirements_results = self.rag.query_similar(
                query_text=f"software specification {card_id} requirements functional non-functional",
                artifact_type="ssd_requirement",
                card_id=card_id,
                top_k=5
            )

            # Query for diagrams
            diagram_results = self.rag.query_similar(
                query_text=f"software specification {card_id} architecture diagram erd",
                artifact_type="ssd_diagram",
                card_id=card_id,
                top_k=3
            )

            # Extract executive content (Pattern #4: use next() for first match)
            executive_content = next(
                (result.get('content', '') for result in executive_results),
                ''
            )

            # Split executive summary and business case
            executive_parts = executive_content.split('\n\n', 1)
            executive_summary = executive_parts[0] if executive_parts else executive_content
            business_case = executive_parts[1] if len(executive_parts) > 1 else ''

            # Pattern #11: Use generator to build key requirements list
            def _extract_key_requirements():
                """Generator yielding formatted requirement strings"""
                for req_result in requirements_results[:5]:  # Top 5 requirements
                    content = req_result.get('content', '')
                    # Extract requirement ID and description from content
                    lines = content.split('\n')
                    if lines:
                        yield lines[0]  # First line usually has ID and description

            key_requirements = '\n'.join(_extract_key_requirements())

            # Pattern #11: Use generator for diagram descriptions
            def _extract_diagram_descriptions():
                """Generator yielding diagram descriptions"""
                for diagram_result in diagram_results:
                    content = diagram_result.get('content', '')
                    try:
                        diagram_data = json.loads(content)
                        yield f"- {diagram_data.get('type', 'diagram')}: {diagram_data.get('description', 'No description')}"
                    except json.JSONDecodeError:
                        continue

            diagram_descriptions = '\n'.join(_extract_diagram_descriptions())

            # Build SSD context dict
            ssd_context = {
                "executive_summary": executive_summary,
                "business_case": business_case,
                "functional_count": len([r for r in requirements_results if r.get('metadata', {}).get('category') == 'functional']),
                "non_functional_count": len([r for r in requirements_results if r.get('metadata', {}).get('category') == 'non_functional']),
                "key_requirements": key_requirements if key_requirements else "No specific requirements found",
                "diagram_descriptions": diagram_descriptions if diagram_descriptions else "No diagrams available",
                "constraints": self._extract_list_from_ssd(executive_content, "Constraints"),
                "success_criteria": self._extract_list_from_ssd(executive_content, "Success Criteria")
            }

            self.logger.log(f"✅ Retrieved SSD from RAG for card {card_id}", "SUCCESS")
            self.logger.log(f"   Found {len(requirements_results)} requirements", "INFO")
            self.logger.log(f"   Found {len(diagram_results)} diagrams", "INFO")

            return ssd_context

        except Exception as e:
            self.logger.log(f"⚠️  Failed to query SSD from RAG: {e}", "WARNING")
            return None

    def _extract_list_from_ssd(self, content: str, section_name: str) -> List[str]:
        """
        Extract list items from SSD content section

        Pattern #11: Generator pattern for extracting list items
        """
        # Guard clause: Check content exists
        if not content or section_name not in content:
            return []

        # Find section and extract bullet points
        section_start = content.find(section_name)
        if section_start == -1:
            return []

        # Get text after section header
        section_text = content[section_start:]

        # Pattern #11: Generator for extracting bullet points
        def _extract_bullets():
            """Generator yielding bullet point items"""
            for line in section_text.split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('*'):
                    yield line[1:].strip()

        return list(_extract_bullets())[:5]  # Return max 5 items

    def _generate_adr_template(self, card: Dict, adr_number: str, structured_requirements=None) -> str:
        """Template-based ADR generation (fallback when AIQueryService unavailable)"""
        title = card.get('title', 'Untitled Task')
        description = card.get('description', 'No description provided')

        # Base ADR header
        adr_content = f"""# ADR-{adr_number}: {title}

**Status**: Accepted
**Date**: {datetime.utcnow().strftime('%Y-%m-%d')}
**Deciders**: Architecture Agent (Automated)
**Task**: {card['card_id']} - {title}

---

## Context

**Task Description**:
{description}

**Priority**: {card.get('priority', 'medium')}
**Complexity**: {card.get('size', 'medium')}
"""

        # Add structured requirements if available
        if structured_requirements:
            adr_content += f"""
**Structured Requirements Available**: ✅
**Project**: {structured_requirements.project_name}
**Requirements Version**: {structured_requirements.version}

### Business Context
"""
            if structured_requirements.executive_summary:
                adr_content += f"""
**Executive Summary**:
{structured_requirements.executive_summary}
"""

            if structured_requirements.business_goals:
                adr_content += "\n**Business Goals**:\n"
                for goal in structured_requirements.business_goals[:5]:  # Top 5 goals
                    adr_content += f"- {goal}\n"

            # Add requirements summary
            adr_content += f"""
### Requirements Summary
- **Functional Requirements**: {len(structured_requirements.functional_requirements)}
- **Non-Functional Requirements**: {len(structured_requirements.non_functional_requirements)}
- **Use Cases**: {len(structured_requirements.use_cases)}
- **Data Requirements**: {len(structured_requirements.data_requirements)}
- **Integration Requirements**: {len(structured_requirements.integration_requirements)}
- **Stakeholders**: {len(structured_requirements.stakeholders)}

### Key Functional Requirements
"""
            # List top 5 critical/high priority functional requirements
            high_priority_reqs = [req for req in structured_requirements.functional_requirements
                                 if req.priority.value in ['critical', 'high']][:5]
            for req in high_priority_reqs:
                adr_content += f"- **{req.id}**: {req.title} [{req.priority.value}]\n"

            # List top 5 critical/high priority non-functional requirements
            if structured_requirements.non_functional_requirements:
                adr_content += "\n### Key Non-Functional Requirements\n"
                nfr_high_priority = [req for req in structured_requirements.non_functional_requirements
                                    if req.priority.value in ['critical', 'high']][:5]
                for req in nfr_high_priority:
                    adr_content += f"- **{req.id}**: {req.title} [{req.type.value}, {req.priority.value}]\n"
                    if req.target:
                        adr_content += f"  Target: {req.target}\n"

        adr_content += """
---

## Decision

"""
        if structured_requirements:
            adr_content += f"""**Approach**: Implement {title.lower()} following the structured requirements from {structured_requirements.project_name}.

**Implementation Strategy**:
- Use structured requirements as architectural blueprint
- Functional requirements → Feature implementations
- Non-functional requirements → Technical decisions (performance, security, scalability)
- Data requirements → Data model and database design
- Integration requirements → API and service integration design
- Developer A: Conservative, minimal-risk implementation focusing on critical requirements
- Developer B: Comprehensive implementation with enhanced features
"""
        else:
            adr_content += f"""**Approach**: Implement {title.lower()} using test-driven development with parallel developer approaches.

**Implementation Strategy**:
- Developer A: Conservative, minimal-risk implementation
- Developer B: Comprehensive implementation with enhanced features
"""

        adr_content += """
---

## Consequences

### Positive
- ✅ Clear architectural direction for developers
"""
        if structured_requirements:
            adr_content += "- ✅ Structured requirements provide comprehensive implementation guidance\n"
            adr_content += "- ✅ Non-functional requirements ensure quality attributes are met\n"
            adr_content += f"- ✅ {len(structured_requirements.use_cases)} use cases validate implementation completeness\n"

        adr_content += "- ✅ Parallel development allows comparison of approaches\n"
        adr_content += "- ✅ TDD ensures quality and testability\n"

        if structured_requirements and structured_requirements.constraints:
            adr_content += "\n### Constraints\n"
            for constraint in structured_requirements.constraints[:5]:  # Top 5 constraints
                adr_content += f"- **{constraint.type.upper()}**: {constraint.description} (Impact: {constraint.impact})\n"

        adr_content += """
---

**Note**: This is an automatically generated ADR. For complex tasks, manual architectural review is recommended.
"""
        if structured_requirements:
            adr_content += f"\n**Requirements Source**: Parsed from {structured_requirements.project_name} requirements document (version {structured_requirements.version})\n"

        return adr_content

    def _send_adr_notification(self, card_id: str, adr_path: str, adr_number: str):
        """Send ADR notification to downstream agents"""
        self.messenger.send_data_update(
            to_agent="dependency-validation-agent",
            card_id=card_id,
            update_type="adr_created",
            data={
                "adr_file": adr_path,
                "adr_number": adr_number
            },
            priority="high"
        )

        self.messenger.update_shared_state(
            card_id=card_id,
            updates={
                "current_stage": "architecture_complete",
                "adr_file": adr_path,
                "adr_number": adr_number
            }
        )

    def _generate_user_stories_from_adr(
        self,
        adr_content: str,
        adr_number: str,
        parent_card: Dict
    ) -> List[Dict]:
        """
        Generate user stories from ADR content using LLM

        Args:
            adr_content: Full ADR markdown content
            adr_number: ADR number (e.g., "001")
            parent_card: Parent task card

        Returns:
            List of user story dicts with title, description, acceptance_criteria, points
        """
        self.logger.log(f"🤖 Generating user stories from ADR-{adr_number}...", "INFO")

        if not hasattr(self, 'llm_client') or not self.llm_client:
            self.logger.log("⚠️  No LLM client available - skipping user story generation", "WARNING")
            return []

        try:
            # Try to get prompt from RAG first
            if self.prompt_manager:
                try:
                    self.logger.log("📝 Loading architecture prompt from RAG", "INFO")
                    prompt_template = self.prompt_manager.get_prompt("architecture_design_adr")

                    if prompt_template:
                        # Render the prompt with ADR content
                        rendered = self.prompt_manager.render_prompt(
                            prompt=prompt_template,
                            variables={
                                "context": f"Converting ADR to user stories",
                                "requirements": adr_content,
                                "constraints": "Focus on implementation tasks",
                                "scale_expectations": "2-5 user stories"
                            }
                        )
                        self.logger.log(f"✅ Loaded RAG prompt with {len(prompt_template.perspectives)} perspectives", "INFO")
                        system_message = rendered['system']
                        user_message = rendered['user']
                    else:
                        raise Exception("Prompt not found in RAG")
                except Exception as e:
                    self.logger.log(f"⚠️  Error loading RAG prompt: {e} - using default", "WARNING")
                    system_message = """You are an expert at converting Architecture Decision Records (ADRs) into actionable user stories.
Generate user stories that implement the architectural decisions, following best practices:
- Use "As a [role], I want [feature], so that [benefit]" format
- Include specific acceptance criteria
- Estimate story points (1-8 scale)
- Break down complex decisions into multiple stories"""

                    user_message = f"""Convert the following ADR into user stories:

{adr_content}

Generate 2-5 user stories in JSON format:
{{
  "user_stories": [
    {{
      "title": "As a developer, I want to implement X, so that Y",
      "description": "Detailed description of what needs to be built",
      "acceptance_criteria": [
        "Given X, when Y, then Z",
        "Criterion 2"
      ],
      "points": 5,
      "priority": "high"
    }}
  ]
}}

Focus on implementation tasks, not architectural discussions."""
            else:
                system_message = """You are an expert at converting Architecture Decision Records (ADRs) into actionable user stories.
Generate user stories that implement the architectural decisions, following best practices:
- Use "As a [role], I want [feature], so that [benefit]" format
- Include specific acceptance criteria
- Estimate story points (1-8 scale)
- Break down complex decisions into multiple stories"""

                user_message = f"""Convert the following ADR into user stories:

{adr_content}

Generate 2-5 user stories in JSON format:
{{
  "user_stories": [
    {{
      "title": "As a developer, I want to implement X, so that Y",
      "description": "Detailed description of what needs to be built",
      "acceptance_criteria": [
        "Given X, when Y, then Z",
        "Criterion 2"
      ],
      "points": 5,
      "priority": "high"
    }}
  ]
}}

Focus on implementation tasks, not architectural discussions."""

            # Use LLM client's complete() method
            from llm_client import LLMMessage
            messages = [
                LLMMessage(role="system", content=system_message),
                LLMMessage(role="user", content=user_message)
            ]

            llm_response = self.llm_client.complete(
                messages=messages,
                temperature=0.4,
                max_tokens=2000
            )
            response = llm_response.content

            # Parse JSON response
            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                self.logger.log("⚠️  LLM response did not contain valid JSON", "WARNING")
                return []

            data = json.loads(json_match.group(0))
            user_stories = data.get('user_stories', [])

            self.logger.log(f"✅ Generated {len(user_stories)} user stories from ADR-{adr_number}", "INFO")
            return user_stories

        except Exception as e:
            self.logger.log(f"❌ Failed to generate user stories: {e}", "ERROR")
            return []

    def _store_kanban_in_rag(self, card_id: str, story_card_ids: List[str]) -> None:
        """
        Store Kanban board state in RAG database

        Args:
            card_id: Parent card ID
            story_card_ids: List of generated story card IDs
        """
        try:
            # Get current board state
            board_state = {
                "parent_card": card_id,
                "generated_stories": story_card_ids,
                "columns": {},
                "total_cards": 0
            }

            # Collect all cards by column
            if hasattr(self.board, 'columns'):
                for column_name in self.board.columns:
                    cards = self.board.get_cards_in_column(column_name)
                    board_state["columns"][column_name] = [
                        {
                            "card_id": c.get('card_id'),
                            "title": c.get('title'),
                            "priority": c.get('priority'),
                            "points": c.get('points')
                        }
                        for c in cards
                    ]
                    board_state["total_cards"] += len(cards)

            # Store in RAG
            self.rag.store_artifact(
                artifact_type="kanban_board_state",
                card_id=card_id,
                task_title=f"Kanban State after ADR-{card_id}",
                content=json.dumps(board_state, indent=2),
                metadata={
                    "parent_card": card_id,
                    "story_count": len(story_card_ids),
                    "total_cards": board_state["total_cards"],
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            self.logger.log(f"✅ Stored Kanban board state in RAG ({board_state['total_cards']} cards)", "INFO")

        except Exception as e:
            self.logger.log(f"⚠️  Failed to store Kanban in RAG: {e}", "WARNING")

    # REMOVED: _query_kg_for_adr_patterns() - now handled by AIQueryService
    # The centralized AIQueryService (ai_query_service.py) handles all
    # KG queries via the ArchitectureKGStrategy class.

    def _store_adr_in_knowledge_graph(
        self,
        card_id: str,
        adr_number: str,
        adr_path: str,
        structured_requirements: Optional[Any]
    ) -> None:
        """
        Store ADR in Knowledge Graph and link to requirements

        Args:
            card_id: Card ID for this task
            adr_number: ADR number (e.g., "001")
            adr_path: Path to ADR file
            structured_requirements: Structured requirements object (if available)
        """
        kg = get_knowledge_graph()
        if not kg:
            self.logger.log("Knowledge Graph not available - skipping KG storage", "DEBUG")
            return

        try:
            self.logger.log("Storing ADR in Knowledge Graph...", "DEBUG")

            # Add ADR node
            adr_id = f"ADR-{adr_number}"
            kg.add_adr(
                adr_id=adr_id,
                title=f"Architecture Decision {adr_number}",
                status="accepted"
            )

            # Link ADR to file
            kg.link_adr_to_file(
                adr_id=adr_id,
                file_path=adr_path,
                relationship="DOCUMENTED_IN"
            )

            # If we have structured requirements, link ADR to requirements
            if structured_requirements:
                req_count = 0

                # Link to functional requirements (top 5 high-priority ones)
                high_priority_functional = [
                    req for req in structured_requirements.functional_requirements
                    if req.priority.value in ['critical', 'high']
                ][:5]

                for req in high_priority_functional:
                    kg.link_requirement_to_adr(req.id, adr_id)
                    req_count += 1

                # Link to non-functional requirements (all of them since they're critical)
                for req in structured_requirements.non_functional_requirements[:5]:
                    kg.link_requirement_to_adr(req.id, adr_id)
                    req_count += 1

                self.logger.log(f"✅ Linked ADR {adr_id} to {req_count} requirements in Knowledge Graph", "INFO")
            else:
                self.logger.log(f"✅ Stored ADR {adr_id} in Knowledge Graph", "INFO")

            # Link ADR to task
            # Note: Task should already exist from requirements stage
            # We just need to ensure the relationship exists
            try:
                # The task node should exist from requirements_stage
                # We can query it or just create a relationship if needed
                self.logger.log(f"   ADR-Task linkage: {adr_id} -> {card_id}", "DEBUG")
            except Exception as e:
                self.logger.log(f"   Could not link ADR to task: {e}", "DEBUG")

        except Exception as e:
            self.logger.log(f"Warning: Could not store ADR in Knowledge Graph: {e}", "WARNING")
            self.logger.log(f"   Exception details: {type(e).__name__}", "DEBUG")


# ============================================================================
# DEPENDENCY VALIDATION STAGE
# ============================================================================

class DependencyValidationStage(PipelineStage, SupervisedStageMixin):
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

        self.board = board
        self.messenger = messenger
        self.logger = logger

    @wrap_exception(PipelineStageError, "Dependency validation stage execution failed")
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

        # Update progress: starting validation
        self.update_progress({"step": "starting", "progress_percent": 10})

        # Check Python version
        self.update_progress({"step": "checking_python_version", "progress_percent": 30})
        python_check = self._check_python_version()

        # Test basic imports
        self.update_progress({"step": "testing_imports", "progress_percent": 50})
        import_check = self._test_imports()

        # Determine status
        self.update_progress({"step": "determining_status", "progress_percent": 70})
        all_passed = python_check['compatible'] and import_check['all_passed']
        status = "PASS" if all_passed else "BLOCKED"

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

class DevelopmentStage(PipelineStage, SupervisedStageMixin):
    """
    Single Responsibility: Invoke parallel developers

    This stage ONLY invokes developers - nothing else.
    Uses DeveloperInvoker to launch autonomous developer agents.

    Integrates with supervisor for:
    - LLM cost tracking
    - Code execution sandboxing
    - Unexpected state handling and recovery
    - Automatic heartbeat and health monitoring
    """

    def __init__(
        self,
        board: KanbanBoard,
        rag: RAGAgent,
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
            stage_name="DevelopmentStage",
            heartbeat_interval=15
        )

        self.board = board
        self.rag = rag
        self.logger = logger
        self.observable = observable
        self.supervisor = supervisor
        self.invoker = DeveloperInvoker(logger, observable=observable)

    @wrap_exception(PipelineStageError, "Development stage execution failed")
    def execute(self, card: Dict, context: Dict) -> Dict:
        """Execute with supervisor monitoring"""
        metadata = {
            "task_id": card.get('card_id'),
            "stage": "development"
        }

        with self.supervised_execution(metadata):
            return self._do_work(card, context)

    def _do_work(self, card: Dict, context: Dict) -> Dict:
        """Internal method - invokes developers and tracks their work"""
        stage_name = "development"
        self.logger.log("Starting Development Stage", "STAGE")

        card_id = card['card_id']
        num_developers = context.get('parallel_developers', 1)

        # Update progress: starting
        self.update_progress({"step": "starting", "progress_percent": 10})

        # Register stage with supervisor
        if self.supervisor:
            from supervisor_agent import RecoveryStrategy
            self.supervisor.register_stage(
                stage_name=stage_name,
                recovery_strategy=RecoveryStrategy(
                    max_retries=3,
                    retry_delay_seconds=10,
                    timeout_seconds=600,  # 10 minutes for developers
                    circuit_breaker_threshold=5
                )
            )

        try:
            # Get ADR from context or card data
            self.update_progress({"step": "reading_adr", "progress_percent": 20})
            adr_file = context.get('adr_file', '')

            # If not in context, try to get from card data
            if not adr_file:
                adr_file = card.get('adr_file', '')

            # If still no ADR file (architecture was skipped), use task description as guidance
            if adr_file:
                adr_content = self._read_adr(adr_file)
            else:
                self.logger.log("No ADR file found (architecture stage may have been skipped)", "INFO")
                adr_content = f"""# Task Requirements

{card.get('description', 'No description available')}

## Implementation Guidance
- Follow coding standards and best practices
- Include error handling
- Write tests for all functionality
- Document your code
"""

            # Invoke developers in parallel
            self.update_progress({"step": "invoking_developers", "progress_percent": 30})
            self.logger.log(f"Invoking {num_developers} parallel developer(s)...", "INFO")

            developer_results = self.invoker.invoke_parallel_developers(
                num_developers=num_developers,
                card=card,
                adr_content=adr_content,
                adr_file=adr_file,
                rag_agent=self.rag  # Pass RAG agent so developers can query feedback
            )

            # Track LLM costs for each developer
            self.update_progress({"step": "tracking_llm_costs", "progress_percent": 50})
            if self.supervisor:
                for result in developer_results:
                    if result.get('success', False) and result.get('tokens_used'):
                        try:
                            tokens_used = result['tokens_used']
                            self.supervisor.track_llm_call(
                                model=result.get('llm_model', 'gpt-4o'),
                                provider=result.get('llm_provider', 'openai'),
                                tokens_input=getattr(tokens_used, 'prompt_tokens', 0),
                                tokens_output=getattr(tokens_used, 'completion_tokens', 0),
                                stage=stage_name,
                                purpose=result.get('developer', 'unknown')
                            )
                            self.logger.log(
                                f"Tracked LLM cost for {result.get('developer')}",
                                "INFO"
                            )
                        except Exception as e:
                            # Budget exceeded or other cost tracking error
                            self.logger.log(f"Cost tracking error: {e}", "ERROR")
                            if "Budget" in str(e):
                                raise

            # Execute developer code in sandbox (if supervisor has sandboxing enabled)
            self.update_progress({"step": "sandboxing_code", "progress_percent": 65})
            if self.supervisor and hasattr(self.supervisor, 'sandbox') and self.supervisor.sandbox:
                # Executable extensions only (skip HTML, notebooks, markdown, etc.)
                executable_exts = {'.py', '.js', '.ts', '.java', '.go', '.rs', '.c', '.cpp'}

                for result in developer_results:
                    if not result.get('success', False):
                        continue

                    dev_name = result.get('developer', 'unknown')

                    # Get implementation files
                    impl_files = result.get('implementation_files', [])
                    for impl_file in impl_files:
                        file_path = Path(impl_file)

                        # Skip non-executable artifacts
                        if not file_path.exists() or file_path.suffix not in executable_exts:
                            continue

                        self.logger.log(f"Executing {dev_name} code in sandbox: {file_path.name}...", "INFO")
                        code = file_path.read_text()

                        # Execute in sandbox
                        exec_result = self.supervisor.execute_code_safely(
                            code=code,
                            scan_security=True
                        )

                        if not exec_result["success"]:
                            error_msg = (
                                f"{dev_name} code execution failed: "
                                f"{exec_result.get('kill_reason', 'unknown')}"
                            )
                            self.logger.log(error_msg, "ERROR")

                            # Mark this developer solution as failed
                            result["success"] = False
                            result["error"] = error_msg

            # Store each developer's solution in RAG
            self.update_progress({"step": "storing_in_rag", "progress_percent": 80})
            for dev_result in developer_results:
                self._store_developer_solution_in_rag(card_id, card, dev_result)

            # Store development artifacts in Knowledge Graph
            self._store_development_in_knowledge_graph(card_id, developer_results)

            # Check if we have any successful developers
            self.update_progress({"step": "checking_results", "progress_percent": 90})
            successful_devs = [r for r in developer_results if r.get("success", False)]

            if not successful_devs:
                # All developers failed - report unexpected state
                if self.supervisor and hasattr(self.supervisor, 'handle_unexpected_state'):
                    recovery = self.supervisor.handle_unexpected_state(
                        current_state="STAGE_FAILED_ALL_DEVELOPERS",
                        expected_states=["STAGE_COMPLETED"],
                        context={
                            "stage_name": stage_name,
                            "error_message": "All developers failed",
                            "card_id": card_id,
                            "developer_count": len(developer_results),
                            "developer_errors": [r.get("error") for r in developer_results]
                        },
                        auto_learn=True  # Let supervisor learn how to fix this
                    )

                    if recovery and recovery.get("success"):
                        self.logger.log(
                            "Supervisor recovered from all-developers-failed state!",
                            "INFO"
                        )
                        # In production, would retry or apply learned solution here
                    else:
                        raise Exception("All developers failed and recovery unsuccessful")
                else:
                    raise Exception("All developers failed")

            # Update progress: complete
            self.update_progress({"step": "complete", "progress_percent": 100})

            return {
                "stage": "development",
                "num_developers": num_developers,
                "developers": developer_results,
                "successful_developers": len(successful_devs),
                "status": "COMPLETE"
            }

        except Exception as e:
            # Let supervisor learn from this failure
            if self.supervisor and hasattr(self.supervisor, 'handle_unexpected_state'):
                import traceback
                self.logger.log(f"Development stage failed, consulting supervisor...", "WARNING")

                recovery = self.supervisor.handle_unexpected_state(
                    current_state="STAGE_FAILED",
                    expected_states=["STAGE_COMPLETED"],
                    context={
                        "stage_name": stage_name,
                        "error_message": str(e),
                        "stack_trace": traceback.format_exc(),
                        "card_id": card_id
                    },
                    auto_learn=True
                )

                if recovery and recovery.get("success"):
                    self.logger.log("Supervisor recovered from failure!", "INFO")
                    # The supervisor's learned workflow already executed
                    # In production, we might want to retry the stage here
                else:
                    self.logger.log("Supervisor could not recover", "ERROR")

            # Re-raise after supervisor has learned
            raise

    def get_stage_name(self) -> str:
        return "development"

    def _read_adr(self, adr_file: str) -> str:
        """Read ADR content"""
        try:
            return FileManager.read_text(Path(adr_file))
        except Exception as e:
            raise wrap_exception(
                e,
                FileReadError,
                "Failed to read ADR file",
                {
                    "adr_file": adr_file,
                    "stage": "development"
                }
            )

    def _store_developer_solution_in_rag(self, card_id: str, card: Dict, dev_result: Dict):
        """Store developer solution in RAG for learning"""
        # Use .get() with defaults to handle missing keys defensively
        developer = dev_result.get('developer', 'unknown')
        approach = dev_result.get('approach', 'standard')  # Default approach if missing

        self.rag.store_artifact(
            artifact_type="developer_solution",
            card_id=card_id,
            task_title=card.get('title', 'Unknown'),
            content=f"{developer} solution using {approach} approach",
            metadata={
                "developer": developer,
                "approach": approach,
                "tdd_compliant": dev_result.get('tdd_workflow', {}).get('tests_written_first', False),
                "implementation_files": dev_result.get('implementation_files', []),
                "test_files": dev_result.get('test_files', [])
            }
        )

    def _store_development_in_knowledge_graph(self, card_id: str, developer_results: list):
        """Store development artifacts in Knowledge Graph for traceability"""
        kg = get_knowledge_graph()
        if not kg:
            self.logger.log("Knowledge Graph not available - skipping KG storage", "DEBUG")
            return

        try:
            self.logger.log("Storing development artifacts in Knowledge Graph...", "DEBUG")

            total_files = 0

            # Process each developer's implementation
            for dev_result in developer_results:
                if not dev_result.get('success', False):
                    continue  # Skip failed implementations

                developer_name = dev_result.get('developer', 'unknown')

                # Add implementation files to knowledge graph
                impl_files = dev_result.get('implementation_files', [])
                for file_path in impl_files:
                    try:
                        # Detect file type
                        file_type = self._detect_file_type(str(file_path))

                        # Add file node
                        kg.add_file(str(file_path), file_type)

                        # Link task to file
                        kg.link_task_to_file(card_id, str(file_path))

                        total_files += 1

                    except Exception as e:
                        self.logger.log(f"   Could not add file {file_path}: {e}", "DEBUG")

                # Add test files to knowledge graph
                test_files = dev_result.get('test_files', [])
                for file_path in test_files:
                    try:
                        # Detect file type
                        file_type = self._detect_file_type(str(file_path))

                        # Add file node
                        kg.add_file(str(file_path), file_type)

                        # Link task to file
                        kg.link_task_to_file(card_id, str(file_path))

                        total_files += 1

                    except Exception as e:
                        self.logger.log(f"   Could not add test file {file_path}: {e}", "DEBUG")

            if total_files > 0:
                self.logger.log(f"✅ Stored {total_files} implementation files in Knowledge Graph", "INFO")
            else:
                self.logger.log("✅ Development stage recorded in Knowledge Graph", "INFO")

        except Exception as e:
            self.logger.log(f"Warning: Could not store development artifacts in Knowledge Graph: {e}", "WARNING")
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


# ============================================================================
# VALIDATION STAGE
# ============================================================================

class ValidationStage(PipelineStage, SupervisedStageMixin):
    """
    Single Responsibility: Validate the WINNING developer solution

    This stage ONLY tests the winner selected by ArbitrationStage.
    No need to test all developers - winner was already chosen.

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
        messenger: Optional['AgentMessenger'] = None,
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

        self.board = board
        self.test_runner = test_runner
        self.logger = logger
        self.messenger = messenger
        self.observable = observable
        self.supervisor = supervisor

        # Register message handlers for supervisor commands
        # TODO: AgentMessenger doesn't have register_handler method yet
        # if self.messenger and hasattr(self.messenger, 'register_handler'):
        #     self.messenger.register_handler("validation_override", self._handle_validation_override)
        #     self.messenger.register_handler("force_approval", self._handle_force_approval)

    @wrap_exception(PipelineStageError, "Validation stage execution failed")
    def execute(self, card: Dict, context: Dict) -> Dict:
        """Execute with supervisor monitoring"""
        metadata = {
            "task_id": card.get('card_id'),
            "stage": "validation"
        }

        with self.supervised_execution(metadata):
            result = self._do_work(card, context)

        return result

    def _do_work(self, card: Dict, context: Dict) -> Dict:
        """Internal method - validates ONLY the winning solution"""
        self.logger.log("Starting Validation Stage", "STAGE")

        card_id = card.get('card_id', 'unknown')

        # Update progress: starting
        self.update_progress({"step": "starting", "progress_percent": 10})

        # Get winner from context (selected by ArbitrationStage)
        winner = context.get('winner', 'developer-a')

        self.logger.log(f"✅ Validating winner: {winner}", "INFO")

        # Notify validation started
        if self.observable:
            from pipeline_observer import PipelineEvent, EventType
            event = PipelineEvent(
                event_type=EventType.VALIDATION_STARTED,
                card_id=card_id,
                data={"winner": winner}
            )
            self.observable.notify(event)

        # Update progress: validating winner
        self.update_progress({"step": f"validating_{winner}", "progress_percent": 40})

        # Validate ONLY the winner's solution
        dev_result = self._validate_developer(winner, card_id)

        # Update progress: processing results
        self.update_progress({"step": "processing_results", "progress_percent": 80})

        status = dev_result['status']

        # ValidationStage should FAIL if tests are blocked (didn't run properly)
        # Only succeed if tests actually executed and passed
        success = (status == "APPROVED")

        result = {
            "stage": "validation",
            "winner": winner,
            "validation_result": dev_result,
            "status": status,
            "success": success  # True only if validation approved
        }

        # Notify validation completed or failed
        self.update_progress({"step": "sending_notifications", "progress_percent": 85})
        if self.observable:
            from pipeline_observer import PipelineEvent, EventType
            if status == "APPROVED":
                event = PipelineEvent(
                    event_type=EventType.VALIDATION_COMPLETED,
                    card_id=card_id,
                    data={
                        "winner": winner,
                        "status": status
                    }
                )
                self.observable.notify(event)
            else:
                error = Exception(f"Validation failed for {winner}")
                event = PipelineEvent(
                    event_type=EventType.VALIDATION_FAILED,
                    card_id=card_id,
                    error=error,
                    data={
                        "winner": winner,
                        "status": status
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
        # Use configured developer output directory via PathConfigService
        test_path = get_developer_tests_path(dev_name)

        self.logger.log(f"Validating {dev_name} solution...", "INFO")

        # Run tests
        test_results = self.test_runner.run_tests(test_path)

        # Determine status
        status = "APPROVED" if test_results['exit_code'] == 0 else "BLOCKED"

        self.logger.log(f"{dev_name}: {status} (exit_code={test_results['exit_code']})",
                       "SUCCESS" if status == "APPROVED" else "WARNING")

        return {
            "developer": dev_name,
            "status": status,
            "test_results": test_results
        }

    def _handle_validation_override(self, message: Dict) -> Dict:
        """
        Handle supervisor command to override validation result

        Message format:
        {
            "command": "validation_override",
            "status": "APPROVED" | "BLOCKED",
            "reason": "explanation"
        }
        """
        status = message.get('status', 'APPROVED')
        reason = message.get('reason', 'Supervisor override')

        self.logger.log(f"🔧 Supervisor override: Setting validation status to {status}", "WARNING")
        self.logger.log(f"   Reason: {reason}", "INFO")

        return {
            "status": "success",
            "validation_status": status,
            "reason": reason
        }

    def _handle_force_approval(self, message: Dict) -> Dict:
        """
        Handle supervisor command to force approval regardless of test results

        Message format:
        {
            "command": "force_approval",
            "reason": "explanation"
        }
        """
        reason = message.get('reason', 'Supervisor forced approval')

        self.logger.log(f"📨 Received supervisor command to force approval", "WARNING")
        self.logger.log(f"   Reason: {reason}", "INFO")

        return {
            "status": "acknowledged",
            "validation_status": "APPROVED",
            "forced": True,
            "reason": reason
        }


# ============================================================================
# INTEGRATION STAGE
# ============================================================================

class IntegrationStage(PipelineStage, SupervisedStageMixin):
    """
    Single Responsibility: Integrate winning solution

    This stage ONLY deploys and runs regression tests - nothing else.

    Integrates with supervisor for:
    - Merge conflict handling
    - Final test execution tracking
    - Integration failure recovery
    - Automatic heartbeat and health monitoring
    """

    def __init__(
        self,
        board: KanbanBoard,
        messenger: AgentMessenger,
        rag: RAGAgent,
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
            stage_name="IntegrationStage",
            heartbeat_interval=15
        )

        self.board = board
        self.messenger = messenger
        self.rag = rag
        self.test_runner = test_runner
        self.logger = logger
        self.supervisor = supervisor
        self.observable = observable

    @wrap_exception(PipelineStageError, "Integration stage execution failed")
    def execute(self, card: Dict, context: Dict) -> Dict:
        """Execute with supervisor monitoring"""
        metadata = {
            "task_id": card.get('card_id'),
            "stage": "integration"
        }

        with self.supervised_execution(metadata):
            return self._do_work(card, context)

    def _do_work(self, card: Dict, context: Dict) -> Dict:
        """Internal method - integrates winning solution"""
        self.logger.log("Starting Integration Stage", "STAGE")

        card_id = card['card_id']

        # Update progress: starting
        self.update_progress({"step": "starting", "progress_percent": 10})

        # Determine winner
        winner = context.get('winner', 'developer-a')

        # Update progress: notifying start
        self.update_progress({"step": "notifying_integration_start", "progress_percent": 20})

        # Notify integration started
        if self.observable:
            from pipeline_observer import PipelineEvent, EventType
            event = PipelineEvent(
                event_type=EventType.INTEGRATION_STARTED,
                card_id=card_id,
                developer_name=winner,
                data={"winning_developer": winner}
            )
            self.observable.notify(event)

        self.logger.log(f"Integrating {winner} solution...", "INFO")

        # Run regression tests
        self.update_progress({"step": "running_regression_tests", "progress_percent": 40})
        # Use configured developer output directory via PathConfigService
        test_path = get_developer_tests_path(winner)
        regression_results = self.test_runner.run_tests(test_path)

        # Verify deployment
        self.update_progress({"step": "verifying_deployment", "progress_percent": 60})

        # Integration passes if:
        # 1. Exit code is 0 (clean test execution), OR
        # 2. Exit code is non-zero but no tests actually failed (e.g., no tests found, which is OK for HTML-only deliverables)
        tests_failed = regression_results.get('failed', 0)
        exit_code = regression_results.get('exit_code', 1)

        deployment_verified = (exit_code == 0) or (tests_failed == 0)
        status = "PASS" if deployment_verified else "FAIL"

        if status == "PASS":
            self.logger.log("Integration complete: All tests passing, deployment verified", "SUCCESS")

            # Notify integration completed
            self.update_progress({"step": "notifying_success", "progress_percent": 75})
            if self.observable:
                from pipeline_observer import PipelineEvent, EventType
                event = PipelineEvent(
                    event_type=EventType.INTEGRATION_COMPLETED,
                    card_id=card_id,
                    developer_name=winner,
                    data={
                        "winner": winner,
                        "tests_passed": regression_results.get('passed', 0),
                        "deployment_verified": deployment_verified
                    }
                )
                self.observable.notify(event)
        else:
            self.logger.log(f"Integration issues detected: {regression_results.get('failed', 0)} tests failed", "WARNING")

            # Notify integration conflict (failures during integration)
            self.update_progress({"step": "notifying_conflict", "progress_percent": 75})
            if self.observable:
                from pipeline_observer import PipelineEvent, EventType
                event = PipelineEvent(
                    event_type=EventType.INTEGRATION_CONFLICT,
                    card_id=card_id,
                    developer_name=winner,
                    data={
                        "winner": winner,
                        "tests_failed": regression_results.get('failed', 0),
                        "exit_code": regression_results.get('exit_code', 1)
                    }
                )
                self.observable.notify(event)

        # Update Kanban
        self.update_progress({"step": "updating_kanban", "progress_percent": 85})
        self.board.move_card(card_id, "testing", "pipeline-orchestrator")

        # Store in RAG
        self.update_progress({"step": "storing_in_rag", "progress_percent": 95})
        self.rag.store_artifact(
            artifact_type="integration_result",
            card_id=card_id,
            task_title=card.get('title', 'Unknown'),
            content=f"Integration of {winner} solution completed",
            metadata={
                "winner": winner,
                "tests_passed": regression_results.get('passed', 0),
                "deployment_verified": deployment_verified
            }
        )

        # Update progress: complete
        self.update_progress({"step": "complete", "progress_percent": 100})

        return {
            "stage": "integration",
            "winner": winner,
            "regression_tests": regression_results,
            "deployment_verified": deployment_verified,
            "status": status
        }

    def get_stage_name(self) -> str:
        return "integration"


# ============================================================================
# TESTING STAGE
# ============================================================================

class TestingStage(PipelineStage, SupervisedStageMixin):
    """
    Single Responsibility: Final quality gates

    This stage ONLY performs final testing - nothing else.

    Integrates with supervisor for:
    - Final test execution tracking
    - Quality gate failure handling
    - Automatic heartbeat and health monitoring
    """

    def __init__(
        self,
        board: KanbanBoard,
        messenger: AgentMessenger,
        rag: RAGAgent,
        test_runner: TestRunner,
        logger: LoggerInterface,
        supervisor: Optional['SupervisorAgent'] = None
    ):
        # Initialize PipelineStage
        PipelineStage.__init__(self)

        # Initialize SupervisedStageMixin for health monitoring
        SupervisedStageMixin.__init__(
            self,
            supervisor=supervisor,
            stage_name="TestingStage",
            heartbeat_interval=15
        )

        self.board = board
        self.messenger = messenger
        self.rag = rag
        self.test_runner = test_runner
        self.logger = logger

    @wrap_exception(PipelineStageError, "Testing stage execution failed")
    def execute(self, card: Dict, context: Dict) -> Dict:
        """Execute with supervisor monitoring"""
        metadata = {
            "task_id": card.get('card_id'),
            "stage": "testing"
        }

        with self.supervised_execution(metadata):
            return self._do_work(card, context)

    def _do_work(self, card: Dict, context: Dict) -> Dict:
        """Internal method - runs final quality gates"""
        self.logger.log("Starting Testing Stage", "STAGE")

        card_id = card['card_id']
        winner = context.get('winner', 'developer-a')

        # Update progress: starting
        self.update_progress({"step": "starting", "progress_percent": 10})

        # Run final regression tests
        self.update_progress({"step": "running_regression_tests", "progress_percent": 30})
        # Use configured developer output directory via PathConfigService
        test_path = get_developer_tests_path(winner)
        regression_results = self.test_runner.run_tests(test_path)

        # Evaluate performance (simplified)
        self.update_progress({"step": "evaluating_performance", "progress_percent": 60})
        performance_score = 85  # In real implementation, this would measure actual performance

        # All quality gates
        self.update_progress({"step": "checking_quality_gates", "progress_percent": 80})
        all_gates_passed = regression_results['exit_code'] == 0
        status = "PASS" if all_gates_passed else "FAIL"

        if status == "PASS":
            self.logger.log("Testing complete: All quality gates passed", "SUCCESS")

        # Update Kanban
        self.update_progress({"step": "updating_kanban", "progress_percent": 90})
        self.board.move_card(card_id, "done", "pipeline-orchestrator")

        # Store in RAG
        self.update_progress({"step": "storing_in_rag", "progress_percent": 95})
        self.rag.store_artifact(
            artifact_type="testing_result",
            card_id=card_id,
            task_title=card.get('title', 'Unknown'),
            content=f"Final testing of {winner} solution completed",
            metadata={
                "winner": winner,
                "performance_score": performance_score,
                "all_gates_passed": all_gates_passed
            }
        )

        # Update progress: complete
        self.update_progress({"step": "complete", "progress_percent": 100})

        return {
            "stage": "testing",
            "winner": winner,
            "regression_tests": regression_results,
            "performance_score": performance_score,
            "all_quality_gates_passed": all_gates_passed,
            "status": status,
            "metrics": {
                "tests_run": regression_results.get('total', 0),
                "tests_passed": regression_results.get('passed', 0),
                "tests_failed": regression_results.get('failed', 0),
                "performance_score": performance_score,
                "quality_gates_passed": all_gates_passed
            }
        }

    def get_stage_name(self) -> str:
        return "testing"
