#!/usr/bin/env python3
"""
Requirements Parser Agent

Parses free-form user requirements documents into structured YAML/JSON format.
Uses LLM to extract and structure requirements from natural language text.

Single Responsibility: Convert unstructured requirements → structured requirements
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional, Any, List
from datetime import datetime

from requirements_models import (
    StructuredRequirements,
    FunctionalRequirement,
    NonFunctionalRequirement,
    UseCase,
    DataRequirement,
    IntegrationRequirement,
    Stakeholder,
    Constraint,
    Assumption,
    Priority,
    RequirementType
)
from llm_client import LLMClient, LLMMessage
from document_reader import DocumentReader
from debug_mixin import DebugMixin
from artemis_exceptions import (
    RequirementsFileError,
    RequirementsParsingError,
    RequirementsExportError,
    wrap_exception
)

# Import PromptManager for RAG-based prompts
try:
    from prompt_manager import PromptManager
    from rag_agent import RAGAgent
    PROMPT_MANAGER_AVAILABLE = True
except ImportError:
    PROMPT_MANAGER_AVAILABLE = False

# Performance: Pre-compute valid enum values for O(1) lookup instead of O(n) list comprehension
VALID_PRIORITIES = {p.value for p in Priority}
VALID_REQ_TYPES = {t.value for t in RequirementType}

# Import centralized AI Query Service
from ai_query_service import (
    AIQueryService,
    create_ai_query_service,
    QueryType,
    AIQueryResult
)


class RequirementsParserAgent(DebugMixin):
    """
    Parse free-form requirements into structured format

    Input: Free-form text file (requirements.txt, requirements.md, etc.)
    Output: StructuredRequirements object → YAML/JSON

    Uses LLM to:
    1. Extract functional requirements
    2. Identify non-functional requirements
    3. Detect use cases and user stories
    4. Identify stakeholders, constraints, assumptions
    5. Extract data and integration requirements
    6. Assign priorities and categorize requirements
    """

    def __init__(
        self,
        llm_provider: str = "openai",
        llm_model: Optional[str] = None,
        verbose: bool = True,
        rag: Optional[Any] = None,
        ai_service: Optional[AIQueryService] = None,
        logger: Optional[Any] = None
    ):
        """
        Initialize Requirements Parser Agent

        Args:
            llm_provider: LLM provider (openai, anthropic)
            llm_model: Specific model to use
            verbose: Enable verbose logging
            rag: RAG agent for PromptManager (optional)
            ai_service: Centralized AI Query Service (optional, created if not provided)
            logger: Logger instance (optional)
        """
        DebugMixin.__init__(self, component_name="requirements_parser")
        self.verbose = verbose
        self.logger = logger
        self.llm_provider = llm_provider or os.getenv("ARTEMIS_LLM_PROVIDER", "openai")
        self.llm_model = llm_model or os.getenv("ARTEMIS_LLM_MODEL")
        self.debug_log("RequirementsParserAgent initialized",
                      provider=self.llm_provider, verbose=verbose)

        # Initialize LLM client using factory
        from llm_client import LLMClientFactory, LLMProvider
        provider_enum = LLMProvider.OPENAI if self.llm_provider == "openai" else LLMProvider.ANTHROPIC
        self.llm = LLMClientFactory.create(provider_enum)

        # Initialize document reader
        self.doc_reader = DocumentReader(verbose=self.verbose)

        # Initialize PromptManager if available
        self.prompt_manager = None
        if PROMPT_MANAGER_AVAILABLE:
            try:
                # Use provided RAG or create new one
                if rag is None:
                    rag = RAGAgent(db_path="db", verbose=False)
                self.prompt_manager = PromptManager(rag, verbose=self.verbose)
                self.log("✅ Prompt manager initialized (using RAG-based prompts)")
            except Exception as e:
                self.log(f"⚠️  Could not initialize PromptManager: {e}")
                self.log("   Falling back to hardcoded prompts")
        else:
            self.log("⚠️  PromptManager not available - using hardcoded prompts")

        # Initialize centralized AI Query Service (KG→RAG→LLM pipeline)
        try:
            if ai_service:
                self.ai_service = ai_service
                self.log("✅ Using provided AI Query Service")
            else:
                self.ai_service = create_ai_query_service(
                    llm_client=self.llm,
                    rag=rag,
                    logger=self.logger,
                    verbose=self.verbose
                )
                self.log("✅ AI Query Service initialized (KG→RAG→LLM pipeline)")
        except Exception as e:
            self.log(f"⚠️  Could not initialize AI Query Service: {e}")
            self.ai_service = None

    def parse_requirements_file(
        self,
        input_file: str,
        project_name: Optional[str] = None,
        output_format: str = "yaml"  # yaml or json
    ) -> StructuredRequirements:
        """Parse requirements and return StructuredRequirements"""
        return self._parse_and_return_structured(input_file, project_name, output_format)

    def parse_requirements_for_validation(
        self,
        task_title: str,
        task_description: str,
        adr_content: str = ""
    ) -> Dict:
        """
        Parse requirements into format for validation system.

        Returns Dict with:
        - artifact_type: str
        - quality_criteria: Dict
        - functional_requirements: List
        - non_functional_requirements: List
        """
        combined = f"{task_title}\n\n{task_description}\n\n{adr_content}"

        prompt = f"""Analyze these requirements and extract validation criteria.

