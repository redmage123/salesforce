#!/usr/bin/env python3
"""
ArchitectureStage

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


class ArchitectureStage(PipelineStage, SupervisedStageMixin, DebugMixin):
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

        # Initialize DebugMixin
        DebugMixin.__init__(self, component_name="architecture")

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

        # DEBUG: Log architecture stage start
        self.debug_log("Starting ADR creation", card_id=card_id, title=card.get('title'))

        # Check for structured requirements from requirements_parsing stage
        structured_requirements = context.get('structured_requirements')
        if structured_requirements:
            self.logger.log("✅ Using structured requirements from requirements parsing stage", "INFO")
            self.logger.log(f"   Found {len(structured_requirements.functional_requirements)} functional requirements", "INFO")
            self.logger.log(f"   Found {len(structured_requirements.non_functional_requirements)} non-functional requirements", "INFO")

            # DEBUG: Dump structured requirements info
            self.debug_dump_if_enabled('dump_design', "Structured Requirements Summary", {
                "project": structured_requirements.project_name,
                "functional_count": len(structured_requirements.functional_requirements),
                "non_functional_count": len(structured_requirements.non_functional_requirements),
                "use_cases": len(structured_requirements.use_cases)
            })

        # Update progress: getting ADR number
        self.update_progress({"step": "getting_adr_number", "progress_percent": 10})

        # Get next ADR number
        adr_number = self._get_next_adr_number()

        # Update progress: generating ADR
        self.update_progress({"step": "generating_adr", "progress_percent": 30})

        # Create ADR file (pass structured requirements if available)
        adr_content = self._generate_adr(card, adr_number, structured_requirements)
        adr_filename = self._create_adr_filename(card['title'], adr_number)
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

        # Store ADR in RAG
        # Store in RAG using helper (DRY)

        RAGStorageHelper.store_stage_artifact(

            rag=self.rag,
            stage_name="architecture_decision",
            card_id=card_id,
            task_title=card.get('title', 'Unknown'),
            content=adr_content,
            metadata={
                "adr_number": adr_number,
                "priority": card.get('priority', 'medium'),
                "story_points": card.get('points', 5),
                "adr_file": str(adr_path)
            }
        )

        # Store ADR in Knowledge Graph for traceability
        self._store_adr_in_knowledge_graph(
            card_id=card_id,
            adr_number=adr_number,
            adr_path=str(adr_path),
            structured_requirements=structured_requirements
        )

        # Update progress: generating user stories from ADR
        self.update_progress({"step": "generating_user_stories", "progress_percent": 80})

        # Generate user stories from ADR and add to Kanban
        user_stories = self._generate_user_stories_from_adr(adr_content, adr_number, card)

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

        # Store Kanban board state in RAG
        self._store_kanban_in_rag(card_id, story_cards)

        # Update progress: complete
        self.update_progress({"step": "complete", "progress_percent": 100})

        return {
            "stage": "architecture",
            "adr_number": adr_number,
            "adr_file": str(adr_path),
            "user_stories_created": len(story_cards),
            "story_card_ids": story_cards,
            "status": "COMPLETE"
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

            # DEBUG: Log ADR generation start
            with self.debug_section("ADR Generation", adr_number=adr_number):
                # If AIQueryService available, use it for intelligent ADR generation
                if self.ai_service:
                    # Build base ADR prompt
                    prompt = self._build_adr_prompt(card, adr_number, structured_requirements)

                    # Extract keywords for KG query
                    keywords = title.split()[:3]

                    # DEBUG: Log KG query parameters
                    self.debug_if_enabled('log_decisions', "Using AI Query Service for ADR generation",
                                         keywords=keywords,
                                         has_structured_reqs=structured_requirements is not None)

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

                        # DEBUG: Dump ADR generation details
                        self.debug_dump_if_enabled('dump_design', "ADR Generation Details", {
                            "adr_number": adr_number,
                            "kg_patterns_found": result.kg_context.pattern_count,
                            "tokens_saved": result.llm_response.tokens_saved,
                            "keywords": keywords
                        })

                    # Return LLM-generated ADR content
                    return result.llm_response.content

                # Fallback: Generate ADR manually without AI service
                self.logger.log("⚠️  AI Query Service unavailable - using template-based generation", "WARNING")
                self.debug_if_enabled('log_decisions', "Falling back to template-based ADR generation")
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
        """Build prompt for LLM ADR generation"""
        title = card.get('title', 'Untitled Task')
        description = card.get('description', 'No description provided')

        prompt = f"""Generate an Architecture Decision Record (ADR) for the following task:

**Title**: {title}
**Description**: {description}
**Priority**: {card.get('priority', 'medium')}
**Complexity**: {card.get('size', 'medium')}
"""

        if structured_requirements:
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

        prompt += f"""
Generate ADR-{adr_number} in this format:

# ADR-{adr_number}: {title}

**Status**: Accepted
**Date**: {datetime.utcnow().strftime('%Y-%m-%d')}
**Deciders**: Architecture Agent (Automated)

## Context
[Explain the technical context and problem being solved]

## Decision
[Document the architectural decision and implementation approach]

## Consequences
[List positive and negative consequences]

Focus on actionable implementation guidance."""

        return prompt

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
            # Store in RAG using helper (DRY)

            RAGStorageHelper.store_stage_artifact(

                rag=self.rag,
                stage_name="kanban_board_state",
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

