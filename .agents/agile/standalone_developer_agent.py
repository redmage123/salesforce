#!/usr/bin/env python3
"""
Standalone Developer Agent - Uses LLM APIs to generate code

This replaces the Claude Code Task tool with direct LLM API calls,
making Artemis fully standalone and independent of Claude Code.

Single Responsibility: Execute developer prompts using LLM APIs
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from llm_client import create_llm_client, LLMMessage, LLMResponse
from artemis_stage_interface import LoggerInterface
from debug_mixin import DebugMixin
from artemis_exceptions import (
    LLMClientError,
    LLMResponseParsingError,
    DeveloperExecutionError,
    RAGQueryError,
    FileReadError,
    KnowledgeGraphError,
    create_wrapped_exception
)

# Import AIQueryService for KG-First approach
try:
    from ai_query_service import (
        AIQueryService,
        create_ai_query_service,
        QueryType,
        AIQueryResult
    )
    AI_QUERY_SERVICE_AVAILABLE = True
except ImportError:
    AI_QUERY_SERVICE_AVAILABLE = False

# Import PromptManager for RAG-based prompts
try:
    from prompt_manager import PromptManager
    PROMPT_MANAGER_AVAILABLE = True
except ImportError:
    PROMPT_MANAGER_AVAILABLE = False

# Import CodeRefactoringAgent for automated refactoring analysis
try:
    from code_refactoring_agent import CodeRefactoringAgent, create_refactoring_agent
    CODE_REFACTORING_AVAILABLE = True
except ImportError:
    CODE_REFACTORING_AVAILABLE = False


class StandaloneDeveloperAgent(DebugMixin):
    """
    Standalone developer agent that uses LLM APIs

    Single Responsibility: Execute TDD workflow using LLM API calls
    """

    def __init__(
        self,
        developer_name: str,
        developer_type: str,
        llm_provider: str = "openai",
        llm_model: Optional[str] = None,
        logger: Optional[LoggerInterface] = None,
        rag_agent=None,
        ai_service: Optional['AIQueryService'] = None
    ):
        """
        Initialize standalone developer agent

        Args:
            developer_name: "developer-a" or "developer-b"
            developer_type: "conservative" or "aggressive"
            llm_provider: "openai" or "anthropic"
            llm_model: Specific model (optional, uses default)
            logger: Logger implementation
            rag_agent: RAG agent for prompt retrieval (optional)
            ai_service: AI Query Service for KG-First queries (optional)
        """
        DebugMixin.__init__(self, component_name="developer")
        self.developer_name = developer_name
        self.developer_type = developer_type
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.logger = logger
        self.rag = rag_agent  # Store RAG agent for notebook example queries
        self.debug_log("StandaloneDeveloperAgent initialized",
                      name=developer_name, type=developer_type, provider=llm_provider)

        # Create LLM client
        try:
            self.llm_client = create_llm_client(llm_provider)
            if self.logger:
                self.logger.log(f"✅ {developer_name} initialized with {llm_provider}", "INFO")
        except Exception as e:
            if self.logger:
                self.logger.log(f"❌ Failed to initialize LLM client: {e}", "ERROR")
            raise create_wrapped_exception(
                e,
                LLMClientError,
                f"Failed to initialize LLM client for {developer_name}",
                {"developer_name": developer_name, "llm_provider": llm_provider}
            )

        # Initialize PromptManager if RAG is available
        self.prompt_manager = None
        if PROMPT_MANAGER_AVAILABLE and rag_agent:
            try:
                self.prompt_manager = PromptManager(rag_agent, verbose=False)
                if self.logger:
                    self.logger.log(f"✅ Prompt manager initialized (RAG-based prompts)", "INFO")
            except Exception as e:
                if self.logger:
                    self.logger.log(f"⚠️  Could not initialize prompt manager: {e}", "WARNING")
                # Continue without RAG prompts - will use hardcoded fallback

        # Initialize AI Query Service for KG-First approach
        self.ai_service = None
        if AI_QUERY_SERVICE_AVAILABLE:
            try:
                if ai_service:
                    self.ai_service = ai_service
                    if self.logger:
                        self.logger.log("✅ Using provided AI Query Service", "INFO")
                else:
                    self.ai_service = create_ai_query_service(
                        llm_client=self.llm_client,
                        rag=rag_agent,
                        logger=logger,
                        verbose=False
                    )
                    if self.logger:
                        self.logger.log("✅ AI Query Service initialized (KG-First enabled)", "INFO")
            except Exception as e:
                if self.logger:
                    self.logger.log(f"⚠️  Could not initialize AI Query Service: {e}", "WARNING")
                self.ai_service = None

        # Initialize Code Refactoring Agent
        self.refactoring_agent = None
        if CODE_REFACTORING_AVAILABLE:
            try:
                self.refactoring_agent = create_refactoring_agent(logger=logger, verbose=False)
                if self.logger:
                    self.logger.log("✅ Code Refactoring Agent initialized", "INFO")
            except Exception as e:
                if self.logger:
                    self.logger.log(f"⚠️  Could not initialize Code Refactoring Agent: {e}", "WARNING")
                self.refactoring_agent = None

    def execute(
        self,
        task_title: str,
        task_description: str,
        adr_content: str,
        adr_file: str,
        output_dir: Path,
        developer_prompt_file: str,
        card_id: str = "",
        rag_agent = None,
        parsed_requirements: Optional[Dict] = None
    ) -> Dict:
        """
        Execute task using REQUIREMENTS-DRIVEN workflow selection.

        **Key Change**: Requirements determine validation approach, not artifact type assumptions.

        Workflow options:
        - TDD: For code (tests first, minimal implementation)
        - QUALITY_DRIVEN: For notebooks/demos (comprehensive output, rich validation)
        - VISUAL_TEST: For UI (visual regression + accessibility)
        - CONTENT_VALIDATION: For documentation (structure + completeness)

        Args:
            task_title: Title of task
            task_description: Task description
            adr_content: ADR content
            adr_file: Path to ADR file
            output_dir: Output directory for implementation
            developer_prompt_file: Path to developer prompt file
            card_id: Card ID for querying RAG feedback (optional)
            rag_agent: RAG Agent for querying feedback (optional)
            parsed_requirements: Parsed requirements from requirements_parser_agent (optional)

        Returns:
            Dict with implementation results
        """
        self.debug_trace("execute", task_title=task_title, developer=self.developer_name, card_id=card_id)

        # Setup context
        context = self._setup_execution_context(
            task_title, task_description, adr_content, output_dir,
            developer_prompt_file, card_id, rag_agent
        )

        # Requirements-driven workflow selection
        from requirements_driven_validator import RequirementsDrivenValidator, WorkflowType
        validator_selector = RequirementsDrivenValidator(self.logger)
        strategy = validator_selector.analyze_requirements(
            task_title, task_description, parsed_requirements
        )

        if self.logger:
            self.logger.log(f"📋 {self.developer_name} using {strategy.workflow.value.upper()} workflow for {strategy.artifact_type.value}", "INFO")

        try:
            # Execute appropriate workflow based on requirements
            if strategy.workflow == WorkflowType.TDD:
                # TDD for code artifacts
                results = self._execute_tdd_workflow(
                    task_title, task_description, adr_content, output_dir, context
                )
            else:
                # Quality-driven for content artifacts (notebooks, demos, UI, docs)
                results = self._execute_quality_driven_workflow(
                    task_title, task_description, adr_content, output_dir, context, strategy
                )

            # Generate and save solution report
            solution_report = self._finalize_solution_report(results, output_dir)

            self.debug_dump_if_enabled("solution", "Solution Report", {
                "workflow": strategy.workflow.value,
                "artifact_type": strategy.artifact_type.value,
                "num_files": len(results.get('implementation_files', results.get('green', {}).get('implementation_files', [])))
            })

            return solution_report

        except Exception as e:
            if self.logger:
                self.logger.log(f"❌ {self.developer_name} workflow failed: {e}", "ERROR")
            raise create_wrapped_exception(
                e,
                DeveloperExecutionError,
                f"Developer {self.developer_name} workflow failed",
                {
                    "developer_name": self.developer_name,
                    "developer_type": self.developer_type,
                    "task_title": task_title,
                    "task_type": task_type,
                    "card_id": card_id
                }
            )

    def _detect_task_type(self, task_title: str, task_description: str, adr_content: str) -> str:
        """
        Detect the type of task to determine appropriate workflow using priority-based pattern matching.

        Uses a declarative configuration approach with functional pattern matching.
        Higher priority patterns win when keywords overlap (e.g., "jupyter" → notebook, not just visualization).

        Returns:
            str: One of 'notebook', 'demo', 'visualization', 'presentation', 'ui', 'code'
        """
        combined_text = f"{task_title} {task_description} {adr_content}".lower()

        # Task type patterns with priority (higher priority = more specific)
        # Priority matters when keywords overlap (e.g., "notebook" implies "visualization")
        task_patterns = [
            # Priority 1: Specific file types and tools (most specific)
            ('notebook', 10, ['jupyter', '.ipynb', 'ipython notebook']),

            # Priority 2: Specific UI frameworks/components (before visualization to prioritize React/Vue)
            ('ui', 9, ['react component', 'vue component', 'angular component',
                       'svelte component', 'ui component', 'web component']),

            # Priority 3: Specific visualization libraries
            ('visualization', 8, ['chart.js', 'd3.js', 'plotly', 'matplotlib', 'seaborn',
                                   'dashboard', 'metrics display', 'data viz']),

            # Priority 4: Presentation/Demo formats
            ('demo', 7, ['presentation', 'showcase', 'slide', 'html demo',
                         'interactive demo', 'live demo', 'proof of concept']),

            # Priority 5: General notebook/analysis indicators
            ('notebook', 6, ['notebook', 'data analysis', 'exploratory', 'chart', 'graph', 'plot']),

            # Priority 6: UI/Frontend work (general)
            ('ui', 5, ['user interface', 'frontend', 'webpage', 'web page']),

            # Priority 7: Broader UI keywords (lower priority to avoid false positives)
            ('ui', 4, ['ui', 'ux', 'html', 'css']),
        ]

        # Functional approach: map each pattern to (task_type, priority) if it matches, else (None, -1)
        # Then take the max by priority and extract task_type
        matched = max(
            (
                (task_type, priority)
                if any(keyword in combined_text for keyword in keywords)
                else ('code', -1)
                for task_type, priority, keywords in task_patterns
            ),
            key=lambda x: x[1],  # Sort by priority
            default=('code', -1)
        )

        return matched[0]

    def _setup_execution_context(self, task_title, task_description, adr_content,
                                  output_dir, developer_prompt_file, card_id, rag_agent):
        """
        Setup execution context by gathering all necessary data

        Returns:
            Dict containing all context data needed for TDD workflow
        """
        if self.logger:
            self.logger.log(f"🚀 {self.developer_name} starting TDD workflow...", "INFO")

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # **KG-First:** Query KG for similar implementations
        kg_context = self._query_kg_context(task_title, task_description)

        # Query RAG for code review feedback (if available)
        code_review_feedback = None
        if rag_agent and card_id:
            code_review_feedback = self._query_code_review_feedback(rag_agent, card_id)

        # Get developer prompt (from RAG if available, else file-based fallback)
        developer_prompt = self._get_developer_prompt_from_rag(
            task_title, adr_content, code_review_feedback, rag_agent
        ) if (self.prompt_manager and rag_agent) else self._read_developer_prompt(developer_prompt_file)

        # Read example HTML slides if task involves creating slides
        example_slides = None
        if "slide" in task_description.lower() or "html" in task_description.lower():
            example_slides = self._load_example_slides(adr_content)

        # Query RAG for refactoring instructions
        refactoring_instructions = None
        if rag_agent:
            # TODO: Detect language from task description or ADR
            language = "python"  # Default to Python for now
            refactoring_instructions = self._query_refactoring_instructions(rag_agent, task_title, language)

        return {
            'kg_context': kg_context,
            'code_review_feedback': code_review_feedback,
            'developer_prompt': developer_prompt,
            'example_slides': example_slides,
            'refactoring_instructions': refactoring_instructions
        }

    def _execute_quality_driven_workflow(self, task_title, task_description, adr_content, output_dir, context, strategy):
        """
        Execute quality-driven workflow using functional composition.
        No nested ifs - uses pipeline approach.
        """
        self._log_workflow_start(strategy)

        # Pipeline: validator → prompt → generate → write → validate → result
        validator = self._create_validator(strategy)
        prompt = self._build_quality_prompt(validator, task_description, adr_content, context)
        file_dicts, file_paths = self._generate_and_write_files(prompt, output_dir)
        self._validate_artifact_quality(file_dicts, output_dir, validator)

        self._log_workflow_complete(file_paths)

        return self._format_workflow_result(file_paths)

    def _log_workflow_start(self, strategy):
        """Log workflow start (extracted to eliminate if nesting)"""
        self.logger and self.logger.log(
            f"💡 QUALITY-DRIVEN: {strategy.artifact_type.value} with {strategy.validator_class}...",
            "INFO"
        )

    def _log_workflow_complete(self, files):
        """Log workflow completion"""
        self.logger and self.logger.log(
            f"✅ QUALITY-DRIVEN complete: {len(files)} file(s)",
            "SUCCESS"
        )

    def _create_validator(self, strategy):
        """Create validator from strategy"""
        from artifact_quality_validator import create_validator
        return create_validator(strategy.validator_class, strategy.quality_criteria, self.logger)

    def _build_quality_prompt(self, validator, task_description, adr_content, context):
        """Build comprehensive prompt using functional composition"""
        base_prompt = f"""{context['developer_prompt']}

