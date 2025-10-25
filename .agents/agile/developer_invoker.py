#!/usr/bin/env python3
"""
Developer Invoker (SOLID: Single Responsibility)

Single Responsibility: Invoke developer agents (A/B) as separate Claude sessions

This class handles ONLY developer invocation - nothing else.
Uses Claude Code's Task tool to launch autonomous developer agents.
"""

from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
import json
import os

from artemis_stage_interface import LoggerInterface
from standalone_developer_agent import StandaloneDeveloperAgent
from artemis_constants import get_developer_prompt_path
from pipeline_observer import PipelineObservable, EventBuilder
from environment_context import get_environment_context_short
from path_config_service import get_path_config
from debug_mixin import DebugMixin
from requirements_parser_agent import RequirementsParserAgent


class DeveloperInvoker(DebugMixin):
    """
    Invoke Developer A and Developer B as autonomous agents

    Single Responsibility: Launch and coordinate developer agents
    - Invokes agents via Claude Code Task tool
    - Passes ADR and task context to each developer
    - Waits for completion
    - Collects results
    """

    def __init__(self, logger: LoggerInterface, observable: Optional[PipelineObservable] = None):
        DebugMixin.__init__(self, component_name="developer_invoker")
        self.logger = logger
        self.observable = observable

        # Get developer output base directory from environment or use default
        self.developer_base_dir = self._get_developer_base_dir()

        # Initialize requirements parser
        llm_provider = os.getenv("ARTEMIS_LLM_PROVIDER", "openai")
        self.requirements_parser = RequirementsParserAgent(
            llm_provider=llm_provider,
            logger=logger
        )

    def _get_developer_base_dir(self) -> Path:
        """
        Get the base directory for developer outputs via PathConfigService

        Returns configured directory using centralized path configuration service.
        """
        return get_path_config().developer_output_dir

    def invoke_developer(
        self,
        developer_name: str,
        developer_type: str,
        card: Dict,
        adr_content: str,
        adr_file: str,
        output_dir: Path,
        rag_agent=None  # RAG Agent for querying code review feedback
    ) -> Dict:
        """
        Invoke a single developer agent

        Args:
            developer_name: "developer-a" or "developer-b"
            developer_type: "conservative" or "aggressive"
            card: Kanban card with task details
            adr_content: Full ADR content
            adr_file: Path to ADR file
            output_dir: Directory for developer output
            rag_agent: RAG Agent for querying feedback (optional)

        Returns:
            Dict with developer results
        """
        self.debug_trace("invoke_developer",
                        developer_name=developer_name,
                        developer_type=developer_type,
                        card_id=card.get('card_id', 'unknown'),
                        output_dir=str(output_dir))

        self.logger.log(f"Invoking {developer_name} ({developer_type} approach)", "INFO")

        # Notify developer started
        card_id = card.get('card_id', 'unknown')
        if self.observable:
            event = EventBuilder.developer_started(
                card_id,
                developer_name,
                developer_type=developer_type,
                task_title=card.get('title')
            )
            self.observable.notify(event)

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Determine which developer prompt file to use (using centralized constant)
        prompt_file = str(get_developer_prompt_path(developer_name))

        # Get LLM provider from env or use default
        llm_provider = os.getenv("ARTEMIS_LLM_PROVIDER", "openai")

        # Parse requirements for validation
        parsed_requirements = self._parse_requirements_for_task(card, adr_content)

        # Create standalone developer agent
        agent = StandaloneDeveloperAgent(
            developer_name=developer_name,
            developer_type=developer_type,
            llm_provider=llm_provider,
            logger=self.logger,
            rag_agent=rag_agent  # Pass RAG agent for DEPTH prompts
        )

        # Execute implementation with parsed requirements
        with self.debug_section("Developer Execution", developer=developer_name):
            result = agent.execute(
                task_title=card.get('title', 'Untitled Task'),
                task_description=card.get('description', 'No description provided'),
                adr_content=adr_content,
                adr_file=adr_file,
                output_dir=output_dir,
                developer_prompt_file=prompt_file,
                card_id=card.get('card_id', ''),
                rag_agent=rag_agent,
                parsed_requirements=parsed_requirements  # NEW: Pass parsed requirements
            )

        self.debug_log("Developer execution completed",
                      developer=developer_name,
                      success=result.get('success', False),
                      files_created=len(result.get('files', [])))

        self.logger.log(f"✅ {developer_name} completed", "SUCCESS")

        # Notify developer completed or failed
        if result.get('success', False):
            if self.observable:
                event = EventBuilder.developer_completed(
                    card_id,
                    developer_name,
                    files_created=len(result.get('files', [])),
                    result=result
                )
                self.observable.notify(event)
        else:
            if self.observable:
                error = Exception(result.get('error', 'Developer failed'))
                from pipeline_observer import PipelineEvent, EventType
                event = PipelineEvent(
                    event_type=EventType.DEVELOPER_FAILED,
                    card_id=card_id,
                    developer_name=developer_name,
                    error=error,
                    data=result
                )
                self.observable.notify(event)

        return result

    def _parse_requirements_for_task(self, card: Dict, adr_content: str) -> Optional[Dict]:
        """Parse requirements for validation system using debug tracing"""
        self.debug_trace("_parse_requirements_for_task", card_id=card.get('card_id'))

        try:
            parsed = self.requirements_parser.parse_requirements_for_validation(
                task_title=card.get('title', ''),
                task_description=card.get('description', ''),
                adr_content=adr_content
            )

            self.debug_log("Requirements parsed", artifact_type=parsed.get('artifact_type'))
            return parsed

        except Exception as e:
            self.debug_log("Requirements parsing failed", error=str(e))
            self.logger.log(f"⚠️  Requirements parsing failed: {e}", "WARNING")
            return None

    def invoke_parallel_developers(
        self,
        num_developers: int,
        card: Dict,
        adr_content: str,
        adr_file: str,
        rag_agent=None,  # RAG Agent for querying code review feedback
        parallel_execution: bool = True  # NEW: Enable true parallel execution
    ) -> List[Dict]:
        """
        Invoke multiple developers in parallel

        Args:
            num_developers: Number of developers to invoke (1-3)
            card: Kanban card
            adr_content: ADR content
            adr_file: ADR file path
            rag_agent: RAG Agent for developers to query feedback (optional)
            parallel_execution: Run developers in parallel threads (default: True)

        Returns:
            List of developer results
        """
        self.debug_trace("invoke_parallel_developers",
                        num_developers=num_developers,
                        parallel_execution=parallel_execution,
                        card_id=card.get('card_id', 'unknown'))

        self.logger.log(f"Invoking {num_developers} developer(s) ({'parallel' if parallel_execution else 'sequential'})", "INFO")

        # Prepare developer configurations
        dev_configs = []
        for i in range(num_developers):
            if i == 0:
                dev_name = "developer-a"
                dev_type = "conservative"
            elif i == 1:
                dev_name = "developer-b"
                dev_type = "aggressive"
            else:
                dev_name = f"developer-c"
                dev_type = "innovative"

            # Use configured developer base directory instead of hardcoded /tmp
            output_dir = Path(self.developer_base_dir) / dev_name

            dev_configs.append({
                "developer_name": dev_name,
                "developer_type": dev_type,
                "card": card,
                "adr_content": adr_content,
                "adr_file": adr_file,
                "output_dir": output_dir,
                "rag_agent": rag_agent
            })

        # Execute developers
        if parallel_execution and num_developers > 1:
            # Run in parallel using threads
            developers = self._invoke_parallel_threaded(dev_configs)
        else:
            # Run sequentially (default for single developer or if disabled)
            developers = self._invoke_sequential(dev_configs)

        return developers

    def _invoke_sequential(self, dev_configs: List[Dict]) -> List[Dict]:
        """
        Invoke developers sequentially (one at a time)

        Args:
            dev_configs: List of developer configurations

        Returns:
            List of developer results
        """
        developers = []
        for config in dev_configs:
            result = self.invoke_developer(**config)
            developers.append(result)
        return developers

    def _invoke_parallel_threaded(self, dev_configs: List[Dict]) -> List[Dict]:
        """
        Invoke developers in parallel using threads

        Args:
            dev_configs: List of developer configurations

        Returns:
            List of developer results
        """
        import concurrent.futures
        import threading

        self.logger.log(f"Starting {len(dev_configs)} developers in parallel threads", "INFO")

        developers = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(dev_configs)) as executor:
            # Submit all developer tasks
            future_to_dev = {
                executor.submit(self.invoke_developer, **config): config['developer_name']
                for config in dev_configs
            }

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_dev):
                dev_name = future_to_dev[future]
                try:
                    result = future.result()
                    developers.append(result)
                    self.logger.log(f"✅ {dev_name} completed (parallel)", "SUCCESS")
                except Exception as e:
                    self.logger.log(f"❌ {dev_name} failed with exception: {e}", "ERROR")
                    # Use configured developer output directory via PathConfigService
                    developers.append({
                        "developer": dev_name,
                        "success": False,
                        "error": str(e),
                        "files": [],
                        "output_dir": str(get_path_config().get_developer_dir(dev_name))
                    })

        self.logger.log(f"All {len(dev_configs)} developers completed", "INFO")
        return developers

    def _build_developer_prompt(
        self,
        developer_name: str,
        developer_type: str,
        card: Dict,
        adr_content: str,
        adr_file: str,
        output_dir: Path
    ) -> str:
        """
        Build detailed prompt for developer agent

        This prompt instructs the autonomous agent to:
        1. Read their developer prompt file
        2. Read the ADR
        3. Implement the solution following TDD
        4. Store results in output directory
        """

        # Determine which developer prompt to use (using centralized constant)
        prompt_file = str(get_developer_prompt_path(developer_name))

        task_title = card.get('title', 'Untitled Task')
        task_description = card.get('description', 'No description provided')

        prompt = f"""You are {developer_name.upper()} - the {developer_type} developer in the Artemis competitive pipeline.

CRITICAL INSTRUCTIONS:

1. **Read your developer prompt**: {prompt_file}
   - Follow ALL instructions in your prompt
   - Apply the {developer_type} approach as specified
   - You MUST follow SOLID principles (mandatory)

2. **Read the ADR**: {adr_file}
   - This contains the architectural decisions and guidance
   - Follow the implementation strategy for {developer_name}

3. **Implement the solution using TDD**:

   **TASK**: {task_title}

   **DESCRIPTION**: {task_description}

   **YOUR APPROACH**: {developer_type}

   **OUTPUT DIRECTORY**: {output_dir}

{get_environment_context_short()}

   **MANDATORY TDD WORKFLOW**:

   Phase 1 - RED (Write Failing Tests):
   - Create test files FIRST in: {output_dir}/tests/
   - Write tests that FAIL (feature not implemented yet)
   - Run tests to verify they fail

   **CRITICAL TEST REQUIREMENTS**:
   - DO NOT import external dependencies that you haven't implemented (Kafka, Spark, InfluxDB, etc.)
   - If requirements mention external systems, use unittest.mock to mock them
   - Write EXECUTABLE tests that can run without installing external infrastructure
   - Focus on testing YOUR logic, not external integrations
   - Example: If requirements mention Kafka, use Mock objects instead of actual Kafka imports

   Example of CORRECT test approach:
   ```python
   import unittest
   from unittest.mock import Mock, patch

   class TestDataIngestion(unittest.TestCase):
       @patch('your_module.KafkaProducer')  # Mock external dependency
       def test_kafka_connection(self, mock_kafka):
           mock_kafka.return_value = Mock()
           # Test your logic, not Kafka itself
           result = your_function()
           self.assertIsNotNone(result)
   ```

   Example of INCORRECT test (DO NOT DO THIS):
   ```python
   from kafka import KafkaProducer  # ❌ NOT INSTALLED, WILL FAIL

   class TestDataIngestion(unittest.TestCase):
       def test_kafka_connection(self):
           producer = KafkaProducer(...)  # ❌ CANNOT RUN
   ```

   Phase 2 - GREEN (Make Tests Pass):
   - Implement MINIMUM code to make tests pass
   - Store implementation in: {output_dir}/
   - Use Mock objects for external dependencies mentioned in requirements
   - DO NOT implement actual Kafka/Spark/InfluxDB connections - use mock interfaces
   - Run tests to verify they pass

   Phase 3 - REFACTOR (Improve Quality):
   - Refactor code while keeping tests green
   - Add SOLID compliance
   - Add type hints and docstrings
   - Run tests to ensure still passing

4. **SOLID Compliance (MANDATORY)**:
   - Apply ALL 5 SOLID principles
   - {"Conservative patterns: Dependency Injection, SRP, Strategy" if developer_type == "conservative" else "Advanced patterns: Hexagonal Architecture, Composite, Decorator"}
   - This is NON-NEGOTIABLE and affects arbitration scoring

5. **Store your solution**:
   - Implementation files: {output_dir}/<feature>.py
   - Test files: {output_dir}/tests/unit/test_<feature>.py
   - Test files: {output_dir}/tests/integration/test_<feature>_integration.py
   - Test files: {output_dir}/tests/acceptance/test_<feature>_acceptance.py

6. **Generate solution report**:
   - Create {output_dir}/solution_report.json with:
     - Approach explanation
     - SOLID principles applied
     - Test coverage metrics
     - TDD workflow timestamps

REMEMBER: You are competing against another developer. Your solution will be scored on:
- SOLID compliance (+15 for exceptional, -10 for violations)
- Test coverage (80% minimum for A, 90% for B)
- Code quality
- TDD compliance

Read your prompt file, read the ADR, and implement the best {developer_type} solution!
"""

        return prompt

    def _invoke_via_task_tool(self, developer_name: str, prompt: str) -> Dict:
        """
        Invoke developer via Claude Code Task tool

        NOTE: This is a placeholder for the actual Task tool invocation.
        In production, this would use:

        from claude_code import Task

        result = Task(
            description=f"Developer {developer_name} implementation",
            prompt=prompt,
            subagent_type="general-purpose"
        )

        return result
        """
        # Placeholder - actual implementation would invoke Task tool
        pass