Requirements:
{combined}

Extract and return JSON:
{{
    "artifact_type": "code|notebook|ui|documentation|demo|visualization",
    "quality_criteria": {{
        "min_cells": <int>,
        "requires_visualizations": <bool>,
        "visualization_library": "<string>",
        "data_source": "<string>",
        "accessibility_required": <bool>,
        "responsive_required": <bool>,
        "min_test_coverage": <float>,
        "requires_unit_tests": <bool>
    }},
    "functional_requirements": ["<requirement>", ...],
    "non_functional_requirements": ["<requirement>", ...]
}}
"""

        messages = [
            LLMMessage(role="system", content="You are a requirements analyst. Extract structured validation criteria."),
            LLMMessage(role="user", content=prompt)
        ]

        response = self.llm_client.complete(
            messages=messages,
            model=self.llm_model,
            temperature=0.3,
            response_format={"type": "json_object"} if self.llm_provider == "openai" else None
        )

        return json.loads(response.content)

    def _parse_and_return_structured(
        self,
        input_file: str,
        project_name: Optional[str] = None,
        output_format: str = "yaml"
    ) -> StructuredRequirements:
        """
        Parse requirements from a document file

        Supports multiple formats:
        - PDF (.pdf)
        - Microsoft Word (.docx, .doc)
        - Microsoft Excel (.xlsx, .xls)
        - LibreOffice Writer (.odt)
        - LibreOffice Calc (.ods)
        - Plain Text (.txt)
        - Markdown (.md)
        - CSV (.csv)
        - HTML (.html)

        Args:
            input_file: Path to requirements document
            project_name: Name of the project (extracted from file if not provided)
            output_format: Output format (yaml or json)

        Returns:
            StructuredRequirements object
        """
        self.debug_trace("parse_requirements_file", input_file=input_file, project_name=project_name)
        try:
            self.log(f"📄 Reading requirements from: {input_file}")

            # Read input file using document reader (supports multiple formats)
            raw_requirements = self.doc_reader.read_document(input_file)

            # Extract project name from filename if not provided
            if not project_name:
                project_name = Path(input_file).stem.replace('_', ' ').replace('-', ' ').title()

            self.log(f"🔍 Parsing requirements for project: {project_name}")

            # Parse requirements using LLM
            structured_reqs = self._parse_with_llm(raw_requirements, project_name)

            self.log(f"✅ Parsed {len(structured_reqs.functional_requirements)} functional requirements")
            self.log(f"✅ Parsed {len(structured_reqs.non_functional_requirements)} non-functional requirements")
            self.log(f"✅ Identified {len(structured_reqs.use_cases)} use cases")
            self.log(f"✅ Identified {len(structured_reqs.stakeholders)} stakeholders")

            self.debug_dump_if_enabled("requirements_summary", "Requirements Summary", {
                "functional": len(structured_reqs.functional_requirements),
                "non_functional": len(structured_reqs.non_functional_requirements),
                "use_cases": len(structured_reqs.use_cases),
                "stakeholders": len(structured_reqs.stakeholders)
            })

            return structured_reqs

        except FileNotFoundError as e:
            raise RequirementsFileError(
                f"Requirements file not found: {input_file}",
                context={"input_file": input_file},
                original_exception=e
            )
        except (ValueError, RuntimeError) as e:
            # Document format errors
            raise RequirementsFileError(
                f"Error reading requirements file: {str(e)}",
                context={"input_file": input_file, "format": Path(input_file).suffix},
                original_exception=e
            )
        except Exception as e:
            raise RequirementsParsingError(
                f"Failed to parse requirements from {input_file}: {str(e)}",
                context={"input_file": input_file, "project_name": project_name},
                original_exception=e
            )

    def _parse_with_llm(self, raw_text: str, project_name: str) -> StructuredRequirements:
        """
        Use LLM to parse requirements from raw text

        First tries production-grade single-call extraction via PromptManager.
        Falls back to multi-step extraction if PromptManager unavailable.

        Multi-step extraction performs:
        1. Extract metadata and overview
        2. Extract functional requirements
        3. Extract non-functional requirements
        4. Extract use cases
        5. Extract data requirements
        6. Extract integration requirements
        7. Identify stakeholders, constraints, assumptions
        """
        self.log("🤖 Using LLM to structure requirements...")

        # Try PromptManager-based extraction first (production-grade single-call)
        if self.prompt_manager:
            try:
                self.log("📝 Using PromptManager for structured extraction")
                structured_reqs = self._parse_with_prompt_manager(raw_text, project_name)
                self.log("✅ Successfully used PromptManager-based extraction")
                return structured_reqs
            except Exception as e:
                self.log(f"⚠️  PromptManager extraction failed: {e}")
                self.log("   Falling back to multi-step extraction")

        # Fallback: Multi-step extraction (legacy approach)
        self.log("📝 Using multi-step extraction (legacy mode)")

        # Step 1: Extract overview and metadata
        overview = self._extract_overview(raw_text, project_name)

        # Step 2: Extract functional requirements
        functional_reqs = self._extract_functional_requirements(raw_text)

        # Step 3: Extract non-functional requirements
        non_functional_reqs = self._extract_non_functional_requirements(raw_text)

        # Step 4: Extract use cases
        use_cases = self._extract_use_cases(raw_text)

        # Step 5: Extract data requirements
        data_reqs = self._extract_data_requirements(raw_text)

        # Step 6: Extract integration requirements
        integration_reqs = self._extract_integration_requirements(raw_text)

        # Step 7: Extract stakeholders, constraints, assumptions
        stakeholders = self._extract_stakeholders(raw_text)
        constraints = self._extract_constraints(raw_text)
        assumptions = self._extract_assumptions(raw_text)

        # Build structured requirements
        structured_reqs = StructuredRequirements(
            project_name=project_name,
            version="1.0",
            created_date=datetime.now().strftime("%Y-%m-%d"),
            executive_summary=overview.get('executive_summary'),
            business_goals=overview.get('business_goals', []),
            success_criteria=overview.get('success_criteria', []),
            stakeholders=stakeholders,
            constraints=constraints,
            assumptions=assumptions,
            functional_requirements=functional_reqs,
            non_functional_requirements=non_functional_reqs,
            use_cases=use_cases,
            data_requirements=data_reqs,
            integration_requirements=integration_reqs,
            glossary=overview.get('glossary', {})
        )

        return structured_reqs

    def _parse_with_prompt_manager(self, raw_text: str, project_name: str) -> StructuredRequirements:
        """
        Parse requirements using PromptManager + AI Query Service

        Uses centralized AIQueryService for KG→RAG→LLM pipeline.
        This automatically handles Knowledge Graph queries, RAG recommendations,
        and LLM calls with proper exception wrapping.
        """
        try:
            import uuid

            # Generate IDs for this extraction run
            run_id = f"r-{uuid.uuid4().hex[:8]}"
            correlation_id = f"c-req-{uuid.uuid4().hex[:8]}"

            # Get prompt from PromptManager
            prompt_template = self.prompt_manager.get_prompt("requirements_structured_extraction")

            if not prompt_template:
                raise RequirementsParsingError(
                    "requirements_structured_extraction prompt not found in RAG",
                    context={"prompt_name": "requirements_structured_extraction"}
                )

            # Render prompt with variables
            rendered = self.prompt_manager.render_prompt(
                prompt=prompt_template,
                variables={
                    "run_id": run_id,
                    "correlation_id": correlation_id,
                    "output_format": "json",
                    "user_requirements": raw_text[:10000]  # Limit to 10k chars
                }
            )

            # Build full prompt (system + user)
            full_prompt = f"{rendered['system']}\n\n{rendered['user']}"

            # Use AI Query Service for KG→RAG→LLM pipeline
            if self.ai_service:
                self.log("🔄 Using AI Query Service for KG→RAG→LLM pipeline")

                # Extract keywords from project name for KG query
                keywords = project_name.lower().split()[:3]

                result = self.ai_service.query(
                    query_type=QueryType.REQUIREMENTS_PARSING,
                    prompt=full_prompt,
                    kg_query_params={'project_name': project_name, 'keywords': keywords},
                    temperature=0.3,
                    max_tokens=4000
                )

                if not result.success:
                    raise RequirementsParsingError(
                        f"AI Query Service failed: {result.error}",
                        context={"project_name": project_name}
                    )

                # Log token savings
                if result.kg_context and result.kg_context.pattern_count > 0:
                    self.log(
                        f"📊 KG found {result.kg_context.pattern_count} patterns, "
                        f"saved ~{result.llm_response.tokens_saved} tokens"
                    )

                response = result.llm_response.content
            else:
                # Fallback: Direct LLM call without AI service
                self.log("⚠️  AI Query Service unavailable - using direct LLM call")
                response = self.llm.generate_text(messages=[
                    LLMMessage(role="system", content=rendered['system']),
                    LLMMessage(role="user", content=rendered['user'])
                ], temperature=0.3)

            # Parse JSON response
            try:
                result_data = json.loads(response.content)
            except json.JSONDecodeError as e:
                # Try to extract JSON from response if wrapped in markdown
                import re
                json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
                if json_match:
                    result_data = json.loads(json_match.group(1))
                else:
                    raise RequirementsParsingError(
                        f"LLM returned invalid JSON: {e}",
                        context={"response_preview": response[:200]},
                        original_exception=e
                    )

            # Check if LLM refused to parse
            if result_data.get("result") == "Refuse":
                raise RequirementsParsingError(
                    f"LLM refused to parse requirements: {result_data.get('reason')}",
                    context={"missing_fields": result_data.get("missing_fields", [])}
                )

            # Convert LLM output to StructuredRequirements
            return self._convert_llm_output_to_structured_requirements(result_data, project_name)
        except RequirementsParsingError:
            # Re-raise already wrapped exceptions
            raise
        except Exception as e:
            raise RequirementsParsingError(
                f"Failed to parse requirements with PromptManager: {str(e)}",
                context={"project_name": project_name},
                original_exception=e
            )

    def _convert_llm_output_to_structured_requirements(
        self,
        llm_output: Dict[str, Any],
        project_name: str
    ) -> StructuredRequirements:
        """
        Convert LLM JSON output to StructuredRequirements object

        The LLM outputs a flatter structure with simpler types.
        This method maps it to our rich dataclass model.
        """
        # Extract non-functional requirements
        nfr_data = llm_output.get("non_functional_requirements", {})

        # Convert functional requirements (strings → FunctionalRequirement objects)
        functional_reqs = []
        for idx, req_text in enumerate(llm_output.get("functional_requirements", []), 1):
            functional_reqs.append(FunctionalRequirement(
                id=f"REQ-F-{idx:03d}",
                title=req_text[:100],  # First 100 chars as title
                description=req_text,
                priority=Priority.MEDIUM,  # Default priority
                acceptance_criteria=[f"Implements: {req_text[:50]}..."]
            ))

        # Convert non-functional requirements
        non_functional_reqs = []
        nfr_idx = 1

        # Performance requirements
        if "performance" in nfr_data:
            perf = nfr_data["performance"]
            if "p95_latency_ms" in perf:
                non_functional_reqs.append(NonFunctionalRequirement(
                    id=f"REQ-NF-{nfr_idx:03d}",
                    title=f"P95 Latency < {perf['p95_latency_ms']}ms",
                    description=f"95th percentile latency must be under {perf['p95_latency_ms']} milliseconds",
                    type=RequirementType.PERFORMANCE,
                    priority=Priority.HIGH,
                    metric="p95_latency_ms",
                    target=f"< {perf['p95_latency_ms']}ms"
                ))
                nfr_idx += 1

        # Security requirements
        for security_req in nfr_data.get("security", []):
            non_functional_reqs.append(NonFunctionalRequirement(
                id=f"REQ-NF-{nfr_idx:03d}",
                title=security_req[:100],
                description=security_req,
                type=RequirementType.SECURITY,
                priority=Priority.CRITICAL
            ))
            nfr_idx += 1

        # Convert actors to stakeholders
        stakeholders = []
        for actor in llm_output.get("actors", []):
            stakeholders.append(Stakeholder(
                name=actor.get("name", "Unknown"),
                role=", ".join(actor.get("roles", [])),
                concerns=[f"Auth: {', '.join(actor.get('auth', []))}"]
            ))

        # Convert risks to constraints (simplified mapping)
        constraints = []
        for risk in llm_output.get("risks", []):
            constraints.append(Constraint(
                type="risk",
                description=risk.get("item", ""),
                impact=risk.get("impact", "M"),
                mitigation=risk.get("mitigation")
            ))

        # Extract assumptions
        assumptions = [
            Assumption(description=assumption, risk_if_false="Unknown")
            for assumption in llm_output.get("assumptions", [])
        ]

        # Build structured requirements
        structured_reqs = StructuredRequirements(
            project_name=project_name,
            version="1.0",
            created_date=datetime.now().strftime("%Y-%m-%d"),
            executive_summary=llm_output.get("domain_context"),
            business_goals=llm_output.get("objectives", []),
            success_criteria=llm_output.get("acceptance_criteria", []),
            stakeholders=stakeholders,
            constraints=constraints,
            assumptions=assumptions,
            functional_requirements=functional_reqs,
            non_functional_requirements=non_functional_reqs,
            use_cases=[],  # TODO: Convert from LLM output if needed
            data_requirements=[],  # TODO: Convert from data_entities
            integration_requirements=[]  # TODO: Convert from integrations
        )

        return structured_reqs

    def _query_kg_for_similar_requirements(self, project_name: str) -> Optional[Dict[str, Any]]:
        """
        Query Knowledge Graph for similar projects and common requirement patterns

        This KG-first approach reduces LLM token usage by providing context from
        previously parsed requirements.

        Returns:
            Dict with similar project info and common requirements, or None if KG unavailable
        """
        try:
            from knowledge_graph_factory import get_knowledge_graph
            kg = get_knowledge_graph()

            if not kg:
                return None

            # Query for similar projects (by name similarity or domain)
            # For now, we'll get all requirements and find common patterns
            similar_requirements = kg.query("""
                MATCH (req:Requirement)
                WHERE req.status = 'active'
                RETURN req.req_id, req.title, req.type, req.priority
                ORDER BY req.priority DESC
                LIMIT 20
            """)

            if not similar_requirements:
                return None

            # Group by type to find common patterns
            type_counts = {}
            common_reqs = []

            for req in similar_requirements:
                req_type = req.get('req.type', 'unknown')
                type_counts[req_type] = type_counts.get(req_type, 0) + 1

                common_reqs.append({
                    'req_id': req.get('req.req_id'),
                    'title': req.get('req.title'),
                    'type': req_type,
                    'priority': req.get('req.priority', 'medium')
                })

            # Estimate token savings:
            # - Providing 5 common requirements as hints ~= 200 tokens
            # - This helps LLM avoid re-generating similar patterns
            # - Estimated savings: ~500-1000 tokens (LLM doesn't need to "invent" common NFRs)
            estimated_savings = len(common_reqs) * 50  # Conservative estimate

            return {
                'similar_projects_count': len(set(req.get('req.req_id', '').split('-')[0] for req in similar_requirements)),
                'common_requirements': common_reqs,
                'requirement_types': type_counts,
                'estimated_token_savings': estimated_savings
            }

        except Exception as e:
            self.log(f"Could not query KG for similar requirements: {e}")
            return None

    def _extract_overview(self, raw_text: str, project_name: str) -> Dict[str, Any]:
        """Extract project overview, goals, and success criteria"""
        prompt = f"""You are a requirements analyst. Extract the following from this requirements document:

1. Executive summary (2-3 sentences)
2. Business goals (list)
3. Success criteria (measurable outcomes)
4. Glossary (key terms and definitions)

Requirements Document:
{raw_text}

Return JSON with keys: executive_summary, business_goals, success_criteria, glossary
Keep it concise and factual."""

        response = self.llm.generate_text(messages=[LLMMessage(role="user", content=prompt)])
        result = self._parse_json_response(response.content)

        return result or {
            "executive_summary": None,
            "business_goals": [],
            "success_criteria": [],
            "glossary": {}
        }

    def _extract_functional_requirements(self, raw_text: str) -> List[FunctionalRequirement]:
        """Extract functional requirements with LLM"""
        prompt = f"""You are a requirements analyst. Extract ALL functional requirements from this document.

For each functional requirement, provide:
- id: REQ-F-XXX (sequential numbering)
- title: Short descriptive title
- description: What the system must do
- priority: critical/high/medium/low/nice_to_have
- user_story: As a [user], I want [goal], so that [benefit] (if applicable)
- acceptance_criteria: List of testable criteria
- estimated_effort: small/medium/large/xl
- tags: Relevant tags for categorization

Requirements Document:
{raw_text}

Return JSON array of functional requirements. Be thorough and extract ALL requirements."""

        response = self.llm.generate_text(messages=[LLMMessage(role="user", content=prompt)])
        result = self._parse_json_response(response.content)

        if not result or not isinstance(result, list):
            return []

        functional_reqs = []
        for idx, req_data in enumerate(result, 1):
            try:
                priority_str = req_data.get('priority', 'medium')
                # Use pre-computed set for O(1) lookup instead of O(n) list comprehension
                priority = Priority(priority_str) if priority_str in VALID_PRIORITIES else Priority.MEDIUM

                req = FunctionalRequirement(
                    id=req_data.get('id', f'REQ-F-{idx:03d}'),
                    title=req_data.get('title', ''),
                    description=req_data.get('description', ''),
                    priority=priority,
                    user_story=req_data.get('user_story'),
                    acceptance_criteria=req_data.get('acceptance_criteria', []),
                    dependencies=req_data.get('dependencies', []),
                    estimated_effort=req_data.get('estimated_effort'),
                    tags=req_data.get('tags', [])
                )
                functional_reqs.append(req)
            except Exception as e:
                self.log(f"⚠️  Error parsing functional requirement {idx}: {e}")

        return functional_reqs

    def _extract_non_functional_requirements(self, raw_text: str) -> List[NonFunctionalRequirement]:
        """Extract non-functional requirements (performance, security, etc.)"""
        prompt = f"""You are a requirements analyst. Extract ALL non-functional requirements from this document.