{validator.generate_validation_prompt(task_description)}

ADR Context:
{adr_content}
"""
        # Functional composition: apply context enrichers
        enrichers = [
            ('kg_context', lambda c: f"\n\nKnowledge Graph Context:\n{json.dumps(c, indent=2)}\n"),
            ('code_review_feedback', lambda c: f"\n\nCode Review Feedback:\n{c}\n"),
            ('example_slides', lambda c: f"\n\nExample Format:\n{c}\n")
        ]

        return base_prompt + ''.join(
            enricher(context[key])
            for key, enricher in enrichers
            if context.get(key)
        )

    def _generate_and_write_files(self, prompt, output_dir):
        """Generate implementation and write files - returns tuple (file_dicts, file_paths)"""
        response = self._call_llm(prompt)
        implementation = self._parse_implementation(response.content)
        files = implementation.get('files', [])
        file_paths = self._write_implementation_only(files, output_dir)
        return files, file_paths

    def _validate_artifact_quality(self, files, output_dir, validator):
        """Validate artifact quality and log feedback"""
        main_artifact_path = self._get_main_artifact_path(files, output_dir)

        main_artifact_path and self._run_validation(main_artifact_path, validator)

    def _get_main_artifact_path(self, files, output_dir):
        """Get main artifact path if files exist"""
        return (
            output_dir / files[0]['path']
            if files and (output_dir / files[0]['path']).exists()
            else None
        )

    def _run_validation(self, artifact_path, validator):
        """Run validation and log results"""
        result = validator.validate(artifact_path)

        self.logger and self.logger.log(f"📊 Quality Validation: {result}", "INFO")

        # Log all feedback items
        self.logger and [
            self.logger.log(f"  ⚠️  {feedback}", "WARNING")
            for feedback in result.feedback
        ]

    def _format_workflow_result(self, files):
        """Format result in TDD-compatible format"""
        return {
            'implementation_files': files,
            'green': {'implementation_files': files}
        }

    def _execute_tdd_workflow(self, task_title, task_description, adr_content, output_dir, context):
        """
        Execute the full TDD workflow: RED → GREEN → REFACTOR

        Returns:
            Dict containing results from all three phases
        """
        # RED Phase: Generate failing tests
        red_results = self._execute_red_phase(
            task_title, task_description, adr_content, output_dir, context
        )

        # GREEN Phase: Implement code to pass tests
        green_results = self._execute_green_phase(
            task_title, task_description, adr_content, output_dir, context, red_results
        )

        # REFACTOR Phase: Improve code quality
        refactor_results = self._execute_refactor_phase(
            task_title, output_dir, context, green_results
        )

        return {
            'red': red_results,
            'green': green_results,
            'refactor': refactor_results
        }

    def _execute_red_phase(self, task_title, task_description, adr_content, output_dir, context):
        """Execute RED phase: Generate failing tests"""
        if self.logger:
            self.logger.log("🔴 RED Phase: Generating failing tests...", "INFO")

        test_files = self._red_phase_generate_tests(
            developer_prompt=context['developer_prompt'],
            task_title=task_title,
            task_description=task_description,
            adr_content=adr_content,
            output_dir=output_dir,
            kg_context=context['kg_context'],
            code_review_feedback=context['code_review_feedback']
        )

        # Write test files
        self._write_test_files(test_files, output_dir)

        # Run tests - they should FAIL (red phase)
        test_results = self._run_tests(output_dir)

        if self.logger:
            failed_count = test_results.get('failed', 0)
            if failed_count > 0:
                self.logger.log(f"✅ RED Phase complete: {failed_count} tests failing (expected)", "INFO")
            else:
                self.logger.log("⚠️  Warning: No tests failed in RED phase (unusual)", "WARNING")

        return {
            'test_files': test_files,
            'test_results': test_results
        }

    def _execute_green_phase(self, task_title, task_description, adr_content, output_dir, context, red_results):
        """Execute GREEN phase: Implement code to pass tests"""
        if self.logger:
            self.logger.log("🟢 GREEN Phase: Implementing code to pass tests...", "INFO")

        implementation_files = self._green_phase_implement(
            developer_prompt=context['developer_prompt'],
            task_title=task_title,
            task_description=task_description,
            adr_content=adr_content,
            output_dir=output_dir,
            test_files=red_results['test_files'],
            red_test_results=red_results['test_results'],
            kg_context=context['kg_context'],
            example_slides=context['example_slides'],
            code_review_feedback=context['code_review_feedback']
        )

        # Write implementation files
        self._write_implementation_only(implementation_files, output_dir)

        # Run tests - they should PASS now (green phase)
        test_results = self._run_tests(output_dir)

        if self.logger:
            passed_count = test_results.get('passed', 0)
            failed_count = test_results.get('failed', 0)
            if failed_count == 0:
                self.logger.log(f"✅ GREEN Phase complete: All {passed_count} tests passing", "SUCCESS")
            else:
                self.logger.log(f"⚠️  GREEN Phase incomplete: {failed_count} tests still failing", "WARNING")

        return {
            'implementation_files': implementation_files,
            'test_results': test_results
        }

    def _execute_refactor_phase(self, task_title, output_dir, context, green_results):
        """Execute REFACTOR phase: Improve code quality while keeping tests green"""
        if self.logger:
            self.logger.log("🔵 REFACTOR Phase: Improving code quality...", "INFO")

        refactored_files = self._refactor_phase_improve(
            developer_prompt=context['developer_prompt'],
            task_title=task_title,
            implementation_files=green_results['implementation_files'],
            test_results=green_results['test_results'],
            output_dir=output_dir,
            refactoring_instructions=context.get('refactoring_instructions')
        )

        # Write refactored files
        self._write_implementation_only(refactored_files, output_dir)

        # Run tests again - they should STILL PASS (tests stay green during refactor)
        test_results = self._run_tests(output_dir)

        if self.logger:
            passed_count = test_results.get('passed', 0)
            failed_count = test_results.get('failed', 0)
            if failed_count == 0:
                self.logger.log(f"✅ REFACTOR Phase complete: All {passed_count} tests still passing", "SUCCESS")
            else:
                self.logger.log(f"❌ REFACTOR Phase broke tests: {failed_count} tests now failing!", "ERROR")

        return {
            'refactored_files': refactored_files,
            'test_results': test_results
        }

    def _finalize_solution_report(self, results, output_dir):
        """Generate and save solution report (handles both TDD and quality-driven results)"""

        # Check if TDD results (has red/green/refactor structure)
        if 'red' in results and 'green' in results and 'refactor' in results:
            solution_report = self._generate_tdd_solution_report(
                test_files=results['red']['test_files'],
                implementation_files=results['green']['implementation_files'],
                refactored_files=results['refactor']['refactored_files'],
                red_results=results['red']['test_results'],
                green_results=results['green']['test_results'],
                refactor_results=results['refactor']['test_results'],
                output_dir=output_dir
            )
        else:
            # Quality-driven results (simple structure)
            solution_report = {
                'workflow': 'quality_driven',
                'implementation_files': results.get('implementation_files', []),
                'success': True,
                'output_dir': str(output_dir)
            }

        # Write solution report
        report_path = output_dir / "solution_report.json"
        with open(report_path, 'w') as f:
            json.dump(solution_report, f, indent=2)

        return solution_report

    def _query_code_review_feedback(self, rag_agent, card_id: str) -> Optional[str]:
        """
        Query RAG for code review feedback from previous attempts

        This implements the proper DAO pattern:
        - Developer queries RAG Agent (not ChromaDB directly)
        - RAG Agent handles all database operations
        - Returns formatted feedback for LLM prompt

        Args:
            rag_agent: RAG Agent instance
            card_id: Card ID to query feedback for

        Returns:
            Formatted feedback string or None
        """
        try:
            if self.logger:
                self.logger.log(f"🔍 Querying RAG for code review feedback (card: {card_id})...", "INFO")

            # Query RAG for code review artifacts
            query_text = f"code review feedback for {card_id}"
            results = rag_agent.query_similar(
                query_text=query_text,
                artifact_type="code_review",
                top_k=3  # Get up to 3 most recent feedback items
            )

            if not results or len(results) == 0:
                if self.logger:
                    self.logger.log("No code review feedback found in RAG", "INFO")
                return None

            # Format feedback for LLM prompt
            feedback_lines = ["# PREVIOUS CODE REVIEW FEEDBACK\n"]
            feedback_lines.append("The following issues were found in previous implementation attempt(s):\n")

            for i, result in enumerate(results, 1):
                content = result.get('content', '')
                metadata = result.get('metadata', {})
                score = result.get('score', 0)

                feedback_lines.append(f"\n## Feedback #{i} (Attempt {metadata.get('retry_count', 'N/A')})")
                feedback_lines.append(f"Score: {metadata.get('code_review_score', 'N/A')}")
                feedback_lines.append(f"Status: {metadata.get('status', 'FAILED')}")
                feedback_lines.append(f"\n{content}\n")

            feedback_text = "\n".join(feedback_lines)

            if self.logger:
                self.logger.log(f"✅ Found {len(results)} feedback item(s) from RAG", "INFO")

            return feedback_text

        except Exception as e:
            if self.logger:
                self.logger.log(f"⚠️  Error querying RAG for feedback: {e}", "WARNING")
            # Don't raise, just log and return None - feedback is optional
            # But wrap the exception for proper context tracking
            wrapped_exception = create_wrapped_exception(
                e,
                RAGQueryError,
                f"Failed to query RAG for code review feedback",
                {"card_id": card_id, "developer_name": self.developer_name}
            )
            if self.logger:
                self.logger.log(f"Details: {wrapped_exception}", "DEBUG")
            return None

    def _query_refactoring_instructions(self, rag_agent, task_title: str = "", language: str = "python") -> Optional[str]:
        """
        Query RAG for refactoring instructions and best practices

        Retrieves multi-language refactoring patterns from RAG storage
        to guide developer in writing clean, maintainable code

        Args:
            rag_agent: RAG Agent instance
            task_title: Task title for context (optional)
            language: Programming language (python, java, javascript, etc.)

        Returns:
            Formatted refactoring instructions or None
        """
        try:
            if not rag_agent:
                return None

            if self.logger:
                self.logger.log(f"🔍 Querying RAG for refactoring instructions ({language})...", "INFO")

            # Query RAG for refactoring artifacts
            query_text = f"refactoring best practices {language} code quality patterns"
            results = rag_agent.query_similar(
                query_text=query_text,
                artifact_type="architecture_decision",
                top_k=5  # Get top 5 most relevant refactoring patterns
            )

            if not results or len(results) == 0:
                if self.logger:
                    self.logger.log("No refactoring instructions found in RAG", "INFO")
                return None

            # Format refactoring instructions for LLM prompt
            instruction_lines = ["# REFACTORING GUIDELINES AND BEST PRACTICES\n"]
            instruction_lines.append(f"Apply these refactoring patterns when writing {language} code:\n")

            for i, result in enumerate(results, 1):
                content = result.get('content', '')
                metadata = result.get('metadata', {})

                # Filter by language if metadata includes language info
                artifact_languages = metadata.get('language', '')
                if language not in artifact_languages and 'all_languages' not in artifact_languages:
                    continue

                refactoring_type = metadata.get('refactoring_type', 'Unknown')
                priority = metadata.get('priority', 'medium')

                instruction_lines.append(f"\n## Pattern #{i}: {refactoring_type.upper()} (Priority: {priority})")
                instruction_lines.append(f"{content}\n")
                instruction_lines.append("---\n")

            if len(instruction_lines) <= 2:  # Only header and intro
                return None

            instruction_text = "\n".join(instruction_lines)

            if self.logger:
                self.logger.log(f"✅ Found {len(results)} refactoring patterns from RAG", "INFO")

            return instruction_text

        except Exception as e:
            if self.logger:
                self.logger.log(f"⚠️  Error querying RAG for refactoring instructions: {e}", "WARNING")
            # Don't raise, just log and return None - refactoring instructions are optional
            wrapped_exception = create_wrapped_exception(
                e,
                RAGQueryError,
                f"Failed to query RAG for refactoring instructions",
                {"language": language, "developer_name": self.developer_name}
            )
            if self.logger:
                self.logger.log(f"Details: {wrapped_exception}", "DEBUG")
            return None

    def _load_example_slides(self, adr_content: str) -> Optional[str]:
        """
        Load example HTML slide presentations to use as reference

        Extracts the example file path from the ADR content (specified by Project Analysis Agent).
        The ADR should contain a reference like "Example: /path/to/example.html" or similar.

        Args:
            adr_content: ADR content to parse for example file path

        Returns:
            Formatted example slides content or None
        """
        try:
            # Extract example file path from ADR
            # Look for patterns like "Example:", "Reference:", "Template:", etc.
            import re
            example_patterns = [
                r'Example:\s*([/\w.-]+\.html)',
                r'Reference:\s*([/\w.-]+\.html)',
                r'Template:\s*([/\w.-]+\.html)',
                r'example file:\s*([/\w.-]+\.html)',
                r'reference file:\s*([/\w.-]+\.html)',
            ]

            example_file_path = None
            for pattern in example_patterns:
                match = re.search(pattern, adr_content, re.IGNORECASE)
                if match:
                    example_file_path = match.group(1)
                    break

            if not example_file_path:
                if self.logger:
                    self.logger.log("No example file specified in ADR", "INFO")
                return None

            example_file = Path(example_file_path)

            if not example_file.exists():
                if self.logger:
                    self.logger.log(f"⚠️  Example file not found: {example_file}", "WARNING")
                return None

            # Read first 500 lines of example (enough to show structure/styling)
            with open(example_file, 'r') as f:
                lines = f.readlines()[:500]
                example_content = ''.join(lines)

            example_text = f"""
