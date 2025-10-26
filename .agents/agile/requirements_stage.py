#!/usr/bin/env python3
"""
Requirements Parsing Stage - Convert Free-Form Requirements to Structured Format

Single Responsibility: Parse user requirements documents → structured YAML/JSON

This stage:
1. Reads requirements document (PDF, Word, Excel, text, etc.)
2. Uses LLM to extract and structure requirements
3. Validates and exports structured requirements
4. Stores in RAG for downstream stages

SOLID Principles:
- Single Responsibility: Only parses requirements
- Open/Closed: Extensible to new document formats without modification
- Liskov Substitution: Implements PipelineStage interface
- Interface Segregation: Minimal, focused interface
- Dependency Inversion: Depends on abstractions (PipelineStage, LoggerInterface)
"""

import os
from pathlib import Path
from typing import Dict, Optional, Any

from artemis_stage_interface import PipelineStage, LoggerInterface
from requirements_parser_agent import RequirementsParserAgent
from requirements_models import StructuredRequirements
from rag_agent import RAGAgent
from agent_messenger import AgentMessenger
from artemis_exceptions import (
    RequirementsFileError,
    RequirementsParsingError,
    RequirementsExportError,
    wrap_exception
)
from supervised_agent_mixin import SupervisedStageMixin
from knowledge_graph_factory import get_knowledge_graph
from rag_storage_helper import RAGStorageHelper