Non-functional requirements include:
- Performance (response time, throughput, scalability)
- Security (authentication, authorization, encryption)
- Compliance (GDPR, HIPAA, SOC2, etc.)
- Usability (user experience, accessibility)
- Reliability (uptime, availability, fault tolerance)
- Maintainability (code quality, documentation)

For each non-functional requirement, provide:
- id: REQ-NF-XXX (sequential numbering)
- title: Short descriptive title
- description: The requirement details
- type: functional/non_functional/performance/security/compliance/usability/accessibility/integration/data/business
- priority: critical/high/medium/low/nice_to_have
- metric: How to measure (if applicable)
- target: Target value (e.g., "< 200ms", "> 99.9% uptime")
- acceptance_criteria: List of testable criteria
- tags: Relevant tags

Requirements Document:
{raw_text}

Return JSON array of non-functional requirements."""

        response = self.llm.generate_text(messages=[LLMMessage(role="user", content=prompt)])
        result = self._parse_json_response(response.content)

        if not result or not isinstance(result, list):
            return []

        non_functional_reqs = []
        for idx, req_data in enumerate(result, 1):
            try:
                priority_str = req_data.get('priority', 'medium')
                # Use pre-computed sets for O(1) lookup instead of O(n) list comprehension
                priority = Priority(priority_str) if priority_str in VALID_PRIORITIES else Priority.MEDIUM

                type_str = req_data.get('type', 'non_functional')
                req_type = RequirementType(type_str) if type_str in VALID_REQ_TYPES else RequirementType.NON_FUNCTIONAL

                req = NonFunctionalRequirement(
                    id=req_data.get('id', f'REQ-NF-{idx:03d}'),
                    title=req_data.get('title', ''),
                    description=req_data.get('description', ''),
                    type=req_type,
                    priority=priority,
                    metric=req_data.get('metric'),
                    target=req_data.get('target'),
                    acceptance_criteria=req_data.get('acceptance_criteria', []),
                    tags=req_data.get('tags', [])
                )
                non_functional_reqs.append(req)
            except Exception as e:
                self.log(f"⚠️  Error parsing non-functional requirement {idx}: {e}")

        return non_functional_reqs

    def _extract_use_cases(self, raw_text: str) -> List[UseCase]:
        """Extract use cases and user scenarios"""
        prompt = f"""Extract use cases from this requirements document.