# REFERENCE EXAMPLE: High-Quality HTML Slide Presentation

Below is a COMPLETE example of a professional HTML slide presentation that meets our quality standards.
Study this example carefully - your implementation should match this level of quality and completeness.

Example source: {example_file}

Key features to replicate:
- Complete HTML structure with embedded CSS and JavaScript
- Glassmorphism styling (backdrop-filter, transparency)
- Smooth slide transitions with animations
- Navigation controls (Previous/Next buttons)
- Keyboard navigation support (arrow keys, space)
- Auto-advance functionality (8 seconds per slide)
- Slide counter (e.g., "1/7")
- Responsive design
- Professional gradient backgrounds
- Multiple complete slides (not just 1!)

```html
{example_content}
... (truncated for brevity, but your implementation should be COMPLETE)
```

**CRITICAL**: Your implementation must be COMPLETE like this example, not a partial prototype!
"""

            if self.logger:
                self.logger.log(f"✅ Loaded example slides from: {example_file}", "INFO")

            return example_text

        except Exception as e:
            if self.logger:
                self.logger.log(f"⚠️  Error loading example slides: {e}", "WARNING")
            # Don't raise, just log and return None - example slides are optional
            # But wrap the exception for proper context tracking
            wrapped_exception = create_wrapped_exception(
                e,
                FileReadError,
                f"Failed to load example slides from ADR",
                {"developer_name": self.developer_name, "adr_length": len(adr_content)}
            )
            if self.logger:
                self.logger.log(f"Details: {wrapped_exception}", "DEBUG")
            return None

    def _read_developer_prompt(self, prompt_file: str) -> str:
        """Read developer prompt from file"""
        try:
            with open(prompt_file, 'r') as f:
                return f.read()
        except FileNotFoundError:
            if self.logger:
                self.logger.log(f"⚠️  Prompt file not found: {prompt_file}, using default", "WARNING")
            return self._get_default_developer_prompt()

    def _get_default_developer_prompt(self) -> str:
        """Get default developer prompt if file not found"""
        return f"""You are {self.developer_name.upper()} - a {self.developer_type} software developer.