class RequirementsParsingStage(PipelineStage, SupervisedStageMixin):
    """
    Parse requirements documents into structured format

    Input (from context):
    - requirements_file: Path to requirements document

    Output (to context):
    - structured_requirements: StructuredRequirements object
    - requirements_yaml_file: Path to exported YAML file
    - requirements_summary: Human-readable summary

    Integrates with supervisor for:
    - LLM cost tracking during parsing
    - Parsing failure recovery
    - Automatic heartbeat monitoring
    """

    def __init__(
        self,
        logger: LoggerInterface,
        rag: RAGAgent,
        messenger: AgentMessenger,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        output_dir: Optional[str] = None,
        supervisor: Optional['SupervisorAgent'] = None
    ):
        """
        Initialize Requirements Parsing Stage

        Args:
            logger: Logger interface
            rag: RAG agent for storing requirements
            messenger: Agent messenger for communication
            llm_provider: LLM provider (openai/anthropic)
            llm_model: Specific model to use
            output_dir: Directory for requirements output
            supervisor: Optional SupervisorAgent for monitoring
        """
        # Initialize PipelineStage
        PipelineStage.__init__(self)

        # Initialize SupervisedStageMixin for health monitoring
        # Requirements parsing can take time, so use 30 second heartbeat
        SupervisedStageMixin.__init__(
            self,
            supervisor=supervisor,
            stage_name="RequirementsParsingStage",
            heartbeat_interval=30  # Longer interval for LLM-heavy stage
        )

        self.logger = logger
        self.rag = rag
        self.messenger = messenger

        # LLM configuration
        self.llm_provider = llm_provider or os.getenv("ARTEMIS_LLM_PROVIDER", "openai")
        self.llm_model = llm_model or os.getenv("ARTEMIS_LLM_MODEL")

        # Output directory
        if output_dir is None:
            output_dir = os.getenv("ARTEMIS_REQUIREMENTS_DIR", "../../.artemis_data/requirements")
            if not os.path.isabs(output_dir):
                script_dir = os.path.dirname(os.path.abspath(__file__))
                output_dir = os.path.join(script_dir, output_dir)

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize requirements parser (with RAG for PromptManager)
        self.parser = RequirementsParserAgent(
            llm_provider=self.llm_provider,
            llm_model=self.llm_model,
            verbose=False,  # Use our logger instead
            rag=self.rag  # Pass RAG for PromptManager integration
        )

    def execute(self, card: Dict, context: Dict) -> Dict:
        """Execute requirements parsing with supervisor monitoring"""
        metadata = {
            "task_id": card.get('card_id'),
            "stage": "requirements_parsing"
        }

        with self.supervised_execution(metadata):
            return self._do_requirements_parsing(card, context)

    def _do_requirements_parsing(self, card: Dict, context: Dict) -> Dict:
        """
        Internal method - performs requirements parsing

        Args:
            card: Kanban card with task details
            context: Context from previous stages

        Returns:
            Dict with parsed requirements and file paths

        Raises:
            RequirementsFileError: If requirements file not found or unreadable
            RequirementsParsingError: If parsing fails
            RequirementsExportError: If export fails
        """
        self.logger.log("Starting Requirements Parsing Stage", "STAGE")
        self.logger.log("📝 Converting Free-Form Requirements → Structured Format", "INFO")

        card_id = card['card_id']
        task_title = card.get('title', 'Unknown Task')

        # Update progress: starting
        self.update_progress({"step": "starting", "progress_percent": 5})

        # Get requirements file from card or context
        requirements_file = card.get('requirements_file') or context.get('requirements_file')

        if not requirements_file:
            self.logger.log("⚠️  No requirements file specified - skipping requirements parsing", "WARNING")
            return {
                "stage": "requirements_parsing",
                "status": "SKIPPED",
                "reason": "No requirements file specified"
            }

        self.logger.log(f"📄 Requirements file: {requirements_file}", "INFO")

        # Update progress: reading file
        self.update_progress({"step": "reading_file", "progress_percent": 10})

        try:
            # Extract project name from card
            project_name = card.get('project_name') or task_title

            self.logger.log(f"🤖 Parsing requirements for: {project_name}", "INFO")

            # Update progress: parsing with LLM
            self.update_progress({"step": "parsing_with_llm", "progress_percent": 20})

            # Parse requirements using LLM
            structured_reqs = self.parser.parse_requirements_file(
                input_file=requirements_file,
                project_name=project_name
            )

            self.logger.log(f"✅ Parsed {len(structured_reqs.functional_requirements)} functional requirements", "SUCCESS")
            self.logger.log(f"✅ Parsed {len(structured_reqs.non_functional_requirements)} non-functional requirements", "SUCCESS")
            self.logger.log(f"✅ Identified {len(structured_reqs.use_cases)} use cases", "SUCCESS")

            # Update progress: exporting
            self.update_progress({"step": "exporting", "progress_percent": 70})

            # Export to YAML
            yaml_file = self.output_dir / f"{card_id}_requirements.yaml"
            structured_reqs.to_yaml(str(yaml_file))
            self.logger.log(f"💾 Exported requirements to: {yaml_file}", "INFO")

            # Also export to JSON for easy programmatic access
            json_file = self.output_dir / f"{card_id}_requirements.json"
            structured_reqs.to_json(str(json_file))

            # Update progress: storing in RAG
            self.update_progress({"step": "storing_in_rag", "progress_percent": 85})

            # Store in RAG for architecture stage
            self._store_requirements_in_rag(card_id, task_title, structured_reqs)

            # Store in Knowledge Graph for traceability
            self._store_requirements_in_knowledge_graph(card_id, task_title, card, structured_reqs)

            # Generate summary
            summary = structured_reqs.get_summary()
            self.logger.log(f"\n{summary}", "INFO")

            # Update progress: notifying agents
            self.update_progress({"step": "notifying_agents", "progress_percent": 95})

            # Send notification to other agents
            self._send_requirements_notification(card_id, yaml_file, summary)

            # Update progress: complete
            self.update_progress({"step": "complete", "progress_percent": 100})

            self.logger.log("✅ Requirements parsing completed successfully", "SUCCESS")

            return {
                "stage": "requirements_parsing",
                "status": "SUCCESS",
                "structured_requirements": structured_reqs,
                "requirements_yaml_file": str(yaml_file),
                "requirements_json_file": str(json_file),
                "requirements_summary": summary,
                "functional_requirements_count": len(structured_reqs.functional_requirements),
                "non_functional_requirements_count": len(structured_reqs.non_functional_requirements),
                "use_cases_count": len(structured_reqs.use_cases),
                "stakeholders_count": len(structured_reqs.stakeholders)
            }

        except RequirementsFileError as e:
            self.logger.log(f"❌ Requirements file error: {e}", "ERROR")
            raise

        except RequirementsParsingError as e:
            self.logger.log(f"❌ Requirements parsing error: {e}", "ERROR")
            raise

        except RequirementsExportError as e:
            self.logger.log(f"❌ Requirements export error: {e}", "ERROR")
            raise

        except Exception as e:
            raise wrap_exception(
                e,
                RequirementsParsingError,
                f"Unexpected error during requirements parsing for card {card_id}",
                context={"card_id": card_id, "requirements_file": requirements_file}
            )

    def get_stage_name(self) -> str:
        """Return stage name"""
        return "requirements_parsing"

    def _store_requirements_in_rag(
        self,
        card_id: str,
        task_title: str,
        structured_reqs: StructuredRequirements
    ):
        """Store requirements in RAG for downstream stages"""
        try:
            # Create summary content for RAG
            content = f"""Requirements for {task_title}

Project: {structured_reqs.project_name}
Version: {structured_reqs.version}

Executive Summary:
{structured_reqs.executive_summary or 'N/A'}

Requirements Summary:
- Functional Requirements: {len(structured_reqs.functional_requirements)}
- Non-Functional Requirements: {len(structured_reqs.non_functional_requirements)}
- Use Cases: {len(structured_reqs.use_cases)}
- Data Requirements: {len(structured_reqs.data_requirements)}
- Integration Requirements: {len(structured_reqs.integration_requirements)}
- Stakeholders: {len(structured_reqs.stakeholders)}

Business Goals:
{chr(10).join(f"- {goal}" for goal in structured_reqs.business_goals)}

This structured requirements document can be used by the architecture stage to generate ADRs.
"""

            # Store in RAG using helper (DRY)


            RAGStorageHelper.store_stage_artifact(


                rag=self.rag,
                stage_name="requirements",
                card_id=card_id,
                task_title=task_title,
                content=content,
                metadata={
                    "project_name": structured_reqs.project_name,
                    "version": structured_reqs.version,
                    "functional_count": len(structured_reqs.functional_requirements),
                    "non_functional_count": len(structured_reqs.non_functional_requirements),
                    "use_cases_count": len(structured_reqs.use_cases),
                    "stakeholders_count": len(structured_reqs.stakeholders)
                }
            )

            self.logger.log(f"Stored requirements in RAG for card {card_id}", "DEBUG")

        except Exception as e:
            self.logger.log(f"Warning: Could not store requirements in RAG: {e}", "WARNING")

    def _send_requirements_notification(
        self,
        card_id: str,
        yaml_file: Path,
        summary: str
    ):
        """Send requirements parsing notification to other agents"""
        try:
            self.messenger.send_notification(
                to_agent="all",
                card_id=card_id,
                notification_type="requirements_parsed",
                data={
                    "requirements_file": str(yaml_file),
                    "summary": summary
                }
            )

            # Update shared state
            self.messenger.update_shared_state(
                card_id=card_id,
                updates={
                    "requirements_parsed": True,
                    "requirements_file": str(yaml_file),
                    "current_stage": "requirements_complete"
                }
            )

        except Exception as e:
            self.logger.log(f"Warning: Could not send requirements notification: {e}", "WARNING")

    def _store_requirements_in_knowledge_graph(
        self,
        card_id: str,
        task_title: str,
        card: Dict,
        structured_reqs: StructuredRequirements
    ):
        """Store requirements in Knowledge Graph for traceability"""
        kg = get_knowledge_graph()
        if not kg:
            self.logger.log("Knowledge Graph not available - skipping KG storage", "DEBUG")
            return

        try:
            self.logger.log("Storing requirements in Knowledge Graph...", "DEBUG")

            # Add task node
            kg.add_task(
                card_id=card_id,
                title=task_title,
                priority=card.get('priority', 'medium'),
                status='in_progress',
                assigned_agents=['requirements_parser']
            )

            req_count = 0

            # Add functional requirement nodes
            for req in structured_reqs.functional_requirements:
                kg.add_requirement(
                    req_id=req.id,
                    title=req.title,
                    type='functional',
                    priority=req.priority.value,
                    status='active'
                )
                # Link requirement to task
                kg.link_requirement_to_task(req.id, card_id)
                req_count += 1

            # Add non-functional requirement nodes
            for req in structured_reqs.non_functional_requirements:
                kg.add_requirement(
                    req_id=req.id,
                    title=req.title,
                    type=req.type.value,
                    priority=req.priority.value,
                    status='active'
                )
                # Link requirement to task
                kg.link_requirement_to_task(req.id, card_id)
                req_count += 1

            # Add use case requirement nodes
            for use_case in structured_reqs.use_cases:
                kg.add_requirement(
                    req_id=use_case.id,
                    title=use_case.title,
                    type='use_case',
                    priority=use_case.priority.value,
                    status='active'
                )
                # Link use case to task
                kg.link_requirement_to_task(use_case.id, card_id)
                req_count += 1

            self.logger.log(f"✅ Stored {req_count} requirements in Knowledge Graph", "INFO")
            self.logger.log(f"   Task node: {card_id}", "DEBUG")

        except Exception as e:
            self.logger.log(f"Warning: Could not store requirements in Knowledge Graph: {e}", "WARNING")
            self.logger.log(f"   Exception details: {type(e).__name__}", "DEBUG")