For each use case, provide:
- id: UC-XXX
- title: Use case name
- actor: Who performs this use case
- preconditions: What must be true before
- main_flow: Step-by-step main scenario
- alternate_flows: Alternative scenarios (dict)
- postconditions: System state after
- related_requirements: Related requirement IDs

Requirements Document:
{raw_text}

Return JSON array of use cases."""

        response = self.llm.generate_text(messages=[LLMMessage(role="user", content=prompt)])
        result = self._parse_json_response(response.content)

        if not result or not isinstance(result, list):
            return []

        use_cases = []
        for idx, uc_data in enumerate(result, 1):
            try:
                uc = UseCase(
                    id=uc_data.get('id', f'UC-{idx:03d}'),
                    title=uc_data.get('title', ''),
                    actor=uc_data.get('actor', ''),
                    preconditions=uc_data.get('preconditions', []),
                    main_flow=uc_data.get('main_flow', []),
                    alternate_flows=uc_data.get('alternate_flows', {}),
                    postconditions=uc_data.get('postconditions', []),
                    related_requirements=uc_data.get('related_requirements', [])
                )
                use_cases.append(uc)
            except Exception as e:
                self.log(f"⚠️  Error parsing use case {idx}: {e}")

        return use_cases

    def _extract_data_requirements(self, raw_text: str) -> List[DataRequirement]:
        """Extract data models and data requirements"""
        prompt = f"""Extract data requirements and data models from this document.