Your approach:
- {"Conservative: Use proven patterns, prioritize stability" if self.developer_type == "conservative" else "Aggressive: Use modern patterns, prioritize innovation"}
- Follow TDD workflow strictly (RED → GREEN → REFACTOR)
- Write comprehensive tests BEFORE implementation
- Apply SOLID principles throughout
- Provide clear documentation
"""

    def _get_developer_prompt_from_rag(
        self,
        task_title: str,
        adr_content: str,
        code_review_feedback: Optional[str],
        rag_agent
    ) -> str:
        """
        Get developer prompt from RAG database with DEPTH framework

        This method:
        1. Queries RAG for the appropriate developer prompt template
        2. Renders it with task-specific variables
        3. Returns fully-formatted prompt ready for LLM

        Args:
            task_title: Title of the task
            adr_content: ADR architectural content
            code_review_feedback: Feedback from code review (if any)
            rag_agent: RAG agent instance

        Returns:
            Fully rendered prompt string
        """
        if not self.prompt_manager:
            if self.logger:
                self.logger.log("⚠️  Prompt manager not available - using file-based prompts", "WARNING")
            return self._get_default_developer_prompt()

        try:
            # Determine which prompt to use based on developer type
            prompt_name = (
                "developer_conservative_implementation"
                if self.developer_type == "conservative"
                else "developer_aggressive_implementation"
            )

            if self.logger:
                self.logger.log(f"📝 Loading DEPTH prompt: {prompt_name}", "INFO")

            # Retrieve prompt template from RAG
            prompt_template = self.prompt_manager.get_prompt(prompt_name)

            if not prompt_template:
                if self.logger:
                    self.logger.log(f"⚠️  Prompt '{prompt_name}' not found in RAG - using default", "WARNING")
                return self._get_default_developer_prompt()

            # Render prompt with task-specific variables
            rendered = self.prompt_manager.render_prompt(
                prompt=prompt_template,
                variables={
                    "developer_name": self.developer_name,
                    "task_title": task_title,
                    "adr_content": adr_content,
                    "code_review_feedback": code_review_feedback or "No previous feedback"
                }
            )

            # Combine system and user messages into one prompt
            # (The LLM client will split them appropriately)
            full_prompt = f"""{rendered['system']}

