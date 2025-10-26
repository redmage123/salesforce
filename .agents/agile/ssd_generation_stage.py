#!/usr/bin/env python3
"""
Software Specification Document (SSD) Generation Stage

This stage creates a comprehensive Software Specification Document that includes:
- Executive Summary and Business Case
- Functional and Non-Functional Requirements
- Architectural Diagrams (using Chart.js)
- ERD Diagrams (using Crow's foot notation)
- Object-Relational Diagrams
- PDF Output

The SSD is used by the Architecture Agent to create ADRs and guides all subsequent stages.

REFACTORING PATTERNS APPLIED:
- Pattern #10: Early Return Pattern (Guard Clauses)
- Pattern #11: Generator Pattern for large data processing
- Pattern #4: Use next() for first match searches
- Single Responsibility: Only generates SSD
- Dependency Injection: All dependencies injected via constructor
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict

from artemis_stage_interface import PipelineStage, LoggerInterface
from artemis_exceptions import PipelineStageError, wrap_exception
from llm_client import LLMClient
from rag_agent import RAGAgent


@dataclass
class RequirementItem:
    """Single requirement item"""
    id: str
    category: str  # functional, non_functional, business
    priority: str  # must_have, should_have, nice_to_have
    description: str
    acceptance_criteria: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class DiagramSpec:
    """Specification for a diagram to be generated"""
    diagram_type: str  # architecture, erd, object_relational, sequence, component
    title: str
    description: str
    chart_js_config: Dict[str, Any]  # Chart.js configuration
    mermaid_syntax: Optional[str] = None  # Alternative: Mermaid diagram syntax


@dataclass
class SSDDocument:
    """Complete Software Specification Document"""
    project_name: str
    card_id: str
    generated_at: str

    # Executive Summary
    executive_summary: str
    business_case: str

    # Requirements
    functional_requirements: List[RequirementItem]
    non_functional_requirements: List[RequirementItem]
    business_requirements: List[RequirementItem]

    # Diagrams
    diagrams: List[DiagramSpec]

    # Additional sections
    constraints: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class SSDGenerationStage(PipelineStage):
    """
    Software Specification Document Generation Stage

    Implements PipelineStage interface following SOLID principles
    """

    def __init__(
        self,
        llm_client: LLMClient,
        rag: Optional[RAGAgent] = None,
        logger: Optional[LoggerInterface] = None,
        output_dir: Optional[Path] = None,
        verbose: bool = True
    ):
        """
        Initialize SSD Generation Stage

        Args:
            llm_client: LLM client for generating specifications
            rag: RAG agent for storing SSD artifacts
            logger: Logger interface
            output_dir: Directory for output files (default: .artemis_data/ssd)
            verbose: Enable verbose logging
        """
        self.llm_client = llm_client
        self.rag = rag
        self.logger = logger
        self.verbose = verbose

        # Set output directory
        self.output_dir = output_dir or Path(".artemis_data/ssd")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if self.verbose and self.logger:
            self.logger.log(f"[SSD] Output directory: {self.output_dir}", "INFO")

    def get_stage_name(self) -> str:
        """Return the stage name for identification"""
        return "ssd_generation"

    def execute(self, card_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute SSD generation stage

        This stage intelligently decides whether a full SSD is needed based on:
        - Task complexity (simple tasks like refactoring skip SSD)
        - Task type (documentation, small fixes skip SSD)
        - Project scope (new features need SSD, bug fixes may not)

        Args:
            card_id: Kanban card ID
            context: Pipeline context containing card and workflow plan

        Returns:
            Dict with SSD document, file paths, and metadata
            OR Dict with status="skipped" if SSD not needed
        """
        # Guard clause: Validate inputs
        if not card_id:
            raise PipelineStageError("SSD Generation", "card_id is required")

        if not context or 'card' not in context:
            raise PipelineStageError("SSD Generation", "context must contain 'card'")

        card = context['card']

        if self.verbose and self.logger:
            self.logger.log("=" * 60, "STAGE")
            self.logger.log("📄 SOFTWARE SPECIFICATION DOCUMENT GENERATION", "STAGE")
            self.logger.log("=" * 60, "STAGE")

        try:
            # STEP 0: Decide if SSD is needed (Pattern #10: Early return for skip case)
            ssd_decision = self._should_generate_ssd(card, context)

            if not ssd_decision['needed']:
                if self.verbose and self.logger:
                    self.logger.log(
                        f"⏭️  SSD generation skipped: {ssd_decision['reason']}",
                        "INFO"
                    )
                    self.logger.log(
                        f"   Complexity: {ssd_decision['complexity']}",
                        "INFO"
                    )
                    self.logger.log(
                        f"   Task type: {ssd_decision['task_type']}",
                        "INFO"
                    )

                return {
                    "status": "skipped",
                    "reason": ssd_decision['reason'],
                    "complexity": ssd_decision['complexity'],
                    "task_type": ssd_decision['task_type'],
                    "ssd_needed": False
                }

            if self.verbose and self.logger:
                self.logger.log(
                    f"✅ SSD generation required: {ssd_decision['reason']}",
                    "INFO"
                )
            # Step 1: Analyze requirements from card
            requirements_analysis = self._analyze_requirements(card, context)

            # Step 2: Generate executive summary and business case
            executive_content = self._generate_executive_summary(
                card,
                requirements_analysis
            )

            # Step 3: Extract structured requirements
            structured_requirements = self._extract_requirements(
                card,
                requirements_analysis
            )

            # Step 4: Generate diagram specifications
            diagram_specs = self._generate_diagram_specifications(
                card,
                structured_requirements,
                context
            )

            # Step 5: Generate constraints, assumptions, risks
            additional_sections = self._generate_additional_sections(
                card,
                requirements_analysis
            )

            # Step 6: Build complete SSD document
            ssd_document = SSDDocument(
                project_name=card.get('title', 'Untitled Project'),
                card_id=card_id,
                generated_at=datetime.now().isoformat(),
                executive_summary=executive_content['executive_summary'],
                business_case=executive_content['business_case'],
                functional_requirements=structured_requirements['functional'],
                non_functional_requirements=structured_requirements['non_functional'],
                business_requirements=structured_requirements['business'],
                diagrams=diagram_specs,
                constraints=additional_sections['constraints'],
                assumptions=additional_sections['assumptions'],
                risks=additional_sections['risks'],
                success_criteria=additional_sections['success_criteria']
            )

            # Step 7: Generate output files (JSON, Markdown, HTML)
            file_paths = self._generate_output_files(card_id, ssd_document)

            # Step 8: Generate PDF (if dependencies available)
            pdf_path = self._generate_pdf(card_id, ssd_document, file_paths)
            if pdf_path:
                file_paths['pdf'] = str(pdf_path)

            # Step 9: Store in RAG for architecture agent
            if self.rag:
                self._store_in_rag(card_id, ssd_document)

            if self.verbose and self.logger:
                self.logger.log("✅ SSD Generation Complete", "SUCCESS")
                self.logger.log(f"   - JSON: {file_paths['json']}", "INFO")
                self.logger.log(f"   - Markdown: {file_paths['markdown']}", "INFO")
                self.logger.log(f"   - HTML: {file_paths['html']}", "INFO")
                if 'pdf' in file_paths:
                    self.logger.log(f"   - PDF: {file_paths['pdf']}", "INFO")

            return {
                "status": "success",
                "ssd_document": ssd_document.to_dict(),
                "file_paths": file_paths,
                "requirements_count": {
                    "functional": len(ssd_document.functional_requirements),
                    "non_functional": len(ssd_document.non_functional_requirements),
                    "business": len(ssd_document.business_requirements),
                },
                "diagrams_count": len(ssd_document.diagrams)
            }

        except Exception as e:
            error_msg = f"Failed to generate SSD: {str(e)}"
            if self.logger:
                self.logger.log(f"❌ {error_msg}", "ERROR")
            raise wrap_exception(e, PipelineStageError, "SSD Generation", error_msg)

    def _should_generate_ssd(
        self,
        card: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Intelligently decide if SSD generation is needed

        Pattern #10: Guard clauses and early returns
        Pattern #4: Use next() for first match in skip conditions

        Skip SSD for:
        - Simple complexity tasks (refactors, small fixes)
        - Documentation-only tasks
        - Bug fixes (unless complex)
        - Minor updates/tweaks

        Require SSD for:
        - Medium/Complex features
        - New applications/services
        - API design
        - Database schema changes
        - Multi-component features

        Returns:
            Dict with 'needed' (bool), 'reason' (str), 'complexity', 'task_type'
        """
        workflow_plan = context.get('workflow_plan', {})
        complexity = workflow_plan.get('complexity', 'medium')
        task_type = workflow_plan.get('task_type', 'other')

        task_description = (
            card.get('description', '') +
            ' ' +
            card.get('title', '')
        ).lower()

        # Define skip conditions (task_type, keywords, reason)
        skip_conditions = [
            ('simple', None, "Simple complexity task doesn't require full SSD"),
            (None, ['refactor', 'cleanup', 'restructure'],
             "Refactoring task doesn't need full specification"),
            (None, ['documentation', 'readme', 'docs'],
             "Documentation task doesn't require SSD"),
            (None, ['fix typo', 'update comment', 'formatting'],
             "Minor update doesn't require SSD"),
            ('bugfix', ['small', 'minor', 'quick'],
             "Simple bug fix doesn't require SSD")
        ]

        # Pattern #4: Use next() to find first matching skip condition
        skip_match = next(
            (
                reason
                for task_type_check, keywords, reason in skip_conditions
                if (
                    # Check task type match
                    (task_type_check and complexity == task_type_check) or
                    # Check keyword match in description
                    (keywords and any(kw in task_description for kw in keywords))
                )
            ),
            None  # Default: no skip match
        )

        # If skip condition matched, return early (Pattern #10)
        if skip_match:
            return {
                "needed": False,
                "reason": skip_match,
                "complexity": complexity,
                "task_type": task_type
            }

        # Define require conditions (complexity/type combinations that NEED SSD)
        require_conditions = [
            (complexity in ['medium', 'complex'], "Medium/complex task benefits from formal specification"),
            (task_type == 'feature', "New feature requires comprehensive specification"),
            ('api' in task_description or 'endpoint' in task_description,
             "API development requires detailed specification"),
            ('database' in task_description or 'schema' in task_description,
             "Database changes require formal specification"),
            ('application' in task_description or 'service' in task_description,
             "New application/service requires SSD"),
            ('architecture' in task_description or 'design' in task_description,
             "Architectural work requires specification document")
        ]

        # Pattern #4: Use next() to find first require condition
        require_match = next(
            (
                reason
                for condition, reason in require_conditions
                if condition
            ),
            "Task scope warrants formal specification"  # Default require reason
        )

        return {
            "needed": True,
            "reason": require_match,
            "complexity": complexity,
            "task_type": task_type
        }

    def _analyze_requirements(
        self,
        card: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze card to extract high-level requirements

        Pattern #10: Guard clauses for validation
        """
        # Guard clause: Check for description
        if not card.get('description') and not card.get('title'):
            raise PipelineStageError(
                "SSD Generation",
                "Card must have description or title"
            )

        task_description = card.get('description', card.get('title', ''))
        task_title = card.get('title', 'Untitled')

        if self.verbose and self.logger:
            self.logger.log("🔍 Analyzing Requirements...", "INFO")

        # Build analysis prompt
        prompt = self._build_requirements_analysis_prompt(
            task_title,
            task_description,
            context
        )

        # Query LLM for requirements analysis
        response = self.llm_client.query(prompt)

        # Parse response (expect JSON)
        analysis = self._parse_json_response(response)

        if self.verbose and self.logger:
            self.logger.log(
                f"   Found {len(analysis.get('key_features', []))} key features",
                "INFO"
            )

        return analysis

    def _generate_executive_summary(
        self,
        card: Dict[str, Any],
        requirements_analysis: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate executive summary and business case"""
        if self.verbose and self.logger:
            self.logger.log("📝 Generating Executive Summary...", "INFO")

        prompt = self._build_executive_summary_prompt(card, requirements_analysis)
        response = self.llm_client.query(prompt)

        # Parse response
        content = self._parse_json_response(response)

        return {
            "executive_summary": content.get('executive_summary', ''),
            "business_case": content.get('business_case', '')
        }

    def _extract_requirements(
        self,
        card: Dict[str, Any],
        requirements_analysis: Dict[str, Any]
    ) -> Dict[str, List[RequirementItem]]:
        """
        Extract structured requirements (functional, non-functional, business)

        Pattern #11: Generator pattern for processing large requirement lists
        """
        if self.verbose and self.logger:
            self.logger.log("📋 Extracting Structured Requirements...", "INFO")

        prompt = self._build_requirements_extraction_prompt(
            card,
            requirements_analysis
        )

        response = self.llm_client.query(prompt)
        parsed = self._parse_json_response(response)

        # Pattern #11: Use generator to process requirements
        def _create_requirement_items(requirements_list: List[Dict], category: str):
            """Generator yielding RequirementItem objects"""
            for idx, req in enumerate(requirements_list, 1):
                yield RequirementItem(
                    id=f"{category.upper()}-{idx:03d}",
                    category=category,
                    priority=req.get('priority', 'should_have'),
                    description=req.get('description', ''),
                    acceptance_criteria=req.get('acceptance_criteria', []),
                    dependencies=req.get('dependencies', [])
                )

        # Convert generators to lists
        return {
            "functional": list(_create_requirement_items(
                parsed.get('functional_requirements', []),
                'functional'
            )),
            "non_functional": list(_create_requirement_items(
                parsed.get('non_functional_requirements', []),
                'non_functional'
            )),
            "business": list(_create_requirement_items(
                parsed.get('business_requirements', []),
                'business'
            ))
        }

    def _generate_diagram_specifications(
        self,
        card: Dict[str, Any],
        requirements: Dict[str, List[RequirementItem]],
        context: Dict[str, Any]
    ) -> List[DiagramSpec]:
        """
        Generate diagram specifications for Chart.js and Mermaid

        Includes:
        - Architecture diagrams
        - ERD with Crow's foot notation
        - Object-relational diagrams
        - Component diagrams
        """
        if self.verbose and self.logger:
            self.logger.log("🎨 Generating Diagram Specifications...", "INFO")

        prompt = self._build_diagram_generation_prompt(card, requirements, context)
        response = self.llm_client.query(prompt)
        parsed = self._parse_json_response(response)

        # Pattern #11: Generator for creating DiagramSpec objects
        def _create_diagram_specs():
            """Generator yielding DiagramSpec objects"""
            for diagram_data in parsed.get('diagrams', []):
                yield DiagramSpec(
                    diagram_type=diagram_data.get('type', 'architecture'),
                    title=diagram_data.get('title', ''),
                    description=diagram_data.get('description', ''),
                    chart_js_config=diagram_data.get('chart_js_config', {}),
                    mermaid_syntax=diagram_data.get('mermaid_syntax')
                )

        diagrams = list(_create_diagram_specs())

        if self.verbose and self.logger:
            self.logger.log(f"   Generated {len(diagrams)} diagram specifications", "INFO")

        return diagrams

    def _generate_additional_sections(
        self,
        card: Dict[str, Any],
        requirements_analysis: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Generate constraints, assumptions, risks, success criteria"""
        if self.verbose and self.logger:
            self.logger.log("📊 Generating Additional Sections...", "INFO")

        prompt = self._build_additional_sections_prompt(card, requirements_analysis)
        response = self.llm_client.query(prompt)
        parsed = self._parse_json_response(response)

        return {
            "constraints": parsed.get('constraints', []),
            "assumptions": parsed.get('assumptions', []),
            "risks": parsed.get('risks', []),
            "success_criteria": parsed.get('success_criteria', [])
        }

    def _generate_output_files(
        self,
        card_id: str,
        ssd_document: SSDDocument
    ) -> Dict[str, str]:
        """
        Generate output files (JSON, Markdown, HTML)

        Returns dict with file paths
        """
        file_paths = {}

        # 1. JSON output
        json_path = self.output_dir / f"ssd_{card_id}.json"
        with open(json_path, 'w') as f:
            json.dump(ssd_document.to_dict(), f, indent=2)
        file_paths['json'] = str(json_path)

        # 2. Markdown output
        markdown_path = self.output_dir / f"ssd_{card_id}.md"
        markdown_content = self._generate_markdown(ssd_document)
        with open(markdown_path, 'w') as f:
            f.write(markdown_content)
        file_paths['markdown'] = str(markdown_path)

        # 3. HTML output (with embedded Chart.js for diagrams)
        html_path = self.output_dir / f"ssd_{card_id}.html"
        html_content = self._generate_html(ssd_document)
        with open(html_path, 'w') as f:
            f.write(html_content)
        file_paths['html'] = str(html_path)

        return file_paths

    def _generate_pdf(
        self,
        card_id: str,
        ssd_document: SSDDocument,
        file_paths: Dict[str, str]
    ) -> Optional[Path]:
        """
        Generate PDF from HTML using weasyprint or similar

        Pattern #10: Guard clauses for dependency checking
        """
        # Guard clause: Check if PDF generation dependencies available
        try:
            from weasyprint import HTML
        except ImportError:
            if self.verbose and self.logger:
                self.logger.log(
                    "⚠️  PDF generation skipped (weasyprint not installed)",
                    "WARNING"
                )
            return None

        # Guard clause: Check HTML file exists
        if 'html' not in file_paths:
            if self.verbose and self.logger:
                self.logger.log("⚠️  PDF generation skipped (no HTML file)", "WARNING")
            return None

        try:
            if self.verbose and self.logger:
                self.logger.log("📄 Generating PDF...", "INFO")

            html_path = file_paths['html']
            pdf_path = self.output_dir / f"ssd_{card_id}.pdf"

            # Generate PDF from HTML
            HTML(filename=html_path).write_pdf(pdf_path)

            if self.verbose and self.logger:
                self.logger.log(f"   PDF generated: {pdf_path}", "SUCCESS")

            return pdf_path

        except Exception as e:
            if self.verbose and self.logger:
                self.logger.log(f"⚠️  PDF generation failed: {e}", "WARNING")
            return None

    def _store_in_rag(self, card_id: str, ssd_document: SSDDocument) -> None:
        """Store SSD in RAG for architecture agent retrieval"""
        # Guard clause: Check RAG available
        if not self.rag:
            return

        if self.verbose and self.logger:
            self.logger.log("💾 Storing SSD in RAG...", "INFO")

        # Store executive summary
        self.rag.store_artifact(
            artifact_type="ssd_executive_summary",
            card_id=card_id,
            task_title=ssd_document.project_name,
            content=f"{ssd_document.executive_summary}\n\n{ssd_document.business_case}",
            metadata={"section": "executive"}
        )

        # Pattern #11: Generator for storing requirements
        def _store_requirements():
            """Generator for storing requirement batches"""
            all_requirements = (
                ssd_document.functional_requirements +
                ssd_document.non_functional_requirements +
                ssd_document.business_requirements
            )

            for req in all_requirements:
                content = f"""
# {req.id}: {req.description}

**Category**: {req.category}
**Priority**: {req.priority}

## Acceptance Criteria
{chr(10).join(f"- {criterion}" for criterion in req.acceptance_criteria)}

## Dependencies
{chr(10).join(f"- {dep}" for dep in req.dependencies) if req.dependencies else "None"}
"""
                yield (req.id, content, req.category)

        # Store requirements (using generator)
        for req_id, content, category in _store_requirements():
            self.rag.store_artifact(
                artifact_type="ssd_requirement",
                card_id=card_id,
                task_title=f"Requirement {req_id}",
                content=content,
                metadata={"requirement_id": req_id, "category": category}
            )

        # Store diagram specifications
        for diagram in ssd_document.diagrams:
            self.rag.store_artifact(
                artifact_type="ssd_diagram",
                card_id=card_id,
                task_title=diagram.title,
                content=json.dumps({
                    "type": diagram.diagram_type,
                    "description": diagram.description,
                    "chart_js_config": diagram.chart_js_config,
                    "mermaid_syntax": diagram.mermaid_syntax
                }, indent=2),
                metadata={"diagram_type": diagram.diagram_type}
            )

        if self.verbose and self.logger:
            self.logger.log("   SSD stored in RAG", "SUCCESS")

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM

        Pattern #10: Guard clauses for error handling
        """
        # Guard clause: Check empty response
        if not response or not response.strip():
            return {}

        try:
            # Try to find JSON in response (may be wrapped in markdown code blocks)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            # Guard clause: Check JSON markers found
            if json_start == -1 or json_end == 0:
                return {}

            json_str = response[json_start:json_end]
            return json.loads(json_str)

        except json.JSONDecodeError:
            # Fallback: Return empty dict if parsing fails
            if self.verbose and self.logger:
                self.logger.log("⚠️  Failed to parse JSON response", "WARNING")
            return {}

    # ========================================================================
    # PROMPT BUILDERS
    # ========================================================================

    def _build_requirements_analysis_prompt(
        self,
        task_title: str,
        task_description: str,
        context: Dict[str, Any]
    ) -> str:
        """Build prompt for requirements analysis"""
        return f"""You are a Senior Business Analyst tasked with analyzing software requirements.

**Task Title**: {task_title}

**Task Description**:
{task_description}

**Workflow Context**:
- Complexity: {context.get('workflow_plan', {}).get('complexity', 'medium')}
- Task Type: {context.get('workflow_plan', {}).get('task_type', 'feature')}

Analyze this task and provide a structured JSON response with:

1. **key_features**: List of main features/capabilities needed
2. **user_personas**: Who will use this? (roles/types of users)
3. **use_cases**: Primary use cases
4. **technical_domains**: Technical areas involved (e.g., backend, frontend, database, API)
5. **business_goals**: What business objectives does this achieve?
6. **success_metrics**: How will success be measured?

Provide response in JSON format:
```json
{{
  "key_features": ["feature1", "feature2", ...],
  "user_personas": ["persona1", "persona2", ...],
  "use_cases": ["use_case1", "use_case2", ...],
  "technical_domains": ["domain1", "domain2", ...],
  "business_goals": ["goal1", "goal2", ...],
  "success_metrics": ["metric1", "metric2", ...]
}}
```"""

    def _build_executive_summary_prompt(
        self,
        card: Dict[str, Any],
        requirements_analysis: Dict[str, Any]
    ) -> str:
        """Build prompt for executive summary generation"""
        return f"""You are a Technical Documentation Specialist creating an Executive Summary for a Software Specification Document.

**Project**: {card.get('title', 'Untitled Project')}

**Requirements Analysis**:
{json.dumps(requirements_analysis, indent=2)}

Create:

1. **Executive Summary** (2-3 paragraphs):
   - High-level overview of the project
   - What problem it solves
   - Who benefits from it
   - Expected outcomes

2. **Business Case** (3-4 paragraphs):
   - Why this project is needed
   - Business value and ROI
   - Alignment with organizational goals
   - Risks of NOT doing this project

Provide response in JSON format:
```json
{{
  "executive_summary": "Your executive summary here...",
  "business_case": "Your business case here..."
}}
```"""

    def _build_requirements_extraction_prompt(
        self,
        card: Dict[str, Any],
        requirements_analysis: Dict[str, Any]
    ) -> str:
        """Build prompt for structured requirements extraction"""
        return f"""You are a Requirements Engineer extracting detailed software requirements.

**Project**: {card.get('title', 'Untitled Project')}
**Description**: {card.get('description', '')}

**Analysis**:
{json.dumps(requirements_analysis, indent=2)}

Extract and categorize requirements into:

1. **Functional Requirements** (what the system must DO):
   - User-facing features
   - System behaviors
   - Data processing
   - Business logic

2. **Non-Functional Requirements** (how the system must PERFORM):
   - Performance (response time, throughput)
   - Scalability (users, data volume)
   - Security (authentication, authorization, encryption)
   - Reliability (uptime, fault tolerance)
   - Usability (UI/UX standards)
   - Maintainability (code quality, documentation)

3. **Business Requirements** (what business needs must be MET):
   - Compliance/regulatory
   - Budget constraints
   - Timeline/deadlines
   - Stakeholder needs

For each requirement provide:
- **description**: Clear, testable description
- **priority**: must_have | should_have | nice_to_have
- **acceptance_criteria**: List of criteria for completion
- **dependencies**: List of other requirements this depends on (use IDs like "FUNC-001")

Provide response in JSON format:
```json
{{
  "functional_requirements": [
    {{
      "description": "User can register with email and password",
      "priority": "must_have",
      "acceptance_criteria": [
        "Email validation is performed",
        "Password meets complexity requirements",
        "Confirmation email is sent"
      ],
      "dependencies": []
    }}
  ],
  "non_functional_requirements": [...],
  "business_requirements": [...]
}}
```"""

    def _build_diagram_generation_prompt(
        self,
        card: Dict[str, Any],
        requirements: Dict[str, List[RequirementItem]],
        context: Dict[str, Any]
    ) -> str:
        """Build prompt for diagram specifications"""
        # Summarize requirements for prompt
        req_summary = {
            "functional_count": len(requirements.get('functional', [])),
            "non_functional_count": len(requirements.get('non_functional', [])),
            "sample_requirements": [
                req.description for req in requirements.get('functional', [])[:3]
            ]
        }

        return f"""You are a Solutions Architect creating technical diagrams for a Software Specification Document.

**Project**: {card.get('title', 'Untitled Project')}

**Requirements Summary**:
{json.dumps(req_summary, indent=2)}

**Workflow Complexity**: {context.get('workflow_plan', {}).get('complexity', 'medium')}

Create diagram specifications for:

1. **System Architecture Diagram**:
   - High-level system components
   - Data flow between components
   - External integrations
   - Use Mermaid flowchart syntax

2. **Entity Relationship Diagram (ERD)**:
   - Database entities/tables
   - Relationships using Crow's foot notation
   - Key attributes
   - Use Mermaid ER diagram syntax

3. **Component Diagram** (if complex):
   - Major software components
   - Dependencies between components
   - Use Mermaid component diagram

For each diagram provide:
- **type**: architecture | erd | object_relational | component | sequence
- **title**: Diagram title
- **description**: What this diagram shows
- **mermaid_syntax**: Mermaid diagram code
- **chart_js_config**: {{}} (optional Chart.js configuration for visual rendering)

**Mermaid ER Diagram Crow's Foot Notation**:
```
erDiagram
    CUSTOMER ||--o{{{{ ORDER : places
    ORDER ||--||{{{{ LINE-ITEM : contains
    CUSTOMER }}|..||{{{{ DELIVERY-ADDRESS : uses
```

Notation:
- ||--o{{{{ : One-to-many
- ||--|| : One-to-one
- }}o--o{{{{ : Many-to-many
- }}|..||{{{{ : Zero or more

Provide response in JSON format:
```json
{{
  "diagrams": [
    {{
      "type": "architecture",
      "title": "System Architecture",
      "description": "High-level architecture showing...",
      "mermaid_syntax": "flowchart TD\\n    A[Client] --> B[API Gateway]\\n    B --> C[Backend Services]",
      "chart_js_config": {{}}
    }},
    {{
      "type": "erd",
      "title": "Entity Relationship Diagram",
      "description": "Database schema showing...",
      "mermaid_syntax": "erDiagram\\n    USER ||--o{{ ORDER : places\\n    ORDER ||--|{{ ITEM : contains",
      "chart_js_config": {{}}
    }}
  ]
}}
```"""

    def _build_additional_sections_prompt(
        self,
        card: Dict[str, Any],
        requirements_analysis: Dict[str, Any]
    ) -> str:
        """Build prompt for constraints, assumptions, risks, success criteria"""
        return f"""You are a Project Manager documenting project constraints and risks.

**Project**: {card.get('title', 'Untitled Project')}

**Analysis**:
{json.dumps(requirements_analysis, indent=2)}

Document:

1. **Constraints**: Limitations we must work within
   - Technical constraints (platforms, languages, frameworks)
   - Resource constraints (budget, team size, timeline)
   - Regulatory constraints (compliance, legal)

2. **Assumptions**: What we're assuming to be true
   - User environment assumptions
   - Technical assumptions
   - Business assumptions

3. **Risks**: Potential problems and mitigation
   - Technical risks
   - Resource risks
   - Timeline risks
   - Dependency risks

4. **Success Criteria**: How we'll know we succeeded
   - Measurable outcomes
   - Acceptance criteria
   - Performance targets

Provide response in JSON format:
```json
{{
  "constraints": [
    "Must use Python 3.12+",
    "Budget limited to $50,000",
    "Must comply with GDPR"
  ],
  "assumptions": [
    "Users have modern browsers (Chrome 90+, Firefox 88+)",
    "Average 1000 concurrent users",
    "Database migration can be done during maintenance window"
  ],
  "risks": [
    "Third-party API may have rate limits (Mitigation: Implement caching)",
    "Key developer may leave (Mitigation: Knowledge sharing sessions)",
    "Timeline is aggressive (Mitigation: MVP approach with phased releases)"
  ],
  "success_criteria": [
    "System handles 10,000 requests/second with <200ms response time",
    "99.9% uptime over 30-day period",
    "All critical security vulnerabilities resolved",
    "Positive user feedback from 80% of beta testers"
  ]
}}
```"""

    def _generate_markdown(self, ssd_document: SSDDocument) -> str:
        """Generate Markdown representation of SSD"""
        md_lines = [
            f"# Software Specification Document: {ssd_document.project_name}",
            "",
            f"**Generated**: {ssd_document.generated_at}",
            f"**Card ID**: {ssd_document.card_id}",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            ssd_document.executive_summary,
            "",
            "## Business Case",
            "",
            ssd_document.business_case,
            "",
            "---",
            "",
            "## Functional Requirements",
            ""
        ]

        # Pattern #11: Use generator to build functional requirements markdown
        def _format_functional_requirements():
            """Generator yielding markdown lines for functional requirements"""
            for req in ssd_document.functional_requirements:
                yield from [
                    f"### {req.id}: {req.description}",
                    "",
                    f"**Priority**: {req.priority}",
                    "",
                    "**Acceptance Criteria**:",
                    *[f"- {criterion}" for criterion in req.acceptance_criteria],
                    "",
                    f"**Dependencies**: {', '.join(req.dependencies) if req.dependencies else 'None'}",
                    ""
                ]

        md_lines.extend(_format_functional_requirements())

        md_lines.extend([
            "---",
            "",
            "## Non-Functional Requirements",
            ""
        ])

        # Pattern #11: Generator for non-functional requirements
        def _format_non_functional_requirements():
            """Generator yielding markdown lines for non-functional requirements"""
            for req in ssd_document.non_functional_requirements:
                yield from [
                    f"### {req.id}: {req.description}",
                    "",
                    f"**Priority**: {req.priority}",
                    "",
                    "**Acceptance Criteria**:",
                    *[f"- {criterion}" for criterion in req.acceptance_criteria],
                    ""
                ]

        md_lines.extend(_format_non_functional_requirements())

        md_lines.extend([
            "---",
            "",
            "## Business Requirements",
            ""
        ])

        # Pattern #11: Generator for business requirements
        def _format_business_requirements():
            """Generator yielding markdown lines for business requirements"""
            for req in ssd_document.business_requirements:
                yield from [
                    f"### {req.id}: {req.description}",
                    "",
                    f"**Priority**: {req.priority}",
                    ""
                ]

        md_lines.extend(_format_business_requirements())

        md_lines.extend([
            "---",
            "",
            "## Diagrams",
            ""
        ])

        # Pattern #11: Generator for diagrams
        def _format_diagrams():
            """Generator yielding markdown lines for diagrams"""
            for diagram in ssd_document.diagrams:
                yield f"### {diagram.title}"
                yield ""
                yield diagram.description
                yield ""
                yield f"**Type**: {diagram.diagram_type}"
                yield ""

                if diagram.mermaid_syntax:
                    yield "```mermaid"
                    yield diagram.mermaid_syntax
                    yield "```"
                    yield ""

        md_lines.extend(_format_diagrams())

        md_lines.extend([
            "---",
            "",
            "## Constraints",
            "",
            *[f"- {constraint}" for constraint in ssd_document.constraints],
            "",
            "## Assumptions",
            "",
            *[f"- {assumption}" for assumption in ssd_document.assumptions],
            "",
            "## Risks",
            "",
            *[f"- {risk}" for risk in ssd_document.risks],
            "",
            "## Success Criteria",
            "",
            *[f"- {criterion}" for criterion in ssd_document.success_criteria],
            ""
        ])

        return "\n".join(md_lines)

    def _generate_html(self, ssd_document: SSDDocument) -> str:
        """
        Generate HTML representation with embedded Mermaid diagrams

        Uses Mermaid.js for rendering diagrams in the browser
        """
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SSD: {ssd_document.project_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 40px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 8px;
            margin-top: 30px;
        }}
        h3 {{
            color: #7f8c8d;
        }}
        .requirement {{
            background-color: #ecf0f1;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #3498db;
        }}
        .priority-must_have {{
            border-left-color: #e74c3c;
        }}
        .priority-should_have {{
            border-left-color: #f39c12;
        }}
        .priority-nice_to_have {{
            border-left-color: #95a5a6;
        }}
        .diagram {{
            margin: 20px 0;
            padding: 20px;
            background-color: #f9f9f9;
            border: 1px solid #ddd;
        }}
        .metadata {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        ul {{
            margin: 10px 0;
        }}
        .section {{
            margin: 30px 0;
        }}
    </style>
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
</head>
<body>
    <div class="container">
        <h1>Software Specification Document</h1>
        <h2>{ssd_document.project_name}</h2>

        <div class="metadata">
            <p><strong>Generated:</strong> {ssd_document.generated_at}</p>
            <p><strong>Card ID:</strong> {ssd_document.card_id}</p>
        </div>

        <div class="section">
            <h2>Executive Summary</h2>
            <p>{ssd_document.executive_summary}</p>
        </div>

        <div class="section">
            <h2>Business Case</h2>
            <p>{ssd_document.business_case}</p>
        </div>

        <div class="section">
            <h2>Functional Requirements</h2>
"""

        # Pattern #11: Generator for functional requirements HTML
        def _format_functional_req_html():
            """Generator yielding HTML for functional requirements"""
            for req in ssd_document.functional_requirements:
                deps = f'<p><strong>Dependencies:</strong> {", ".join(req.dependencies)}</p>' if req.dependencies else ''
                yield f"""
            <div class="requirement priority-{req.priority}">
                <h3>{req.id}: {req.description}</h3>
                <p><strong>Priority:</strong> {req.priority.replace('_', ' ').title()}</p>
                <p><strong>Acceptance Criteria:</strong></p>
                <ul>
                    {''.join(f'<li>{criterion}</li>' for criterion in req.acceptance_criteria)}
                </ul>
                {deps}
            </div>
"""

        html += ''.join(_format_functional_req_html())

        html += """
        </div>

        <div class="section">
            <h2>Non-Functional Requirements</h2>
"""

        # Pattern #11: Generator for non-functional requirements HTML
        def _format_non_functional_req_html():
            """Generator yielding HTML for non-functional requirements"""
            for req in ssd_document.non_functional_requirements:
                yield f"""
            <div class="requirement priority-{req.priority}">
                <h3>{req.id}: {req.description}</h3>
                <p><strong>Priority:</strong> {req.priority.replace('_', ' ').title()}</p>
                <p><strong>Acceptance Criteria:</strong></p>
                <ul>
                    {''.join(f'<li>{criterion}</li>' for criterion in req.acceptance_criteria)}
                </ul>
            </div>
"""

        html += ''.join(_format_non_functional_req_html())

        html += """
        </div>

        <div class="section">
            <h2>Business Requirements</h2>
"""

        # Pattern #11: Generator for business requirements HTML
        def _format_business_req_html():
            """Generator yielding HTML for business requirements"""
            for req in ssd_document.business_requirements:
                yield f"""
            <div class="requirement priority-{req.priority}">
                <h3>{req.id}: {req.description}</h3>
                <p><strong>Priority:</strong> {req.priority.replace('_', ' ').title()}</p>
            </div>
"""

        html += ''.join(_format_business_req_html())

        html += """
        </div>

        <div class="section">
            <h2>Architecture & Design</h2>
"""

        # Pattern #11: Generator for diagrams HTML
        def _format_diagrams_html():
            """Generator yielding HTML for diagrams"""
            for diagram in ssd_document.diagrams:
                mermaid_code = diagram.mermaid_syntax if diagram.mermaid_syntax else ""
                yield f"""
            <div class="diagram">
                <h3>{diagram.title}</h3>
                <p>{diagram.description}</p>
                <div class="mermaid">
{mermaid_code}
                </div>
            </div>
"""

        html += ''.join(_format_diagrams_html())

        html += f"""
        </div>

        <div class="section">
            <h2>Constraints</h2>
            <ul>
                {''.join(f'<li>{constraint}</li>' for constraint in ssd_document.constraints)}
            </ul>
        </div>

        <div class="section">
            <h2>Assumptions</h2>
            <ul>
                {''.join(f'<li>{assumption}</li>' for assumption in ssd_document.assumptions)}
            </ul>
        </div>

        <div class="section">
            <h2>Risks</h2>
            <ul>
                {''.join(f'<li>{risk}</li>' for risk in ssd_document.risks)}
            </ul>
        </div>

        <div class="section">
            <h2>Success Criteria</h2>
            <ul>
                {''.join(f'<li>{criterion}</li>' for criterion in ssd_document.success_criteria)}
            </ul>
        </div>
    </div>
</body>
</html>
"""

        return html