For each data entity, provide:
- id: REQ-D-XXX
- entity_name: Name of the data entity
- description: What this entity represents
- attributes: List of attributes with name, type, required
- relationships: Relationships to other entities
- volume: Expected data volume
- retention: Data retention policy
- compliance: Compliance requirements (GDPR, etc.)

Requirements Document:
{raw_text}

Return JSON array of data requirements. Only extract if data models are mentioned."""

        response = self.llm.generate_text(messages=[LLMMessage(role="user", content=prompt)])
        result = self._parse_json_response(response.content)

        if not result or not isinstance(result, list):
            return []

        data_reqs = []
        for idx, data in enumerate(result, 1):
            try:
                req = DataRequirement(
                    id=data.get('id', f'REQ-D-{idx:03d}'),
                    entity_name=data.get('entity_name', ''),
                    description=data.get('description', ''),
                    attributes=data.get('attributes', []),
                    relationships=data.get('relationships', []),
                    volume=data.get('volume'),
                    retention=data.get('retention'),
                    compliance=data.get('compliance', [])
                )
                data_reqs.append(req)
            except Exception as e:
                self.log(f"⚠️  Error parsing data requirement {idx}: {e}")

        return data_reqs

    def _extract_integration_requirements(self, raw_text: str) -> List[IntegrationRequirement]:
        """Extract external system integration requirements"""
        prompt = f"""Extract integration requirements with external systems from this document.