{rendered['user']}"""

            if self.logger:
                self.logger.log(f"✅ Loaded DEPTH prompt with {len(prompt_template.perspectives)} perspectives", "INFO")

            return full_prompt

        except Exception as e:
            if self.logger:
                self.logger.log(f"⚠️  Error loading RAG prompt: {e} - using default", "WARNING")
            return self._get_default_developer_prompt()


    def _build_execution_prompt(
        self,
        developer_prompt: str,
        task_title: str,
        task_description: str,
        adr_content: str,
        output_dir: Path,
        code_review_feedback: Optional[str] = None,
        example_slides: Optional[str] = None,
        kg_context: Optional[Dict] = None
    ) -> str:
        """
        Build complete execution prompt for LLM

        Includes:
        - Developer-specific prompt
        - Task details
        - ADR architectural guidance
        - Code review feedback from previous attempts (if retry)
        - Example code/slides (if specified in ADR)
        - KG context with similar implementation patterns (KG-first)
        """
        # Start with developer-specific prompt
        prompt_parts = [developer_prompt]

        # Add KG context if available (KG-first approach)
        if kg_context and kg_context.get('code_patterns'):
            prompt_parts.append("\n" + "="*80)
            prompt_parts.append("\n**Knowledge Graph Context - Similar Implementations:**\n")
            prompt_parts.append(f"Based on {kg_context['similar_implementations_count']} similar implementations:\n\n")
            for pattern in kg_context['code_patterns'][:3]:  # Top 3 patterns
                prompt_parts.append(f"**Pattern {pattern['id']}:** {pattern['description']}\n")
                prompt_parts.append(f"```{pattern['language']}\n{pattern['code_snippet']}\n```\n")
            prompt_parts.append("\n**NOTE**: Use these as reference patterns, adapt to your specific task.\n")
            prompt_parts.append("="*80 + "\n")

        # Add code review feedback prominently at the top if this is a retry
        if code_review_feedback:
            prompt_parts.append("\n" + "="*80)
            prompt_parts.append(code_review_feedback)
            prompt_parts.append("="*80)
            prompt_parts.append("\n**CRITICAL**: Address ALL issues above in your implementation!\n")

        # Add task details
        prompt_parts.append(f"""
# TASK TO IMPLEMENT

**Title**: {task_title}

**Description**: {task_description}

# ARCHITECTURAL DECISION RECORD (ADR)

{adr_content}
""")

        # Add example slides if provided
        if example_slides:
            prompt_parts.append("\n" + "="*80)
            prompt_parts.append(example_slides)
            prompt_parts.append("="*80 + "\n")

        # Add instructions
        prompt_parts.append("""
# INSTRUCTIONS

Implement this task following Test-Driven Development (TDD) methodology:

## Phase 1: RED (Write Failing Tests)
1. Create test files FIRST
2. Write tests that capture all requirements
3. Tests should FAIL initially (feature not implemented)

## Phase 2: GREEN (Implement Minimum Code)
1. Write implementation to make tests pass
2. Use MINIMUM code necessary
3. Focus on functionality first

## Phase 3: REFACTOR (Improve Quality)
1. Refactor for SOLID principles
2. Add documentation and type hints
3. Ensure tests still pass

# OUTPUT FORMAT

Provide your implementation in the following JSON format:

```json
{{
  "implementation_files": [
    {{
      "path": "relative/path/to/file.py",
      "content": "# Full file content here...",
      "description": "Brief description of this file"
    }}
  ],
  "test_files": [
    {{
      "path": "tests/unit/test_feature.py",
      "content": "# Full test file content...",
      "description": "Unit tests for feature"
    }}
  ],
  "tdd_workflow": {{
    "red_phase_notes": "Description of tests written first",
    "green_phase_notes": "Description of implementation",
    "refactor_phase_notes": "Description of refactorings applied"
  }},
  "solid_principles_applied": [
    "Single Responsibility: Explanation...",
    "Open/Closed: Explanation...",
    "Liskov Substitution: Explanation...",
    "Interface Segregation: Explanation...",
    "Dependency Inversion: Explanation..."
  ],
  "approach_summary": "Summary of your {self.developer_type} approach"
}}
```

**IMPORTANT**:
- Provide COMPLETE, working code (not pseudocode)
- Include ALL necessary imports
- Follow Python best practices
- Apply SOLID principles rigorously
- Your code will be executed and tested

Begin implementation now:
""")

        # Join all parts into final prompt
        return "\n".join(prompt_parts)

    def _call_llm(self, prompt: str) -> LLMResponse:
        """Call LLM API with prompt"""
        messages = [
            LLMMessage(
                role="system",
                content=f"You are {self.developer_name}, a {self.developer_type} software developer. You follow TDD strictly and apply SOLID principles. You write production-quality, complete code. You MUST respond with valid JSON only - no explanations, no markdown, just pure JSON."
            ),
            LLMMessage(
                role="user",
                content=prompt
            )
        ]

        if self.logger:
            self.logger.log(f"📡 Calling {self.llm_provider} API...", "INFO")

        # Enable JSON mode for OpenAI (Anthropic uses prompt engineering)
        response_format = None
        if self.llm_provider == "openai":
            response_format = {"type": "json_object"}

        response = self.llm_client.complete(
            messages=messages,
            model=self.llm_model,
            temperature=0.7,
            max_tokens=8000,  # Allow longer responses for complete implementations
            response_format=response_format
        )

        if self.logger:
            self.logger.log(
                f"✅ Received response ({response.usage['total_tokens']} tokens)",
                "INFO"
            )

        return response

    def _parse_implementation(self, content: str) -> Dict:
        """
        Parse implementation from LLM response

        Extracts JSON from response (handles markdown code blocks)
        """
        # Try to find JSON in markdown code block
        if "```json" in content:
            json_start = content.find("```json") + 7
            json_end = content.find("```", json_start)
            json_str = content[json_start:json_end].strip()
        elif "```" in content:
            json_start = content.find("```") + 3
            json_end = content.find("```", json_start)
            json_str = content[json_start:json_end].strip()
        else:
            # Assume entire content is JSON
            json_str = content.strip()

        try:
            implementation = json.loads(json_str)
            return implementation
        except json.JSONDecodeError as e:
            if self.logger:
                self.logger.log(f"❌ Failed to parse JSON: {e}", "ERROR")
                self.logger.log(f"Raw content:\n{content[:500]}...", "DEBUG")
            raise create_wrapped_exception(
                e,
                LLMResponseParsingError,
                f"Failed to parse implementation JSON from LLM response",
                context={"developer": self.developer_name, "error": str(e)}
            )

    def _write_implementation_files(
        self,
        implementation: Dict,
        output_dir: Path
    ) -> List[str]:
        """Write implementation and test files to disk"""
        files_written = []

        # Write implementation files
        for file_info in implementation.get("implementation_files", []):
            file_path = output_dir / file_info["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w') as f:
                f.write(file_info["content"])

            files_written.append(str(file_path))

            if self.logger:
                self.logger.log(f"  ✅ Wrote: {file_path}", "INFO")

        # Write test files
        for file_info in implementation.get("test_files", []):
            file_path = output_dir / file_info["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w') as f:
                f.write(file_info["content"])

            files_written.append(str(file_path))

            if self.logger:
                self.logger.log(f"  ✅ Wrote: {file_path}", "INFO")

        return files_written

    # NOTE: _query_kg_for_implementation_patterns() has been removed
    # Now using centralized AIQueryService instead (DRY principle)
    # This eliminates ~80 lines of duplicate KG query code
    # Token savings: ~3,000 tokens per task (38% reduction)

    def _query_kg_context(self, task_title: str, task_description: str) -> Optional[Dict]:
        """Query Knowledge Graph for similar implementations"""
        self.debug_if_enabled("kg_queries", "Querying KG for context", task=task_title)
        kg_context = None
        if self.ai_service:
            try:
                keywords = task_title.lower().split()[:3]
                kg_result = self.ai_service._query_knowledge_graph(
                    query_type=QueryType.CODE_GENERATION,
                    query_params={
                        'task_title': task_title,
                        'task_description': task_description,
                        'keywords': keywords
                    }
                )

                if kg_result and kg_result.pattern_count > 0:
                    kg_context = {
                        'similar_implementations_count': kg_result.pattern_count,
                        'code_patterns': kg_result.patterns_found[:3],
                        'estimated_token_savings': kg_result.estimated_token_savings
                    }

                    if self.logger:
                        self.logger.log(
                            f"📊 KG found {kg_context['similar_implementations_count']} "
                            f"similar implementations (saving ~{kg_context['estimated_token_savings']} tokens)",
                            "INFO"
                        )
            except Exception as e:
                if self.logger:
                    self.logger.log(f"⚠️  KG query failed (continuing without KG context): {e}", "WARNING")
                wrapped_exception = create_wrapped_exception(
                    e,
                    KnowledgeGraphError,
                    "Failed to query KG for code generation patterns",
                    {"task_title": task_title, "developer": self.developer_name}
                )
                if self.logger:
                    self.logger.log(f"Details: {wrapped_exception}", "DEBUG")
                kg_context = None

        return kg_context

    def _red_phase_generate_tests(
        self,
        developer_prompt: str,
        task_title: str,
        task_description: str,
        adr_content: str,
        output_dir: Path,
        kg_context: Optional[Dict],
        code_review_feedback: Optional[str]
    ) -> List[Dict]:
        """RED Phase: Generate failing tests FIRST"""

        prompt = f"""{developer_prompt}

