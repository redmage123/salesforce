#!/usr/bin/env python3
"""
ADRGenerator (SOLID: Single Responsibility)

Single Responsibility: Generate ADR content

This service handles ONLY ADR content generation:
- Building ADR generation prompts
- Generating ADR via AI Query Service or templates
- Querying SSD from RAG for context
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from artemis_stage_interface import LoggerInterface
from artemis_exceptions import ADRGenerationError, wrap_exception
from environment_context import get_environment_context


class ADRGenerator:
    """
    Service for generating ADR content

    Single Responsibility: ADR content generation
    - Build prompts for ADR generation
    - Generate ADR using AI Query Service (KG→RAG→LLM pipeline)
    - Fallback to template-based generation
    - Query SSD from RAG for comprehensive context
    """

    def __init__(
        self,
        rag,  # RAGAgent
        logger: LoggerInterface,
        llm_client=None,
        ai_service=None,  # AIQueryService
        prompt_manager=None  # PromptManager
    ):
        """
        Initialize ADR generator

        Args:
            rag: RAG agent for querying context
            logger: Logger interface
            llm_client: LLM client (optional)
            ai_service: AI Query Service for KG→RAG→LLM pipeline (optional)
            prompt_manager: Prompt manager for RAG-based prompts (optional)
        """
        self.rag = rag
        self.logger = logger
        self.llm_client = llm_client
        self.ai_service = ai_service
        self.prompt_manager = prompt_manager

    def generate_adr(
        self,
        card: Dict,
        adr_number: str,
        structured_requirements=None
    ) -> str:
        """
        Generate ADR content using AIQueryService (KG→RAG→LLM pipeline)

        Uses centralized AIQueryService to automatically query Knowledge Graph
        for similar ADRs, get RAG recommendations, and call LLM with enhanced context.

        Args:
            card: Kanban card with task details
            adr_number: ADR number (e.g., "001")
            structured_requirements: Structured requirements (optional)

        Returns:
            Generated ADR content as markdown string

        Raises:
            ADRGenerationError: If ADR generation fails
        """
        try:
            title = card.get('title', 'Untitled Task')

            # If AIQueryService available, use it for intelligent ADR generation
            if self.ai_service:
                # Build base ADR prompt
                prompt = self._build_adr_prompt(card, adr_number, structured_requirements)

                # Extract keywords for KG query
                keywords = title.split()[:3]

                # Use AI Query Service (handles KG→RAG→LLM automatically)
                self.logger.log("🔄 Using AI Query Service for KG→RAG→LLM pipeline", "INFO")

                # Import QueryType here to avoid circular import
                from ai_query_service import QueryType

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

    def _build_adr_prompt(
        self,
        card: Dict,
        adr_number: str,
        structured_requirements=None
    ) -> str:
        """
        Build prompt for LLM ADR generation

        Now queries RAG for Software Specification Document (SSD) to provide
        comprehensive context including:
        - Executive summary and business case
        - Functional and non-functional requirements
        - Diagram specifications
        - Constraints and assumptions

        Args:
            card: Kanban card
            adr_number: ADR number
            structured_requirements: Structured requirements (optional)

        Returns:
            Prompt string for LLM
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

        Args:
            card_id: Card ID to query SSD for

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

        Args:
            content: SSD content
            section_name: Section name to extract

        Returns:
            List of extracted items (max 5)
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

    def _generate_adr_template(
        self,
        card: Dict,
        adr_number: str,
        structured_requirements=None
    ) -> str:
        """
        Template-based ADR generation (fallback when AIQueryService unavailable)

        Args:
            card: Kanban card
            adr_number: ADR number
            structured_requirements: Structured requirements (optional)

        Returns:
            Generated ADR content as markdown string
        """
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