For each integration, provide:
- id: REQ-I-XXX
- system_name: Name of external system
- description: What the integration does
- direction: inbound/outbound/bidirectional
- protocol: REST/GraphQL/gRPC/SOAP/etc
- data_format: JSON/XML/CSV/etc
- frequency: real-time/batch/scheduled
- authentication: OAuth/API key/etc
- sla: Service level agreement

Requirements Document:
{raw_text}

Return JSON array of integration requirements. Only extract if integrations are mentioned."""

        response = self.llm.generate_text(messages=[LLMMessage(role="user", content=prompt)])
        result = self._parse_json_response(response.content)

        if not result or not isinstance(result, list):
            return []

        integration_reqs = []
        for idx, integration in enumerate(result, 1):
            try:
                req = IntegrationRequirement(
                    id=integration.get('id', f'REQ-I-{idx:03d}'),
                    system_name=integration.get('system_name', ''),
                    description=integration.get('description', ''),
                    direction=integration.get('direction', 'bidirectional'),
                    protocol=integration.get('protocol'),
                    data_format=integration.get('data_format'),
                    frequency=integration.get('frequency'),
                    authentication=integration.get('authentication'),
                    sla=integration.get('sla')
                )
                integration_reqs.append(req)
            except Exception as e:
                self.log(f"⚠️  Error parsing integration requirement {idx}: {e}")

        return integration_reqs

    def _extract_stakeholders(self, raw_text: str) -> List[Stakeholder]:
        """Extract stakeholder information"""
        prompt = f"""Identify stakeholders from this requirements document.

For each stakeholder, provide:
- name: Name or role
- role: Job title/role
- contact: Contact info (if mentioned)
- concerns: Key concerns/interests

Requirements Document:
{raw_text}