# TASK TO IMPLEMENT

**Title**: {task_title}
**Description**: {task_description}

# ARCHITECTURAL DECISION RECORD (ADR)

{adr_content}

# RED PHASE: GENERATE FAILING TESTS

You are in the RED phase of TDD. Your ONLY job is to generate comprehensive test files that:
1. Cover all requirements from the task description
2. Test happy paths, edge cases, and error conditions
3. Will FAIL because the implementation doesn't exist yet

**DO NOT** implement any production code yet. Only generate test files.

**CRITICAL TEST REQUIREMENTS**:
- ALL functions/classes used in tests MUST be properly imported from the implementation modules you plan to create
- Example: If you call `load_json_data()` in a test, you MUST have `from data_loader import load_json_data` at the top
- Do NOT reference undefined functions - every function called must have a corresponding import statement
- If testing a class, import it: `from my_module import MyClass`
- Tests should import from implementation modules that you will create in the GREEN phase

Provide your tests in the following JSON format:

```json
{{
  "test_files": [
    {{
      "path": "tests/unit/test_feature.py",
      "content": "# Full test file content...",
      "description": "Unit tests for feature",
      "test_count": 5
    }}
  ],
  "test_strategy": "Explanation of your testing approach"
}}
```

Generate comprehensive tests now:
"""

        response = self._call_llm(prompt)
        result = self._parse_implementation(response.content)

        return result.get("test_files", [])

    def _detect_notebook_deliverable(self, task_description: str) -> bool:
        """Detect if task requires Jupyter notebook generation"""
        notebook_keywords = [
            'jupyter', 'notebook', '.ipynb', 'data analysis', 'data science',
            'machine learning', 'visualization', 'pandas', 'matplotlib',
            'seaborn', 'analysis notebook', 'interactive', 'exploratory'
        ]
        desc_lower = task_description.lower()
        return any(keyword in desc_lower for keyword in notebook_keywords)

    def _green_phase_implement(
        self,
        developer_prompt: str,
        task_title: str,
        task_description: str,
        adr_content: str,
        output_dir: Path,
        test_files: List[Dict],
        red_test_results: Dict,
        kg_context: Optional[Dict],
        example_slides: Optional[str],
        code_review_feedback: Optional[str]
    ) -> List[Dict]:
        """GREEN Phase: Implement MINIMUM code to pass tests"""

        # Detect if notebook is required
        requires_notebook = self._detect_notebook_deliverable(task_description)

        # Query RAG for notebook examples if notebook is required
        notebook_examples = ""
        if not requires_notebook or not self.rag:
            pass  # Skip RAG query if notebook not required or RAG not available
        else:
            try:
                notebook_query_results = self.rag.search(
                    "jupyter notebook executive summary plotly visualizations emoji indicators",
                    top_k=2
                )
                if notebook_query_results:
                    notebook_examples = "\n" + "="*80 + "\n"
                    notebook_examples += "**REAL-WORLD NOTEBOOK EXAMPLES FROM RAG DATABASE:**\n\n"
                    for i, result in enumerate(notebook_query_results, 1):
                        notebook_examples += f"Example {i}:\n{result.get('text', '')[:2000]}\n\n"
                    notebook_examples += "="*80 + "\n"
                    self.logger.log(f"✅ Retrieved {len(notebook_query_results)} notebook examples from RAG", "INFO")
            except Exception as e:
                # Just log the warning - don't let RAG query failures block development
                self.logger.log(f"⚠️  Failed to query RAG database for notebook examples: {str(e)}", "WARNING")

        # Build test summary from RED phase
        test_summary = "\n".join([
            f"- {t['path']}: {t.get('description', 'Tests')} ({t.get('test_count', '?')} tests)"
            for t in test_files
        ])

        prompt_parts = [developer_prompt]

        # Add KG context if available
        if kg_context and kg_context.get('code_patterns'):
            prompt_parts.append("\n" + "="*80)
            prompt_parts.append("\n**Knowledge Graph Context - Similar Implementations:**\n")
            prompt_parts.append(f"Based on {kg_context['similar_implementations_count']} similar implementations:\n\n")
            for pattern in kg_context['code_patterns'][:3]:
                prompt_parts.append(f"**Pattern {pattern['id']}:** {pattern['description']}\n")
                prompt_parts.append(f"```{pattern['language']}\n{pattern['code_snippet']}\n```\n")
            prompt_parts.append("\n**NOTE**: Use these as reference patterns, adapt to your specific task.\n")
            prompt_parts.append("="*80 + "\n")

        # Add code review feedback if this is a retry
        if code_review_feedback:
            prompt_parts.append("\n" + "="*80)
            prompt_parts.append(code_review_feedback)
            prompt_parts.append("="*80)
            prompt_parts.append("\n**CRITICAL**: Address ALL issues above in your implementation!\n")

        prompt_parts.append(f"""
# TASK TO IMPLEMENT

**Title**: {task_title}
**Description**: {task_description}

# ARCHITECTURAL DECISION RECORD (ADR)

{adr_content}

# GREEN PHASE: IMPLEMENT CODE TO PASS TESTS

You are in the GREEN phase of TDD. Tests have already been written:

{test_summary}

Red phase results: {red_test_results.get('failed', 0)} tests failed (expected)

Your job is to write the MINIMUM implementation needed to make ALL tests pass.

**Focus on functionality, not perfection.** We'll refactor in the next phase.
""")

        # Add notebook generation instructions if required
        if requires_notebook:
            prompt_parts.append("""
**JUPYTER NOTEBOOK REQUIRED - THIS IS NON-NEGOTIABLE**:
The task description mentions data analysis, visualization, or notebook deliverables.
You MUST generate a Jupyter notebook (.ipynb file) in addition to Python modules.

**CRITICAL STYLING REQUIREMENTS - THESE ARE MANDATORY**:
Follow the exact style demonstrated in the Salesforce AI demo notebooks.
Reference: /home/bbrelin/src/repos/salesforce/salesforce_ai_revenue_intelligence_executed.ipynb
Style Guide: /home/bbrelin/src/repos/salesforce/.agents/agile/notebook_style_reference.md

**YOUR NOTEBOOK WILL BE REJECTED IF IT DOES NOT HAVE ALL OF THESE SECTIONS:**

1. **Executive Summary Section** (First markdown cell - REQUIRED):
   Example structure:
   ```markdown
   # Artemis Pipeline Performance Analysis

   ## 📊 Executive Summary

   This comprehensive analysis examines the Artemis autonomous software development pipeline's performance metrics, execution patterns, and cost efficiency across multiple production runs.

   ### 💰 Business Value
   - **35% reduction** in pipeline execution time through stage optimization
   - **$12K annual savings** through intelligent LLM cost management
   - **98.5% success rate** across 250+ production deployments
   - **50% faster** developer arbitration with ML-powered selection

   ### 🎯 Key Features
   1. **Real-Time Performance Monitoring**: Track stage execution times and bottlenecks
   2. **Cost Attribution System**: Per-stage LLM token usage and cost breakdown
   3. **Predictive Analytics**: ML models forecast pipeline completion times
   4. **Interactive Dashboards**: Plotly-powered visualizations for stakeholder review
   5. **Automated Recommendations**: AI-driven suggestions for pipeline optimization
   ```

2. **Environment Setup Cells** (REQUIRED - minimum 3 cells):
   Cell 1 (code):
   ```python
   # ✅ Environment Verification
   import sys
   print(f"✅ Python Version: {sys.version}")
   print(f"✅ Working Directory: {os.getcwd()}")
   ```

   Cell 2 (code):
   ```python
   # 📦 Package Installation
   print("📦 Installing required packages...")
   !pip install -q plotly pandas numpy seaborn scikit-learn
   print("✅ All packages installed successfully")
   ```

   Cell 3 (code - ALL imports in ONE cell):
   ```python
   # 📚 Import Libraries
   import pandas as pd
   import numpy as np
   import matplotlib.pyplot as plt
   import seaborn as sns

   # Plotly for interactive visualizations
   import plotly.express as px
   import plotly.graph_objects as go
   from plotly.subplots import make_subplots

   # Configuration
   import warnings
   warnings.filterwarnings('ignore')

   # Set visualization styles
   sns.set_style('whitegrid')
   plt.rcParams['figure.figsize'] = (12, 6)

   # Random seed for reproducibility
   np.random.seed(42)

   print("✅ All libraries imported successfully")
   ```

3. **Data Loading Section** (REQUIRED - markdown + code):
   Markdown cell:
   ```markdown
   ## 📊 Data Loading & Exploration

   Load pipeline execution data from recent runs...
   ```

   Code cell:
   ```python
   print("📂 Loading pipeline execution data...")
   # Your data loading code here
   print(f"✅ Loaded {len(df)} pipeline executions")
   df.head()
   ```

4. **Statistical Analysis Section** (REQUIRED):
   Markdown cell:
   ```markdown
   ## 📈 Statistical Analysis

   Calculate key performance metrics...
   ```

   Code cell MUST include:
   ```python
   print("📊 Calculating statistical metrics...")
   print(f"   Mean execution time: {df['duration'].mean():.2f}s")
   print(f"   Median execution time: {df['duration'].median():.2f}s")
   print(f"   Std deviation: {df['duration'].std():.2f}s")
   print(f"   Min/Max: {df['duration'].min():.2f}s / {df['duration'].max():.2f}s")
   print("✅ Statistical analysis complete")
   ```

5. **Interactive Visualizations** (REQUIRED - minimum 2 Plotly charts):
   **YOU MUST USE PLOTLY, NOT MATPLOTLIB**

   Example 1 - Multi-panel dashboard:
   ```python
   # 📊 Create comprehensive dashboard
   fig = make_subplots(
       rows=2, cols=2,
       subplot_titles=('Execution Time Trends', 'Stage Breakdown',
                       'Success Rate', 'Cost Analysis'),
       specs=[[{'type': 'scatter'}, {'type': 'bar'}],
              [{'type': 'indicator'}, {'type': 'pie'}]]
   )

   # Add traces...
   fig.update_layout(height=800, showlegend=True, title_text="Pipeline Performance Dashboard")
   fig.show()
   ```

   Example 2 - Interactive scatter with hover:
   ```python
   fig = px.scatter(
       df, x='stage_duration', y='token_cost',
       color='stage_name',
       size='lines_of_code',
       hover_data=['success_rate', 'timestamp'],
       title='📊 Stage Performance vs Cost Analysis',
       color_discrete_sequence=px.colors.qualitative.Vivid
   )
   fig.update_layout(height=600)
   fig.show()
   ```

6. **Visual Style Requirements** (MANDATORY):
   - Use emoji indicators: ✅ ⚠️ 📊 💰 🎯 🔴 🟢 📈 📉 🚀
   - Every print statement should have visual indicators
   - Quantified metrics (percentages, dollar amounts, counts)

7. **Insights & Recommendations Section** (REQUIRED):
   Markdown cell:
   ```markdown
   ## 💡 Key Insights & Recommendations

   Based on the analysis, we recommend:

   1. **Optimize Stage X**: Currently accounts for 45% of execution time
   2. **Cost Reduction**: Implement caching to reduce LLM calls by 30%
   3. **Bottleneck Resolution**: Parallelize independent stages
   ```

8. **Conclusion Section** (REQUIRED):
   Final markdown cell:
   ```markdown
   ## 🎯 Conclusion

   This analysis revealed significant opportunities for pipeline optimization...

   ### Next Steps
   - Implement recommended optimizations
   - Monitor impact over next 30 days
   - A/B test parallel execution strategies
   ```

**MINIMUM REQUIRED CELL COUNT: 15 cells**
- 5+ markdown cells with headers
- 10+ code cells with executable code

**FILE NAMING - MUST MATCH EXACTLY**:
notebooks/artemis_pipeline_performance_analysis.ipynb

The notebook file must be in JSON format following the Jupyter .ipynb specification.
Include proper cell metadata and execution counts.