Return JSON array of stakeholders."""

        response = self.llm.generate_text(messages=[LLMMessage(role="user", content=prompt)])
        result = self._parse_json_response(response.content)

        if not result or not isinstance(result, list):
            return []

        stakeholders = []
        for s in result:
            try:
                stakeholder = Stakeholder(
                    name=s.get('name', ''),
                    role=s.get('role', ''),
                    contact=s.get('contact'),
                    concerns=s.get('concerns', [])
                )
                stakeholders.append(stakeholder)
            except Exception as e:
                self.log(f"⚠️  Error parsing stakeholder: {e}")

        return stakeholders

    def _extract_constraints(self, raw_text: str) -> List[Constraint]:
        """Extract project constraints"""
        prompt = f"""Identify constraints from this requirements document.

Constraints include:
- Technical constraints (technology stack, platforms)
- Business constraints (budget, timeline)
- Regulatory constraints (compliance, legal)

For each constraint, provide:
- type: technical/business/regulatory/timeline/budget
- description: The constraint
- impact: high/medium/low
- mitigation: How to address (if mentioned)

Requirements Document:
{raw_text}

Return JSON array of constraints."""

        response = self.llm.generate_text(messages=[LLMMessage(role="user", content=prompt)])
        result = self._parse_json_response(response.content)

        if not result or not isinstance(result, list):
            return []

        constraints = []
        for c in result:
            try:
                constraint = Constraint(
                    type=c.get('type', 'technical'),
                    description=c.get('description', ''),
                    impact=c.get('impact', 'medium'),
                    mitigation=c.get('mitigation')
                )
                constraints.append(constraint)
            except Exception as e:
                self.log(f"⚠️  Error parsing constraint: {e}")

        return constraints

    def _extract_assumptions(self, raw_text: str) -> List[Assumption]:
        """Extract project assumptions"""
        prompt = f"""Identify assumptions from this requirements document.

For each assumption, provide:
- description: The assumption
- risk_if_false: Risk if assumption is wrong
- validation_needed: true/false

Requirements Document:
{raw_text}

Return JSON array of assumptions."""

        response = self.llm.generate_text(messages=[LLMMessage(role="user", content=prompt)])
        result = self._parse_json_response(response.content)

        if not result or not isinstance(result, list):
            return []

        assumptions = []
        for a in result:
            try:
                assumption = Assumption(
                    description=a.get('description', ''),
                    risk_if_false=a.get('risk_if_false', ''),
                    validation_needed=a.get('validation_needed', True)
                )
                assumptions.append(assumption)
            except Exception as e:
                self.log(f"⚠️  Error parsing assumption: {e}")

        return assumptions

    def _parse_json_response(self, response: str) -> Any:
        """Parse JSON from LLM response (handle markdown code blocks)"""
        try:
            # Try direct JSON parse
            return json.loads(response)
        except json.JSONDecodeError:
            # Try extracting from markdown code block
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
                return json.loads(json_str)
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
                return json.loads(json_str)
            else:
                self.log(f"⚠️  Failed to parse JSON from LLM response")
                return None

    def log(self, message: str):
        """Log message if verbose"""
        if self.verbose:
            print(f"[RequirementsParser] {message}")


def main():
    """Example usage"""
    import argparse

    parser = argparse.ArgumentParser(description="Parse free-form requirements into structured format")
    parser.add_argument("input_file", help="Path to requirements document")
    parser.add_argument("--output", "-o", help="Output file path (default: requirements.yaml)")
    parser.add_argument("--format", "-f", choices=["yaml", "json"], default="yaml", help="Output format")
    parser.add_argument("--project-name", "-p", help="Project name")
    parser.add_argument("--llm-provider", default="openai", help="LLM provider")
    parser.add_argument("--llm-model", help="LLM model")

    args = parser.parse_args()

    # Initialize parser
    parser_agent = RequirementsParserAgent(
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        verbose=True
    )

    # Parse requirements
    structured_reqs = parser_agent.parse_requirements_file(
        input_file=args.input_file,
        project_name=args.project_name,
        output_format=args.format
    )

    # Save output
    output_file = args.output or f"requirements.{args.format}"
    if args.format == "yaml":
        structured_reqs.to_yaml(output_file)
    else:
        structured_reqs.to_json(output_file)

    print(f"\n✅ Requirements parsed and saved to: {output_file}")
    print(f"\n{structured_reqs.get_summary()}")


if __name__ == "__main__":
    main()