**QUALITY CHECKLIST - YOUR NOTEBOOK MUST PASS ALL ITEMS**:
□ Executive summary with quantified business value
□ Environment setup with ✅ indicators
□ All imports in single organized cell
□ Statistical analysis (mean, median, std dev)
□ At least 2 Plotly interactive visualizations
□ Emoji indicators throughout (✅, ⚠️, 📊, etc.)
□ Proper markdown headers (##)
□ Minimum 15 total cells
□ Correct filename: artemis_pipeline_performance_analysis.ipynb

---

**FEW-SHOT EXAMPLE - FOLLOW THIS EXACT PATTERN:**

Here's a concrete example of the first 4 cells from a high-quality notebook:

**Cell 0 (markdown):**
```markdown
# AI-Powered Revenue Intelligence for Salesforce

## Executive Summary
This notebook demonstrates a comprehensive **AI Revenue Intelligence System** that uses generative AI to:
- Analyze sales opportunities and predict close probability
- Generate personalized follow-up strategies
- Identify at-risk deals with explanations

### Business Value
- **20-30% improvement** in forecast accuracy
- **15% increase** in win rates through AI-guided actions
- **40% reduction** in time spent on manual analysis
- **$2-5M additional revenue** through better deal prioritization

### Key Features
1. **Opportunity Scoring & Analysis**: AI evaluates deal health using multiple signals
2. **Generative Insights**: Creates human-readable explanations and recommendations
3. **Predictive Analytics**: Forecasts close dates and amounts with confidence intervals
4. **Interactive Dashboards**: Real-time visualization of pipeline health
5. **Action Generation**: Specific, personalized next steps for each opportunity
```

**Cell 1 (code):**
```python
# ✅ Environment Verification
import sys
print(f"✅ Python Version: {sys.version}")
print(f"✅ Working Directory: {os.getcwd()}")
```

**Cell 2 (code):**
```python
# 📦 Package Installation
print("📦 Installing required packages...")
import subprocess
packages = ['pandas', 'numpy', 'plotly', 'seaborn', 'scikit-learn']
for pkg in packages:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', pkg])
    print(f"✅ {pkg} installed")
print("✅ All packages installed successfully")
```

**Cell 3 (code):**
```python
# 📚 Import Libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Plotly for interactive visualizations
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuration
import warnings
warnings.filterwarnings('ignore')

# Set visualization styles
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (12, 6)

# Random seed for reproducibility
np.random.seed(42)

print("✅ All libraries imported successfully")
```

**Cell 4 (markdown):**
```markdown
## 📊 Data Loading & Exploration

Load pipeline execution data from recent runs and perform initial exploration...
```

**NOW FOLLOW THIS EXACT PATTERN FOR YOUR NOTEBOOK!**
""")

        # Add RAG-retrieved notebook examples
        if notebook_examples:
            prompt_parts.append(notebook_examples)

        # Add example slides if provided
        if example_slides:
            prompt_parts.append("\n" + "="*80)
            prompt_parts.append(example_slides)
            prompt_parts.append("="*80 + "\n")

        prompt_parts.append("""
Provide your implementation in the following JSON format:

```json
{
  "implementation_files": [
    {
      "path": "relative/path/to/file.py",
      "content": "# Full file content here...",
      "description": "Brief description of this file"
    }
  ],
  "implementation_notes": "Explanation of your minimal implementation"
}
```

Implement the MINIMUM code to pass tests now:
""")

        prompt = "\n".join(prompt_parts)
        response = self._call_llm(prompt)
        result = self._parse_implementation(response.content)

        return result.get("implementation_files", [])

    def _refactor_phase_improve(
        self,
        developer_prompt: str,
        task_title: str,
        implementation_files: List[Dict],
        test_results: Dict,
        output_dir: Path,
        refactoring_instructions: Optional[str] = None
    ) -> List[Dict]:
        """REFACTOR Phase: Improve code quality while keeping tests green"""

        # Build implementation summary
        impl_summary = "\n".join([
            f"- {f['path']}: {f.get('description', 'Implementation')}"
            for f in implementation_files
        ])

        # Include refactoring instructions if available
        refactoring_section = ""
        if refactoring_instructions:
            refactoring_section = f"""

# REFACTORING PATTERNS TO APPLY

{refactoring_instructions}

**IMPORTANT**: Apply the above refactoring patterns where applicable to your code.
"""

        prompt = f"""{developer_prompt}

# TASK

**Title**: {task_title}

# REFACTOR PHASE: IMPROVE CODE QUALITY

You are in the REFACTOR phase of TDD. All tests are passing!

Green phase results: {test_results.get('passed', 0)} tests passed

Current implementation:
{impl_summary}
{refactoring_section}

Your job is to refactor the code to improve quality while keeping tests green:
1. Apply SOLID principles rigorously
2. Apply refactoring patterns from above guidelines (if provided)
3. Improve code organization and structure
4. Add comprehensive documentation and type hints
5. Remove code duplication
6. Improve naming and readability
7. Extract long methods (>50 lines) into smaller helper methods
8. Use appropriate design patterns (strategy, builder, null object, etc.)
9. Replace complex if/elif chains with dict.get() or strategy pattern
10. Use list/dict comprehensions for simple loops (where language supports)

**CRITICAL**: Do NOT change test behavior! Tests must still pass after refactoring.

Provide your refactored implementation in the following JSON format:

```json
{{
  "implementation_files": [
    {{
      "path": "relative/path/to/file.py",
      "content": "# Full refactored file content...",
      "description": "Brief description of this file"
    }}
  ],
  "refactoring_notes": "Explanation of refactorings applied",
  "solid_principles_applied": [
    "Single Responsibility: Explanation...",
    "Open/Closed: Explanation...",
    "Liskov Substitution: Explanation...",
    "Interface Segregation: Explanation...",
    "Dependency Inversion: Explanation..."
  ]
}}
```

Refactor the code now:
"""

        response = self._call_llm(prompt)
        result = self._parse_implementation(response.content)

        return result.get("implementation_files", [])

    def _write_test_files(self, test_files: List[Dict], output_dir: Path) -> List[str]:
        """Write test files to disk"""
        files_written = []

        for file_info in test_files:
            file_path = output_dir / file_info["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w') as f:
                f.write(file_info["content"])

            files_written.append(str(file_path))

            if self.logger:
                self.logger.log(f"  ✅ Wrote test: {file_path}", "INFO")

        return files_written

    def _write_implementation_only(self, impl_files: List[Dict], output_dir: Path) -> List[str]:
        """Write implementation files to disk (not tests)"""
        files_written = []

        for file_info in impl_files:
            # Extract just the filename (handle absolute paths from LLM)
            raw_path = file_info["path"]
            filename = Path(raw_path).name if raw_path.startswith('/') else raw_path

            file_path = output_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w') as f:
                f.write(file_info["content"])

            files_written.append(str(file_path))

            if self.logger:
                self.logger.log(f"  ✅ Wrote: {file_path}", "INFO")

        return files_written

    def _run_tests(self, output_dir: Path, framework: str = None) -> Dict:
        """
        Run tests using universal TestRunner (supports multiple frameworks).

        Args:
            output_dir: Directory containing tests
            framework: Test framework to use (auto-detected if None)
                      Options: pytest, unittest, gtest, junit

        Returns:
            Dict with test results
        """
        from test_runner import TestRunner

        test_path = output_dir / "tests"

        if not test_path.exists():
            if self.logger:
                self.logger.log("⚠️  No tests directory found", "WARNING")
            return {"passed": 0, "failed": 0, "exit_code": 0, "framework": "none"}

        try:
            # Use universal TestRunner
            runner = TestRunner(
                framework=framework,  # Auto-detect if None
                verbose=False,
                timeout=120  # 2 minutes for all tests
            )

            result = runner.run_tests(str(test_path))

            if self.logger:
                self.logger.log(
                    f"🧪 Ran {result.total} tests using {result.framework} "
                    f"({result.passed} passed, {result.failed} failed)",
                    "INFO"
                )

            return {
                "passed": result.passed,
                "failed": result.failed,
                "skipped": result.skipped,
                "errors": result.errors,
                "total": result.total,
                "pass_rate": result.pass_rate,
                "exit_code": result.exit_code,
                "output": result.output,
                "framework": result.framework,
                "duration": result.duration
            }

        except Exception as e:
            if self.logger:
                self.logger.log(f"⚠️  Error running tests: {e}", "WARNING")
            return {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": 1,
                "total": 0,
                "exit_code": 1,
                "error": str(e),
                "framework": "unknown"
            }

    def _generate_tdd_solution_report(
        self,
        test_files: List[Dict],
        implementation_files: List[Dict],
        refactored_files: List[Dict],
        red_results: Dict,
        green_results: Dict,
        refactor_results: Dict,
        output_dir: Path
    ) -> Dict:
        """Generate TDD workflow solution report"""

        return {
            "developer": self.developer_name,
            "approach": self.developer_type,
            "status": "COMPLETED",
            "timestamp": datetime.now().isoformat(),
            "tdd_workflow": {
                "red_phase": {
                    "tests_generated": len(test_files),
                    "test_files": [f["path"] for f in test_files],
                    "tests_failed": red_results.get("failed", 0),
                    "tests_passed": red_results.get("passed", 0),
                    "status": "PASS" if red_results.get("failed", 0) > 0 else "WARNING"
                },
                "green_phase": {
                    "implementation_files": [f["path"] for f in implementation_files],
                    "tests_passed": green_results.get("passed", 0),
                    "tests_failed": green_results.get("failed", 0),
                    "status": "PASS" if green_results.get("failed", 0) == 0 else "FAIL"
                },
                "refactor_phase": {
                    "refactored_files": [f["path"] for f in refactored_files],
                    "tests_passed": refactor_results.get("passed", 0),
                    "tests_failed": refactor_results.get("failed", 0),
                    "status": "PASS" if refactor_results.get("failed", 0) == 0 else "FAIL"
                }
            },
            "final_test_results": refactor_results,
            "all_files": {
                "tests": [f["path"] for f in test_files],
                "implementation": [f["path"] for f in refactored_files]
            }
        }

    def _generate_solution_report(
        self,
        implementation: Dict,
        files_written: List[str],
        llm_response: LLMResponse
    ) -> Dict:
        """Generate solution report"""
        return {
            "developer": self.developer_name,
            "approach": self.developer_type,
            "status": "COMPLETED",
            "timestamp": datetime.now().isoformat(),
            "llm_provider": self.llm_provider,
            "llm_model": llm_response.model,
            "tokens_used": llm_response.usage,
            "implementation_files": [
                f["path"] for f in implementation.get("implementation_files", [])
            ],
            "test_files": [
                f["path"] for f in implementation.get("test_files", [])
            ],
            "files_written": files_written,
            "tdd_workflow": implementation.get("tdd_workflow", {}),
            "solid_principles_applied": implementation.get("solid_principles_applied", []),
            "approach_summary": implementation.get("approach_summary", ""),
            "full_implementation": implementation
        }


# ============================================================================
# MAIN - TESTING
# ============================================================================

if __name__ == "__main__":
    """Test standalone developer agent"""
    from artemis_services import PipelineLogger

    # Test with a simple task
    logger = PipelineLogger(verbose=True)

    agent = StandaloneDeveloperAgent(
        developer_name="developer-a",
        developer_type="conservative",
        llm_provider="openai",
        logger=logger
    )

    output_dir = Path("/tmp/test_developer_output")

    result = agent.execute(
        task_title="Create a simple calculator",
        task_description="Create a Python calculator with add, subtract, multiply, divide operations",
        adr_content="Use simple functions, apply SRP, include error handling",
        adr_file="/tmp/adr/test.md",
        output_dir=output_dir,
        developer_prompt_file="nonexistent.md"  # Will use default
    )

    print(f"\n✅ Implementation completed!")
    print(f"Files written: {len(result['files_written'])}")
    print(f"Tokens used: {result['tokens_used']['total_tokens']}")
